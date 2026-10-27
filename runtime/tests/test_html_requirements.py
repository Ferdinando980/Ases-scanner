"""Column fidelity and inert HTML recovery; assessed defect retained as regression."""
import pytest
from ases.pipeline import scan_project
from ases.engineering.inputs import StaticHTML


@pytest.mark.parametrize('header',['Statement','Description','Descrizione'])
def test_html_requirement_text_excludes_priority_and_retains_table_position(tmp_path,header):
    root=tmp_path/'project';(root/'docs').mkdir(parents=True)
    (root/'docs/RAD.html').write_text('<table><tr><th>ID</th><th>'+header+'</th><th>Priority</th></tr><tr><td>RF_HTML_1</td><td>The caller shall read café.</td><td>High</td></tr></table>',encoding='utf-8')
    model=scan_project(root,tmp_path/'scan')['engineering_model']
    row=model['requirements'][0]
    assert row['statement']=='The caller shall read café.'
    assert row['fields']['priority']=='High'
    assert row['locations'][0]['element']=='table[1]' and row['locations'][0]['table_row']==2
    assert row['satisfaction']=='not-verified'
    assert model['document_profile']=='inert-documents/9'


def test_html_tables_remain_inert_and_cell_budget_is_enforced(monkeypatch):
    parser=StaticHTML();parser.feed('<table><tr><td>A<script>RF_BAD_1 fake requirement</script>B</td></tr></table>')
    assert parser.tables==[[['AB']]]
    monkeypatch.setattr('ases.engineering.inputs.MAX_CELLS',1)
    with pytest.raises(ValueError,match='cell limit'):StaticHTML().feed('<table><tr><td>a</td><td>b</td></tr></table>')
