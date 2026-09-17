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
- If the user has only one design image and wants a 2D modeling sheet first, use `concept-multiview-sheet` to produce five symmetric or six asymmetric views; return here after the inferred views are approved. Do not present generated hidden views as measurements.
- For reference-driven work, read [references/fidelity-and-completion.md](references/fidelity-and-completion.md) and create a module ledger before detailed geometry. Track semantic modules and their signature features separately from Blender object count.
- Treat `blockout`, `feature-complete`, and `final` as different acceptance stages. A good silhouette, attractive hero render, high object count, or presence of a coarse primitive does not authorize claiming that the referenced model is complete.
- Never hide simplification inside a single completion percentage. Report matched, simplified, blockout, and missing module counts plus both presence coverage and full-fidelity coverage.
- After every meaningful stage, verify it. A task is not complete until the expected objects/data exist and the visual result has been inspected.

## Workflow

1. **Resolve the deliverable.** Identify the requested model/scene change, real-world scale, output format and path, reference images, and whether the current `.blend` must be preserved. Infer ordinary artistic details, but do not invent dimensions or destructive scope that materially changes the result.
2. **Analyze references when present.** Read [references/reference-image-analysis.md](references/reference-image-analysis.md) and [references/fidelity-and-completion.md](references/fidelity-and-completion.md). Extract normalized silhouettes and per-view ratios, then inventory visible modules, repeated counts, deliberate asymmetry, and signature features in a module ledger. Without a scale anchor, keep the model normalized and label absolute size as unknown.
3. **Inspect Blender.** Call `get_addon_status`, then `get_scene_info`. Inspect specific existing objects with `get_object_info`. If Blender is unreachable, still create a code-only script when that satisfies the request; otherwise explain that Blender and its MCP add-on must be running.
4. **Plan ownership.** Choose a stable task ID, collection, object/material prefixes, units, coordinate convention, and the smallest set of existing objects the script may edit. For an existing scene, record relevant names and types before editing.
5. **Choose a content recipe and target stage.** Route by the table below, then design the object hierarchy, construction method, modifier/node stack, materials, lighting, and output constraints before coding. State whether this pass targets blockout, feature-complete, or final; do not silently lower that target because detailed modules are harder to script.
6. **Write the script.** Start from [assets/blender_task_template.py](assets/blender_task_template.py) when useful. Keep `build_*`, `update_*`, `validate_*`, and optional `export_*` functions separable. Read [references/python-modeling.md](references/python-modeling.md) for robust `bpy` patterns.
7. **Run in stages.** Load the saved script through a small `execute_blender_code` bootstrap. For large work, execute geometry, materials, layout, and render setup as separate deterministic stages so failures are local and earlier results remain inspectable. See [references/mcp-workflow.md](references/mcp-workflow.md).
8. **Verify and iterate.** Use `get_scene_info`, targeted `get_object_info`, and `get_viewport_screenshot`. Render matching reference views, compare silhouettes with the analyzer, and update every module status from visual evidence rather than code intent. Fix missing or simplified primary/secondary modules before tertiary polish. Adjust the persistent script rather than hand-patching the scene.
9. **Apply the completion gate.** Run `scripts/validate_module_ledger.py` and inspect a multi-view contact sheet plus a perspective view. If the requested gate fails, continue iterating or report the exact unmatched modules; never relabel a blockout or feature-complete asset as final.
10. **Persist deliberately.** Save or export only to the requested or clearly derived path. Use the MCP `export_scene` tool for GLB/FBX when suitable. Do not silently overwrite a user's source `.blend`. Apply [references/verification.md](references/verification.md) before reporting completion.

## Loading a persistent script through MCP

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

Report the script path, live scene changes, validation performed, and any `.blend`/render/export paths. For reference-driven models, include the target stage, required module count, matched/simplified/blockout/missing counts, presence coverage, full-fidelity coverage, and every user-approved simplification. State assumptions that affect scale, topology, materials, or fidelity, and distinguish a verified live result from a script that was created but could not be run. Use unqualified words such as "finished" or "complete" only when the final ledger gate reports `ready_to_claim_complete: true` and the rendered views have been inspected.
