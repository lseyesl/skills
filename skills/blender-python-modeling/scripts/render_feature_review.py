"""Render a reference crop and fixed-camera clay/material pairs for ledger features."""

import argparse
import json
import math
import re
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage_guard import file_input, run_stage


VIEWS = ("before", "after")
CHANNELS = ("clay", "material")
FILENAMES = ("reference.png", *(f"{view}-{channel}.png" for view in VIEWS for channel in CHANNELS))


def vector(values, label):
    if len(values) != 3 or not all(math.isfinite(value) for value in values):
        raise ValueError(f"{label} requires three finite coordinates")
    return Vector(values)


def positive(value, label):
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be positive and finite")
    return value


def new_object(scene, name, data):
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    return obj


def aim(obj, target, location):
    obj.location = location
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def configure_scene(scene, camera, studio, resolution, samples):
    target = vector(camera["target"], "camera.target")
    direction = vector(camera["direction"], "camera.direction")
    positive(direction.length, "camera.direction length")
    span = positive(camera["span"], "camera.span")
    center = vector(studio["center"], "studio.center")
    scale = positive(studio["scale"], "studio.scale")

    for obj in scene.objects:
        if obj.type == "LIGHT":
            obj.hide_render = True
    rig = (
        ("key", (-1.6, -2.0, 2.4), 120, 1.3),
        ("fill", (1.7, -0.9, 0.5), 50, 1.0),
        ("rim", (0.4, 1.8, 1.6), 90, 1.1),
    )
    for name, direction_offset, power, size in rig:
        data = bpy.data.lights.new("Feature review " + name, "AREA")
        data.energy = power * scale**2
        data.shape = "DISK"
        data.size = size * scale
        aim(new_object(scene, data.name, data), center, center + Vector(direction_offset) * scale)
    world = bpy.data.worlds.new("Feature review world")
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (0.42, 0.42, 0.42, 1)
    background.inputs["Strength"].default_value = 0.45
    scene.world = world
    lens = bpy.data.cameras.new("Feature review camera")
    lens.type = "ORTHO"
    lens.ortho_scale = span
    distance = 5 * max(span, scale)
    lens.clip_start, lens.clip_end = distance / 1000, distance * 4
    scene.camera = new_object(scene, lens.name, lens)
    aim(scene.camera, target, target + direction.normalized() * distance)

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = True
    scene.render.use_border = scene.render.use_multiview = False
    scene.render.use_compositing = scene.render.use_sequencer = False
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"
    scene.view_settings.exposure, scene.view_settings.gamma = 0, 1
    scene.view_settings.use_curve_mapping = False
    if hasattr(scene.view_settings, "use_white_balance"):
        scene.view_settings.use_white_balance = False

    clay = bpy.data.materials.new("Feature review clay")
    clay.use_nodes = True
    shader = next(node for node in clay.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = (0.48, 0.48, 0.48, 1)
    shader.inputs["Roughness"].default_value = 0.72
    return clay


def crop_reference(path, box, destination):
    source = bpy.data.images.load(str(path), check_existing=False)
    try:
        width, height = source.size
        left, top, right, bottom = box
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise ValueError(f"Crop is outside {width}x{height}: {box}")
        pixels = np.empty(width * height * 4, dtype=np.float32)
        source.pixels.foreach_get(pixels)
        crop = pixels.reshape(height, width, 4)[height-bottom:height-top, left:right, :]
        image = bpy.data.images.new("Feature reference crop", right-left, bottom-top, alpha=True)
        try:
            image.pixels.foreach_set(crop.ravel())
            image.file_format = "PNG"
            image.filepath_raw = str(destination)
            image.save()
        finally:
            bpy.data.images.remove(image)
    finally:
        bpy.data.images.remove(source)


def render_pair(source, feature, config, out, tag, setup_materials):
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False, load_ui=False)
    scene = bpy.context.scene
    layer = bpy.context.view_layer
    materials = setup_materials(scene) if setup_materials else []
    clay = configure_scene(scene, feature["camera"], config["studio"], config["resolution"], config["samples"])
    for channel in CHANNELS:
        layer.material_override = clay if channel == "clay" else None
        path = out / f"{tag}-{channel}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True, layer=layer.name)
        file_input(path)
    return materials


def execute(config_path, out, *, selected=(), setup_materials=None, material_inputs=()):
    """Run only selected feature IDs when given. Geometry snapshots are opened read-only on disk."""
    config_path = Path(config_path).resolve()
    out = Path(out).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["schema_version"] != 1:
        raise ValueError("Unsupported feature review configuration")
    if any(type(config[key]) is not int or config[key] < limit for key, limit in (("resolution", 64), ("samples", 1))):
        raise ValueError("resolution and samples must be integers >= 64 and >= 1")
    root = config_path.parent
    snapshots = {tag: (root / config["snapshots"][tag]).resolve() for tag in VIEWS}
    material_files = [(root / path).resolve() for path in config.get("material_files", [])]
    ledger_path = (root / config["ledger"]).resolve()
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    modules = {module["id"]: module for module in ledger["modules"]}
    features = {feature["id"]: feature for feature in config["features"]}
    if not features or len(features) != len(config["features"]):
        raise ValueError("Feature IDs must be unique and nonempty")
    if set(selected) - features.keys():
        raise ValueError(f"Unknown feature IDs: {sorted(set(selected) - features.keys())}")
    for key, feature in features.items():
        if selected and key not in selected:
            continue
        if not re.fullmatch(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", key):
            raise ValueError(f"Invalid feature ID: {key}")
        module = modules[feature["module_id"]]
        if feature["signature_feature"] not in module["signature_features"]:
            raise ValueError(f"{key}: feature is not in the declared module ledger")
        reference = feature["reference"]
        if len(reference["box_px"]) != 4 or any(type(item) is not int for item in reference["box_px"]):
            raise ValueError(f"{key}: box_px needs four integer coordinates")
        if any(not feature[field].strip() for field in ("issue", "change")) or not reference["view"].strip():
            raise ValueError(f"{key}: issue, change and reference view are required")
        source = (root / reference["image"]).resolve()
        folder = out / key
        images = [folder / name for name in FILENAMES]
        manifest = folder / "feature.json"
        receipt = folder / "receipt.json"
        inputs = [config_path, ledger_path, source, *snapshots.values(), *material_files, *map(Path, material_inputs),
                  Path(__file__).resolve(), Path(__file__).with_name("stage_guard.py")]
        if {p.resolve() for p in [*images, manifest, receipt]} & {p.resolve() for p in inputs}:
            raise ValueError(f"{key}: outputs overlap an input file")
        settings = {key: config[key] for key in ("studio", "resolution", "samples")}
        stage_settings = dict(settings, schema_version=config["schema_version"], feature=feature,
                              ledger={"path": str(ledger_path), "task_id": ledger["task_id"]},
                              material_recipe=config.get("material_recipe"))
        evidence_files = [path for path in inputs if path not in (config_path, ledger_path)]

        def work():
            crop_reference(source, reference["box_px"], images[0])
            appearances = {tag: render_pair(path, feature, config, folder, tag, setup_materials)
                           for tag, path in snapshots.items()}
            record = dict(feature, review_status="pending_visual_review", blender=bpy.app.version_string,
                          snapshots={tag: file_input(path) for tag, path in snapshots.items()},
                          source_reference=file_input(source), materials=appearances,
                          **settings,
                          artifacts={path.stem: path.name for path in images})
            manifest.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return all(path.is_file() and path.stat().st_size > 0 for path in images)

        run_stage(receipt, "feature_review_render",
                  lambda: {"settings": stage_settings, "files": [file_input(path) for path in evidence_files]},
                  [*images, manifest], work, lambda result: result is True)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--feature", action="append", default=[])
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


if __name__ == "__main__":
    args = parse_args()
    execute(args.config, args.out, selected=args.feature)
