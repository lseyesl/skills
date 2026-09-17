# Physics and Simulation

Treat simulation as a separate, explicitly cached stage. Record Blender version, FPS, frame range, unit scale, solver settings, seeds, cache paths and dependency geometry before baking. A viewport playback is not a reproducible delivery.

## Shared simulation rules

- Work in real-world scale where the solver expects it; tiny or enormous scenes can become unstable.
- Apply scale only when safe for the source object and required by the solver. Preserve an editable copy.
- Start with simple collision geometry and no initial intersections.
- Use stable object names and task-owned cache directories outside shared or ambiguous locations.
- Set deterministic seeds wherever exposed. Some solvers or hardware paths can still vary; report that limitation.
- Preview at lower resolution/substeps, then freeze settings before the final bake.
- Never overwrite or free an existing cache outside the task's ownership without explicit permission.

## Rigid bodies

Rigid-body creation is operator-driven in common Blender APIs, so establish selection and active object explicitly:

```python
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.rigidbody.object_add()
obj.rigid_body.type = "ACTIVE"
obj.rigid_body.collision_shape = "CONVEX_HULL"
obj.rigid_body.mass = 1.0
```

Use primitive/convex collision shapes when possible; `MESH` is expensive and can be unstable for moving concave bodies. Validate mass ratios, margins, substeps, solver iterations, deactivation, constraints and high-speed tunnelling. Confirm the Rigid Body World collection contains only intended participants.

## Cloth and soft bodies

Cloth quality depends on mesh scale and topology. Use even quads where practical, separate simulation and render subdivision, and define pinning through an explicit vertex group. Validate bending, self-collision, collision thickness, friction and extreme poses.

Soft bodies require explicit goal/spring intent and topology suited to deformation. For both systems, test a short frame range before committing to the final cache. Initial intersections commonly cause explosive results; diagnose geometry before increasing solver quality.

## Fluids, smoke and fire

Mantaflow requires a domain that encloses flows and effectors throughout the simulated interval. Record domain type, resolution, adaptive settings, time scale, cache type, cache directory, flow behavior, effector thickness and secondary data such as mesh/noise/particles.

- Use low resolution for behavior tests, not as evidence of final surface quality.
- Keep cache directories unique per task/version/settings hash.
- Bake dependencies in the order required by the running Blender API.
- Verify domain bounds over the entire animation; moving sources can leave the domain.
- Treat liquid mesh, gas noise and spray/foam/bubble caches as separate outputs when applicable.

Fluid operators and cache schemas are version-sensitive. Inspect RNA and modifier/domain properties in the running Blender; do not copy Blender 5.x bake calls into a 4.x pipeline without a disposable test.

## Force fields and particles

Confirm field type, falloff, strength, noise, affected systems and collection visibility. Legacy particle systems and Geometry Nodes simulations have different data and export behavior; choose intentionally. Do not promise that procedural particles or simulation zones survive GLB/FBX—bake or convert only on a delivery copy when required.

## Baking and invalidation

Before baking, hash or record the settings and upstream inputs that invalidate the cache: topology, transforms, frame range, FPS, solver quality, collision objects, vertex groups and source animation. Store this metadata beside the cache when possible.

After a bake:

- sample start, middle, end and difficult contact frames;
- verify cache files exist and remain readable after reopening the `.blend`;
- ensure no dependency changed after the bake;
- render representative frames, because viewport and final subdivision/materials can expose intersections;
- bake transforms or mesh sequences for export only when the consumer requires them.

Stop after repeated instability and report the smallest failing frame/settings rather than silently escalating resolution or overwriting caches.
