"""Bounded, inert readers for explicitly structured requirement exports."""
from __future__ import annotations

from html.parser import HTMLParser
import json
import re

DEFAULT_RECORDS = 100_000
DEFAULT_TEXT = 8 * 1024 * 1024
MAX_DEPTH = 256
MAX_NODES = 500_000
MAX_INPUT_BYTES = 32 * 1024 * 1024
_BLOCKS = {"p", "div", "li", "tr", "br", "h1", "h2", "h3", "h4", "h5", "h6", "section"}


class _InertHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style"}:
            self.skip.append(tag)
        if not self.skip and tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if not self.skip and tag in _BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.skip:
            if self.skip[-1] == tag:
                self.skip.pop()
            return
        if tag in _BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def _html_text(value: str) -> tuple[str, list[str]]:
    parser = _InertHTML()
    parser.feed(value)
    parser.close()
    text = re.sub(r"[\t\f\v ]+", " ", "".join(parser.parts))
    text = re.sub(r" *\n+ *", "\n", text).strip()
    return text, parser.links


def _limits(max_records, max_text):
    if type(max_records) is not int or max_records < 0 or type(max_text) is not int or max_text < 0:
        raise ValueError("Limits must be non-negative integers")


def read_reqview(data: bytes, *, max_records=DEFAULT_RECORDS, max_text=DEFAULT_TEXT):
    """Read ReqView's JSON .reqw export without evaluating dashboard or attachment content."""
    _limits(max_records, max_text)
    if not isinstance(data, bytes) or len(data) > MAX_INPUT_BYTES:
        raise ValueError("ReqView input byte limit exceeded or input is not bytes")
    try:
        root = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Malformed ReqView JSON export") from exc
    if not isinstance(root, dict) or not isinstance(root.get("id"), str) or not isinstance(root.get("documents"), list):
        raise ValueError("Unsupported ReqView export structure")
    project_id = root["id"]
    local_ids = set()
    for known_doc in root["documents"]:
        if not isinstance(known_doc, dict) or not isinstance(known_doc.get("id"), str):
            continue
        pending = list(reversed(known_doc.get("data", []))) if isinstance(known_doc.get("data", []), list) else []
        while pending and len(local_ids) <= MAX_NODES:
            known = pending.pop()
            if isinstance(known, dict):
                if isinstance(known.get("id"), (str, int)):
                    local_ids.add(f"{known_doc['id']}-{known['id']}")
                children = known.get("children", [])
                if isinstance(children, list):
                    pending.extend(reversed(children))
    units, requirements, references, notes = [], [], [], []
    text_used = 0
    seen_nodes = 0
    partial = False
    for doc in root["documents"]:
        if not isinstance(doc, dict) or not isinstance(doc.get("id"), str) or not isinstance(doc.get("data", []), list):
            raise ValueError("Malformed ReqView document")
        doc_id = doc["id"]
        type_attr = doc.get("attributes", {}).get("type", {}) if isinstance(doc.get("attributes", {}), dict) else {}
        enum_values = type_attr.get("values", []) if isinstance(type_attr, dict) else []
        labels = {}
        for option in enum_values if isinstance(enum_values, list) else []:
            if isinstance(option, dict) and isinstance(option.get("key"), str):
                labels[option["key"]] = option.get("label", option["key"])
        stack = [(node, (), 1) for node in reversed(doc.get("data", []))]
        while stack:
            node, ancestors, depth = stack.pop()
            seen_nodes += 1
            if seen_nodes > MAX_NODES:
                partial = True
                notes.append("ReqView node limit reached")
                stack.clear()
                break
            if depth > MAX_DEPTH:
                partial = True
                notes.append("ReqView nesting limit reached")
                continue
            if not isinstance(node, dict):
                raise ValueError("Malformed ReqView element")
            row_id = node.get("id")
            node_id = f"{project_id}-{doc_id}-{row_id}" if isinstance(row_id, (str, int)) else None
            heading = node.get("heading") if isinstance(node.get("heading"), str) else ""
            text = ""
            links = []
            if isinstance(node.get("text"), str):
                text, links = _html_text(node["text"])
                room = max_text - text_used
                if len(text) > room:
                    text = text[:room]
                    partial = True
                    notes.append("ReqView extracted-text limit reached")
                text_used += len(text)
            location = {"element": "document-row", "document": doc_id, "row_id": row_id,
                        "path": list(ancestors) + ([row_id] if row_id is not None else [])}
            if text or heading:
                units.append({"text": "\n".join(v for v in (heading, text) if v), "location": location,
                              "document_id": doc_id, "row_id": row_id})
            source_type = node.get("type")
            type_is_declared = isinstance(source_type, str) and source_type in labels
            label = labels.get(source_type) if type_is_declared else None
            type_name = " ".join(str(v) for v in (source_type, label) if v).casefold()
            kind = "functional" if type_is_declared and source_type in {"FR", "RF", "F"} else "nonfunctional" if type_is_declared and source_type in {"NFR", "RNF", "NF"} else "unspecified"
            is_requirement = type_is_declared and (source_type in {"FR", "RF", "F", "NFR", "RNF", "NF", "REQ"} or bool(re.search(r"\brequirements?\b", type_name)))
            attrs = {k: v for k, v in node.items() if k not in {"id", "guid", "children", "text", "links", "attachments"}}
            if is_requirement and node_id:
                if len(requirements) >= max_records:
                    partial = True
                    notes.append("ReqView record limit reached")
                    stack.clear()
                    break
                requirements.append({"id": node_id, "statement": text, "kind": kind,
                    "recognition": "explicit-reqview/1", "location": location, "title": heading,
                    "status": node.get("status"), "source_kind": source_type,
                    "identifier_origin": "native-reqview", "declared_id": row_id,
                    "project_id": project_id, "document_id": doc_id, "attributes": attrs})
                for relation, targets in (node.get("links", {}) or {}).items():
                    if not isinstance(targets, list):
                        continue
                    for target in targets:
                        if isinstance(target, str):
                            qualified_target = f"{project_id}-{target}" if target in local_ids else target
                            references.append({"source": node_id, "target": qualified_target, "native_role": relation,
                                "direction": "source-to-target", "href": None, "location": location})
            for child in reversed(node.get("children", []) if isinstance(node.get("children", []), list) else []):
                stack.append((child, ancestors + ((row_id,) if row_id is not None else ()), depth + 1))
    status = "partial" if partial else "complete"
    return units, status, list(dict.fromkeys(notes)), {"structured_requirements": requirements,
        "structured_references": references, "project_id": project_id, "format": "reqview-json/1"}


def _arff_unquote(value: str) -> str:
    value = value.strip()
    if not value or value[0] not in "'\"":
        if any(ch in value for ch in ",\r\n"):
            raise ValueError("Malformed unquoted ARFF value")
        return value
    quote = value[0]
    out, i = [], 1
    while i < len(value):
        char = value[i]
        if char == "\\":
            i += 1
            if i >= len(value):
                raise ValueError("Malformed ARFF escape")
            out.append(value[i])
        elif char == quote:
            if i + 1 < len(value) and value[i + 1] == quote:
                out.append(quote)
                i += 1
            elif value[i + 1:].strip():
                raise ValueError("Trailing data after ARFF value")
            else:
                return "".join(out)
        else:
            out.append(char)
        i += 1
    raise ValueError("Unterminated ARFF quoted value")


def _arff_row(line: str) -> list[str]:
    fields, start, quote, escaped = [], 0, None, False
    spans, i = [], 0
    while i < len(line):
        char = line[i]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                if i + 1 < len(line) and line[i + 1] == quote:
                    i += 1
                else:
                    quote = None
        elif char in "'\"":
            quote = char
        elif char == ",":
            spans.append(line[start:i]); start = i + 1
        i += 1
    if quote or escaped:
        raise ValueError("Unterminated ARFF row value")
    spans.append(line[start:])
    return [_arff_unquote(field) for field in spans]


def read_arff(data: bytes, *, max_records=DEFAULT_RECORDS, max_text=DEFAULT_TEXT):
    """Read a bounded ARFF table with declared statement/class columns."""
    _limits(max_records, max_text)
    if not isinstance(data, bytes) or len(data) > MAX_INPUT_BYTES:
        raise ValueError("ARFF input byte limit exceeded or input is not bytes")
    notes = []
    try:
        source = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        source = data.decode("cp1252")
        notes.append("Decoded using Windows-1252 fallback")
    if "\x00" in source:
        raise ValueError("NUL byte in ARFF input")
    attributes, rows, in_data, header_done = [], [], False, False
    lines = source.splitlines()
    current, current_line = "", 0
    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()
        if not current and (not stripped or stripped.startswith("%")):
            continue
        if not in_data:
            if stripped.casefold() == "@data":
                in_data, header_done = True, True
                continue
            match = re.match(r"(?is)^@attribute\s+(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"|([^\s]+))\s+(.+?)\s*$", stripped)
            if stripped.casefold().startswith("@relation"):
                continue
            if not match:
                raise ValueError(f"Malformed ARFF header at line {line_no}")
            name = next(x for x in match.groups()[:3] if x is not None)
            attr_type = match.group(4).strip()
            attributes.append((name, attr_type))
            continue
        if not current:
            current_line = line_no
        current += ("\n" if current else "") + line
        try:
            parsed = _arff_row(current)
        except ValueError as exc:
            if "Unterminated" in str(exc):
                continue
            raise ValueError(f"Malformed ARFF row beginning at line {current_line}") from exc
        if len(parsed) != len(attributes):
            raise ValueError(f"ARFF row at line {current_line} has {len(parsed)} values; expected {len(attributes)}")
        rows.append((current_line, parsed)); current = ""
    if not header_done:
        raise ValueError("ARFF data section is missing")
    if current:
        raise ValueError(f"Unterminated ARFF row beginning at line {current_line}")
    names = [name.casefold() for name, _ in attributes]
    statement_index = next((i for i, n in enumerate(names) if n in {"requirementtext", "statement", "requirement"}), None)
    if statement_index is None:
        raise ValueError("ARFF has no declared requirement statement attribute")
    id_index = next((i for i, n in enumerate(names) if n in {"id", "requirementid", "reqid"}), None)
    kind_index = next((i for i, n in enumerate(names) if n in {"kind", "type", "class"}), None)
    project_index = next((i for i, n in enumerate(names) if n in {"project", "projectid"}), None)
    enum_values = set(re.findall(r"(?:^|[,\{])\s*([^,\{\}\s]+)\s*(?=,|\})", attributes[kind_index][1])) if kind_index is not None else set()
    known_quality = {"A", "L", "LF", "MN", "O", "PE", "SC", "SE", "US", "FT", "PO"}
    compatible_quality = kind_index is not None and {x.upper() for x in enum_values} == known_quality | {"F"}
    records, units, used, partial = [], [], 0, False
    for row_number, values in rows:
        if len(records) >= max_records:
            partial = True
            notes.append("ARFF record limit reached")
            break
        original_statement = values[statement_index]
        room = max_text - used
        statement = original_statement[:max(0, room)]
        used += len(statement)
        if len(statement) != len(original_statement):
            partial = True
            notes.append("ARFF extracted-text limit reached")
        declared_id = values[id_index] if id_index is not None and values[id_index] != "?" else None
        source_kind = values[kind_index] if kind_index is not None and values[kind_index] != "?" else None
        code = source_kind.upper() if source_kind else ""
        if code in {"F", "FR", "RF"}:
            kind = "functional"
        elif code in {"NF", "NFR", "RNF"}:
            kind = "nonfunctional"
        else:
            kind = "unspecified"
        if compatible_quality and code in known_quality:
            kind = "unspecified"
        project_id = values[project_index] if project_index is not None and values[project_index] != "?" else None
        identity = declared_id or f"arff-row-{row_number}"
        location = {"element": "arff-data-row", "line": row_number, "table_row": len(records) + 1}
        record = {"id": identity, "statement": statement, "kind": kind, "recognition": "explicit-arff/1",
            "location": location, "source_kind": source_kind,
            "identifier_origin": "declared" if declared_id else "generated-row-key",
            "declared_id": declared_id, "project_id": project_id,
            "attributes": {name: value for (name, _), value in zip(attributes, values)}}
        records.append(record)
        units.append({"text": statement, "location": location, "row": len(records), "attributes": record["attributes"]})
    status = "partial" if partial else "complete"
    metadata = {"structured_requirements": records, "structured_references": [], "format": "arff-requirements/1",
                "attributes": [{"name": name, "type": kind} for name, kind in attributes]}
    return units, status, list(dict.fromkeys(notes)), metadata
