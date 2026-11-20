"""Build and evaluate three isolated corrections using real Blender geometry and renders."""

import sys
from hashlib import sha256
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_lantern import MODULES, anchors, rebuild
from calibrate import TASK, read, write
from capture_reference import VIEWS, camera, render, workbench
from reference_workspace import appearance_signature, model_signature, require_reference_review, workspace_signature
from validate_module_ledger import validate_ledger


INITIAL = {"base_width": 1.18, "vent_blocked": True, "hood_seat": 0.0055}
CORRECTIONS = [
    ("base", "base_width", 1.0),
    ("vent", "vent_blocked", False),
    ("supports", "hood_seat", -0.0034),
]


def ledger(collection=None):
    modules = []
    for key, (name, feature, count) in MODULES.items():
        objects = [obj for obj in collection.objects if obj.get("lantern_module") == key] if collection else []
        implemented = sum("diagnostic" not in obj.name and "stem" not in obj.name for obj in objects)
        modules.append({
            "id": key, "name": name, "evidence": "observed", "source_views": ["front", "right", "iso"],
            "priority": "primary" if key in {"base", "globe", "hood", "vent", "supports", "bail"} else "secondary",
            "required": True, "expected_instances": count, "implemented_instances": implemented,
            "signature_features": [feature], "matched_signature_features": [], "feature_reviews": [],
            "status": "blockout" if objects else "missing", "implementation_objects": [obj.name for obj in objects],
        })
    return {"schema_version": 1, "task_id": TASK, "target_stage": "blockout", "modules": modules}


def mask(path):
    im = bpy.data.images.load(str(path), check_existing=False)
    try:
        pixels = np.empty(len(im.pixels), dtype=np.float32)
        im.pixels.foreach_get(pixels)
        return pixels.reshape(im.size[1], im.size[0], 4)[::-1, :, 3] > 0.5
    finally:
        bpy.data.images.remove(im)


def silhouettes(scene, out, tag, frame, references):
    result = {}
    for view, reference in references.items():
        camera(scene, frame["target"], VIEWS[view])
        workbench(scene, mask=True)
        path = out / f"{tag}-{view}-mask.png"
        render(scene, path)
        candidate = mask(path)
        both = reference & candidate
        either = reference | candidate
        ppu = frame["pixels_per_unit"]
        bands = []
        # Pixel rows from the inspected, common 720px frame. Keep absolute scale fixed.
        for top, bottom in [(611, 631), (631, 651), (651, 671)]:
            widths = []
            for image in (reference, candidate):
                widths.append(float(np.mean(image[top:bottom].sum(axis=1))) * 1000 / ppu)
            bands.append({"rows": [top, bottom], "reference_mm": widths[0], "candidate_mm": widths[1],
                          "absolute_error_mm": abs(widths[0] - widths[1])})
        result[view] = {"iou": float(both.sum() / either.sum()), "reservoir_width_bands": bands}
    return result


def mesh_report(collection):
    records = {}
    graph = bpy.context.evaluated_depsgraph_get()
    for obj in collection.objects:
        bm = bmesh.new()
        try:
            bm.from_object(obj, graph)
            records[obj.name] = {"vertices": len(bm.verts), "faces": len(bm.faces),
                                 "nonmanifold_edges": sum(not e.is_manifold for e in bm.edges),
                                 "degenerate_faces": sum(f.calc_area() < 1e-12 for f in bm.faces)}
        finally:
            bm.free()
    return records


def openings(scene, a):
    graph = bpy.context.evaluated_depsgraph_get()
    mark = a["front"]["vent"][-1]
    paths = [(side*(mark.x + dx), mark.z + dz)
             for side in (-1, 1) for dx in (-0.002, -0.0007, 0.0007, 0.002)
             for dz in (-0.00065, 0.0, 0.00065)]
    open_count = sum(not scene.ray_cast(graph, (x, -0.20, z), (0, 1, 0), distance=0.40)[0] for x, z in paths)
    loop_z = (a["front"]["lifter"][0].z + a["front"]["lifter"][-1].z) / 2
    loop_open = not scene.ray_cast(graph, (0, -0.20, loop_z), (0, 1, 0), distance=0.40)[0]
    return {"vent_clear_rays": open_count, "vent_sample_rays": len(paths), "lifting_loop_center_clear": loop_open}


def seats(collection):
    graph = bpy.context.evaluated_depsgraph_get()
    by_name = {obj.name.rsplit("::", 1)[-1]: obj.evaluated_get(graph) for obj in collection.objects}
    result = {}
    for side, sign in (("left", -1), ("right", 1)):
        tube = by_name[side]
        count = tube["cap_ring_size"]
        vertices = tube.data.vertices
        if any(sign * (tube.matrix_world @ v.co).x <= 0 for v in vertices):
            raise RuntimeError(f"{side} support crosses the lantern centerline")
        for label, indices, target_name in (
            ("reservoir", range(count), "reservoir"),
            ("hood", range(len(vertices)-count, len(vertices)), "bell"),
        ):
            center = sum((tube.matrix_world @ vertices[i].co for i in indices), Vector()) / count
            target = by_name[target_name]
            inv = target.matrix_world.inverted()
            hit, point, _, _ = target.ray_cast(inv @ Vector((sign*0.09, center.y, center.z)),
                                                inv.to_3x3() @ Vector((-sign, 0, 0)))
            if not hit:
                raise RuntimeError(f"Seat probe missed the {target_name} mesh")
            surface = target.matrix_world @ point
            gap = sign * (center.x - surface.x)
            result[f"{side}_{label}"] = {"signed_gap_mm": 1000*gap, "seated": gap <= -0.001,
                                         "tube_endpoint_m": list(center), "seat_surface_m": list(surface)}
    return result


def signature(collection, module):
    other = [obj for obj in collection.objects if obj.get("lantern_module") != module]
    return {"geometry": model_signature(other), "materials": sorted(
        (obj.name, tuple(slot.material.name for slot in obj.material_slots), tuple(obj.color)) for obj in other)}


def measure(scene, collection, out, tag, frame, references):
    return {"silhouettes": silhouettes(scene, out, tag, frame, references),
            "openings": openings(scene, frame["anchors"]), "seats": seats(collection),
            "mesh": mesh_report(collection)}


def width_error(record):
    return sum(band["absolute_error_mm"] for view in record["silhouettes"].values()
               for band in view["reservoir_width_bands"])


def accept(module, before, after):
    no_major_iou_regression = all(after["silhouettes"][view]["iou"] >= metrics["iou"] - 0.005
                                  for view, metrics in before["silhouettes"].items())
    clean = all(not row["nonmanifold_edges"] and not row["degenerate_faces"] for row in after["mesh"].values())
    if module == "base":
        improvement = width_error(after) < width_error(before) * 0.5
    elif module == "vent":
        improvement = (before["openings"]["vent_clear_rays"] == 0 and
                       after["openings"]["vent_clear_rays"] == after["openings"]["vent_sample_rays"])
    else:
        improvement = (not before["seats"]["right_hood"]["seated"] and
                       all(row["seated"] for row in after["seats"].values()))
    return clean and no_major_iou_regression and improvement


def snapshot(scene, out, tag, target):
    workbench(scene)
    for view, direction in VIEWS.items():
        camera(scene, target, direction)
        render(scene, out / f"{tag}-{view}.png")
    for detail, center, span, direction in (
        ("vent", (0, 0, 0.198), 0.072, VIEWS["front"]),
        ("joint", (0.026, 0, 0.168), 0.045, VIEWS["front"]),
    ):
        camera(scene, center, direction, span=span, resolution=480)
        render(scene, out / f"{tag}-{detail}.png")
    camera(scene, target, VIEWS["iso"])
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                space = area.spaces.active
                space.shading.color_type = "OBJECT"
                space.overlay.show_floor = False
                space.region_3d.view_location = target
                space.region_3d.view_rotation = scene.camera.rotation_euler.to_quaternion()
                space.region_3d.view_distance = 0.50
                space.region_3d.view_perspective = "ORTHO"
    bpy.ops.wm.save_as_mainfile(filepath=str(out / f"{tag}.blend"))


def main(out):
    write(out / "verification.json", {"status": "running"})
    bpy.ops.wm.open_mainfile(filepath=str(out / "workspace.blend"))
    scene = bpy.context.scene
    require_reference_review(scene, TASK, out / "calibration-review.json")
    bpy.context.preferences.filepaths.save_version = 0
    frame = read(out / "reference-frame.json")
    frame["anchors"] = anchors(scene)
    refs = {view: mask(out / f"reference-{view}.png") for view in ("front", "right")}
    collection = bpy.data.collections.new(f"{TASK}::model")
    scene.collection.children.link(collection)
    write(out / "module-ledger-plan.json", ledger())
    params = INITIAL.copy()
    for module in MODULES:
        rebuild(collection, module, frame["anchors"], params)
    baseline = measure(scene, collection, out, "before", frame, refs)
    snapshot(scene, out, "before", frame["target"])
    report = {"status": "running", "blender": bpy.app.version_string, "reference_height_m": frame["height_m"],
              "before": baseline, "initial_parameters": params, "rounds": []}
    write(out / "verification.json", report)
    current = baseline
    for module, key, value in CORRECTIONS:
        unchanged = signature(collection, module)
        candidate = params | {key: value}
        rebuild(collection, module, frame["anchors"], candidate)
        metrics = measure(scene, collection, out, f"round-{module}", frame, refs)
        stable = signature(collection, module) == unchanged
        accepted = stable and accept(module, current, metrics)
        report["rounds"].append({"module": module, "parameter": key, "before": params[key], "after": value,
                                 "unaffected_modules_unchanged": stable, "accepted": accepted, "metrics": metrics})
        write(out / "verification.json", report)
        if not accepted:
            rebuild(collection, module, frame["anchors"], params)
            report["status"] = "rejected"
            write(out / "verification.json", report)
            raise RuntimeError(f"Rejected {module}; no corrected snapshot saved")
        current, params = metrics, candidate
    snapshot(scene, out, "after", frame["target"])
    report["after"] = current
    report["accepted_parameters"] = params
    points = [obj.matrix_world @ Vector(p) for obj in collection.objects for p in obj.bound_box]
    report["bounds_mm"] = [1000*(max(p[i] for p in points)-min(p[i] for p in points)) for i in range(3)]
    module_ledger = ledger(collection)
    write(out / "module-ledger.json", module_ledger)
    validation = validate_ledger(module_ledger)
    write(out / "module-ledger-validation.json", validation)
    if not validation["ok"]:
        raise RuntimeError(validation["errors"])
    report["status"] = "passed"
    report["snapshot_sha256"] = {tag: sha256((out / f"{tag}.blend").read_bytes()).hexdigest()
                                 for tag in ("before", "after")}
    write(out / "verification.json", report)


def review(out):
    """Bind separately inspected captures to the saved model and update the existing ledger."""
    report = read(out / "verification.json")
    findings = read(out / "comparison-findings.json")
    artifact = out / "after.blend"
    digest = sha256(artifact.read_bytes()).hexdigest()
    if report["status"] != "passed" or digest != report["snapshot_sha256"]["after"] or digest != findings["snapshot_sha256"]:
        raise RuntimeError("Comparison findings must refer to the current accepted snapshot")
    bpy.ops.wm.open_mainfile(filepath=str(artifact))
    scene = bpy.context.scene
    objects = list(bpy.data.collections[f"{TASK}::model"].objects)
    receipt = {"workspace_signature": workspace_signature(scene, TASK), "phase": "comparison",
               "status": "passed", "views": findings["views"],
               "model_signature": model_signature(objects), "appearance_signature": appearance_signature(scene, objects)}
    review_path = out / "comparison-review.json"
    write(review_path, receipt)
    require_reference_review(scene, TASK, review_path, phase="comparison", objects=objects)
    module_ledger = read(out / "module-ledger.json")
    for module in module_ledger["modules"]:
        evidence = findings["features"].get(module["id"])
        if not evidence:
            continue
        for key in ("reference", "candidate"):
            if not (out / evidence[key]).is_file():
                raise FileNotFoundError(evidence[key])
        feature, = module["signature_features"]
        module.update(status="matched", matched_signature_features=[feature],
                      feature_reviews=[dict(evidence, feature=feature, status="matched")])
    validation = validate_ledger(module_ledger)
    if not validation["ok"]:
        raise RuntimeError(validation["errors"])
    write(out / "module-ledger.json", module_ledger)
    write(out / "module-ledger-validation.json", validation)


if __name__ == "__main__":
    folder, *args = sys.argv[sys.argv.index("--") + 1:]
    out = Path(folder).resolve()
    if args == ["review"]:
        review(out)
    elif not args:
        main(out)
    else:
        raise ValueError(f"Unknown mode: {args}")
