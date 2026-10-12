# Miniature lighting and camera

`setup_clay_lighting.py` generates scene-scoped key/fill/rim Area lights, a node World and an optional camera. It preserves the prior world/camera datablocks, but assigns its own active references. Use `with_camera=False` / `--keep-camera` when framing is already approved. Existing lights are preserved and still contribute: hide or tune only those explicitly within the user's scope.

## Scale and softness

`scale` is a reference-length multiplier in Blender coordinates, not a command to rescale arbitrary scene data or alter `scene.unit_settings`. Positions, light sizes and camera clipping are multiplied by it. Light power scales by `scale²`, compensating approximately for inverse-square falloff under uniform geometric scaling. World strength and camera focal length remain unchanged.

The default rig centers around `lighting.center`, with broad disk emitters:

- key offset (−3,−4,5), size 4, energy 450;
- fill offset (4,−1,3), size 5, 40% of key power;
- rim offset (1,4,4), size 3, 55% of key power;
- neutral World background, strength 0.3.

These are starting ratios in reference coordinates, not universal watt values. Set `center` for each composition. A large source relative to the asset softens shadows; a weak environment preserves modeling in the shadow side. Use a real floor and physically plausible object contact for grounding. Bright environment light cannot compensate for missing ground or floating geometry.

Cycles supplies physical indirect light. EEVEE can need scene-appropriate probes/ray tracing and sufficient samples depending on version and composition. Do not set old contact-shadow, AO or ray-tracing properties blindly; use RNA and a rendered comparison. The portable rig uses `use_shadow`, real geometry and area lights rather than obsolete global AO switches.

## Camera and miniature cues

Choose 45–85 mm perspective lenses to control distortion, or orthographic projection for diagrammatic/icon compositions. Avoid an automatic ultra-wide lens to fit the scene. The camera has explicit normalized position/target, lens, orthographic scale and clipping configuration; it is **not** an auto-framing algorithm.

Leave margins for the entire motion envelope and its shadow. A portrait output often needs a farther camera or different layout than landscape. Inspect evaluated bounding boxes at extreme frames and camera depth/clipping. The QA tool detects conservative bounding-box crop/clip; a cropped background can be tagged `obj["soft_clay_background"] = True`.

Depth of field is optional, off by default. When enabled, the focus distance targets `camera.target`, with configurable f-stop; start around f/5.6–8. Strong DOF can convey miniature scale, but unreadable faces, hands or contacts fail acceptance. Verify focus at moving extremities, not just frame 1. Production tracking focus can use a project-owned target and is outside the static rig's setup.

## Repeatability

Run with the same scene name and owner to update the same lights/camera. Shared cross-scene rig objects, linked/overridden data, animation or constraints on rig objects produce errors rather than destroying authored motion. Use a distinct owner to create an independent setup. For moving lights/cameras, set up once then animate in a project recipe; do not rerun a static rig over authored animation.

Use one OCIO view transform, look, exposure and gamma across shots. `setup_render` configures these separately from the rig. A custom OCIO installation can lack AgX; choose a runtime-supported view transform or explicitly set `KEEP` and record the actual choice. See [rendering](rendering.md) and the [general scene reference](../../blender-python-modeling/references/scene-lighting-rendering.md).
