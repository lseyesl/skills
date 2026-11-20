"""Audit declared 2D anchors at every supplied frame; never solves motion or approves visuals.

Uses shadow-puppet-part-splitter's transform implementation. Contacts use inclusive
frame ranges and rest-canvas anchor coordinates. A target is either a fixed point
or {node, point}; moving targets use the same evaluated pose as the actor.
"""
import argparse
import json
import math
from pathlib import Path
import sys


def audit(manifest, motion, contacts, splitter_scripts=None):
    scripts = Path(splitter_scripts) if splitter_scripts else Path(__file__).resolve().parents[2] / 'shadow-puppet-part-splitter/scripts'
    if not (scripts / 'puppet_core.py').is_file():
        raise ValueError('Install shadow-puppet-part-splitter or provide --splitter-scripts')
    sys.path.insert(0, str(scripts))
    from puppet_core import normalize, pose_transforms, apply, pair, number
    data = normalize(manifest)
    node_ids = {node['id'] for node in data['nodes']}
    if not isinstance(motion, list) or not isinstance(contacts, list):
        raise ValueError('Motion and contacts must be arrays')
    frames = {}
    for pose in motion:
        if not isinstance(pose, dict):
            raise ValueError('Each pose must be an object')
        f = pose.get('frame')
        if type(f) is not int or f in frames:
            raise ValueError('Frames must have unique integer IDs')
        frames[f] = pose_transforms(data, pose)
        if any(not all(number(v) for v in matrix) for matrix in frames[f].values()):
            raise ValueError('Nonfinite evaluated transform')
    if not contacts:
        raise ValueError('No declared contacts: cannot report pass')
    results = []
    ids = set()
    for contact in contacts:
        if not isinstance(contact, dict):
            raise ValueError('Each contact must be an object')
        identity = contact.get('id')
        if not isinstance(identity, str) or not identity.strip() or identity in ids:
            raise ValueError('Contacts require unique nonempty IDs')
        ids.add(identity)
        if not isinstance(contact.get('node'), str) or contact['node'] not in node_ids:
            raise ValueError('Contact actor must name an existing node')
        start, end = contact['frames']
        if type(start) is not int or type(end) is not int or start > end:
            raise ValueError('Invalid inclusive frame range')
        tolerance = contact['tolerance_px']
        if not number(tolerance) or tolerance < 0:
            raise ValueError('Invalid tolerance')
        point, target = contact['point'], contact['target']
        if not isinstance(target, dict):
            raise ValueError('Target must be an object')
        if 'node' in target and (not isinstance(target['node'], str) or target['node'] not in node_ids):
            raise ValueError('Target node must name an existing node; omit for a fixed point')
        target_point = target['point']
        if not pair(point) or not pair(target_point):
            raise ValueError('Anchors must be finite pixel pairs')
        samples = []
        for f in range(start, end + 1):
            if f not in frames:
                raise ValueError(f'Missing frame {f}; sparse samples cannot certify this interval')
            mats = frames[f]
            actual = apply(mats[contact['node']], point)
            expected = apply(mats[target['node']], target_point) if target.get('node') else target_point
            error = math.dist(actual, expected)
            if not pair(actual) or not pair(expected) or not number(error):
                raise ValueError('Nonfinite evaluated contact')
            samples.append(dict(frame=f, actual=actual, target=expected, error_px=error))
        worst = max(samples, key=lambda row: row['error_px'])
        results.append(dict(id=contact['id'], status='pass' if worst['error_px'] <= tolerance else 'fail',
                            tolerance_px=tolerance, worst=worst, samples=samples))
    return dict(status='pass' if all(r['status']=='pass' for r in results) else 'fail',
                scope='declared 2D anchor distances only; no silhouette, physics, timing or visual approval',
                visual_review='pending', contacts=results)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'motion', 'contacts', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--splitter-scripts', type=Path)
    args = p.parse_args()
    inputs = (args.manifest, args.motion, args.contacts)
    if args.output.resolve() in [f.resolve() for f in inputs] or args.output.exists():
        p.error('Output must be a new file distinct from inputs')
    try:
        result = audit(*(json.loads(f.read_text()) for f in inputs), args.splitter_scripts)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    except (ValueError, KeyError, TypeError, OSError) as exc:
        p.exit(2, str(exc)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='contacts'}))
    return 0 if result['status']=='pass' else 1


if __name__ == '__main__':
    sys.exit(main())
