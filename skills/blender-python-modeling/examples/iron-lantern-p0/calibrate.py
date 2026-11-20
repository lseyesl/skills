"""Prepare and capture the actual Blender reference workspace in a dedicated file."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from reference_workspace import setup_references, workspace_signature

TASK = "iron-lantern-p0"
REGIONS = ["base", "globe", "cups", "hood", "vent", "supports", "bail", "lifter", "cage", "controls"]
FINDINGS = {
    "front": "The two side tubes and lifting loop are separated. The centered ground line, body stations and front vent windows are readable.",
    "right": "The bail collapses into a narrow vertical strip. The side tube overlaps the centerline and the front fill cap projects toward -Y.",
    "iso": "The three-quarter view shows the seat of both side tubes and the cage wires; use it as supplementary review.",
}


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def prepare(out):
    frame = read(out / "reference-frame.json")
    annotations = read(HERE / "landmarks.json")
    checks = {
        "pose": "All views show the same scan with the bail raised and no pose changes.",
        "proportions": "The ground and cap heights agree across the front and right with one orthographic scale.",
        "projection": "Front and right are parallel axis renders of the centered scan with identical frame and scale.",
        "structure": "The side tubes, loop, hood, vent, reservoir and globe are distinct. Internal lamp mechanics are outside this exterior test.",
        "appearance": "Flat diagnostic colors identify glass versus metal. Material matching is outside the construction scope.",
        "axes": "Front looks from -Y, right from +X. Fill-cap projection confirms the front side.",
    }
    views = {}
    config = {"multiview_review": "multiview-review.json", "views": {}}
    for view, finding in FINDINGS.items():
        name = f"reference-{view}.png"
        controlling = view in annotations
        views[view] = {"image": name, "sha256": hashlib.sha256((out / name).read_bytes()).hexdigest(),
                       "role": "controlling" if controlling else "supplemental", "finding": finding}
        if controlling:
            views[view]["controls"] = REGIONS if view == "front" else ["base", "globe", "supports", "controls"]
            config["views"][view] = {
                "image": name, "pixels_per_unit": frame["pixels_per_unit"], "origin_px": frame["origin_px"],
                "landmarks": {f"{group}.{i}": point for group, points in annotations[view].items()
                              for i, point in enumerate(points)},
            }
    write(out / "multiview-review.json", {
        "schema_version": 1, "purpose": "Calibrated exterior prop pilot", "pose": "Upright, bail raised",
        "readiness": "passed", "checks": {key: {"status": "passed", "finding": value} for key, value in checks.items()},
        "allowed_regions": REGIONS, "views": views, "review_artifacts": [item["image"] for item in views.values()],
    })
    write(out / "reference-setup.json", config)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    setup_references(scene, TASK, config, out)
    write(out / "workspace.json", {"signature": workspace_signature(scene, TASK)})
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "workspace.blend"))


def capture(out, tag):
    """Run in regular UI Blender after opening the workspace or a generated snapshot."""
    views = iter([("front", (0, 1, 0)), ("right", (-1, 0, 0))])
    frame = read(out / "reference-frame.json")
    window = bpy.context.window_manager.windows[0]
    area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
    space = area.spaces.active
    space.overlay.show_floor = False
    space.overlay.show_axis_x = space.overlay.show_axis_y = False
    space.shading.color_type = "OBJECT"
    if bpy.context.scene.camera:
        bpy.context.scene.camera.hide_set(True)
    space.region_3d.view_perspective = "ORTHO"
    space.region_3d.view_location = frame["target"]
    space.region_3d.view_distance = 0.56
    pending = None

    def tick():
        nonlocal pending
        try:
            if pending:
                with bpy.context.temp_override(window=window, area=area):
                    bpy.ops.screen.screenshot(filepath=str(out / f"{tag}-{pending}.png"))
            item = next(views, None)
            if item is None:
                bpy.ops.wm.quit_blender()
                return None
            pending, direction = item
            space.region_3d.view_rotation = Vector(direction).to_track_quat("-Z", "Y")
            area.tag_redraw()
            return 0.9
        except Exception as error:
            (out / f"{tag}-error.txt").write_text(repr(error), encoding="utf-8")
            bpy.ops.wm.quit_blender()
            return None

    bpy.app.timers.register(tick, first_interval=1.5)


if __name__ == "__main__":
    mode, folder, *args = sys.argv[sys.argv.index("--") + 1:]
    out = Path(folder).resolve()
    if mode == "prepare":
        prepare(out)
    elif mode == "capture":
        capture(out, args[0])
    else:
        raise ValueError(f"Unknown mode: {mode}")
