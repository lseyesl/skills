# Clay girl fitting regression case

This is a separate version-1 character configuration, not a universal clay-person template. Reference images come from the project's AI-generated girl sheet. Front controls placement; side is slightly rotated/inconsistent and only guides assumed depth. Absolute physical units are unknown.

`character.json` separates shape, material, fixed render and validation/search controls. Object coordinates and hair guides are case data; generic code does not import the old output recipe. `references/annotations.json` points to visible-region masks. The masks were generated with localized case-specific HSV/color evidence and visually reviewed; confidence 0.75–0.8 is qualitative annotation reliability, not an automatic classifier probability. Version 2 removes an artificial head-crop boundary discovered during review. Covered torso remains `not_evaluable`.

`materials.*.color` stores observed reference-mask medians. Their source illumination is unknown. They are reproducible initial colors, not recovered intrinsic pigment. `hair` is locked in the example to demonstrate unrelated-component protection; that computational state does not mean the user has approved its shape or style. New subjects require their own masks, dimensions, flow guides and candidate ranges.

Run the repository-root commands in [the workflow](../../references/reference-fitting/workflow.md). Use a fresh output directory. `optimize` produces an initial snapshot, four rounds with bounded minus/plus candidates, selected-state logs and a final `.blend` with packed references. It can stop with unresolved parts; inspect the actual metrics and views.

The original three-expression model is preserved in the project's historical outputs. This new baseline fixture models the reference happy expression only; arbitrary expression generation/swap sets are not added to the fitter. No production armature is delivered: `--rig-test` skins and bends disposable copies as a smoke test.
