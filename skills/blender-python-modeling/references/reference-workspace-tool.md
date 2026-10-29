# Apply imported references to geometry

Use `scripts/reference_workspace.py` inside Blender for generic reference-driven
procedural builds. It supplies image-guide setup, live-state checks, pixel-to-world
landmark mapping and evidence checks. It does not interpret pixels, detect semantic
landmarks, generate screenshots or judge visual agreement automatically.

The existing character fitter already has calibrated pixel/profile construction
and render comparison. It may retain that path; do not replace its anatomy builders
or claim a headless worker produced human-reviewed viewport overlays. The generic
template formerly had no corresponding prerequisite; it now requires explicit
`reference`, `original`, or user-authorized `waived` mode.

## 1. Prepare the workspace before a geometry build

For multiple construction guides, first complete the [pre-model review](../../concept-multiview-sheet/references/pre-model-review.md). Add `"multiview_review": "multiview-review.json"` to the config. If its readiness is `partial`, add explicit `"build_regions": ["body"]` (use actual reviewed regions). `setup_references` checks source hashes, view roles and scope **before any guide mutation**. A supplemental/rejected view cannot silently become a guide, and blocked parent/child regions cannot enter the declared build. The record is declared inspection evidence, not automated pixel/anatomy judgment; the actual builder must honor those region names. A single ordinary guide does not require an artificial multiview receipt.

Keep a project-local `reference-setup.json`, with separate image paths and reviewed
pixel anchors. Example shape only; replace its coordinates with actual analysis:

```json
{
  "views": {
    "front": {
      "image": "front.png",
      "pixels_per_unit": 170,
      "origin_px": [50, 180],
      "origin_world": [0, 0, 0],
      "opacity": 0.4,
      "landmarks": {
        "body_center": [50, 95],
        "body_left": [10, 95],
        "body_right": [90, 95],
        "body_top": [50, 10],
        "body_bottom": [50, 180]
      }
    }
  }
}
```

Pixels start at image top-left, +X right and +Y down. `origin_px` identifies the
image pixel corresponding to `origin_world`; `pixels_per_unit` gives uniform
scale. With no real dimension, choose normalized units and label depth and hidden
geometry as inferred. A front landmark alone supplies a point in a plane, not
measured 3D depth. Add side/top constraints when they are trustworthy.

Blender view bases: front looks from -Y, back +Y, right +X, left -X, top +Z, bottom
-Z. Opposite views have the appropriate in-plane reversal. If an existing project
uses different axes, adapt a documented basis rather than silently mirroring it.

From a persistent setup script, with the requested scene active:

```python
import json, sys
from pathlib import Path
import bpy

sys.path.insert(0, "/absolute/skill/blender-python-modeling/scripts")
from reference_workspace import setup_references, workspace_signature

p = Path("/absolute/project/reference-setup.json")
setup_references(bpy.context.scene, "my-task", json.loads(p.read_text()), p.parent)
signature = workspace_signature(bpy.context.scene, "my-task")
```

This creates only task-owned Image Empties, aligned and calibrated, Depth Front,
default opacity .4, front-side/orthographic-axis visibility, transform/selection
locks, packed images. It reuses owned guides/images and refuses unowned collisions.
It does not move a guide arbitrarily toward the camera to obtain front draw order.

## 2. Inspect calibration, then open the build gate

Capture actual orthographic viewports with the references visible, inspect image
orientation, ground/origin, scale and anchors, and save captures to the project.
Record `calibration-review.json` only after inspection:

```json
{
  "workspace_signature": "signature returned for the actual scene",
  "phase": "calibration",
  "status": "passed",
  "views": {
    "front": {
      "artifact": "review/front-reference.png",
      "finding": "Record actual axis, scale and landmark observations here"
    }
  }
}
```

Record every configured guide view. Keep unreliable/contradictory panels out of
the controlling setup and preserve them as supplemental design evidence. A
perspective original is not a calibrated orthographic view merely because its
filename is front.png. Resolve material ambiguities with the existing evidence
policy; do not demand fabricated measurements for an artistic model.

The template checks this review **before removing prior generated geometry**.
Missing guides, wrong front/alpha/visibility settings, changed sources/transforms,
missing captures or a stale workspace signature stop the build. This verifies
state and declared evidence; it cannot certify the contents of a screenshot.

## 3. Use the imported guide's coordinates in the builder

Set the template's helper/config/review paths and `BUILD_MODE = "reference"`.
Use the mapping for actual model inputs, for example:

```python
from reference_workspace import reference_landmark
center = reference_landmark(scene, task, "front", "body_center")
left = reference_landmark(scene, task, "front", "body_left")
right = reference_landmark(scene, task, "front", "body_right")
width = (right - left).length
# Use center/width in mesh placement and dimensions, not just in a log.
```

The helper maps through the live Image Empty transform and records consumed
anchors in the scene. For curved outlines, sample reviewed profile anchors and
construct the appropriate surface; the sample cube is only a coordinate-use
example. Runtime usage records establish provenance, not artistic similarity or
proof that a caller honestly used a returned value. Parameters must remain
traceable to those values and the resulting shape must be compared.

## 4. Compare the model before final delivery

Build a blockout, inspect reference-visible axis overlays, and repair differences.
Save `comparison-review.json` using phase `comparison`, current workspace signature,
per-view capture/findings, `model_signature(objects)` and
`appearance_signature(scene, objects, extra=...)` for the actual model/presentation.
Both functions are exported by `reference_workspace`. Store external visual
dependencies under `appearance_extra` if used, and pass that same value to the
appearance signature. See [staged-execution.md](staged-execution.md) for scope.
Run `require_reference_review(scene, task, path, phase="comparison", objects=objects)`
before claiming a final reference-guided result. The template without this review
reports `blockout_pending_comparison`, not completion.

Changing model geometry/transforms/evaluated modifiers invalidates the comparison;
material/texture/attribute, light/world, camera and render changes invalidate its
appearance evidence even when geometry is identical. Old comparison receipts
without an appearance signature need inspection and renewal, not an automatic pass.
moving, hiding or replacing a guide invalidates calibration. New landmark readings
alone do not renew a visual pass. Supply the comparison artifact in feature/final
ledger review evidence; a valid ledger does not replace this Blender live-state
check. Images remain viewport guides, separate from normal final beauty renders.

The pre-model review text is retained in the scene for portable packed-file inspection. Source files and review artifacts must be present for a new setup/build; an existing packed scene can be inspected away from them. A changed available design receipt invalidates calibration. Old saved workspaces remain readable, but new multiple-guide setup requires the scoped design review.

For separate build/render calls, enable `BUILD_RECEIPT` in the task template and provide helper paths/actual stage inputs and saved outputs. A failed or interrupted new attempt cannot reuse an old successful receipt. Use [staged execution](staged-execution.md) instead of branching on a transport error flag alone.

## Executable checks

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python skills/blender-python-modeling/tests/blender_reference_workspace.py
```

The synthetic test checks six-axis mapping, Front/alpha settings, stable ownership,
template gates before deletion, actual anchor-derived dimensions, missing/stale
evidence and comparison invalidation after edits. Synthetic capture receipts test
the mechanism only; they are not real model overlays or artistic approval.
