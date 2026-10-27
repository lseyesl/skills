# Executable reference-fitting workflow (Phase 0–4)

Use when the task needs repeated reference evaluation and parameter-level local changes. Ordinary non-character modeling can keep using existing scripts. Existing scene/ledger/three-expression workflows are retained; the new character example supplies the reference happy face only.

## Environment and reproducible commands

Validated: Blender **4.5.12 LTS**, host Python via this skill's existing uv project, NumPy/OpenCV. No Python packages are installed into Blender. Other 4.x/5.x versions require runtime capabilities; other versions fail before mutation. CPU Cycles is the demonstrated fitter engine; the existing soft-clay tool also has EEVEE integration coverage.

From repository root:

```bash
# Inspect supplied masks, annotation reliability and observed source colors.
uv run --project skills/blender-python-modeling python \
  skills/blender-python-modeling/scripts/fit_character.py analyze \
  --config skills/blender-python-modeling/examples/clay-girl-fit/character.json \
  --output output/my-fit-analysis

# One-command reproducible full case; output directory must be empty.
uv run --project skills/blender-python-modeling python \
  skills/blender-python-modeling/scripts/fit_character.py optimize \
  --config skills/blender-python-modeling/examples/clay-girl-fit/character.json \
  --output output/my-fit-run --rig-test \
  --blender /Applications/Blender.app/Contents/MacOS/Blender
```

`build` creates one model/render/measurement; `render --source accepted.blend` validates matching geometry/material config and refreshes reference calibration plus render outputs without rebuilding geometry; `evaluate` remeasures an existing render directory; `baseline --source existing.blend` applies the example's configurable legacy object-to-label mapping in a disposable process. `optimize --source accepted/scene.blend --config accepted/config.json` resumes an existing owned configuration, requiring shape/material identity. Baseline/source files are never overwritten. Every run retains its Blender log and a worker timeout (default 600 seconds). Existing output directories are rejected instead of overwriting review evidence.

See [architecture.md](architecture.md) for the audited reuse decisions and module boundaries. This is an additive system; no old API migration is required.

## Phase 0: freeze evidence

Retain the original editable source, reference crop, camera/engine/color transform, configuration and source hash. Use original unstitched images rather than extracting masks from a three-column comparison. Establish normalized height units; absolute units remain unknown. Record source visibility, AI inconsistency and all inferred depths.

## Phase 1: semantic evidence and repeatable measurement

`reference.image` is source RGBA (preferred); `reference.annotation` has version 1, exact `image_size`, and explicit component `mask` paths or `polygon` pixel arrays. Each annotation needs provenance and qualitative `confidence` >= 0.7 before measurement. Low-confidence/covered parts are `not_evaluable`; mask absence is an error. These values describe annotation reliability, not calibrated model probabilities. There is no universal reliable automatic semantic segmenter here. New subjects need reviewed masks/polygons, not copied girl-specific color thresholds.

The example's masks were localized and derived from source HSV/color boundaries, then visually inspected. Their occlusion boundaries remain approximate. The covered torso is N/A. Correct annotations when inspection finds an artificial crop/semantic boundary; retain previous runs rather than rewriting their scores. `input_hashes` fingerprints the image, annotation and actual mask arrays.

Validation produces front `beauty`, `silhouette`, `labels`, `albedo`, `clay`, plus side/back/three-quarter beauty. ID/silhouette/albedo use Standard, exposure 0, gamma 1, deterministic seeds and **no denoising**. Temporary materials restore in `finally`. The source and model share canvas dimensions and the calibrated orthographic camera. Style beauty and albedo remain separate, so lighting-driven darkness is not mistaken for base-color mismatch.

Registration permits `none` (default for calibrated scenes) or one global `bbox_similarity` (uniform scale and translation, including pixel-center correction). It records before/after transforms and IoU. No per-component warps, anisotropic scaling or elastic registration.

Reports include visible component IoU, symmetric boundary distance / full character height, actual mesh-anchor projection errors, and median Lab delta-E76 between reference and unlit base colors. Lab is **descriptive** because source illumination is unknown. No intrinsic reflectance recovery is claimed. Current example anchors are chin and both hand centers; add trustworthy facial landmarks for tighter expression evaluation. IoU measures annotated pixels, not volumetric or production quality.

## Phase 2: configurable structure

`shape` keys are stable component IDs. Each has `kind`, `material`, optional `label` aggregation and state. Supported builders:

- `head`: multiple `[z, half_width, half_depth, center_x, center_y, rotation]` sections, cheek fullness, chin taper, width/depth/asymmetry. Uses bounded monotone Hermite interpolation to avoid section bands. Depth floor prevents paper-thin optimization.
- `sweep`: continuous path and matching radius profile, optional palm/thumb volumes, radius/palm scale. Shoulder sockets should enter the torso; do not let a wide garment AABB stand in for a real joint connection.
- `loft`: at least three curved dress sections, explicit thickness, independent strap paths and low-frequency hem waves.
- `shoe`: toe, upper, annular opening rim and thin sole, independently identifiable objects. The current rim overlaps a continuous upper; it is a visual opening cue, **not a functional hollow shoe cavity**.
- `hair`: continuous cap, explicit directed flow guides and buns with a few directional folds. Styling remains an artistic design problem; the example does not achieve the reference hair silhouette.
- `surface_patch`: a source polygon is triangulated, degenerate planar edges cleaned, internally subdivided, then every vertex ray-projected onto the actual head before shallow extrusion. Patches depend on head updates. Raised ellipsoids can use `head`, `surface_anchor_px`, `surface_offset` (e.g. nose).

Positions, contours and guides belong in each character config; no example coordinates live in generic builders. Stable names are `<character>::<component>::<role>`. A head update rebuilds its projected dependents; a locked dependency blocks that candidate. Existing expression swapping is preserved in the original workflow; this fitter does not yet generate arbitrary new expression sets.

## Phase 3: separate style/material parameters

`blender-styles/scripts/handmade_surface.py` reuses the existing clay material factory and sRGB conversion. Each material has its own seed, low-frequency scale-relative geometry deformation, localized medium dents/relief, restrained high-frequency bump, color variation and roughness. Fresh geometry is displaced once; local seeds derive from stable IDs so rebuilding a limb cannot reshuffle hair dents.

`analyze` writes `sampled-colors.json` using robust visible-mask medians. Review those colors before placing them in the config: reference highlights/shadows remain in the samples. `materials.*.color_source` records provenance; it does not imply automatic material relighting. The example's surface is still too clean for the intended rough clay style, despite implemented three-band controls. Shape fitting takes precedence over increasing noise.

## Phase 4: local refinement and regression protection

A structured defect names the component, observed bbox/boundary mismatch, confidence, candidate parameters and locality. Coordinate search evaluates minus/plus a bounded step for one component/parameter each round. It reopens the last accepted snapshot, rebuilds only that dependency set, and hashes every unaffected object's geometry, transform, modifiers and shader data.

A candidate is rejected for structural failure, global silhouette regression, another measured component's regression, landmark regression, or insignificant local improvement. `locked`/`approved` components are not rebuilt. These are computational states; marking something locked for a search is **not user artistic approval**. Candidate acceptance and selection are recorded separately when both directions improve. The accepted `.blend` and config remain immutable; rollback means continuing from their paths, not attempting to undo a mutated shared scene.

Stop reasons: measured thresholds (only when the evidence gate allows), iteration limit, or no actionable unlocked parameters. A low locked score or N/A part is not silently accepted. Failed subprocesses/timeouts remain in history with their logs.

3D QA evaluates finite coordinates, non-manifold edges, degenerate faces, consistent winding, positive signed volume, depth floor, palm connection, configured endpoint-to-convex-surface sockets and AABB broad phase. It **does not** certify arbitrary self-intersection, cloth collisions or hidden geometry. `--rig-test` creates temporary skinned limb copies with two bones, bends each joint and verifies finite displacement, then removes them. This is a real smoke test, **not a delivered production rig or deformation-quality certification**.

## Tests

```bash
uv run --project skills/blender-python-modeling python -m unittest discover \
  -s skills/blender-python-modeling/tests -v

blender --background --factory-startup --python-exit-code 1 \
  --python skills/blender-python-modeling/tests/blender_fit_integration.py \
  -- --output output/fit-integration-check

uv run --project skills/blender-python-modeling python \
  skills/blender-python-modeling/scripts/test_reference_image_analysis.py
uv run --project skills/blender-python-modeling python \
  skills/blender-python-modeling/scripts/test_module_ledger.py
```

Keep the original `blender-styles/scripts/test_soft_clay.py --render` regression suite. See the run-specific report for actual counts and failures; command exit success alone does not validate reference agreement.

Generate a paired report with `scripts/report_fit_run.py --baseline BASELINE --run RUN --delivery FINAL_RENDER_DIR --output REPORT_DIR`. Verify real snapshots/candidate history with `scripts/verify_fit_run.py --run RUN --baseline BASELINE --output REPORT.json`.
