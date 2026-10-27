"""Bounded, inert document readers. A failed source cannot erase successful sources."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote
import zipfile
import xml.etree.ElementTree as ET

from ..scanners.filesystem import iter_project_files, DOCUMENT_EXTS, _doc_role
from .document_formats import read_arff, read_reqview
from .requirements import prose_requirement

MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_PAGES = 1000
MAX_CELLS = 250000
MAX_TEXT = 8 * 1024 * 1024
STRUCTURED = {".yaml", ".yml", ".json", ".xml", ".side", ".mpp"}


def xml(data):
    if b"\x00" in data:
        raise ValueError("NUL-encoded XML is not supported")
    # JaCoCo emits this inert external DTD declaration. Remove the exact known
    # dialect without fetching anything; internal subsets/entities remain rejected.
    data = re.sub(br'<!DOCTYPE\s+report\s+PUBLIC\s+"-//JACOCO//DTD Report [\d.]+//EN"\s+"report\.dtd"\s*>', b"", data)
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("XML entities/DOCTYPE are not supported")
    return ET.fromstring(data)


def local(tag):
    return tag.rsplit("}", 1)[-1]


class StaticHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.skip = [], [], 0
        self.signatures, self.pre = [], None
        self.tables, self.table_depth, self.row, self.cell = [], 0, None, None
        self.cell_count = 0
        self.structured_requirements, self.structured_references = [], []
        self.typed_row = None
        self.typed_cell = None
        self.typed_rows_seen = 0
        self.typed_exclusions = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").casefold().split())
        if tag in {"nav", "aside", "pre", "code", "script", "style"} or {"toc", "example", "examples"} & classes:
            self.typed_exclusions.append(tag)
        typed_allowed = not self.typed_exclusions
        if typed_allowed and tag == "tr" and self.table_depth == 1:
            self.typed_row = ({"fields": {}, "line": self.getpos()[0], "table": len(self.tables), "row": self.typed_rows_seen + 1}
                              if attrs.get("data-row-type", "").casefold() == "requirement" else None)
            self.typed_rows_seen += 1
        if typed_allowed and tag in {"td", "th"} and self.table_depth == 1 and self.typed_row is not None:
            field = attrs.get("data-field-name", "").strip().upper()
            self.typed_cell = {"name": field, "parts": [], "anchors": []}
        elif typed_allowed and self.typed_cell is not None and tag == "a":
            role = "parent" if "requirement__link-parent" in classes else "child" if "requirement__link-child" in classes else None
            if role and attrs.get("href"):
                self.typed_cell["anchors"].append((role, attrs["href"], self.getpos()[0]))
        if tag == "table" and not self.skip:
            self.table_depth += 1
            if self.table_depth == 1:
                self.tables.append([])
        if self.table_depth == 1 and not self.skip:
            if tag == "tr":
                self.finish_row(); self.row = []
            elif tag in {"td", "th"}:
                self.finish_cell(); self.cell = []
        if tag == "pre" and not self.skip:
            self.pre = []
        if tag in {"script", "style"}:
            self.skip += 1
        if tag in {"p", "div", "tr", "br", "li", "h1", "h2", "h3", "pre", "dt", "dd"} and not self.table_depth:
            self.parts.append("\n")
        elif self.cell is not None and tag in {"br", "p", "div", "li", "ul", "ol", "td", "tr"}:
            self.cell.append(" ")
        if self.typed_cell is not None and typed_allowed and tag in {"br", "p", "div", "li", "ul", "ol", "td", "tr"}:
            self.typed_cell["parts"].append(" ")
        if tag == "a":
            self.links.extend(v for k, v in attrs.items() if k == "href" and v)

    def handle_endtag(self, tag):
        typed_allowed = not self.typed_exclusions
        if typed_allowed and tag in {"td", "th"} and self.table_depth == 1 and self.typed_cell is not None:
            cell = self.typed_cell
            if cell["name"]:
                self.typed_row["fields"].setdefault(cell["name"], []).append(" ".join("".join(cell["parts"]).split()))
            if cell["name"] == "RELATIONS":
                for role, href, line in cell["anchors"]:
                    target = unquote(href.split("#", 1)[1]).strip() if "#" in href else ""
                    if target:
                        self.typed_row.setdefault("references", []).append({"source": "", "target": target,
                            "native_role": role, "href": href, "location": {"line": line, "element": "typed-requirement-row"}})
            self.typed_cell = None
        if typed_allowed and tag == "tr" and self.table_depth == 1 and self.typed_row is not None:
            fields = self.typed_row["fields"]
            uid = fields.get("UID", [])
            statement = fields.get("STATEMENT", [])
            # Ambiguous identity or statement fields are withheld instead of guessed.
            if len(uid) == 1 and uid[0].strip() and len(statement) <= 1 and len(self.structured_requirements) < MAX_CELLS:
                self.typed_row["id"] = uid[0].strip()
                self.structured_requirements.append({"id": uid[0].strip(), "statement": statement[0] if statement else "",
                    "kind": fields.get("KIND", ["unspecified"])[0] or "unspecified", "title": fields.get("TITLE", [""])[0],
                    "status": fields.get("STATUS", [""])[0], "recognition": "explicit-html/1",
                    "location": {"line": self.typed_row["line"], "element": "typed-requirement-row"},
                    "statement_missing": not bool(statement and statement[0].strip())})
                for reference in self.typed_row.get("references", []):
                    reference["source"] = uid[0].strip()
                    self.structured_references.append(reference)
            self.typed_row = None
        if not self.skip and self.table_depth == 1:
            if tag in {"td", "th"}: self.finish_cell()
            elif tag in {"tr", "table"}: self.finish_row()
        if tag == "table" and not self.skip:
            self.table_depth = max(0, self.table_depth - 1)
        if tag == "pre" and self.pre is not None:
            value = "".join(self.pre).strip()
            if value:
                self.signatures.append(value)
            self.pre = None
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)
        if self.typed_exclusions and self.typed_exclusions[-1] == tag:
            self.typed_exclusions.pop()
        if tag in {"td", "th"} and not self.table_depth:
            self.parts.append(" | ")

    def handle_data(self, data):
        if not self.skip:
            # Code and preformatted examples are not discovery contexts, but
            # their literal text remains part of an explicit STATEMENT field.
            retain_statement_code = (self.typed_cell is not None and self.typed_cell["name"] == "STATEMENT"
                                     and bool(self.typed_exclusions) and all(t in {"code", "pre"} for t in self.typed_exclusions))
            if self.typed_cell is not None and (not self.typed_exclusions or retain_statement_code):
                self.typed_cell["parts"].append(data)
            if self.cell is not None:
                self.cell.append(data)
            elif not self.table_depth:
                self.parts.append(data)
            if self.pre is not None:
                self.pre.append(data)

    def finish_cell(self):
        if self.cell is not None:
            self.cell_count += 1
            if self.cell_count > MAX_CELLS:
                raise ValueError("HTML cell limit exceeded")
            if self.row is None: self.row = []
            self.row.append("".join(self.cell).strip())
            self.cell = None

    def finish_row(self):
        self.finish_cell()
        if self.row is not None and self.tables:
            self.tables[-1].append(self.row)
            self.row = None


class _HeadingRequirements(HTMLParser):
    """Conservative heading/paragraph fallback for exported requirement pages."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.heading = None
        self.block = None
        self.current = None
        self.records, self.references = [], []
        self.paragraph_records = []
        self.excluded = []
        self.excluded_depth = 0
        self.table_depth = 0
        self.section = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table": self.table_depth += 1
        if tag in {"nav", "aside", "pre", "code", "script", "style"} or {"toc", "example", "examples"} & set(attrs.get("class", "").casefold().split()):
            self.excluded.append(tag)
            self.excluded_depth += 1
        if tag in {"script", "style"}: self.skip += 1
        if self.skip or self.excluded_depth: return
        if re.fullmatch(r"h[1-6]", tag):
            self.heading = {"text": [], "line": self.getpos()[0], "id": attrs.get("id", "")}
        elif tag in {"p", "blockquote", "li"}:
            self.block = {"tag": tag, "parts": [], "line": self.getpos()[0], "links": [],
                          "in_table": self.table_depth > 0,
                          "paragraph_candidate": tag == "p" and self.table_depth == 0}
        elif tag == "a" and self.block is not None:
            classes = set(attrs.get("class", "").split())
            role = "parent" if "requirement__link-parent" in classes else "child" if "requirement__link-child" in classes else None
            if attrs.get("href"):
                self.block["links"].append((role, attrs["href"], self.getpos()[0]))

    def handle_data(self, data):
        if self.skip: return
        if self.heading is not None: self.heading["text"].append(data)
        if self.block is not None: self.block["parts"].append(data)

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)
        if self.excluded and self.excluded[-1] == tag:
            self.excluded.pop()
            self.excluded_depth = max(0, self.excluded_depth - 1)
        if tag == "table":
            self.table_depth = max(0, self.table_depth - 1)
        if self.skip or self.excluded_depth: return
        if re.fullmatch(r"h[1-6]", tag) and self.heading is not None:
            self._finish_current()
            title = " ".join("".join(self.heading["text"]).split())
            heading_id = self.heading["id"].strip()
            match = re.fullmatch(r"(?:REQ|FR|NFR)[-_ ]?\d+(?:\.\d+)*", heading_id, re.I)
            if not match:
                match = re.match(r"^((?:REQ|FR|NFR)[-_ ]?\d+(?:\.\d+)*)\b", title, re.I)
                heading_id = match.group(1) if match else ""
            # A trailing visible UID is redundant in the title; keep the authored index and text.
            clean_title = re.sub(r"\s+(?:REQ|FR|NFR)[-_ ]?\d+(?:\.\d+)*\s*$", "", title, flags=re.I) if heading_id else title
            self.current = ({"id": heading_id, "title": clean_title, "line": self.heading["line"], "parts": [], "obligation_seen": False, "statement_closed": False} if heading_id else None)
            self.section = title
            self.heading = None
        if tag in {"p", "blockquote", "li"} and self.block is not None:
            text = " ".join("".join(self.block["parts"]).split())
            if self.block["paragraph_candidate"] and len(self.paragraph_records) < MAX_CELLS:
                match = re.fullmatch(r"\[([A-Za-z0-9][A-Za-z0-9_.:-]*)\]\s*(.+)", text, re.S)
                if match:
                    uid, statement = match.group(1), match.group(2).strip()
                    if prose_requirement(statement, self.section):
                        kind = ("functional" if re.match(r"^RF[-_ ]?\d", uid, re.I) else
                                "nonfunctional" if re.match(r"^RNF[-_ ]?\d", uid, re.I) else
                                "nonfunctional" if re.search(r"\b(?:NFR|non[- ]?functional requirements?)\b", self.section, re.I) else
                                "functional" if re.search(r"\b(?:FR|functional requirements?)\b", self.section, re.I) else
                                "unspecified")
                        self.paragraph_records.append({"id": uid, "statement": statement, "kind": kind,
                            "title": self.section, "status": "", "recognition": "explicit-html-paragraph/1",
                            "location": {"line": self.block["line"], "element": "requirement-paragraph"},
                            "statement_missing": False})
            if self.current is not None and not self.block["in_table"]:
                label = re.match(r"\s*(parent|child)\s+links\s*:\s*", text, re.I)
                links = self.block["links"]
                if label:
                    self.current["statement_closed"] = True
                    role = label.group(1).lower()
                    for _, href, line in links:
                        target = unquote(href.split("#", 1)[1]).strip() if "#" in href else ""
                        if target:
                            self.references.append({"source": self.current["id"], "target": target, "native_role": role,
                                "href": href, "location": {"line": line, "element": "heading-requirement"}})
                    self.block = None
                    return
                if any(role for role, _, _ in self.block["links"]):
                    self.current["statement_closed"] = True
                    for role, href, line in self.block["links"]:
                        target = unquote(href.split("#", 1)[1]).strip() if "#" in href else ""
                        if target:
                            self.references.append({"source": self.current["id"], "target": target, "native_role": role,
                                "href": href, "location": {"line": line, "element": "heading-requirement"}})
                elif re.match(r"\s*(?:references?|riferimenti|links?)\s*:", text, re.I):
                    self.current["statement_closed"] = True
                elif self.current["statement_closed"]:
                    pass
                elif not self.current["obligation_seen"] and re.search(r"\b(?:shall|must|deve|devono|dovrà|dovranno)\b", text, re.I):
                    self.current["obligation_seen"] = True
                    self.current["parts"].append(text)
                elif self.current["obligation_seen"] and text:
                    self.current["parts"].append(text)
            self.block = None

    def finish(self):
        self._finish_current()

    def _finish_current(self):
        if self.current and self.current["parts"] and len(self.records) < MAX_CELLS:
            self.records.append({"id": self.current["id"], "statement": " ".join(self.current["parts"]),
                "kind": "unspecified", "title": self.current["title"], "status": "", "recognition": "explicit-html-heading/1",
                "location": {"line": self.current["line"], "element": "requirement-heading"}, "statement_missing": False})
        self.current = None


def safe_zip(path):
    archive = zipfile.ZipFile(path)
    if sum(i.file_size for i in archive.infolist()) > MAX_TOTAL or len(archive.infolist()) > 20000:
        archive.close()
        raise ValueError("ZIP expansion limit exceeded")
    return archive


def workbook(path, tick):
    """Read all populated cells, preserving formulas and caches without recalculation."""
    units = []
    with safe_zip(path) as z:
        date_styles = set()
        if "xl/styles.xml" in z.namelist():
            style_tree = xml(z.read("xl/styles.xml"))
            formats = {int(n.get("numFmtId")): n.get("formatCode", "") for n in style_tree.iter() if local(n.tag) == "numFmt"}
            xfs = next((n for n in style_tree if local(n.tag) == "cellXfs"), [])
            for i, style in enumerate(xfs):
                fmt = int(style.get("numFmtId", "0"))
                code = re.sub(r'"[^"]*"|\[[^\]]*\]', '', formats.get(fmt, "")).lower()
                if fmt in {14, 15, 16, 17, 22, 27, 30, 36, 45, 46, 47, 50, 57} or "y" in code and "d" in code:
                    date_styles.add(i)
        workbook_tree = xml(z.read("xl/workbook.xml"))
        date1904 = any(local(n.tag) == "workbookPr" and n.get("date1904") in {"1", "true"} for n in workbook_tree)
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            strings = ["".join(n.itertext()) for n in xml(z.read("xl/sharedStrings.xml"))]
        rels = {n.attrib["Id"]: n.attrib["Target"] for n in xml(z.read("xl/_rels/workbook.xml.rels"))}
        count = 0
        for sheet in workbook_tree.iter():
            if local(sheet.tag) != "sheet":
                continue
            tick()
            rid = next(v for k, v in sheet.attrib.items() if local(k) == "id")
            target = rels[rid].replace("\\", "/")
            target = target.lstrip("/") if target.startswith("/") else "xl/" + target
            if ".." in Path(target).parts:
                raise ValueError("Workbook relationship outside archive scope")
            for row in xml(z.read(target)).iter():
                if local(row.tag) != "row":
                    continue
                cells = []
                for cell in row:
                    if local(cell.tag) != "c":
                        continue
                    values = {local(n.tag): "".join(n.itertext()) for n in cell}
                    value = values.get("v", values.get("is", ""))
                    if cell.get("t") == "s" and value:
                        value = strings[int(value)]
                    if not value and "f" not in values:
                        continue
                    raw_value = value
                    if int(cell.get("s", "0")) in date_styles and value and cell.get("t") not in {"s", "inlineStr", "str"}:
                        try:
                            value = (datetime(1904, 1, 1) if date1904 else datetime(1899, 12, 30)) + timedelta(days=float(value))
                            value = value.isoformat()
                        except (ValueError, OverflowError):
                            value = raw_value
                    count += 1
                    if count > MAX_CELLS:
                        return units, "partial", ["populated-cell-limit"]
                    cells.append({"cell": cell.get("r"), "value": value,
                                  "raw_value": raw_value, "formula": values.get("f"), "cached_value": value if "f" in values else None})
                if cells:
                    units.append({"sheet": sheet.get("name"), "row": int(row.get("r", "0")),
                                  "cells": cells, "text": " | ".join(c["value"] for c in cells)})
    cells_by_sheet = {(u["sheet"], c["cell"]): c for u in units for c in u["cells"]}
    for unit in units:
        for cell in unit["cells"]:
            if not cell.get("formula"):
                continue
            # Resolve only literal internal references, never evaluate arbitrary formulas.
            formula = re.sub(r'"(?:[^"]|"")*"', '""', cell["formula"])
            refs = []
            for match in re.finditer(r"(?:(?:'([^']+)'|([A-Za-z_][\w ]*))!)?(\$?[A-Z]{1,3}\$?\d+)\b", formula):
                sheet = match[1] or match[2] or unit["sheet"]
                coordinate = match[3].replace("$", "")
                target = cells_by_sheet.get((sheet, coordinate))
                refs.append({"sheet": sheet, "cell": coordinate, "resolved": target is not None,
                             "cached_or_literal_value": target.get("value") if target else None})
            cell["internal_references"] = refs
            cell["evaluation"] = "not evaluated; ranges, external links and computed references may remain unresolved"
    return units, "complete", []


def spreadsheet_results(units):
    headers = {}
    for unit in units:
        sheet = unit["sheet"]
        cells = unit.get("cells", [])
        row = {re.sub(r"\d", "", c["cell"]): c["value"] for c in cells}
        if any(re.fullmatch(r"(?:test case id|test id|id test)", str(v).strip(), re.I) for v in row.values()):
            headers[sheet] = row
            continue
        header = headers.get(sheet, {})
        id_col = next((k for k, v in header.items() if re.fullmatch(r"(?:test case id|test id|id test)", str(v).strip(), re.I)), None)
        result_col = next((k for k, v in header.items() if re.fullmatch(r"(?:esito|status|result|outcome)", str(v).strip(), re.I)), None)
        date_col = next((k for k, v in header.items() if re.fullmatch(r"(?:data|date|timestamp)", str(v).strip(), re.I)), None)
        if not id_col or not result_col or not row.get(id_col) or not row.get(result_col):
            continue
        value = str(row[result_col]).strip().casefold()
        states = {"passed": "passed", "pass": "passed", "not passed": "failure", "failed": "failure", "fail": "failure", "skipped": "skipped"}
        if value not in states:
            continue
        unit["test_result"] = {"name": row[id_col], "status": states[value], "status_declared": row[result_col],
                               "timestamp": row.get(date_col), "scope": sheet, "revision": None, "environment": None}


def read_input(path, tick):
    ext = path.suffix.lower()
    if ext == ".reqw":
        return read_reqview(path.read_bytes())
    if ext == ".arff":
        return read_arff(path.read_bytes())
    if ext == ".pdf":
        try:
            import pdfplumber
        except ImportError:
            return [], "unsupported", ["Install ases[documents] to read textual PDFs"], {}
        units, notes = [], []
        with pdfplumber.open(path) as pdf:
            total = len(pdf.pages)
            for index, page in enumerate(pdf.pages[:MAX_PAGES]):
                tick()
                try:
                    text = page.extract_text() or ""
                except Exception as exc:
                    text = ""
                    notes.append(f"page-{index + 1}: text reader failed ({type(exc).__name__}); other pages retained")
                try:
                    tables = page.extract_tables()
                except Exception as exc:
                    tables = []
                    notes.append(f"page-{index + 1}: table reader failed ({type(exc).__name__}); text retained")
                units.append({"page": index + 1, "text": text, "tables": tables})
                if not text.strip():
                    notes.append(f"page-{index + 1}: no textual layer; OCR/diagram interpretation unavailable")
                if sum(len(u["text"]) for u in units) > MAX_TEXT:
                    notes.append("extracted-text-limit")
                    break
                page.close()
        if total > len(units):
            notes.append(f"read-{len(units)}-of-{total}-pages")
        return units, "partial" if notes else "complete", notes, {"pages_total": total}
    if ext == ".xlsx":
        units, status, notes = workbook(path, tick)
        spreadsheet_results(units)
        return units, status, notes, {}
    if ext == ".docx":
        units = []
        with safe_zip(path) as z:
            body = xml(z.read("word/document.xml"))
            for i, node in enumerate(n for n in body.iter() if local(n.tag) == "p"):
                text = "".join(n.text or "" for n in node.iter() if local(n.tag) == "t")
                if text:
                    units.append({"paragraph": i + 1, "text": text})
        return units, "complete", ["Text and table paragraphs; drawing/layout semantics not interpreted"], {}
    if ext in {".html", ".htm"}:
        parser = StaticHTML()
        html = path.read_text(encoding="utf-8", errors="replace")
        parser.feed(html)
        parser.finish_row()
        units = line_units("".join(parser.parts))
        units += [{"element": f"table[{i}]", "table_index": i, "tables": [table],
                   "text": "\n".join(" | ".join(row) for row in table)} for i, table in enumerate(parser.tables, 1)]
        metadata = {"references": parser.links[:5000], "api_signatures": parser.signatures[:5000]}
        if parser.structured_requirements:
            metadata["structured_requirements"] = parser.structured_requirements[:MAX_CELLS]
        if parser.structured_references:
            metadata["structured_references"] = parser.structured_references[:MAX_CELLS]
        heading_parser = _HeadingRequirements()
        heading_parser.feed(html)
        heading_parser.finish()
        known = {r["id"] for r in metadata.get("structured_requirements", [])}
        heading_records = []
        for record in heading_parser.paragraph_records + heading_parser.records:
            if record["id"] not in known:
                heading_records.append(record)
                known.add(record["id"])
        if heading_records:
            metadata.setdefault("structured_requirements", []).extend(heading_records[:MAX_CELLS])
        if heading_parser.references:
            metadata.setdefault("structured_references", []).extend(heading_parser.references[:MAX_CELLS])
        return units, "complete", ["Static HTML tables retain cells; nested table layout and CSS semantics remain partial"], metadata
    if ext == ".xml":
        tree = xml(path.read_bytes())
        root = local(tree.tag)
        units = []
        if root in {"testsuites", "testsuite"}:
            for i, case in enumerate(n for n in tree.iter() if local(n.tag) == "testcase"):
                units.append({"element": f"testcase[{i + 1}]", "text": case.get("name", ""),
                              "test_result": {**case.attrib, "status": next((local(n.tag) for n in case if local(n.tag) in {"failure", "error", "skipped"}), "passed"),
                                              "timestamp": tree.get("timestamp"), "scope": tree.get("name"), "revision": None}})
        elif root == "report":
            counters = [dict(n.attrib) for n in tree if local(n.tag) == "counter"]
            sessions = [dict(n.attrib) for n in tree if local(n.tag) == "sessioninfo"]
            units = [{"element": "report", "text": "JaCoCo imported coverage", "counters": counters, "sessions": sessions}]
        else:
            return [], "unsupported", ["XML dialect unsupported (JUnit/JaCoCo only)"], {}
        return units, "complete", ["Imported report; target tests were not executed by ASES"], {}
    if ext == ".side":
        data = json.loads(path.read_text(encoding="utf-8"))
        return [{"element": f"tests[{i}]", "text": test.get("name", ""), "definition": test} for i, test in enumerate(data.get("tests", []))], "complete", ["Selenium definitions, not executions"], {}
    if ext in {".md", ".txt", ".rst", ".adoc", ".yaml", ".yml", ".json", ".puml", ".mmd", ".plantuml", ".drawio", ".wsd"}:
        text = path.read_text(encoding="utf-8", errors="replace")
        metadata = {}
        if ext in {".json", ".yaml", ".yml"}:
            import yaml
            data = json.loads(text) if ext == ".json" else yaml.safe_load(text)
            if isinstance(data, dict) and isinstance(data.get("requirements"), list):
                metadata["structured_requirements"] = data["requirements"]
            else:
                return [], "unsupported", ["Structured data has no supported requirements list; not interpreted as prose or test results. Original retained in the source repository."], {}
        return line_units(text[:MAX_TEXT]), "partial" if len(text) > MAX_TEXT else "complete", [], metadata
    return [], "unsupported", [f"No reader for {ext}; original preserved in source repository"], {}


def line_units(text):
    return [{"line": i + 1, "text": line} for i, line in enumerate(text.splitlines()) if line.strip()]


def extract_sources(root: Path, inventory, progress=None):
    docs = {d["path"] for d in inventory.get("documentation_artifacts", [])}
    # Add declared structured docs and report dialects, without interpreting arbitrary config as requirements.
    for path in iter_project_files(root):
        rel = path.relative_to(root).as_posix()
        ext = path.suffix.lower()
        doc_tree = any("doc" in part.casefold() for part in path.relative_to(root).parts[:-1])
        if ext in {".pdf", ".xlsx", ".docx", ".reqw", ".arff"} or ext in {".html", ".htm"} and doc_tree:
            docs.add(rel)
        if path.suffix.lower() in STRUCTURED and (path.suffix.lower() in {".side", ".mpp", ".xml"} or any(t in rel.lower() for t in ("doc", "requirement", "spec", "traceab", "tracciab"))):
            docs.add(rel)
    sources, total = [], 0
    def tick():
        if progress:
            progress("document-inputs")
    for rel in sorted(docs):
        tick()
        path = root / rel
        source = {"id": "doc:" + sha256(rel.encode()).hexdigest()[:20], "path": rel, "format": path.suffix.lower().lstrip("."),
                  "role": _doc_role(rel), "sha256": "", "extraction": "failed", "interpretation": "not-run", "units": [], "limitations": []}
        try:
            size = path.stat().st_size
            source["bytes"] = size
            if size > MAX_FILE or total + size > MAX_TOTAL:
                source.update(extraction="partial", limitations=["document-byte-limit; content not read"])
            else:
                total += size
                source["sha256"] = sha256(path.read_bytes()).hexdigest()
                units, status, notes, metadata = read_input(path, tick)
                if sha256(path.read_bytes()).hexdigest() != source["sha256"]:
                    raise ValueError("Source changed during document extraction")
                source.update(units=units, extraction=status, limitations=notes, metadata=metadata)
                source["interpretation"] = "partial" if units else "not-run"
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            # Avoid reader exception text exposing passwords, absolute paths or embedded document data.
            cause, password_error = exc, False
            for _ in range(5):
                password_error |= "Password" in type(cause).__name__
                cause = cause.__cause__ or cause.__context__
                if cause is None:
                    break
            source["limitations"] = (["Encrypted PDF requires a password; not read"] if password_error else [f"Reader failed: {type(exc).__name__}"])
        sources.append(source)
    counts = Counter(s["extraction"] for s in sources)
    return sources, {"sources": len(sources), "extraction": dict(counts), "bytes_read": total,
                     "pages_read": sum("page" in u for s in sources for u in s["units"]),
                     "cells_read": sum(len(u.get("cells", [])) for s in sources for u in s["units"]),
                     "interpretation": "partial; text, explicit IDs and supported records only; no OCR"}
