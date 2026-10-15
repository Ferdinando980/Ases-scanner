"""Bounded, read-only observations of a published frontend."""
from __future__ import annotations

from collections import deque
from hashlib import sha256
from html.parser import HTMLParser
from ipaddress import ip_address
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser
import socket
import tempfile

from .epistemology import stable_fingerprint
from .claims import build_claims

USER_AGENT = "ASES/1.7 (+passive frontend inventory)"
MAX_HTML_BYTES = 1_000_000
MAX_ROBOTS_BYTES = 200_000
SKIP_PATH_SEGMENTS = {"logout", "signout", "delete", "remove"}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.links = []
        self.forms = []
        self.scripts = []
        self.stylesheets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        elif tag == "form":
            self.forms.append({"method": (attrs.get("method") or "GET").upper(), "action": attrs.get("action") or ""})
        elif tag == "script" and attrs.get("src"):
            self.scripts.append(attrs["src"])
        elif tag == "link" and attrs.get("href"):
            rel = (attrs.get("rel") or "").lower()
            if "stylesheet" in rel:
                self.stylesheets.append(attrs["href"])
            elif "modulepreload" in rel or ("preload" in rel and attrs.get("as") == "script"):
                self.scripts.append(attrs["href"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def _canonical(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("A site scan requires an HTTP(S) URL without credentials.")
    host = parts.hostname.lower()
    port = parts.port
    netloc = host if port is None else f"{host}:{port}"
    if ":" in host:
        netloc = f"[{host}]" if port is None else f"[{host}]:{port}"
    return urlunsplit((parts.scheme, netloc, parts.path or "/", parts.query, ""))


def _origin(url: str) -> tuple[str, str, int | None]:
    parts = urlsplit(url)
    return parts.scheme, parts.hostname or "", parts.port


def _public_host(url: str, allow_local: bool) -> None:
    host = urlsplit(url).hostname
    if not host:
        raise ValueError("Site URL has no host.")
    try:
        addresses = {ip_address(item[4][0]) for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise RuntimeError(f"Could not resolve site host: {host}") from exc
    if not addresses or (not allow_local and any(not addr.is_global for addr in addresses)):
        raise ValueError("Site URL resolves to a non-public address; use --allow-local only for a trusted local test site.")


def _get(url: str, *, allow_local: bool, limit: int) -> tuple[str, bytes, str]:
    opener = build_opener(_NoRedirect)
    current = _canonical(url)
    expected_origin = _origin(current)
    for _ in range(4):
        _public_host(current, allow_local)
        request = Request(current, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.1"})
        try:
            response = opener.open(request, timeout=10)
        except HTTPError as exc:
            if exc.code not in {301, 302, 303, 307, 308}:
                raise
            response = exc
        with response:
            if response.status in {301, 302, 303, 307, 308}:
                target = _canonical(urljoin(current, response.headers.get("Location", "")))
                if _origin(target) != expected_origin:
                    raise ValueError("Site redirect leaves the original origin.")
                current = target
                continue
            body = response.read(limit + 1)
            if len(body) > limit:
                raise ValueError(f"Site response exceeds the {limit}-byte limit.")
            return current, body, response.headers.get("Content-Type", "")
    raise ValueError("Site redirected too many times.")


def _robots(start: str, allow_local: bool) -> RobotFileParser:
    robots_url = urljoin(start, "/robots.txt")
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        _, body, _ = _get(robots_url, allow_local=allow_local, limit=MAX_ROBOTS_BYTES)
    except HTTPError as exc:
        if exc.code == 404:
            parser.parse([])
            return parser
        raise RuntimeError(f"Could not read robots.txt (HTTP {exc.code}).") from exc
    parser.parse(body.decode("utf-8", errors="replace").splitlines())
    return parser


def _framework_hints(html: str, url: str) -> list[dict]:
    markers = {
        "Angular": ("ng-version=", "<app-root"),
        "Next.js": ("__NEXT_DATA__", "/_next/static/"),
        "Nuxt": ("__NUXT__", "data-nuxt"),
        "SvelteKit": ("__sveltekit",),
    }
    return [
        {"name": name, "state": "INFERRED", "confidence": "medium", "evidence": [url], "marker": marker}
        for name, choices in markers.items() for marker in choices if marker in html
    ]


def capture_site(url: str, *, max_pages: int = 5, allow_local: bool = False) -> dict:
    """Fetch at most max_pages same-origin HTML pages; never submit forms or execute JS."""
    if not 1 <= max_pages <= 10:
        raise ValueError("max_pages must be between 1 and 10.")
    start = _canonical(url)
    _public_host(start, allow_local)
    robots = _robots(start, allow_local)
    if not robots.can_fetch(USER_AGENT, start):
        raise ValueError("robots.txt disallows fetching the requested page.")

    pages = []
    queue = deque([start])
    seen = set()
    hints = []
    while queue and len(pages) < max_pages:
        target = queue.popleft()
        if target in seen or not robots.can_fetch(USER_AGENT, target):
            continue
        seen.add(target)
        try:
            final_url, body, content_type = _get(target, allow_local=allow_local, limit=MAX_HTML_BYTES)
        except HTTPError as exc:
            if target == start:
                raise RuntimeError(f"Site returned HTTP {exc.code} for the requested page.") from exc
            continue
        except (ValueError, RuntimeError):
            if target == start:
                raise
            continue
        if "text/html" not in content_type.lower():
            if target == start:
                raise ValueError("The requested URL did not return HTML.")
            continue
        html = body.decode("utf-8", errors="replace")
        parser = _PageParser()
        parser.feed(html)
        forms = []
        for form in parser.forms:
            try:
                action = _canonical(urljoin(final_url, form["action"]))
            except ValueError:
                continue
            forms.append({"method": form["method"], "action": action, "external": _origin(action) != _origin(start)})
        scripts = set()
        for src in parser.scripts:
            try:
                scripts.add(_canonical(urljoin(final_url, src)))
            except ValueError:
                continue
        pages.append({
            "url": final_url, "title": parser.title.strip(), "html_sha256": sha256(body).hexdigest(),
            "forms": forms, "scripts": sorted(scripts), "script_count": len(parser.scripts),
            "stylesheet_count": len(parser.stylesheets), "link_count": len(parser.links),
        })
        hints.extend(_framework_hints(html, final_url))
        for href in parser.links:
            try:
                candidate = _canonical(urljoin(final_url, href))
            except ValueError:
                continue
            parts = urlsplit(candidate)
            if (_origin(candidate) == _origin(start) and not parts.query
                    and not any(segment.lower() in SKIP_PATH_SEGMENTS for segment in parts.path.split("/"))
                    and candidate not in seen and candidate not in queue and len(queue) < 50):
                queue.append(candidate)

    if not pages:
        raise RuntimeError("No HTML page was captured.")
    unique_hints = {}
    for item in hints:
        unique_hints.setdefault(item["name"], item)
    return {
        "source_uri": start, "method": "passive_html_get", "max_pages": max_pages,
        "pages": pages, "framework_hints": list(unique_hints.values()),
        "limits": ["Only sampled public HTML and referenced asset URLs were read.",
                   "Scripts were not downloaded or executed; client-rendered routes and API calls may be absent.",
                   "No form was submitted and no authenticated state was accessed."],
    }


def enrich_site_model(model: dict, observations: dict) -> None:
    pages = observations["pages"]
    model["project"].update({"name": urlsplit(observations["source_uri"]).hostname,
                             "source_uri": observations["source_uri"], "source_mode": "LIVE_SITE",
                             "entry_mode": "LIVE_SITE"})
    model["site_observations"] = observations
    model["frontend"]["pages"] = [
        {"id": f"site-page:{page['url']}", "name": page["title"] or page["url"],
         "kind": "published_page", "url": page["url"],
         "provenance": {"state": "OBSERVED", "confidence": "high", "evidence": [page["url"]], "assumptions": []}}
        for page in pages
    ]
    model["source_classification"] = {"roles": {}, "scopes": {}}
    model["unknowns"] = []
    coverage = model["semantic_quality"]["analysis_coverage"]
    for dimension in ("source_structure", "static_behavior", "architecture", "design_patterns",
                      "frontend_structure", "frontend_backend_contracts"):
        coverage[dimension] = {"status": "NOT_OBSERVED", "basis": "The published site does not expose project source structure."}
    coverage["published_frontend"] = {"status": "ANALYZED", "basis": f"Passive GET of {len(pages)} same-origin HTML page(s); no JavaScript execution."}
    coverage["deployment_topology"] = {"status": "UNKNOWN", "basis": "HTTP responses alone do not reveal the deployment topology."}
    evidence = [page["url"] for page in pages]
    scripts = {script for page in pages for script in page["scripts"]}
    forms = sum(len(page["forms"]) for page in pages)
    fp = stable_fingerprint("site.published_frontend_surface", "Published Frontend Surface", evidence)
    finding = {
        "id": f"finding:{fp}", "fingerprint": fp, "rule_id": "site.published_frontend_surface",
        "type": "site_observation", "category": "FRONTEND_SURFACE", "level": "FRONTEND_SURFACE",
        "pattern": "Published Frontend Surface", "subject": "Published Frontend Surface",
        "status": "OBSERVED", "confidence": "high", "scope": "project",
        "reason": f"Observed {len(pages)} public HTML page(s), {forms} form(s), and {len(scripts)} referenced script URL(s) in a bounded sample.",
        "evidence": evidence, "evidence_strength": "DIRECT", "counter_evidence": [],
        "assumptions": ["The sampled HTML may not represent routes rendered only after JavaScript execution or authentication."],
        "signals": {"positive": [], "negative": []}, "guidance": "Use a source scan for component architecture and frontend/backend route contracts.",
        "entity": {"type": "project", "id": "project", "name": model["project"]["name"]},
        "source_role": "MIXED",
    }
    model["frontend_findings"] = [finding]
    model["claims"] = build_claims(model)


def scan_site(url: str, out: Path, *, max_pages: int = 5, allow_local: bool = False) -> dict:
    observations = capture_site(url, max_pages=max_pages, allow_local=allow_local)
    from .pipeline import scan_project
    with tempfile.TemporaryDirectory(prefix="ases-site-") as temp:
        return scan_project(Path(temp), out, source_uri=observations["source_uri"],
                            site_observations=observations)
