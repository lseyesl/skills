"""Prepare a portable lantern GLB and publish it only after real round-trip checks."""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from build_lantern import TASK, anchors
from capture_reference import VIEWS, camera, render, workbench
from render_feature_review import configure_scene
from review_p1 import FINISHES, shader_for
from run_pilot import openings
from stage_guard import file_input
from validate_glb_roundtrip import inventory, verify, write


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def select(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if {obj.name for obj in bpy.context.selected_objects} != {obj.name for obj in objects}:
        raise RuntimeError("Could not select the exact export meshes")


def swept_uvs(obj, layer):
    """Unroll the sweep by ring angle and traveled length, with separate end caps."""
    mesh = obj.data
    sides = obj["cap_ring_size"]
    rings = [mesh.vertices[start:start+sides] for start in range(0, len(mesh.vertices), sides)]
    centers = [sum((vert.co for vert in ring), Vector()) / sides for ring in rings]
    lengths = [0.0]
    for a, b in zip(centers, centers[1:]):
        lengths.append(lengths[-1] + (b-a).length)
    radius = sum((vert.co-centers[0]).length for vert in rings[0]) / sides
    width = min(0.56, 0.90 * math.tau * radius / lengths[-1])
    cap_radius = min(0.08, width / math.tau)
    for face in mesh.polygons:
        angular = {mesh.loops[i].vertex_index % sides for i in face.loop_indices}
        wraps = 0 in angular and sides-1 in angular
        for i in face.loop_indices:
            ring, side = divmod(mesh.loops[i].vertex_index, sides)
            if len(face.vertices) == sides:
                theta = math.tau * side / sides
                uv = (0.80 + cap_radius*math.cos(theta), (0.25 if ring == 0 else 0.55) + cap_radius*math.sin(theta))
            else:
                if wraps and side == 0:
                    side = sides
                uv = (0.05 + width*side/sides, 0.05 + 0.90*lengths[ring]/lengths[-1])
            layer.data[i].uv = uv


def prepare_uvs(objects):
    uv_op = bpy.ops.uv.smart_project
    if "island_margin" not in uv_op.get_rna_type().properties:
        raise RuntimeError("Missing smart_project island_margin")
    for obj in objects:
        if len(obj.data.uv_layers):
            raise ValueError(f"Unexpected UV layers on the P0 fixture: {obj.name}")
        layer = obj.data.uv_layers.new(name="UVMap")
        swept = obj.get("lantern_module") in {"bail", "supports"}
        if swept:
            swept_uvs(obj, layer)
        bm = bmesh.new()
        try:
            bm.from_mesh(obj.data)
            bmesh.ops.triangulate(bm, faces=list(bm.faces))
            bm.to_mesh(obj.data)
        finally:
            bm.free()
        obj.data.update()
        if swept:
            continue
        select([obj])
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            bpy.ops.mesh.select_all(action="SELECT")
            if "FINISHED" not in uv_op(island_margin=0.02):
                raise RuntimeError(f"UV unwrap failed for {obj.name}")
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")


def load_map(path, *, color):
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        image.colorspace_settings.name = "sRGB" if color else "Non-Color"
        image.scale(512, 512)
        pixels = np.empty(512 * 512 * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        return np.clip(pixels.reshape(-1, 4), 0, 1)
    finally:
        bpy.data.images.remove(image)


def png(path, rgb, color_space):
    image = bpy.data.images.new(path.stem, width=512, height=512, alpha=False)
    try:
        image.colorspace_settings.name = color_space
        rgba = np.column_stack((rgb, np.ones(len(rgb), dtype=np.float32)))
        image.pixels.foreach_set(rgba.astype(np.float32).ravel())
        image.filepath_raw = str(path)
        image.file_format = "PNG"
        image.save()
    finally:
        bpy.data.images.remove(image)
    result = bpy.data.images.load(str(path), check_existing=False)
    result.colorspace_settings.name = color_space
    result.pack()
    return result


def bind_materials(p1, out):
    source = read(HERE / "p1-review.json")["source"]
    maps, files = {}, {}
    for role in ("base_color", "roughness", "metallic"):
        path = p1 / "textures" / source["id"] / f"{role}.jpg"
        files[role] = file_input(path)
        if files[role]["sha256"] != source["maps"][role]["sha256"]:
            raise RuntimeError(f"P1 source map changed: {role}")
        maps[role] = load_map(path, color=role == "base_color")
    color = maps["base_color"][:, :3]
    linear = np.where(color <= 0.04045, color/12.92, ((color+0.055)/1.055)**2.4)
    assets = out / "delivery-textures"
    assets.mkdir(exist_ok=True)
    for role, (tone, roughness, metallic) in FINISHES.items():
        material = bpy.data.materials[f"{TASK}::{role}"]
        shader = shader_for(material)
        tree = material.node_tree
        tinted = 0.8*np.array(tone[:3]) + 0.2*linear
        srgb = np.where(tinted <= 0.0031308, tinted*12.92, 1.055*tinted**(1/2.4)-0.055)
        mr = np.column_stack((np.ones(len(color)),
                              roughness[0] + (roughness[1]-roughness[0])*maps["roughness"][:, 0],
                              metallic[0] + (metallic[1]-metallic[0])*maps["metallic"][:, 0]))
        diffuse = tree.nodes.new("ShaderNodeTexImage")
        diffuse.image = png(assets / f"{role}_base_color.png", srgb, "sRGB")
        packed = tree.nodes.new("ShaderNodeTexImage")
        packed.image = png(assets / f"{role}_metallic_roughness.png", mr, "Non-Color")
        separate = tree.nodes.new("ShaderNodeSeparateColor")
        tree.links.new(diffuse.outputs["Color"], shader.inputs["Base Color"])
        tree.links.new(packed.outputs["Color"], separate.inputs["Color"])
        tree.links.new(separate.outputs["Green"], shader.inputs["Roughness"])
        tree.links.new(separate.outputs["Blue"], shader.inputs["Metallic"])
    glass = shader_for(bpy.data.materials[f"{TASK}::glass"])
    glass.inputs["Base Color"].default_value = (0.11, 0.17, 0.18, 1)
    glass.inputs["Roughness"].default_value = 0.25
    return {"asset": source["asset"], "url": source["asset_url"], "creator": source["creator"],
            "license": source["license"], "maps": files, "policy": "UV-mapped base color and packed G roughness/B metal."}


def cast_x(obj, x, y, z, direction):
    inverse = obj.matrix_world.inverted()
    hit, point, _, _ = obj.ray_cast(inverse @ Vector((x, y, z)), inverse.to_3x3() @ Vector((direction, 0, 0)))
    return (obj.matrix_world @ point).x if hit else None


def probe_features(scene, guide, expected_seats):
    result = openings(scene, guide)
    checks = {"vent_and_loop": {**result, "passed": result["vent_clear_rays"] == result["vent_sample_rays"]
                                 and result["lifting_loop_center_clear"]}}
    graph = bpy.context.evaluated_depsgraph_get()
    objects = {obj.name.rsplit("::", 1)[-1]: obj.evaluated_get(graph) for obj in scene.objects if obj.type == "MESH"}
    for key, seat in expected_seats.items():
        side, part = key.split("_")
        sign = -1 if side == "left" else 1
        _, y, z = seat["tube_endpoint_m"]
        tube = objects.get(side)
        target = objects.get({"hood": "bell", "reservoir": "reservoir"}[part])
        end = cast_x(tube, 0, y, z, sign) if tube else None
        surface = cast_x(target, sign*0.09, y, z, -sign) if target else None
        gap = None if end is None or surface is None else sign*(end-surface)*1000
        expected = seat["signed_gap_mm"]
        checks[key] = {"signed_gap_mm": gap, "source_mm": expected, "probe_yz_m": [y, z],
                       "passed": gap is not None and gap <= -1 and abs(gap-expected) <= 0.10}
    return checks


def previews(out, frame):
    scene = bpy.context.scene
    target = frame["target"]
    configure_scene(scene, {"target": target, "direction": VIEWS["iso"], "span": 0.35},
                    {"center": target, "scale": 0.17}, 560, 24)
    render(scene, out / "reimport-material.png")
    workbench(scene, mask=False)
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (0.64, 0.64, 0.64)
    for key, center, span in (("vent", (0, 0, 0.198), 0.072), ("joint", (0.026, 0, 0.168), 0.045)):
        camera(scene, center, VIEWS["front"], span=span, resolution=480)
        render(scene, out / f"reimport-{key}.png")


def main(p0, p1, out):
    p0, p1, out = (path.resolve() for path in (p0, p1, out))
    if out in (p0, p1):
        raise ValueError("Use a separate directory for P2")
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "roundtrip.json"
    write(report_path, {"status": "running"})
    try:
        state = read(p0 / "verification.json")
        original = file_input(p0 / "after.blend")
        if state["status"] != "passed" or original["sha256"] != state["snapshot_sha256"]["after"]:
            raise RuntimeError("The accepted P0 snapshot is stale")
        bpy.ops.wm.open_mainfile(filepath=original["path"], use_scripts=False, load_ui=False)
        scene = bpy.context.scene
        if scene.unit_settings.scale_length != 1:
            raise ValueError("Expected one Blender unit per meter")
        guide = anchors(scene)
        objects = sorted(bpy.data.collections[f"{TASK}::model"].objects, key=lambda obj: obj.name)
        prepare_uvs(objects)
        material_source = bind_materials(p1, out)
        select(objects)
        source = inventory(objects)
        bpy.context.preferences.filepaths.save_version = 0
        staging = out / "delivery-source.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(staging))
        candidate = out / "iron-lantern.candidate.glb"
        target = out / "iron-lantern.glb"
        opts = {"export_format": "GLB", "use_selection": True, "export_yup": True, "export_apply": False,
                "export_materials": "EXPORT", "export_image_format": "AUTO", "export_texcoords": True,
                "export_normals": True, "export_animations": False, "export_draco_mesh_compression_enable": False}
        unknown = opts.keys() - set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
        if unknown:
            raise RuntimeError(f"Unsupported GLB export options: {sorted(unknown)}")
        if "FINISHED" not in bpy.ops.export_scene.gltf(filepath=str(candidate), **opts):
            raise RuntimeError("GLB exporter failed")
        report = verify(source, candidate, probes=lambda scene: probe_features(scene, guide, state["after"]["seats"]))
        report.update(source_blend=original, delivery_source=file_input(staging), material_source=material_source,
                      export_options=opts, uv_policy="One packed 0-1 layout per mesh. Material textures repeat across separate meshes.")
        if report["status"] != "passed":
            write(report_path, report)
            raise RuntimeError(f"Rejected GLB: {report['failed_checks']}")
        previews(out, read(p0 / "reference-frame.json"))
        if file_input(p0 / "after.blend") != original or file_input(candidate) != {
            key: report["glb"][key] for key in ("path", "sha256")
        }:
            raise RuntimeError("Source or candidate changed during review")
        os.replace(candidate, target)
        report["glb"]["path"] = str(target)
        report["images"] = [file_input(out / f"reimport-{key}.png") for key in ("material", "vent", "joint")]
        write(report_path, report)
    except Exception as exc:
        if read(report_path)["status"] == "running":
            write(report_path, {"status": "failed", "error": str(exc)})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("p0", "p1", "out"):
        parser.add_argument(key, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    main(args.p0, args.p1, args.out)
