"""Private subprocess entry point. Input/output are bounded JSON only."""
import hashlib
import json
import os
import re
import sys
from pathlib import Path


_MODEL_FILES = {'config.json', 'model.safetensors', 'README.md', 'added_tokens.json',
                'special_tokens_map.json', 'spm.model', 'tokenizer_config.json',
                'tokenizer.json', 'encoder_config'}
_SCHEMA_TOKEN_RESERVE = 128


def _valid_model_directory(model_dir):
    entries = {p.name: p for p in model_dir.iterdir()}
    extras = set(entries) - _MODEL_FILES
    if (not {'config.json', 'model.safetensors'}.issubset(entries) or
            any(not re.fullmatch(r'[A-Za-z0-9._-]{1,80}-manifest\.json', name, re.I) or
                entries[name].is_symlink() or not entries[name].is_file() or
                entries[name].stat().st_size > 64 * 1024 for name in extras) or len(extras) > 1 or
            any((model_dir / name).is_symlink() or not (model_dir / name).is_file()
                for name in ('config.json', 'model.safetensors'))):
        return False
    if 'encoder_config' in entries:
        encoder_dir = entries['encoder_config']
        if encoder_dir.is_symlink() or not encoder_dir.is_dir() or {p.name for p in encoder_dir.iterdir()} != {'config.json'}:
            return False
    return True


def _token_preflight(tokenizer, text, max_tokens, reserved_tokens=_SCHEMA_TOKEN_RESERVE):
    """Count full text tokens without truncation, reserving room for schema tokens."""
    encoded = tokenizer(text, truncation=False, add_special_tokens=True)
    input_ids = encoded['input_ids']
    if input_ids and isinstance(input_ids[0], list):
        if len(input_ids) != 1:
            raise ValueError('Tokenizer returned unexpected batch output.')
        input_ids = input_ids[0]
    count = len(input_ids)
    text_budget = max_tokens - reserved_tokens
    if count > text_budget:
        return False, f'text token limit exceeded with {reserved_tokens} schema tokens reserved ({count}>{text_budget}; encoder limit {max_tokens})'
    return True, None


def main():
    raw = sys.stdin.buffer.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Input exceeds limit')
    request = json.loads(raw)
    sentences, labels = request['sentences'], request['labels']
    if len(sentences) > 200 or len(labels) != 3 or any(len(row.get('text','')) > 2000 for row in sentences):
        raise ValueError('Invalid bounded input')
    try:
        import psutil
        available = psutil.virtual_memory().available
    except ImportError:
        available = 0
    if available < request['min_available_memory']:
        raise MemoryError('Memoria disponibile sotto la soglia configurata; modello non caricato.')
    model_dir = Path(request['model_path'])
    entries = {p.name: p for p in model_dir.iterdir()}
    if not _valid_model_directory(model_dir):
        raise ValueError('Directory modello non valida; file non ammesso o config/pesi mancanti.')
    import torch
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    from gliner2 import GLiNER2
    model = GLiNER2.from_pretrained(str(model_dir), map_location='cpu', local_files_only=True,
                                    attention_backend='standard')
    model.eval()
    tokenizer = model.processor.tokenizer
    model_limit = getattr(tokenizer, 'model_max_length', None)
    encoder_limit = getattr(getattr(getattr(model, 'encoder', None), 'config', None),
                            'max_position_embeddings', None)
    limits = [v for v in (model_limit, encoder_limit) if isinstance(v, int) and 0 < v < 1_000_000]
    if not limits:
        raise ValueError('Limite token encoder non disponibile; nessun testo classificato.')
    max_tokens = min(limits)
    output = []
    schema = {'requirement_type': labels}
    with torch.inference_mode():
        for row in sentences:
            allowed, reason = _token_preflight(tokenizer, row['text'], max_tokens)
            if not allowed:
                output.append({'skipped': True, 'reason': reason})
                continue
            answer = model.classify_text(row['text'], schema, include_confidence=True)
            value = answer.get('requirement_type') if isinstance(answer, dict) else None
            if isinstance(value, dict):
                label = value.get('label') or value.get('classification')
                score = value.get('confidence', value.get('score'))
            else:
                label, score = value, None
            output.append({'skipped': False, 'label': label, 'score': score})
    print(json.dumps({'source_fingerprint': hashlib.sha256(json.dumps(sentences, sort_keys=True, ensure_ascii=False, separators=(',',':')).encode()).hexdigest(),
                      'classifications': output}, ensure_ascii=False, separators=(',',':')))


if __name__ == '__main__':
    main()
