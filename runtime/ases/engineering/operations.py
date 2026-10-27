"""Operation views over explicit entry sets; sharing a helper never merges them."""
from __future__ import annotations

from collections import defaultdict
import json


def build_operations(model):
    from .model import digest
    groups = defaultdict(list)
    for row in model.get('recovered_requirements', []):
        entries = tuple(sorted(set(row.get('entry_points', []))))
        groups[entries or (row['entry_ref'],)].append(row)
    operations, links = [], []
    for entries, rows in sorted(groups.items()):
        identifier = 'operation:' + digest(entries)[:24]
        locations, steps, sources = [], [], []
        seen_locations, seen_steps = set(), set()
        for row in rows:
            for loc in row['locations']:
                key = json.dumps(loc, sort_keys=True)
                if key not in seen_locations:
                    locations.append(loc); seen_locations.add(key)
            for fact in row['facts']:
                if fact['kind'] != 'call': continue
                key = json.dumps({k:fact.get(k) for k in ('entity_ref','line','callee','conditions')}, sort_keys=True)
                if key in seen_steps: continue
                seen_steps.add(key)
                steps.append({'callee':fact['callee'], 'conditions':fact['conditions'], 'entity_ref':fact['entity_ref'],
                              'line':fact['line'], 'fact_ref':fact['fact_id'], 'behavior_ref':row['id'],
                              'scope':'entry' if fact['entity_ref'] in entries else 'linked-component'})
            sources.append({'id':row['id'], 'name':row['name'], 'statement_it':row['statement_it'], 'statement_en':row['statement_en']})
            links.append({'id':'operation-link:'+digest([identifier,row['id']])[:24], 'source':identifier,'target':row['id'],
                          'target_collection':'recovered_requirements','relation':'supported-by-behavior', 'resolved':True,
                          'status':'same explicit entry set; not proof of global execution order','authority':'static-inference',
                          'locations':row['locations']})
        questions = [
            {'id':'purpose','text_it':'Quale obiettivo deve raggiungere questa operazione?','text_en':'What goal should this operation achieve?'},
            {'id':'actor','text_it':'Chi può eseguire questa operazione e con quali permessi?','text_en':'Who may perform this operation, and with which permissions?'},
            {'id':'acceptance','text_it':'Quale risultato atteso indipendente permette di verificare questa operazione?','text_en':'Which independent expected result can verify this operation?'}]
        row = {'id':identifier,'kind':'recovered-operation','authority':'static-inference',
               'basis_profiles':{key:model.get(key) for key in ('behavior_profile','narrative_profile','behavior_parser_profiles','entry_selection_profile')},
               'name':' / '.join(dict.fromkeys(r['name'] for r in rows)), 'entry_points':list(entries),
               'behavior_refs':[r['id'] for r in rows], 'behavior_summaries':sources,
               'entity_refs':sorted({ref for r in rows for ref in r['entity_refs']}),
               'locations':locations, 'inputs':[{'behavior_ref':r['id'],'declared':r.get('inputs')} for r in rows],
               'supported_steps':steps[:60], 'omitted_steps':max(0,len(steps)-60), 'questions':questions,
               'flow_limits':list(dict.fromkeys(limit for r in rows for limit in r['flow_limits'])),
               'coverage':{'status':'partial','method':'explicit-entry-operations/2',
                           'grouping':'identical nonempty entry-point sets only',
                           'step_order':'syntax locations only; global execution order and runtime satisfaction unverified'}}
        scopes = {r.get('entry_scope') for r in rows}
        if len(scopes) == 1 and scopes <= {'lexical-local', 'package-local', 'implementation-local', 'conditional-local'}:
            row['entry_scope'] = next(iter(scopes))
            row['entry_visibility'] = rows[0]['entry_visibility']
        row['coverage']['method'] = 'explicit-entry-operations/4'
        row['record_digest']=digest(row)
        operations.append(row)
    return operations, links
