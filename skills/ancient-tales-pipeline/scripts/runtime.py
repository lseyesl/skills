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
import io
import importlib.util
from concurrent.futures import ThreadPoolExecutor

# Project wrappers use runpy.run_path(), which does not add this directory to
# sys.path. Always load our sibling module by its own path.
_dependency_spec = importlib.util.spec_from_file_location('ancient_tales_dependencies', Path(__file__).with_name('skill_dependencies.py'))
dependencies = importlib.util.module_from_spec(_dependency_spec)
_dependency_spec.loader.exec_module(dependencies)

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
        previous = checked_lock(path) if path.exists() else {'assets': []}
        old = {a['path']: a for a in previous['assets']}
        missing = [p for p in old if not safe(root, p).is_file()]
        if missing:
            raise ValueError('Indexed assets are missing; pull them or explicitly forget them: ' + ', '.join(missing))
        excluded = previous.get('excluded_roots', [])
        # Scanning a partial checkout or changing filters must never erase an
        # existing record. Only the explicit forget operation removes records.
        result = dict(old)
        for p in files(root):
            if p.relative_to(root).parts[0] in excluded:
                continue
            if p.suffix.lower() not in MEDIA:
                continue
            rel, sha = p.relative_to(root).as_posix(), digest(p)
            before = old.get(rel, {})
            if before.get('sha256') == sha:
                # A rescan discovers bytes, not a new business version or approval.
                # Keep identity, receipts and project-specific extension fields intact.
                continue
            if before.get('sha256') != sha and before.get('status') in {'approved', 'locked'}:
                raise ValueError('Approved asset changed in place; create a new version: ' + rel)
            result[rel] = {'asset_id': before.get('asset_id', rel), 'project_id': rel.split('/')[1] if rel.startswith('projects/') else 'shared', 'path': rel, 'sha256': sha, 'size': p.stat().st_size, 'version': sha, 'status': before.get('status', 'unreviewed'), 'uri': f'hf://buckets/{args.bucket}/{args.repository_id}/objects/{sha}{p.suffix.lower()}'}
        # Pending is promoted only by push after verified upload.
        write(root / 'assets.pending.json', {**previous, 'schema_version': 1, 'bucket': args.bucket, 'repository_id': args.repository_id, 'excluded_roots': excluded, 'assets': [result[p] for p in sorted(result)]})
        print('ASSETS_INDEX_PENDING', len(result))
    elif args.action == 'forget':
        lock = checked_lock(path)
        paths = set(getattr(args, 'path', None) or [])
        known = {a['path']: a for a in lock['assets']}
        if not paths or not paths.issubset(known):
            raise ValueError('forget requires explicit existing --path values')
        if not getattr(args, 'allow_locked', False) and any(known[p].get('status') in {'approved', 'locked'} for p in paths):
            raise ValueError('Removing approved/locked records requires --allow-locked')
        write(root / 'assets.pending.json', {**lock, 'removed_paths': sorted(paths), 'assets': [a for a in lock['assets'] if a['path'] not in paths]})
        print('ASSETS_FORGET_PENDING', len(paths), '(remote objects and local files unchanged)')
    elif args.action == 'push':
        pending = root / 'assets.pending.json'
        lock = checked_lock(pending if pending.exists() else path)
        if path.exists():
            old_paths = {a['path'] for a in read(path)['assets']}
            removed = old_paths - {a['path'] for a in lock['assets']}
            if not removed.issubset(set(lock.get('removed_paths', []))):
                raise ValueError('Asset records cannot disappear without explicit forget')
        asset_transfer(root, lock, 'push')
        write(path, {k: v for k, v in lock.items() if k != 'removed_paths'})
        pending.unlink(missing_ok=True)
    elif args.action == 'pull':
        asset_transfer(root, checked_lock(path), 'pull')
    else:
        print('ASSETS_VERIFY_OK', asset_verify(root, checked_lock(path)))

def git_bytes(source, *args, input=None):
    return subprocess.check_output(['git', '-C', str(source), *args], input=input)


def committed_snapshot(source, commit, directory):
    """Read immutable Git blob bytes; checkout filters and HEAD are irrelevant."""
    entries = []
    prefix = directory.rstrip('/') + '/'
    for record in git_bytes(source, 'ls-tree', '-r', '-z', '--full-tree', commit, '--', directory).split(b'\0'):
        if not record:
            continue
        meta, name = record.split(b'\t', 1)
        mode, kind, oid = meta.split()
        name = name.decode('utf-8')
        if not name.startswith(prefix):
            raise ValueError('Unexpected Git tree path')
        rel = name[len(prefix):]
        if any(part in SKIP for part in Path(rel).parts):
            continue
        if kind != b'blob' or mode not in {b'100644', b'100755'}:
            raise ValueError('Skill snapshots do not support symlinks/submodules: ' + name)
        entries.append((rel, mode, oid))
    if not any(rel == 'SKILL.md' for rel, _, _ in entries):
        raise ValueError('Missing committed SKILL.md: ' + directory)
    stream = io.BytesIO(git_bytes(source, 'cat-file', '--batch', input=b''.join(oid + b'\n' for _, _, oid in entries)))
    result = {}
    for rel, mode, oid in entries:
        header = stream.readline().split()
        if len(header) != 3 or header[0] != oid or header[1] != b'blob':
            raise ValueError('Missing Git blob: ' + rel)
        content = stream.read(int(header[2]))
        if stream.read(1) != b'\n':
            raise ValueError('Invalid Git batch response')
        result[rel] = (content, mode)
    return result


def snapshot_hash(snapshot):
    h = hashlib.sha256()
    for rel, (content, _) in sorted(snapshot.items()):
        h.update((rel + '\0' + hashlib.sha256(content).hexdigest() + '\n').encode('utf-8'))
    return h.hexdigest()


def stage_skill(source, entry, dest):
    if entry.get('content_format') == 'git-blob-sha256-v1':
        snapshot = committed_snapshot(source, entry['source_commit'], entry['directory'])
        if snapshot_hash(snapshot) != entry['tree_sha256']:
            raise ValueError('Locked Git content hash differs: ' + entry['name'])
        dest.mkdir(parents=True)
        for rel, (content, mode) in snapshot.items():
            p = safe(dest, rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)
            if os.name != 'nt':
                p.chmod(0o755 if mode == b'100755' else 0o644)
    else:
        # Legacy locks and explicitly allowed development snapshots keep their
        # exact worktree-byte semantics until the owner runs skills update.
        src = safe(source, entry['directory'])
        git_bytes(source, 'cat-file', '-e', entry['source_commit'] + '^{commit}')
        if tree(src) != entry['tree_sha256']:
            raise ValueError('Source differs from locked worktree: ' + entry['name'])
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(*SKIP))


def registry_at(source, commit=None):
    content = git_bytes(source, 'show', commit + ':skills.json') if commit else (source / 'skills.json').read_bytes()
    data = json.loads(content)
    return dependencies.validate_registry(data), hashlib.sha256(content).hexdigest()


def skills(args):
    root = Path(args.project).resolve()
    lock_path = root / 'skills.lock.json'
    lock = read(lock_path) if lock_path.exists() else {'skills': []}
    if args.action == 'update':
        source_arg = args.source or os.environ.get('ANCIENT_TALES_SKILLS_SOURCE')
        if not source_arg:
            raise ValueError('Set --source or ANCIENT_TALES_SKILLS_SOURCE')
        source = Path(source_arg).resolve()
        commit = git_bytes(source, 'rev-parse', 'HEAD').decode().strip()
        registry_dirty = bool(git_bytes(source, 'status', '--porcelain', '--untracked-files=all', '--', 'skills.json').strip())
        catalog, registry_hash = registry_at(source, None if registry_dirty else commit)
        roots = getattr(args, 'skill', None) or lock.get('requested_skills') or [s['name'] for s in lock['skills']]
        if not roots:
            raise ValueError('Select initial roots with --skill <name>')
        entries = []
        for name in dependencies.resolve(roots, catalog):
            item = catalog[name]
            directory = item['directory']
            src = safe(source, directory)
            if not (src / 'SKILL.md').is_file():
                raise ValueError('Missing Skill entry: ' + name)
            dirty = registry_dirty or bool(git_bytes(source, 'status', '--porcelain', '--untracked-files=all', '--', directory).strip())
            if dirty and not getattr(args, 'allow_working_tree', False):
                raise ValueError('Commit source first or explicitly use --allow-working-tree: ' + name)
            sha = tree(src) if dirty else snapshot_hash(committed_snapshot(source, commit, directory))
            entries.append({'name': name, 'directory': directory, 'requires': item.get('requires', []), 'source_commit': commit, 'source_state': 'working-tree' if dirty else 'committed', 'content_format': 'worktree-sha256-v1' if dirty else 'git-blob-sha256-v1', 'tree_sha256': sha})
        install_directory = getattr(args, 'install_dir', None) or lock.get('install_directory', '.agents/skills')
        safe(root, install_directory)
        write(lock_path, {'schema_version': 2, 'source_repository': 'https://github.com/lseyesl/skills', 'requested_skills': list(dict.fromkeys(roots)), 'install_directory': install_directory, 'dependency_manifest': {'source_commit': commit, 'sha256': registry_hash, 'source_state': 'working-tree' if registry_dirty else 'committed'}, 'skills': entries})
        print('SKILLS_LOCK_UPDATED; install explicitly to activate')
        return
    if not lock['skills']:
        raise ValueError('No locked Skills; run skills update first')
    dependencies.validate_lock(lock['skills'])
    install_root = safe(root, lock.get('install_directory', '.agents/skills'))
    receipts_path = install_root.parent / (install_root.name + '-receipts.json')
    receipts = read(receipts_path) if receipts_path.exists() else {}
    for entry in lock['skills']:
        dest = safe(install_root, entry['name'])
        if dest.exists() and tree(dest) != receipts.get(entry['name']):
            raise ValueError('Locally modified/unmanaged installed skill: ' + entry['name'])
        if args.action == 'check' and (not dest.exists() or tree(dest) != entry['tree_sha256']):
            raise ValueError('Missing or outdated skill: ' + entry['name'])
    if args.action == 'install':
        source_arg = args.source or os.environ.get('ANCIENT_TALES_SKILLS_SOURCE')
        if not source_arg:
            raise ValueError('Set --source or ANCIENT_TALES_SKILLS_SOURCE')
        source = Path(source_arg).resolve()
        manifest = lock.get('dependency_manifest')
        if manifest:
            catalog, sha = registry_at(source, manifest['source_commit'] if manifest['source_state'] == 'committed' else None)
            if sha != manifest['sha256']:
                raise ValueError('Dependency manifest differs from lock')
            for entry in lock['skills']:
                if catalog[entry['name']].get('requires', []) != entry.get('requires', []):
                    raise ValueError('Locked dependency declaration differs: ' + entry['name'])
        install_root.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='skills-', dir=install_root.parent) as temp:
            stage = Path(temp)
            incoming, backup_root = stage / 'incoming', stage / 'backups'
            incoming.mkdir(); backup_root.mkdir()
            for entry in lock['skills']:
                target = safe(incoming, entry['name'])
                stage_skill(source, entry, target)
                # Check the copied/extracted bytes, not just the mutable source.
                if tree(target) != entry['tree_sha256']:
                    raise ValueError('Staged Skill differs from lock: ' + entry['name'])
            install_root.mkdir(exist_ok=True)
            backups, installed = [], []
            try:
                for entry in lock['skills']:
                    dest = safe(install_root, entry['name'])
                    if dest.exists():
                        backup = safe(backup_root, entry['name'])
                        os.replace(dest, backup)
                        backups.append((dest, backup))
                    os.replace(incoming / entry['name'], dest)
                    installed.append(dest)
                    receipts[entry['name']] = tree(dest)
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
    p.add_argument('action', choices=['index', 'push', 'pull', 'verify', 'forget'])
    p.add_argument('--project', default='.')
    p.add_argument('--bucket', default='lseyesl/mv_assets')
    p.add_argument('--repository-id')
    p.add_argument('--path', action='append', help='Explicit local asset record to forget (repeatable)')
    p.add_argument('--allow-locked', action='store_true', help='Allow forgetting approved/locked records')
    p.set_defaults(func=assets)
    p = subs.add_parser('skills')
    p.add_argument('action', choices=['check', 'install', 'update'])
    p.add_argument('--project', default='.')
    p.add_argument('--source')
    p.add_argument('--skill', action='append', help='Requested root Skill for update (repeatable)')
    p.add_argument('--install-dir', help='Project-relative destination, default .agents/skills')
    p.add_argument('--allow-working-tree', action='store_true', help='Explicitly lock development snapshots')
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
