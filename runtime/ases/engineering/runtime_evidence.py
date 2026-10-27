"""Correlate supplied HTTP observations, without executing or probing the target."""
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit

from .model import digest
from .service import read_json
from ..semantic_diff import load_context

SCHEMA='ases-http-observations/1.0'


def template(snapshot):
    context=load_context(snapshot,max_bytes=256*1024*1024)
    return {'schema':SCHEMA,'snapshot_id':context['snapshot_id'],
            'source_digest':digest(sorted((r['path'],r['sha256']) for r in context['source_manifest'])),
            'collector':{'name':'REPLACE_WITH_COLLECTOR','independent':False},
            'captured_at':datetime.now(timezone.utc).isoformat(),'environment':{},
            'coverage':{'status':'PARTIAL','scope':'Supplied HTTP requests only'},'observations':[]}


def correlate(snapshot, supplied):
    context=load_context(snapshot,max_bytes=256*1024*1024);expected=template(snapshot)
    if isinstance(supplied,(str,Path)):supplied=read_json(supplied,4*1024*1024)
    if not isinstance(supplied,dict) or supplied.get('schema')!=SCHEMA:
        raise ValueError('Unsupported HTTP observation schema.')
    if any(supplied.get(k)!=expected[k] for k in ('snapshot_id','source_digest')):
        raise ValueError('HTTP observations refer to a different snapshot or source digest.')
    if (not isinstance(supplied.get('collector'),dict) or not supplied['collector'].get('name')
            or not isinstance(supplied.get('environment'),dict) or not isinstance(supplied.get('coverage'),dict)
            or supplied['coverage'].get('status') not in {'PARTIAL','UNKNOWN','ANALYZED'}):
        raise ValueError('HTTP observations need collector, environment and coverage provenance.')
    try:
        stamp=datetime.fromisoformat(supplied['captured_at'].replace('Z','+00:00'))
        if stamp.tzinfo is None:raise ValueError()
    except (KeyError,ValueError,TypeError,AttributeError):raise ValueError('Capture time must include a timezone.') from None
    rows=supplied.get('observations')
    if not isinstance(rows,list) or len(rows)>1000:raise ValueError('At most 1000 HTTP observations are supported.')
    routes=[e for e in context['entities'] if e['kind']=='route']
    bindings={e['id'] for e in context['entities']}
    matches=[]
    for row in rows:
        if not isinstance(row,dict):raise ValueError('Malformed HTTP observation.')
        method,path,status=row.get('method'),row.get('path'),row.get('status')
        if (method not in {'GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'} or not isinstance(path,str)
                or not path.startswith('/') or path.startswith('//') or len(path)>2048
                or urlsplit(path).query or urlsplit(path).fragment or any(ord(c)<32 for c in path)
                or type(status) is not int or not 100<=status<=599):
            raise ValueError('HTTP observations need a literal method/path without credentials, query or fragment and a valid status.')
        handler=row.get('handler_entity_ref')
        if handler is not None and handler not in bindings:raise ValueError('Observed handler is not in this snapshot.')
        candidates=[]
        for entity in routes:
            props=entity.get('properties',{})
            if props.get('http_method')!=method:continue
            if props.get('match_kind')=='prefix':
                match=path.startswith(props.get('path_prefix','\x00'))
            else:match=props.get('path')==path
            if match:candidates.append(entity)
        if handler is not None:
            selected=[e for e in candidates if e.get('properties',{}).get('handler')==handler]
            state='handler-correlated' if selected else 'binding-not-reconstructed'
        else:
            selected=candidates
            state='candidate' if len(selected)==1 else 'ambiguous' if selected else 'dynamic-or-unreconstructed'
        matches.append({'method':method,'path':path,'status':status,'handler_entity_ref':handler,
                        'state':state,'candidate_refs':[e['id'] for e in selected],
                        'authority':'imported-runtime-observation','execution_verified_by_ases':False})
    return {'schema':'ases-http-correlation/1.0','snapshot_id':context['snapshot_id'],
            'provenance':{k:supplied[k] for k in ('collector','environment','captured_at','coverage')},
            'matches':matches,'counts':{state:sum(m['state']==state for m in matches)
                for state in ('handler-correlated','candidate','ambiguous','binding-not-reconstructed','dynamic-or-unreconstructed')},
            'limits':['Imported observations are supplied evidence, not independently verified executions.',
                      'No requests, target code, build or tests executed by this operation.',
                      'Unobserved routes are not absent or broken. Candidate overlap does not determine dispatch order.',
                      'Dynamic observations remain separate from the immutable static snapshot.']}
