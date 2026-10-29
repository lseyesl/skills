# Fail-closed stages and selective rendering

Use a project-local entry point for work split across build, rig, verify, save and render calls. Reuse the existing fitter/worker when it already supplies equivalent checks; do not create a second orchestration system for a one-step edit.

## Never infer success from transport status

MCP can return `isError: false` while its text reports `Error executing code`, a traceback or a communication failure. Inspect the actual result and require a fresh project stage receipt before dependent work. Clear old success markers before each attempt; a pre-existing file or `build_ok=True` from yesterday cannot authorize rendering a failed rebuild.

`scripts/stage_guard.py` provides standard-library helpers. In the project entry point, use one writer per receipt path:

```python
from stage_guard import file_input, run_stage, require_stage

# Resolve inputs inside run_stage so missing files also invalidate prior success.
def build_inputs():
    return {"recipe": file_input(script_path), "references": file_input(reference_config),
            "parameters": actual_model_parameters}

result = run_stage(build_receipt, "build", build_inputs, [saved_blend],
                   work=build_and_save,
                   validate=validate_build_result)  # must return True or raise
# The current attempt, input fingerprint and artifact hashes must still agree.
receipt = require_stage(build_receipt, "build", build_inputs)
run_stage(render_receipt, "render", {"build_run": receipt["run_id"],
          "blend": file_input(saved_blend), "views": affected_views,
          "render_config": actual_render_parameters}, expected_images,
          work=render_affected_views, validate=validate_render_outputs)
```

Callbacks above are project implementations, not bundled geometry/render functions. Do not catch a stage exception and continue dependent steps. A failed attempt records `failed`; an interrupted `running` receipt cannot pass. Include all actual dependencies in fingerprints: recipe/helper/config/source hashes, parameters, rig version, render settings and predecessor attempt. `BUILD_RECEIPT` in the task template enables the same build guard; set `BUILD_OUTPUTS` when its project builder saves files. A live-only receipt with no file outputs certifies that stage's checks, not subsequent scene freshness; compare current geometry/appearance signatures before using it across calls.

Record stage elapsed wall time (including failures) separately from generation calls, user waiting and total task duration. Report totals only when measured. Stage receipts establish execution and artifact freshness, not artistic or animation approval.

## Spend rendering effort where evidence changed

- Before full delivery views, review one representative local sample in intended materials/light. Resolve head/muzzle/joint shape and signature relief before whole-scene polish.
- After a local edit, rerender the affected crop and controlling views first; retain unchanged artifacts with provenance. Run the final common-scale multi-view sheet once the local checks pass.
- Make the affected-view decision explicit. Head/pose/geometry changes affect relevant silhouettes; global palette, lighting, exposure or shared shader changes can affect every view. Do not skip a necessary rerender merely because only one parameter changed.
- Check back/top/bottom early when projected regions can leak: ear fronts versus backs, throat/chest versus belly, paw tops versus soles, tail root versus tip.
- Avoid regenerating an entire image sheet to repair a single view or to add line art. Preserve accepted source panels; a model-backed orthographic/contour sheet is preferable once a reviewed blockout exists.

## Fresh visual comparisons

Keep geometry, appearance, and animation acceptance separate. `model_signature(objects)` tracks evaluated shape/transforms. `appearance_signature(scene, objects, extra=...)` additionally fingerprints materials and nested node groups, texture content/bindings, UV/custom attributes, other rendered geometry, lights/world, cameras, render/colour settings and compositor nodes. A comparison receipt needs both signatures. Changing either invalidates its prior visual findings even when the file still opens.

The built-in fingerprint is not a complete dependency scanner for external movies/UDIM tiles, simulation caches, custom render engines, sequence-editor content, viewport shading/environment overrides or every add-on node. Include those dependencies in `appearance_extra` and stage inputs, and inspect the rendered result. For externally animated/unstable inputs, capture the exact frames/caches used by the review. Old comparison JSON without an appearance signature must be inspected and renewed, not mechanically backfilled as passed.

After a change, preserve unrelated evidence and renew affected comparisons. Calibration/reference-design approval never substitutes for mesh fidelity; finite coordinates and weight sums never substitute for visible deformation/contact checks.
