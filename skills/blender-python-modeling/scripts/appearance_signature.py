"""Blender visual-state fingerprint for invalidating inspected render evidence.

It supplements evaluated geometry checks. Custom external engines, simulations
and untracked asset types need project-specific inputs; a hash is not image QA.
"""
from array import array
from pathlib import Path
import hashlib
import json

import bpy


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    try:
        return [_value(x) for x in value]
    except TypeError:
        return str(value)


def _props(obj, keys):
    return {k: _value(getattr(obj, k)) for k in keys if hasattr(obj, k)}


def _node_properties(node):
    # Inspect scalar/array RNA, excluding editor layout and decoration. This also
    # captures stock-node settings such as Brick offset_frequency, not just sockets.
    editor = {'name', 'label', 'location', 'location_absolute', 'dimensions', 'width', 'height', 'width_hidden',
              'color', 'use_custom_color', 'select', 'hide', 'show_options',
              'show_preview', 'show_texture'}
    return {p.identifier: _value(getattr(node, p.identifier))
            for p in node.bl_rna.properties if not p.is_readonly
            and p.type in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}
            and p.identifier not in editor and not p.identifier.startswith('bl_')}


def _image(image):
    path = Path(bpy.path.abspath(image.filepath)) if image.filepath else None
    data = {'name': image.name, 'source': image.source, 'size': list(image.size),
            'colorspace': image.colorspace_settings.name, 'alpha': image.alpha_mode}
    if path and path.is_file():
        data['file'] = hashlib.sha256(path.read_bytes()).hexdigest()
    packed = image.packed_file
    if packed:
        data['packed'] = hashlib.sha256(bytes(packed.data)).hexdigest()
    if image.is_dirty or image.source == 'GENERATED':
        pixels = array('f', [0]) * len(image.pixels)
        image.pixels.foreach_get(pixels)
        data['pixels'] = hashlib.sha256(pixels.tobytes()).hexdigest()
    if image.source in {'MOVIE', 'SEQUENCE', 'TILED'}:
        # These need the exact current frame/tile dependencies supplied by caller.
        data['external_dependencies_required'] = True
    return data


def _ramp(ramp):
    return {'interpolation': ramp.interpolation, 'mode': ramp.color_mode,
            'hue': ramp.hue_interpolation,
            'elements': [(e.position, list(e.color)) for e in ramp.elements]}


def _curves(mapping):
    return {'levels': _props(mapping, ('black_level', 'white_level', 'use_clip')),
            'curves': [[(list(p.location), p.handle_type) for p in c.points] for c in mapping.curves]}


def _tree(tree, stack=()):
    if tree is None:
        return None
    if tree.as_pointer() in stack:
        raise RuntimeError('Recursive node group cannot be fingerprinted')
    stack = (*stack, tree.as_pointer())
    nodes = []
    for n in sorted(tree.nodes, key=lambda x: x.name):
        if n.type == 'FRAME':  # Editor-only parent frames do not shade the asset.
            continue
        item = {'name': n.name, 'type': n.bl_idname, 'mute': n.mute,
                'properties': _props(n, ('operation', 'blend_type', 'data_type', 'interpolation',
                    'extension', 'projection', 'projection_blend', 'distribution', 'subsurface_method',
                    'attribute_name', 'attribute_type', 'uv_map', 'vector_type', 'convert_from',
                    'convert_to', 'space', 'noise_dimensions', 'normalize', 'clamp', 'use_clamp',
                    'is_active_output', 'target', 'mode', 'invert', 'component', 'feature',
                    'distance', 'voronoi_dimensions', 'gradient_type', 'wave_type', 'wave_profile',
                    'bands_direction', 'rings_direction', 'use_alpha', 'image_user')),
                'inputs': [(x.identifier, _value(x.default_value)) for x in n.inputs
                           if hasattr(x, 'default_value')],
                'outputs': [(x.identifier, _value(x.default_value)) for x in n.outputs
                            if hasattr(x, 'default_value')]}
        # image_user has no stable string representation; capture its actual frame settings.
        item['properties'].pop('image_user', None)
        item['properties'].update(_node_properties(n))
        if hasattr(n, 'texture_mapping'):
            item['texture_mapping'] = _props(n.texture_mapping, ('translation', 'rotation', 'scale',
                'min', 'max', 'use_min', 'use_max', 'vector_type'))
        if hasattr(n, 'color_mapping'):
            item['color_mapping'] = _props(n.color_mapping, ('brightness', 'contrast', 'saturation',
                'blend_color', 'blend_factor', 'blend_type', 'use_color_ramp'))
            item['color_mapping']['ramp'] = _ramp(n.color_mapping.color_ramp)
        if hasattr(n, 'image_user'):
            item['image_user'] = _props(n.image_user, ('frame_current', 'frame_duration', 'frame_offset',
                                                       'frame_start', 'use_auto_refresh', 'use_cyclic'))
        if getattr(n, 'image', None):
            item['image'] = _image(n.image)
        if getattr(n, 'object', None):
            item['object'] = {'name': n.object.name, 'matrix': [list(r) for r in n.object.matrix_world]}
        if getattr(n, 'node_tree', None):
            item['group'] = _tree(n.node_tree, stack)
        if hasattr(n, 'color_ramp'):
            item['ramp'] = _ramp(n.color_ramp)
        if hasattr(n, 'mapping'):
            item['curves'] = _curves(n.mapping)
        nodes.append(item)
    links = sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier)
                   for l in tree.links)
    return {'nodes': nodes, 'links': links}


def _material(material):
    if material is None:
        return None
    return {'name': material.name, 'properties': _props(material, (
                'use_nodes', 'diffuse_color', 'metallic', 'roughness', 'surface_render_method',
                'use_backface_culling', 'use_transparency_overlap', 'use_transparent_shadow',
                'displacement_method', 'alpha_threshold')),
            'nodes': _tree(material.node_tree) if material.use_nodes else None}


def _attribute(attr):
    if not attr.data:
        return {'type': attr.data_type, 'domain': attr.domain, 'hash': ''}
    sample = attr.data[0]
    field = next((n for n in ('vector', 'color', 'value') if hasattr(sample, n)), None)
    if field:
        v = getattr(sample, field)
        width = 1 if isinstance(v, (bool, float, int)) else len(v)
        code = 'i' if attr.data_type.startswith('INT') else 'b' if attr.data_type == 'BOOLEAN' else 'f'
        values = array(code, [0]) * (len(attr.data) * width)
        attr.data.foreach_get(field, values)
        digest = hashlib.sha256(values.tobytes()).hexdigest()
    else:
        # Fail closed for new attribute types instead of silently ignoring visual data.
        raise RuntimeError('Unsupported visual attribute: ' + attr.name + '/' + attr.data_type)
    return {'type': attr.data_type, 'domain': attr.domain, 'hash': digest}


def appearance_signature(scene, objects, *, extra=None):
    """Hash live materials, attributes, shading context and render presentation.

    Supply JSON-serializable extra inputs for external caches, frame sequences,
    custom engines, compositor resources or project-specific visual dependencies.
    """
    objects = list(objects)
    if not objects:
        raise RuntimeError('No model objects for appearance comparison')
    context = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    # Include other rendered meshes too: a studio ground or occluder affects the image.
    for o in sorted(scene.objects, key=lambda x: x.name):
        if o.type == 'EMPTY' or (o.hide_render and o not in objects):
            continue
        item = {'name': o.name, 'type': o.type, 'matrix': [list(r) for r in o.matrix_world],
                'visibility': _props(o, ('hide_render', 'visible_camera', 'visible_shadow',
                                        'visible_diffuse', 'visible_glossy'))}
        if o.type in {'MESH', 'CURVE'}:
            item['materials'] = [_material(slot.material) for slot in o.material_slots]
            e = o.evaluated_get(depsgraph)
            mesh = e.to_mesh()
            try:
                item['material_indices'] = _hash([p.material_index for p in mesh.polygons])
                item['smooth'] = _hash([p.use_smooth for p in mesh.polygons])
                item['attributes'] = {a.name: _attribute(a) for a in mesh.attributes
                                      if a.name != 'position' and not a.name.startswith('.')}
                # Additional scene geometry participates in shadows/occlusion.
                if o not in objects:
                    item['geometry'] = _hash({'v': [list(v.co) for v in mesh.vertices],
                                              'f': [list(p.vertices) for p in mesh.polygons]})
            finally:
                e.to_mesh_clear()
        elif o.type == 'LIGHT':
            item['light'] = _props(o.data, ('type', 'color', 'energy', 'shape', 'size', 'size_y',
                    'use_shadow', 'shadow_soft_size', 'spot_size', 'spot_blend', 'spread',
                    'normalize', 'exposure', 'use_temperature', 'temperature'))
            item['nodes'] = _tree(o.data.node_tree) if o.data.use_nodes else None
        elif o.type == 'CAMERA':
            item['camera'] = _props(o.data, ('type', 'lens', 'ortho_scale', 'sensor_fit', 'sensor_width',
                    'sensor_height', 'shift_x', 'shift_y', 'clip_start', 'clip_end'))
            item['dof'] = _props(o.data.dof, ('use_dof', 'focus_distance', 'aperture_fstop',
                                             'aperture_blades', 'aperture_rotation', 'aperture_ratio'))
            focus = o.data.dof.focus_object
            if focus:
                item['focus'] = [list(r) for r in focus.matrix_world]
        context.append(item)
    def layer(c):
        return {'name': c.name, 'exclude': c.exclude, 'render_hidden': c.collection.hide_render,
                'children': [layer(x) for x in c.children]}
    data = {'frame': scene.frame_current, 'active_camera': scene.camera.name if scene.camera else None,
            'objects': context, 'layers': [layer(l.layer_collection) for l in scene.view_layers],
            'render': _props(scene.render, ('engine', 'resolution_x', 'resolution_y', 'resolution_percentage',
                'film_transparent', 'use_motion_blur', 'motion_blur_shutter', 'use_compositing', 'use_sequencer')),
            'view': _props(scene.view_settings, ('view_transform', 'look', 'exposure', 'gamma',
                'use_curve_mapping', 'use_white_balance', 'temperature', 'tint')),
            'display': _props(scene.display_settings, ('display_device',)),
            'world': {'color': list(scene.world.color), 'nodes': _tree(scene.world.node_tree)
                      if scene.world.use_nodes else None} if scene.world else None,
            'compositor': _tree(scene.node_tree) if scene.use_nodes else None,
            'extra': extra}
    if scene.view_settings.use_curve_mapping:
        data['view_curves'] = _curves(scene.view_settings.curve_mapping)
    if scene.render.engine == 'CYCLES':
        data['engine_settings'] = _props(scene.cycles, ('samples', 'use_denoising', 'use_adaptive_sampling',
                                                       'adaptive_threshold', 'max_bounces'))
    elif hasattr(scene, 'eevee'):
        data['engine_settings'] = _props(scene.eevee, ('taa_render_samples', 'use_shadows', 'use_raytracing',
                                                     'shadow_ray_count', 'shadow_step_count'))
    return _hash(data)
