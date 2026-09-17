# Reference Fidelity and Completion Gates

Use this workflow for any model reconstructed from concept art, turnarounds,
photos, diagrams, or AI-generated multi-view sheets. A silhouette match proves
only the outer envelope. It does not prove that the visible design has been
modeled at the requested level of detail.

## Module versus Blender object

A **module** is a semantic assembly that a reviewer can identify and judge,
such as a viewport, manipulator arm, propulsion ring, hatch, seat, or sensor
mast. A Blender object is only an implementation unit. One module may contain
many objects, and a high object count says nothing about reference coverage.

Count modules before modeling. Split a coarse assembly into child modules when
the reference gives them an independently readable silhouette, material,
mechanical role, attachment, or repeated count. For example, do not record
"submarine details" as one module when the sheet separately shows a mast,
radome, antenna, service hatch, vents, lights, and sonar.

## Build a module ledger first

Copy [module-ledger-template.json](../assets/module-ledger-template.json) into
the task output directory and populate it before detailed geometry. Record:

- stable module ID and human-readable name;
- observed, inferred, or unknown evidence;
- source views where it is visible;
- primary, secondary, or tertiary priority;
- expected repeated-instance count;
- visible signature features that make the module recognizable;
- the subset of signature features actually verified in rendered views;
- current status and its Blender objects or collection;
- whether the user explicitly approved a simplification.

Use these priority meanings:

- **Primary:** controls the overall silhouette, proportions, or identity.
- **Secondary:** a separately recognizable assembly or large design feature.
- **Tertiary:** panel seams, fasteners, small vents, labels, and micro-detail.

Repeated asymmetric parts need separate ledger entries. Symmetric repeated
parts may share one entry only when `expected_instances` records the count and
the implementation is genuinely shared.

## Do not silently coarsen the ledger

Use the following test: if a reviewer could point to a visible item and say
"this part is missing or wrong" without referring to the whole model, it needs
its own module or signature feature.

Before leaving reference analysis, inspect every supplied view at full
resolution and account for:

- outer silhouette and negative spaces;
- attachments and connection geometry;
- repeated-part counts;
- front/back/top/bottom-only equipment;
- interiors visible through glass or openings;
- material boundaries and large colour blocks;
- service panels, vents, lights, sensors, rails, and handles;
- deliberate asymmetry.

## Completion stages

Use stage names literally. Never present an earlier stage as a finished model.

### Blockout

Purpose: validate axes, cameras, proportions, primary masses, and major
attachments.

Gate:

- every required primary module exists at least as `blockout`;
- matching orthographic renders have been inspected;
- report missing secondary and tertiary modules explicitly.

Allowed report language: "blockout complete" or "primary proportions pass".
Do not say "model complete".

### Feature-complete

Purpose: establish the complete recognizable design before micro-detail.

Gate:

- every required primary module is `matched`;
- no required primary or secondary module is `missing`;
- repeated instance counts match the reference;
- each primary and secondary module includes its signature features or is
  marked `simplified` with a concrete reason;
- front, back, both sides for asymmetric designs, top, and bottom have been
  visually reviewed where references exist.

Allowed report language: "feature-complete with N simplified and M missing
tertiary modules". Do not collapse those counts into a single percentage.

### Final

Purpose: deliver the user-requested finished asset.

Gate:

- every required module is `matched`; or a `simplified` module has explicit
  user approval recorded in the ledger;
- required repeated counts and signature features are present;
- `missing == 0` and `unapproved_simplified == 0`;
- structural, geometric, visual, render, save, and requested export checks
  pass;
- both a contact sheet and at least one perspective/hero view are inspected.

Only this gate authorizes unqualified language such as "finished" or
"complete".

## Presence and fidelity are different metrics

Always report both:

- `presence_coverage = (matched + simplified + blockout) / required`;
- `full_fidelity_coverage = matched / required`.

Also report absolute counts for `matched`, `simplified`, `blockout`, and
`missing`. A model with 18 of 20 modules present but only 12 matched is not
"90% complete"; it has 90% presence coverage and 60% full-fidelity coverage.

Silhouette or image-similarity scores are separate evidence. Never use them as
a substitute for module and signature-feature coverage.

## Acceptable reasons for simplification

Simplification must be visible in the ledger and final report. Acceptable
reasons include:

- the user requested a blockout, low-poly budget, distant background asset, or
  another constrained output target;
- supplied views contradict each other and the chosen interpretation is
  recorded;
- a hidden surface is genuinely unobservable and does not affect the requested
  function;
- the user explicitly approved the tradeoff.

The following are not sufficient reasons:

- a primitive was easier to script;
- the silhouette already looks close;
- the object count is high;
- the part is visible only in the top, bottom, or back view;
- the render is attractive enough to conceal the omission.

## Iteration policy

After each render pass:

1. Update module statuses from visual evidence, not from code intent.
2. Find the largest primary or secondary fidelity gap.
3. Fix that gap in the persistent script.
4. Re-render every affected controlling view.
5. Re-run the ledger validator.

Do not spend time on tertiary fasteners while a primary or secondary module is
missing, incorrectly oriented, or represented by an unrelated primitive.

Run the deterministic ledger check with the skill environment:

```bash
uv run --project /absolute/path/to/blender-python-modeling \
  python /absolute/path/to/blender-python-modeling/scripts/validate_module_ledger.py \
  /absolute/task/module-ledger.json \
  --output /absolute/task/module-coverage-report.json
```

The validator checks bookkeeping and completion claims. It cannot decide
whether a mesh visually matches the reference; that still requires rendered
view inspection.
