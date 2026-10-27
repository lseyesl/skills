# Minimal usage and cross-project application

## Standalone smoke scene

From this repository root:

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python skills/blender-styles/scripts/build_demo.py -- \
  --config skills/blender-styles/styles/soft-clay/examples/preview.json \
  --output .tmp/clay-example --render still
```

The example contains an abstract multipart bob/tilt model, large floor, rounded block, tapered cone, pebble, five clay colors, area lights, camera and a duplicate loop endpoint outside the output range. It creates a new scene and leaves other scenes/data intact. The geometry is a validation fixture, not a required project style or naming convention.

Use `examples/portrait.json` for a portrait EEVEE preview. `build_demo.py --render animation` outputs a sequence (or native video if the profile sets `format="FFMPEG"`). Change output directories between experiments; `--overwrite` explicitly opts into replacement.

## Existing project recipe

The tools are importable functions as well as CLI scripts. Use one persistent project script for dependent setup steps so unsaved changes are not lost between Blender processes:

```python
from pathlib import Path
import json
import sys
import bpy

# Supply the installed Skill's scripts location; no project-specific path is in the Skill.
tool_dir = Path("/absolute/installed/blender-styles/scripts")
sys.path.insert(0, str(tool_dir))
from clay_common import merge_config, save_new
from create_clay_material import create_palette
from setup_clay_lighting import setup_lighting
from setup_render import setup_render
from validate_clay_scene import validate_scene

scene = bpy.context.scene
profile = merge_config(json.loads(Path("/absolute/project/style.json").read_text()))
palette = create_palette(scene, profile, owner="project-style")
targets = [scene.objects[name] for name in authorized_mesh_names]
for obj in targets:
    # Choose a specific authorized slot; clone shared mesh data first if needed.
    obj.data.materials[authorized_slot_for(obj)] = palette[palette_key_for(obj)]
setup_lighting(scene, profile, owner="project-style", with_camera=False)
setup_render(scene, profile, output="/absolute/output/frame-")
report = validate_scene(scene, profile, owner="project-style", objects=targets)
if not report["structural_ok"]:
    raise RuntimeError(report["errors"])
save_new("/absolute/output/styled.blend")
```

`authorized_mesh_names`, slot/color mappings and geometry are project inputs. Do not implement them by applying the style to all objects indiscriminately. Existing material slots and shared mesh data are the caller's responsibility. `merge_config` validates the full merged profile before edits.

For animation call `setup_animation(obj, scene, profile, owner)` on explicitly chosen unconstrained targets after inserting keys. For authored rigs with constraints/NLA, use a render duplicate with evaluated baked motion; do not remove production rig controls just to satisfy this helper.

## Individual CLI stages

All stages accept `--config`, `--scene`, `--owner` after Blender's `--`. They only change in-memory data unless saving is requested:

```bash
blender --background /absolute/project/source.blend --python-exit-code 1 \
  --python skills/blender-styles/scripts/create_clay_material.py -- \
  --config /absolute/project/style.json --owner project-style
```

This checks material creation but does not persist it. To combine CLI stages, either run one wrapper script as above or use ordered Blender `--python` invocations **without per-script CLI arguments**, then save via the last stage/project recipe. Per-stage `--` arguments are shared by every script in a Blender process, so do not combine differing parsers that way.

`setup_render.py --save /absolute/output/styled.blend` saves a configured copy. `setup_render.py --output /absolute/output/preview.png --render still` renders explicitly. `setup_clay_lighting.py --keep-camera` preserves the active camera. `setup_clay_animation.py --objects NAME ...` never guesses animated targets.

## Local repeatable test suite

```bash
blender --background --factory-startup -t 2 --python-exit-code 1 \
  --python skills/blender-styles/scripts/test_soft_clay.py -- \
  --output .tmp/clay-tests --render
```

Remove `--render` for fast structural tests. The suite creates disposable new scenes, tests both renderers, portrait/landscape overrides, reruns, ownership preservation, timing, bad inputs and negative QA cases. It uses CPU Cycles, leaves hardware preferences unchanged and writes a machine-readable report. Run only in a disposable process, not over a production open scene. See the recorded [test results](test-results.md) for what actually executed.
