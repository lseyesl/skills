# Character Delivery

Treat the editable rig, deformation mesh, baked export rig, and exported clips as separate deliverables. Do not apply transforms, collapse modifiers, rename bones, or replace actions on the editable source merely to satisfy an exporter.

## Bind readiness

Before binding:

- confirm mesh and armature scale, orientation, rest pose, symmetry and intended root;
- resolve non-manifold geometry, duplicate vertices, accidental internal faces, and invalid normals;
- preserve modifier order, especially Mirror/Subdivision relative to Armature;
- ensure bone roll and local axes are stable before weights or animations are authored;
- decide whether clothing/accessories use deformation, rigid parenting, surface deform, or their own skeleton.

Automatic weights are a starting point. They require object selection and an active armature; inspect runtime operator options rather than assuming a UI command maps unchanged across versions. Always review high-curvature joints, fingers, face, shoulders, hips, loose garments, and overlapping shells manually or with scripted diagnostics.

## Weight validation

For each deforming mesh, inspect only vertex groups that correspond to deform bones. Report:

- unweighted vertices;
- weights whose deform-group sum is outside tolerance of 1.0;
- influences below the cleanup threshold;
- vertices exceeding the target's influence limit;
- left/right naming or symmetry mismatches;
- weights assigned to missing or non-deform bones.

Context-sensitive cleanup operators include `vertex_group_clean`, `vertex_group_normalize_all`, and `vertex_group_limit_total`. Use them only on the intended mesh in Weight Paint or Object Mode as required by the running API, and revalidate after each operation. Do not normalize non-deform control groups into the skin weights accidentally.

Test deformation poses, not only numerical sums: arms up/down, elbow/knee extremes, shoulder twist, hip flexion, wrist/ankle rotation, facial extremes, and any gameplay-critical silhouette.

## Armature and modifier contract

- Keep one explicit armature modifier per intended deform rig unless the design requires layered deformation.
- Verify modifier target, vertex-group/multi-modifier options, preserve-volume choice, and order relative to corrective modifiers.
- Export only deform bones when the target allows it; control/mechanism bones may be required for baking but not runtime.
- Avoid scale compensation tricks that produce non-unit bone/object scale at export.
- Preserve an editable rig and create a task-owned export rig if constraints, drivers, custom shapes, or unsupported bone structures must be baked away.

## Shape keys

Shape-key vertex correspondence is topology-sensitive. Do not change vertex count/order, apply incompatible modifiers, or join/split the mesh after shape keys are authored.

- Keep Basis stable and name keys deterministically.
- Validate slider ranges and combinations, not only individual keys.
- Check corrective keys with their driver poses and ensure dependencies do not form cycles.
- Confirm whether the target exports morph normals/tangents and whether animation of shape-key values is supported.

## Actions, clips, and root motion

Define ownership before baking:

- one action per clip, NLA strips, or the target exporter's supported convention;
- exact frame ranges, FPS, sampling step, loop boundary, and naming;
- root-motion source bone/object and whether motion remains in-place or extracted;
- reference/rest pose expectations and negative-frame policy.

Bake constraints/drivers to an export copy only when needed. Preserve the source actions and verify start, middle, end, contacts, loop seam, and root displacement for every clip. Avoid exporting all actions simply because an exporter offers that checkbox; filter to the intended character and clips.

## Character export acceptance

Read [export-and-packaging.md](export-and-packaging.md), then verify:

- mesh, skeleton and root have the intended scale, axes and pivots;
- no unweighted vertices or excess influences remain;
- rest pose, bone hierarchy, bone axes and deform-only filtering survive;
- modifier evaluation and shape keys survive without topology drift;
- animation names, ranges, FPS, root motion and loop behavior survive;
- materials, UVs, normals, tangents and transparency match the consumer;
- each LOD remains bound to the compatible skeleton where required;
- the exported character is reopened in a disposable scene or tested in the destination engine.
