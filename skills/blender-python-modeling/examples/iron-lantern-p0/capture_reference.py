"""Render orthographic construction guides from the CC0 scan in an isolated Blender process."""

import json
import sys
from hashlib import sha256
from pathlib import Path

import bpy
from mathutils import Vector


RESOLUTION = 720
FRAME = 0.34
VIEWS = {"front": (0, -1, 0), "right": (1, 0, 0), "iso": (0.72, -1, 0.30)}
REFERENCE_SHA256 = "fa4557380f5b547476fbd57fa312b8a78603d11e6dd656439ee39bc4e950074a"


def camera(scene, target, direction, span=FRAME, resolution=RESOLUTION):
    if scene.camera is None:
        lens = bpy.data.cameras.new("Review camera")
        scene.camera = bpy.data.objects.new("Review camera", lens)
        scene.collection.objects.link(scene.camera)
    obj = scene.camera
    obj.data.type = "ORTHO"
    obj.data.ortho_scale = span
    obj.data.clip_start = 0.001
    obj.location = Vector(target) + Vector(direction).normalized() * 0.8
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.resolution_x = scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100


def workbench(scene, *, mask=False):
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.display.render_aa = "16"
    shade = scene.display.shading
    shade.light = "FLAT" if mask else "STUDIO"
    shade.color_type = "SINGLE" if mask else "OBJECT"
    shade.single_color = (1, 1, 1)
    shade.show_shadows = shade.show_cavity = not mask
    shade.cavity_type = "BOTH"
    shade.show_object_outline = False


def render(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main(out):
    source = out / "truth-lantern.glb"
    if sha256(source.read_bytes()).hexdigest() != REFERENCE_SHA256:
        raise ValueError("These landmark annotations require the pinned Lantern 01 scan")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    scene = bpy.context.scene
    objects = [obj for obj in scene.objects if obj.type == "MESH"]
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    low = Vector([min(p[i] for p in points) for i in range(3)])
    high = Vector([max(p[i] for p in points) for i in range(3)])
    offset = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
    for obj in objects:
        obj.location -= offset
        obj.color = (0.34, 0.44, 0.53, 1) if "glass" in obj.name.lower() else (0.57, 0.48, 0.34, 1)
    height = high.z - low.z
    target = (0, 0, height / 2)
    for view, direction in VIEWS.items():
        camera(scene, target, direction)
        workbench(scene)
        render(scene, out / f"reference-{view}.png")
    (out / "reference-frame.json").write_text(json.dumps({"height_m": height, "target": target,
        "pixels_per_unit": RESOLUTION / FRAME, "resolution": RESOLUTION,
        "origin_px": [RESOLUTION / 2, RESOLUTION / 2 + target[2] * RESOLUTION / FRAME]}, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[sys.argv.index("--") + 1]).resolve())
