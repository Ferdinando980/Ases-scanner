"""Review suggestions, never automatic identity migration or semantic equivalence."""
from __future__ import annotations

from collections import defaultdict
import re

COLLECTIONS = ('requirements', 'recovered_requirements', 'api', 'scenarios', 'test_cases', 'operations', 'user_requirements')
POSITION_KEYS = {'id', 'record_digest', 'fact_id', 'fact_refs', 'entity_ref', 'entity_refs',
                 'line', 'locations', 'sha256', 'behavior_ref', 'behavior_refs'}


def supported(value):
    if isinstance(value, dict):
        return {k: supported(v) for k, v in value.items() if k not in POSITION_KEYS}
    if isinstance(value, list):
        return [supported(v) for v in value]
    if isinstance(value, str):
        # Formatting outside quoted literals only. This is not a program-equivalence solver.
        return re.findall(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_$À-ÿ][\w$À-ÿ]*|\d+|[^\s]', value)
    return value


def review_changes(before, after, field_selector):
    old = {r['id']: (collection, r) for collection in COLLECTIONS for r in before.get(collection, [])}
    new = {r['id']: (collection, r) for collection in COLLECTIONS for r in after.get(collection, [])}
    pairs = [(key, key, 'same-id') for key in sorted(old.keys() & new.keys())]
    remaining_old, remaining_new = set(old) - set(new), set(new) - set(old)
    ambiguous = []

    def key(item, include_path):
        collection, row = item
        name = row.get('qualified_name') or row.get('declared_id') or row.get('name')
        if not name:
            return None
        paths = tuple(sorted({loc['path'] for loc in row.get('locations', [])})) if include_path else ()
        return collection, row.get('kind'), name, paths

    for include_path in (True, False):
        groups_old, groups_new = defaultdict(list), defaultdict(list)
        for identifier in sorted(remaining_old):
            if (identity := key(old[identifier], include_path)) is not None: groups_old[identity].append(identifier)
        for identifier in sorted(remaining_new):
            if (identity := key(new[identifier], include_path)) is not None: groups_new[identity].append(identifier)
        for identity in sorted(groups_old.keys() & groups_new.keys(), key=str):
            left, right = groups_old[identity], groups_new[identity]
            if len(left) == len(right) == 1:
                pairs.append((left[0], right[0], 'candidate-same-declaration' if include_path else 'candidate-relocation'))
                remaining_old.remove(left[0]); remaining_new.remove(right[0])
            elif not include_path:
                ambiguous.append({'before': left[:20], 'after': right[:20], 'candidate_count': len(left) * len(right),
                                  'status': 'ambiguous; manual review required'})
    changes = []
    for left, right, basis in pairs:
        a, b = old[left][1], new[right][1]
        fields_a, fields_b = field_selector(a), field_selector(b)
        reasons = []
        if supported(fields_a) != supported(fields_b):
            reasons.append('supported-content-changed')
            for field, reason in (('signature', 'signature-changed'), ('scope', 'requirement-scope-changed'),
                                  ('user_context', 'human-context-changed'), ('statement', 'statement-changed')):
                if supported(a.get(field)) != supported(b.get(field)): reasons.append(reason)
            if any(supported(a.get(k)) != supported(b.get(k)) for k in ('conditions', 'external_outcomes', 'effects', 'errors')):
                reasons.append('supported-behavior-changed')
        elif a.get('record_digest') != b.get('record_digest') or left != right:
            reasons.append('supported-content-unchanged; inspect-source-or-formatting')
        locations_a, locations_b = a.get('locations', []), b.get('locations', [])
        if [{k:v for k,v in loc.items() if k != 'sha256'} for loc in locations_a] != [{k:v for k,v in loc.items() if k != 'sha256'} for loc in locations_b]:
            reasons.append('source-position-or-path-changed')
        if reasons:
            changes.append({'before_id': left, 'after_id': right, 'basis': basis, 'reasons': reasons,
                            'name': b.get('qualified_name') or b.get('declared_id') or b.get('name') or right,
                            'review': 'required; no annotation automatically transferred' if basis != 'same-id' else 'inspect changed support'})
    def source_hashes(model):
        result = defaultdict(set)
        for source in model.get('sources', []): result[source['path']].add(source['sha256'])
        for collection in COLLECTIONS:
            for row in model.get(collection, []):
                for loc in row.get('locations', []): result[loc['path']].add(loc['sha256'])
        return result
    sources_a, sources_b = source_hashes(before), source_hashes(after)
    scope_a, scope_b = before.get('analysis_scope'), after.get('analysis_scope')
    return {'record_changes': changes, 'ambiguous_matches': ambiguous,
            'source_changes': sorted(p for p in sources_a.keys() | sources_b.keys() if sources_a[p] != sources_b[p]),
            'configured_scope_changed': None if scope_a is None or scope_b is None else
                {k:v for k,v in scope_a.items() if k != 'source_paths'} != {k:v for k,v in scope_b.items() if k != 'source_paths'},
            'source_set_changed': None if scope_a is None or scope_b is None else scope_a.get('source_paths') != scope_b.get('source_paths'),
            'scope_comparison': 'unknown for legacy models without recorded analysis scope' if scope_a is None or scope_b is None else 'recorded scope only',
            'identity_policy': 'Candidates are review aids. Missing records remain missing; no resolution or semantic equivalence is inferred.'}
