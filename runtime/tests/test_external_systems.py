from pathlib import Path
from ases.pipeline import scan_project


def _model(tmp_path, name, files):
    root=tmp_path/name
    root.mkdir()
    for filename,code in files.items():
        path=root/filename
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(code,encoding='utf-8')
    return scan_project(root,tmp_path/f'{name}-out')['semantic_model']


def _names(model):
    return {x['name'] for x in model['external_systems']}


def test_python_known_client_import_is_recovered(tmp_path):
    model=_model(tmp_path,'py-ext',{
        'app.py':'import openai\n\nclass Client:\n    def run(self):\n        return openai.OpenAI()\n',
    })
    names=_names(model)
    assert 'OpenAI API' in names
    entry=next(x for x in model['external_systems'] if x['name']=='OpenAI API')
    assert entry['provenance']['state']=='INFERRED'
    assert entry['provenance']['evidence']


def test_typescript_known_client_import_is_recovered(tmp_path):
    model=_model(tmp_path,'ts-ext',{
        'client.ts':"import Stripe from 'stripe'\n\nclass Billing {\n  run() { return new Stripe('key') }\n}\n",
    })
    assert 'Stripe' in _names(model)


def test_java_known_client_import_is_recovered(tmp_path):
    model=_model(tmp_path,'java-ext',{
        'src/main/java/demo/Notifier.java':'import com.twilio.Twilio;\n\nclass Notifier {\n    void run() { Twilio.init("a","b"); }\n}\n',
    })
    assert 'Twilio' in _names(model)


def test_no_known_client_import_means_empty(tmp_path):
    model=_model(tmp_path,'no-ext',{
        'app.py':'import json\n\nclass Thing:\n    def run(self):\n        return json.dumps({})\n',
    })
    assert model['external_systems']==[]


def test_db_driver_import_is_not_treated_as_external_system(tmp_path):
    # Deliberate scope boundary (see recover_external_systems docstring/comment): generic DB
    # drivers are not in the allowlist, so they never show up here — they overlap with
    # data_stores, which already covers "entity" nodes.
    model=_model(tmp_path,'db-ext',{
        'app.py':'import psycopg2\n\nclass Repo:\n    def run(self):\n        return psycopg2.connect("")\n',
    })
    assert model['external_systems']==[]
