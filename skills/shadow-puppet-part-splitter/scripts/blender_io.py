#!/usr/bin/env python3
"""Generic explicit-data Blender IO. Run with Blender --background --python ... -- ..."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from puppet_core import read_manifest, require, asset, pose_transforms, apply
from blender_rig import build


def bone_name(key):
    return 'node_'+hashlib.sha256(key.encode()).hexdigest()[:24]


def prepare(manifest, motion=None):
    data = read_manifest(manifest)
    motion = motion or {}
    require(motion.get('angle_convention', 'relative-clockwise') == 'relative-clockwise', 'unsupported angles')
    clips = motion.get('clips')
    if clips is None:
        poses = motion.get('poses', [])
        clips = [{'id': 'poses', 'frames': [dict(p, frame=p.get('frame', i*12+1)) for i, p in enumerate(poses)]}] if poses else []
    require(isinstance(clips, list), 'clips must be an array of {id, frames}')
    ids = set()
    for clip in clips:
        require(isinstance(clip, dict), 'clip must be an object')
        require(isinstance(clip.get('id'), str) and clip['id'] and clip['id'] not in ids, 'invalid/duplicate clip id')
        ids.add(clip['id']); frames = set()
        require(clip.get('frames'), 'clip has no frames')
        for case in clip['frames']:
            require('root_offset' not in case, 'convert root_offset to an explicit translations mapping')
            require(isinstance(case.get('frame'), int) and not isinstance(case['frame'], bool) and case['frame'] not in frames, 'invalid/duplicate frame')
            frames.add(case['frame'])
            pose_transforms(data, case)
    fps = motion.get('fps', 24)
    require(isinstance(fps, int) and not isinstance(fps, bool) and fps > 0, 'fps must be positive integer')
    return data, clips, fps


def set_pose(rig, nodes, pose):
    if rig is None:
        return
    for key in nodes:
        pb = rig.pose.bones[bone_name(key)]
        pb.rotation_euler = (0, 0, math.radians(-pose.get('angles', {}).get(key, 0)))
        dx, dy = pose.get('translations', {}).get(key, [0, 0])
        pb.location = (dx*.01, -dy*.01, 0)
        sx, sy = pose.get('scales', {}).get(key, [1, 1])
        pb.scale = (sx, sy, 1)


def measure(data, pose, meshes, point):
    matrices = pose_transforms(data, pose)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    error = 0.0
    for p in data['parts']:
        obj = meshes[p['id']]; evaluated = obj.evaluated_get(deps)
        ox, oy = p['crop_origin']; w, h = p['pixel_size']
        for i, xy in enumerate(((ox, oy), (ox+w, oy), (ox+w, oy+h), (ox, oy+h))):
            expected = point(apply(matrices[p['node']], xy))
            error = max(error, (evaluated.data.vertices[i].co-expected).length)
    require(error < 1e-4, f'evaluated vertex mismatch: {error}')
    return error


def samples(clip):
    keys = sorted(clip['frames'], key=lambda c: c['frame'])
    result = list(keys)
    for a, b in zip(keys, keys[1:]):
        middle = {'frame': (a['frame']+b['frame'])/2}
        for channel, default in (('angles', 0), ('translations', [0, 0]), ('scales', [1, 1])):
            middle[channel] = {}
            for key in set(a.get(channel, {})) | set(b.get(channel, {})):
                x, y = a.get(channel, {}).get(key, default), b.get(channel, {}).get(key, default)
                middle[channel][key] = [(u+v)/2 for u, v in zip(x, y)] if isinstance(default, list) else (x+y)/2
        result.append(middle)
    return result


def reopen(report, out):
    r = json.loads(Path(report).read_text())
    scene = bpy.data.scenes[r['scene_name']]
    bpy.context.window.scene = scene
    data = r['manifest']; nodes = {n['id']: n for n in data['nodes']}
    rig = bpy.data.objects[r['rig_name']] if r['rig_name'] else None
    meshes = {key: bpy.data.objects[value] for key, value in r['mesh_names'].items()}
    w, h = data['source_size']
    def point(p): return Vector(((p[0]-w/2)*.01, (h/2-p[1])*.01, 0))
    errors = []
    for p in data['parts']:
        obj = meshes[p['id']]
        if p['node'] is not None:
            for v in obj.data.vertices:
                require(len(v.groups) == 1 and abs(v.groups[0].weight-1) < 1e-6 and
                        obj.vertex_groups[v.groups[0].group].name == bone_name(p['node']), 'invalid rigid weights')
        rank = sorted(data['parts'], key=lambda p: p['z_index']).index(p)
        require(abs(obj.location.z-rank*.005) < 1e-6, 'invalid layer depth')
    for clip in r['clips']:
        require(rig is not None, 'animation requires nodes')
        rig.animation_data.action = bpy.data.actions[r['actions'][clip['id']]]
        for case in samples(clip):
            scene.frame_set(math.floor(case['frame']), subframe=case['frame'] % 1)
            errors.append(measure(data, case, meshes, point))
    if not r['clips']:
        errors.append(measure(data, {}, meshes, point))
    count = 0
    for obj in meshes.values():
        for material in obj.data.materials:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    require(node.image is not None and node.image.packed_file is not None, 'unpacked/missing texture')
                    count += 1
    require(count == len(data['parts']), 'texture reference count mismatch')
    result = dict(status='ok', max_vertex_error_world=max(errors, default=0), checked_samples=len(errors), packed_textures=count, visual_review='pending')
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--motion-plan', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--resolution', nargs=2, type=int, metavar=('WIDTH', 'HEIGHT'))
    parser.add_argument('--reopen-report', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.reopen_report:
        reopen(args.reopen_report, args.out)
        return
    require(args.manifest is not None, '--manifest required for import')
    out = args.out.resolve(); manifest = args.manifest.resolve()
    require(not (out/'rig.blend').exists(), 'choose a new output directory: rig.blend already exists')
    data, clips, fps = prepare(manifest, json.loads(args.motion_plan.read_text()) if args.motion_plan else None)
    nodes = {n['id']: n for n in data['nodes']}
    # Blender names have byte limits; stable internal IDs retain arbitrary external IDs.
    import copy
    internal = copy.deepcopy(data)
    for n in internal['nodes']:
        n['id'] = bone_name(n['id'])
        n['parent'] = bone_name(n['parent']) if n['parent'] is not None else None
    for p in internal['parts']:
        p['node'] = bone_name(p['node']) if p['node'] is not None else None
    internal_nodes = {n['id']: n for n in internal['nodes']}
    motion = {'target_ranges': {k: n['rotation_range'] for k, n in internal_nodes.items() if n.get('rotation_range') is not None}}
    out.mkdir(parents=True, exist_ok=True)
    scene, rig, meshes, point, ranges = build(internal, motion, internal_nodes, manifest, out, False)
    scene.render.fps = fps
    if args.resolution:
        require(min(args.resolution) > 0, 'resolution must be positive')
        require(abs(args.resolution[0]/args.resolution[1]-data['source_size'][0]/data['source_size'][1]) < 1e-5,
                'resolution must preserve source aspect ratio')
        scene.render.resolution_x, scene.render.resolution_y = args.resolution
    for p in data['parts']:
        image = next(n.image for n in meshes[p['id']].data.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE')
        require(list(image.size) == p['pixel_size'], 'image size mismatch')
    if rig:
        rig['mode'] = 'explicit_data_unreviewed'
        for pb in rig.pose.bones:
            pb.lock_location = (False, False, True); pb.lock_scale = (False, False, True)
            pb.lock_rotation = (True, True, False)
    actions, errors = {}, []
    for ci, clip in enumerate(clips):
        require(rig is not None, 'animation requires nodes')
        rig.animation_data_create(); rig.animation_data.action = None
        for case in sorted(clip['frames'], key=lambda c: c['frame']):
            scene.frame_set(case['frame']); set_pose(rig, nodes, case)
            for pb in rig.pose.bones:
                for channel in ('rotation_euler', 'location', 'scale'):
                    pb.keyframe_insert(data_path=channel, frame=case['frame'])
            errors.append(measure(data, case, meshes, point))
            if args.render:
                scene.render.filepath = str(out/'preview'/f'clip-{ci:03d}-frame-{case["frame"]:08d}.png')
                bpy.ops.render.render(write_still=True)
        action = rig.animation_data.action
        action.name = 'SPP_action_'+hashlib.sha256(clip['id'].encode()).hexdigest()[:20]
        action.use_fake_user = True
        # Linear between supplied keys; no procedural action design or IK assumptions.
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        actions[clip['id']] = action.name
    if not clips:
        errors.append(measure(data, {}, meshes, point))
        if args.render:
            scene.render.filepath = str(out/'preview'/'rest.png'); bpy.ops.render.render(write_still=True)
    if clips:
        rig.animation_data.action = bpy.data.actions[actions[clips[0]['id']]]
        scene.frame_start = min(c['frame'] for c in clips[0]['frames'])
        scene.frame_end = max(c['frame'] for c in clips[0]['frames'])
        scene.frame_set(scene.frame_start)
    r = dict(status='ok', manifest=data, clips=clips, actions=actions, scene_name=scene.name,
             rig_name=rig.name if rig else None, mesh_names={k: o.name for k, o in meshes.items()},
             max_vertex_error_world=max(errors, default=0), visual_review='pending',
             checked_samples=len(errors), blender_version=bpy.app.version_string)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'rig.blend'))
    (out/'io-report.json').write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in r.items() if k not in ('manifest', 'clips', 'mesh_names')}))


if __name__ == '__main__':
    main()
