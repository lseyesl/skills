# Materials and Node Recipes

## Stable node access

Find nodes by `node.type`, not translated display names. Find sockets by runtime identifier and fail with the available identifiers when the expected socket is absent:

```python
def socket_by_identifier(node, *identifiers):
    wanted = set(identifiers)
    for socket in node.inputs:
        if socket.identifier in wanted:
            return socket
    available = [socket.identifier for socket in node.inputs]
    raise KeyError(f"missing {sorted(wanted)}; available={available}")

material.use_nodes = True
principled = next(
    node for node in material.node_tree.nodes
    if node.type == "BSDF_PRINCIPLED"
)
socket_by_identifier(principled, "Base Color").default_value = (0.2, 0.4, 0.8, 1)
socket_by_identifier(principled, "Metallic").default_value = 0.0
socket_by_identifier(principled, "Roughness").default_value = 0.35
```

The verified Blender 4.5 Principled identifiers include `Base Color`, `Metallic`, `Roughness`, `IOR`, `Alpha`, `Normal`, `Transmission Weight`, `Emission Color`, and `Emission Strength`. Do not assume those exact identifiers on another build; call `describe_node_type` first.

## Material choices

| Surface | Principled starting point |
|---|---|
| Matte plastic | Metallic 0, Roughness 0.35–0.6 |
| Painted metal | Metallic 0 for the paint, Roughness 0.2–0.5; expose metal only where paint is removed |
| Bare metal | Metallic 1, Roughness 0.08–0.45 |
| Clear glass | Transmission Weight 1, IOR about 1.45, low Roughness |
| Frosted glass | Transmission Weight 1, IOR about 1.45, Roughness 0.2–0.6 |
| Rubber | Metallic 0, Roughness 0.65–0.9, dark but not zero Base Color |
| Emissive sign | Emission Color plus physically plausible Emission Strength; verify in render |

Treat these as starting ranges, not universal constants. Scale, lighting, exposure, and render engine change the appearance.

## Texture-based PBR

Use this map routing:

- Base Color: sRGB image → Principled Base Color;
- Roughness/Metallic: Non-Color image → corresponding scalar input;
- Normal: Non-Color image → Normal Map node → Principled Normal;
- Height: Non-Color image → Bump for a cheap surface effect, or Displacement for true Cycles displacement when supported.

Load each image once with `check_existing=True`. Confirm the installed colour-space identifiers before assignment if a nonstandard OCIO configuration is possible.

For GLB, favor Principled-compatible nodes and conventional image maps. Complex procedural trees often need baking before they transfer faithfully.

## Procedural materials

Common Blender 4.x-compatible patterns:

- Noise Texture → Color Ramp → Base Color for stone, paint variation, clouds;
- Noise/Voronoi → Bump → Normal for fine surface relief;
- Wave Texture plus Noise distortion for wood-like bands;
- Geometry/Object coordinates → Mapping → textures for controllable scale;
- Layer Weight or Fresnel for angle-dependent coating effects.

Use `describe_node_type` before wiring an unfamiliar node. Socket layouts can change with node properties such as data type, and shared nodes like Mix have version-sensitive layouts.

## Geometry Nodes baseline

The tested Blender 4.5 baseline includes Mesh Cube, Set Position, Join Geometry, Curve Line, Curve to Mesh, and Instance on Points. Create group sockets using the Blender 4.x interface API:

```python
group = bpy.data.node_groups.new("GN_task_scatter", "GeometryNodeTree")
group.interface.new_socket(
    name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
)
group.interface.new_socket(
    name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
)
group_in = group.nodes.new("NodeGroupInput")
group_out = group.nodes.new("NodeGroupOutput")
geometry_out = next(s for s in group_in.outputs if s.type == "GEOMETRY")
geometry_in = next(s for s in group_out.inputs if s.type == "GEOMETRY")
group.links.new(geometry_out, geometry_in)
modifier = obj.modifiers.new("GN_task", "NODES")
modifier.node_group = group
```

Useful patterns:

- Scatter: Distribute Points on Faces → Instance on Points; randomize rotation and scale, realize late.
- Deform: Position/Normal plus Noise → vector math → Set Position Offset.
- Cable/profile: Curve Line or input curve → Curve to Mesh with a Curve Circle profile.
- Conditional branches: Separate Geometry → process branches → Join Geometry.

Do not infer node identifiers from labels. Blender 5.x For Each Element, Bundle, Bone Info, Raycast, new UV/volume-grid nodes, and Font sockets are not part of the 4.x baseline.

## Node-tree quality

- Give nodes stable names and readable labels, but retrieve them by stored references or `bl_idname`/`type`.
- Place nodes left-to-right with consistent spacing so a human can inspect the graph.
- Use Frame nodes for logical sections in complex graphs.
- Expose only parameters users need to tune; keep implementation details internal.
- Reuse task-owned materials and node groups on rerun rather than creating `.001` duplicates.
- Validate both the node topology and a rendered/viewport result.
