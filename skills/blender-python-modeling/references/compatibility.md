# Blender Version Compatibility

## Support statement

- **Executed baseline:** Blender 4.5.12 LTS, Python 3.11.11 on macOS.
- **Other Blender 4.x builds:** supported by capability detection and API lookup, but not claimed as fully tested.
- **Blender 5.x:** do not assume examples from a 5.x reference work unchanged. Detect the feature and verify the result in that Blender build.

Run the bundled smoke test in a disposable session after changing recipes or when a different Blender build is installed:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup \
  --python scripts/validate_blender_compat.py
```

Adjust the executable and script paths for the host project. The test creates temporary datablocks, validates the APIs used by this skill, removes them, prints JSON, and exits non-zero on required failures.

## Prefer capabilities over version numbers

Backports and LTS releases make simple version assumptions unreliable. For example, Blender 4.5.12 already exposes `bpy.ops.pose.apply_to_basis`, although some Blender 5.1-oriented material describes it as new in 5.1.

Use this order:

1. Query `bpy_api_lookup` or `describe_node_type` through MCP.
2. Inspect RNA or use `hasattr` for properties/operators.
3. Create a throwaway node/modifier in a scratch datablock to prove its type exists.
4. Use `bpy.app.version` only when behavior genuinely changed at a documented boundary.

Never catch every exception and silently continue. A missing required capability should produce a clear error naming the Blender version and missing API.

## Blender 4.5.12 verified facts

The bundled smoke test verifies:

- BMesh cube creation and face-normal recalculation;
- mesh UV-layer creation, loop UV assignment, active render UV, and UV unwrap/pack RNA discovery;
- Mirror, Solidify, Bevel, Subdivision Surface, and Exact Boolean modifiers;
- 3D Bezier curves with bevel and fill caps;
- Principled BSDF discovery by node type and core PBR socket identifiers;
- Noise, Color Ramp, Image Texture, and Normal Map shader nodes;
- Geometry Nodes group interface via `node_group.interface.new_socket`;
- Mesh Cube, Set Position, Join Geometry, Curve Line, Curve to Mesh, and Instance on Points nodes;
- camera aiming with `to_track_quat`, Area lights, and object keyframes.
- export-operator RNA discovery for glTF/GLB, FBX, OBJ, and STL;
- a real one-triangle GLB export/import round trip with UV data.
- armature Edit Mode construction, normalized deform weights, and an Armature modifier;
- object asset marking, description, tags, and clearing;
- Render Layers, Denoise, Cryptomatte, File Output, and Composite nodes plus required view-layer passes;
- rigid-body creation, collision shape assignment, Cloth modifier creation, and point-cache access.

Observed runtime values include:

- EEVEE engine: `BLENDER_EEVEE_NEXT`;
- image formats: PNG, JPEG, OpenEXR, TIFF, HDR, WEBP, FFMPEG, and others reported by RNA;
- no AVIF in the tested build;
- `scene.eevee`, `mesh.remove_doubles`, `mesh.merge_by_distance`, and `pose.apply_to_basis` are present, but presence alone does not make them the preferred cross-version API.
- export operators are `export_scene.gltf`, `export_scene.fbx`, `wm.obj_export`, and `wm.stl_export`; discover their properties at runtime instead of copying settings from another Blender release.

## Known 5.x-only or unsafe-to-assume features

Do not use the following in a Blender 4.x-compatible script unless runtime lookup proves availability:

- For Each Element zones and Bundle nodes introduced in Blender 5.x;
- Blender 5.1 Bone Info, shader Raycast, Font sockets, newer volume-grid and UV nodes;
- AVIF output and HTJ2K OpenEXR codec;
- Blender 5.1 compositor Strip Info and Mask to SDF nodes;
- Blender 5.x-specific layered-action helpers or removed legacy conversion operators;
- node socket names copied from screenshots or English UI labels.

## Dynamic values

Treat these as runtime data:

- `scene.render.engine` identifiers;
- image/video formats and codec enums;
- render device backends such as CUDA, OptiX, HIP, Metal, or oneAPI;
- colour-management view transforms and looks;
- node type availability, socket identifiers, and socket order;
- operator parameters and modifier enum items.

Read RNA/API metadata first. For the dynamic render-engine enum, keep the valid current value or assign the desired engine inside `try/except TypeError` and report the accepted identifiers from the exception.
