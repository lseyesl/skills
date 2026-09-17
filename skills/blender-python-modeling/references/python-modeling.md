# Blender Python Modeling Rules

## Script shape

Use a stable task identifier and keep generated data visibly owned by the task. Split the script into functions and end in a small `main()`:

```python
def main():
    remove_previous_generated_data()
    build_geometry()
    build_materials()
    assemble_scene()
    validate_result()

if __name__ == "__main__":
    main()
```

Rerunning the script should converge on the same result. Tag objects with a custom owner property and delete only matching generated objects. Do not use `bpy.ops.object.select_all(...); bpy.ops.object.delete()` as reset logic in a user's scene.

## Data API before operators

Prefer:

- `bpy.data.meshes.new`, `bmesh`, `mesh.from_pydata`, and `foreach_set` for geometry;
- `bpy.data.objects.new` and explicit collection linking;
- direct transforms, constraints, modifier properties, keyframes, and node tree edits;
- evaluated dependency graph data for measurements.

Use `bpy.ops` only when Blender exposes no reasonable data-API equivalent. Before an operator, set the correct mode, active object, selection and context override. Restore any user-facing mode/selection state when practical.

For background-compatible scripts, avoid viewport-only operators and UI area assumptions.

## Version and API safety

- Read Blender's actual version from `get_addon_status`; do not target a guessed release.
- Query `bpy_api_lookup` before using an uncertain operator argument, RNA property, enum, or version-sensitive API.
- Never hardcode enum identifiers without confirming them from RNA. `scene.render.engine` is a dynamic-enum exception: keep the valid current value, or assign a desired value inside `try/except TypeError` and handle the reported valid identifiers.
- Query `describe_node_type` before indexing unfamiliar sockets or when socket layout depends on a node property.
- Use feature detection (`hasattr`, RNA inspection) only as a compatibility boundary, not to hide genuine errors.

## Nodes and materials

Blender node display names can be localized. Find nodes by type:

```python
principled = next(
    node for node in material.node_tree.nodes
    if node.type == "BSDF_PRINCIPLED"
)
```

Do not rely on `nodes["Principled BSDF"]`. With `material.use_nodes = True`, set render appearance on shader inputs; `material.diffuse_color` alone is only a viewport display color.

Give generated materials task-scoped names. Reuse and update owned materials instead of appending duplicates on each run. Preserve existing user-authored material slots unless the request explicitly replaces them.

## Geometry, scale, and transforms

- Adopt one unit convention, normally metres with `scene.unit_settings.system = 'METRIC'`, without changing an established scene convention casually.
- Build geometry at intended scale. Report assumptions when real dimensions were not supplied.
- Prefer explicit matrices or direct vertex coordinates over sequences of context-dependent transform operators.
- Decide whether scale/rotation should remain non-applied for procedural editing, rigs, or shape keys. Apply transforms only when the downstream deliverable requires it.
- Use sufficient curve and bevel resolution for the target output, but keep preview geometry economical.
- Recalculate normals, validate meshes, and inspect non-manifold boundaries when the deliverable requires watertight geometry.

## Performance and maintainability

- Use `foreach_set`, `mesh.from_pydata`, NumPy where available, or `bmesh` operations instead of per-element `bpy.ops` loops.
- Cache frequently used scene, collection, view-layer, and node references inside a stage.
- Remove temporary owned datablocks when finished and avoid orphan accumulation across reruns.
- Seed random generation explicitly and store important parameters near the top of the script.
- Emit compact summaries such as object counts, polygon counts, bounds, material names, and elapsed time. Avoid printing entire meshes or node graphs.

## Existing-scene edits

Snapshot the relevant object names, types, transforms, parent relationships, modifiers, materials, and collections before editing. Touch only the objects within the user's request. When a change could invalidate rigging, shape keys, simulations, linked data, library overrides, or existing animation, inspect those relationships first and preserve them unless replacement is explicitly requested.
