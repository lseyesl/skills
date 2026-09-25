# Pose and Configuration Normalization

Use this contract when a generated sheet is intended to guide Blender blockout. The controlling views must behave like orthographic camera renders of one frozen subject, even though image generation cannot guarantee true geometric reconstruction.

## Choose one subject state

Record the state before generation instead of accepting whichever pose each panel invents.

For characters:

- use the pose requested by the user; otherwise prefer a relaxed, symmetric modeling A-pose for a humanoid character;
- record head direction and tilt, spine and pelvis neutrality, arm elevation, elbow and wrist state, hand shape, leg spacing, knee state, ankle/foot direction, and ground contact;
- record tail, wing, ear, hair, garment, handheld prop, and wearable-accessory state when they affect silhouette or attachment placement;
- preserve observed anatomical or costume asymmetry without introducing pose asymmetry merely to reveal details.

For articulated props, vehicles, and machines:

- record steering, suspension, hinge, piston, wheel, door, hatch, control-surface, robot-joint, weapon, and deployable-tool state where applicable;
- use the state requested or clearly observed; otherwise prefer a neutral closed or zero configuration suitable for blockout;
- expose hidden construction in a separate non-controlling detail view, not by changing the configuration of one orthographic panel.

A truly rigid subject has no pose to normalize, but still needs coordinate, origin, scale, and alignment normalization.

## Lock the reference frame

Record:

- canonical forward, up, and subject-left/right directions;
- a stable origin or ground-contact rule;
- a centerline or root reference;
- semantic landmarks that can be compared across views, such as foot sole, knee, pelvis, shoulder, eye line, wheel axle, hinge center, roof line, or attachment origin;
- one common orthographic scale for every controlling panel.

Treat every controlling panel as a camera change around that fixed state. Do not independently rotate the subject, bend parts, redistribute weight, change soft-part motion, or fit each panel to its own silhouette bounds.

## Source-pose conversion

When the source is dynamic, foreshortened, seated, partially occluded, or strongly perspective-distorted, a normalized modeling pose is inferred rather than observed. Preserve identity, anatomy, outfit construction, attachment locations, and proportions as far as the evidence supports, but record the pose conversion under **Inferred** and keep uncertain joint or hidden-body structure under **Unknown**.

Do not claim that normalization recovers exact joint centers, hidden anatomy, real depth, or measurements from a single image.

## Readiness decision

Label a sheet **Blender-blockout-ready** only when all controlling views agree on:

- the recorded pose or mechanical configuration;
- root/origin, ground contact, centerline, and semantic landmarks;
- canonical axes and left/right meaning;
- common orthographic scale;
- attachment origins and major rest silhouettes.

If a mismatch would force a modeler to choose between contradictory joint centers, attachment positions, silhouettes, or volumes, label the sheet **preview-only**, list the conflict, and use it as design evidence rather than a tracing authority.
