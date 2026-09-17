# Export and Asset Packaging

Export is a reproducible build stage. Preserve the editable source scene and prepare a task-owned delivery copy when transforms, modifiers, triangulation, baked animation, or texture relinking must become destructive.

## Define the delivery contract

Before export, record:

- destination application and format;
- absolute output path and overwrite permission;
- selected objects or collection;
- unit scale, forward/up axes, origin and pivot convention;
- modifier, instance, curve, Geometry Nodes, and triangulation policy;
- materials, texture embedding/copying, UV sets, vertex colours, normals and tangents;
- armature, shape-key, animation clip, FPS and frame-range requirements;
- polygon, material, texture, bone, influence, LOD and collision budgets.

Do not infer engine conventions from a filename alone. Unity, Unreal, web glTF, slicers, and CAD-adjacent tools have different axis, scale, animation, material, and naming expectations.

## Choose the format

| Format | Use for | Important limits |
|---|---|---|
| GLB/glTF | web, real-time PBR, portable static/animated assets | constrained material model; bake unsupported procedural nodes |
| FBX | DCC/game-engine exchange, especially rigs and clips | axis, leaf-bone, NLA/action and scale settings need target tests |
| OBJ | simple static mesh exchange | limited hierarchy/animation/material behavior |
| STL | 3D-print geometry | no reliable unit metadata, materials, hierarchy, UVs, or animation |
| `.blend` | editable Blender source or reusable asset | downstream Blender version and external-file paths matter |

Use `mcp__blender__export_scene` for GLB/FBX when it exposes every required option. Otherwise run a persistent `bpy` export function through MCP. Do not switch mechanisms midway without recording the effective settings.

## Discover operators and parameters

Operator names and keyword sets differ across Blender releases and enabled extensions. Blender 4.5.12 exposes `bpy.ops.export_scene.gltf`, `bpy.ops.export_scene.fbx`, `bpy.ops.wm.obj_export`, and `bpy.ops.wm.stl_export`; older examples using `export_mesh.stl` or `export_scene.obj` may not apply.

Resolve and filter explicitly:

```python
def resolve_operator(path):
    namespace, name = path.split(".", 1)
    operator = getattr(getattr(bpy.ops, namespace), name)
    try:
        operator.get_rna_type()
    except KeyError as exc:
        raise RuntimeError(f"export operator unavailable: bpy.ops.{path}") from exc
    return operator


def call_supported(operator, **requested):
    allowed = set(operator.get_rna_type().properties.keys())
    unknown = sorted(set(requested) - allowed)
    if unknown:
        raise RuntimeError(f"unsupported export options: {unknown}; allowed={sorted(allowed)}")
    return operator(**requested)
```

Failing on unsupported options is safer than silently dropping a setting that changes scale, material, or animation output. Use MCP `bpy_api_lookup` first when available.

## Stable selection and export examples

Before a selection-limited export, enter Object Mode, deselect everything, select the exact task-owned objects, set a meaningful active object, and verify the selected-name set. Restore the user's selection afterwards when practical.

Minimal Blender 4.5-compatible GLB call:

```python
call_supported(
    resolve_operator("export_scene.gltf"),
    filepath=str(output_path),
    export_format="GLB",
    use_selection=True,
    export_apply=False,
    export_texcoords=True,
    export_normals=True,
    export_tangents=True,
    export_materials="EXPORT",
    export_animations=True,
    export_yup=True,
    check_existing=True,
)
```

Enable tangents only when the mesh has a valid UV map and the target needs tangent-space normals. Choose `export_apply` only after testing rigs, shape keys, instances, and Geometry Nodes evaluation.

Typical FBX settings include `use_selection=True`, `axis_forward="-Z"`, `axis_up="Y"`, `apply_unit_scale=True`, `use_mesh_modifiers=True`, and explicit animation/NLA options. These are common starting values, not a universal engine preset. OBJ uses `wm.obj_export` with `export_selected_objects`; STL uses `wm.stl_export` with `export_selected_objects` and optionally `use_scene_unit`. Inspect runtime RNA before passing them.

## Prepare delivery geometry

Keep authoring objects intact. In a separate task-owned export collection when needed:

- convert curves/text only if the target cannot consume them;
- realize instances only when required and record the resulting triangle count;
- evaluate Geometry Nodes and modifiers deliberately;
- triangulate at a known stage so baked tangent normals and exported topology agree;
- apply transforms only when required by the target contract;
- remove hidden helpers, cutters, cameras, lights, and preview-only data unless requested;
- validate normals, material slots, UV layers, vertex colours, origins and bounds.

For game assets, include target-specific LOD and collision conventions in the contract. Generate LODs from an approved source, preserve silhouette and UV/material compatibility, and validate each evaluated triangle count. Collision meshes should be simple, closed where required, correctly named for the destination, and excluded from render geometry unless the target expects otherwise.

## Textures and external files

Choose one packaging mode and report it:

- GLB: embed supported images in the binary when requested;
- glTF separate: keep `.gltf`, `.bin`, and texture paths together and portable;
- FBX: copy or embed textures only if the consumer supports the chosen mode;
- `.blend`: make paths relative or explicitly pack resources, without mutating the user's source file unexpectedly.

Check `bpy.data.images` for missing files, generated/dirty images, packed state, colour space, dimensions, and duplicate logical textures. Save generated or baked images before export. Do not assume `bpy.ops.file.pack_all()` saves dirty images or makes unsupported procedural materials portable.

Emit a small delivery manifest beside complex assets when useful: source Blender version, format, effective export options, axes/units, object names, evaluated triangle counts, materials, textures, animations, LODs, collisions, and known limitations.

For game-ready naming, texture suffixes, packed-channel conventions, LODs, collisions and evaluated budgets, apply [game-assets.md](game-assets.md). For deform rigs, skin influences, shape keys and root motion, apply [character-delivery.md](character-delivery.md).

## Save `.blend` safely

Never overwrite the user's source file unless explicitly requested. Resolve the absolute path, verify the parent directory, and use Save As or Save Copy semantics appropriate to the task. After saving, confirm `bpy.data.filepath` only when the operation was intended to change the live document path, and verify the output exists with non-zero size.

## Round-trip validation

File existence is only the first check. Validate high-risk exports in a disposable blank scene or the actual consumer:

1. record source object hierarchy, transforms, bounds, evaluated triangle counts, materials, UV layers, armature/bone counts, shape keys, animation ranges and texture paths;
2. export to a new absolute path;
3. confirm the exporter result, file extension and non-zero byte size;
4. import into an isolated scene or open in the destination viewer/engine;
5. compare scale, axes, hierarchy, pivots, shading, UVs, textures, animations, LODs and collisions;
6. capture a screenshot or render and report deviations.

Never round-trip into the user's working scene. Import operator names are version-sensitive just like export operators; discover their RNA at runtime.

## Export acceptance checks

- Only intended objects were exported.
- World-space bounds, units, axes, origins and pivots match the contract.
- Evaluated geometry and triangle counts are within budget.
- Normals, tangents, UV sets, material assignments and alpha modes survive.
- Textures resolve on another machine or in the destination package.
- Armature hierarchy, bone axes, skin weights, shape keys and clips survive when applicable.
- The source scene remains editable and unchanged outside the task-owned export stage.
- Export path, byte size, effective settings, Blender version and downstream test result are reported.
