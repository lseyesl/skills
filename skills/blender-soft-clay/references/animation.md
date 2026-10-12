# Clay animation and timing

## Playback rate versus pose rate

| Delivery | Playback configuration | Motion treatment |
|---|---|---|
| Smooth 24fps | `fps=24`, `fps_base=1` | `hold_frames=1`, Bezier or Linear |
| 12 poses/sec on 24fps | `fps=24`, `fps_base=1` | `hold_frames=2`, motion blur off |
| Native 12fps | `fps=12`, `fps_base=1` | Retimed keys/range preserving seconds, then `hold_frames=1` |

Changing scene FPS changes the duration of existing keys. To preserve a key's time relative to frame origin, use `new_frame = origin + (old_frame-origin) * new_fps/old_fps`, including Bezier handles. Review contacts after retiming and round only at an explicit sampling boundary. The helper does not automatically retime keys or change playback FPS.

## Keyframe and hold helper

Create keyframes using `keyframe_insert`, following the [general animation workflow](../../blender-python-modeling/references/animation-and-rigging.md). `setup_clay_animation.py` accepts explicit object names and an existing active Action. It:

1. refuses linked/override objects, objects shared between scenes, NLA tracks, drivers and object/pose constraints;
2. copies a non-owned/shared Action and preserves the source via fake user;
3. reads curves for this object's assigned slot on layered Actions, or legacy F-Curves;
4. sets requested interpolation and Auto Clamped Bezier handles;
5. replaces only named `SoftClayCycle` / `SoftClayHold` modifiers;
6. adds repeat cycles and/or STEPPED sampling aligned to `scene.frame_start`.

Sampling preserves the underlying editable keys; a hold repeats the evaluated pose for each interval. Constant interpolation holds until the next key, which is a separate artistic choice. Holds do not quantize simulations, other Actions, shape-key datablocks, shader/light animation or an unselected parent. Supply and review all relevant animated datablocks in the project workflow. The helper directly supports object and unconstrained pose-bone curves; shape-key/material data need their own timing treatment.

Existing unnamed artistic Cycles/Stepped modifiers cause an explicit conflict error. Blender requires Cycles to be first, so loop setup also rejects any other artistic modifiers before editing rather than reordering them. With looping disabled, other artistic modifiers remain and need evaluation checks. The tool changes all channels of the assigned slot, so use a dedicated Action rather than a mixed production control Action if only some channels should be held.

## Rigging and topology

Use [character delivery](../../blender-python-modeling/references/character-delivery.md) for rest transforms, deform/control bone separation, normalized weights and root motion. Favor rigid parts with parent/bone attachment for toys or mechanical shapes; use skinning for bendable limbs. Place joints at functional pivots, keep edge loops and avoid bevel/decimation that disrupts articulation. Check maximum bend and opposing poses before final shading.

For constrained production rigs, bake the evaluated pose into a **new** Action at the intended sample rate using the project's validated bake workflow. Preserve the source Action, rig and constraints; use a render duplicate for constraint-free playback. The timing helper intentionally does not disable constraints or rewrite NLA/driver relationships.

## Loop contract

Define period `P` explicitly. For output frames `start…start+P−1`, key the duplicate endpoint at `start+P`, outside the output range. Match translations, orientations and deform geometry, and review velocity/acceleration at the seam. Euler values should avoid accidental ±2π discontinuities; quaternion channels require sign consistency and evaluated pose review.

For held loops, `P` must be divisible by `hold_frames`. Do not export both the first frame and identical endpoint as visible frames: that inserts a pause. The validator compares evaluated transforms/mesh vertices/bone matrices at start and end+1 and checks per-curve holds; it does not prove matching seam velocity or coherent contact motion.

## Contact and continuity review

Inspect every contact transition, most compressed/extended poses and the seam. Mark the supporting foot or contact surface; verify slide, penetration, floating parts, limb flips and accessory collisions. In simple rigid work, animate a parent Empty to avoid unintended mesh deformation. Use deformation tests rather than assuming low-poly meshes tolerate any pose.

Render a contact sheet including first/last/seam-neighbor frames, then play the full clip at the actual playback FPS. Keep scale, materials, light intensity and camera stable unless their change is intentional. The demo tests a bob/tilt loop, not a walking rig or collision solver. `continuous-action` is an optional, separate library/reference workflow rather than a dependency here.
