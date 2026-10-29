# Character Delivery

Treat the editable rig, deformation mesh, baked export rig, and exported clips as separate deliverables. Do not apply transforms, collapse modifiers, rename bones, or replace actions on the editable source merely to satisfy an exporter.

## Reference and rest pose before modeling

Decide this at character design/reference generation, not when the user later asks for bones. For reusable characters and unspecified character-model requests, prepare a neutral bind-pose image, then generate the controlling multiview sheet in that same pose. A seated, crouched or action concept can define identity, palette and surface treatment, but cannot be the sole construction reference for a general-purpose deforming character. Explicit fixed-pose sculptures may stay in their requested pose without an extra animation workflow.

- **Humanoids/bipeds:** choose relaxed A-pose by default; use T-pose when the intended rig/retargeting convention calls for it. Keep arms clear of the torso, legs separated, hands open/readable, spine and pelvis neutral, feet on one plane, and slight joint bends where needed to establish bend direction. Record the selected angles rather than treating the name “A-pose” as sufficient.
- **Quadrupeds:** use a balanced four-foot standing rest, neutral back/head, readable shoulder/hip attachments, modest elbow/knee/hock bends, separated limb volumes and a relaxed tail clear of the legs. Do not force humanoid A/T poses onto animals. Occlusion in a true side view is legitimate; use front/back/top or supplemental joint close-ups to explain overlap rather than staggering a limb in one panel.
- **Other anatomies:** choose a relaxed, structurally readable rest configuration; keep wings, tentacles or accessories clear of deforming joints where practical, preserving identity and anatomy.

Record intended use, reference roles (appearance versus bind-pose construction), neutral-pose image/sheet paths, axes/ground, joint state, inferred hidden regions and review findings in the project reference record. Import/calibrate the neutral construction views using the normal reference-workspace workflow, derive mesh proportions/joint landmarks from them, and compare the actual unposed mesh before skinning. Presentation poses are subsequent rig poses or separate static variants. Do not fuse adjacent limbs, tail-to-leg contacts or clothing to skin merely because they touch in the beauty reference.

If animation is requested only after a posed model exists, inspect topology and pose suitability first. Preserve that source and derive a neutral version; revise topology/weights or rebuild affected regions when necessary. Do not assume adding bones or rotating sitting limbs makes the asset walk-ready. Existing compatible rigs/rest references may be reused; generating a new image is unnecessary for an ordinary animation edit that already has an adequate rest mesh.

## Animation mesh before binding

Distinguish the high-resolution clay sculpt from the deformation mesh. Record a target appropriate to the intended renderer, shot size, runtime/export limits and expected motion; do not prescribe one universal polygon count. A dense voxel-fused surface can be a valid sculpt, but face count, watertightness and smooth shading do not establish useful joint topology.

Before general animation binding, inspect edge flow and density around shoulders, hips, elbows, knees/hocks, wrists/ankles and any deforming face. Keep the sculpt for shape/normal detail and prepare a simpler animation mesh with joint loops where required. Avoid collapsing a bending joint to a pole or placing uncontrolled overlapping/internal surfaces there. A sculpt used directly for limited clay/stop-motion poses needs deformation and performance evidence for that limited use; do not label it production-animation-ready by default. Resolve topology before final weights/shape keys to avoid repeated skinning work.

## Bind readiness

Before binding:

- confirm mesh and armature scale, orientation, rest pose, symmetry and intended root;
- compare the rest mesh to the reviewed neutral-pose references and confirm separate limb volumes, readable joint attachments and room for the intended range of motion; a consistent sheet or correct weight sums alone do not establish this;
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

## Separate animation acceptance levels

- **Basic FK binding:** rest mesh, hierarchy/weights, neutral-pose equivalence and representative small poses checked. State this scope explicitly; finite coordinates and normalized weights alone are insufficient even here.
- **Motion validated:** inspect the intended range with actual materials: joint compression/volume, creasing, self-intersection, gaps, eye/ear/muzzle attachments, paw deformation and texture stability. IK controls, facial shapes and retargeting require their own checks when requested.
- **Locomotion validated:** review at least one complete stride, its support/swing transitions and loop boundary from side and three-quarter views. Check actual evaluated sole contact, penetration, unintended foot sliding during stance, swing clearance, weight transfer and root travel. Ankle-target error is not sole-contact evidence. For a traveling loop, compare matching phases after removing intended root translation; also inspect texture/material continuity.

Choose motion/contact tolerances for character scale and style, record them with observations, and sample critical contacts rather than just start/middle/end. A few pleasant stills or a zero-nonfinite-vertex test cannot authorize a walking/running-ready claim. Do not generate an animation solely because the user mentioned possible future use; establish the neutral mesh/basic scope and preserve the validation backlog.

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
