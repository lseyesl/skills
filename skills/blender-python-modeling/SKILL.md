---
name: blender-python-modeling
description: Create, inspect, or modify Blender models and scenes with reproducible Python (`bpy`) scripts and the locally configured `mcp-for-blender` server. Use for AI/reference-image analysis, modeling, UVs, texture baking, materials, geometry nodes, game or character assets, scene assembly, asset libraries, cameras, lights, rendering/compositing, animation, physics, `.blend` work, or export. Includes concrete recipes validated on Blender 4.5 LTS with runtime guards for other 4.x/5.x versions. Do not use for another DCC, Blender installation, or a request that only needs a 2D image.
---

# Blender Python Modeling

Build Blender work as an inspectable pipeline: inspect the live file, write a persistent Python script, run it through Blender MCP, and verify both scene structure and appearance.

## Core contract

- Prefer a reusable `.py` file over a long one-off MCP code string. In an existing project, follow its script layout; otherwise use `scripts/blender/<task-name>.py`.
- Use the configured `mcp__blender__*` tools from `ahujasid/mcp-for-blender`. Do not substitute similarly named tools from other Blender MCP implementations.
- Before mutation, call `get_addon_status` and `get_scene_info`. Pass the user's latest Blender request verbatim as `user_prompt` on every MCP call; do not replace it with an internal plan step.
- Preserve existing work. Never clear the whole scene, delete unowned datablocks, or overwrite an existing `.blend` merely to make a script repeatable. Give generated objects a stable task prefix or owner property and replace only those objects.
- Prefer `bpy.data`, `bmesh`, and direct property assignment to context-sensitive `bpy.ops`. Use operators only when there is no practical data-API equivalent, and establish the required mode, active object, selection, area, and override explicitly.
- Treat Blender version, RNA properties, enum identifiers, node sockets, and operator signatures as runtime facts. Use `bpy_api_lookup` or `describe_node_type` before relying on uncertain or version-sensitive details.
- Treat Blender 4.5.12 LTS as the tested baseline, not as proof of compatibility with every 4.x or 5.x build. Read [references/compatibility.md](references/compatibility.md) before using version-sensitive features.
- Run host-side reference-image tools through this skill's uv project (`uv run --project <skill-dir> ...`). Do not install OpenCV/NumPy into Blender's bundled Python or the user's global Python.
- For “generate a design image, then make its model” tasks, include `concept-multiview-sheet` before detailed geometry: five symmetric or six asymmetric design views, reviewed for consistent pose and projection. Do not wait for the user to request missing views. For ordinary single-photo tasks, add views when hidden shape/attachment/orientation materially constrains modeling; do not force image generation for trivial edits or an explicitly waived sheet. Generated hidden views are inferences, not measurements. A flawed sheet stays preview-only; a later model render cannot retroactively satisfy pre-model reference preparation.
- Before building reference-driven geometry, establish an in-Blender reference workspace: separate view images, axis-aligned Image Empties, calibrated scale/origin, adjustable opacity, front depth display, and axis-view visibility. Inspect actual front/side overlays before proceeding; an image-analysis JSON or imported-object count does not replace this step. Follow [references/reference-image-analysis.md](references/reference-image-analysis.md).
- Treat AI references as fallible design evidence. Resolve local artifacts using reliable source evidence, anatomy/mechanics, and consistent views; record the interpretation. When materially different plausible interpretations remain and evidence cannot decide, ask for human judgment on the affected region and continue independent work. Do not reproduce impossible geometry or silently redesign identity-defining features to fit a generated panel.
- For reference-driven work, read [references/fidelity-and-completion.md](references/fidelity-and-completion.md) and create a module ledger before detailed geometry. Track semantic modules and their signature features separately from Blender object count.
- Treat `blockout`, `feature-complete`, and `final` as different acceptance stages. A good silhouette, attractive hero render, high object count, or presence of a coarse primitive does not authorize claiming that the referenced model is complete.
- Never hide simplification inside a single completion percentage. Report matched, simplified, blockout, and missing module counts, separating presence from reference agreement. Any coverage fractions derived from ledger labels are bookkeeping, not measured reconstruction accuracy; a `matched` label needs view-specific comparison evidence.
- After every meaningful stage, verify it. A task is not complete until the expected objects/data exist and the visual result has been inspected.
- Before a full render suite, pass the [local shape and detail review](references/local-feature-review.md): surface orientation, thickness, attachments and signature relief in the evaluated mesh and intended lighting. A vein formula, bump shader or nonzero displacement does not prove the referenced feature is readable. Review one representative repeated part first.
- For a requested art style, use the [blender-styles index](../blender-styles/SKILL.md), then read only the selected style and needed references. Style rules supplement this modeling/reference workflow; they do not replace proportion, geometry or delivery checks.

## Workflow

1. **Resolve the deliverable.** Identify the requested model/scene change, real-world scale, output format and path, reference images, and whether the current `.blend` must be preserved. Infer ordinary artistic details, but do not invent dimensions or destructive scope that materially changes the result.
2. **Analyze references when present.** Read [references/reference-image-analysis.md](references/reference-image-analysis.md) and [references/fidelity-and-completion.md](references/fidelity-and-completion.md). Extract normalized silhouettes and per-view ratios, then inventory visible modules, repeated counts, deliberate asymmetry, and signature features in a module ledger. Identify trustworthy regions, AI artifacts, and cross-view conflicts; choose controlling evidence per region and record reasoned inferences. Ask for human judgment only when an unresolved choice materially changes the result. Without a scale anchor, keep the model normalized and label absolute size as unknown.
3. **Inspect Blender.** Call `get_addon_status`, then `get_scene_info`. Inspect specific existing objects with `get_object_info`. If Blender is unreachable, follow the bounded connection recovery in [references/mcp-workflow.md](references/mcp-workflow.md): check whether Blender is running, launch it in normal UI mode if absent (the window may stay in the background or minimized), and retry before asking the user to start it manually. Do not use `--background` / `-b` headless mode to recover an MCP connection. A code-only script remains an option when that satisfies the request; label it unexecuted.
4. **Plan ownership.** Choose a stable task ID, collection, object/material prefixes, units, coordinate convention, and the smallest set of existing objects the script may edit. For an existing scene, record relevant names and types before editing.
5. **Establish the reference workspace before geometry.** For reference-driven tasks, import the separate views into a task-owned collection as Image Empties facing their corresponding orthographic axes. Set adjustable opacity (start around 0.35–0.5), front depth display, and appropriate front-side/axis-only visibility; lock selection/transforms after calibration. Align centerline, ground/origin, scale and semantic landmarks, keeping unreliable views supplemental. Inspect front/side screenshots with the reference visible; preserve the packed images and calibration/interpretation record in the deliverable. If Blender cannot be run, label this prerequisite unexecuted instead of claiming reference-guided modeling. Skip this stage only when the task has no visual reference or the user explicitly waives it.
6. **Choose a content recipe and target stage.** Route by the table below, then design the object hierarchy, construction method, modifier/node stack, materials, lighting, and output constraints before coding. State whether this pass targets blockout, feature-complete, or final; do not silently lower that target because detailed modules are harder to script.
7. **Write the script.** Start from [assets/blender_task_template.py](assets/blender_task_template.py) when useful. Keep `build_*`, `update_*`, `validate_*`, and optional `export_*` functions separable. Read [references/python-modeling.md](references/python-modeling.md) for robust `bpy` patterns. Derive reference-driven positions and proportions from the calibrated landmarks/profiles, not unexplained hand-picked coordinates.
8. **Run in stages.** Load the saved script through a small `execute_blender_code` bootstrap. For large work, execute geometry, materials, layout, and render setup as separate deterministic stages so failures are local and earlier results remain inspectable. See [references/mcp-workflow.md](references/mcp-workflow.md).
9. **Verify and iterate against the references.** Use scene/object inspection and viewport screenshots with the relevant reference visible. Inspect matched-camera overlays and local landmark/profile differences, including facial placement, head width/height/depth, and limb thickness continuity for characters. Use the analyzer as supporting evidence; whole-object silhouette overlap cannot validate these local features. Fix major mismatches before materials or tertiary polish. Reconsider suspected AI artifacts using the recorded evidence policy, and ask for human judgment when it cannot resolve a material ambiguity. Update module statuses from these comparisons and adjust the persistent script.
10. **Apply the completion gate.** Run `scripts/validate_module_ledger.py` with per-feature comparison records and final review evidence, and inspect a multi-view contact sheet plus a perspective view. The validator checks evidence declarations, not image agreement; do not mark modules `matched` in bulk because they exist. User corrections invalidate affected matches and final review until repaired and re-reviewed. If the requested gate fails, continue iterating or report exact unmatched modules; never relabel a blockout or feature-complete asset as final.
11. **Persist deliberately.** Save or export only to the requested or clearly derived path. Use the MCP `export_scene` tool for GLB/FBX when suitable. Do not silently overwrite a user's source `.blend`. Apply [references/verification.md](references/verification.md) before reporting completion.

## Loading a persistent script through MCP

For repeated character/reference fitting, use the executable [reference-fitting workflow](references/reference-fitting/workflow.md) and `scripts/fit_character.py`: reviewed semantic masks/anchors, fixed render channels, component metrics, configurable builders, bounded local candidates, locks, immutable snapshots and rollback. Read the [architecture audit](references/reference-fitting/architecture.md) before extending it. Keep subject-specific coordinates in JSON and reuse existing geometry/style helpers. A 2D threshold or temporary limb rig test does not satisfy final 3D/animation acceptance.

Send only this style of bootstrap through `execute_blender_code`, substituting an absolute path safely:

```python
from pathlib import Path

script_path = Path("/absolute/project/scripts/blender/build_asset.py")
scope = {"__name__": "__main__", "__file__": str(script_path)}
exec(compile(script_path.read_text(encoding="utf-8"), str(script_path), "exec"), scope)
```

If Blender cannot read the project path, execute the same script in several small, self-contained MCP chunks. Each chunk must re-import its modules and retrieve prior objects by stable name or owner tag; do not depend on Python globals surviving between calls.

## Content routing

Read only the references needed for the current request:

| Task | Read |
|---|---|
| Soft clay, handmade plasticine, or mixed art direction | [blender-styles](../blender-styles/SKILL.md), then the selected `styles/<id>/STYLE.md` |
| AI render, photo, line drawing, or multi-view reference input | [references/reference-image-analysis.md](references/reference-image-analysis.md) and [references/fidelity-and-completion.md](references/fidelity-and-completion.md) |
| Mesh, curve, hard-surface, repeated or organic forms | [references/modeling-recipes.md](references/modeling-recipes.md) |
| UV unwrap, texel density, lightmap UV, UDIM, or texture baking | [references/uv-and-texture-baking.md](references/uv-and-texture-baking.md) |
| PBR/procedural materials or Geometry Nodes | [references/materials-and-nodes.md](references/materials-and-nodes.md) |
| Retopology, polygon budgets, LODs, collision meshes, or game-engine naming | [references/game-assets.md](references/game-assets.md) |
| Cameras, studio lighting, world, render settings | [references/scene-lighting-rendering.md](references/scene-lighting-rendering.md) |
| Render passes, Cryptomatte, denoise, compositing, or multilayer EXR | [references/compositing-and-passes.md](references/compositing-and-passes.md) |
| Keyframes, constraints, drivers, armatures | [references/animation-and-rigging.md](references/animation-and-rigging.md) |
| Skin weights, deform rigs, shape keys, root motion, or character export | [references/character-delivery.md](references/character-delivery.md) |
| Rigid bodies, cloth, fluids, soft bodies, force fields, or caches | [references/physics-and-simulation.md](references/physics-and-simulation.md) |
| Asset Browser, reusable assets, linked/appended libraries, or overrides | [references/asset-libraries.md](references/asset-libraries.md) |
| Still image, animation, game asset, 3D-print output, or target selection | [references/output-targets.md](references/output-targets.md) |
| Save, GLB/glTF, FBX, OBJ, STL, asset packaging, or round-trip validation | [references/export-and-packaging.md](references/export-and-packaging.md) |
| Blender version uncertainty or an API mismatch | [references/compatibility.md](references/compatibility.md) |

The cross-cutting references remain applicable:

- For tool order, exact local MCP names, connection failures, and staged execution, read [references/mcp-workflow.md](references/mcp-workflow.md).
- For idempotence, context safety, transforms, naming, and performance, read [references/python-modeling.md](references/python-modeling.md).
- For structural, geometric, visual, render, save, and export acceptance checks, read [references/verification.md](references/verification.md).

## Completion report

Report the script path, scene changes, validation performed, and any `.blend`/render/export paths. For reference-driven models, include the reference collection/calibration record and comparison evidence, target stage, required module count, matched/simplified/blockout/missing counts, and every user-approved simplification. If reporting presence/full-fidelity coverage fields, identify them as ledger-derived counts, not image similarity or measured reconstruction accuracy. State rejected AI artifacts, inferred corrections, unresolved choices and assumptions affecting scale, topology, materials or fidelity. Distinguish a verified Blender result from an unexecuted script. Use unqualified words such as "finished" or "complete" only when the final ledger gate reports `ready_to_claim_complete: true` and reference comparisons plus rendered views have passed review.
