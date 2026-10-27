"""Configure EEVEE/Cycles; optionally save a copy or render still/animation."""
from pathlib import Path
import json
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clay_common import cli, emit, enum_set, parse, save_new


def select_engine(scene, requested):
    if requested == "KEEP":
        if scene.render.engine not in ("CYCLES", "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
            raise RuntimeError("Active engine is not EEVEE/Cycles; choose one in render.engine")
        return scene.render.engine
    candidates = ("CYCLES",) if requested == "CYCLES" else ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")
    errors = []
    for engine in candidates:
        try:
            scene.render.engine = engine  # Render-engine enum is dynamic.
            return engine
        except (TypeError, ValueError) as exc:
            errors.append(str(exc))
    raise RuntimeError(f"{bpy.app.version_string}: {requested} unavailable: {errors}")


def setup_render(scene, config, output=None):
    r = config["render"]
    engine = select_engine(scene, r["engine"])
    if engine == "CYCLES":
        if not hasattr(scene, "cycles"):
            raise RuntimeError("Cycles settings unavailable in this Blender build")
        if r["device"] == "GPU":
            addon = bpy.context.preferences.addons.get("cycles")
            prefs = addon.preferences if addon else None
            if prefs and hasattr(prefs, "get_devices"):
                prefs.get_devices()
            if not prefs or not any(d.use and d.type != "CPU" for d in prefs.devices):
                raise RuntimeError("GPU requested but no enabled Cycles GPU; configure Blender devices first")
        if r["device"] != "KEEP":
            enum_set(scene.cycles, "device", r["device"])
        scene.cycles.samples = r["samples"]
        scene.cycles.use_denoising = r["denoise"]
    else:
        settings = getattr(scene, "eevee", None)
        if not settings or not hasattr(settings, "taa_render_samples"):
            raise RuntimeError(f"{bpy.app.version_string}: EEVEE sample API not supported; inspect RNA")
        settings.taa_render_samples = r["samples"]
    scene.render.resolution_x, scene.render.resolution_y = r["width"], r["height"]
    scene.render.resolution_percentage = r["percentage"]
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    scene.render.fps, scene.render.fps_base = r["fps"], r["fps_base"]
    scene.frame_start, scene.frame_end, scene.frame_step = r["frame_start"], r["frame_end"], 1
    enum_set(scene.render.image_settings, "file_format", r["format"])
    scene.render.film_transparent = r["transparent"]
    scene.render.use_file_extension = True
    if hasattr(scene.render, "use_motion_blur"):
        scene.render.use_motion_blur = r["motion_blur"]
    elif hasattr(getattr(scene, "eevee", None), "use_motion_blur"):
        scene.eevee.use_motion_blur = r["motion_blur"]
    elif r["motion_blur"]:
        raise RuntimeError("Motion blur requested but unsupported by this build")
    if r["format"] == "FFMPEG":
        if r["transparent"]:
            raise ValueError("H.264 output cannot preserve alpha; use an RGBA PNG/EXR sequence")
        ffmpeg = getattr(scene.render, "ffmpeg", None)
        if not ffmpeg:
            raise RuntimeError("FFMPEG settings unavailable; use PNG sequence")
        enum_set(ffmpeg, "format", "MPEG4")
        enum_set(ffmpeg, "codec", "H264")
        enum_set(ffmpeg, "constant_rate_factor", "MEDIUM")
        enum_set(ffmpeg, "audio_codec", "NONE")
        enum_set(scene.render.image_settings, "color_mode", "RGB")
    else:
        enum_set(scene.render.image_settings, "color_mode", "RGBA" if r["transparent"] else "RGB")
        enum_set(scene.render.image_settings, "color_depth", "16" if r["format"] == "OPEN_EXR" else "8")
    for prop in ("view_transform", "look"):
        if r[prop] != "KEEP":
            enum_set(scene.view_settings, prop, r[prop])
    scene.view_settings.exposure, scene.view_settings.gamma = r["exposure"], r["gamma"]
    if output is not None:
        scene.render.filepath = str(Path(output).expanduser().resolve())
    scene["soft_clay_profile"] = json.dumps(config, sort_keys=True)
    return {"engine": scene.render.engine, "resolution": [r["width"], r["height"]],
            "fps": r["fps"] / r["fps_base"], "output": scene.render.filepath}


def render(scene, mode, overwrite=False):
    if not scene.camera or scene.camera.name not in scene.objects:
        raise RuntimeError("An active camera linked to this scene is required")
    output = Path(bpy.path.abspath(scene.render.filepath))
    if scene.render.image_settings.file_format == "FFMPEG":
        if mode != "animation":
            raise ValueError("FFMPEG requires --render animation")
        existing = list(output.parent.glob(output.name + "*"))
        paths = []
    else:
        frames = [scene.frame_current] if mode == "still" else range(scene.frame_start, scene.frame_end + 1)
        paths = [Path(scene.render.frame_path(frame=f)) for f in frames]
        if mode == "still":
            # write_still uses filepath + extension, not the animation frame-number path.
            extension = scene.render.file_extension
            paths = [output if str(output).endswith(extension) else Path(str(output) + extension)]
        existing = [p for p in paths if p.exists()]
    if existing and not overwrite:
        raise FileExistsError(f"Output exists: {existing[0]}; use --overwrite explicitly")
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(animation=mode == "animation", write_still=mode == "still", scene=scene.name)
    if not paths:
        paths = [p for p in output.parent.glob(output.name + "*") if p.is_file()]
    if not paths or any(not p.is_file() or p.stat().st_size == 0 for p in paths):
        raise RuntimeError("Render did not produce all expected nonempty output files")
    return [str(p) for p in paths]


def main():
    parser = cli(__doc__)
    parser.add_argument("--output", type=Path, help="Output filename or image-sequence prefix")
    parser.add_argument("--save", type=Path, help="Save configured blend copy")
    parser.add_argument("--render", choices=("still", "animation"))
    parser.add_argument("--overwrite", action="store_true")
    args, config, scene = parse(parser)
    if args.render and args.output is None:
        raise ValueError("Rendering requires explicit --output")
    result = setup_render(scene, config, args.output)
    if args.save:
        save_new(args.save, args.overwrite)
    if args.render:
        result["files"] = render(scene, args.render, args.overwrite)
    emit("render", **result)


if __name__ == "__main__":
    main()
