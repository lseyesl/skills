# Soft low-poly modeling

## Art-direction contract

Measure silhouette and part ratios against the approved design before counting faces. Low-poly describes economical geometry, not automatically flat shading. A rounded readable shape with 100–1000 base faces per small prop is a useful starting point; the configured QA budget defaults to 5000 **base and evaluated faces per mesh**. Set project budgets explicitly; subdivision and bevels count toward evaluated complexity.

Use few large, recognizable masses with modest asymmetry where designed. Avoid thin spikes, razor edges and unnecessarily dense detail. In miniature shots, secondary detail should be visible at output resolution and not compete with the silhouette. Keep head/body, limb length, prop thickness and origin conventions in an asset manifest. Uniform global scale should preserve proportions; changing one part's scale requires review in multiple views.

## Geometry recipe

1. Block out with cubes, low-segment UV spheres, icospheres, cones or curves. Build vertices at intended dimensions using `bmesh` or data API.
2. Start bevel width at 3–8% of the smallest relevant dimension, 2–3 segments, and angle-limited edges. A bevel smaller than a pixel rarely contributes. Inspect overlap/clamping in narrow features; do not automatically bevel all deforming edges.
3. Use smooth polygons on rounded organic volumes and flat polygons on broad planar panels. Blend these by per-polygon `use_smooth`; inspect normals on the resulting bevel stack. Flat-shaded icospheres can retain facets when intentionally desired.
4. Recalculate normals on newly built owned meshes. Validate zero-area faces, disconnected vertices and negative/zero transforms. Do not blindly repair or apply modifiers on an existing asset.
5. Inspect orthographic front/side/back plus the shot camera. Refine the silhouette before adding texture detail.

```python
# An explicitly authorized mesh, not all objects in the scene.
for face in mesh.polygons:
    face.use_smooth = face.index in organic_face_indices
bevel = obj.modifiers.new("asset_bevel", "BEVEL")
bevel.width, bevel.segments = intended_width, 2
bevel.limit_method = "ANGLE"
```

Do not rely on old `mesh.use_auto_smooth` API. Smoothing-by-angle, custom normals and weighted normals differ across Blender versions; inspect capabilities and verify them in renders. The bundled example uses portable polygon smoothing and Bevel without requiring any of those APIs.

## Deforming and modular assets

- Keep loops around bending joints, enough longitudinal segments for deformation and clean quad flow where helpful. Rigid low-poly parts can use object/bone parenting instead of skinning.
- Simplify before rigging. Decimate/remesh after binding may invalidate weights, shape keys, UVs and vertex-index dependent effects. Never use a generic style pass to destructively simplify a bound mesh.
- Keep base meshes, rig, accessory parts and material slots modular. Prefer instances for identical rigid props; make data single-user before per-instance mesh edits.
- Store real dimensions or normalized ratios and their uncertainty. Freeze pivots and rest transforms before binding; do not apply transforms to a rigged model to “fix” procedural texture scale.
- Mark approved assets for Asset Browser using the existing skill's library workflow. No bundled character, story or scene naming convention is required.

Reuse [general modeling rules](../../../../blender-python-modeling/references/python-modeling.md), [modeling recipes](../../../../blender-python-modeling/references/modeling-recipes.md), [character delivery](../../../../blender-python-modeling/references/character-delivery.md) and [asset libraries](../../../../blender-python-modeling/references/asset-libraries.md) for construction, binding, export and reuse. This reference adds style choices, not a second modeling framework.
