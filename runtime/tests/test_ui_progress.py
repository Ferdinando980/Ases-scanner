"""Exercise the actual progress renderer without a browser or a project scan."""
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
from time import monotonic

import pytest


def test_progress_read_gap_keeps_last_confirmed_stage(tmp_path):
    from ases.ui import Desk
    desk = Desk('')
    desk.pending = SimpleNamespace(name=str(tmp_path))
    desk.started = monotonic()
    desk.state = {'status':'running','stage':'starting'}
    path = tmp_path/'progress.json'
    path.write_text(json.dumps({'stage':'behavior-interpretation'}))
    assert desk.status()['stage']=='behavior-interpretation'
    path.unlink()
    assert desk.status()['stage']=='behavior-interpretation'
    path.write_text('{')
    assert desk.status()['stage']=='behavior-interpretation'
    desk.pending = None


@pytest.mark.parametrize("language", ["it", "en"])
def test_document_progress_does_not_restart_file_scope(language):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed to execute the desk renderer")
    app = (Path(__file__).parents[1] / "ases/ui_assets/app.js").read_text(encoding="utf-8")
    renderer = app.split("function renderProgress(state){", 1)[1].split("function renderReport()", 1)[0]
    script = """
const assert = require('node:assert/strict');
const language = LANGUAGE;
const nodes = new Map();
const $ = id => {
  if (!nodes.has(id)) nodes.set(id, {value:'project', replaceChildren(...children){this.children=children;}});
  return nodes.get(id);
};
const el = (tag, text, className) => ({tag,text,className});
const t = key => key;
const labelAction = key => key;
function renderProgress(state){RENDERER
for (const stage of ['documents','document-inputs','document-analysis','document-api','behavior-interpretation','document-rendering']) {
  renderProgress({stage,elapsed:61,status:'running'});
  assert.equal($('job-stages').children.findIndex(row=>row.className==='active'),3,stage);
  assert.notEqual($('stage').textContent,$('job-stages').children[0].text,stage);
  assert.match($('elapsed').textContent,/1:01$/);
}
renderProgress({stage:'future-stage',elapsed:62,status:'running'});
assert.equal($('job-stages').children.filter(row=>row.className==='active').length,0);
assert.equal($('stage').textContent,language==='it'?'Analisi in corso':'Analysis in progress');
renderProgress({stage:'behavior-interpretation',elapsed:63,status:'cancelling'});
assert.equal($('stage').textContent,'cancelling');
""".replace("LANGUAGE", json.dumps(language)).replace("RENDERER", renderer)
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)


@pytest.mark.parametrize("language", ["it", "en"])
def test_open_snapshot_progress_uses_one_operation_stage(language):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed to execute the desk renderer")
    app = (Path(__file__).parents[1] / "ases/ui_assets/app.js").read_text(encoding="utf-8")
    renderer = app.split("function renderProgress(state){", 1)[1].split("function renderReport()", 1)[0]
    script = """
const assert = require('node:assert/strict');
const language = LANGUAGE;
const nodes = new Map();
const $ = id => {
  if (!nodes.has(id)) nodes.set(id, {value:id==='task'?'open':'project', replaceChildren(...children){this.children=children;}});
  return nodes.get(id);
};
const el = (tag, text, className) => ({tag,text,className});
const t = key => key;
const labelAction = key => key;
function renderProgress(state){RENDERER
const opening = language==='it'?'Apro lo snapshot salvato':'Opening saved snapshot';
for (const stage of ['starting','open','presentation','unknown-stage']) {
  renderProgress({stage,elapsed:61,status:'running'});
  assert.deepEqual($('job-stages').children.map(row=>row.text),[language==='it'?'Riapertura snapshot':'Reopening snapshot'],stage);
  assert.equal($('job-stages').children[0].className,'active',stage);
  assert.equal($('stage').textContent,opening,stage);
  assert.match($('elapsed').textContent,/1:01$/,stage);
}
renderProgress({stage:'open',elapsed:63,status:'cancelling'});
assert.equal($('stage').textContent,'cancelling');
assert.equal($('job-stages').children.length,1);
assert.equal($('job-stages').children[0].className,'active');
$('task').value='scan';
renderProgress({stage:'starting',elapsed:64,status:'running'});
assert.equal($('job-stages').children.length,5);
assert.equal($('job-stages').children[0].className,'active');
renderProgress({stage:'document-analysis',elapsed:65,status:'running'});
assert.equal($('job-stages').children.findIndex(row=>row.className==='active'),3);
""".replace("LANGUAGE", json.dumps(language)).replace("RENDERER", renderer)
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)
