"""Portable standard-library knowledge search; usable from a locked Skill copy."""
import argparse
import json
from pathlib import Path
import re

KINDS = {'overview', 'knowledge', 'procedure', 'acceptance', 'style'}
TASKS = {'create', 'inspect', 'repair', 'optimize', 'animate', 'export', 'query', 'convert', 'produce', 'install'}


def strings(value, label, nonempty=False):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value) or (nonempty and not value):
        raise ValueError('Expected string list: ' + label)
    return value


def load_catalog(skills_dir):
    skills_dir = Path(skills_dir).resolve()
    entries = {}
    for manifest in sorted(skills_dir.glob('*/knowledge.json')):
        data = json.loads(manifest.read_text(encoding='utf-8'))
        if data.get('schema_version') != 1 or not isinstance(data.get('entries'), list):
            raise ValueError('Invalid knowledge manifest: ' + str(manifest))
        exclusions = strings(data.get('query_exclusions', []), 'query_exclusions')
        owner = manifest.parent.name
        for item in data['entries']:
            ident = item.get('id', '')
            if not re.fullmatch(r'[a-z0-9][a-z0-9.-]+', ident) or ident in entries:
                raise ValueError('Invalid/duplicate knowledge ID: ' + ident)
            if item.get('kind') not in KINDS or item.get('status') not in {'experimental', 'validated', 'deprecated'}:
                raise ValueError('Invalid kind/status: ' + ident)
            for field in ('title', 'entry'):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    raise ValueError('Missing ' + field + ': ' + ident)
            for field in ('tasks', 'subjects', 'aliases', 'applies_when', 'exclude_when', 'requires', 'verification', 'required_facts'):
                strings(item.get(field), ident + '.' + field, field in {'tasks', 'applies_when'})
            if not set(item['tasks']) <= TASKS:
                raise ValueError('Unknown task: ' + ident)
            conditions = item.get('conditions', {})
            if not isinstance(conditions, dict) or any(not isinstance(k, str) or type(v) not in (str, bool, int, float) for k, v in conditions.items()):
                raise ValueError('Invalid applicability conditions: ' + ident)
            path = (manifest.parent / item['entry']).resolve()
            if not path.is_relative_to(manifest.parent) or not path.is_file() or 'history' in path.relative_to(manifest.parent).parts:
                raise ValueError('Missing/escaping/retired knowledge file: ' + ident)
            if item['status'] == 'validated':
                if not item.get('validated_for') or not item.get('evidence'):
                    raise ValueError('Validated knowledge needs scope and evidence: ' + ident)
                for evidence in strings(item['evidence'], ident + '.evidence', True):
                    ep = (manifest.parent / evidence).resolve()
                    if not ep.is_relative_to(manifest.parent) or not ep.is_file():
                        raise ValueError('Missing validation evidence: ' + ident)
            entries[ident] = {**item, 'skill': owner, 'path': str(path), '_query_exclusions': exclusions}
    return entries


def validate_catalog(root):
    root = Path(root)
    registry = json.loads((root / 'skills.json').read_text(encoding='utf-8'))['skills']
    taxonomy = json.loads((root / 'catalog/taxonomy.json').read_text(encoding='utf-8'))
    if taxonomy.get('schema_version') != 1:
        raise ValueError('Invalid taxonomy version')
    members = [s for group in taxonomy['groups'].values() for s in group]
    if len(members) != len(set(members)) or set(members) != set(registry):
        raise ValueError('Taxonomy must classify every Skill exactly once')
    entries = load_catalog(root / 'skills')
    if {e['skill'] for e in entries.values()} != set(registry):
        raise ValueError('Every Skill needs a knowledge entry')
    def closure(owner):
        result = set()
        def visit(s):
            if s in result: return
            result.add(s)
            for dep in registry[s].get('requires', []): visit(dep)
        visit(owner)
        return result
    for ident, entry in entries.items():
        for dep in entry['requires'] + entry['verification']:
            if dep not in entries: raise ValueError('Unknown knowledge reference: ' + dep)
            if entries[dep]['skill'] not in closure(entry['skill']):
                raise ValueError('Required knowledge crosses undeclared required Skill dependency: ' + ident)
    visiting, done = set(), set()
    def visit(ident):
        if ident in visiting: raise ValueError('Knowledge dependency cycle: ' + ident)
        if ident in done: return
        visiting.add(ident)
        for dep in entries[ident]['requires']: visit(dep)
        visiting.remove(ident); done.add(ident)
    for ident in entries: visit(ident)
    return {'entries': len(entries), 'groups': len(taxonomy['groups'])}


def tokens(text):
    # English identifiers + Chinese bigrams (no dependency on a segmenter).
    lowered = text.lower()
    words = re.findall(r'[a-z0-9]+', lowered)
    for run in re.findall(r'[\u4e00-\u9fff]+', lowered):
        words.extend(run[i:i+2] for i in range(max(1, len(run)-1)))
    return set(words)


def search(entries, query, task=None, subject=None, facts=None, limit=5):
    if task is not None and task not in TASKS: raise ValueError('Unknown task: ' + task)
    if facts is not None and not isinstance(facts, dict): raise ValueError('facts must be a mapping')
    if type(limit) is not int or limit < 1: raise ValueError('limit must be a positive integer')
    facts = {k: v for k, v in (facts or {}).items() if v is not None}
    query_terms = tokens(query)
    results = []
    for entry in entries.values():
        if entry['status'] == 'deprecated' or (task and task not in entry['tasks']) or (subject and subject not in entry['subjects']): continue
        if any(tokens(phrase) and tokens(phrase) <= query_terms for phrase in entry.get('_query_exclusions', [])): continue
        # Explicit facts are hard exclusions; absent facts remain pending checks.
        if any((type(facts[k]) is not type(v) or facts[k] != v) for k, v in entry.get('conditions', {}).items() if k in facts): continue
        terms = tokens(' '.join([entry['title'], *entry['aliases'], *entry['subjects']]))
        matches = sorted(query_terms & terms)
        if not matches: continue
        missing = sorted(set(entry['required_facts']) - facts.keys())
        results.append({'id': entry['id'], 'skill': entry['skill'], 'entry': entry['entry'], 'title': entry['title'],
                        'score': len(matches), 'matched_terms': matches, 'applies_when': entry['applies_when'],
                        'exclude_when': entry['exclude_when'], 'missing_facts': missing,
                        'readiness': 'needs-inspection' if missing else 'check-applicability', 'status': entry['status']})
    priority = {'procedure': 0, 'style': 1, 'knowledge': 2, 'overview': 3, 'acceptance': 4}
    return sorted(results, key=lambda e: (-e['score'], priority[entries[e['id']]['kind']], e['id']))[:limit]


def impacts(entries, ident):
    if ident not in entries: raise ValueError('Unknown knowledge ID: ' + ident)
    affected = {ident}
    while True:
        added = {key for key, entry in entries.items() if set(entry['requires'] + entry['verification']) & affected}
        if added <= affected: break
        affected.update(added)
    return sorted(affected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skills-dir', type=Path, default=Path(__file__).resolve().parents[2])
    sub = parser.add_subparsers(dest='action', required=True)
    q = sub.add_parser('search'); q.add_argument('query'); q.add_argument('--task', choices=sorted(TASKS)); q.add_argument('--subject'); q.add_argument('--facts', default='{}')
    r = sub.add_parser('retrieve'); r.add_argument('id')
    impact = sub.add_parser('impacts'); impact.add_argument('id')
    args = parser.parse_args(); entries = load_catalog(args.skills_dir)
    if args.action == 'search':
        facts = json.loads(args.facts)
        if not isinstance(facts, dict): parser.error('--facts must be a JSON object')
        print(json.dumps(search(entries, args.query, args.task, args.subject, facts), ensure_ascii=False, indent=2))
    elif args.action == 'impacts':
        print(json.dumps(impacts(entries, args.id), ensure_ascii=False, indent=2))
    else:
        if args.id not in entries: parser.error('Unknown/uninstalled knowledge ID')
        item = entries[args.id]
        print(json.dumps({k: item[k] for k in ('id', 'status', 'applies_when', 'exclude_when', 'requires', 'verification')}, ensure_ascii=False))
        print(Path(item['path']).read_text(encoding='utf-8'))

if __name__ == '__main__': main()
