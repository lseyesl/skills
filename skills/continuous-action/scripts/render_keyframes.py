"""Render individual action pose references from A.blend, or an optional sheet.

Run: blender -b assets/A.blend -t 2 --python scripts/render_keyframes.py -- \
  --action ACTION_ID_FROM_CATALOG --count 8 --view front

Without --output, a fresh directory is created under the repository's
.tmp/continuous-action/. Never write rendered images into the skill.
"""
import argparse
from array import array
import json
import math
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector


def far_limb_color(rgba, dim, cool_strength):
    """Keep the requested luminance reduction while shifting the far limb cooler."""
    rgb = rgba[:3]
    luminance = lambda values: sum(a * b for a, b in zip(values, (0.2126, 0.7152, 0.0722)))
    shifted = (rgb[0] * (1 - 0.35 * cool_strength),
               rgb[1] * (1 + 0.08 * cool_strength),
               rgb[2] * (1 + 0.8 * cool_strength))
    scale = luminance(rgb) * (1 - dim) / max(luminance(shifted), 1e-6)
    return tuple(min(1.0, channel * scale) for channel in shifted) + (rgba[3],)


def shade_far_limbs(meshes, far_side, dim=0.15, cool_strength=1.0):
    """Darken and cool polygons led by far-side limb weights for side-view guides."""
    changed = {}
    for obj in meshes:
        groups = {group.index: group.name for group in obj.vertex_groups}
        vertex_sides = []
        for vertex in obj.data.vertices:
            weights = {"Left": 0.0, "Right": 0.0}
            for membership in vertex.groups:
                name = groups.get(membership.group, "")
                for side in weights:
                    if name.startswith(f"mixamorig:{side}") and any(
                        part in name for part in ("Shoulder", "Arm", "Hand", "Leg", "Foot", "Toe")
                    ):
                        weights[side] += membership.weight
            vertex_sides.append(weights)

        original_materials = list(obj.data.materials)
        far_materials = {}
        for index, material in enumerate(original_materials):
            if material is None:
                continue
            darker = material.copy()
            darker.name = f"{material.name}_far_{far_side}_{round(dim * 100)}pct"
            darker.diffuse_color = far_limb_color(material.diffuse_color, dim, cool_strength)
            if darker.use_nodes:
                for node in darker.node_tree.nodes:
                    if node.type == "BSDF_PRINCIPLED":
                        socket = node.inputs.get("Base Color")
                        if socket and not socket.is_linked:
                            socket.default_value = far_limb_color(socket.default_value, dim, cool_strength)
            far_materials[index] = len(obj.data.materials)
            obj.data.materials.append(darker)

        shaded = 0
        for polygon in obj.data.polygons:
            if polygon.material_index not in far_materials:
                continue
            scores = {side: sum(vertex_sides[i][side] for i in polygon.vertices) for side in ("Left", "Right")}
            if scores[far_side] > scores["Right" if far_side == "Left" else "Left"] and scores[far_side] > 0:
                polygon.material_index = far_materials[polygon.material_index]
                shaded += 1
        changed[obj.name] = shaded
    return changed


def args_after_separator():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def select_phase_markers(clip, count, overrides):
    """Select named motion events with phase coverage, never uniform time sampling."""
    start, end = clip["frame_start"], clip["frame_end"]
    if clip.get("phase_frame_range") != [start, end]:
        raise ValueError("phase markers are missing or stale for this action range; review A.catalog.json")
    markers = [dict(marker) for marker in clip.get("phase_markers", [])]
    if not markers:
        raise ValueError("this action has no reviewed phase markers in A.catalog.json")
    names = [marker.get("phase") for marker in markers]
    if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(names):
        raise ValueError("phase names must be nonempty and unique")
    for override in overrides:
        name, separator, value = override.partition("=")
        if not separator or name not in names:
            raise ValueError(f"invalid --phase-frame {override!r}; use PHASE=FRAME from the catalog")
        try:
            frame = int(value)
        except ValueError as exc:
            raise ValueError(f"invalid frame in --phase-frame {override!r}") from exc
        markers[names.index(name)]["frame"] = frame
    frames = [marker.get("frame") for marker in markers]
    if any(type(frame) is not int or not start <= frame <= end for frame in frames):
        raise ValueError("phase frames must be integers within the action range")
    if frames != sorted(set(frames)):
        raise ValueError("phase frames must be unique and in chronological order")
    if clip["loop_hint"] and end in frames:
        raise ValueError("loop phase markers must omit the repeated final frame")
    if any(type(marker.get("priority")) is not int or marker["priority"] < 0 for marker in markers):
        raise ValueError("phase priorities must be nonnegative integers")
    if count > len(markers):
        raise ValueError(f"requested {count} frames, but only {len(markers)} reviewed phases exist; add phase markers before rendering")
    if count == len(markers):
        return markers

    selected = {0 if clip["loop_hint"] or count > 1 else
                min(range(len(markers)), key=lambda index: (markers[index]["priority"], index))}
    if not clip["loop_hint"] and count > 1:
        selected.add(len(markers) - 1)
    period = end - start
    while len(selected) < count:
        def score(index):
            frame = frames[index]
            distance = min(
                min(abs(frame - frames[other]), period - abs(frame - frames[other]))
                if clip["loop_hint"] else abs(frame - frames[other])
                for other in selected
            )
            return (distance / max(period, 1) + 0.1 * (5 - markers[index]["priority"]),
                    -markers[index]["priority"], -index)
        selected.add(max((index for index in range(len(markers)) if index not in selected), key=score))
    return [markers[index] for index in sorted(selected)]


def compose_reference_sheet(frame_paths, sheet_path, columns):
    """Pack temporary Blender renders into one transparent PNG, in reading order."""
    first = bpy.data.images.load(str(frame_paths[0]), check_existing=False)
    width, height = first.size
    bpy.data.images.remove(first)
    rows = math.ceil(len(frame_paths) / columns)
    sheet_width, sheet_height = width * columns, height * rows
    pixels = array("f", [0.0]) * (sheet_width * sheet_height * 4)
    regions = []
    for index, path in enumerate(frame_paths):
        source = bpy.data.images.load(str(path), check_existing=False)
        if tuple(source.size) != (width, height) or source.channels != 4:
            raise RuntimeError(f"inconsistent reference render dimensions or channels: {path}")
        source_pixels = array("f", [0.0]) * (width * height * 4)
        source.pixels.foreach_get(source_pixels)
        x = index % columns * width
        top_y = index // columns * height
        bottom_y = sheet_height - top_y - height
        for row in range(height):
            source_start = row * width * 4
            target_start = ((bottom_y + row) * sheet_width + x) * 4
            pixels[target_start:target_start + width * 4] = source_pixels[source_start:source_start + width * 4]
        regions.append({"x": x, "y": top_y, "width": width, "height": height})
        bpy.data.images.remove(source)
    sheet = bpy.data.images.new("ActionReferenceSheet", width=sheet_width, height=sheet_height, alpha=True)
    sheet.pixels.foreach_set(pixels)
    sheet.file_format = "PNG"
    sheet.filepath_raw = str(sheet_path)
    sheet.save()
    bpy.data.images.remove(sheet)
    return {"columns": columns, "rows": rows, "width": sheet_width, "height": sheet_height}, regions


def main():
    skill_dir = Path(__file__).resolve().parents[1]
    root = skill_dir.parents[1]
    catalog = json.loads((skill_dir / "assets" / "A.catalog.json").read_text())
    clips = catalog.get("clips")
    if not isinstance(clips, dict) or not clips:
        raise RuntimeError("A.catalog.json must contain a nonempty clips object")
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True, choices=sorted(clips))
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--phase-frame", action="append", default=[], metavar="PHASE=FRAME",
                        help="Move a reviewed phase to a nearby frame after visual QA; may be repeated")
    parser.add_argument("--format", choices=("frames", "sheet"), default="frames",
                        help="Individual pose PNGs for precise frame matching (default), or one sequence sheet")
    parser.add_argument("--columns", type=int, default=4, help="Maximum columns in the single reference image (default 4)")
    parser.add_argument("--output", type=Path, help="Directory under repository .tmp/continuous-action; defaults to a fresh run")
    parser.add_argument("--view", choices=("front", "back", "left", "right"), default="front")
    parser.add_argument("--follow-hips", action="store_true", help="Keep translating clips centered horizontally")
    parser.add_argument("--far-limb-dim", type=float, default=0.15,
                        help="Side views: far-side limb brightness reduction, from 0.10 to 0.20 (default 0.15)")
    parser.add_argument("--far-limb-cool-strength", type=float, default=1.0,
                        help="Side views: cool color cue strength, from 0 to 1.5 (default 1.0)")
    options = parser.parse_args(args_after_separator())
    if options.count < 1:
        parser.error("--count must be at least 1")
    if options.columns < 1:
        parser.error("--columns must be at least 1")
    if not 0.10 <= options.far_limb_dim <= 0.20:
        parser.error("--far-limb-dim must be between 0.10 and 0.20")
    if not 0 <= options.far_limb_cool_strength <= 1.5:
        parser.error("--far-limb-cool-strength must be between 0 and 1.5")
    clip = clips[options.action]
    try:
        selected_markers = select_phase_markers(clip, options.count, options.phase_frame)
    except ValueError as exc:
        parser.error(str(exc))
    frames = [marker["frame"] for marker in selected_markers]
    rig = bpy.data.objects[catalog["rig"]]
    rig.animation_data.action = bpy.data.actions[clip["action"]]
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
    camera = bpy.data.objects["ReferenceCamera"]
    camera.location = {
        "front": (0, -4, 1.0), "back": (0, 4, 1.0),
        "left": (-4, 0, 1.0), "right": (4, 0, 1.0),
    }[options.view]
    camera.rotation_euler = (math.pi / 2, 0, {
        "front": 0, "back": math.pi, "left": -math.pi / 2, "right": math.pi / 2,
    }[options.view])
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    far_side = {"left": "Left", "right": "Right"}.get(options.view)
    shaded_polygons = shade_far_limbs(
        [bpy.data.objects[name] for name in catalog["meshes"]], far_side,
        options.far_limb_dim, options.far_limb_cool_strength
    ) if far_side else {}
    temp_root = root / ".tmp" / "continuous-action"
    temp_root.mkdir(parents=True, exist_ok=True)
    output = (options.output.expanduser().resolve() if options.output else
              Path(tempfile.mkdtemp(prefix=f"{options.action}-{options.view}-", dir=temp_root)))
    if output == temp_root or temp_root not in output.parents:
        parser.error(f"output must be a task directory below {temp_root}")
    if output.exists() and any(output.iterdir()):
        parser.error(f"output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"source_blend": str(skill_dir / "assets" / "A.blend"), "action": options.action,
                "source_fbx": clip["source_fbx"], "view": options.view,
                "follow_hips": options.follow_hips,
                "reference_format": options.format,
                "sampling": {"method": "reviewed_action_phases", "phase_frame_overrides": options.phase_frame},
                "reference_palette": {"near_side": "Right" if far_side == "Left" else "Left" if far_side else None,
                                      "far_side": far_side, "far_limb_dim": options.far_limb_dim if far_side else None,
                                      "far_limb_cool_strength": options.far_limb_cool_strength if far_side else None,
                                      "shaded_polygons": shaded_polygons,
                                      "final_output": "Restore the character's original colors; guide shading is motion-only."},
                "frames": []}
    camera_start = camera.location.copy()
    camera_right = camera.rotation_euler.to_quaternion() @ Vector((1, 0, 0))
    scene.frame_set(frames[0])
    hips = next(bone for bone in rig.pose.bones if bone.parent is None)
    hips_start = rig.matrix_world @ hips.matrix.translation
    def render_frames(target):
        paths = []
        for index, frame in enumerate(frames, 1):
            scene.frame_set(frame)
            if options.follow_hips:
                hips_now = rig.matrix_world @ hips.matrix.translation
                camera.location = camera_start + camera_right * (hips_now - hips_start).dot(camera_right)
            image_path = target / f"{index:02d}_{options.action}_f{frame:03d}.png"
            scene.render.filepath = str(image_path)
            bpy.ops.render.render(write_still=True)
            paths.append(image_path)
        return paths

    if options.format == "frames":
        for index, (marker, image_path) in enumerate(zip(selected_markers, render_frames(output)), 1):
            manifest["frames"].append({"id": f"{index:02d}", "source_frame": marker["frame"],
                                       "phase": marker["phase"], "image": str(image_path)})
    else:
        manifest["reference_image"] = str(output / "action-reference.png")
        with tempfile.TemporaryDirectory(prefix=".frame-staging-", dir=output) as staging:
            frame_paths = render_frames(Path(staging))
            manifest["layout"], regions = compose_reference_sheet(
                frame_paths, Path(manifest["reference_image"]), min(options.columns, options.count)
            )
        for index, (marker, region) in enumerate(zip(selected_markers, regions), 1):
            manifest["frames"].append({"id": f"{index:02d}", "source_frame": marker["frame"],
                                       "phase": marker["phase"], "region": region})
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    if options.format == "sheet":
        print("ACTION_REFERENCE_IMAGE", manifest["reference_image"])
    print("KEYFRAME_MANIFEST", output / "manifest.json")


if __name__ == "__main__":
    main()
