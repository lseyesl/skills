"""Asset metadata and receipt checks. No transfer or approval side effects."""
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

STATUSES = {'draft', 'review', 'approved', 'locked', 'blocked', 'needs-sync', 'unreviewed'}
SHA = re.compile(r'^[0-9a-f]{64}$')


def relative_file(root, value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Expected a repository-relative POSIX path')
    rel = PurePosixPath(value)
    if rel.is_absolute() or '..' in rel.parts or rel.as_posix() != value:
        raise ValueError('Expected a canonical repository-relative path: ' + value)
    root = Path(root).resolve()
    dest = (root / value).resolve()
    if dest == root or root not in dest.parents:
        raise ValueError('Path escapes project: ' + value)
    return dest


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def text_field(obj, key):
    if not isinstance(obj, dict):
        raise ValueError('Expected an object containing ' + key)
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Missing/invalid ' + key)
    return value


def validate_attribution(record):
    text_field(record, 'approved_by')
    try:
        datetime.fromisoformat(text_field(record, 'approved_at').replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid receipt approved_at') from exc


def validate_manifest(lock, root=None, strict=False, expected_project=None):
    """Legacy transport records may omit IDs; strict handoffs may not."""
    if not isinstance(lock, dict) or not isinstance(lock.get('assets'), list):
        raise ValueError('Asset manifest needs an assets list')
    repository = text_field(lock, 'repository_id')
    bucket = text_field(lock, 'bucket')
    segment = r'[\w][\w.-]*'
    if not re.fullmatch(segment, repository) or not re.fullmatch(segment + '/' + segment, bucket):
        raise ValueError('Invalid repository/bucket namespace')
    seen, identities = set(), set()
    for asset in lock['assets']:
        if not isinstance(asset, dict):
            raise ValueError('Asset record must be an object')
        path = text_field(asset, 'path')
        relative_file(root or Path.cwd(), path)
        if path in seen:
            raise ValueError('Duplicate asset path')
        seen.add(path)
        sha = asset.get('sha256')
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise ValueError('Invalid asset sha256: ' + path)
        size = asset.get('size')
        if type(size) is not int or size < 0:
            raise ValueError('Invalid asset size: ' + path)
        if not isinstance(asset.get('status'), str) or asset['status'] not in STATUSES:
            raise ValueError('Unknown asset status: ' + path)
        uri = f"hf://buckets/{bucket}/{repository}/objects/{sha}{PurePosixPath(path).suffix.lower()}"
        if asset.get('uri') != uri:
            raise ValueError('Asset URI is not content-addressed in its repository namespace: ' + path)
        if asset.get('repository_id', repository) != repository:
            raise ValueError('Asset repository identity mismatch: ' + path)
        parts = PurePosixPath(path).parts
        path_project = parts[1] if len(parts) > 2 and parts[0] == 'projects' else None
        if expected_project and path_project and expected_project != path_project:
            raise ValueError('Asset path belongs to a different project: ' + path)
        project = expected_project or path_project
        if project and asset.get('project_id', project if not strict else None) != project:
            raise ValueError('Asset project identity mismatch: ' + path)
        for field in ('asset_id', 'project_id', 'version'):
            if strict or field in asset:
                text_field(asset, field)
        if all(field in asset for field in ('project_id', 'asset_id', 'version')):
            identity = (asset['project_id'], asset['asset_id'], asset['version'])
            if identity in identities:
                raise ValueError('Duplicate asset identity/version')
            identities.add(identity)
        if strict and asset['status'] in {'approved', 'locked'}:
            if root is None:
                raise ValueError('Receipt validation requires project root')
            receipt_path = relative_file(root, text_field(asset, 'approval_receipt'))
            if not receipt_path.is_file() or file_sha(receipt_path) != asset.get('approval_receipt_sha256'):
                raise ValueError('Missing/changed approval receipt: ' + path)
            receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig'))
            if not isinstance(receipt, dict):
                raise ValueError('Approval receipt must be an object')
            for field, expected in [('repository_id', repository), *[(k, asset[k]) for k in ('project_id', 'asset_id', 'version', 'sha256')]]:
                if receipt.get(field) != expected:
                    raise ValueError('Approval receipt identity/hash mismatch: ' + field)
            validate_attribution(receipt)
            for field in ('approved_by', 'approved_at'):
                if field in asset and asset[field] != receipt[field]:
                    raise ValueError('Approval receipt attribution mismatch: ' + field)
    return len(seen)
