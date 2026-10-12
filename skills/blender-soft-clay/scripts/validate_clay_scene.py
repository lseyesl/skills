"""Read-only structural, animation, framing and output QA; JSON with manual gates."""
from pathlib import Path
import glob
import json
import math
import sys

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clay_common import (OWNER_KEY, cli, curves_for, emit, parse, scope, socket, write_json)


def check_outputs(paths):
    results = []
    for path in paths:
        path = Path(path).resolve()
        result = {"path": str(path), "ok": False}
        image = None
        try:
            if not path.is_file() or not path.stat().st_size:
                raise ValueError("Missing/empty output")
            image = bpy.data.images.load(str(path), check_existing=False)
            width, height = image.size
            if min(width, height) < 1:
                raise ValueError("Output cannot be decoded")
            pixels = image.pixels[:]
            if not pixels or not all(math.isfinite(v) for v in pixels):
                raise ValueError("Nonfinite/empty pixels")
            rgb = [pixels[i] for i in range(0, len(pixels), max(4, len(pixels) // 1024 // 4 * 4))]
            result.update(ok=True, size=[width, height], bytes=path.stat().st_size,
                          sampled_red_range=max(rgb) - min(rgb))
        except (RuntimeError, ValueError) as exc:
            result["error"] = str(exc)
        finally:
            if image:
                bpy.data.images.remove(image)
        results.append(result)
    return results


def geometry_signature(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    values = [v for row in evaluated.matrix_world for v in row]
    if obj.type == "ARMATURE":
        values += [v for bone in evaluated.pose.bones for row in bone.matrix for v in row]
    if obj.type == "MESH":
        mesh = evaluated.to_mesh()
        try:
            values += [v for vertex in mesh.vertices for v in vertex.co]
        finally:
            evaluated.to_mesh_clear()
    return values


def validate_scene(scene, config, owner="soft-clay", objects=None, frames=None, outputs=None,
                   expectations=None):
    if bpy.context.scene != scene:
        raise RuntimeError("QA requires the requested scene to be active for evaluated depsgraph checks")
    q = config["quality"]
    owned_scope = scope(scene, owner)
    objects = list(objects) if objects is not None else [
        o for o in scene.objects if o.get(OWNER_KEY) == owned_scope]
    report = {"blender": bpy.app.version_string, "scene": scene.name,
              "errors": [], "warnings": [], "meshes": [], "materials": [],
              "animation": [], "manual_review_required": [
                  "silhouette/proportions against approved design",
                  "matte color, micro-relief, exposure and soft contact shadows in renders",
                  "contact/penetration, deformation, motion rhythm and seam velocity",
                  "multi-shot palette/exposure/framing consistency"], "visual_approved": False}
    errors, warnings = report["errors"], report["warnings"]
    if not objects:
        errors.append("No QA targets; pass --objects for existing unowned assets")
    if not scene.camera or scene.camera.name not in scene.objects:
        errors.append("No camera linked to scene")
    areas = [o for o in scene.objects if o.type == "LIGHT" and o.data.type == "AREA"
             and not o.hide_render and o.data.energy > 0]
    if not areas:
        errors.append("No visible, powered Area light")
    elif any(o.data.size <= 0 or not o.data.use_shadow for o in areas):
        warnings.append("Area light size/shadow settings need review")
    if not scene.world:
        warnings.append("No environment world")
    if scene.frame_end < scene.frame_start or scene.render.fps < 1:
        errors.append("Invalid animation range/FPS")
    expected = config["render"]
    for actual, wanted, label in (
        (scene.render.resolution_x, expected["width"], "width"),
        (scene.render.resolution_y, expected["height"], "height"),
        (scene.render.fps, expected["fps"], "fps"),
        (scene.render.fps_base, expected["fps_base"], "fps_base"),
        (scene.render.resolution_percentage, expected["percentage"], "percentage"),
    ):
        if actual != wanted:
            errors.append(f"Render {label} differs from requested profile")
    for prop in ("view_transform", "look"):
        if expected[prop] != "KEEP" and getattr(scene.view_settings, prop) != expected[prop]:
            errors.append(f"Color management {prop} differs from requested profile")
    if abs(scene.view_settings.exposure - expected["exposure"]) > 1e-6:
        errors.append("Exposure differs from requested profile")
    # Project supplied dimensions at the current evaluation frame, not inferred geometry.
    for name, entry in (expectations or {}).items():
        obj = scene.objects.get(name)
        if obj is None:
            errors.append(f"Missing expected asset: {name}")
            continue
        wanted = entry.get("dimensions")
        tolerance = entry.get("tolerance", 0.01)
        if (not isinstance(wanted, list) or len(wanted) != 3 or
                not all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in wanted)
                or not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or tolerance < 0):
            raise ValueError(f"Invalid dimension expectation: {name}")
        actual = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).dimensions
        if any(abs(a - b) > tolerance for a, b in zip(actual, wanted)):
            errors.append(f"Dimension/proportion expectation mismatch: {name}")
    for obj in objects:
        if obj.name not in scene.objects:
            errors.append(f"QA target not linked to scene: {obj.name}")
            continue
        if any(not math.isfinite(v) for row in obj.matrix_world for v in row):
            errors.append(f"Nonfinite transform: {obj.name}")
        if min(abs(v) for v in obj.scale) < 1e-8:
            errors.append(f"Zero scale: {obj.name}")
        if obj.type != "MESH":
            continue
        mesh = obj.data
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            bad_faces = sum(f.calc_area() < 1e-12 for f in bm.faces)
            boundary = sum(not e.is_manifold for e in bm.edges)
            loose = sum(not v.link_faces for v in bm.verts)
        finally:
            bm.free()
        item = {"object": obj.name, "base_faces": len(mesh.polygons),
                "nonmanifold_edges": boundary, "degenerate_faces": bad_faces, "loose_vertices": loose}
        report["meshes"].append(item)
        if bad_faces or loose:
            errors.append(f"Degenerate/loose geometry: {obj.name}")
        if len(mesh.polygons) > q["max_faces"]:
            errors.append(f"Face budget exceeded: {obj.name}")
        if boundary and q["require_manifold"]:
            errors.append(f"Nonmanifold geometry: {obj.name}")
        for modifier in obj.modifiers:
            if modifier.type == "ARMATURE":
                rig = modifier.object
                if not rig or rig.type != "ARMATURE" or rig.name not in scene.objects:
                    errors.append(f"Invalid armature target: {obj.name}")
                    continue
                deform = {b.name for b in rig.data.bones if b.use_deform}
                indices = {g.index for g in obj.vertex_groups if g.name in deform}
                bad_weights = 0
                for vertex in mesh.vertices:
                    weights = [g.weight for g in vertex.groups if g.group in indices and g.weight > 0]
                    if not weights or abs(sum(weights) - 1) > 0.001:
                        bad_weights += 1
                if bad_weights:
                    errors.append(f"{obj.name}: {bad_weights} vertices have missing/unnormalized deform weights")
                if modifier.use_bone_envelopes:
                    warnings.append(f"Envelope weights need evaluated review: {obj.name}")
        if not mesh.materials or any(m is None for m in mesh.materials):
            errors.append(f"Missing material slots: {obj.name}")
    materials = {m for o in objects if o.type == "MESH" for m in o.data.materials if m}
    for material in sorted(materials, key=lambda m: m.name):
        principled = [n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"] if material.use_nodes else []
        if len(principled) != 1:
            errors.append(f"Expected one clay Principled shader: {material.name}")
            continue
        rough = socket(principled[0], "Roughness")
        metal = socket(principled[0], "Metallic")
        if rough.is_linked or metal.is_linked:
            warnings.append(f"Driven roughness/metallic requires evaluated material review: {material.name}")
        elif rough.default_value < q["min_roughness"] or metal.default_value != 0:
            errors.append(f"Non-matte/non-dielectric clay: {material.name}")
        report["materials"].append({"name": material.name, "roughness": rough.default_value})
        if material.get("soft_clay_parameters"):
            params = json.loads(material["soft_clay_parameters"])
            for key, value in config["material"].items():
                if abs(params[key] - value) > 1e-6:
                    errors.append(f"Material profile mismatch: {material.name}/{key}")
            for field, identifiers in (("roughness", ("Roughness",)),
                                       ("specular", ("Specular IOR Level", "Specular"))):
                input_socket = socket(principled[0], *identifiers)
                if input_socket.is_linked or abs(input_socket.default_value - config["material"][field]) > 1e-6:
                    errors.append(f"Actual shader parameter mismatch: {material.name}/{field}")
            normal = socket(principled[0], "Normal")
            base = socket(principled[0], "Base Color")
            if not normal.is_linked or not base.is_linked:
                errors.append(f"Disconnected clay shader: {material.name}")
    original_frame, original_subframe = scene.frame_current, scene.frame_subframe
    frames = frames or sorted({scene.frame_start, (scene.frame_start + scene.frame_end) // 2,
                              scene.frame_end, scene.frame_end + 1})
    try:
        signatures = {}
        for frame in sorted(set(frames) | {scene.frame_start, scene.frame_end + 1}):
            scene.frame_set(frame)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            for obj in objects:
                signature = geometry_signature(obj, depsgraph)
                if any(not math.isfinite(v) for v in signature):
                    errors.append(f"Nonfinite evaluated geometry: {obj.name} at {frame}")
                if obj.get("soft_clay_loop"):
                    signatures[(obj.name, frame)] = signature
                if obj.type == "MESH":
                    evaluated = obj.evaluated_get(depsgraph)
                    evaluated_mesh = evaluated.to_mesh()
                    try:
                        face_count = len(evaluated_mesh.polygons)
                    finally:
                        evaluated.to_mesh_clear()
                    if face_count > q["max_faces"]:
                        errors.append(f"Evaluated face budget exceeded: {obj.name} at {frame}")
                    if scene.camera and not obj.get("soft_clay_background"):
                        points = [world_to_camera_view(scene, scene.camera, evaluated.matrix_world @ Vector(v))
                                  for v in evaluated.bound_box]
                        if any(p.x < 0 or p.x > 1 or p.y < 0 or p.y > 1 or
                               p.z < scene.camera.data.clip_start or p.z > scene.camera.data.clip_end
                               for p in points):
                            errors.append(f"Camera crop/clip at frame {frame}: {obj.name}")
        for obj in objects:
            if obj.get("soft_clay_loop"):
                first = signatures[(obj.name, scene.frame_start)]
                last = signatures[(obj.name, scene.frame_end + 1)]
                delta = max((abs(a - b) for a, b in zip(first, last)), default=0)
                ok = len(first) == len(last) and delta <= q["loop_tolerance"]
                report["animation"].append({"object": obj.name, "loop_endpoint_ok": ok, "max_delta": delta})
                if not ok:
                    errors.append(f"Loop endpoint mismatch: {obj.name}")
                hold = obj.get("soft_clay_hold_frames", 1)
                if hold > 1:
                    if (scene.frame_end - scene.frame_start + 1) % hold:
                        errors.append(f"Loop period is not divisible by hold step: {obj.name}")
                    for fc in curves_for(obj):
                        for f in range(scene.frame_start, scene.frame_end + 1):
                            anchor = scene.frame_start + ((f - scene.frame_start) // hold) * hold
                            if abs(fc.evaluate(f) - fc.evaluate(anchor)) > q["loop_tolerance"]:
                                errors.append(f"Hold timing mismatch: {obj.name} at {f}")
                                break
    finally:
        scene.frame_set(original_frame, subframe=original_subframe)
    report["outputs"] = check_outputs(outputs or [])
    if any(not o["ok"] for o in report["outputs"]):
        errors.append("Invalid rendered output(s)")
    expected_size = [max(1, int(config["render"][key] * config["render"]["percentage"] / 100))
                     for key in ("width", "height")]
    if any(o["ok"] and o["size"] != expected_size for o in report["outputs"]):
        errors.append("Rendered dimensions differ from profile")
    report["errors"] = sorted(set(errors))
    report["warnings"] = sorted(set(warnings))
    report["structural_ok"] = not report["errors"]
    # Do not approve silhouette, penetration, color or seam velocity automatically.
    return report


def compare_shots(scenes):
    """Compare style fields across stored profiles AND actual color-management settings."""
    records = []
    for scene in scenes:
        raw = scene.get("soft_clay_profile")
        if not raw:
            raise ValueError(f"Missing soft_clay_profile: {scene.name}")
        config = json.loads(raw)
        records.append({"palette": config["palette"], "material": config["material"],
                        "lighting": config["lighting"],
                        "view_transform": scene.view_settings.view_transform,
                        "look": scene.view_settings.look, "exposure": scene.view_settings.exposure,
                        "gamma": scene.view_settings.gamma,
                        "fps": scene.render.fps / scene.render.fps_base})
    return {"ok": bool(records) and all(r == records[0] for r in records),
            "scenes": [s.name for s in scenes], "note": "Intentional shot differences need visual approval"}


def main():
    parser = cli(__doc__)
    parser.add_argument("--objects", nargs="+", help="Explicit QA targets; otherwise owned objects")
    parser.add_argument("--frames", nargs="+", type=int)
    parser.add_argument("--images", nargs="+", help="Image paths/globs; video needs separate decoder review")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--shots", nargs="+", help="Compare these existing scene profiles")
    parser.add_argument("--expectations", type=Path,
                        help="JSON mapping object names to dimensions and absolute tolerance")
    args, config, scene = parse(parser)
    if bpy.context.scene != scene:
        raise RuntimeError("QA uses active depsgraph; make the requested scene active before running")
    objects = None
    if args.objects:
        objects = [scene.objects.get(n) for n in args.objects]
        if any(o is None for o in objects):
            raise ValueError("Unknown QA object")
    paths = []
    for pattern in args.images or []:
        matches = glob.glob(pattern)
        if not matches:
            raise FileNotFoundError(f"No images match {pattern}")
        paths.extend(matches)
    expectations = json.loads(args.expectations.read_text()) if args.expectations else None
    report = validate_scene(scene, config, args.owner, objects, args.frames, paths, expectations)
    if args.shots:
        scenes = [bpy.data.scenes.get(n) for n in args.shots]
        if any(s is None for s in scenes):
            raise ValueError("Unknown shot scene")
        report["shots"] = compare_shots(scenes)
        if not report["shots"]["ok"]:
            report["structural_ok"] = False
            report["errors"].append("Shot profile mismatch")
    if args.report:
        write_json(args.report, report)
    emit("quality", report=report)
    if not report["structural_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
