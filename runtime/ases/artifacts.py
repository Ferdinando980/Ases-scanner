"""Offline artifact inventory and reconciliation of supplied observations. No execution or acquisition."""
from __future__ import annotations

from hashlib import sha256
from datetime import datetime
import json
import os
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit

from .evidence import digest, validate_context
from .scanners.javascript import EXTENSIONS, MAX_BYTES, parse, walk, field, text, literal, tokens, parser_profile, safe_endpoint, api_calls, args

ARTIFACT_SCHEMA = "ases-artifact-snapshot/1.0"
RUNTIME_SCHEMA = "ases-runtime-observations/1.0"
MAX_TOTAL = 64 * 1024 * 1024
MAX_FILES = 2000
HEX = re.compile(r"[0-9a-f]{64}")


def _seal(document):
    document["snapshot_id"] = "artifact:" + digest({k: v for k, v in document.items() if k != "snapshot_id"})
    return document


def _json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_TOTAL:
        raise ValueError("JSON input must be a bounded regular file")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Malformed JSON input") from exc
    if not isinstance(result, dict):
        raise ValueError("JSON input must be an object")
    return result


def inspect_artifact(path: Path) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.exists():
        raise ValueError("Artifact input must be an existing regular file or directory")
    path = path.absolute().resolve()
    root = path if path.is_dir() else path.parent
    files, unknowns, source_maps, total = [], [], [], 0
    candidates = []
    if path.is_file():
        candidates = [path]
    else:
        for directory, directories, names in os.walk(path, followlinks=False):
            directories[:] = sorted(d for d in directories if not (Path(directory) / d).is_symlink()
                                     and not (os.name == "nt" and (Path(directory) / d).lstat().st_file_attributes & 1024)
                                     and not d.endswith(".ases") and d not in {".git", ".venv", "__pycache__"})
            candidates.extend(Path(directory) / name for name in sorted(names))
            if len(candidates) > MAX_FILES:
                unknowns.append({"reason": "inventory_file_limit", "omitted_count": None})
                candidates = candidates[:MAX_FILES]
                break
    for file in candidates:
        rel = file.relative_to(root).as_posix()
        if file.is_symlink() or not file.resolve().is_relative_to(root) or not file.is_file():
            unknowns.append({"path": rel, "reason": "unsafe_or_unavailable_file"})
            continue
        size = file.stat().st_size
        if size > MAX_BYTES or total + size > MAX_TOTAL:
            unknowns.append({"path": rel, "reason": "artifact_byte_limit", "omitted_count": None})
            continue
        data = file.read_bytes()
        total += len(data)
        row = {"path": rel, "sha256": sha256(data).hexdigest(), "bytes": len(data),
               "source_role": "BUILD_ARTIFACT", "syntax_status": "NOT_APPLICABLE", "functions": [], "imports": [], "literal_requests": []}
        if file.suffix in EXTENSIONS:
            try:
                tree = parse(data.decode("utf-8"), file.suffix)
                row["syntax_status"] = "PARTIAL" if tree.has_error else "ANALYZED"
                for node in walk(tree):
                    if node.type in {"function_declaration", "function_expression", "arrow_function", "method_definition"}:
                        row["functions"].append({"name": text(field(node, "name")) or None,
                                                 "structure_fingerprint": digest(tokens(node)),
                                                 "line": node.start_point.row + 1})
                    if node.type == "import_statement" and literal(field(node, "source")) is not None:
                        row["imports"].append(literal(field(node, "source")))
                    if node.type == "call_expression" and text(field(node, "function")) == "require" and args(node) and literal(args(node)[0]) is not None:
                        row["imports"].append(literal(args(node)[0]))
                row["imports"] = sorted(set(row["imports"]))
                row["literal_requests"] = [{"method": method, "endpoint": target, "line": node.start_point.row + 1,
                                            "basis": "literal-request-syntax", "state": "INFERRED"}
                                           for node, method, target in api_calls(data.decode("utf-8"), file.suffix)]
                if tree.has_error:
                    unknowns.append({"path": rel, "reason": "parser_recovery"})
            except (UnicodeError, ValueError) as exc:
                row["syntax_status"] = "UNKNOWN"
                unknowns.append({"path": rel, "reason": str(exc)})
        elif file.name == "package.json":
            try:
                manifest = json.loads(data.decode("utf-8"))
                if not isinstance(manifest, dict):
                    raise ValueError("malformed_package_manifest")
                row["manifest"] = {key: manifest[key] for key in ("name", "version", "type", "main")
                                   if isinstance(manifest.get(key), str)}
                row["syntax_status"] = "ANALYZED"
            except (ValueError, UnicodeError, RecursionError) as exc:
                row["syntax_status"] = "UNKNOWN"
                unknowns.append({"path": rel, "reason": str(exc)})
        elif file.suffix == ".map":
            try:
                source_map = json.loads(data.decode("utf-8"))
                if not isinstance(source_map, dict) or source_map.get("version") != 3 or not isinstance(source_map.get("sources"), list):
                    raise ValueError("unsupported_source_map")
                contents = source_map.get("sourcesContent", [])
                if not isinstance(contents, list) or any(not isinstance(x, str) for x in source_map["sources"]):
                    raise ValueError("malformed_source_map")
                if not isinstance(source_map.get("sourceRoot", ""), str) or source_map.get("file") is not None and not isinstance(source_map["file"], str):
                    raise ValueError("malformed_source_map_location")
                for index, source in enumerate(source_map["sources"]):
                    content = contents[index] if index < len(contents) else None
                    if content is not None and not isinstance(content, str):
                        raise ValueError("malformed_source_content")
                    source_maps.append({"map_path": rel, "source_index": index, "map_sha256": row["sha256"], "original_name": source,
                                        "source_root": source_map.get("sourceRoot", ""),
                                        "content_sha256": sha256(content.encode("utf-8")).hexdigest() if content is not None else None,
                                        "declared_file": source_map.get("file"), "authority": "source-map-assertion"})
                row["syntax_status"] = "ANALYZED"
            except (ValueError, UnicodeError, RecursionError) as exc:
                row["syntax_status"] = "UNKNOWN"
                unknowns.append({"path": rel, "reason": str(exc)})
        files.append(row)
    return _seal({"schema": ARTIFACT_SCHEMA, "files": sorted(files, key=lambda x: x["path"]),
                  "source_maps": source_maps, "unknowns": unknowns,
                  "coverage": {"status": "PARTIAL" if unknowns else "ANALYZED", "bytes_read": total,
                               "omitted_count": None if unknowns else 0,
                               "limits": {"files": MAX_FILES, "file_bytes": MAX_BYTES, "total_bytes": MAX_TOTAL}},
                  "analysis_profile": parser_profile(), "untrusted_content": True,
                  "limitations": ["Supplied artifacts only; no build, target execution, source-map fetching or runtime capture.",
                                  "Function fingerprints and source maps do not establish behavioral equivalence."]})


def load_artifact(path):
    artifact = _json(path)
    validate_artifact(artifact)
    return artifact


def validate_artifact(artifact):
    if artifact.get("schema") != ARTIFACT_SCHEMA or not isinstance(artifact.get("files"), list):
        raise ValueError("Unsupported artifact snapshot")
    expected = "artifact:" + digest({k: v for k, v in artifact.items() if k != "snapshot_id"})
    if artifact.get("snapshot_id") != expected:
        raise ValueError("Artifact snapshot digest mismatch")
    seen = set()
    for row in artifact["files"]:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str) or not isinstance(row.get("sha256"), str) or not HEX.fullmatch(row["sha256"]):
            raise ValueError("Malformed artifact file record")
        name = PurePosixPath(row["path"])
        if name.is_absolute() or ".." in name.parts or "\\" in row["path"] or row["path"] in seen:
            raise ValueError("Unsafe or duplicate artifact path")
        seen.add(row["path"])
        if type(row.get("bytes")) is not int or row["bytes"] < 0 or row.get("source_role") != "BUILD_ARTIFACT" or row.get("syntax_status") not in {"ANALYZED", "PARTIAL", "UNKNOWN", "NOT_APPLICABLE"}:
            raise ValueError("Malformed artifact file authority/size")
    if not isinstance(artifact.get("source_maps"), list) or not isinstance(artifact.get("unknowns"), list) or not isinstance(artifact.get("coverage"), dict):
        raise ValueError("Malformed artifact coverage/maps")
    for row in artifact["source_maps"]:
        if not isinstance(row, dict) or not isinstance(row.get("map_path"), str) or row["map_path"] not in seen or not isinstance(row.get("original_name"), str) or type(row.get("source_index")) is not int or row["source_index"] < 0:
            raise ValueError("Malformed source map record")
        for key in ("content_sha256", "map_sha256"):
            value = row.get(key)
            if value is not None and (not isinstance(value, str) or not HEX.fullmatch(value)):
                raise ValueError("Malformed source map digest")


def load_runtime(path):
    runtime = _json(path)
    validate_runtime(runtime)
    return runtime


def validate_runtime(runtime):
    if runtime.get("schema") != RUNTIME_SCHEMA:
        raise ValueError("Unsupported runtime observation schema")
    if not isinstance(runtime.get("collector"), dict) or not isinstance(runtime["collector"].get("name"), str) or not runtime["collector"]["name"] or not isinstance(runtime.get("environment"), dict):
        raise ValueError("Runtime collector and environment provenance required")
    if not isinstance(runtime.get("captured_at"), str) or not isinstance(runtime.get("coverage"), dict):
        raise ValueError("Runtime capture scope/time required")
    try:
        if datetime.fromisoformat(runtime["captured_at"].replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("Runtime capture time requires a timezone")
    except ValueError as exc:
        raise ValueError("Invalid runtime capture time") from exc
    if runtime["coverage"].get("status") not in {"ANALYZED", "PARTIAL", "UNKNOWN"} or not isinstance(runtime.get("scripts"), list):
        raise ValueError("Malformed runtime coverage/scripts")
    for script in runtime["scripts"]:
        if not isinstance(script, dict) or not isinstance(script.get("location"), str) or not isinstance(script.get("loaded"), bool):
            raise ValueError("Malformed runtime script")
        if script.get("sha256") is not None and (not isinstance(script["sha256"], str) or not HEX.fullmatch(script["sha256"])):
            raise ValueError("Invalid runtime script digest")


def reconcile_artifact(source, artifact, runtime=None, mappings=None):
    validate_context(source)
    validate_artifact(artifact)
    files = artifact["files"]
    matches = []
    for original in source.get("source_manifest", []):
        exact = [row["path"] for row in files if row["sha256"] == original["sha256"]]
        mapped = [row for row in artifact["source_maps"] if row["content_sha256"] == original["sha256"]]
        candidates = exact if exact else sorted(f"{row['map_path']}#{row['source_index']}:{row['original_name']}" for row in mapped)
        contradictions = [row["map_path"] for row in artifact["source_maps"] if row["original_name"] == original["path"]
                          and row["content_sha256"] is not None and row["content_sha256"] != original["sha256"]]
        matches.append({"source_path": original["path"], "source_sha256": original["sha256"], "candidates": candidates,
                        "status": "matched" if len(candidates) == 1 else "ambiguous" if candidates else "mismatch" if contradictions else "unknown",
                        "basis": "exact-bytes" if exact else "source-map-content" if mapped else "no-correspondence",
                        "state": "INFERRED", "source_map_contradictions": contradictions})
    runtime_matches = []
    mappings = mappings or []
    if runtime is not None:
        validate_runtime(runtime)
        for script in runtime["scripts"]:
            path_candidates = []
            for mapping in mappings:
                if not isinstance(mapping, dict):
                    raise ValueError("Invalid runtime mapping")
                prefix, target = mapping.get("runtime_prefix"), mapping.get("artifact_prefix", "")
                if not isinstance(prefix, str) or not isinstance(target, str):
                    raise ValueError("Invalid runtime mapping")
                loc = script["location"]
                if not loc.startswith(prefix):
                    continue
                a, b = urlsplit(prefix), urlsplit(loc)
                if a.scheme and (a.scheme, a.netloc) != (b.scheme, b.netloc):
                    continue
                remainder = loc[len(prefix):].split("?", 1)[0].split("#", 1)[0]
                candidate = str(PurePosixPath(target) / remainder)
                path_candidates.extend(row for row in files if row["path"] == candidate)
            exact = [row for row in files if script.get("sha256") and row["sha256"] == script["sha256"]]
            mismatch = bool(path_candidates and script.get("sha256") and any(row["sha256"] != script["sha256"] for row in path_candidates))
            candidates = exact if exact else path_candidates if not script.get("sha256") else []
            qualified = sorted({row["path"] for row in candidates})
            status = "mismatch" if mismatch else "ambiguous" if len(qualified) > 1 else "matched" if qualified else "unknown"
            runtime_matches.append({"location": safe_endpoint(script["location"]), "status": status, "candidates": qualified,
                                    "load_state": "loaded" if status == "matched" and script["loaded"] else "unknown",
                                    "basis": "captured-digest" if exact else "declared-location-mapping" if qualified else "no-correspondence",
                                    "state": "INFERRED"})
    return {"schema": "ases-artifact-reconciliation/1.0", "source_snapshot_id": source["snapshot_id"],
            "artifact_snapshot_id": artifact["snapshot_id"], "source_matches": matches, "runtime_matches": runtime_matches,
            "runtime_provenance": {k: runtime[k] for k in ("collector", "environment", "captured_at", "coverage")} if runtime else None,
            "coverage": {"artifact": artifact["coverage"], "runtime": runtime["coverage"] if runtime else {"status": "NOT_OBSERVED"}},
            "limitations": ["Imported collector assertions are not independently authenticated.",
                            "Loaded script, resident module, executed feature and deployment truth remain distinct.",
                            "Absence from a partial capture is not proof of global absence."], "untrusted_content": True}


def write_artifact(path, out):
    out = Path(out)
    if out.is_symlink() or Path(path).absolute().resolve().is_relative_to(out.absolute().resolve()):
        raise ValueError("Artifact output cannot replace the supplied input or follow a symlink")
    document = inspect_artifact(path)
    from .pipeline import prepare_output
    out = prepare_output(out, clear=False)
    (out / ".ases-output").write_text("ASES artifact snapshot; no target execution.\n", encoding="utf-8")
    (out / "artifact-snapshot.json").write_text(json.dumps(document, indent=2), encoding="utf-8")
    return document
