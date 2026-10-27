# Executable and visual acceptance

Use `scripts/validate_clay_scene.py` for structural checks and JSON evidence. It is read-only apart from temporary frame evaluation (restored on exit) and temporary loaded images (removed). Supply the same JSON profile as setup. By default it checks owned objects; use `--objects` for explicit existing assets.

The requested scene must be active because evaluated geometry uses its dependency graph. In a project recipe, set the correct scene before calling `validate_scene`; the checker refuses a mismatched scene rather than evaluating against another scene's graph.

```bash
blender --background /absolute/output/demo.blend --python-exit-code 1 \
  --python skills/blender-styles/scripts/validate_clay_scene.py -- \
  --config /absolute/project/style.json --frames 1 7 13 19 24 25 \
  --images '/absolute/output/frame-*.png' --report /absolute/output/quality.json
```

## Automated gates

| Area | Executable checks | Further acceptance |
|---|---|---|
| Geometry | Finite transforms, nonzero scale, base/evaluated face budget, degenerate/loose geometry; optional manifold and project dimension expectations | Compare silhouette and part ratios to approved design in several views |
| Materials | Assigned material slots, single Principled, roughness/metallic limits, stored parameter agreement, actual roughness/specular and required links | Actual rendered palette, highlights, texture scale and temporal stability |
| Lighting | Active powered Area lights, shadows/size diagnostics, environment presence | Soft shadow direction, readable contact, no blown-out/floating forms |
| Camera | Active linked camera, sampled evaluated bounding boxes in frame and clip range | Deliberate framing/DOF and room for shadows/motion |
| Binding | Armature target exists, deform-group weights present/normalized | Rest pose, extreme bends, joint volume, controls and deformation behavior |
| Animation | Finite evaluated data, loop endpoints (transforms/vertices/bones), hold sampling and period divisibility | Full playback, contact transitions, penetration, seam velocity and limb identity |
| Shots | `--shots` compares stored palette/material/light profiles plus actual OCIO/exposure/gamma/FPS | Rendered colors, silhouette scale, light direction and edit continuity |
| Output | Existing nonempty decodable images, finite pixels, profile dimension agreement | Expected frame count/order, video decoder/playback |

`require_manifold` is false by default because renderable open surfaces can be intentional. Enable it for closed assets requiring watertight geometry. Face budget is **faces**, not triangles, and excludes generated instances that need separate asset-level checks. A single high-complexity evaluated mesh fails even when its base mesh is sparse.

Background meshes intentionally outside the camera may be marked `soft_clay_background=True`; this bypasses only crop checking, not topology/material validation. Bounding-box framing is conservative and can report a crop for an intentionally cropped foreground: record that shot-specific exception in review rather than hiding other objects from QA.

When enforcing real proportions, pass `--expectations /absolute/project/asset-dimensions.json`: a mapping such as `{"actual object name": {"dimensions": [1.0, 0.8, 1.5], "tolerance": 0.01}}`. Dimensions and absolute tolerance are Blender units and are evaluated at the current frame. Keep ratio/design evidence in the project manifest too. The generic shader/rig cannot infer which proportions are correct. For reference-driven projects reuse the existing [module ledger and fidelity workflow](../../../../blender-python-modeling/references/fidelity-and-completion.md).

## Manual review record

Store review notes with output frame names and pass/fail for:

1. Geometry: approved silhouettes, part ratios, rounded edges and controlled facets.
2. Material: matte response, coherent palette, no stone-like blotches or sparkling bump.
3. Light: readable contact shadows, controlled highlights and stable illumination.
4. Animation: contact and extreme poses, full-speed playback, adjacent seam frames, no unintended deformation/intersections.
5. Multi-shot edit: stable asset proportions, palette, exposure and intentional camera/light differences.

`structural_ok` means automatic checks passed. `visual_approved` stays false: an agent/user must inspect images and playback and record evidence separately. Endpoint equality alone cannot certify a seamless cycle. Weight normalization alone cannot certify a good rig. The generic checker does not implement a collision solver, infer a target silhouette, or certify all frames from a few samples.

Keep failed reports and repair the persistent recipe. Deliver test results and known limits using [test results](test-results.md), with actual Blender version and renderer evidence rather than an inferred compatibility claim.
