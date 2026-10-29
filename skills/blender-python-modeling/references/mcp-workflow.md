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

Use the [guarded project stages](staged-execution.md) and `scripts/stage_guard.py` when build/verify/render span separate tool calls. A new attempt invalidates prior success before work. Inspect tool result text as well as `isError`: a returned `Error executing code`/traceback/communication error must stop dependent rendering even when the transport flag says false. Require the current predecessor receipt and artifact hashes; do not reuse a stale `.blend` or scene success flag after a failed attempt.

Separate expensive or failure-prone work into bounded stages such as:

1. generated collection and base geometry;
2. modifiers and topology cleanup;
3. UVs, materials, and textures;
4. scene assembly, lights, and camera;
5. animation or simulation setup;
6. rendering and export.

Each stage should be idempotent and retrieve existing data by stable names or task owner properties. Do not assume variables from a previous MCP call still exist. Return a short machine-readable summary with names, counts, dimensions, and warnings rather than printing huge vertex arrays.

## Connection and execution failures

- **Blender unreachable:** follow the recovery sequence below before asking the user to launch Blender manually. An exposed MCP tool only proves that the bridge is available, not that Blender or its add-on service is running.
- **Add-on/server mismatch:** relay the update instruction returned by `get_addon_status`; do not guess installation paths.
- **Timeout:** split the work into smaller stages, reduce preview resolution, or move heavy loops into the persistent script. Do not resend the identical large call.
- **Context or poll failure:** inspect mode, active object, selection, area and region. Prefer a direct data API or a narrow `bpy.context.temp_override`.
- **API or enum error:** query `bpy_api_lookup`; do not trial-and-error several guessed spellings.
- **Node/socket error:** query `describe_node_type` with the intended property overrides before rewriting node code.

### Recover an unreachable Blender

1. Check for the actual Blender application process. On macOS, `pgrep -fl Blender` can help, but a thumbnail extension or an `mcp-for-blender` bridge process does not count. If process inspection is denied by the sandbox, request execution approval; do not interpret the denial as proof that Blender is closed.
2. If Blender is absent and the task needs a live session, launch the installed application once. On macOS, use `open -a /Applications/Blender.app` when that path exists; otherwise locate the installed app first. Follow the environment's approval requirements. Launch Blender in normal UI mode; its window may stay in the background or minimized while MCP is used. Do not use `blender --background` or `blender -b` headless mode for MCP connection recovery: this add-on's auto-start callback skips that mode, and viewport tools need a UI context. Do not install or reconfigure Blender as part of connection recovery.
3. Allow startup to finish, then retry `get_addon_status` up to three times, roughly five seconds apart. If the add-on is enabled and auto-start is configured, no manual Start button should be needed. A connection reset immediately after a known add-on reload can also warrant this bounded retry. Once status succeeds, call `get_scene_info` before continuing the task.
4. If Blender is already running or the retries fail, inspect whether the MCP add-on is enabled and its service started, whether the configured host/port match, and whether another Blender instance owns the port. Check version compatibility once reachable. Preserve any existing auto-start setting. Do not launch duplicate instances, kill/restart a running Blender, or update/reinstall the add-on merely to retry a connection; those actions can affect current work or configuration and require appropriate task scope.
5. If recovery still fails, report the observed error and the specific remaining check. Ask the user to enable/start the add-on only when it cannot be done with available authorized tools. A code-only deliverable can still be completed when appropriate and clearly labeled unexecuted. Never claim connection success without a successful MCP response.

## Optional asset services

The MCP may expose Poly Haven, Poly Pizza, Sketchfab, Hyper3D, or Hunyuan3D tools. They are optional sources, not the default modeling route. Use them only when the request calls for external/generated assets or they materially improve the requested result. Preserve licence/attribution metadata and get user approval before invoking a paid or metered generation service.
