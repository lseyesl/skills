"""Create/update scene-scoped area lights, world, and an optional clay camera."""
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clay_common import cli, emit, enum_set, linear_rgba, owned, parse, rig_object, scope, socket


def aim(obj, target):
    direction = Vector(target) - obj.location
    if direction.length < 1e-8:
        raise ValueError("Cannot aim at the object's own position")
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_lighting(scene, config, owner="soft-clay", with_camera=True):
    owner = scope(scene, owner)
    scale, p = config["scale"], config["lighting"]
    center = Vector(p["center"]) * scale
    lights = []
    for role, offset, ratio, size in (
        ("key", (-3, -4, 5), 1, p["key_size"]),
        ("fill", (4, -1, 3), p["fill_ratio"], p["fill_size"]),
        ("rim", (1, 4, 4), p["rim_ratio"], p["rim_size"]),
    ):
        obj = rig_object(scene, owner, role, "LIGHT")
        obj.location = center + Vector(offset) * scale
        aim(obj, center)
        obj.data.type = "AREA"
        enum_set(obj.data, "shape", "DISK")
        obj.data.size = size * scale
        obj.data.energy = p["key_energy"] * ratio * scale ** 2
        obj.data.color = (1, 1, 1)
        obj.data.use_shadow = True
        lights.append(obj)
    world = owned(bpy.data.worlds, owner, "world", bpy.data.worlds.new)
    if world.users > 1:
        raise RuntimeError("World shared between scenes; use separate scene owner")
    world.use_nodes = True
    world.node_tree.nodes.clear()
    bg = world.node_tree.nodes.new("ShaderNodeBackground")
    out = world.node_tree.nodes.new("ShaderNodeOutputWorld")
    socket(bg, "Color").default_value = linear_rgba(p["world_color"])
    socket(bg, "Strength").default_value = p["world_strength"]
    world.node_tree.links.new(socket(bg, "Background", output=True), socket(out, "Surface"))
    scene.world = world  # Previous world datablock is preserved.
    camera = None
    if with_camera:
        c = config["camera"]
        camera = rig_object(scene, owner, "camera", "CAMERA")
        camera.location = Vector(c["position"]) * scale
        target = Vector(c["target"]) * scale
        aim(camera, target)
        enum_set(camera.data, "type", c["type"])
        camera.data.lens = c["lens"]
        camera.data.ortho_scale = c["ortho_scale"] * scale
        camera.data.clip_start = c["clip_start"] * scale
        camera.data.clip_end = c["clip_end"] * scale
        camera.data.dof.use_dof = c["dof"]
        camera.data.dof.focus_object = None
        camera.data.dof.focus_distance = (target - camera.location).length
        camera.data.dof.aperture_fstop = c["fstop"]
        scene.camera = camera
    return {"lights": [o.name for o in lights], "world": world.name,
            "camera": camera.name if camera else None}


def main():
    parser = cli(__doc__)
    parser.add_argument("--keep-camera", action="store_true", help="Preserve the active camera")
    args, config, scene = parse(parser)
    emit("lighting", **setup_lighting(scene, config, args.owner, not args.keep_camera))


if __name__ == "__main__":
    main()
