"""Disposable abstract scene example; never clears the user's scene."""
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clay_common import cli, collection, emit, owned, parse, save_new, scope, tag, write_json
from create_clay_material import create_palette
from setup_clay_animation import setup_animation
from setup_clay_lighting import setup_lighting
from setup_render import render, setup_render
from validate_clay_scene import validate_scene


def build_demo(scene, config, owner="soft-clay"):
    scoped = scope(scene, owner)
    for obj in bpy.data.objects:
        if obj.get("soft_clay_owner") == scoped and obj.get("soft_clay_role", "").startswith("demo-"):
            if any(s != scene and obj.name in s.objects for s in bpy.data.scenes):
                raise RuntimeError("Demo object shared across scenes; refusing to rebuild")
            if obj.constraints or obj.library or obj.override_library:
                raise RuntimeError("Authored constraints/linked data on demo object; refusing to rebuild")
    palette = create_palette(scene, config, owner)
    colors = list(palette.values())
    col = collection(scene, scoped)
    scale = config["scale"]
    root = owned(bpy.data.objects, scoped, "demo-root", lambda n: bpy.data.objects.new(n, None))
    if root.name not in col.objects:
        col.objects.link(root)
    objects = [root]

    def geometry(role, kind, position, dimensions, index, smooth=False, parent=None):
        mesh = owned(bpy.data.meshes, scoped, role + "-mesh", bpy.data.meshes.new)
        obj = owned(bpy.data.objects, scoped, role, lambda n: bpy.data.objects.new(n, mesh))
        if obj.data != mesh or mesh.users > 1:
            raise RuntimeError("Demo data was shared; preserve it instead of rebuilding")
        if obj.name not in col.objects:
            col.objects.link(obj)
        bm = bmesh.new()
        try:
            if kind == "cube":
                bmesh.ops.create_cube(bm, size=1)
            elif kind == "sphere":
                bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.5)
            elif kind == "ico":
                bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.5)
            elif kind == "cone":
                bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=12,
                                     radius1=0.5, radius2=0.25, depth=1)
            bmesh.ops.transform(bm, matrix=Matrix.Diagonal(tuple(d * scale for d in dimensions) + (1,)),
                                verts=list(bm.verts))
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            bm.to_mesh(mesh)
        finally:
            bm.free()
        mesh.update()
        for polygon in mesh.polygons:
            polygon.use_smooth = smooth
        mesh.materials.clear()
        mesh.materials.append(colors[index % len(colors)])
        obj.parent = parent
        obj.location = Vector(position) * scale
        obj.rotation_euler = (0, 0, 0)
        obj.scale = (1, 1, 1)
        if kind in ("cube", "cone"):
            bevel = obj.modifiers.get("SoftClayBevel") or obj.modifiers.new("SoftClayBevel", "BEVEL")
            bevel.width = min(dimensions) * scale * 0.08
            bevel.segments = 2
            bevel.limit_method = "ANGLE"
        objects.append(obj)
        return obj

    ground = geometry("demo-ground", "cube", (0, 0, -0.15), (200, 200, 0.3), len(colors) - 1)
    ground["soft_clay_background"] = True
    geometry("demo-body", "ico", (0, 0, 0.85), (1.15, 0.9, 1.4), 0, True, root)
    geometry("demo-head", "sphere", (0, 0, 1.85), (0.85, 0.8, 0.85), 2, True, root)
    for side in (-1, 1):
        geometry(f"demo-foot-{side}", "cube", (side * 0.3, -0.18, 0.16), (0.38, 0.58, 0.32), 1,
                 False, root)
    geometry("demo-block", "cube", (-1.65, 0.4, 0.45), (0.9, 0.9, 0.9), 3)
    geometry("demo-cone", "cone", (1.6, 0.6, 0.6), (0.9, 0.9, 1.2), 1)
    geometry("demo-pebble", "ico", (1.25, -1.0, 0.3), (0.8, 0.7, 0.6), 2, True)
    start, end = config["render"]["frame_start"], config["render"]["frame_end"]
    period = end - start + 1
    if period < 4:
        raise ValueError("Demo loop needs at least four output frames")
    # Demo-owned animation only. Existing non-demo source actions are never cleared.
    if root.animation_data and root.animation_data.action:
        old = root.animation_data.action
        if old.get("soft_clay_owner") != scoped or old.users > 1:
            raise RuntimeError("Demo root action is unowned/shared; refusing to replace")
        root.animation_data_clear()
        bpy.data.actions.remove(old)
    for phase, height, tilt in ((0, 0, 0), (0.25, 0.18, 0.08), (0.5, 0, 0),
                                (0.75, 0.18, -0.08), (1, 0, 0)):
        root.location = (0, 0, height * scale)
        root.rotation_euler = (0, tilt, 0)
        frame = start + period * phase
        root.keyframe_insert(data_path="location", frame=frame)
        root.keyframe_insert(data_path="rotation_euler", frame=frame)
    tag(root.animation_data.action, scoped, "action-" + root.name)
    setup_render(scene, config)
    setup_animation(root, scene, config, owner)
    setup_lighting(scene, config, owner)
    scene.frame_set(start)
    bpy.context.view_layer.update()
    return objects


def main():
    parser = cli(__doc__)
    parser.add_argument("--name", default="Soft Clay Demo", help="New demo scene name")
    parser.add_argument("--output", type=Path, required=True, help="Artifact directory")
    parser.add_argument("--render", choices=("still", "animation"))
    parser.add_argument("--overwrite", action="store_true")
    args, config, _ = parse(parser)
    if bpy.data.scenes.get(args.name):
        raise ValueError("Demo scene already exists; choose a new --name")
    destination = args.output.expanduser().resolve()
    blend = destination / "demo.blend"
    if blend.exists() and not args.overwrite:
        raise FileExistsError(f"{blend} exists; select another output or --overwrite")
    scene = bpy.data.scenes.new(args.name)
    bpy.context.window.scene = scene
    objects = build_demo(scene, config, args.owner)
    prefix = destination / ("animation-" if args.render == "animation" else "preview.png")
    setup_render(scene, config, prefix)
    save_new(blend, args.overwrite)
    outputs = render(scene, args.render, args.overwrite) if args.render else []
    report = validate_scene(scene, config, args.owner, objects, outputs=outputs if config["render"]["format"] != "FFMPEG" else [])
    write_json(destination / "quality.json", report)
    emit("demo", blend=str(blend), outputs=outputs, structural_ok=report["structural_ok"])
    if not report["structural_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
