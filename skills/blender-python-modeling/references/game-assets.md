# Game Asset Production

Start from the destination engine contract. A visually correct Blender mesh can still fail because of scale, pivot, triangle count, materials, UVs, skin influences, LOD names, collision naming, or unsupported shader features.

## Budget before topology

Record budgets per deliverable, not as universal numbers:

- evaluated triangles at each LOD;
- material slots and draw-call implications;
- texture sets, resolution, channel packing, and memory format;
- UV sets and vertex-colour channels;
- bones, deform influences per vertex, shape keys, and animation clips;
- collision hull count and complexity;
- instancing and batching constraints.

Measure evaluated geometry from the dependency graph. Source polygon counts do not include subdivision, Geometry Nodes, realized instances, curves, or export-time triangulation.

```python
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = obj.evaluated_get(depsgraph)
mesh = evaluated.to_mesh()
try:
    mesh.calc_loop_triangles()
    triangle_count = len(mesh.loop_triangles)
finally:
    evaluated.to_mesh_clear()
```

## Retopology and shading

- Preserve silhouette, deformation loops, hard-surface highlights, openings, and contact surfaces first.
- Put loops where they control silhouette or deformation; remove invisible internal geometry unless gameplay requires it.
- Retopologize deliberately for animated hero assets. Decimation is suitable for some static props and lower LODs, not a substitute for deformation topology.
- Decide sharp edges, custom normals, UV seams, and triangulation together. A triangulation change after normal-map baking can alter tangent-space shading.
- Test mirrored and negative-scale objects after transforms/export; avoid leaving negative determinant transforms in delivery assets.

Keep a high/editable source and a separate task-owned game-ready mesh. Do not destructively collapse the only source merely to meet export requirements.

## LODs

Define LOD thresholds in the destination engine, then create meshes that preserve the features visible at those thresholds.

- Keep origin, scale, material ordering, skeleton binding, and naming consistent across LODs.
- Reduce small silhouette details, internal faces, bevel segments, material complexity, and bone influences progressively.
- Do not generate each LOD independently from a changing source; derive them from a frozen approved version.
- Render or capture every LOD at its intended screen size. Triangle reduction alone is not acceptance evidence.

Use the engine's required naming or metadata only after it is known. Common suffixes such as `_LOD0` are conventions, not cross-engine standards.

## Collision meshes

Choose the cheapest collision representation that satisfies gameplay:

- primitives for boxes, capsules, spheres, and simple blockers;
- several convex hulls for compound shapes;
- triangle mesh collision only for static geometry when the engine supports it;
- separate trigger volumes for interaction logic.

Collision objects should have intentional transforms, closed convex geometry when required, no render materials, and names required by the target importer. Validate containment and clearance visually. Never infer that a render mesh is an acceptable collision mesh.

## Naming and hierarchy

Use deterministic ASCII-safe names when the consumer has restrictions. Keep a stable root, predictable mesh/armature relationship, and unique names after case folding when targeting case-insensitive pipelines. Avoid `.001` suffixes, hidden duplicate meshes, accidental parents, and helper objects in the export selection.

Document target-specific prefixes/suffixes for:

- render meshes and skeleton roots;
- LOD levels;
- simple/convex/complex collisions;
- sockets, locators, mount points, and effects anchors;
- animation clips and morph targets.

## Texture delivery

Use stable suffixes such as `_basecolor`, `_roughness`, `_metallic`, `_normal`, `_ao`, `_emissive`, `_opacity`, and `_height`, adjusted to the destination's naming rules. Record:

- dimensions, bit depth, alpha use, colour space, and file format;
- normal-map tangent convention;
- packed-channel layout, for example ORM = AO/Roughness/Metallic in RGB;
- tiling, clamp behavior, UV set, and UDIM use;
- compression performed by the engine versus precompressed source delivery.

Base Color/Emission are usually colour textures; scalar maps, masks, normals, AO and height are non-colour data. Do not pack unrelated colour-space data into one texture without a documented consumer shader.

## Game-asset validation

Combine [uv-and-texture-baking.md](uv-and-texture-baking.md), [export-and-packaging.md](export-and-packaging.md), and these checks:

- evaluated bounds, triangles, materials, UVs, vertex colours and influences meet the budget;
- LOD switching preserves position, silhouette, materials and skeleton;
- collision objects are exported once and recognized by the consumer;
- tangent normals match after final triangulation;
- transparent materials sort and render acceptably in the destination;
- a round-trip or engine import confirms scale, axes, pivots, hierarchy and texture paths.
