# Single-View Inference Contract

The source image constrains only what it actually shows. Before prompting image generation, create a compact evidence map.

## Classify the source view

Record:

- likely view: front, rear, side, top, or three-quarter;
- projection confidence: orthographic-like, weak perspective, or strong perspective;
- visible axes and foreshortening;
- crop, occlusion, transparency, reflection, or motion blur;
- whether the design appears symmetric and along which axis.

Do not measure pixel ratios from a perspective view as if they were orthographic dimensions.

## Choose five or six views

Use five views only when the design is bilaterally symmetric or the user explicitly accepts mirrored hidden-side assumptions. Record which side view is canonical.

Upgrade to six views when:

- visible left/right details differ;
- a side-mounted door, tool, limb, weapon, intake, exhaust, control, or accessory is present;
- asymmetry affects silhouette, function, assembly, materials, or identity;
- symmetry is uncertain and choosing it would materially constrain later modeling.

Top and bottom remain required in both modes. A three-quarter image can clarify volume but never replaces front, back, side, top, or bottom controlling views.

## Evidence labels

Use three labels:

- **Observed:** visible in the supplied image, such as colour blocks, openings, wheel count on the visible side, or a front silhouette.
- **Inferred:** chosen to complete hidden views, such as rear propulsion, unseen-side symmetry, depth, or attachment layout.
- **Unknown:** cannot be resolved without another view or user decision, such as exact back panel, interior depth, underside mechanism, or real scale.

The prompt may instruct the generator to realize inferred features, but the completion report must not merge them into observed facts.

## Build an invariant ledger

Keep a short list that every generated view must preserve:

- primary silhouette and overall proportion family;
- repeated-component count;
- major openings, windows, limbs, wings, wheels, handles, or appendages;
- attachment positions relative to the body;
- colour/material regions;
- symmetry or deliberate asymmetry;
- canonical forward/up direction;
- style, age, wear level, and surface-language density.

Avoid arbitrary side-specific details. If only one side is visible and no asymmetry is implied, default to bilateral symmetry and state that assumption.

## Functional versus decorative uncertainty

Ask for clarification or produce alternatives when hidden design changes function, assembly, identity, or silhouette. Examples include wheel count, door placement, limb structure, weapon location, propulsion type, or a load-bearing joint.

Infer ordinary low-impact details without blocking, such as continuation of a trim line, repeated panel spacing, or a plausible underside seam.

## Scale and dimensions

Without a known dimension or semantic scale anchor:

- use relative/normalized proportions only;
- do not add rulers, measurements, grids with implied units, or dimension arrows;
- do not infer category-average size as fact;
- state that absolute scale remains unknown.

If the user supplies one trusted dimension, preserve it as metadata for later modeling. Image generation still cannot guarantee dimensionally exact pixels.

## Character-specific constraints

For characters, also lock:

- one explicit neutral A-pose/T-pose/standing pose as requested, including head, spine, pelvis, shoulder, elbow, wrist, hip, knee, ankle, hand, tail, and wing state where applicable;
- face identity, hairstyle silhouette, age, body proportions, outfit layers, footwear and accessories;
- left/right asymmetry that is actually observed;
- uncovered view of hands, feet, tail, wings, props, or equipment needed for modeling.

Use the same joint state, ground plane, centerline, and semantic landmark heights in every controlling view. A perspective source may guide the chosen pose, but converting it into a normalized modeling pose is an inference and must be labeled as such. Read [pose-and-configuration-normalization.md](pose-and-configuration-normalization.md) for the Blender-readiness contract.

Do not invent anatomy hidden by clothing as if it were documented design.

## Articulated props and machines

Lock one mechanical configuration before generation: steering angle, suspension state, doors and hatches, hinges, pistons, robot joints, control surfaces, deployable tools, and other movable assemblies. Unless the source or user requires an active state, prefer a neutral closed or zero configuration suitable for blockout. Do not use different configurations to expose otherwise hidden parts in separate views.
