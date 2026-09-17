# Consistency Review

Inspect the image itself; a successful generation call is not acceptance evidence.

## Layout and projection

- exactly five controlling views for an accepted symmetric design, or six for an asymmetric/uncertain design;
- front, back, top, and bottom are always present; five-view mode has one documented canonical side, while six-view mode has both left and right;
- the combined sheet has two render rows and two matching line-art rows in the required order;
- every subject is fully visible, centered, similarly scaled, and aligned;
- every controlling view is an elevation rather than a three-quarter variation;
- directional subjects use the chosen orientation consistently;
- the background is one uniform solid isolation colour across every panel and does not create a false horizon or perspective floor;
- the background differs clearly from every colour and material touching the subject's outer silhouette; saturated magenta is preferred unless it overlaps the subject palette;
- no gradient, texture, scenery, contact shadow, or similar-coloured region obscures the subject/background boundary.

## Cross-view design

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
- observed/inferred/unknown ledger;
- any trusted scale anchor;
- unresolved cross-view conflicts.

The Blender stage should use real orthographic cameras and derive final line/wire views from one model, replacing image-generated geometry claims with model-backed evidence.
