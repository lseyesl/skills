"""Portable asset and skill management. Python 3.10+, hf CLI for transfers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor

MEDIA = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tif', '.tiff', '.svg', '.exr', '.hdr', '.mp3', '.wav', '.ogg', '.flac', '.m4a', '.mp4', '.mov', '.mkv', '.webm', '.avi', '.blend', '.fbx', '.glb', '.gltf', '.obj', '.zip', '.7z', '.pdf', '.ttf', '.otf'}
SKIP = {'.git', '.codex', '.agents', '.tmp', '__pycache__', '.venv', '.godot', '.space', 'node_modules'}

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def safe(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    if p == root.resolve() or root.resolve() not in p.parents:
        raise ValueError(f'Path escapes root: {rel}')
    return p

def files(root: Path):
    return sorted((p for p in root.rglob('*') if p.is_file() and not any(x in SKIP for x in p.relative_to(root).parts)), key=lambda p: p.relative_to(root).as_posix())

def tree(root: Path) -> str:
    h = hashlib.sha256()
    for p in files(root):
        h.update((p.relative_to(root).as_posix() + '\0' + digest(p) + '\n').encode())
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.partial')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)

def run(*args):
    subprocess.run([str(x) for x in args], check=True)

def asset_verify(root, lock):
    errors = []
    seen = set()
    for a in lock['assets']:
        p = safe(root, a['path'])
        if a['path'] in seen:
            raise ValueError('Duplicate asset path')
        seen.add(a['path'])
        if not p.is_file() or p.stat().st_size != a['size'] or digest(p) != a['sha256']:
            errors.append(a['path'])
    if errors:
        raise ValueError('Missing or corrupt assets: ' + ', '.join(errors))
    return len(seen)

def asset_transfer(root, lock, mode):
    prefix = f"hf://buckets/{lock['bucket']}/{lock['repository_id']}/objects/"
    root.joinpath('.tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='assets-', dir=root / '.tmp') as temp:
        stage = Path(temp)
        if mode == 'push':
            asset_verify(root, lock)
            for a in lock['assets']:
                if not a['uri'].startswith(prefix):
                    raise ValueError('Asset outside repository namespace')
                name = a['uri'][len(prefix):]
                if name != a['sha256'] + Path(a['path']).suffix.lower():
                    raise ValueError('Object key must be content addressed')
                shutil.copyfile(safe(root, a['path']), safe(stage, name))
            if lock['assets']:
                run('hf', 'buckets', 'sync', str(stage), prefix)
            # A successful upload alone is insufficient: read back the bytes.
        else:
            # Preserve edited working files; pull never silently overwrites them.
            for a in lock['assets']:
                p = safe(root, a['path'])
                if p.exists() and digest(p) != a['sha256']:
                    raise ValueError('Locally modified asset: ' + a['path'])
        # Fetch only manifest objects, not all historical objects in the bucket.
        by_uri = {a['uri']: a for a in lock['assets']}
        def fetch(item):
            i, (uri, a) = item
            if not uri.startswith(prefix):
                raise ValueError('Asset outside repository namespace')
            dest = stage / ('verify-' + str(i))
            run('hf', 'buckets', 'cp', uri, str(dest), '--quiet')
            if dest.stat().st_size != a['size'] or digest(dest) != a['sha256']:
                raise ValueError('Remote checksum mismatch: ' + uri)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(fetch, enumerate(by_uri.items())))
        if mode == 'pull':
            verified = {uri: stage / ('verify-' + str(i)) for i, uri in enumerate(by_uri)}
            for a in lock['assets']:
                p = safe(root, a['path'])
                if p.exists():
                    continue
                p.parent.mkdir(parents=True, exist_ok=True)
                partial = p.with_name(p.name + '.partial')
                shutil.copyfile(verified[a['uri']], partial)
                os.replace(partial, p)
    print(f"ASSETS_{mode.upper()}_OK {len(lock['assets'])}")

def assets(args):
    root = Path(args.project).resolve()
    policy_path = root / 'assets.config.json'
    if not policy_path.is_file():
        raise ValueError('HF assets are enabled only in explicitly configured production repositories; skills and Obsidian stay in Git')
    policy = read(policy_path)
    if not policy.get('enabled') or policy.get('repository_id') in {'skills', 'obsidian_note'}:
        raise ValueError('This repository does not use HF asset storage')
    path = root / 'assets.lock.json'
    def checked_lock(lock_path):
        lock = read(lock_path)
        if (lock.get('repository_id'), lock.get('bucket')) != (policy['repository_id'], policy['bucket']):
            raise ValueError('Asset manifest namespace differs from repository policy')
        return lock
    if args.action == 'index':
        if args.repository_id != policy['repository_id'] or args.bucket != policy['bucket']:
            raise ValueError('Repository/bucket differs from assets.config.json')
        previous = read(path) if path.exists() else {'assets': []}
        old = {a['path']: a for a in previous['assets']}
        excluded = previous.get('excluded_roots', [])
        result = []
        for p in files(root):
            if p.relative_to(root).parts[0] in excluded:
                continue
            if p.suffix.lower() not in MEDIA:
                continue
            rel, sha = p.relative_to(root).as_posix(), digest(p)
            before = old.get(rel, {})
            if before.get('sha256') != sha and before.get('status') in {'approved', 'locked'}:
                raise ValueError('Approved asset changed in place; create a new version: ' + rel)
            result.append({'asset_id': before.get('asset_id', rel), 'project_id': rel.split('/')[1] if rel.startswith('projects/') else 'shared', 'path': rel, 'sha256': sha, 'size': p.stat().st_size, 'version': sha, 'status': before.get('status', 'unreviewed'), 'uri': f'hf://buckets/{args.bucket}/{args.repository_id}/objects/{sha}{p.suffix.lower()}'})
        # Pending is promoted only by push after verified upload.
        write(root / 'assets.pending.json', {'schema_version': 1, 'bucket': args.bucket, 'repository_id': args.repository_id, 'excluded_roots': excluded, 'assets': result})
        print('ASSETS_INDEX_PENDING', len(result))
    elif args.action == 'push':
        pending = root / 'assets.pending.json'
        lock = checked_lock(pending if pending.exists() else path)
        asset_transfer(root, lock, 'push')
        write(path, lock)
        pending.unlink(missing_ok=True)
    elif args.action == 'pull':
        asset_transfer(root, checked_lock(path), 'pull')
    else:
        print('ASSETS_VERIFY_OK', asset_verify(root, checked_lock(path)))

def skills(args):
    root = Path(args.project).resolve()
    lock_path = root / 'skills.lock.json'
    lock = read(lock_path)
    source = Path(args.source or os.environ.get('ANCIENT_TALES_SKILLS_SOURCE', '')).resolve()
    if not (source / '.git').exists():
        raise ValueError('Set --source or ANCIENT_TALES_SKILLS_SOURCE to the skills repository')
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True, encoding='utf-8').strip()
    if args.action == 'update':
        for s in lock['skills']:
            src = safe(source, s['directory'])
            if not (src / 'SKILL.md').is_file():
                raise ValueError('Missing skill entry: ' + s['name'])
            s['source_commit'] = commit
            s['tree_sha256'] = tree(src)
            changed = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=all', '--', s['directory']], text=True, encoding='utf-8')
            s['source_state'] = 'working-tree' if changed.strip() else 'committed'
        write(lock_path, lock)
        print('SKILLS_LOCK_UPDATED; install explicitly to activate')
        return
    install_root = root / '.agents' / 'skills'
    receipts_path = root / '.agents' / 'skills-receipts.json'
    receipts = read(receipts_path) if receipts_path.exists() else {}
    for s in lock['skills']:
        dest = safe(install_root, s['name'])
        if dest.exists() and tree(dest) != receipts.get(s['name']):
            raise ValueError('Locally modified/unmanaged installed skill: ' + s['name'])
        if args.action == 'check':
            if not dest.exists() or tree(dest) != s['tree_sha256']:
                raise ValueError('Missing or outdated skill: ' + s['name'])
    # Validate every source before modifying any installation.
    if args.action == 'install':
        for s in lock['skills']:
            src = safe(source, s['directory'])
            if tree(src) != s['tree_sha256']:
                raise ValueError('Source differs from locked tree: ' + s['name'])
            # Verify the recorded commit exists; source tree hash allows explicit
            # uncommitted locks without falsely claiming they are in Git.
            subprocess.run(['git', '-C', str(source), 'cat-file', '-e', s['source_commit'] + '^{commit}'], check=True)
            if s.get('source_state') == 'committed':
                expected = subprocess.check_output(['git', '-C', str(source), 'rev-parse', s['source_commit'] + ':' + s['directory']], text=True, encoding='utf-8').strip()
                actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD:' + s['directory']], text=True, encoding='utf-8').strip()
                if expected != actual:
                    raise ValueError('Checkout locked source commit first: ' + s['name'])
        install_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='skills-', dir=root / '.agents') as temp:
            stage = Path(temp)
            for s in lock['skills']:
                shutil.copytree(safe(source, s['directory']), stage / s['name'], ignore=shutil.ignore_patterns(*SKIP))
            backups, installed = [], []
            try:
                for s in lock['skills']:
                    dest = safe(install_root, s['name'])
                    if dest.exists():
                        backup = stage / ('backup-' + s['name'])
                        os.replace(dest, backup)
                        backups.append((dest, backup))
                    os.replace(stage / s['name'], dest)
                    installed.append(dest)
                    receipts[s['name']] = tree(dest)
                write(receipts_path, receipts)
            except BaseException:
                for dest in installed:
                    shutil.rmtree(dest)
                for dest, backup in backups:
                    os.replace(backup, dest)
                raise
    drafts = [s['name'] for s in lock['skills'] if s.get('source_state') != 'committed']
    print('SKILLS_' + args.action.upper() + '_OK', len(lock['skills']), 'uncommitted_sources=' + ','.join(drafts))

def git_check(args):
    root = Path(args.project).resolve()
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z'], text=True, encoding='utf-8').split('\0')
    bad = [p for p in tracked if p and safe(root, p).exists() and Path(p).suffix.lower() in MEDIA]
    if bad:
        raise ValueError('Media must be removed from Git index: ' + ', '.join(bad))
    print('GIT_ASSET_POLICY_OK')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('assets')
    p.add_argument('action', choices=['index', 'push', 'pull', 'verify'])
    p.add_argument('--project', default='.')
    p.add_argument('--bucket', default='lseyesl/mv_assets')
    p.add_argument('--repository-id')
    p.set_defaults(func=assets)
    p = subs.add_parser('skills')
    p.add_argument('action', choices=['check', 'install', 'update'])
    p.add_argument('--project', default='.')
    p.add_argument('--source')
    p.set_defaults(func=skills)
    p = subs.add_parser('git-check')
    p.add_argument('--project', default='.')
    p.set_defaults(func=git_check)
    args = parser.parse_args()
    try:
        args.func(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as e:
        parser.exit(1, str(e) + '\n')

if __name__ == '__main__':
    main()
