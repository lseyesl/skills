"""Blender-only calibrated image guides and explicit reference-use gates.

No image/overlay is automatically judged: review records come from inspected
viewport captures. Pixel positions use top-left image coordinates.
"""
from pathlib import Path
import hashlib
import json
import math

import bpy
from mathutils import Matrix, Vector
from reference_review import require_design_review
from appearance_signature import appearance_signature

OWNER = 'reference_workspace_owner'
BASES = {
    'front': ((1, 0, 0), (0, 0, 1), (0, -1, 0)),
    'back': ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
    'right': ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
    'left': ((0, -1, 0), (0, 0, 1), (-1, 0, 0)),
    'top': ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    'bottom': ((1, 0, 0), (0, -1, 0), (0, 0, -1)),
}


def _key(task):
    return 'reference_workspace::' + task


def _object(scene, task, view):
    matches = [o for o in scene.objects if o.get(OWNER) == task and o.get('reference_view') == view]
    if len(matches) != 1:
        raise RuntimeError(f'{view}: expected one owned reference in active scene, found {len(matches)}')
    return matches[0]


def setup_references(scene, task, config, base):
    """Import/reuse only owned Image Empties; do not build model geometry."""
    if scene != bpy.context.scene:
        raise RuntimeError('Make the reference scene active before setup')
    if not task or not config.get('views'):
        raise ValueError('task and separate reference views are required')
    base = Path(base).resolve()
    # Source design review precedes even guide mutation, not just geometry deletion.
    design = require_design_review(config, base)
    name = task + '::reference-workspace'
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        collection[OWNER] = task
        scene.collection.children.link(collection)
    elif collection.get(OWNER) != task or collection.name not in scene.collection.children or collection.users > 1:
        raise RuntimeError('Reference collection collision or collection belongs to another scene')
    if any(o.get(OWNER) != task for o in collection.objects):
        raise RuntimeError('Reference collection contains unowned objects')
    if {o.get('reference_view') for o in collection.objects} - set(config['views']):
        raise RuntimeError('Remove obsolete owned references explicitly before changing view set')
    records = {}
    for view, item in config['views'].items():
        if view not in BASES:
            raise ValueError('Unsupported orthographic view: ' + view)
        path = (base / item['image']).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        ppu = float(item['pixels_per_unit'])
        opacity = float(item.get('opacity', .4))
        if not math.isfinite(ppu) or ppu <= 0 or not .05 <= opacity <= .85:
            raise ValueError('Positive finite pixels_per_unit and useful opacity .05–.85 required')
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        images = [im for im in bpy.data.images if im.get(OWNER) == task
                  and im.get('reference_sha256') == source_hash
                  and Path(bpy.path.abspath(im.filepath)).resolve() == path]
        image = images[0] if images else bpy.data.images.load(str(path), check_existing=False)
        image[OWNER] = task
        image['reference_sha256'] = source_hash
        if min(image.size) <= 0:
            raise ValueError('Reference image cannot be decoded')
        image.pack()
        name = task + '::reference::' + view
        obj = bpy.data.objects.get(name)
        if obj is None:
            obj = bpy.data.objects.new(name, None)
            collection.objects.link(obj)
        elif obj.get(OWNER) != task or obj.name not in collection.objects or obj.type != 'EMPTY':
            raise RuntimeError('Unowned/shared reference name collision: ' + name)
        if any(s != scene and obj.name in s.objects for s in bpy.data.scenes):
            raise RuntimeError('Reference object shared with another scene: ' + name)
        right, up, normal = [Vector(x) for x in BASES[view]]
        cx, cy = [float(v) for v in item['origin_px']]
        origin = Vector(item.get('origin_world', [0, 0, 0]))
        if not all(math.isfinite(x) for x in [cx, cy, *origin]):
            raise ValueError('Nonfinite calibration')
        for anchor in item.get('landmarks', {}).values():
            if len(anchor) != 2 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in anchor):
                raise ValueError('Landmarks require finite pixel coordinates')
        w, h = image.size
        obj.empty_display_type = 'IMAGE'
        obj.data = image
        # Draw order supplies front display; the image stays on its calibrated plane.
        obj.empty_image_depth = 'FRONT'
        obj.empty_image_side = 'FRONT'
        obj.use_empty_image_alpha = True
        obj.color = (1, 1, 1, opacity)
        obj.show_empty_image_only_axis_aligned = True
        obj.show_empty_image_orthographic = True
        obj.show_empty_image_perspective = False
        obj.empty_image_offset = (-.5, -.5)
        obj.empty_display_size = max(w, h) / ppu
        obj.location = origin + right * ((w / 2 - cx) / ppu) + up * ((cy - h / 2) / ppu)
        obj.rotation_euler = Matrix((right, up, normal)).transposed().to_euler()
        obj.scale = (1, 1, 1)
        obj.hide_render = True
        obj.hide_viewport = False
        obj.hide_set(False)
        obj.hide_select = True
        obj.lock_location = obj.lock_rotation = obj.lock_scale = (True, True, True)
        obj[OWNER] = task
        obj['reference_view'] = view
        obj['reference_landmarks'] = json.dumps(item.get('landmarks', {}))
        records[view] = {'object': name, 'path': str(path), 'sha256': source_hash,
                         'size': list(image.size), 'pixels_per_unit': ppu, 'origin_px': [cx, cy],
                         'origin_world': list(origin), 'opacity': opacity, 'landmarks': item.get('landmarks', {})}
    bpy.context.view_layer.update()
    for view, entry in records.items():
        entry['matrix'] = [list(row) for row in _object(scene, task, view).matrix_world]
    scene[_key(task)] = json.dumps(records, sort_keys=True)
    scene[_key(task) + '::used'] = '[]'
    if design:
        scene[_key(task) + '::design'] = json.dumps({
            'config': config, 'base': str(base), 'review': design,
            'review_text': Path(design['path']).read_bytes().decode('utf-8')}, sort_keys=True)
    elif _key(task) + '::design' in scene:
        del scene[_key(task) + '::design']
    return records


def workspace_signature(scene, task):
    """Read live scene state so moving/hiding a guide invalidates its review."""
    if scene != bpy.context.scene:
        raise RuntimeError('Make the reference scene active before checking it')
    if _key(task) not in scene:
        raise RuntimeError('No calibrated reference workspace; a packed image is insufficient')
    records = json.loads(scene[_key(task)])
    for view, entry in records.items():
        obj = _object(scene, task, view)
        if obj.type != 'EMPTY' or obj.empty_display_type != 'IMAGE' or not obj.data:
            raise RuntimeError(view + ': missing Image Empty')
        if obj.empty_image_depth != 'FRONT' or obj.empty_image_side != 'FRONT':
            raise RuntimeError(view + ': reference must display in front, front side only')
        if not obj.use_empty_image_alpha or abs(obj.color[3] - entry['opacity']) > 1e-6:
            raise RuntimeError(view + ': reference opacity differs from calibrated setting')
        if not obj.show_empty_image_only_axis_aligned or not obj.show_empty_image_orthographic or obj.show_empty_image_perspective:
            raise RuntimeError(view + ': incorrect axis-view visibility')
        if obj.hide_viewport or obj.hide_get() or not obj.visible_get():
            raise RuntimeError(view + ': reference is hidden in the active view layer')
        if list(obj.data.size) != entry['size'] or Path(bpy.path.abspath(obj.data.filepath)).resolve() != Path(entry['path']):
            raise RuntimeError(view + ': source image changed')
        path = Path(entry['path'])
        packed = obj.data.packed_file
        source_bytes = path.read_bytes() if path.is_file() else bytes(packed.data) if packed else b''
        if hashlib.sha256(source_bytes).hexdigest() != entry['sha256']:
            raise RuntimeError(view + ': source file changed; recalibrate')
        if max(abs(obj.matrix_world[i][j] - entry['matrix'][i][j]) for i in range(4) for j in range(4)) > 1e-6:
            raise RuntimeError(view + ': reference transform changed; recalibrate')
        if abs(obj.empty_display_size - max(entry['size']) / entry['pixels_per_unit']) > 1e-6 or tuple(obj.empty_image_offset) != (-.5, -.5):
            raise RuntimeError(view + ': reference scale or image offset changed')
    design_key = _key(task) + '::design'
    if design_key in scene:
        design = json.loads(scene[design_key])
        live = design['review']
        receipt = Path(live['path'])
        embedded = hashlib.sha256(design['review_text'].encode('utf-8')).hexdigest()
        # Existing packed scenes remain inspectable away from their source folder.
        # New setup/build still validates all source files and scope above.
        if embedded != live['sha256'] or (receipt.is_file() and
                hashlib.sha256(receipt.read_bytes()).hexdigest() != live['sha256']):
            raise RuntimeError('Pre-model design review changed; inspect and recalibrate')
        records = {'guides': records, 'design_review': live}
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()


def reference_landmark(scene, task, view, name):
    """Return an actual imported guide's calibrated world-space landmark."""
    workspace_signature(scene, task)
    obj = _object(scene, task, view)
    record = json.loads(scene[_key(task)])[view]
    x, y = record['landmarks'][name]
    w, h = record['size']
    # Local XY plane of the actual image guide, accounting for pixel aspect/size.
    ppu = record['pixels_per_unit']
    point = obj.matrix_world @ Vector(((x - w / 2) / ppu, (h / 2 - y) / ppu, 0))
    used = json.loads(scene[_key(task) + '::used'])
    binding = {'view': view, 'landmark': name, 'world': list(point)}
    if binding not in used:
        used.append(binding)
        scene[_key(task) + '::used'] = json.dumps(used)
    return point


def require_reference_review(scene, task, review_path, *, phase='calibration', objects=()):
    """Require inspected viewport artifacts; never auto-approve their content."""
    path = Path(review_path).resolve()
    if phase not in {'calibration', 'comparison'}:
        raise ValueError('Review phase must be calibration or comparison')
    review = json.loads(path.read_text())
    if review.get('workspace_signature') != workspace_signature(scene, task):
        raise RuntimeError('Reference review is stale or for a different workspace')
    if review.get('phase') != phase or review.get('status') != 'passed':
        raise RuntimeError('Reference review has not passed the requested phase')
    records = json.loads(scene[_key(task)])
    for view in records:
        entry = review.get('views', {}).get(view, {})
        artifact = entry.get('artifact')
        finding = entry.get('finding')
        if not isinstance(artifact, str) or not artifact.strip() or not isinstance(finding, str) or not finding.strip():
            raise RuntimeError(view + ': missing actual viewport capture/review finding')
        image = (path.parent / artifact).resolve()
        if not image.is_file() or image.stat().st_size == 0:
            raise RuntimeError(view + ': review capture missing or empty')
    if phase == 'comparison':
        objects = list(objects)
        used = json.loads(scene[_key(task) + '::used'])
        if not used:
            raise RuntimeError('No reference landmarks consumed by the builder')
        if review.get('model_signature') != model_signature(objects):
            raise RuntimeError('Model changed since reference comparison')
        if review.get('appearance_signature') != appearance_signature(
                scene, objects, extra=review.get('appearance_extra')):
            raise RuntimeError('Visual state changed or missing; inspect materials/lights/cameras again')
    return review


def model_signature(objects):
    records = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in sorted(objects, key=lambda o: o.name):
        evaluated = obj.evaluated_get(depsgraph)
        data = {'object': obj.name, 'matrix': [list(r) for r in evaluated.matrix_world]}
        if obj.type in {'MESH', 'CURVE'}:
            mesh = evaluated.to_mesh()
            try:
                data['vertices'] = [list(v.co) for v in mesh.vertices]
                data['faces'] = [list(f.vertices) for f in mesh.polygons]
            finally:
                evaluated.to_mesh_clear()
        records.append(data)
    if not records:
        raise RuntimeError('No model objects supplied for reference comparison')
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
