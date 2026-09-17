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

If no scale anchor exists, use normalized units with the longest inferred dimension equal to `1.0`. Do not silently choose metres, centimetres, or a category-average size.

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
3. Decompose the visible object into primitives, profiles, repeated parts, and negative spaces.
4. Build primary forms first and render matching front/side/top cameras.
5. Run the analyzer again with those renders as `--candidate` inputs.
6. Fix the largest silhouette and aspect errors in the Python parameters.
7. Add secondary forms and material detail only after primary proportions converge.

A high silhouette score does not prove correct depth, topology, back-side construction, or real-world scale.

## Interpreting confidence

- Low segmentation confidence: inspect the debug overlay; background, shadow, or cropped subject may have contaminated the mask.
- Low orthographic confidence: do not use that view for metric ratios.
- High multi-view residual: preserve alternatives or choose one controlling view and report the conflict.
- Low render comparison score: check camera matching before changing geometry.
- Good front/side scores but uncertain perspective: hidden curvature remains underconstrained.

## Stop conditions

Stop automatic iteration and request judgment when:

- different views show incompatible part counts or attachment points;
- the object is cropped in a controlling view;
- reflective/transparent surfaces defeat segmentation;
- the camera cannot be matched well enough for silhouette comparison;
- a dimensionally accurate deliverable is requested without any scale anchor;
- inferred hidden geometry would materially affect function, printing, or assembly.
