# Modeling Recipes

## Choose the representation first

| Shape or requirement | Preferred construction |
|---|---|
| Mechanical, architectural, dimension-driven | primitives/BMesh plus live modifiers |
| Tubes, cables, rails, outlines, paths | curves with bevel or Curve to Mesh |
| Repeated parts | linked meshes, collection instances, Array, or Geometry Nodes |
| Terrain and patterned surfaces | Geometry Nodes or displaced mesh |
| Soft/organic silhouette | low-resolution base mesh plus Subdivision; sculpt only when needed |
| Watertight print part | explicit manifold mesh, booleans with cleanup, measured thickness |

Block out primary proportions before details. Name major parts separately when they need distinct pivots, materials, export behavior, or replacement. Use one real-world unit convention and keep user-editable parameters at the top of the script.

## Direct mesh construction

Use `mesh.from_pydata` for known topology and BMesh for procedural editing:

```python
mesh = bpy.data.meshes.new("MESH_task_panel")
mesh.from_pydata(
    [(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)],
    [],
    [(0, 1, 2, 3)],
)
mesh.validate(verbose=True)
mesh.update()
obj = bpy.data.objects.new("GEO_task_panel", mesh)
collection.objects.link(obj)
```

```python
mesh = bpy.data.meshes.new("MESH_task_body")
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bmesh.ops.bevel(
    bm,
    geom=list(bm.edges),
    offset=0.08,
    segments=3,
    affect="EDGES",
)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh)
bm.free()
mesh.validate(verbose=True)
mesh.update()
```

Check uncertain BMesh arguments with `bpy_api_lookup` or Blender's Python API for the running version; they are not RNA operators and may require direct documentation lookup.

## Curves for linear forms

Use curves for wires, pipes, handles, trims, roads, and profile sweeps. Keep them procedural until mesh-only operations or export require conversion.

```python
curve = bpy.data.curves.new("CURVE_task_rail", "CURVE")
curve.dimensions = "3D"
curve.resolution_u = 12
curve.bevel_depth = 0.015
curve.bevel_resolution = 3
curve.use_fill_caps = True
spline = curve.splines.new("BEZIER")
points = [(-1, 0, 0), (0, 0.4, 0.5), (1, 0, 0)]
spline.bezier_points.add(len(points) - 1)
for point, co in zip(spline.bezier_points, points, strict=True):
    point.co = co
    point.handle_left_type = "AUTO"
    point.handle_right_type = "AUTO"
```

Use `AUTO` for smooth organic paths, `ALIGNED` for controlled tangency, and `VECTOR` for corners. Choose bevel resolution from the output target rather than maximizing it.

## Hard-surface modifier stacks

A common non-destructive order is:

1. Mirror for symmetry;
2. Array for repetition;
3. Boolean for major cuts/unions;
4. Solidify when a surface needs thickness;
5. Bevel for manufactured edges;
6. Subdivision only when the form needs continuous smoothing.

Order is part of the design. Boolean-before-Bevel usually produces cleaner manufactured edges than Bevel-before-Boolean. Mirror-before-Boolean makes cutters affect both sides; reversing them can be useful when asymmetry is intended.

```python
mirror = obj.modifiers.new("MOD_task_mirror", "MIRROR")
mirror.use_axis = (True, False, False)
mirror.use_clip = True

boolean = obj.modifiers.new("MOD_task_cut", "BOOLEAN")
boolean.operation = "DIFFERENCE"
boolean.solver = "EXACT"
boolean.object = cutter

bevel = obj.modifiers.new("MOD_task_bevel", "BEVEL")
bevel.width = 0.01
bevel.segments = 3

for polygon in obj.data.polygons:
    polygon.use_smooth = True
```

Keep cutters in a task-owned collection and hide them only after visual validation. Do not apply modifiers merely to make the viewport tidy. Apply or bake only when the next operation or output requires evaluated geometry.

## Organic and sculptable forms

For script-generated organic objects:

1. create a low-resolution, evenly distributed base mesh;
2. establish symmetry and silhouette;
3. add Subdivision or Multiresolution at conservative preview levels;
4. keep eyes, teeth, accessories, and rigid parts separate;
5. sculpt manually only after the procedural base and scale are accepted.

Avoid scripting detailed sculpt strokes as a default: they are context-sensitive, hard to reproduce, and difficult to validate. For procedural organic variation, use controlled displacement or Geometry Nodes with an explicit random seed.

## Topology and cleanup

For an evaluated BMesh:

```python
bm = bmesh.new()
bm.from_mesh(mesh)
bm.normal_update()
loose_verts = [v for v in bm.verts if not v.link_edges]
boundary_or_nonmanifold = [e for e in bm.edges if not e.is_manifold]
degenerate_faces = [f for f in bm.faces if f.calc_area() <= 1e-12]
bm.free()
```

Interpret non-manifold edges according to the target: they are invalid for a closed print solid but expected on an open sheet. Merge-by-distance and hole filling are corrective operations, not automatic defaults; they can destroy deliberate seams and openings.

Use direct mesh edits or BMesh operations for cleanup. If an operator is unavoidable, prefer `bpy.ops.mesh.merge_by_distance` after API lookup; do not rely on the older `remove_doubles` alias across versions.

## Repetition and instances

- Use linked duplicates when many objects share one editable mesh.
- Use Array for linear or radial repetition that belongs to one object.
- Use collection instances for repeated assemblies.
- Use Geometry Nodes for attribute-driven scattering and large counts.

Keep instances unrealized until downstream mesh operations or export require real geometry. Record expected instance and evaluated triangle counts so a rerun cannot silently explode scene complexity.
