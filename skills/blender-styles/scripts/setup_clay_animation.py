"""Non-destructive action copy with interpolation, Cycles and stepped sampling."""
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clay_common import OWNER_KEY, ROLE_KEY, cli, curves_for, emit, parse, scope, tag


def setup_animation(obj, scene, config, owner="soft-clay"):
    if obj.name not in scene.objects:
        raise ValueError(f"Object not in scene: {obj.name}")
    if obj.library or obj.override_library:
        raise RuntimeError("Linked/override animation is read-only")
    ad = obj.animation_data
    if not ad or not ad.action or not curves_for(obj):
        raise ValueError(f"No action curves on {obj.name}")
    if ad.nla_tracks or ad.drivers or obj.constraints:
        raise RuntimeError("NLA, drivers and object constraints need explicit evaluated baking first")
    if obj.type == "ARMATURE" and any(b.constraints for b in obj.pose.bones):
        raise RuntimeError("Constrained rig needs evaluated baking before stepped timing")
    # Multi-scene shared objects cannot have independent animation without duplication.
    if any(s != scene and obj.name in s.objects for s in bpy.data.scenes):
        raise RuntimeError("Animation object is shared across scenes; duplicate it first")
    p = config["animation"]
    # Check every channel before any interpolation edits or Action replacement.
    for fc in curves_for(obj):
        for m in fc.modifiers:
            if p["loop"] and m.name not in ("SoftClayCycle", "SoftClayHold"):
                raise RuntimeError("Loop Cycles must be first; bake/resolve existing artistic modifiers first")
            if m.name not in ("SoftClayCycle", "SoftClayHold") and (
                p["loop"] and m.type == "CYCLES" or p["hold_frames"] > 1 and m.type == "STEPPED"
            ):
                raise RuntimeError(f"Existing artistic {m.type} modifier; resolve before timing changes")
    owner = scope(scene, owner)
    role = "action-" + obj.name
    original = ad.action
    if (original.get(OWNER_KEY) != owner or original.get(ROLE_KEY) != role or
            original.users - int(original.use_fake_user) > 1):
        slot_id = getattr(getattr(ad, "action_slot", None), "identifier", None)
        copied = original.copy()
        copied.use_fake_user = False
        tag(copied, owner, role)
        copied.name = f"Clay::{owner}::{role}"
        original.use_fake_user = True  # Preserve source even when it has no other users.
        ad.action = copied
        if slot_id and hasattr(copied, "slots"):
            slots = [s for s in copied.slots if s.identifier == slot_id]
            if not slots:
                raise RuntimeError("Copied action lost its source slot")
            ad.action_slot = slots[0]
    curves = curves_for(obj)
    for fc in curves:
        for point in fc.keyframe_points:
            point.interpolation = p["interpolation"]
            if p["interpolation"] == "BEZIER":
                point.handle_left_type = point.handle_right_type = "AUTO_CLAMPED"
        # Own only these named timing modifiers; leave artistic modifiers intact.
        for modifier in list(fc.modifiers):
            if modifier.name in ("SoftClayCycle", "SoftClayHold"):
                fc.modifiers.remove(modifier)
        if p["loop"]:
            cycle = fc.modifiers.new("CYCLES")
            if cycle is None:
                raise RuntimeError("Blender refused a first-position Cycles modifier")
            cycle.name = "SoftClayCycle"
            cycle.mode_before = cycle.mode_after = "REPEAT"
        if p["hold_frames"] > 1:
            hold = fc.modifiers.new("STEPPED")
            hold.name = "SoftClayHold"
            hold.frame_step = p["hold_frames"]
            hold.frame_offset = scene.frame_start
        fc.update()
    obj["soft_clay_hold_frames"] = p["hold_frames"]
    obj["soft_clay_loop"] = p["loop"]
    return {"object": obj.name, "action": ad.action.name, "curves": len(curves), **p}


def main():
    parser = cli(__doc__)
    parser.add_argument("--objects", nargs="+", required=True, help="Explicit existing object names")
    args, config, scene = parse(parser)
    targets = [bpy.data.objects.get(name) for name in args.objects]
    if any(o is None for o in targets):
        raise ValueError("One or more requested animation objects do not exist")
    emit("animation", results=[setup_animation(o, scene, config, args.owner) for o in targets])


if __name__ == "__main__":
    main()
