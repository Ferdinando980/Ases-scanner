"""Saved-model regeneration and non-destructive, optimistic user reviews."""
from __future__ import annotations

import json
from pathlib import Path
import re

from . import SCHEMA
from .model import digest
from .render import render_documents

REVIEW_SCHEMA = "ases-engineering-review/1.1"
LEGACY_REVIEW_SCHEMA = "ases-engineering-review/1.0"
MAX_MODEL_BYTES = 256 * 1024 * 1024


def read_json(path, limit=MAX_MODEL_BYTES):
    with Path(path).open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Engineering input exceeds reader limit")
    return json.loads(data)


def load_model(snapshot):
    snapshot = Path(snapshot)
    model = read_json(snapshot / "engineering-model.json" if snapshot.is_dir() else snapshot)
    if not isinstance(model, dict) or model.get("schema") != SCHEMA:
        raise ValueError("Unsupported engineering model; scan again to recover documents")
    for key in ("sources", "requirements", "api", "links", "issues", "recovered_requirements", "scenarios", "test_cases", "test_results", "diagrams", "operations", "user_requirements"):
        if key not in model and key not in {"sources", "requirements", "api", "links", "issues"}:
            continue
        if not isinstance(model.get(key), list) or not all(isinstance(r, dict) for r in model[key]):
            raise ValueError("Invalid engineering collection: " + key)
    if not isinstance(model.get("coverage"), dict) or not isinstance(model.get("model_digest"), str):
        raise ValueError("Invalid engineering identity or coverage")
    expected = model["model_digest"]
    if digest({k: v for k, v in model.items() if k != "model_digest"}) != expected:
        raise ValueError("Engineering model digest mismatch")
    return model


def load_reviewed_model(snapshot):
    snapshot = Path(snapshot)
    review = (snapshot if snapshot.is_dir() else snapshot.parent) / "engineering-review.json"
    return apply_review(load_model(snapshot), read_json(review, 1024 * 1024) if review.is_file() else None)


def apply_review(model, review):
    result = dict(model)
    if not review:
        return result
    if not isinstance(review, dict) or review.get("schema") not in {REVIEW_SCHEMA, LEGACY_REVIEW_SCHEMA} or not isinstance(review.get("operations"), list) or len(review["operations"]) > 1000:
        raise ValueError("Invalid review schema or operations")
    if review["schema"] == REVIEW_SCHEMA and (not isinstance(review.get("base_model_digest"),str) or not review["base_model_digest"]):
        raise ValueError("Authoring review needs the base model digest")
    # Source extraction is immutable. Copy only records receiving review overlays,
    # rather than cloning every page/cell on every desk request.
    collections = ("requirements", "recovered_requirements", "api", "scenarios", "test_cases", "operations", "user_requirements")
    for key in collections:
        result[key] = [dict(row) for row in model.get(key, [])]
    result["links"] = list(model.get("links", []))
    records = {r["id"]: r for key in collections for r in result.get(key, [])}
    declared_ids = {r.get("declared_id", r["id"]) for r in result["requirements"] + result["user_requirements"]}
    conflicts, applied = [], []
    seen = set()
    for op in review["operations"]:
        if not isinstance(op, dict) or not isinstance(op.get("record_id"), str):
            raise ValueError("Review operations need a record ID")
        action = op.get("action")
        if not isinstance(action, str):
            raise ValueError("Review action must be a string")
        if "base_model_digest" in op and (not isinstance(op["base_model_digest"],str) or not op["base_model_digest"]):
            raise ValueError("Operation base model digest must be a nonempty string")
        legacy = action in {"annotate", "confirm", "reject"}
        if not legacy and (review["schema"] != REVIEW_SCHEMA or action not in {"set-operation-context", "add-requirement", "adopt-requirement"}):
            raise ValueError("Unknown review action or review schema too old for authoring")
        note = op.get("note", "" if not legacy else None)
        if not isinstance(note, str) or len(note) > 10000:
            raise ValueError("Review needs a bounded note")
        token = ("annotation" if legacy else action, op["record_id"])
        if token in seen:
            raise ValueError("Duplicate review operation")
        seen.add(token)
        if action in {"add-requirement", "adopt-requirement"}:
            requirement, source = _authored_requirement(op, review, records)
            if requirement["id"] in records or requirement["declared_id"] in declared_ids:
                raise ValueError("Requirement ID already exists; preserve the original declaration")
            declared_ids.add(requirement["declared_id"])
            result["user_requirements"].append(requirement)
            records[requirement["id"]] = requirement
            if action == "adopt-requirement":
                valid = requirement["support_state"] == "current-candidate"
                if not valid:
                    conflicts.append({"operation":op, "reason":"Adopted requirement retained; supporting candidate absent or changed"})
                result["links"].append({"id":"user-link:"+digest(op)[:24],"source":requirement["id"],"target":op["source_record_id"],
                                        "target_collection":"operations" if op["source_record_id"].startswith("operation:") else "recovered_requirements",
                                        "relation":"adopted-from-candidate","resolved":valid,"authority":"user-confirmation",
                                        "status":"User-adopted need; satisfaction not verified" if valid else "Supporting candidate needs review; requirement retained",
                                        "locations":requirement["locations"]})
            applied.append(requirement["id"])
            continue
        if action == "set-operation-context":
            context = op.get("context")
            allowed = {"title":200,"purpose":4000,"actor":1000,"acceptance":4000}
            if not isinstance(context, dict) or any(k not in allowed or not isinstance(v,str) or len(v)>allowed[k] or '\x00' in v for k,v in context.items()):
                raise ValueError("Operation context supports bounded title, purpose, actor and acceptance text")
        row = records.get(op.get("record_id"))
        if not row or not op.get("expected_digest") or row.get("record_digest") != op["expected_digest"] or (action=="set-operation-context" and row.get("kind")!="recovered-operation"):
            conflicts.append({"operation": op, "reason": "record absent or changed; review retained, not silently applied"})
            continue
        if action == "set-operation-context":
            row["user_context"] = {**context,"authority":"user-confirmation","meaning":"User-provided context; implementation and satisfaction unverified"}
        else:
            row["review"] = {"action": action, "note": note, "authority": "user-confirmation"}
        applied.append(row["id"])
    result["review_state"] = {"base_model_digest": review.get("base_model_digest"), "base_matches": review.get("base_model_digest") == model["model_digest"],
                              "review_digest": digest(review), "applied": applied, "conflicts": conflicts}
    return result


def _authored_requirement(op, review, records):
    identifier, data = op["record_id"], op.get("requirement")
    if not re.fullmatch(r"user-requirement:[A-Za-z0-9._:-]{1,120}", identifier) or not isinstance(data, dict):
        raise ValueError("User requirement needs a namespaced ID and explicit fields")
    limits = {"declared_id":80,"statement":8000,"author":200,"scope":1000,"acceptance":4000}
    for key, limit in limits.items():
        if not isinstance(data.get(key),str) or not data[key].strip() or len(data[key])>limit or '\x00' in data[key]:
            raise ValueError("User requirement needs bounded nonempty " + key)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}",data["declared_id"]):
        raise ValueError("Requirement ID uses letters, digits, dots, underscores, colons or hyphens")
    if data.get("kind") not in {"functional","nonfunctional"}:
        raise ValueError("Choose a functional or nonfunctional requirement")
    source = None
    if op["action"] == "adopt-requirement":
        if not isinstance(op.get("source_record_id"),str) or not isinstance(op.get("expected_source_digest"),str) or not op["expected_source_digest"]:
            raise ValueError("Adoption needs an explicit candidate and expected digest")
        if not op["source_record_id"].startswith(("operation:","recovered-requirement:")):
            raise ValueError("Adoption needs a recovered operation or behavior ID")
        source = records.get(op["source_record_id"])
        if source and source.get("kind") not in {"recovered-operation","reconstructed-functional-requirement"}:
            raise ValueError("Only recovered operations/behaviors can be adopted as new requirements")
    valid = source is not None and source.get("record_digest") == op.get("expected_source_digest")
    result = {"id":identifier,"declared_id":data["declared_id"].strip(),"kind":data["kind"],"statement":data["statement"].strip(),
              "author":data["author"].strip(),"scope":data["scope"].strip(),"acceptance":data["acceptance"].strip(),
              "authority":"user-confirmation","satisfaction":"not-verified",
              "origin":{"action":op["action"],"base_model_digest":op.get("base_model_digest",review.get("base_model_digest")),
                        "source_record_id":op.get("source_record_id"),"expected_source_digest":op.get("expected_source_digest")},
              "support_state":"current-candidate" if valid else "needs-review" if op["action"]=="adopt-requirement" else "user-authored",
              "locations":source.get("locations",[]) if valid else []}
    result["record_digest"]=digest(result)
    return result, source


def write_documents(model, directory, language="it", review=None, *, signature="", legacy=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    rendered = render_documents(apply_review(model, review), language)
    marker = directory / "engineering-documents.json"
    if marker.is_file():
        previous = read_json(marker, 1024 * 1024)
        for name, expected in previous.get("files", {}).items():
            path = directory / name
            if not path.resolve().is_relative_to(directory.resolve()) or path.is_symlink() or not path.is_file() or digest(path.read_text(encoding="utf-8")) != expected:
                raise ValueError("Generated documents were edited; preserve them and use a new document package")
    for name, text in rendered.items():
        if legacy and name in legacy:
            text += "\n\n---\n\n## Additional code-only baseline\n\nThis view describes code recovery only; it does not override the documented declarations above.\n\n" + legacy[name]
        (directory / name).write_text(signature + text, encoding="utf-8")
    marker.write_text(json.dumps({"schema": "ases-generated-documents/1.0", "files": {
        name: digest((directory / name).read_text(encoding="utf-8")) for name in rendered}}, indent=2), encoding="utf-8")
    return rendered


def regenerate(snapshot, out, *, review=None, language="it"):
    from ..pipeline import _output_path
    if language not in {"it", "en"}:
        raise ValueError("Supported document languages: it, en")
    model = load_model(snapshot)
    if isinstance(review, (str, Path)):
        review = read_json(review, 1024 * 1024)
    applied = apply_review(model, review)
    out = _output_path(out)
    snapshot = Path(snapshot).resolve()
    if out == snapshot or out.is_relative_to(snapshot) or snapshot.is_relative_to(out):
        raise ValueError("Use a separate document package directory")
    marker = out / "document-package.json"
    if out.exists() and any(out.iterdir()):
        if not marker.is_file():
            raise ValueError("Refusing to overwrite unrecognized document directory")
        old = read_json(marker)
        expected = old.get("files", {})
        actual = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
        if actual != set(expected) | {"document-package.json"}:
            raise ValueError("Document package has user files; choose a new output directory")
        for name, expected_hash in expected.items():
            path = out / name
            if not path.resolve().is_relative_to(out) or path.is_symlink() or digest(path.read_text(encoding="utf-8")) != expected_hash:
                raise ValueError("Generated documents were edited; choose a new output directory")
        if review is None and (out / "engineering-review.json").is_file():
            review = read_json(out / "engineering-review.json", 1024 * 1024)
            applied = apply_review(model, review)
    out.mkdir(parents=True, exist_ok=True)
    rendered = write_documents(model, out, language, review)
    (out / "engineering-model.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    if review:
        (out / "engineering-review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    package = {"schema": "ases-document-package/1.0", "parent_snapshot": model["snapshot_id"], "model_digest": model["model_digest"],
               "review_digest": digest(review) if review else None, "language": language,
               "review_state": applied.get("review_state"),
               "files": {p.name: digest(p.read_text(encoding="utf-8")) for p in out.iterdir() if p.is_file() and p.name != marker.name}}
    marker.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    return package
