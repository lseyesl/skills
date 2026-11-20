"""Content-bound validation receipts. Freshness is not proof of expert correctness."""
import hashlib
import json
from pathlib import Path


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def own_fingerprint(entry):
    semantic={k:v for k,v in entry.items() if not k.startswith('_') and k not in {'status','evidence','validated_for','path','skill','validation_state'}}
    semantic['content_sha256']=sha(entry['path'])
    semantic['routing']={key:entry.get(key,[]) for key in ('_query_exclusions','_context_exclusions','_domain_terms')}
    return hashlib.sha256(json.dumps(semantic,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def closure(entries,ident):
    seen=set()
    def visit(key):
        if key in seen:return
        seen.add(key)
        for child in entries[key]['requires']+entries[key]['verification']:visit(child)
    visit(ident);return seen


def snapshot(entries,ident,suite,tools):
    entry=entries[ident];folder=Path(entry['_skill_dir'])
    def local(relative):
        path=(folder/relative).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file():raise ValueError('Missing/escaping evidence input: '+relative)
        return path
    files={name:sha(local(name)) for name in [suite,*tools]}
    return {'schema_version':1,'knowledge_id':ident,'knowledge_fingerprints':{key:own_fingerprint(entries[key]) for key in sorted(closure(entries,ident))},
            'file_fingerprints':files,'suite':suite,'tools':tools,'scope':{},'checks':{},'reviewer':None,'verdict':'unknown'}


def receipt_state(entries,ident):
    entry=entries[ident]
    if entry['status']!='validated':return 'experimental'
    folder=Path(entry['_skill_dir'])
    reasons=[]
    for relative in entry.get('evidence',[]):
        try:
            report=json.loads((folder/relative).read_text())
            if report.get('schema_version')!=1 or report.get('knowledge_id')!=ident:raise ValueError('receipt identity/schema')
            if not isinstance(report.get('checks'),dict):raise ValueError('invalid checks')
            if report.get('verdict')!='passed' or not report.get('reviewer') or not report.get('checks') or not all(v is True for v in report['checks'].values()):raise ValueError('unreviewed/incomplete checks')
            if report.get('scope')!=entry.get('validated_for'):raise ValueError('scope mismatch')
            current=snapshot(entries,ident,report['suite'],report['tools'])
            for key in ('knowledge_fingerprints','file_fingerprints'):
                if report.get(key)!=current[key]:raise ValueError('changed '+key)
            if not set(entry.get('tool_dependencies',[])) <= set(report['tools']):raise ValueError('missing tool dependency')
        except (ValueError,KeyError,OSError,TypeError) as exc:reasons.append(str(exc))
    return 'fresh' if entry.get('evidence') and not reasons else 'stale: '+ '; '.join(reasons or ['no evidence'])
