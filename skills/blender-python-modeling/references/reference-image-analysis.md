# AI Reference Image Analysis

Use reference images as evidence for a parametric model, not as proof of hidden geometry or real dimensions. AI-generated views frequently contain inconsistent proportions, topology, perspective, and details.

When only one design view exists and the user first needs inferred modeling artwork, use `concept-multiview-sheet` to create five symmetric or six asymmetric views. Treat its output as a design hypothesis: retain its observed/inferred/unknown ledger and run the consistency checks below before blockout.

## Input priority

The most useful package is:

1. front, canonical side, back, top, and bottom views labeled explicitly for a symmetric model;
2. both left and right views instead of one canonical side when the design is asymmetric;
3. one three-quarter/perspective view for volume and style;
4. close-ups for joints and surface details;
5. any semantic scale anchor, even approximate, such as “tabletop object” or “about 20 cm tall.”

For reusable characters, the controlling package must depict the selected neutral bind/rest pose, prepared before geometry. Keep seated/action beauty images as separate appearance references; do not use their silhouette as the sole construction target for a later walking rig. Select the anatomy-appropriate pose and record source-pose conversion as inference using [character-delivery.md](character-delivery.md#reference-and-rest-pose-before-modeling). Existing calibrated neutral references can be reused; explicitly fixed-pose sculptures retain their requested pose.

If no scale anchor exists, use normalized units with the longest inferred dimension equal to `1.0`. Do not silently choose metres, centimetres, or a category-average size.

## Establish the Blender reference workspace before geometry

Seeing an image in the conversation is not the same as having a calibrated modeling reference. Before building reference-driven geometry:

For generic procedural tasks, use [reference_workspace.py](../scripts/reference_workspace.py)
and the [executable setup/build/review sequence](reference-workspace-tool.md).
The task template calls its prerequisite before deleting/rebuilding old geometry.
An imported Image Empty is a visual guide, not an automatic modeling constraint:
builders must consume calibrated landmarks/profiles or use an equivalent measured
fitting path, then compare actual geometry to those guides.

1. **Prepare separate images.** Split a sheet into its real view regions, preserving complete silhouettes and useful landmarks. Do not assume the generator obeyed equal cell boundaries. Preserve originals and the crop/label mapping; do not stretch a distorted panel to make its geometry appear correct.
2. **Choose axes and controlling evidence.** Record forward/up, anatomical left/right where relevant, pose, origin and scale. Identify which views or regions control width, height, depth and attachments. A weak perspective side image can help judge volume without being a dimensional authority. Missing or rejected views remain explicitly unresolved or inferred, not manufactured measurements.
3. **Import into Blender.** Put Image Empty reference objects in a named task-owned collection. Orient each image plane to its corresponding orthographic view and choose its in-plane orientation so forward/up agree across views. Keep opposite views on distinguishable objects; confirm they are not accidentally mirrored.
4. **Configure useful display.** Start opacity around 0.35–0.5 and adjust for legible comparison. Use the reference image's **Depth: Front** display mode to overlay the model; this is a draw-order setting, not a requirement to move the image arbitrarily toward a camera. Use front-side visibility and axis-aligned orthographic-only display when supported, hiding unrelated references through collections/local views otherwise. Hide perspective display by default so all planes do not obscure the model. Inspect the running Blender's properties/enums before scripting these settings.
5. **Calibrate and protect.** Align centerline, ground/origin and trusted landmarks such as sole, knee, pelvis, shoulder, eye line and crown, or axles/hinges for mechanical subjects. Use uniform scaling per image and record any correction for generated panel scale drift. Do not independently squash width/depth or move a feature to hide disagreement. Lock reference transforms/selection after calibration, while leaving opacity and visibility adjustable.
6. **Review before construction.** Inspect actual front and side orthographic viewport screenshots, with the references visible and axes/landmarks checked; include other controlling views where available. Save the calibration record and screenshots. Import success alone does not pass this gate. If the evidence cannot constrain a region, apply the interpretation policy below before shaping it.

Keep a compact project-local record (for example `reference-setup.json`): original/cropped image paths, view labels and reliability, object names, axis/rotation, uniform scale and offsets, image/world landmark correspondences, intended constraints, unresolved conflicts and chosen interpretations. Derive modeling parameters from this record; handwritten coordinates without a documented reference relationship do not establish a match. Pack the reference images into the derived `.blend` or include portable relative files, then verify that reopening retains them.

Image Empties are viewport guides and do not appear in normal final renders. Use viewport captures for their display settings, and separate matched-camera render/reference overlays for shape comparison. Do not silently substitute a rendered image plane for an imported modeling reference.

## Interpret AI artifacts using evidence and structure

AI panels can invent extra fingers, flatten a skull, distort a limb, move attachments, change pose, or expose a part that should be occluded. Do not copy every pixel or force one model to satisfy mutually incompatible panels.

- Honor explicit user constraints and trusted measurements. For visible identity/design, prefer the original source and mutually consistent regions over an isolated generated variation.
- Check anatomy, mechanical connectivity, volume, symmetry/asymmetry, occlusion and the possibility of one fixed three-dimensional configuration. Use these to identify likely depiction errors, without erasing intentional stylization or replacing the user's design with generic anatomy.
- For a local, low-impact artifact whose intended construction is clear, make the smallest coherent correction, continue modeling and record the source evidence, rejected depiction, chosen interpretation and uncertainty. Use other reliable regions to constrain it. An inaccurate panel does not require stopping the whole task.
- When two or more plausible interpretations remain and the choice materially changes identity, silhouette, attachment, motion, fit or function, request human judgment **before committing that affected geometry**. Show the conflicting crops or an annotated overlay, explain what cannot be inferred, and offer concrete options with a recommendation where justified. Continue unrelated, well-constrained work while waiting; elapsed time is not approval.
- When a view is cropped or segmentation fails, use another trustworthy view or bounded manual landmark analysis if sufficient. Ask for help only if the remaining evidence cannot support the requested result. Do not claim measured accuracy from a guessed correction.

Record each consequential interpretation as observed / inferred / unresolved, and make any approved design changes traceable. After resolving a conflict, compare against the selected constraints rather than reporting the rejected AI pixels as unexplained modeling error.

## Run the analyzer

The host-side analyzer uses this skill's `pyproject.toml` and `uv.lock`; do not install OpenCV or NumPy into Blender's bundled Python or the user's global Python. From any working directory, run:

```bash
uv run --project /absolute/path/to/blender-python-modeling \
  python /absolute/path/to/blender-python-modeling/scripts/analyze_reference_images.py \
  --view front=/absolute/front.png \
  --view side=/absolute/side.png \
  --view top=/absolute/top.png \
  --output /absolute/reference-analysis.json \
  --debug-dir /absolute/reference-debug
```

The first run creates `<skill-dir>/.venv`; the repository-root `.gitignore` must exclude `.venv/` directories from version control. Commit `uv.lock` with the skill so later runs resolve the same dependency versions.

Use `--candidate front=/absolute/render-front.png` after Blender produces a matching render. Candidate labels must match reference labels. Add `--known-largest-dimension <value>` only when the user supplies or approves a scale anchor.

The analyzer is deterministic and local. It does not call an AI service.

## What it extracts

- foreground mask and bounding box;
- normalized contour with centered, Y-up coordinates;
- width/height aspect, occupancy, solidity, holes, and symmetry scores;
- dominant line directions as perspective evidence;
- a small foreground colour palette;
- front/side/top dimension ratios when at least two labeled orthographic views exist;
- a residual showing whether the three ratios agree;
- render/reference silhouette IoU, shape distance, aspect error, and a combined score;
- warnings and confidence values.

The script does not infer semantic parts or hidden surfaces. After reading its JSON, use visual reasoning to propose primitives and part relationships, marking each as observed, inferred, or unknown.

## Multi-view dimension fusion

For labeled orthographic-like views, the analyzer uses scale-invariant ratios:

- front: width / height;
- side: depth / height;
- top: width / depth.

It solves these ratios together and normalizes the largest dimension to `1.0`. Because ratios survive independent image crops, the views do not need identical pixel scale. A high residual means the AI views contradict one another; do not average the conflict silently.

Perspective images are excluded from dimension fusion. Use them for curvature, occlusion, material, and style evidence only.

## Modeling from the analysis

1. Treat the fused dimensions as a blockout envelope, not a finished surface.
   Start from [assets/reference_blockout_template.py](../assets/reference_blockout_template.py) when a concrete normalized blockout and front/side/top cameras are useful.
2. Map normalized contour points to the intended Blender axes for each view.
3. Establish and inspect the calibrated Blender reference workspace above, then decompose the visible object into primitives, profiles, repeated parts, and negative spaces. Keep landmark-derived positions and cross-section profiles in the persistent recipe.
4. Build primary forms first and render matching front/side/top cameras.
5. Run the analyzer again with those renders as `--candidate` inputs.
6. Inspect matched-camera overlays and fix the largest silhouette, aspect, landmark and local profile errors in the Python parameters. For characters, compare eye/brow/nose/mouth locations in head-relative coordinates, skull width/height/depth, and limb widths at several heights including joints. Distinguish intentional asymmetry from uncontrolled random variation. A plausible whole silhouette does not excuse incorrect facial placement or discontinuous limb thickness.
7. Add secondary forms and material detail only after primary proportions converge.

A high silhouette score does not prove correct depth, topology, back-side construction, or real-world scale.

## Interpreting confidence

- Low segmentation confidence: inspect the debug overlay; background, shadow, or cropped subject may have contaminated the mask.
- Low orthographic confidence: do not use that view for metric ratios.
- High multi-view residual: preserve alternatives or choose one controlling view and report the conflict.
- Low render comparison score: check camera matching before changing geometry.
- Good front/side scores but uncertain perspective: hidden curvature remains underconstrained.

## Human judgment and stopping the affected work

First attempt the evidence-based interpretation policy above. Request human judgment when incompatible part counts, attachments, camera hypotheses or hidden constructions remain materially ambiguous; when no usable reference remains for a required region; or when a dimensionally accurate deliverable lacks the necessary measurements. Explain the specific uncertainty and which region is paused. Do not block unrelated work for a minor AI depiction error, and do not keep retrying image matching when the disputed pixels cannot describe a coherent object.
