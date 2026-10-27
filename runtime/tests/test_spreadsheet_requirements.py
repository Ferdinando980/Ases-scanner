"""Explicit column declarations stay separate from statement text and formula caches."""
import pytest
from ases.engineering.model import interpret_sources

def unit(sheet, number, values):
    return {'sheet':sheet,'row':number,'cells':[{'cell':col+str(number),'value':value,**extra}
            for col,value,extra in values], 'text':' | '.join(value for _,value,_ in values)}

def recover(units):
    return interpret_sources([{'id':'doc:sheet','path':'docs/RAD.xlsx','sha256':'a'*64,
        'role':'RAD','units':units,'limitations':[],'metadata':{}}])

@pytest.mark.parametrize('headers',[('ID','Descrizione','Priorità'),('Requirement ID','Statement','Priority'),('Codice','Description','Priorita')])
def test_explicit_columns_and_sparse_actor_position(headers):
    model=recover([unit('Requirements',1,[('A',headers[0],{}),('C',headers[1],{}),('F',headers[2],{}),('H','Actor',{})]),
        unit('Requirements',2,[('A','RF_BOOK_1',{}),('C','The reader shall find a book.',{}),('F','High',{}),('H','Reader',{})])])
    row=model['requirements'][0]
    assert row['statement']=='The reader shall find a book.'
    assert row['fields']['priority']=='High' and row['fields']['actor']=='Reader'
    assert row['locations'][0]['cell']=='A2,C2,F2,H2'
    assert row['satisfaction']=='not-verified'

def test_headers_do_not_leak_between_sheets_or_malformed_new_tables():
    rows=[unit('A',1,[('A','ID',{}),('B','Statement',{}),('C','Priority',{})]),
          unit('B',1,[('A','RF_BOOK_2',{}),('B','The reader shall browse a book.',{}),('C','High',{})]),
          unit('A',2,[('A','ID',{}),('B','Other value',{}),('C','Priority',{})]),
          unit('A',3,[('A','RF_BOOK_3',{}),('B','The reader shall select a book.',{}),('C','High',{})])]
    model=recover(rows)
    assert all(row['fields']['priority'] is None for row in model['requirements'])

def test_formula_cache_is_not_a_declared_priority_or_authored_statement():
    header=unit('A',1,[('A','ID',{}),('B','Statement',{}),('C','Priority',{})])
    model=recover([header,unit('A',2,[('A','RF_BOOK_1',{}),('B','The reader shall find a book.',{}),('C','High',{'formula':'"High"'})]),
        unit('A',3,[('A','RF_BOOK_2',{}),('B','The reader shall delete a book.',{'formula':'"The reader shall delete a book."'})]),
        unit('A',4,[('A','RF_BOOK_3',{'formula':'"RF_BOOK_3"'}),('B','The reader shall browse a book.',{})])])
    assert len(model['requirements'])==1 and model['requirements'][0]['id']=='RF_BOOK_1'
    assert model['requirements'][0]['fields']['priority'] is None

def test_ambiguous_priority_headers_do_not_select_a_column():
    model=recover([unit('A',1,[('A','ID',{}),('B','Statement',{}),('C','Priority',{}),('D','Priority',{})]),
                   unit('A',2,[('A','RF_BOOK_1',{}),('B','The reader shall find a book.',{}),('C','High',{}),('D','Low',{})])])
    assert model['requirements'][0]['fields']['priority'] is None
