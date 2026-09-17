# Blender Result Verification

Select checks proportional to the deliverable. Structural success alone is insufficient for a visual scene, and a good screenshot alone is insufficient for an exportable model.

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

Call `get_viewport_screenshot` after each meaningful visual stage. Inspect at least:

- silhouette and proportions;
- camera framing and clipping;
- intersections, gaps, floating parts, and z-fighting;
- smoothing, shading seams, flipped normals, material assignment, and texture orientation;
- light direction, exposure, colour balance, shadow quality, and readability.

For a scene whose deliverable is a final image or animation, render representative output; a solid-mode viewport screenshot does not validate render materials or lighting.

## Animation and simulation checks

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

Report:

- persistent script path;
- objects/collections created or modified;
- Blender version and whether live MCP execution succeeded;
- structural and visual checks performed;
- render, `.blend`, GLB, or FBX paths and sizes when produced;
- unresolved warnings or assumptions.
