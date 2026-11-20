# Local shape, relief and render review

Use before expensive full renders of reference-driven models. Catch wrong
geometry in the evaluated mesh and inspect surface detail at its intended scale.

## Independent shape constraints

Record each important part's long axis, broad surface normal, thickness direction,
attachment and signature relief. A closed leaf-shaped volume can still be an
upright paddle when its upper surface should face upward; a thick petal can lack
its central concavity. Record tilt relative to subject axes, not the hero camera.
Do not apply a leaf-specific numeric normal threshold to unrelated shapes.

Check front/side/top blockouts before detail. Check attachments against actual
stem, parent or joint positions; a correctly oriented floating part still fails.
Keep the same pose across views instead of rotating parts for better visibility.

## Geometry and sampling

Silhouette, cupping, folds, swollen margins and deep pressed grooves need geometry
when they define the reference or must survive side views/exports. Fine grain
may use bump/normal shading. A procedural shader does not replace missing form.

For recessed veins, require a continuous main path, branching side paths that
join it, tapering ends and clearance from the blade edge. Detached tubes,
parallel marks or one blurred center trench do not restore branching venation.
Generalize this check to seams, folds and engraved detail as appropriate.

Set sampling relative to the narrowest required feature and inspect the evaluated
mesh after subdivision, bevel, remeshing or decimation. Nonzero displacement and
manifold topology prove neither readable grooves nor adequate depth. Increase
local sampling/support or revise the relief profile if modifiers erase it;
avoid global polygon increases without evidence.

## Cheap-to-expensive review

1. Inspect one representative part from front/side/top in solid/clay lighting:
   orientation, volume and connections first.
   For characters, make the head/face and one shoulder-to-limb-to-paw chain the first samples: compare muzzle/jaw depth and section curvature, eye placement/surface fit, ear thickness/recess, joint width continuity and real sole contact. Trace cross-sections and local landmarks to trusted regions; extra primitives or grain cannot compensate for incorrect primary volume.
2. Render a local crop at modest samples using intended material, light and color
   management. Check grooves, branching, raised margins and dents individually.
3. Inspect at intended presentation scale. A feature visible only in an enlarged
   diagnostic image has not passed a main-shot readability requirement.
4. Only then render the full common-scale multiview suite and final hero.

After corrections, rerender affected local crops and controlling views first. Refresh the whole suite when global lighting/material changes or final assembly make those views affected; retain unchanged evidence with provenance rather than rerendering every camera mechanically. Follow the stage/freshness rules in [staged-execution.md](staged-execution.md).

If a feature disappears, distinguish shallow geometry/undersampling from modifier
smoothing, material contrast, light direction and occlusion. Change the cause,
not every bump or the whole style. For a correction, compare before/after with
the same camera, light and material. Label isolation renders and restore hidden
parts; they supplement the assembly image and cannot prove attachment/occlusion.

## Fixed-camera review for a local correction

Use [the Blender review renderer](../scripts/render_feature_review.py) on saved
before/after snapshots in an isolated process. For each defect it writes a
reference crop, before/after clay and before/after material images, and a
manifest bound to the module ID and its ledger feature. Keep the attachment and
its receiving part in the same crop. Use snapshots saved at the same pose. Both
channels use a common orthographic camera, studio rig, and exposure. Clay overrides the materials to expose
the shape. The material channel uses the snapshot's assigned shaders, or the
same project-specific preview material setup for both snapshots.

```bash
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python scripts/render_feature_review.py -- review-config.json --out review
```

The config uses schema version 1. Paths are relative to the config unless absolute.
`snapshots` names `before` and `after` Blender files. Supply `ledger`, square
`resolution`, Cycles `samples`, and `studio` with a world-space `center` and
positive `scale` to size the lights. List any unpacked material textures in
`material_files` so their contents participate in the run receipt.
Each entry in `features` names an `id`,
`module_id`, exact ledger `signature_feature`, `issue`, and `change`.
Its `camera` specifies world-space `target`, viewing `direction` from the target
to the camera, and square orthographic `span`. Its `reference` specifies `image`,
`view`, and top-left, end-exclusive `box_px` as `[left, top, right, bottom]`.
When comparing an orthographic guide, derive target and span from the calibrated
crop. For a perspective photo without a solved camera, treat the crop as visual
context and record the projection difference in the comparison.

Pass `--feature <id>` (repeatable) to rerender only the affected crops. A
`receipt.json` binds each run's inputs and artifacts, and `feature.json` leaves
visual review pending. Inspect the clay pair for shape and the material pair for
surface readability, then record the observations in the ledger. The
[lantern P1 replay](../examples/iron-lantern-p0/README.md#p1-fixed-camera-feature-and-material-review)
shows a project wrapper, source map provenance, and three matched-camera crops.

For a realistic surface, choose a sourced PBR set per reference material region
and record its origin, creator, licence, files and intended usage. Compare base
color under the fixed lighting, roughness by the size and strength of highlights,
and wear by where exposed material appears on the form. Use the source map as
supporting evidence for roughness and wear. A photo highlight cannot uniquely
determine base color or roughness. Follow [material map routing](materials-and-nodes.md#texture-based-pbr).

## Evidence and iteration cost

Record source region, candidate artifact/view, observed difference and verdict
per feature in `feature_reviews`. Parameters are implementation evidence, not
visual comparison. Do not batch-copy expected labels into matched features.

User feedback invalidates the affected match and prior final review. Keep failed
evidence, reopen the feature, repair and re-review. Do not narrow its definition
after a failure just to make the same mesh pass.

Rerender affected crops/views first; reuse unchanged evidence with provenance.
Record actual build/generation/render durations and retry reasons when available;
file timestamps and user response delays do not measure active execution time.
Do not generate images or rebuild models merely to verify prose-only skill edits.
