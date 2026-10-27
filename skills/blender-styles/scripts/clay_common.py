"""Shared bpy utilities. Import from Blender, not the host Python interpreter."""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

import bpy

OWNER_KEY = "soft_clay_owner"
ROLE_KEY = "soft_clay_role"
DEFAULTS = {
    "scale": 1.0,
    "palette": {"peach": "#DFA58D", "sage": "#9DB6A0", "cream": "#E8D8B9",
                "blue": "#8EA9BF", "ground": "#D6C9B7"},
    "material": {"roughness": 0.82, "specular": 0.22, "color_variation": 0.035,
                 "color_scale": 3.0, "micro_scale": 110.0,
                 "bump_strength": 0.12, "bump_distance": 0.003},
    "lighting": {"center": [0, 0, 0.8], "world_color": "#E3E8ED", "world_strength": 0.3,
                 "key_energy": 450.0, "fill_ratio": 0.4, "rim_ratio": 0.55,
                 "key_size": 4.0, "fill_size": 5.0, "rim_size": 3.0},
    "camera": {"position": [6.0, -8.5, 5.8], "target": [0, 0, 0.8],
               "type": "PERSP", "lens": 55.0, "ortho_scale": 6.0,
               "dof": False, "fstop": 5.6, "clip_start": 0.01, "clip_end": 200.0},
    "render": {"engine": "KEEP", "width": 960, "height": 540, "percentage": 100,
               "fps": 24, "fps_base": 1.0, "frame_start": 1, "frame_end": 24,
               "samples": 32, "device": "KEEP", "denoise": True,
               "format": "PNG", "transparent": False, "motion_blur": False,
               "view_transform": "AgX", "look": "KEEP", "exposure": 0.0,
               "gamma": 1.0},
    "animation": {"interpolation": "BEZIER", "hold_frames": 1, "loop": True},
    "quality": {"max_faces": 5000, "min_roughness": 0.65, "loop_tolerance": 0.0001,
                "require_manifold": False},
}


def merge_config(overrides=None):
    """Strict partial overrides; palette is replaced as a whole."""
    config = copy.deepcopy(DEFAULTS)
    overrides = {} if overrides is None else overrides
    if not isinstance(overrides, dict):
        raise ValueError("Config must be a JSON object")
    for section, value in overrides.items():
        if section not in config:
            raise ValueError(f"Unknown config key: {section}")
        if section == "palette":
            config[section] = copy.deepcopy(value)
        elif isinstance(config[section], dict):
            if not isinstance(value, dict):
                raise ValueError(f"{section} must be an object")
            unknown = set(value) - set(config[section])
            if unknown:
                raise ValueError(f"Unknown {section} keys: {sorted(unknown)}")
            config[section].update(value)
        else:
            config[section] = value
    validate_config(config)
    return config


def number(value, label, low=None, high=None, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if integer and not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f"{label} outside [{low}, {high}]")


def linear_rgba(color):
    """Hex is sRGB; numeric RGB(A) is already scene-linear (no double conversion)."""
    if isinstance(color, str):
        if len(color) != 7 or not color.startswith("#"):
            raise ValueError(f"Expected #RRGGBB: {color}")
        try:
            rgb = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        except ValueError as exc:
            raise ValueError(f"Invalid hex color: {color}") from exc
        return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
                     for c in rgb) + (1.0,)
    if not isinstance(color, (list, tuple)) or len(color) not in (3, 4):
        raise ValueError("Colors must be hex strings or scene-linear RGB(A)")
    for c in color:
        number(c, "color channel", 0, 1)
    if len(color) == 4 and color[3] != 1:
        raise ValueError("Clay palette is opaque; alpha must be 1")
    return tuple(color[:3]) + (1.0,)


def validate_config(c):
    number(c["scale"], "scale", 0.000001)
    if not isinstance(c["palette"], dict) or not c["palette"]:
        raise ValueError("palette must be a nonempty color-name mapping")
    for name, color in c["palette"].items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Palette names must be nonempty strings")
        linear_rgba(color)
    for key in ("roughness", "specular", "bump_strength"):
        number(c["material"][key], key, 0, 1)
    number(c["material"]["color_variation"], "color_variation", 0, 0.25)
    for key in ("color_scale", "micro_scale"):
        number(c["material"][key], key, 0.000001)
    number(c["material"]["bump_distance"], "bump_distance", 0)
    for key in ("world_strength", "key_energy", "fill_ratio", "rim_ratio"):
        number(c["lighting"][key], key, 0)
    for key in ("key_size", "fill_size", "rim_size"):
        number(c["lighting"][key], key, 0.000001)
    linear_rgba(c["lighting"]["world_color"])
    for section, key in (("lighting", "center"), ("camera", "position"), ("camera", "target")):
        vec = c[section][key]
        if not isinstance(vec, (list, tuple)) or len(vec) != 3:
            raise ValueError(f"{section}.{key} must have three components")
        for v in vec:
            number(v, f"{section}.{key}")
    cam = c["camera"]
    if cam["type"] not in ("PERSP", "ORTHO") or cam["position"] == cam["target"]:
        raise ValueError("Camera must be PERSP/ORTHO with distinct position and target")
    for key in ("lens", "ortho_scale", "fstop", "clip_start", "clip_end"):
        number(cam[key], key, 0.000001)
    if cam["clip_end"] <= cam["clip_start"]:
        raise ValueError("clip_end must exceed clip_start")
    r = c["render"]
    for key, lo, hi in (("width", 4, 65536), ("height", 4, 65536), ("percentage", 1, 100),
                        ("fps", 1, 32767), ("samples", 1, 1000000),
                        ("frame_start", 0, 1048574), ("frame_end", 0, 1048574)):
        number(r[key], key, lo, hi, integer=True)
    number(r["fps_base"], "fps_base", 0.000001)
    number(r["exposure"], "exposure", -32, 32)
    number(r["gamma"], "gamma", 0.01, 10)
    if r["frame_end"] < r["frame_start"]:
        raise ValueError("frame_end must be >= frame_start")
    if r["engine"] not in ("KEEP", "EEVEE", "CYCLES"):
        raise ValueError("engine must be KEEP, EEVEE or CYCLES")
    if r["device"] not in ("KEEP", "CPU", "GPU"):
        raise ValueError("device must be KEEP, CPU or GPU")
    if r["format"] not in ("PNG", "OPEN_EXR", "FFMPEG"):
        raise ValueError("format must be PNG, OPEN_EXR or FFMPEG")
    for key in ("view_transform", "look"):
        if not isinstance(r[key], str) or not r[key]:
            raise ValueError(f"{key} must be a nonempty enum or KEEP")
    for section, keys in (("camera", ("dof",)),
                          ("render", ("denoise", "transparent", "motion_blur")),
                          ("animation", ("loop",)), ("quality", ("require_manifold",))):
        for key in keys:
            if not isinstance(c[section][key], bool):
                raise ValueError(f"{section}.{key} must be boolean")
    a = c["animation"]
    if a["interpolation"] not in ("BEZIER", "LINEAR", "CONSTANT"):
        raise ValueError("interpolation must be BEZIER, LINEAR or CONSTANT")
    number(a["hold_frames"], "hold_frames", 1, 1000, integer=True)
    number(c["quality"]["max_faces"], "max_faces", 1, integer=True)
    number(c["quality"]["min_roughness"], "min_roughness", 0, 1)
    number(c["quality"]["loop_tolerance"], "loop_tolerance", 0)


def cli(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", type=Path, help="Partial JSON style profile")
    parser.add_argument("--scene", help="Existing scene name; default is active scene")
    parser.add_argument("--owner", default="soft-clay", help="Stable task ID, scoped per scene")
    return parser


def parse(parser):
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    raw = json.loads(args.config.read_text()) if args.config else {}
    if not isinstance(raw, dict):
        raise ValueError("Config file must contain a JSON object")
    config = merge_config(raw)
    scene = bpy.data.scenes.get(args.scene) if args.scene else bpy.context.scene
    if scene is None:
        raise ValueError(f"Scene not found: {args.scene}")
    if not args.owner.strip():
        raise ValueError("owner must be nonempty")
    return args, config, scene


def scope(scene, owner):
    return f"{owner}::{scene.name}"


def tag(data, owner, role):
    data[OWNER_KEY], data[ROLE_KEY] = owner, role
    return data


def owned(blocks, owner, role, factory):
    matches = [d for d in blocks if d.get(OWNER_KEY) == owner and d.get(ROLE_KEY) == role]
    if len(matches) > 1:
        raise RuntimeError(f"Duplicate ownership for {owner}/{role}; resolve before updating")
    if matches:
        data = matches[0]
        if data.library or data.override_library:
            raise RuntimeError(f"Refusing to edit linked/override data: {data.name}")
        return data
    name = f"Clay::{owner}::{role}"
    if blocks.get(name):
        raise RuntimeError(f"Unowned name collision: {name}")
    return tag(factory(name), owner, role)


def collection(scene, owner):
    result = owned(bpy.data.collections, owner, "rig", bpy.data.collections.new)
    if result.name not in scene.collection.children:
        scene.collection.children.link(result)
    return result


def rig_object(scene, owner, role, kind):
    blocks = bpy.data.lights if kind == "LIGHT" else bpy.data.cameras
    factory = (lambda name: blocks.new(name, "AREA")) if kind == "LIGHT" else blocks.new
    data = owned(blocks, owner, role + "-data", factory)
    obj = owned(bpy.data.objects, owner, role, lambda name: bpy.data.objects.new(name, data))
    if obj.type != kind or obj.data != data or data.users > 1:
        raise RuntimeError(f"Unexpected type or shared rig data: {obj.name}")
    if any(s != scene and obj.name in s.objects for s in bpy.data.scenes):
        raise RuntimeError(f"Rig object shared across scenes: {obj.name}")
    col = collection(scene, owner)
    if obj.name not in col.objects:
        col.objects.link(obj)
    if obj.animation_data or obj.constraints:
        raise RuntimeError(f"Rig object has animation/constraints; preserve it: {obj.name}")
    obj.parent = None
    obj.scale = (1, 1, 1)
    return obj


def socket(node, *identifiers, output=False):
    sockets = node.outputs if output else node.inputs
    for s in sockets:
        if s.identifier in identifiers:
            return s
    raise RuntimeError(f"{bpy.app.version_string}: {node.bl_idname} needs {identifiers}; "
                       f"available={[s.identifier for s in sockets]}")


def enum_set(data, prop, value):
    valid = {x.identifier for x in data.bl_rna.properties[prop].enum_items}
    # OCIO and engine dynamic enums can expose a static NONE placeholder.
    # Assignment consults the actual runtime choices and is authoritative.
    try:
        setattr(data, prop, value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{bpy.app.version_string}: cannot set {prop}={value!r}: {exc}; "
                           f"static RNA choices={sorted(valid)}") from exc


def curves_for(obj):
    """Read only this object's action slot, supporting legacy and layered actions."""
    ad = obj.animation_data
    if not ad or not ad.action:
        return []
    action = ad.action
    if getattr(action, "is_action_layered", False):
        slot = getattr(ad, "action_slot", None)
        if slot is None:
            raise RuntimeError(f"Missing action slot on {obj.name}")
        curves = []
        for layer in action.layers:
            for strip in layer.strips:
                if hasattr(strip, "channelbag"):
                    bag = strip.channelbag(slot)
                    if bag:
                        curves.extend(bag.fcurves)
        return curves
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    raise RuntimeError(f"Unsupported Action API on Blender {bpy.app.version_string}")


def save_new(path, overwrite=False):
    path = Path(path).expanduser().resolve()
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}; use --overwrite explicitly")
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)


def write_json(path, value):
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def emit(stage, **kwargs):
    print(json.dumps({"stage": stage, "blender": bpy.app.version_string, **kwargs}, sort_keys=True))
