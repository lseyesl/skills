# Executed tests and known limits

This is the historical soft-clay baseline, originally executed before the unified `blender-styles` directory migration. Reproduction commands below use current paths; the dates, results and artifact locations retain their original provenance. Migration-specific checks are recorded separately in [migration validation](../../../references/migration-validation.md).

## Baseline and reproduction

Executed on **2026-10-12**, macOS, **Blender 4.5.12 LTS** (build `84afd5f785f7`), bundled Python 3.11.11. No third-party Python dependency or GPU preference change was needed. The shipped suite uses CPU Cycles and the installed graphics backend for EEVEE.

```bash
blender --background --factory-startup -t 2 --python-exit-code 1 \
  --python skills/blender-styles/scripts/test_soft_clay.py -- \
  --output .tmp/clay-tests --render
```

Use an empty output directory. If the host sandbox blocks Blender's graphics initialization, run through the host's normal approval flow; do not change global GPU preferences to bypass it. This host required approved execution outside the sandbox after a Metal startup crash before Python ran.

## Results

**25/25 integration checks passed.** The reproducible machine summary is [evals/test-summary.json](../evals/test-summary.json). Full local reports and generated artifacts are in the repository's ignored `.tmp/blender-soft-clay/verified/` directory; generated `.blend`/images/video are not bundled as required Skill assets.

| Verification | Evidence |
|---|---|
| General scene | Multipart abstract model, closed ground/block/cone/pebble, 5 procedural clay colors, 3 Area lights, camera, bob/tilt loop |
| Repeated execution | 3 reruns, identical counts across objects, meshes, materials, cameras, lights, worlds, Actions and collections |
| Preservation | Startup objects/world retained; unowned name collisions rejected; shared demo object rejected before rebuild |
| Shader | Required shader nodes/links, sRGB conversion, actual roughness/specular profile drift detected |
| Timing | 24fps with two-frame holds (12 pose updates/sec), six object curves, smooth timing restored, matching loop endpoint |
| Source animation | Shared source Action preserved, independent copy created, copy reused; artistic timing conflicts fail before edits |
| Binding | New one-bone test rig, 42 normalized weighted vertices, unweighted-vertex negative case, pose-loop endpoint |
| Geometry QA | Zero-scale and loop mismatch rejected; project dimension expectations pass/fail as intended |
| Independent project | Separate scene, 2× scale, custom two-color palette, portrait camera, quadratic light-power scaling, independent world/camera |
| Shot consistency | Matching profiles pass; profile and actual exposure drift fail |
| Invalid configuration | 15 malformed/unknown/out-of-range/type-invalid overrides rejected |
| Cycles | CPU landscape PNG, 480×270, 8 samples, decoded finite pixels |
| EEVEE | Independent portrait PNG, 270×480, 8 samples, decoded finite pixels |
| Image sequence | 24 decoded PNG frames, 160×90, 4 samples, frame range 1–24 |
| Video | Native H.264/MPEG-4, 160×90, 24fps, 24 frames, 1.000 seconds; ffprobe metadata and full ffmpeg decode passed |
| Output protection | Existing `.blend`/still overwrite rejected; corrupt image rejected |

The standalone material, lighting (`--keep-camera`), animation (`--objects`), render-setup and quality-check CLIs were also executed on saved scenes. Background demo creation was exercised during development; the integration suite runs the same builder functions and verifies the final defaults.

## Visual review

Inspected the final Cycles still, EEVEE portrait and contact sheet covering frames 1, 7, 13, 19, 23 and 24. The preview demonstrates muted matte colors, broad soft highlights, rounded economical shapes and coherent silhouette through the bob/tilt loop. All foreground bounds fit the final camera. The abstract loop deliberately lifts the whole model; it does not demonstrate walking foot locks.

EEVEE's low-sample portrait has weaker contact detail and a distant floor/background edge near the top; it is a test preview rather than a final miniature shot. Final shot layout, backdrop, shadow detail and DOF need project-specific refinement. Sequence/video are deliberately tiny, low-sample validation outputs; neither is presented as production resolution. Full decoding and pose/endpoint checks passed; a production edit still requires real-time playback and contact review.

## Known limits

- Only this Blender version was executed. Other 4.x/5.x builds have runtime guards but require their own suite/render review. GPU Cycles and custom OCIO are not executed test targets.
- Shader coordinates are object-space. Deforming characters can need UV/rest-position textures or baking to avoid swimming. Procedural materials may require baking for external-engine export.
- This is a style/tool layer, not auto-rigging, retargeting, motion-library packaging, physical clay or collision simulation. Production constraints, NLA and drivers require evaluated baking before timing setup.
- Loop equality and normalized weights are structural checks, not proof of good deformation, contact or seamless velocity. The checker leaves `visual_approved=false` deliberately.
- Shot comparison verifies stored style parameters and actual color-management/FPS; it does not compare all actual shader/light edits or rendered perceptual similarity.
- EXR, GPU configurations, constrained rigs, sophisticated simulations and large production sequences are documented capabilities/workflows but were not part of this rendering baseline.

## Existing-Skill boundaries

`blender-python-modeling` supplies general modeling, reference analysis, rigging, export and live MCP conventions. This style uses the clay palette/shader, scaled studio rig, timing adapter, render presets and focused QA now housed in the unified `blender-styles/scripts/` directory. Those tools import no Python code from another Skill, so the unified executable tool directory remains self-contained. Documentation links provide deeper workflow guidance.

`continuous-action` remains responsible for its `A.blend`-based keyframe/image-reference workflow. `concept-multiview-sheet` remains responsible for inferred 2D design views. Neither is a runtime dependency; no assets from those Skills are copied into this one.
