# Prompt Recipes

Use the `stylized-concept` image-generation category unless the source clearly requires product rendering, scientific illustration, or another established category. Keep prompts compact enough that invariants remain prominent.

## Pass 1A: symmetric five-view renders

```text
Use case: stylized-concept
Asset type: modeling reference / orthographic concept sheet
Primary request: infer a coherent five-view bilaterally symmetric design from the supplied single-view reference
Input image: design reference; preserve visible identity, silhouette language, components, palette, materials, and style
Subject: <short subject description>
Observed invariants: <visible facts that must remain>
Inferred hidden design: <approved assumptions only>
Unknowns: keep visually simple and plausible; do not imply measured certainty
Symmetry: bilateral; the <left/right> side is canonical and the unseen opposite side mirrors it
Canonical orientation: FRONT faces viewer; SIDE, TOP, and BOTTOM point <direction>
Composition: clean 2-row by 3-column render sheet. Row 1: FRONT, canonical SIDE, BACK. Row 2: TOP, BOTTOM, <optional THREE-QUARTER or intentionally empty isolation-colour panel>. Same design, common scale, centered, fully visible, aligned
Projection: strict orthographic-looking elevation views; no three-quarter angle, lens distortion, foreshortening, or perspective floor
Style: polished <source style> design render, clean isolated reference presentation
Background: uniform solid <isolation colour> background, default saturated magenta. If magenta occurs prominently in the subject, use another colour strongly separated from all subject edge colours in both hue and value. Keep exactly the same background colour in every panel
Constraints: identical part count, placement, proportion family, symmetry, colour blocks, attachments, and surface details across views; crisp unambiguous subject/background boundary around the complete silhouette
Avoid: background colours close to the subject, gradients, textures, scenery, floor or horizon, contact shadows that merge into the silhouette, dimensions, grid units, dramatic shadows, labels beyond optional short view names, prose, logos, watermark, cutaway, exploded view, cropped subject
```

## Pass 1B: asymmetric six-view renders

```text
Use case: stylized-concept
Asset type: modeling reference / orthographic concept sheet
Primary request: infer a coherent complete six-view asymmetric design from the supplied single-view reference
Input image: design reference; preserve visible identity, silhouette language, components, palette, materials, and style
Subject: <short subject description>
Observed invariants: <visible facts that must remain>
Inferred hidden design: <approved assumptions only>
Known asymmetry: <side-specific components and placements>
Unknowns: keep visually simple and plausible; do not imply measured certainty
Canonical orientation: FRONT faces viewer; LEFT and RIGHT mean the subject's own sides; TOP and BOTTOM point <direction>
Composition: clean 2-row by 3-column render sheet. Row 1: FRONT, LEFT, RIGHT. Row 2: BACK, TOP, BOTTOM. Same design, common scale, centered, fully visible, aligned
Projection: strict orthographic-looking elevation views; no three-quarter angle, lens distortion, foreshortening, or perspective floor
Style: polished <source style> design render, clean isolated reference presentation
Background: uniform solid <isolation colour> background, default saturated magenta. If magenta occurs prominently in the subject, use another colour strongly separated from all subject edge colours in both hue and value. Keep exactly the same background colour in every panel
Constraints: preserve every side-specific component while keeping shared structure, proportions, colour blocks, attachments, and surface language consistent; crisp unambiguous subject/background boundary around the complete silhouette
Avoid: background colours close to the subject, gradients, textures, scenery, floor or horizon, contact shadows that merge into the silhouette, mirrored-away asymmetry, dimensions, grid units, dramatic shadows, prose, logos, watermark, cutaway, exploded view, cropped subject
```

For a character, replace directional language with a neutral pose and consistent limb/accessory visibility. Preserve real left/right costume or anatomy differences. For an object whose front/back is ambiguous, define the chosen front in the inference record.

## Pass 2: combined render and line-art sheet

Use the approved 2×3 render sheet as the edit target:

```text
Preserve the first two render rows exactly: same five or six rendered views, design, scale, alignment, colours, materials, component positions, asymmetry, and silhouettes.

Expand the canvas into a clean 4-row by 3-column sheet. Add two line-art rows that repeat the exact same panel order as the render rows.

For the symmetric five-view layout: render rows are FRONT/SIDE/BACK then TOP/BOTTOM/optional THREE-QUARTER or blank; line rows repeat that order.

For the asymmetric six-view layout: render rows are FRONT/LEFT/RIGHT then BACK/TOP/BOTTOM; line rows repeat that order.

Line-art requirements: crisp lines with strong contrast against the same solid isolation background used by the render rows; strong readable outer silhouette; major component contours, joints, panel boundaries, openings, and centerlines; restrained construction lines only where visually supported. Match every upper-row component one-for-one. If dark lines do not contrast sufficiently with the chosen isolation colour, use light lines instead.

Do not invent dense polygon topology, hidden internals, dimensions, prose, extra perspective views, scenery, shadows, logos, or watermark. Keep every view centered, fully visible, equally scaled, evenly spaced, and aligned.
```

If the edit changes either rendered row, restore the render-only sheet and retry with one correction rather than accumulating edits.

## Targeted repair prompts

Change one failure at a time:

- “Keep everything unchanged; make the side and top views point nose-left and tail-right.”
- “Keep everything unchanged; restore the missing BOTTOM view as a true upward-looking orthographic elevation.”
- “Keep all shared geometry unchanged; restore the left-only attachment in LEFT view and remove it from RIGHT view.”
- “Keep all silhouettes unchanged; restore exactly two side thrusters in every applicable view.”
- “Keep both render rows unchanged; increase only the line-art-row contrast.”
- “Keep the subject, views, layout, lighting, and all design details unchanged; replace only the complete background with one uniform saturated magenta isolation colour, with a crisp boundary and no gradient, floor, horizon, or contact shadow.”
- “Replace only the SIDE render with a true flat side elevation; remove visible top/front surfaces.”
- “Align all panels to the same bounding-box scale without changing design details.”

Avoid broad prompts such as “make it more consistent”; name the mismatched component and the controlling view.

## Alternative interpretations

When hidden structure materially affects the design, create separate complete sheets rather than mixing alternatives inside one sheet:

- Variant A: symmetric continuation;
- Variant B: function-led alternative;
- optional short note explaining the assumption changed.

Each variant must remain internally consistent. Do not use `n` variants as a substitute for distinct prompts when the hidden-design assumptions differ.
