import json
import pytest
from ases.engineering import local_interpret as local
from ases.pipeline import scan_project


@pytest.mark.parametrize('endpoint',['https://127.0.0.1:80','http://localhost:80','http://127.0.0.1.example.org',
    'http://user:password@127.0.0.1','http://127.0.0.1/path','http://10.0.0.1','http://127.0.0.1?key=x'])
def test_local_interpretation_rejects_nonliteral_or_credentialed_endpoints(endpoint):
    with pytest.raises(ValueError):local.endpoint_parts(endpoint)


def test_hypotheses_require_exact_citations_and_do_not_modify_source_model(tmp_path,monkeypatch):
    root=tmp_path/'app';root.mkdir()
    text='Users search stored documents and receive ranked matches with excerpts from the matching documents.'
    (root/'README.md').write_text(text)
    scan_project(root,tmp_path/'snapshot')
    modelpath=tmp_path/'snapshot/engineering-model.json';before=modelpath.read_bytes()
    def reply(endpoint,path,payload=None):
        assert endpoint=='http://127.0.0.1:8080/v1'
        if path.endswith('/models'):return {'data':[{'id':'test-model'}]}
        assert payload['chat_template_kwargs']=={'enable_thinking':False}
        return {'choices':[{'message':{'content':json.dumps({'candidates':[
            {'statement':'Gli utenti possono cercare documenti e leggere estratti dei risultati.','quote':text,'kind':'functional'},
            {'statement':'Il servizio garantisce disponibilità continua.','quote':'Invented availability guarantee','kind':'nonfunctional'}]})}}]}
    monkeypatch.setattr(local,'request_json',reply)
    result=local.interpret(tmp_path/'snapshot','http://127.0.0.1:8080/v1',maximum=1)
    assert len(result['candidates'])==1 and result['rejected_candidates']==1
    assert result['candidates'][0]['authority']=='local-model-hypothesis'
    assert result['candidates'][0]['satisfaction']=='not-verified'
    local.write_result(result,tmp_path/'interpretation')
    assert modelpath.read_bytes()==before
    with pytest.raises(ValueError,match='existing files'):local.write_result(result,tmp_path/'interpretation')


def test_malformed_model_answer_is_an_explicit_reading_gap(tmp_path,monkeypatch):
    root=tmp_path/'app';root.mkdir();(root/'README.md').write_text('A descriptive sentence about searchable documents, preserved with its original source evidence. '*2)
    scan_project(root,tmp_path/'snapshot')
    monkeypatch.setattr(local,'request_json',lambda *a,**kw:{'choices':[{'message':{'content':'[]'}}]})
    result=local.interpret(tmp_path/'snapshot','http://127.0.0.1:8080',model_name='test',maximum=1)
    assert not result['candidates'] and len(result['failures'])==1


def test_excerpt_selection_skips_navigation_and_fenced_examples():
    text='The user searches stored documents and can inspect matching passages in a readable result list.'
    source={'id':'doc:test','path':'README.md','sha256':'a'*64,'role':'GUIDE','units':[
        {'line':1,'text':'- [A long navigation title with no actual behavioral explanation at all](#navigation)'},
        {'line':2,'text':'```python'},{'line':3,'text':text},{'line':4,'text':'```'},
        {'line':5,'text':text}]}
    rows=local.excerpts({'sources':[source]},3)
    assert len(rows)==1 and rows[0]['locations'][0]['line']==5
    valid=local.validate_candidate({'statement':'Gli utenti possono consultare i risultati della ricerca.','kind':'functional','quote_index':0},rows[0])
    assert valid['quote']==text
    assert local.validate_candidate({'statement':'Gli utenti possono consultare i risultati della ricerca.','kind':'functional','quote_index':True},rows[0]) is None
