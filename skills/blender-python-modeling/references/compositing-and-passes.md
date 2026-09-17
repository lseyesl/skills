# Compositing and Render Passes

Build compositor graphs only when the deliverable needs denoising, grading, masks, pass output, glare, keying, or other post-processing. Keep raw render data available for high-value deliveries; destructive grading in a single flattened image limits later correction.

## Plan passes before rendering

Choose passes from the actual composite or downstream workflow:

- Combined for the beauty image;
- Denoising Normal/Albedo for Cycles denoise;
- Z or Mist for depth effects, with camera clipping and value range verified;
- Normal, Position, Vector, UV or Object Index only when the consumer uses them;
- Diffuse/Glossy/Transmission/Emission components for relighting or grading;
- Cryptomatte Object/Material/Asset for robust masks.

Every pass increases memory, file size and render time. Do not enable all passes defensively.

## Script a stable compositor tree

Use exact node `bl_idname` values and retrieve sockets by runtime identifier/name after verifying the node schema:

```python
scene.use_nodes = True
tree = scene.node_tree
nodes = tree.nodes
links = tree.links

render_layers = nodes.new("CompositorNodeRLayers")
denoise = nodes.new("CompositorNodeDenoise")
composite = nodes.new("CompositorNodeComposite")

links.new(render_layers.outputs["Image"], denoise.inputs["Image"])
links.new(denoise.outputs["Image"], composite.inputs["Image"])
```

The example omits Denoising Normal/Albedo links until those passes are enabled and their sockets are confirmed. Blender node sockets and compositor execution changed across releases; use `describe_node_type` or inspect the created node rather than indexing Blender 5.x-only sockets blindly.

Give task-owned nodes stable names and frames. When editing an existing compositor, preserve unowned nodes and connect into the requested branch rather than clearing the whole tree.

## File outputs and colour

- Use absolute base paths and deterministic slot names for File Output nodes.
- Choose PNG/TIFF for display-referred images and OpenEXR for scene-linear/high-dynamic-range or multi-pass delivery.
- Prefer multilayer OpenEXR when passes must remain synchronized; document compression and bit depth.
- Do not apply display transforms twice. Clarify whether the output is scene-linear, view-transformed, or intended for a colour-managed application.
- For animation, use frame-numbered sequences; do not rely on a video container as the only master render.

## Cryptomatte and masks

Enable the matching view-layer Cryptomatte pass before creating Cryptomatte nodes. Preserve enough manifest data in the EXR when downstream selection is required. Validate masks on overlapping transparent, motion-blurred, instanced and hair/volume elements; a visible object does not guarantee a useful matte.

Use ID masks only when their integer assignment and anti-aliasing limitations are acceptable. Do not silently substitute object index for Cryptomatte.

## Denoising and grading

- Denoise the beauty path with compatible guiding passes and inspect fine textures, hair, reflections, transparency and motion.
- Grade after denoising unless the chosen workflow requires otherwise.
- Keep exposure and white balance decisions consistent with scene colour management.
- Clamp or glare only with explicit artistic intent; they can hide fireflies or destroy highlight information.

## Composite validation

- Render a representative frame using the actual engine and view layer.
- Verify required sockets are populated, file outputs are written, and paths/extensions match settings.
- Inspect raw Combined, each required pass, matte edges, denoised output and final Composite.
- For animation, sample motion-heavy and transparent frames and verify Vector/Z/Mist temporal behavior.
- Confirm a headless/background render produces the same required files as the interactive session.
