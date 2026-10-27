# Soft Clay Style

Produce an editable, reproducible scene plus visually reviewed render evidence. This is an art-direction layer over general Blender modeling, not a character generator or a physics simulator.

All `scripts/...` paths refer to the shared `blender-styles/` root. Style examples and historical results stay in this style directory. Read the [shared workflow](../../references/workflow-and-review.md) before applying this profile.

## Workflow

1. Inspect the project and current scene. Resolve asset scale, owned targets, static/animation delivery, aspect ratio, render engine, playback FPS and pose cadence. Preserve unrelated data and source `.blend` files. For live MCP work, use [blender-python-modeling](../../../blender-python-modeling/SKILL.md) for inspection, execution and save/export conventions; its rigging and reference-analysis procedures remain authoritative.
2. Write a project-local Python recipe and JSON style profile. Load only the references needed below. Use [examples/preview.json](examples/preview.json) or [examples/portrait.json](examples/portrait.json) as partial overrides of `scripts/clay_common.py::DEFAULTS`. Keep one palette/material/color-management profile across shots. Do not copy the example character or scene layout into a production project unless requested.
3. Build economical, rounded silhouettes and modular assets. Preserve rig topology and unapplied deformation stacks. Choose smooth organic surfaces and flat broad planar faces deliberately; keep bevels small relative to each part. Review silhouettes before materials.
4. Import the bundled tools from their absolute `scripts/` directory in the project recipe. Call `create_palette`, `setup_lighting`, `setup_render`, and, for explicit animated targets, `setup_animation`. Material generation does not replace existing material slots. Lighting replaces the active world and, by default, camera references, while retaining prior datablocks; use `with_camera=False` to preserve a shot camera. Existing lights remain active and need review.
5. Evaluate start, contact/extreme, middle, last and loop-boundary frames. Configure playback FPS separately from pose holds. For a 24-frame loop, key frames 1 and 25 to the same pose and render 1–24. A two-frame hold at 24fps gives 12 pose updates/second without slowing playback. Constrained rigs, NLA and drivers require explicit evaluated baking before the timing helper.
6. Run `validate_scene` / `validate_clay_scene.py`. Render representative images in the chosen engine; inspect matte response, micro-relief, silhouette, framing, shadows, deformation and contacts. Automated checks do not certify proportions against a design, collision-free motion, or perceptual shot consistency. Keep those visual gates explicit.
7. Save to a derived output path, render a restartable image sequence where appropriate, and deliver scripts, profile, `.blend`, renders, QA report, Blender version and limitations. Use `--python-exit-code 1` in batch runs so Python failures reach the shell. Do not claim a finished visual scene merely because structural QA passes.

## Load references progressively

| Work | Read |
|---|---|
| Mesh budget, silhouette, bevels, modular or deformable assets | [modeling](references/modeling.md) |
| Palette, procedural shader, noise scale, material assignment | [materials](references/materials.md) |
| Scene scale, large lights, contact shadows, camera/DOF | [lighting](references/lighting.md) |
| Keyframes, rigs, stop-motion holds, 12/24fps, loop seam | [animation](references/animation.md) |
| Renderer/device/OCIO compatibility, sequences/video/batch | [rendering](references/rendering.md) |
| Executable checks, manual gates and multi-shot acceptance | [quality check](references/quality-check.md) |
| Minimal commands and applying to an existing project | [usage](references/usage.md) |
| Executed evidence and untested boundaries | [test results](references/test-results.md) |

## Resource ownership and scope

- Tools tag generated datablocks with `soft_clay_owner = <owner>::<scene.name>` and `soft_clay_role`. Keep owner and scene name stable on reruns. Find resources by tags; refuse unowned name collisions and linked/override edits. Independent scenes get independent rigs/materials.
- Never clear the user's scene, remesh a bound character, replace all material slots, apply rig transforms, or force a GPU backend as part of styling. The demo alone rebuilds its owned test meshes.
- The animation helper copies non-owned/shared Actions, preserves the source and operates only on the object's assigned slot. It does not retarget, auto-rig or solve contacts. Reruns replace only its named timing modifiers.
- CLI setup scripts change the current process but do not automatically save. Use a project recipe or `setup_render.py --save` to persist all stages. Avoid separate unsaved Blender processes for dependent setup stages.
- `continuous-action` may supply motion references only when its action-library workflow is requested; this Skill has no dependency on `A.blend` or image generation. `concept-multiview-sheet` supplies inferred design views, not measured geometry.

## Minimal smoke test

From the repository root, replacing `blender` with the host's executable:

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python skills/blender-styles/scripts/build_demo.py -- \
  --config skills/blender-styles/styles/soft-clay/examples/preview.json \
  --output .tmp/clay-smoke --render still
```

This creates a new abstract test scene, a saved `.blend`, a preview, and `quality.json`. It preserves the original startup scene. The default tools have no project paths; output locations come from the caller.
