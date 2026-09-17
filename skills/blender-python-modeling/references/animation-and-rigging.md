# Animation and Rigging Recipes

## Direct keyframes

For object transforms and scalar properties, direct keyframe insertion is more stable than UI operators:

```python
obj.location = (0.0, 0.0, 0.0)
obj.keyframe_insert(data_path="location", frame=1)
obj.location = (2.0, 0.0, 0.0)
obj.keyframe_insert(data_path="location", frame=48)
```

Set rotation mode explicitly before animating rotations. Use quaternion rotation for unconstrained 3D motion and Euler angles when artist-facing channels and predictable single-axis edits matter.

Keyframe material inputs, shape-key values, light energy, camera lens, constraint influence, and custom properties on the owning datablock. Validate start, middle, end, contact, and loop-boundary frames.

## Interpolation and motion design

- Bezier: natural acceleration and editable easing;
- Linear: constant-rate mechanical motion;
- Constant: stepped/blocking animation;
- Cycles modifiers: repeat motion without duplicating keys.

Blender's layered Action API changed across late 4.x and 5.x. Simple `keyframe_insert` is verified on Blender 4.5.12; for direct F-Curve/action-layer manipulation, inspect the running Action schema instead of copying a 5.x example.

## Constraints before baked keyframes

Use constraints for relationships that should remain editable:

- Copy Location/Rotation/Transforms for following;
- Track To or Damped Track for cameras and look-at objects;
- Child Of for switchable parenting;
- Limit Location/Rotation/Scale for mechanical bounds;
- IK for limb chains;
- Follow Path for path-driven motion.

Create constraints directly:

```python
constraint = camera.constraints.new("TRACK_TO")
constraint.target = target
constraint.track_axis = "TRACK_NEGATIVE_Z"
constraint.up_axis = "UP_Y"
```

Confirm enum identifiers through `bpy_api_lookup` when uncertain. Check dependency cycles before linking objects that already influence one another.

## Drivers

Drivers are appropriate for deterministic relationships, not arbitrary scripting:

```python
fcurve = driven.driver_add("scale", 2)
driver = fcurve.driver
driver.type = "SCRIPTED"
variable = driver.variables.new()
variable.name = "control_x"
variable.type = "TRANSFORMS"
variable.targets[0].id = controller
variable.targets[0].transform_type = "LOC_X"
variable.targets[0].transform_space = "WORLD_SPACE"
driver.expression = "max(0.1, 1.0 + control_x)"
```

Keep expressions simple and use driver variables rather than reaching through `bpy` from the expression. Give controls clear names and document their ranges.

## Armature construction

Armature edit bones require Edit Mode, so isolate this context-sensitive stage:

1. create armature data and object through `bpy.data`;
2. make it active and selected;
3. enter Edit Mode and create/connect bones;
4. return to Object Mode in a `finally`-style cleanup path;
5. add pose constraints in Pose Mode or directly on `pose.bones`;
6. verify rest pose, bone roll, parent chains, and deformation before weight painting.

Do not apply object transforms or destructive modifiers to a rigged mesh without checking armature modifiers, shape keys, vertex groups, and animation. Keep deform bones separate from control/mechanism bones through naming and bone collections where supported.

## IK and mechanical rigs

For a limb IK chain, configure the IK target, pole target, chain length, pole angle, and influence. Test straight, bent, and extreme poses for flips. For mechanical rigs, prefer explicit constraints and local axes; arbitrary Euler keyframes accumulate alignment errors.

## Baking and export

Bake only at the output boundary or when simulation/constraint evaluation must become explicit keys. Preserve an editable source action/rig. For GLB/FBX, verify frame range, sampling rate, root motion, object/bone axes, NLA inclusion, and whether modifiers or shape keys must remain unapplied.

For deform weights, influence limits, shape keys, clip ownership, root motion, and character-specific export checks, read [character-delivery.md](character-delivery.md).

Physics and simulation caches are highly context- and version-sensitive. Treat them as separate stages with explicit cache directories and frame ranges; verify the running API before baking, and never overwrite an existing cache implicitly.
