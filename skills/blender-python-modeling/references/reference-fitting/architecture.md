# Reference fitting audit and design

Phase 0 audited on Blender 4.5.12 LTS. Optimization specification: user-supplied `blender_clay_skill_optimization.md` v1.0. This adds an executable pipeline to the existing skills, retaining all existing script APIs.

| Existing module | Already provides | Decision |
|---|---|---|
| `analyze_reference_images.py` | Alpha/background foreground, silhouette ratios, contour, deterministic palette | Reuse foreground extraction and IoU; add semantic annotation layer rather than another foreground detector |
| `validate_module_ledger.py` | Presence and claimed-stage bookkeeping | Retain; image metrics are additional evidence, never overwrite ledger labels |
| `blender-styles/scripts/clay_common.py` | Strict shared config, ownership, sRGB conversion | Reuse color, shader config and socket helpers; keep character config separate |
| `create_clay_material.py`, `setup_render.py` | Existing palette/shader and engine/color management setup | Reuse from optional handmade surface/validation adapters; do not alter old defaults |
| `validate_clay_scene.py`, `test_soft_clay.py` | Basic scene/output QA, existing integration regressions | Retain and run alongside new fitter tests |
| Original girl `rebuild/` recipe | Imported reference workspace, head surface projection, continuous limbs, three interchangeable expressions | Preserve original files; generalize construction concepts into independent config-driven builders. The new example includes the reference happy face; the old three-expression workflow remains available |
| Original `compare_reference.py` | Same-camera overlay and whole silhouette debug IoU | Preserve; replace its role for optimization with component masks, landmarks, Lab and boundary errors |

New data flow:

```text
character.json + explicit trusted masks/polygons + source RGBA
   -> config.validate + reference_masks
   -> Blender worker: packed reference workspace BEFORE geometry
   -> component builders -> per-material three-band clay
   -> fixed camera/render -> beauty / silhouette / labels / albedo / clay
   -> ONE global similarity alignment (or none)
   -> visible component IoU + boundary + actual mesh landmark + descriptive Lab
   -> defects -> bounded per-component parameter candidates
   -> reopen last accepted scene -> rebuild affected dependency set
   -> hash unrelated geometry/transforms/materials -> structural guard
   -> evaluate -> retain candidate OR rollback to immutable accepted snapshot
```

Module boundaries:

- `scripts/reference_fit/config.py`: Blender-independent validation, canonical hashes, change/dependency detection.
- `geometry.py`: testable monotone cross-sections and variable-radius path sampling.
- `blender_builder.py`: stable owner/component/object IDs; heads, limbs/hands, dress/straps, shoes, directed hair, projected facial patches. Local updates only remove owned affected objects. Material trees reused during local shape changes.
- `blender_validation.py`: actual Image Empties, fixed render environment, temporary pass materials restored in `finally`, topology/depth/connection checks and disposable two-bone bend tests.
- `evaluation.py`: shared foreground reuse, explicit semantic annotations, one recorded global transform, masks/overlays/heatmaps/metrics.
- `refiner.py`: evidence-linked defects, bounded coordinate search, lock/dependency protection, immutable snapshots and rejection reasons.
- `worker.py`: isolated Blender execution; `fit_character.py`: host orchestration, timeouts, retained logs and CLI.
- `blender-styles/scripts/handmade_surface.py`: optional per-region deterministic low-frequency deformation, localized medium dents and medium shader relief, restrained high-frequency bump; uses established shader API.

Character dimensions, source-specific masks, contour points, material values, hair flow guides and candidate bounds live in `examples/clay-girl-fit/`, never in generic algorithms. Geometry units are normalized character height; absolute physical size is unknown. Side view is fallible AI evidence, not calibrated photography.

Frozen original baseline: run `baseline --source <original.blend>` into a new directory. The source blend is read, tagged only inside the disposable process, and never saved over. New environment applies identical camera/lights/color management to both baseline and new model. Preserve its config, Blender version, render record and source file hash in the run report. A baseline render under a different environment must be labeled separately from the original historical beauty.
