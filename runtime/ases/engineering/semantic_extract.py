"""Optional offline GLiNER2 requirement suggestions in an owned subprocess."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from time import monotonic

SCHEMA = 'ases-local-interpretation/1.0'
LABELS = ('functional requirement', 'nonfunctional requirement', 'not a requirement')


def _load_model(snapshot_path):
    from .service import load_model
    return load_model(snapshot_path)


def _model_fingerprint(directory):
    """Hash the only accepted, non-pickle local model files by content."""
    directory = Path(directory)
    required = {'config.json', 'model.safetensors'}
    allowed = required | {'README.md', 'added_tokens.json', 'special_tokens_map.json',
                          'spm.model', 'tokenizer_config.json', 'tokenizer.json',
                          'encoder_config'}
    entries = {p.name: p for p in directory.iterdir()}
    extras = set(entries) - allowed
    if (not required.issubset(entries) or
            any(not re.fullmatch(r'[A-Za-z0-9._-]{1,80}-manifest\.json', name, re.I) or
                entries[name].is_symlink() or not entries[name].is_file() or
                entries[name].stat().st_size > 64 * 1024 for name in extras) or len(extras) > 1):
        raise ValueError('Directory modello non valida: file non ammesso o pesi/config mancanti.')
    if 'encoder_config' in entries:
        encoder_dir = entries['encoder_config']
        if encoder_dir.is_symlink() or not encoder_dir.is_dir() or {p.name for p in encoder_dir.iterdir()} != {'config.json'}:
            raise ValueError('Directory encoder_config non valida.')
    h = hashlib.sha256()
    for name in sorted(required):
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('File modello non valido.')
        size = path.stat().st_size
        maximum = 1024 * 1024 if name == 'config.json' else 8 * 1024**3
        if not size or size > maximum:
            raise ValueError('Dimensione file modello non valida.')
        h.update(name.encode() + b'\0' + str(size).encode() + b'\0')
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(chunk)
    return h.hexdigest()


def _sentences(model, limit):
    rows, omissions = [], 0
    for source in model.get('sources', []):
        fence = None
        headings = []
        for unit in source.get('units', []):
            raw = unit.get('text', '')
            if not isinstance(raw, str):
                continue
            quote = raw.strip()
            # Keep extraction atomic at the source-unit boundary. Do not split
            # punctuation (e.g. 99.9%, abbreviations) or silently truncate tokens.
            if not quote:
                continue
            is_heading, level, heading = _markdown_heading(quote)
            if is_heading:
                headings = [(depth, title) for depth, title in headings if depth < level]
                headings.append((level, heading))
            in_example_section = any(_is_example_heading(title) for _, title in headings)
            in_fence, next_fence = _fence_state(raw, fence)
            skip = is_heading or in_fence or in_example_section or len(quote) > 2000 or _is_example_or_code(quote)
            fence = next_fence
            if skip:
                omissions += 1
                continue
            if len(rows) >= limit:
                omissions += 1
                continue
            rows.append({'id': 'excerpt:' + hashlib.sha256((source['id'] + quote).encode()).hexdigest()[:16],
                         'text': quote, 'source_text': raw,
                         'locations': [{'path': source['path'], 'sha256': source['sha256'], **{k: unit[k] for k in ('line','page','table','table_row','paragraph','sheet','row','element') if k in unit}}]})
    return rows, omissions


def _is_example_or_code(text):
    stripped = text.strip()
    low = stripped.lower()
    if '```' in stripped or stripped.startswith(('~~~', '<code', '<pre')):
        return True
    if low.startswith(('example:', 'for example:', 'e.g.', 'esempio:', 'ad esempio:')):
        return True
    if low.startswith(('```', '~~~')) or low.endswith(('```', '~~~')):
        return True
    return False


def _markdown_heading(text):
    match = re.match(r'^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$', text)
    return (True, len(match.group(1)), match.group(2).strip()) if match else (False, 0, '')


def _is_example_heading(text):
    return bool(re.search(r'\b(?:examples?|esempi|tutorial|templates?|modelli di esempio)\b', text, re.I))


def _fence_state(text, current):
    """Return whether a source unit contains/is within a Markdown code fence."""
    skip = current is not None
    for line in text.splitlines() or [text]:
        match = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if not match:
            if current is not None:
                skip = True
            continue
        marker = match.group(1)
        if current is None:
            current = marker[0]
            skip = True
        elif marker[0] == current and len(marker) >= 3:
            current = None
            skip = True
        else:
            skip = True
    return skip, current


def interpret(snapshot_path, *, python_executable, model_path, limit=40, timeout=120,
              min_available_memory=4 * 1024**3, log_path=None):
    """Return partial local hypotheses; source facts and snapshot remain untouched."""
    from .model import digest
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ValueError('Il limite deve essere compreso tra 1 e 200 frasi.')
    if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 900:
        raise ValueError('Il timeout deve essere compreso tra 0 e 900 secondi.')
    executable, model_dir = Path(python_executable), Path(model_path)
    model = _load_model(snapshot_path)
    sentences, omitted = _sentences(model, limit)
    if not executable.is_file() or not model_dir.is_dir():
        return {'schema':SCHEMA,'snapshot_id':model['snapshot_id'],'base_model_digest':model['model_digest'],
                'model':'GLiNER2 (percorso locale esplicito)','hypotheses':[],'sources':sentences,'omissions':omitted,
                'coverage':{'selected_excerpts':len(sentences),'documents_available':len(model['sources']),'status':'PARTIAL'},
                'provider':{'name':'GLiNER2','status':'unavailable','model_fingerprint':None},
                'failures':[{'reason':'Runtime Python o directory del modello locale non disponibili; nessun download avviato.'}],
                'limits':['Proposte automatiche da rivedere; non sono dichiarazioni approvate o verificate.']}
    if not sentences:
        return {'schema':SCHEMA,'snapshot_id':model['snapshot_id'],'base_model_digest':model['model_digest'],
                'model':'GLiNER2 (percorso locale esplicito)','hypotheses':[],'sources':[], 'omissions':0,
                'coverage':{'selected_excerpts':0,'documents_available':len(model['sources']),'status':'PARTIAL'},
                    'provider':{'name':'GLiNER2','status':'empty','model_fingerprint':None},
                'failures':[],'limits':['Proposte automatiche da rivedere; non sono dichiarazioni approvate o verificate.']}
    payload = {'sentences': [{'id':r['id'],'text':r['text']} for r in sentences], 'labels':list(LABELS),
               'model_path':str(model_dir.resolve()), 'min_available_memory':int(min_available_memory)}
    try:
        model_fingerprint = _model_fingerprint(model_dir)
    except (OSError, ValueError) as exc:
        return {'schema':SCHEMA,'snapshot_id':model['snapshot_id'],'base_model_digest':model['model_digest'],
                'model':'GLiNER2 (percorso locale esplicito)','hypotheses':[],'sources':sentences,'omissions':omitted,
                'coverage':{'selected_excerpts':len(sentences),'documents_available':len(model['sources']),'status':'PARTIAL'},
                'provider':{'name':'GLiNER2','status':'unavailable','model_fingerprint':None},
                'failures':[{'reason':str(exc)}], 'limits':['Proposte automatiche da rivedere; non sono dichiarazioni approvate o verificate.']}
    env = os.environ.copy()
    env.update({'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1',
                'TOKENIZERS_PARALLELISM':'false','HF_HUB_DISABLE_PROGRESS_BARS':'1'})
    started = monotonic()
    try:
        proc = subprocess.Popen([str(executable), '-I', '-B', str(Path(__file__).with_name('_semantic_worker.py'))],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding='utf-8', env=env, shell=False)
        try:
            stdout, stderr = proc.communicate(json.dumps(payload, ensure_ascii=False), timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.communicate()
            raise TimeoutError('Scaduto il tempo massimo del classificatore locale.')
        if log_path:
            Path(log_path).write_text(stderr[-16000:], encoding='utf-8')
        if len(stdout.encode('utf-8')) > 128 * 1024:
            raise ValueError('La risposta del worker supera il limite di dimensione.')
        if proc.returncode != 0:
            if 'Memoria disponibile sotto la soglia' in stderr:
                raise RuntimeError('Memoria disponibile insufficiente; modello non caricato e nessun download avviato.')
            raise RuntimeError('Il worker locale è terminato con errore; nessuna proposta accettata.')
        result = json.loads(stdout)
        if result.get('source_fingerprint') != digest(payload['sentences']):
            raise ValueError('Fingerprint delle frasi restituito dal worker non valido.')
        classifications = result.get('classifications')
        if not isinstance(classifications, list) or len(classifications) != len(sentences):
            raise ValueError('Risposta del worker incompleta o non valida.')
        if any(not isinstance(item, dict) for item in classifications):
            raise ValueError('Risposta del worker incompleta o non valida.')
    except (OSError, ValueError, RuntimeError, TimeoutError, json.JSONDecodeError) as exc:
        reason = str(exc)[:1000]
        return {'schema':SCHEMA,'snapshot_id':model['snapshot_id'],'base_model_digest':model['model_digest'],
                'model':'GLiNER2 (percorso locale esplicito)','hypotheses':[],'sources':sentences,'omissions':omitted,
                'coverage':{'selected_excerpts':len(sentences),'documents_available':len(model['sources']),'status':'PARTIAL'},
                'provider':{'name':'GLiNER2','status':'error','model_fingerprint':model_fingerprint},
                'failures':[{'reason':reason}], 'limits':['Proposte automatiche da rivedere; non sono dichiarazioni approvate o verificate.']}
    hypotheses=[]
    skipped = 0
    for row, prediction in zip(sentences, classifications):
        if prediction.get('skipped') is True:
            skipped += 1
            row['classification_status'] = 'skipped'
            row['classification_skip_reason'] = str(prediction.get('reason', 'token preflight failed'))[:200]
            continue
        if not isinstance(prediction, dict) or prediction.get('label') not in LABELS[:2]:
            continue
        quote = row['text']
        score = prediction.get('score')
        if isinstance(score, bool) or not isinstance(score, (int,float)) or not math.isfinite(score) or not 0 <= score <= 1:
            score = None
        hypotheses.append({'id':'hypothesis:'+hashlib.sha256((row['id']+prediction['label']).encode()).hexdigest()[:24],
            'kind':'functional' if prediction['label']==LABELS[0] else 'nonfunctional','state':'INFERRED',
            'authority':'local-model-hypothesis','statement':quote,'quote':quote,'source_ref':row['id'],
            'locations':row['locations'],'confidence':{'value':score,'meaning':'un-calibrated model score; human review required'}})
    return {'schema':SCHEMA,'snapshot_id':model['snapshot_id'],'base_model_digest':model['model_digest'],
            'model':'GLiNER2 (percorso locale esplicito)','seconds':round(monotonic()-started,3), 'hypotheses':hypotheses,
            'sources':sentences,'omissions':omitted + skipped,
            'coverage':{'selected_excerpts':len(sentences),'classifications_attempted':len(sentences) - skipped,
                        'documents_available':len(model['sources']),'status':'PARTIAL'},
            'provider':{'name':'GLiNER2','status':'ok','model_fingerprint':model_fingerprint,
                        'schema_fingerprint':hashlib.sha256(json.dumps(LABELS).encode()).hexdigest()},
            'failures':[],'limits':['Proposte automatiche da rivedere; non sono dichiarazioni approvate o verificate.',
                                     'Ogni unità sorgente oltre 2000 caratteri viene omessa; il preflight conta i token del testo senza troncamento e riserva 128 token al contesto dello schema.',
                                     'La riserva è un limite prudenziale per questa classificazione, non una garanzia universale sulla lunghezza del prompt interno.',
                                     'Nessuna inferenza dimostra autorità, soddisfacimento o correttezza semantica.']}
