from io import BytesIO
import http.client
import json
from pathlib import Path
import tempfile
import threading
import subprocess
import sys
import zipfile

import pytest

from ases.cli import build_parser
from ases.pipeline import scan_project
from ases.ui import Desk, create_server, kit_catalog, kit_download
from ases.ui_operations import execute


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    root = tmp_path / "bookshop"
    root.mkdir()
    (root / "app.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n"
        "def read_books():\n    return ['a book']\n"
        "@app.get('/books')\ndef books():\n    return read_books()\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture
def desk(project):
    value = Desk(str(project))
    yield value
    value.close()


def finish(desk, source, **kwargs):
    desk.start(str(source), **kwargs)
    desk.worker.join(20)
    assert not desk.worker.is_alive()
    assert desk.state["status"] == "complete", desk.state
    return desk.result


def test_reduced_export_excludes_text_paths_names_and_saved_notes(desk,project):
    (project/'requirements.yaml').write_text('requirements:\n  - id: RF_PRIVATE_1\n    kind: functional\n    statement: The PRIVATE_DOCUMENT_SENTINEL shall stay local.\n',encoding='utf-8')
    result=finish(desk,project)
    model=json.loads((result['output']/'engineering-model.json').read_text(encoding='utf-8'))
    row=model['requirements'][0]
    desk.save_engineering_review({'schema':'ases-engineering-review/1.0','operations':[{'action':'annotate','record_id':row['id'],'expected_digest':row['record_digest'],'note':'PRIVATE_NOTE_SENTINEL'}]})
    with zipfile.ZipFile(BytesIO(desk.download('it','reduced'))) as archive:
        assert set(archive.namelist())=={'START-HERE.md','EXPORT-CONTENTS.json'}
        content=b'\n'.join(archive.read(name) for name in archive.namelist())
        for value in (b'PRIVATE_DOCUMENT_SENTINEL',b'PRIVATE_NOTE_SENTINEL',b'app.py',b'bookshop',str(project).encode(),model['snapshot_id'].encode()):
            assert value not in content
        policy=json.loads(archive.read('EXPORT-CONTENTS.json'))
        assert not policy['reopenable_snapshot'] and policy['omitted']
    with zipfile.ZipFile(BytesIO(desk.download('it','full'))) as archive:
        assert b'PRIVATE_NOTE_SENTINEL' in archive.read('engineering-review.json')
        assert 'docs/OVERVIEW.md' in archive.namelist() and 'docs/TRACEABILITY.md' in archive.namelist()
        assert json.loads(archive.read('EXPORT-CONTENTS.json'))['mode']=='full'


def test_export_limit_keeps_result_and_reduced_download(desk,project,monkeypatch):
    result=finish(desk,project)
    monkeypatch.setattr('ases.ui.MAX_EXPORT_BYTES',16)
    with pytest.raises(ValueError,match='128 MiB'):desk.download(mode='full')
    assert desk.result is result and desk.download(mode='reduced')
    with pytest.raises(ValueError,match='Unknown export mode'):desk.download(mode='arbitrary')


def test_export_bounds_uncompressed_input_separately(desk,project,monkeypatch):
    result=finish(desk,project)
    monkeypatch.setattr('ases.ui.MAX_EXPORT_INPUT_BYTES',16)
    with pytest.raises(ValueError,match='512 MiB'):desk.download(mode='full')
    assert desk.result is result
    assert desk.download(mode='reduced')


def test_ui_command_and_port_contract():
    args = build_parser().parse_args(["ui", "/project", "--no-browser", "--port", "8012"])
    assert (args.source, args.no_browser, args.port) == ("/project", True, 8012)
    with pytest.raises(ValueError, match="Port"):
        create_server(Desk(), -1)


def test_engineering_review_sources_export_and_rescan_conflict(desk, project, tmp_path):
    (project / "requirements.yaml").write_text('requirements:\n  - id: RF_BOOK_1\n    statement: The reader shall browse books.\n    actor: Reader\n', encoding="utf-8")
    finish(desk, project)
    data = desk.engineering({})
    assert data["available"] and data["counts"]["requirements"] == 1
    req = data["items"][0]
    excerpt = desk.engineering_source({"path": "requirements.yaml"})
    assert "browse books" in str(excerpt["units"])
    review = {"schema":"ases-engineering-review/1.0", "base_model_digest":data["model_digest"], "operations":[
        {"record_id":req["id"],"expected_digest":req["record_digest"],"action":"confirm","note":"Reviewed with the reader"}]}
    assert desk.save_engineering_review(review)["saved"]
    assert desk.engineering({})["items"][0]["review"]["note"] == "Reviewed with the reader"
    with zipfile.ZipFile(BytesIO(desk.download())) as archive:
        assert "engineering-review.json" in archive.namelist()
        assert "Reviewed with the reader" in archive.read("docs/RAD.md").decode()
    saved = tmp_path / "saved.ases"
    saved.mkdir()
    with zipfile.ZipFile(BytesIO(desk.download())) as archive:
        archive.extractall(saved)
    finish(desk, saved, action="open")
    assert desk.engineering({})["review"]["operations"] == review["operations"]
    (project / "requirements.yaml").write_text('requirements:\n  - id: RF_BOOK_1\n    statement: The reader shall buy books.\n', encoding="utf-8")
    finish(desk, project)
    result = desk.save_engineering_review(review)
    assert result["review_state"]["conflicts"]
    assert "review" not in desk.engineering({})["items"][0]


def test_engineering_source_rejects_unreferenced_paths(desk, project):
    finish(desk, project)
    with pytest.raises(ValueError, match="not present"):
        desk.engineering_source({"path":"../private.txt"})
    with pytest.raises(ValueError, match="Unknown"):
        desk.engineering({"collection":"arbitrary"})


def test_scan_brief_trace_source_and_temporary_cleanup(desk, project):
    before = sorted(p.name for p in project.iterdir())
    result = finish(desk, project)
    report = result["report"]
    assert report["counts"]["routes"] == 1
    assert report["languages"] == ["Python"]
    assert "non è stato eseguito" in report["brief"]["it"][-1]
    assert report["relationship_coverage"]["calls"]["PARTIAL"] >= 1
    route = next(e for e in desk.items("entities")["items"] if e["kind"] == "route")
    assert route["locations"][0]["path"] == "app.py"
    source = desk.source("app.py", 6)
    assert any("read_books" in line for line in source["lines"])
    assert source["line"] == 6
    output = result["output"]
    with zipfile.ZipFile(BytesIO(desk.download())) as archive:
        assert "START-HERE.md" in archive.namelist()
        assert "docs/SUMMARY.md" in archive.namelist()
        assert "docs/REPORT.it.md" in archive.namelist()
        assert "Da verificare" in archive.read("START-HERE.md").decode("utf-8")
        assert "Il progetto non è stato eseguito" in archive.read("docs/REPORT.it.md").decode("utf-8")
        assert "consumer-context.v2.json" in archive.namelist()
        assert "app.py" not in archive.namelist()
    assert sorted(p.name for p in project.iterdir()) == before
    desk.clear()
    assert not output.exists()
    assert desk.state == {"status": "idle"}


def test_source_is_bound_to_observed_file_and_fresh_bytes(desk, project, tmp_path):
    finish(desk, project)
    secret = tmp_path / "unrelated.txt"
    secret.write_text("not part of this project")
    for path in ("../unrelated.txt", str(secret), "missing.py"):
        with pytest.raises(ValueError, match="not referenced"):
            desk.source(path)
    with pytest.raises(ValueError, match="line does not exist"):
        desk.source("app.py", 900)
    (project / "app.py").write_text("changed source")
    with pytest.raises(ValueError, match="changed"):
        desk.source("app.py")


def test_failure_preserves_the_last_completed_result(desk, project):
    finish(desk, project)
    old_output = desk.result["output"]
    desk.start(str(project / "missing-project"))
    desk.worker.join(10)
    assert desk.state["status"] == "failed"
    assert desk.status()["has_result"]
    assert desk._ready()["output"] == old_output
    assert old_output.exists()


def test_cancellation_stops_isolated_worker_and_preserves_result(desk, project, monkeypatch):
    finish(desk, project)
    old_output = desk.result["output"]
    original = subprocess.Popen
    entered = threading.Event()
    def slow_worker(command, **kwargs):
        if "-m" in command and "ases.ui_worker" in command:
            command = [sys.executable, "-c", "import time; time.sleep(30)"]
            entered.set()
        return original(command, **kwargs)
    monkeypatch.setattr(subprocess, "Popen", slow_worker)
    desk.start(str(project))
    assert entered.wait(5)
    with pytest.raises(ValueError, match="already running"):
        desk.start(str(project))
    with pytest.raises(ValueError, match="running operation"):
        desk.clear()
    assert desk.status()["has_result"]
    pending = Path(desk.pending.name)
    desk.cancel()
    desk.worker.join(15)
    assert not desk.worker.is_alive()
    assert desk.state["status"] == "cancelled", desk.state
    assert desk.process.poll() is not None
    assert not pending.exists()
    assert old_output.exists()
    assert desk._ready()["output"] == old_output


def test_scope_limit_can_be_fixed_without_changing_the_project(desk, project):
    (project / "large.py").write_text("#" + "x" * (2 * 1024 * 1024))
    desk.start(str(project))
    desk.worker.join(15)
    assert desk.state["status"] == "failed"
    assert "UI_SCOPE_LIMIT" in desk.state["error"]
    result = finish(desk, project, options={"exclude": "large.py"})
    assert result["report"]["counts"]["files"] == 1
    assert not (project / ".asesignore").exists()


def test_worker_does_not_import_project_modules_from_its_working_directory(desk, project, monkeypatch):
    counterfeit = project / "ases"
    counterfeit.mkdir()
    marker = project / "should-never-be-created"
    (counterfeit / "__init__.py").write_text("from pathlib import Path\nPath('should-never-be-created').write_text('executed')\n")
    (counterfeit / "ui_worker.py").write_text("raise RuntimeError('project code must not run')\n")
    monkeypatch.chdir(project)
    result = finish(desk, project)
    assert result["report"]["counts"]["routes"] == 1
    assert not marker.exists()


def test_pagination_search_and_unknown_collections(desk, project):
    (project / "many.py").write_text("\n".join(f"def fn_{i}(): return {i}" for i in range(90)))
    finish(desk, project)
    first = desk.items("entities")
    second = desk.items("entities", offset=40)
    assert first["total"] > 80
    assert not {e["id"] for e in first["items"]} & {e["id"] for e in second["items"]}
    assert desk.items("entities", "fn_89")["total"] == 1
    with pytest.raises(ValueError, match="Unknown collection"):
        desk.items("secrets")
    with pytest.raises(ValueError, match="Invalid page"):
        desk.items("entities", offset=-1)


def test_snapshot_open_export_compare_and_artifact_reconciliation(project, tmp_path):
    before, after = tmp_path / "before.ases", tmp_path / "after.ases"
    scan_project(project, before)
    (project / "more.py").write_text("def another(): return 1\n")
    scan_project(project, after)
    diff = execute("compare", {"source": str(before), "other": str(after)}, tmp_path / "delta", retain_source=lambda _: None)
    assert diff["data"]["semantic"]
    exported = execute("export", {"source": str(after), "schema": "2.0"}, tmp_path / "export", retain_source=lambda _: None)
    assert exported["data"]["schema"] == "ases-consumer-context/2.0"
    (after / "not-a-report.txt").write_text("unrelated")
    desk = Desk()
    try:
        result = finish(desk, after, action="open", options={"other": str(project)})
        assert result["report"]["counts"]["routes"] == 1
        assert not (result["output"] / "not-a-report.txt").exists()
        for name in ("OVERVIEW.md", "TRACEABILITY.md"):
            assert (result["output"] / "docs" / name).read_bytes() == (after / "docs" / name).read_bytes()
        assert desk.source("more.py")["lines"] == ["def another(): return 1"]
        finish(desk, project, action="artifact")
        assert desk.result["report"]["kind"] == "operation"
        artifact_path = desk.result["output"] / "artifact-snapshot.json"
        reconciled = execute("reconcile", {"source": str(after), "other": str(artifact_path)}, tmp_path / "reconciled", retain_source=lambda _: None)
        assert any(row["status"] == "matched" for row in reconciled["data"]["source_matches"])
        with pytest.raises(ValueError, match="does not contain"):
            desk.items("entities")
    finally:
        desk.close()


def test_audit_and_selfcheck_do_not_write_to_input(project, tmp_path):
    output = tmp_path / "check.ases"
    result = execute("selfcheck", {"source": str(project)}, output, retain_source=lambda _: None)
    assert result["data"]["status"] == "FAIL"  # A bookshop is not an ASES checkout.
    assert not (project / ".ases-selfcheck").exists()
    result = execute("audit", {"source": str(project)}, tmp_path / "audit.ases", retain_source=lambda _: None)
    assert result["data"]["status"] == "NO_BASELINE"


def test_kit_documents_are_explicit_drafts_and_download_only():
    catalog = kit_catalog()
    assert catalog["available"]
    assert "SOW.md" in catalog["templates"]
    content = "# Project intention\n\nA person wrote this requirement."
    with zipfile.ZipFile(BytesIO(kit_download({"SOW.md": content}))) as archive:
        assert archive.read("SOW.md").decode() == content
        assert archive.namelist() == ["SOW.md"]
    with pytest.raises(ValueError):
        kit_download({"../outside.md": content})
    with pytest.raises(ValueError):
        kit_download({"SOW.md": ["invalid"]})


def test_progress_retries_windows_reader_contention(tmp_path, monkeypatch):
    from ases.ui_worker import write_state
    original = Path.replace
    calls = []
    def transient(path, target):
        calls.append(target)
        if len(calls) < 3:
            raise PermissionError("reader briefly holds file")
        return original(path, target)
    monkeypatch.setattr(Path, "replace", transient)
    target = tmp_path / "progress.json"
    write_state(target, {"stage": "inventory"})
    assert json.loads(target.read_text())["stage"] == "inventory"
    assert len(calls) == 3


def test_previews_bound_delivery_without_changing_totals():
    from ases.ui_worker import operation_preview
    document = {"files": [{"path": f"{i}.js"} for i in range(55)], "unknowns": []}
    preview = operation_preview(document, "artifact")
    assert len(preview["files"]) == 10
    assert preview["counts"]["files"] == 55
    assert len(document["files"]) == 55
    assert preview["delivery"]["truncated"]


def test_cleanup_requires_current_preview_and_rejects_changed_output(desk, project, tmp_path):
    output = tmp_path / "saved.ases"
    scan_project(project, output)
    result = finish(desk, output, action="clean")
    fingerprint = result["data"]["fingerprint"]
    (output / "extra.txt").write_text("new material since preview")
    with pytest.raises(ValueError, match="changed"):
        desk.remove_output(fingerprint)
    assert output.exists()
    result = finish(desk, output, action="clean")
    desk.remove_output(result["data"]["fingerprint"])
    assert not output.exists()
    assert project.exists()


def test_browser_remote_protocols_and_credentials_are_not_accepted(project, tmp_path):
    for source in ("ssh://example.org/repo", "file:///some/repo", "https://user:pass@example.org/repo"):
        with pytest.raises(ValueError, match="public HTTPS"):
            execute("scan", {"source": source}, tmp_path / "unused", retain_source=lambda _: None)


def test_loopback_http_boundary_and_real_scan(desk, project):
    server = create_server(desk)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    def request(path, *, method="GET", body=None, headers=None, authenticated=True):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
        values = {"X-ASES-Token": desk.token} if authenticated else {}
        if body is not None:
            body = json.dumps(body)
            values["Content-Type"] = "application/json"
        values.update(headers or {})
        conn.request(method, path, body, values)
        response = conn.getresponse()
        payload = response.read()
        result = (response.status, dict(response.getheaders()), payload)
        conn.close()
        return result
    try:
        assert server.server_address[0] == "127.0.0.1"
        assert request("/")[0] == 200
        assert request("/api/config", authenticated=False)[0] == 403
        assert request("/api/config", headers={"Host": "attacker.example"})[0] == 403
        assert request("/api/config", headers={"Origin": "https://attacker.example"})[0] == 403
        assert request("/api/config", headers={"Origin": "null"})[0] == 403
        status, headers, _ = request("/api/config")
        assert status == 200 and headers["Cache-Control"] == "no-store"
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
        assert request("/api/scan", method="POST", body={"source": str(project), "options": []})[0] == 400
        assert request("/api/scan", method="POST", body={"source": str(project)})[0] == 202
        desk.worker.join(20)
        assert desk.state["status"] == "complete", desk.state
        status, _, payload = request("/api/report")
        assert status == 200 and json.loads(payload)["counts"]["routes"] == 1
        assert request("/api/source?path=../unrelated.txt")[0] == 400
        assert request("/api/source?path=app.py&line=6")[0] == 200
        assert request("/api/report", headers={"X-ASES-Snapshot": "stale"})[0] == 400
        assert request("/api/engineering-review",method="POST",body={"review":{"schema":"ases-engineering-review/1.1","operations":[]}},headers={"X-ASES-Snapshot":"stale"})[0]==400
        assert not (desk.result["output"] / "engineering-review.json").exists()
        route = next(e for e in desk.result["entities"] if e["kind"] == "route")
        trace = json.loads(request("/api/trace?id=" + route["id"])[2])
        assert trace["selection"] == "exact"
        assert trace["relations"]
        assert request("/api/document?name=SUMMARY.md")[0] == 200
        for name in ("OVERVIEW.md", "TRACEABILITY.md"):
            status, _, payload = request("/api/document?name=" + name)
            assert status == 200 and "\n# " in json.loads(payload)["text"]
        (desk.result["output"] / "docs" / "SUMMARY.md").write_text("readable\n" * 2000)
        preview = json.loads(request("/api/document?name=SUMMARY.md")[2])
        assert preview["truncated"]
        assert len(preview["text"].splitlines()) == 1500
        assert request("/api/document?name=../private.txt")[0] == 400
        assert request("/api/download?lang=en")[0] == 200
        assert request("/api/clear", method="POST", body={})[0] == 200
        assert request("/api/report")[0] == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_operation_context_and_adopted_requirement_export_reopen_and_source_change(desk,project,tmp_path):
    finish(desk,project)
    data=desk.engineering({"collection":"operations"});op=data["items"][0]
    review={"schema":"ases-engineering-review/1.1","base_model_digest":data["model_digest"],"operations":[
        {"action":"set-operation-context","record_id":op["id"],"expected_digest":op["record_digest"],"context":{"title":"Browse books","actor":"Reader"}},
        {"action":"adopt-requirement","record_id":"user-requirement:reader","source_record_id":op["id"],"expected_source_digest":op["record_digest"],
         "requirement":{"declared_id":"RF_READER_1","kind":"functional","statement":"The reader shall browse books.","author":"Project owner","scope":"Proposed release","acceptance":"Given an available book, its title appears in the list."}}]}
    assert desk.save_engineering_review(review)["saved"]
    assert desk.engineering({"collection":"operations"})["items"][0]["user_context"]["title"]=="Browse books"
    req=desk.engineering({"collection":"user_requirements"})["items"][0]
    assert req["satisfaction"]=="not-verified" and req["support_state"]=="current-candidate"
    saved=tmp_path/'saved.ases';saved.mkdir()
    with zipfile.ZipFile(BytesIO(desk.download())) as archive:
        assert "RF_READER_1" in archive.read("docs/RAD.md").decode('utf-8')
        archive.extractall(saved)
    finish(desk,saved,action='open')
    assert desk.engineering({"collection":"user_requirements"})["total"]==1
    assert desk.engineering({"collection":"operations"})["items"][0]["user_context"]["actor"]=="Reader"
    (project/'app.py').write_text((project/'app.py').read_text(encoding='utf-8').replace("a book","another book"),encoding='utf-8')
    finish(desk,project)
    assert desk.save_engineering_review(review)["review_state"]["conflicts"]
    assert desk.engineering({"collection":"user_requirements"})["items"][0]["support_state"]=="needs-review"
    assert 'user_context' not in desk.engineering({"collection":"operations"})["items"][0]
