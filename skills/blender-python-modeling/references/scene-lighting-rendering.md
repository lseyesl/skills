# Scene, Lighting, and Rendering Recipes

## Camera composition

Create a camera with a deliberate target, lens, distance, and clipping range. Aim without viewport operators:

```python
from mathutils import Vector

camera.location = (4.0, -4.0, 3.0)
target = Vector((0.0, 0.0, 1.0))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 50.0
camera.data.clip_start = 0.01
camera.data.clip_end = 1000.0
scene.camera = camera
```

Use orthographic projection for diagrams, elevations, icons, and dimensionally neutral product views. Use perspective for natural scale cues. For products, start around 50–85 mm; for interiors, use a wider lens carefully and check edge distortion.

Frame from the evaluated bounds of the subject, not a guessed distance. Leave margin for shadows, motion, and aspect-ratio changes.

## Three-point studio lighting

A practical baseline:

- key: large Area light 30–60° to the subject, strongest source;
- fill: larger and weaker from the opposite side;
- rim: behind/above to separate the silhouette;
- world: low-strength neutral environment, not a substitute for deliberate lights.

Large sources produce softer shadows. Scale light size with the subject. Use energy ratios as a starting point and judge the rendered image; identical watt values behave differently across scene scale and exposure.

For daylight exteriors, use a Sun for direction and an HDRI or sky for environment. For stylized work, build the value structure first, then add colour contrast.

## World nodes

Retrieve world nodes by type:

```python
world = scene.world or bpy.data.worlds.new("WORLD_task")
scene.world = world
world.use_nodes = True
background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
socket_by_identifier(background, "Color").default_value = (0.03, 0.03, 0.03, 1.0)
socket_by_identifier(background, "Strength").default_value = 0.3
```

Use the `socket_by_identifier` helper from the material reference. Before indexing world sockets on another Blender version, inspect the node with `describe_node_type`.

## Render engine selection

Render-engine identifiers are dynamic. Blender 4.5.12 reports `BLENDER_EEVEE_NEXT`; do not copy `BLENDER_EEVEE` from older or Blender 5-oriented examples.

Keep the current valid engine unless the deliverable requires another. When switching, assign inside `try/except TypeError`, report the accepted values, and verify the result:

```python
try:
    scene.render.engine = desired_engine
except TypeError as exc:
    raise RuntimeError(
        f"Render engine {desired_engine!r} is unavailable in {bpy.app.version_string}: {exc}"
    ) from exc
```

Use EEVEE for fast iteration, stylized work, and many real-time previews. Use Cycles when accurate indirect lighting, refraction, caustic-sensitive glass, or final photorealism matters. Do not configure GPU backends by a hardcoded enum; inspect available devices and preserve the user's device choices unless the task explicitly changes them.

## Output settings

Set resolution, frame range, FPS, output path, and format explicitly. Enumerate valid file formats from RNA before assignment:

```python
settings = scene.render.image_settings
valid = {
    item.identifier
    for item in settings.bl_rna.properties["file_format"].enum_items
}
if requested_format not in valid:
    raise ValueError(f"unsupported format {requested_format}; valid={sorted(valid)}")
settings.file_format = requested_format
```

Blender 4.5.12 does not report AVIF, while Blender 5.1 references may. The tested baseline includes PNG, JPEG, OpenEXR, TIFF, HDR, WEBP, and FFMPEG.

For stills, use PNG for lossless delivery and OpenEXR for compositing/high dynamic range. For animation, prefer an image sequence for expensive or restartable renders, then encode video separately.

## Colour management

Do not hardcode a colour-management look. List the valid view transforms and looks in the running OCIO configuration. Preserve the current setup unless the user requests a look change. Adjust exposure before compensating by arbitrarily multiplying every light.

## Render validation

Before the final render:

- confirm the active camera and aspect ratio;
- inspect near/far clipping and subject bounds;
- render a low-sample preview at reduced resolution;
- check materials in the chosen render engine, not only solid viewport mode;
- inspect highlights, shadow detail, noise, transparency, displacement, and colour transform;
- when passes, denoising, masks, or post-processing are required, apply [compositing-and-passes.md](compositing-and-passes.md) and validate the final Composite/File Output result rather than only the raw Render Result.
- confirm the output path does not overwrite an unrelated file.
