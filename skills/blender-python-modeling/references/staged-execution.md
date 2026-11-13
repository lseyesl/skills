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

## Scoped blockout prerequisite

Use blockout_gate.py with the existing stage_guard, rather than adding another general execution engine. Define module methods, objects, dependencies and checks in modeling-plan.json. Multiple semantic modules may share one continuous mesh; the default signature then conservatively tracks that whole mesh. Do not split a continuous surface merely to make the records independent.

Create a pending review using `make_review_draft(plan, scope, state_provider, dependencies)` before inspection. It records inspection_signature and unknown checks. Save it as a new review file; inspect the actual evidence before filling reviewer/findings/status. `record_blockout_review` refuses a passed document whose inspection_signature differs from the current plan/state/dependencies; it does not silently rebind old approval to changed geometry.

Call `require_blockout_review` before a refinement callback. The production template separates blockout/review/refine and includes the source review in `refinement_inputs()`, so later `require_stage(refinement_receipt, 'refine', refinement_inputs)` also checks source freshness. Keep coarse sources immutable and refine copies; changes to detailed copies alone do not invalidate the coarse gate. Modifying the coarse source during a failed refinement is detected, not automatically rolled back; recover from the preserved project snapshot and renew evidence.

Use a separate receipt per scope. depends_on extends the state to necessary neighboring modules; changing an independent module does not require unrelated review. The default recipe dependency is the whole project script, which is conservative. Separate coarse recipe files and declare all relevant BLOCKOUT_INPUT_FILES/parameters for narrower invalidation; do not omit real dependencies to make stale evidence pass. Use --stage or a runtime setting to switch phases, not file edits that alter the recipe hash.

Reviewers can be the inspecting Agent or a human. No blanket user approval is introduced. The gate verifies declared inspection, scope and freshness, not artistic judgment. For context-sensitive inspections, include relevant cameras, occluders, external caches and scene settings in project dependencies; the default source signature alone cannot discover all of them.
