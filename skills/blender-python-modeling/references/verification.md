# Blender Result Verification

Select checks proportional to the deliverable. Structural success alone is insufficient for a visual scene, and a good screenshot alone is insufficient for an exportable model.

New creation starts in an owned empty task scene with no startup objects. Verify the saved file opens in that scene without a verifier selecting it on the user's behalf. Before render comparisons, execute and record the [render preflight](production-workspace.md). Before final claims, apply [use-specific acceptance](acceptance/usable-asset.md); a static fitter or disposable rig test cannot certify an animation asset.

## Structural checks

- Expected collection, object, material, camera, light, armature, action, and node-group names exist.
- Object types and parent/constraint relationships match the design.
- Rerunning the script does not duplicate generated data.
- Existing out-of-scope objects and datablocks remain present and unchanged.
- No task-owned temporary objects or materials remain unintentionally.

Use `get_scene_info` for the inventory and `get_object_info` for important objects.

## Geometry checks

- Dimensions and location agree with the requested scale and coordinate convention.
- Vertex/edge/face or triangle counts are plausible for the target use.
- Normals face consistently; there are no accidental zero-area faces, duplicate vertices, isolated geometry, or unapplied transforms that break the output.
- Watertight/manifold checks pass when required for fabrication, boolean solids, collision, or volume.
- Modifiers are ordered correctly and remain unapplied when editability, rigs, or shape keys require it.
- Symmetry, clearance, thickness, pivot/origin placement, and part alignment meet the model's purpose.

Put detailed checks in the persistent script and print a compact pass/fail summary. Use evaluated meshes when checking the final modifier result.

## Visual checks

Before multiple construction views enter Blender, require their scoped [pre-model review](../../concept-multiview-sheet/references/pre-model-review.md). Check pose suitability, common scale/landmarks, projection/occlusion, structure/colour and axes; reject critical conflicts for affected detailed geometry. The imported-workspace calibration below is a second check, not a substitute for source consistency.

For reference-driven work, first inspect the imported, calibrated Image Empty
workspace in the corresponding orthographic views: source images, orientation,
scale, landmark alignment, opacity/front display, view filtering and locked
transforms. Reopen the derived file to confirm images are packed or resolve
through portable paths. Merely finding reference objects is not a visual pass.

At each geometry stage, retain a matched-view reference/model overlay or
side-by-side comparison and inspect local features as well as the outer contour.
For characters, check face landmarks relative to the head, skull depth from the
side, and limb width/continuity through joints; use equivalent functional
landmarks for props. Fix major position/proportion errors before material polish.
Explain any AI artifact rejected on structural evidence, or seek human judgment
when a material ambiguity remains unresolved. Mesh integrity, expression-switch
success and ledger validation do not certify reference fidelity.

Call `get_viewport_screenshot` after each meaningful visual stage. Inspect at least:

- silhouette and proportions;
- camera framing and clipping;
- intersections, gaps, floating parts, and z-fighting;
- smoothing, shading seams, flipped normals, material assignment, and texture orientation;
- light direction, exposure, colour balance, shadow quality, and readability.

For a scene whose deliverable is a final image or animation, render representative output; a solid-mode viewport screenshot does not validate render materials or lighting.

Keep current geometry and appearance signatures in visual comparison records. Shader inputs/groups, source textures, UV/region attributes, lights/world, cameras and render/colour settings can invalidate an image judgment without changing vertices. The executable comparison gate checks both; external caches/engines need explicit additional dependencies. See [staged-execution.md](staged-execution.md). A valid receipt establishes freshness and declared inspection, not image agreement.

## Animation and simulation checks

Use the [character acceptance levels](character-delivery.md#separate-animation-acceptance-levels) for rigs: small FK poses, full motion-range deformation, and complete locomotion contact/loop checks are distinct. Inspect actual evaluated soles and intended materials; finite vertices and weight sums cannot certify walking.

- Scrub or sample the start, middle, end, and important contact frames.
- Confirm frame rate, frame range, interpolation, looping, constraints, and object origins.
- Check for penetrations, unstable simulations, dependency cycles, and unbaked caches.
- Do not apply modifiers or transforms that invalidate rigs, shape keys, or cached simulations.

## Save and export checks

- Use an absolute output path and create only the intended parent directory.
- Do not overwrite an existing source `.blend` without explicit user direction.
- For GLB/FBX, verify the returned exported object list and file byte size, then confirm the file exists.
- Confirm axis, scale, materials, normals/tangents, animations, modifiers, texture packing, and selection scope against the target application.
- Preserve licence and attribution for imported external assets.

## Completion evidence

For generic reference-driven builds, run the live workspace/review gate from
[reference-workspace-tool.md](reference-workspace-tool.md) before final claims.
Attach the current calibration and model-comparison records, consumed landmark
bindings and actual reference-visible viewport captures. A source image packed
in the blend or an import count does not show that it influenced geometry.

Report:

- persistent script path;
- objects/collections created or modified;
- Blender version and whether live MCP execution succeeded;
- structural and visual checks performed;
- render, `.blend`, GLB, or FBX paths and sizes when produced;
- unresolved warnings or assumptions.

## Source, evaluated triangles and reimport are distinct layers

Use production_checks.inspect_mesh for source topology plus evaluated triangulation. The existing degenerate_faces field measures original polygon area in mesh-local coordinates; degenerate_triangles measures the actual tessellation in world coordinates, including object transforms. A positive-area n-gon can contain zero-area triangles. Defaults use min_triangle_area=5e-13 world-unit squared; record a purpose/scale-derived tolerance rather than treating it as a universal physical threshold. Reports include offending triangle/polygon IDs, retained source diagnostics and evaluated structural_issues. A legal open control cage closed by a modifier is inspected as two different representations.

Use inspect_asset / require_asset_geometry on the complete explicit asset whitelist at blockout, refine and delivery. They count evaluated triangles in aggregate; missing max_triangles is budget_passed=null, not a budget success. An exception preserves the measured report and does not repair geometry. The template binds limits in modeling-plan.json; the static fitter uses validation.working_max_triangles and validation.min_triangle_area for source checks, and separately reports the eventual validation.max_triangles delivery target. Use resource_limits(plan, stage): final max_triangles applies only at delivery/reimport; blockout_max_triangles and working_max_triangles are optional explicit working-resource caps, with no fallback to the final cap. Invalid geometry or a failed explicit working cap blocks that stage. An otherwise valid refined source may exceed the delivery cap and proceed to source-fidelity review, not budgeted delivery acceptance. Freeze a reviewed source, then verify its optimized copy separately; see [realtime optimization](procedures/delivery/realtime-optimization.md).

asset_delivery.export_glb accepts max_triangles, min_triangle_area and require_closed. It rejects bad current evaluated geometry before export and checks every declared animation sample in the disposable package and actual reimport. Source preflight and worker failure reports are retained; a format-valid GLB may still fail these checks.

GLB attribute/normal seams can split vertices even for a closed cube. Raw reimport boundary counts remain in the report; when require_closed is requested, the worker additionally measures geometric closure on a temporary position-welded copy at the declared spatial tolerance. This does not modify the imported/source mesh, close genuine holes or certify printability, self-intersections or thin-wall strength. Inspect the recorded tolerance and both raw/seam-welded results; never rename that check as proof of raw topological manifoldness.

Constant PBR transport checks do not prove source appearance. Retain original-source comparisons independently of construction-mask agreement, and preserve source/clay/material views when optimizing topology or resources.
