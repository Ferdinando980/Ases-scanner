import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from ases.site_source import scan_site


@pytest.fixture
def demo_site():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            if self.path == "/robots.txt":
                body = b"User-agent: *\nDisallow: /private\n"
                kind = "text/plain"
            elif self.path == "/":
                body = (b'<title>Demo</title><app-root></app-root>'
                        b'<link rel="modulepreload" href="/chunk.js">'
                        b'<script src="/main.js"></script>'
                        b'<a href="/about">About</a><a href="/logout">Logout</a>'
                        b'<a href="/private">Private</a>'
                        b'<form method="post" action="/contact"></form>')
                kind = "text/html; charset=utf-8"
            elif self.path == "/about":
                body = b"<title>About</title><p>Public page</p>"
                kind = "text/html"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/", requests
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_site_scan_records_published_evidence_without_source_claims(tmp_path, demo_site):
    url, requests = demo_site
    out = tmp_path / "demo.site.ases"
    result = scan_site(url, out, allow_local=True)
    model = result["semantic_model"]
    observed = model["site_observations"]

    assert result["validation"]["status"] == "PASS"
    assert model["project"]["source_mode"] == "LIVE_SITE"
    assert model["semantic_quality"]["analysis_coverage"]["source_structure"]["status"] == "NOT_OBSERVED"
    assert len(observed["pages"]) == 2
    assert observed["pages"][0]["forms"] == [{"method": "POST", "action": url + "contact", "external": False}]
    assert len(observed["pages"][0]["scripts"]) == 2
    assert observed["framework_hints"][0]["name"] == "Angular"
    assert requests == ["/robots.txt", "/", "/about"]
    assert len(model["frontend"]["pages"]) == 2
    assert model["frontend_findings"][0]["status"] == "OBSERVED"
    assert (out / "docs" / "SITE-OVERVIEW.md").exists()
    assert not (out / "docs" / "RAD.md").exists()
    assert json.loads((out / "consumer-context.json").read_text())["site_observations"]["pages"] == observed["pages"]


def test_site_scan_rejects_private_host_by_default(tmp_path, demo_site):
    url, requests = demo_site
    with pytest.raises(ValueError, match="non-public"):
        scan_site(url, tmp_path / "blocked.site.ases")
    assert not requests
