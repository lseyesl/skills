# Render configuration and batch delivery

The tools only need Blender's Python and standard library. Keep configuration as JSON partial overrides; unknown keys and invalid values fail before setup. Use `scale`, `palette`, `material`, `lighting`, `camera`, `render`, `animation`, `quality`. The complete key set and defaults live in `scripts/clay_common.py`; `palette` replaces its mapping while other sections merge.

## Engine and hardware

`render.engine`: `KEEP` preserves a valid EEVEE/Cycles engine; `EEVEE` tries runtime-supported `BLENDER_EEVEE_NEXT` then `BLENDER_EEVEE`; `CYCLES` requests Cycles. A missing engine or required sample API produces a diagnostic, not a silent renderer fallback. `samples` controls Cycles samples or the supported EEVEE render-sample property.

`render.device`: `KEEP` preserves Cycles' device choice. `CPU` explicitly selects CPU for reproducible tests. `GPU` requires an already configured and enabled GPU; the script does not select Metal/CUDA/OptiX/HIP or alter global device preferences. EEVEE's graphics backend is controlled by Blender/platform, not `render.device`. A CPU-only Cycles path remains available; EEVEE background rendering may require a working graphics context.

Runtime compatibility guards cover engine assignment, format/codec/OCIO enums, shader socket identifiers, layered versus legacy Actions, motion blur and sample properties. The executed baseline is Blender 4.5.12 LTS. Other 4.x/5.x releases are **not** claimed tested; run `scripts/test_soft_clay.py` on that build and inspect errors/RNA before extending adapters. A detected capability is not visual verification.

## Aspect ratio, frame range and color

- Landscape: e.g. `width=1920`, `height=1080`; portrait: `width=1080`, `height=1920`.
- `percentage` scales final pixel dimensions; pixel aspect stays square.
- Set `fps`, `fps_base`, `frame_start`, `frame_end`; render step is 1 so pose holds remain visible at playback rate.
- `view_transform="AgX"`, `look="KEEP"`, `exposure=0`, `gamma=1` are starting values. Keep a runtime-supported look explicitly in production profiles when shot uniformity matters; `KEEP` preserves an existing choice that may differ across projects.
- `transparent` uses RGBA for PNG/EXR. H.264 has no alpha; the tool rejects transparent FFMPEG output.
- Disable motion blur for stop-motion holds. Smooth animation may enable it after validating the installed API and rendering.

## Stills, image sequences and video

`PNG` is the default lossless display output (8-bit). `OPEN_EXR` is 16-bit scene-linear compositing output. `FFMPEG` configures MPEG-4/H.264 without audio using Blender's native encoder; select `--render animation`. These are deliberate supported presets, not an exhaustive format list.

For expensive animation, prefer PNG/EXR sequences: isolated frames are resumable and can be compared in review. Encode the approved sequence with Blender's VSE or an available encoder; ensure frame count, order, actual FPS, dimensions, codec and playback duration match. The direct FFMPEG route rerenders animation and is convenient for a short preview, not a resumable sequence encoder.

```bash
# Existing configured .blend; commands shown from repository root.
blender --background /absolute/output/demo.blend --python-exit-code 1 \
  --python skills/blender-soft-clay/scripts/setup_render.py -- \
  --config /absolute/project/style.json --output /absolute/output/frame- \
  --render animation
```

An image-sequence prefix emits numbered files such as `frame-0001.png`. Still output uses the supplied filename plus an extension when needed. Blender may add frame-range suffixes to video filenames; use the emitted `files` list as the actual result. Each render preflights existing outputs and rejects overwrite unless `--overwrite` is explicit.

For a saved configured scene, native batch rendering also works:

```bash
blender --background /absolute/output/demo.blend -o /absolute/output/frame- -F PNG -s 1 -e 24 -a
```

Blender CLI arguments execute in order; place the render action last. Avoid a preexisting output prefix; native `-a` does not use this Skill's overwrite guard. Use the scripted path when that guard or config validation matters.

## Evidence

Record engine, device policy, Blender build, profile, resolution, FPS and frame range. Decode rendered images and check finite pixels and expected dimensions/count. A valid image or MP4 file is not proof of correct composition or motion; inspect representative frames and play the video. Renderer differences, custom OCIO, DOF noise and low sample counts can shift the look; test in the final renderer.
