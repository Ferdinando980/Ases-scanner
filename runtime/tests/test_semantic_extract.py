import json
import pytest

from ases.engineering import semantic_extract as semantic
from ases.engineering.model import digest
from ases.engineering import _semantic_worker as worker


def _snapshot():
    sentence = 'The application shall allow a librarian to reserve an available book.'
    model = {'snapshot_id':'snap-test','model_digest':'base-digest','sources':[{'id':'doc:1','path':'req.md','sha256':'a'*64,
             'units':[{'line':3,'text':sentence}]}]}
    return model, sentence


def _fake_setup(tmp_path, monkeypatch, stdout, returncode=0, stderr=''):
    model, sentence = _snapshot()
    monkeypatch.setattr(semantic, '_load_model', lambda _path: model)
    py = tmp_path/'python.exe'; py.touch()
    model_dir = tmp_path/'model'; model_dir.mkdir()
    (model_dir/'config.json').write_text('{}', encoding='utf-8')
    (model_dir/'model.safetensors').write_bytes(b'fixture weights')
    class Runner:
        returncode = 0
        def communicate(self, data, timeout):
            assert json.loads(data)['sentences'][0]['text'] == sentence
            assert timeout in (5, 120)
            return stdout, stderr
        def kill(self): raise AssertionError('normal fixture must not be killed')
    runner = Runner()
    runner.returncode = returncode
    monkeypatch.setattr(semantic.subprocess, 'Popen', lambda args, **kwargs: runner)
    return model, sentence, py, model_dir


def test_semantic_extract_accepts_exact_sentence_and_keeps_score_heuristic(tmp_path, monkeypatch):
    model, sentence = _snapshot()
    selected, _ = semantic._sentences(model, 40)
    response = {'source_fingerprint':digest([{'id':selected[0]['id'],'text':sentence}]),
                'classifications':[{'label':'functional requirement','score':0.82}]}
    _, _, py, model_dir = _fake_setup(tmp_path, monkeypatch, json.dumps(response))
    artifact = semantic.interpret(tmp_path, python_executable=py, model_path=model_dir, timeout=5)
    assert artifact['schema'] == 'ases-local-interpretation/1.0'
    assert artifact['hypotheses'][0]['statement'] == artifact['hypotheses'][0]['quote'] == sentence
    assert artifact['hypotheses'][0]['confidence']['value'] == 0.82
    assert artifact['hypotheses'][0]['authority'] == 'local-model-hypothesis'
    assert artifact['coverage']['status'] == 'PARTIAL'


def test_semantic_extract_reports_malformed_worker_as_error(tmp_path, monkeypatch):
    _, _, py, model_dir = _fake_setup(tmp_path, monkeypatch, '{bad json')
    artifact = semantic.interpret(tmp_path, python_executable=py, model_path=model_dir)
    assert artifact['provider']['status'] == 'error'
    assert artifact['hypotheses'] == [] and artifact['failures']


def test_semantic_extract_rejects_worker_source_fingerprint_mismatch(tmp_path, monkeypatch):
    response={'source_fingerprint':'0'*64,'classifications':[{'label':'functional requirement','score':.9}]}
    _, _, py, model_dir = _fake_setup(tmp_path, monkeypatch, json.dumps(response))
    artifact=semantic.interpret(tmp_path,python_executable=py,model_path=model_dir)
    assert artifact['provider']['status']=='error' and not artifact['hypotheses']
    assert 'Fingerprint' in artifact['failures'][0]['reason']


def test_semantic_extract_preserves_multiline_source_and_never_invents_quotes():
    model, sentence = _snapshot()
    raw='Header text for context.\n' + sentence + '\nFollow-up detail without a terminator'
    model['sources'][0]['units'][0]['text']=raw
    selected, _=semantic._sentences(model,40)
    assert all(row['text'] in raw for row in selected)
    assert all(row['source_text']==raw for row in selected)
    assert len(selected)==1
    assert selected[0]['text']==raw.strip()


def test_whole_source_units_keep_decimal_abbreviations_and_skip_examples_code_and_long_units():
    model, _ = _snapshot()
    model['sources'][0]['units'] = [
        {'line': 1, 'text': 'The sensor shall report 99.9% uptime for Dr. Smith.'},
        {'line': 2, 'text': 'Example: The system shall print a sample message.'},
        {'line': 3, 'text': '```python\nThe system shall do something.\n```'},
        {'line': 4, 'text': 'x' * 2001},
    ]
    selected, omitted = semantic._sentences(model, 40)
    assert [row['text'] for row in selected] == ['The sensor shall report 99.9% uptime for Dr. Smith.']
    assert omitted == 3


def test_source_unit_state_skips_separate_fence_lines_and_example_section_contents():
    model, _ = _snapshot()
    model['sources'][0]['units'] = [
        {'line': 1, 'text': '```python'},
        {'line': 2, 'text': 'The system shall print a code sample.'},
        {'line': 3, 'text': '```'},
        {'line': 4, 'text': '# Examples'},
        {'line': 5, 'text': 'The system shall print a documentation example.'},
        {'line': 6, 'text': '# Requirements'},
        {'line': 7, 'text': 'The application shall retain an approved requirement.'},
    ]
    selected, omitted = semantic._sentences(model, 40)
    assert [row['text'] for row in selected] == ['The application shall retain an approved requirement.']
    assert omitted == 6


def test_model_fingerprint_hashes_contents_even_when_size_and_mtime_match(tmp_path):
    model_dir = tmp_path/'model'; model_dir.mkdir()
    config = model_dir/'config.json'; weights = model_dir/'model.safetensors'
    config.write_bytes(b'{}'); weights.write_bytes(b'first weights')
    before = semantic._model_fingerprint(model_dir)
    stat = weights.stat()
    weights.write_bytes(b'other weights')
    import os
    os.utime(weights, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert weights.stat().st_size == stat.st_size
    assert semantic._model_fingerprint(model_dir) != before


def test_model_fingerprint_rejects_arbitrary_and_pickle_files(tmp_path):
    model_dir = tmp_path/'model'; model_dir.mkdir()
    (model_dir/'config.json').write_bytes(b'{}')
    (model_dir/'model.safetensors').write_bytes(b'weights')
    (model_dir/'private.pkl').write_bytes(b'pickle')
    with pytest.raises(ValueError, match='non ammesso'):
        semantic._model_fingerprint(model_dir)


def test_model_fingerprint_allows_bounded_generic_manifest_without_hashing_it(tmp_path):
    model_dir = tmp_path/'model'; model_dir.mkdir()
    (model_dir/'config.json').write_bytes(b'{}')
    (model_dir/'model.safetensors').write_bytes(b'weights')
    manifest = model_dir/'vendor-manifest.json'; manifest.write_text('first', encoding='utf-8')
    first = semantic._model_fingerprint(model_dir)
    manifest.write_text('second', encoding='utf-8')
    assert semantic._model_fingerprint(model_dir) == first


def test_worker_token_preflight_disables_truncation_and_skips_over_limit_text():
    class Tokenizer:
        model_max_length = 512
        def __call__(self, text, *, truncation, add_special_tokens):
            assert truncation is False and add_special_tokens is True
            # Simulate code/CJK tokenization expanding far beyond whitespace words.
            return {'input_ids': list(range(600 if text == 'dense' else 20))}
    tokenizer = Tokenizer()
    assert worker._token_preflight(tokenizer, 'short', 512) == (True, None)
    allowed, reason = worker._token_preflight(tokenizer, 'dense', 512)
    assert not allowed and '600>384' in reason and '128 schema tokens reserved' in reason


def test_coordinator_counts_worker_token_skips_as_omissions_and_attempts(tmp_path, monkeypatch):
    model, sentence = _snapshot(); selected, _ = semantic._sentences(model, 40)
    response = {'source_fingerprint':digest([{'id':selected[0]['id'],'text':sentence}]),
                'classifications':[{'skipped':True,'reason':'token limit exceeded (600>512)'}]}
    _, _, py, model_dir = _fake_setup(tmp_path, monkeypatch, json.dumps(response))
    artifact = semantic.interpret(tmp_path, python_executable=py, model_path=model_dir, timeout=5)
    assert artifact['hypotheses'] == []
    assert artifact['omissions'] == 1
    assert artifact['coverage']['classifications_attempted'] == 0
    assert artifact['sources'][0]['classification_status'] == 'skipped'


@pytest.mark.parametrize('score', [float('nan'), -0.01, 1.01, float('inf')])
def test_semantic_extract_ignores_invalid_and_nonfinite_model_scores(tmp_path, monkeypatch, score):
    model, sentence = _snapshot(); selected,_=semantic._sentences(model,40)
    response={'source_fingerprint':digest([{'id':selected[0]['id'],'text':sentence}]),
              'classifications':[{'label':'functional requirement','score':score}]}
    _,_,py,model_dir=_fake_setup(tmp_path,monkeypatch,json.dumps(response))
    artifact=semantic.interpret(tmp_path,python_executable=py,model_path=model_dir,timeout=5)
    assert len(artifact['hypotheses'])==1
    assert artifact['hypotheses'][0]['confidence']['value'] is None


def test_semantic_extract_distinguishes_empty_classification_from_worker_error(tmp_path, monkeypatch):
    model, sentence=_snapshot(); selected,_=semantic._sentences(model,40)
    empty={'source_fingerprint':digest([{'id':selected[0]['id'],'text':sentence}]),
           'classifications':[{'label':'not a requirement','score':.77}]}
    _,_,py,model_dir=_fake_setup(tmp_path,monkeypatch,json.dumps(empty))
    result=semantic.interpret(tmp_path,python_executable=py,model_path=model_dir,timeout=5)
    assert result['provider']['status']=='ok' and not result['hypotheses'] and not result['failures']


def test_unavailable_local_runtime_is_explicit_and_does_not_start_worker(tmp_path, monkeypatch):
    model,_=_snapshot();monkeypatch.setattr(semantic,'_load_model',lambda _path:model)
    monkeypatch.setattr(semantic.subprocess,'Popen',lambda *a,**k: (_ for _ in ()).throw(AssertionError('worker must not start')))
    result=semantic.interpret(tmp_path,python_executable=tmp_path/'missing.exe',model_path=tmp_path/'missing-model')
    assert result['provider']['status']=='unavailable'
    assert 'nessun download' in result['failures'][0]['reason']


def test_low_memory_worker_error_is_not_retried_or_resolved_by_download(tmp_path, monkeypatch):
    _,_,py,model_dir=_fake_setup(tmp_path,monkeypatch,'',returncode=1,
                                 stderr='Memoria disponibile sotto la soglia configurata; modello non caricato.')
    result=semantic.interpret(tmp_path,python_executable=py,model_path=model_dir,timeout=5,log_path=tmp_path/'worker.log')
    assert result['provider']['status']=='error' and len(result['failures'])==1
    assert 'nessun download' in result['failures'][0]['reason']
    assert (tmp_path/'worker.log').read_text(encoding='utf-8').startswith('Memoria disponibile')


def test_semantic_extract_timeout_is_explicit_and_worker_is_owned(tmp_path, monkeypatch):
    model, _ = _snapshot(); monkeypatch.setattr(semantic, '_load_model', lambda _path: model)
    py=tmp_path/'python.exe';py.touch(); model_dir=tmp_path/'model';model_dir.mkdir()
    (model_dir/'config.json').write_text('{}', encoding='utf-8')
    (model_dir/'model.safetensors').write_bytes(b'fixture weights')
    class Proc:
        killed=False
        def communicate(self, *args, **kwargs): raise semantic.subprocess.TimeoutExpired('owned', 1)
        def kill(self): self.killed=True
        def communicate_after_kill(self): pass
    proc=Proc()
    def start(args, **kwargs):
        assert kwargs['shell'] is False and kwargs['env']['HF_HUB_OFFLINE']=='1'
        return proc
    monkeypatch.setattr(semantic.subprocess,'Popen',start)
    # communicate is called a second time after kill by the coordinator.
    calls={'n':0}
    def communicate(*args,**kwargs):
        calls['n']+=1
        if calls['n']==1: raise semantic.subprocess.TimeoutExpired('owned',1)
        return ('','')
    proc.communicate=communicate
    artifact=semantic.interpret(tmp_path,python_executable=py,model_path=model_dir,timeout=1)
    assert proc.killed and artifact['provider']['status']=='error'
    assert 'Scaduto' in artifact['failures'][0]['reason']
