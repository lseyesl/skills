"""Dependency-free manifest and screen-space affine math (also used in Blender)."""
import copy
import json
import math
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def pair(v, integer=False):
    return isinstance(v, list) and len(v) == 2 and all(number(x) and (not integer or isinstance(x, int)) for x in v)


def asset(root, name):
    require(isinstance(name, str) and bool(name), 'asset path must be a nonempty string')
    path = (Path(root) / name).resolve()
    require(path.is_file(), f'asset missing: {name}')
    return path


def index(items, label):
    require(isinstance(items, list), f'{label} must be an array')
    result = {}
    for item in items:
        require(isinstance(item, dict), f'{label} item must be an object')
        key = item.get('id')
        require(isinstance(key, str) and key and key not in result, f'invalid/duplicate {label} id: {key}')
        result[key] = item
    return result


def normalize(data):
    require(isinstance(data, dict), 'manifest must be an object')
    data = copy.deepcopy(data)
    require(data.get('schema_version') == '1.0', 'unsupported schema_version')
    require(data.get('coordinate_system') == 'image-pixels-y-down', 'unsupported coordinate_system')
    require(pair(data.get('source_size'), True) and min(data['source_size']) > 0, 'invalid source_size')
    data.setdefault('nodes', [])
    nodes, parts = index(data['nodes'], 'nodes'), index(data.get('parts'), 'parts')
    require(parts, 'parts must not be empty')
    for key, node in nodes.items():
        require(pair(node.get('pivot_global')), f'{key}: invalid pivot_global')
        node.setdefault('parent', None)
        require(node['parent'] is None or isinstance(node['parent'], str) and node['parent'] in nodes, f'{key}: unknown parent')
        bounds = node.get('rotation_range')
        require(bounds is None or pair(bounds) and bounds[0] <= bounds[1], f'{key}: invalid rotation_range')
    done = set()
    for key in nodes:
        chain, cursor = set(), key
        while cursor is not None and cursor not in done:
            require(cursor not in chain, f'parent cycle at {cursor}')
            chain.add(cursor)
            cursor = nodes[cursor]['parent']
        done.update(chain)
    for key, part in parts.items():
        node = part.setdefault('node', None)
        require(node is None or isinstance(node, str) and node in nodes, f'{key}: unknown node')
        part.setdefault('crop_origin', [0, 0])
        part.setdefault('z_index', 0)
        part.setdefault('label', key)
        part.setdefault('inferred', False)
        require(pair(part['crop_origin'], True), f'{key}: invalid crop_origin')
        require(pair(part.get('pixel_size'), True) and min(part['pixel_size']) > 0, f'{key}: invalid pixel_size')
        require(number(part['z_index']), f'{key}: invalid z_index')
        require(isinstance(part['inferred'], bool), f'{key}: invalid inferred boolean')
        if node is not None:
            expected = [nodes[node]['pivot_global'][i] - part['crop_origin'][i] for i in range(2)]
            pivot = part.setdefault('pivot_local', expected)
            require(pair(pivot) and all(abs(a-b) < 1e-6 for a, b in zip(pivot, expected)), f'{key}: pivot mismatch')
        require(not part['inferred'] or part.get('inferred_region_mask'), f'{key}: inferred mask required')
    return data


def read_manifest(path):
    return normalize(json.loads(Path(path).read_text(encoding='utf-8')))


IDENTITY = (1, 0, 0, 0, 1, 0)


def multiply(a, b):
    return (a[0]*b[0]+a[1]*b[3], a[0]*b[1]+a[1]*b[4], a[0]*b[2]+a[1]*b[5]+a[2],
            a[3]*b[0]+a[4]*b[3], a[3]*b[1]+a[4]*b[4], a[3]*b[2]+a[4]*b[5]+a[5])


def inverse(m):
    a, b, x, c, d, y = m
    det = a*d-b*c
    require(abs(det) > 1e-12, 'singular transform')
    return (d/det, -b/det, (b*y-d*x)/det, -c/det, a/det, (c*x-a*y)/det)


def apply(m, point):
    x, y = point
    return [m[0]*x+m[1]*y+m[2], m[3]*x+m[4]*y+m[5]]


def pose_transforms(data, pose=None, enforce_limits=True):
    pose = {} if pose is None else pose
    require(isinstance(pose, dict), 'pose must be an object')
    nodes = index(data.get('nodes', []), 'nodes')
    angles, translations, scales = [pose.get(k, {}) for k in ('angles', 'translations', 'scales')]
    for field, values in zip(('angles', 'translations', 'scales'), (angles, translations, scales)):
        require(isinstance(values, dict) and all(k in nodes for k in values), f'unknown/invalid {field} node')
        for key, v in values.items():
            require(number(v) if field == 'angles' else pair(v), f'{key}: invalid {field}')
            if field == 'scales':
                require(all(abs(x) > 1e-8 for x in v), f'{key}: zero scale')
    for key, value in angles.items():
        bounds = nodes[key].get('rotation_range')
        require(not enforce_limits or bounds is None or bounds[0] <= value <= bounds[1], f'{key}: angle outside rotation_range')
    result = {None: IDENTITY}
    for key in nodes:
        pending, cursor = [], key
        while cursor not in result:
            pending.append(cursor)
            cursor = nodes[cursor]['parent']
        for cursor in reversed(pending):
            node = nodes[cursor]
            x, y = node['pivot_global']
            dx, dy = translations.get(cursor, [0, 0])
            sx, sy = scales.get(cursor, [1, 1])
            t = math.radians(angles.get(cursor, 0))
            a, b, c, d = math.cos(t)*sx, -math.sin(t)*sy, math.sin(t)*sx, math.cos(t)*sy
            local = (a, b, x+dx-a*x-b*y, c, d, y+dy-c*x-d*y)
            result[cursor] = multiply(result[node['parent']], local)
    return result


def transforms(data, angles):
    return pose_transforms(data, {'angles': angles})
