"""Validate declared pre-model multiview evidence and allowed construction scope.

This does not inspect pixels or certify visual agreement. Paths in the review are
relative to the review file; configured guide paths are relative to config base.
"""
from pathlib import Path
import argparse
import hashlib
import json

CHECKS = ('pose', 'proportions', 'projection', 'structure', 'appearance', 'axes')


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _regions(value, field):
    if not isinstance(value, list) or not value or not all(_text(x) for x in value):
        raise ValueError(field + ' must name explicit nonempty semantic regions')
    if any('*' in x or any(not p.strip() for p in x.split('.')) for x in value):
        raise ValueError(field + ' does not allow wildcards or empty path components')
    return value


def _overlap(a, b):
    return a == b or a.startswith(b + '.') or b.startswith(a + '.')


def require_design_review(config, base):
    """Gate multiple construction views before importing/mutating a workspace."""
    views = config.get('views', {})
    declared = config.get('multiview_review')
    if len(views) < 2 and not declared:
        return None
    if not _text(declared):
        raise ValueError('Multiple construction views require multiview_review before modeling')
    path = (Path(base) / declared).resolve()
    review = json.loads(path.read_text())
    if review.get('schema_version') != 1:
        raise ValueError('Unsupported multiview review schema')
    if not all(_text(review.get(k)) for k in ('purpose', 'pose')):
        raise ValueError('Review must state downstream purpose and fixed pose/configuration')
    readiness = review.get('readiness')
    if readiness not in {'passed', 'partial', 'blocked'}:
        raise ValueError('Readiness must be passed, partial, or blocked')
    statuses = []
    for key in CHECKS:
        item = review.get('checks', {}).get(key, {})
        status = item.get('status')
        if status not in {'passed', 'partial', 'blocked'} or not _text(item.get('finding')):
            raise ValueError(key + ': missing inspected finding/status')
        statuses.append(status)
    if readiness == 'blocked' or 'blocked' in statuses:
        raise RuntimeError('Reference set blocked; repair or use diagnostic-only blockout outside this build gate')
    if readiness == 'passed' and any(x != 'passed' for x in statuses):
        raise ValueError('Passed review cannot conceal partial checks')
    allowed = _regions(review.get('allowed_regions'), 'allowed_regions')
    blocked = review.get('blocked_regions', [])
    if not isinstance(blocked, list) or any(not _text(x) for x in blocked):
        raise ValueError('blocked_regions must be a list')
    if blocked:
        _regions(blocked, 'blocked_regions')
    conflicts = review.get('conflicts', [])
    if not isinstance(conflicts, list):
        raise ValueError('conflicts must be a list')
    for conflict in conflicts:
        if (not isinstance(conflict, dict) or not _text(conflict.get('finding'))
                or conflict.get('severity') not in {'critical', 'local'}
                or conflict.get('status') not in {'resolved', 'unresolved'}):
            raise ValueError('Each conflict needs severity, status and an actual finding')
        if conflict['status'] == 'resolved':
            if not _text(conflict.get('resolution')):
                raise ValueError('Resolved conflict needs the selected evidence and rationale')
        elif conflict['severity'] == 'critical':
            regions = _regions(conflict.get('regions'), 'critical conflict regions')
            if readiness != 'partial' or not all(
                    any(x == y or x.startswith(y + '.') for y in blocked) for x in regions):
                raise ValueError('Critical unresolved regions must be explicitly blocked in a partial review')
    if readiness == 'passed' and blocked:
        raise ValueError('Passed review cannot have blocked regions')
    if any(_overlap(a, b) for a in allowed for b in blocked):
        raise ValueError('Allowed scope overlaps a blocked region, including parent/child scope')
    requested = config.get('build_regions')
    if readiness == 'partial':
        requested = _regions(requested, 'build_regions for a partial review')
    elif requested is not None:
        requested = _regions(requested, 'build_regions')
    else:
        requested = allowed
    for region in requested:
        if any(_overlap(region, x) for x in blocked):
            raise RuntimeError('Build touches blocked region: ' + region)
        if not any(region == a or region.startswith(a + '.') for a in allowed):
            raise RuntimeError('Build exceeds reviewed scope: ' + region)
    review_views = review.get('views', {})
    if not isinstance(review_views, dict):
        raise ValueError('Review views must be an object')
    for name, item in review_views.items():
        if not isinstance(item, dict) or item.get('role') not in {'controlling', 'supplemental', 'rejected'}:
            raise ValueError(name + ': explicit view role required')
        if not _text(item.get('finding')) or not _text(item.get('image')):
            raise ValueError(name + ': inspected view finding/image required')
        source = (path.parent / item['image']).resolve()
        if not source.is_file() or item.get('sha256') != file_hash(source):
            raise RuntimeError(name + ': reviewed source changed or is missing')
        if item['role'] == 'controlling':
            _regions(item.get('controls'), name + '.controls')
    for name, item in views.items():
        entry = review_views.get(name, {})
        if entry.get('role') != 'controlling':
            raise RuntimeError(name + ': supplemental/rejected/unreviewed view cannot control construction')
        if (path.parent / entry['image']).resolve() != (Path(base) / item['image']).resolve():
            raise RuntimeError(name + ': configured guide is not the reviewed source')
    for region in requested:
        if not any(_overlap(region, c) for name in views for c in review_views[name]['controls']):
            raise RuntimeError('No configured controlling view constrains region: ' + region)
    artifacts = review.get('review_artifacts')
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError('Actual inspected review artifacts required')
    for artifact in artifacts:
        if not _text(artifact):
            raise ValueError('Invalid review artifact')
        target = (path.parent / artifact).resolve()
        if not target.is_file() or not target.stat().st_size:
            raise RuntimeError('Missing review artifact: ' + artifact)
    return {'path': str(path), 'sha256': file_hash(path), 'readiness': readiness,
            'build_regions': requested}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    args = parser.parse_args()
    try:
        result = require_design_review(json.loads(args.config.read_text()), args.config.resolve().parent)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps({'ok': True, 'review': result, 'scope': 'Evidence/state validation, not automated image agreement'}))
