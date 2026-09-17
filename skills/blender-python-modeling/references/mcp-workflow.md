# Local Blender MCP Workflow

This skill targets the installed `ahujasid/mcp-for-blender` tool namespace. Tool availability is runtime-dependent; use only tools actually exposed in the current session.

## Required order

1. `mcp__blender__get_addon_status` — confirm the add-on connection, server/add-on compatibility, and `blender_version`.
2. `mcp__blender__get_scene_info` — inventory the current scene before any mutation.
3. `mcp__blender__get_object_info` — inspect each existing object that will be edited or used as a reference.
4. `mcp__blender__bpy_api_lookup` or `mcp__blender__describe_node_type` — resolve uncertain API signatures, enums, node properties, and socket layouts.
5. `mcp__blender__execute_blender_code` — run a small probe, a persistent script bootstrap, or one bounded build stage.
6. `mcp__blender__get_scene_info` plus targeted `get_object_info` — confirm structural results.
7. `mcp__blender__get_viewport_screenshot` — inspect the visible result; repeat after fixes.
8. `mcp__blender__export_scene` — export GLB/FBX when requested, then verify the returned path, byte size, and exported objects.

On every tool call, copy the user's latest Blender request exactly into `user_prompt`. Keep the same text across a multi-call operation unless the user changes the request.

## Execute persistent scripts

Prefer a checked-in or otherwise saved Python source file. `execute_blender_code` should normally receive only a loader:

```python
from pathlib import Path

p = Path(r"/absolute/path/to/script.py")
ns = {"__name__": "__main__", "__file__": str(p)}
exec(compile(p.read_text(encoding="utf-8"), str(p), "exec"), ns)
```

Use an absolute path and quote it safely. The script owns all substantive logic so the result can be reproduced after Blender restarts.

## Stage large builds

Separate expensive or failure-prone work into bounded stages such as:

1. generated collection and base geometry;
2. modifiers and topology cleanup;
3. UVs, materials, and textures;
4. scene assembly, lights, and camera;
5. animation or simulation setup;
6. rendering and export.

Each stage should be idempotent and retrieve existing data by stable names or task owner properties. Do not assume variables from a previous MCP call still exist. Return a short machine-readable summary with names, counts, dimensions, and warnings rather than printing huge vertex arrays.

## Connection and execution failures

- **Blender unreachable:** ask the user to open Blender and start the Blender MCP add-on. A code-only deliverable can still be completed and clearly labeled unexecuted.
- **Add-on/server mismatch:** relay the update instruction returned by `get_addon_status`; do not guess installation paths.
- **Timeout:** split the work into smaller stages, reduce preview resolution, or move heavy loops into the persistent script. Do not resend the identical large call.
- **Context or poll failure:** inspect mode, active object, selection, area and region. Prefer a direct data API or a narrow `bpy.context.temp_override`.
- **API or enum error:** query `bpy_api_lookup`; do not trial-and-error several guessed spellings.
- **Node/socket error:** query `describe_node_type` with the intended property overrides before rewriting node code.

## Optional asset services

The MCP may expose Poly Haven, Poly Pizza, Sketchfab, Hyper3D, or Hunyuan3D tools. They are optional sources, not the default modeling route. Use them only when the request calls for external/generated assets or they materially improve the requested result. Preserve licence/attribution metadata and get user approval before invoking a paid or metered generation service.
