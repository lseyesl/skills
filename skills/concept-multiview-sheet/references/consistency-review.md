# Consistency Review

Inspect the image itself; a successful generation call is not acceptance evidence.

For modeling handoff, complete the [pre-model review and scoped receipt](pre-model-review.md) before detailed geometry. Review every panel and explicitly classify controlling/supplemental/rejected views. Pose consistency, imported-image calibration, model fidelity and animation readiness are separate decisions. Critical unresolved regions cannot be approved through a generic whole-sheet pass.

## Layout and projection

- exactly five controlling views for an accepted symmetric design, or six for an asymmetric/uncertain design;
- front, back, top, and bottom are always present; five-view mode has one documented canonical side, while six-view mode has both left and right;
- the combined sheet has two render rows and two matching line-art rows in the required order;
- every subject is fully visible, centered, and aligned;
- every panel uses one common orthographic scale and semantic anchors; apparent scale is not independently fitted to each panel's bounding box;
- every controlling view is an elevation rather than a three-quarter variation;
- directional subjects use the chosen orientation consistently;
- the background is one uniform solid isolation colour across every panel and does not create a false horizon or perspective floor;
- the background differs clearly from every colour and material touching the subject's outer silhouette; saturated magenta is preferred unless it overlaps the subject palette;
- no gradient, texture, scenery, contact shadow, or similar-coloured region obscures the subject/background boundary.

## Cross-view design

Check projection using each part's surface normal and expected occlusion. A
vertical disk should be thin from above/below; an upward-facing leaf or tabletop
should expose its broad surface from above. A face-on disk in a TOP panel or
camera-facing leaves in every panel indicate reposing or incorrect projection.
An underside view must respect occlusion by the base/saucer/support. Preserve a
common orthographic scale rather than enlarging top/bottom panels to fill them.
If adding line art rescales or changes the render panels, retain the render-only
source and mark the combined sheet preview-only; do not claim exact preservation.

Compare views component by component:

- primary body length/width/height ratios are plausible together;
- repeated-part count agrees;
- attachments occupy compatible longitudinal, lateral, and vertical positions;
- windows/openings/panels continue logically around the form;
- colour and material boundaries align;
- symmetry and intentional asymmetry are preserved;
- top, bottom, and back details reconcile with the corresponding attachment positions visible in other views;
- no panel invents a second design language, extra limb, different tail, changed roof, or missing mechanism.

Prefer the original supplied view as the controlling evidence for visible features. For hidden features, prefer the recorded inference ledger rather than whichever generated panel looks most detailed.

## Pose and configuration normalization

First check suitability for the declared use: a reusable character requires the reviewed neutral construction pose, with separate limb volumes and readable joint attachments across the view set. An internally consistent seated/action sheet is insufficient for this purpose. A fixed-pose sculpture may retain its specified pose. Neutral pose and multiview consistency do not certify a deformation-ready mesh.

For a character or articulated subject, compare the views as projections of one frozen state:

- head, spine, pelvis, shoulder, elbow, wrist, hand, hip, knee, ankle, foot, tail, and wing states agree wherever applicable;
- left/right joint relationships remain intentional and do not change merely to expose a component;
- feet or other supports share the recorded ground plane, while the root/centerline and landmark heights remain compatible across elevations;
- hair, clothing, soft appendages, held props, and accessories use one recorded resting state rather than a different convenient silhouette per panel;
- steering, suspension, doors, hatches, hinges, pistons, robot joints, control surfaces, and deployable tools remain in the recorded mechanical configuration;
- an occluded part stays occluded when geometry requires it; visibility is not evidence that the pose was preserved.

Any disagreement that changes a joint center, attachment origin, rest silhouette, or inferred volume blocks the **Blender-blockout-ready** label. The result may still be delivered as **preview-only** design evidence with the conflict disclosed.

## Render-to-line correspondence

- each line-art silhouette matches its corresponding render in the same grid position two rows above;
- component counts and outlines match one-for-one;
- line art is readable against the background;
- panel lines describe the visible design without pretending to reveal hidden interiors;
- there is no dense fake quad topology unless a 3D model supplied it.

## Severity and iteration

Repair before delivery when a mismatch changes identity, silhouette, function, part count, attachment position, or modeling interpretation. Minor highlights, tiny fasteners, and lighting differences can remain if they do not alter structure.

Make one targeted correction, then re-check the whole sheet. Stop image-only iteration when:

- fixing one panel repeatedly breaks another;
- orthographic views remain perspective-distorted;
- component positions cannot be reconciled;
- line art repeatedly diverges from the renders;
- the user needs actual topology or dimensional consistency.

At that point, preserve the best concept sheet, document the unresolved ambiguity, and recommend a Blender blockout.

## Handoff package

For later modeling, provide:

- original source image;
- approved five- or six-view render-only sheet;
- approved combined render/line sheet;
- canonical orientation;
- normalized pose or mechanical configuration, coordinate convention, ground/origin, and semantic alignment anchors;
- observed/inferred/unknown ledger;
- any trusted scale anchor;
- unresolved cross-view conflicts, including any pose/configuration drift that prevents Blender readiness.

The Blender stage should use real orthographic cameras and derive final line/wire views from one model, replacing image-generated geometry claims with model-backed evidence.
