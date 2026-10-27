import json

import pytest

from ases.cli import build_parser, main
from ases.ui_operations import execute


def _gliner_result():
    return {
        'schema': 'ases-local-interpretation/1.0',
        'snapshot_id': 'snapshot-test',
        'base_model_digest': 'digest-test',
        'model': 'GLiNER2 (percorso locale esplicito)',
        'hypotheses': [{'statement': 'A saved sentence.', 'quote': 'A saved sentence.',
                        'kind': 'functional', 'locations': [{'path': 'README.md'}],
                        'authority': 'local-model-hypothesis'}],
        'failures': [], 'limits': ['Review each hypothesis manually.'],
        'provider': {'name': 'GLiNER2', 'status': 'ok'},
    }


def test_cli_interpret_dispatches_gliner2_and_uses_shared_writer(tmp_path, monkeypatch, capsys):
    from ases.engineering import semantic_extract
    calls = []

    def interpret(snapshot, *, python_executable, model_path, limit):
        assert limit == 3
        calls.append((snapshot, python_executable, model_path))
        return _gliner_result()

    monkeypatch.setattr(semantic_extract, 'interpret', interpret)
    output = tmp_path / 'reading'
    assert main(['interpret', str(tmp_path / 'snapshot'), '--provider', 'gliner2',
                 '--python-executable', 'local-python', '--model-path', 'local-model',
                 '--out', str(output)]) == 0
    assert calls == [(str(tmp_path / 'snapshot'), 'local-python', 'local-model')]
    saved = json.loads((output / 'interpretation.json').read_text(encoding='utf-8'))
    assert saved['hypotheses'] == _gliner_result()['hypotheses']
    assert saved['candidates'] == saved['hypotheses']
    assert 'A saved sentence.' in (output / 'INTERPRETATION.md').read_text(encoding='utf-8')
    assert json.loads(capsys.readouterr().out)['provider']['name'] == 'GLiNER2'


def test_ui_interpret_dispatches_gliner2_and_persists_backend_report(tmp_path, monkeypatch):
    from ases.engineering import semantic_extract
    calls = []

    def interpret(snapshot, *, python_executable, model_path):
        calls.append((snapshot, python_executable, model_path))
        return _gliner_result()

    monkeypatch.setattr(semantic_extract, 'interpret', interpret)
    output = tmp_path / 'reading'
    snapshot = tmp_path / 'snapshot'
    snapshot.mkdir()
    result = execute('interpret', {'source': str(snapshot), 'provider': 'gliner2',
                                   'python_executable': 'local-python', 'model_path': 'local-model'},
                     output, retain_source=lambda _: None)
    assert calls == [(snapshot, 'local-python', 'local-model')]
    assert result['data']['hypotheses'] == _gliner_result()['hypotheses']
    assert result['data']['candidates'] == result['data']['hypotheses']
    saved = json.loads((output / 'operation-result.json').read_text(encoding='utf-8'))
    assert saved['provider']['name'] == 'GLiNER2'


def test_provider_arguments_are_conditional_and_missing_values_fail_clearly(tmp_path):
    default = build_parser().parse_args(['interpret', 'snapshot', '--out', 'reading'])
    assert default.provider == 'llm' and default.endpoint is None
    with pytest.raises(SystemExit, match='endpoint'):
        main(['interpret', 'snapshot', '--out', str(tmp_path / 'out')])
    with pytest.raises(SystemExit, match='python-executable and --model-path'):
        main(['interpret', 'snapshot', '--provider', 'gliner2', '--out', str(tmp_path / 'out')])
    with pytest.raises(ValueError, match='local model server endpoint'):
        execute('interpret', {'source': str(tmp_path / 'snapshot'), 'provider': 'llm'},
                tmp_path / 'ui-out', retain_source=lambda _: None)
    with pytest.raises(ValueError, match='Python runtime and model directory'):
        execute('interpret', {'source': str(tmp_path / 'snapshot'), 'provider': 'gliner2'},
                tmp_path / 'ui-out', retain_source=lambda _: None)
