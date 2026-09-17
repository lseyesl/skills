# Output-Target Recipes

The destination determines modeling, topology, materials, transforms, and validation. Choose the target before finalizing the asset.

## Still image or product render

- Optimize silhouette, shading, materials, camera, and light rather than unseen topology.
- Keep procedural modifiers and high-resolution render settings separate from viewport settings.
- Validate the actual render engine, colour management, transparency, displacement, denoising, and output format.
- Deliver the source script, `.blend` when requested, and rendered files with resolution/colour-space notes.

## Animation

- Set FPS, frame range, handles, interpolation, loop boundary, motion blur, and simulation caches explicitly.
- Use image sequences for long or expensive renders.
- Check representative frames and temporal artifacts, not only a single hero frame.
- Preserve editable rigs/actions and distinguish them from baked export actions.

## Real-time/game or GLB asset

- Build at real-world scale with an intentional origin and forward/up-axis convention.
- Budget evaluated triangles, materials, texture dimensions, skin influences, bones, shape keys, and animation clips.
- Prefer Principled PBR with Base Color, Metallic, Roughness, Normal, Emission, and Alpha maps.
- Apply or export modifiers deliberately; keep armature and shape-key requirements in mind.
- Use instances during authoring but confirm how the exporter realizes or preserves them.
- Test the exported asset in the target engine/viewer; Blender appearance alone is insufficient.

Use `mcp__blender__export_scene` for GLB/FBX when its options cover the target. Verify the returned object list and bytes, then inspect the file in the consumer when possible.

Read [export-and-packaging.md](export-and-packaging.md) for executable export patterns, Blender 4.x operator names, texture packaging, LOD/collision delivery, and round-trip checks. Read [uv-and-texture-baking.md](uv-and-texture-baking.md) before exporting textured assets.

For production game meshes, also read [game-assets.md](game-assets.md). For skinned characters, read [character-delivery.md](character-delivery.md) before applying transforms, modifiers, or animation baking.

## 3D printing

- Use the requested physical units and dimensions.
- Require a closed, consistently oriented manifold unless the printing process explicitly accepts surfaces.
- Check wall thickness, clearance, unsupported overhangs, trapped volumes, tiny features, and disconnected shells.
- Apply booleans and relevant modifiers in a copy or export stage, then re-run manifold and dimension checks.
- Materials, lights, and camera are irrelevant to print validity; do not confuse a good render with printable geometry.

STL commonly carries no units, so communicate the assumed unit and confirm dimensions in the slicer. Prefer a unit-aware format when the downstream tool supports it.

## CAD-like or manufacturing reference

Blender is a mesh modeler, not a parametric solid CAD system. It can create dimensioned visual or mesh prototypes, but do not claim STEP-like analytic surfaces, constraint history, or manufacturing tolerances. Keep dimensions as named parameters, validate them numerically, and recommend a CAD handoff when exact B-rep deliverables are required.

## Reusable Blender asset

- Use stable collection/object/material/node-group names and clean origins.
- Keep modifiers editable and expose meaningful parameters.
- Remove task-owned temporary data, unused material slots, and accidental duplicates.
- Pack or document external textures and library links.
- Include a clear preview camera/light setup only when it belongs to the asset package.

Read [asset-libraries.md](asset-libraries.md) when the deliverable will be marked for Asset Browser use, linked across `.blend` files, appended as a local copy, or edited through a library override.

## Delivery checklist

For every target, report:

- Blender version used;
- script and source paths;
- scale, units, axes, and origin convention;
- evaluated object/triangle/material/texture counts where relevant;
- animation frame range and FPS where relevant;
- render/export format, path, and file size;
- checks performed in Blender and in any downstream consumer;
- assumptions and known limitations.
