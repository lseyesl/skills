---
name: concept-multiview-sheet
description: Turn a single-view concept image, sketch, product design, vehicle, prop, or character reference into scoped orthographic construction views or a full inferred five- or six-view concept sheet with matching line art. Use when hidden views must be designed consistently for later modeling or visualization. Do not use to claim measured geometry, recover real dimensions, edit an existing 3D model, or produce a true topology wireframe.
---

# Concept Multiview Sheet

Expand one visible design into a coherent inferred design sheet. Preserve observed evidence, make hidden-view assumptions explicit, and never present generated geometry or dimensions as recovered facts.

For reconstruction from a photograph or existing design, use the [source-fidelity workflow](references/source-fidelity.md) first. Faithful preservation of observed identity is the default; design exploration is a separate user-selected goal. Source fidelity and cross-view consistency are independent gates: either can fail while the other looks convincing.

## Boundaries

- This is generative design completion, not photogrammetry or geometric reconstruction.
- A single image underdetermines depth, back-side construction, attachments, symmetry, and scale. Label these as inferred or unknown.
- Keep the evidence labels explicit: **Observed** comes from the source, **Inferred** completes hidden design, and **Unknown** remains unresolved.
- “Line art” means clean design/technical contours and panel lines. A true topology wireframe must come from a 3D model; hand that request to `blender-python-modeling`.
- If the user needs manufacturing, assembly, fit, or dimensionally accurate views, require measurements/CAD/multiple calibrated views instead of inventing them.
- Use the built-in image generation tool by default. Use a CLI/API fallback only when the user explicitly requests or confirms it.

## Choose the requested deliverable

For a construction handoff, first identify which view would change an actual modeling decision. Reuse source views that already constrain the region, generate only the missing controlling views, and review the selected set for source fidelity and cross-view consistency. Hand off separate views, anchors and explicit allowed regions. Make presentation line art only when requested or needed to clarify a constraint. If an existing coherent blockout can explain hidden geometry, use its orthographic renders as model-derived evidence and keep their provenance distinct from the source.

### Character accessories in construction views

Apply this decision to the first neutral-pose image and carry it through all later views, detail crops and line art. Inventory accessories visible in the source or explicitly requested. Record count, side, attachment and which body landmarks each covers. Character role, style or an unseen back is insufficient evidence to invent equipment. With no evidenced or requested prop, generate the character alone.

- Keep integral costume features and unobtrusive identity details in place, including a tied sash, its observed short ends and a hair tie. Preserve their observed length and number. An unclear rear attachment does not justify extra trailing ribbons.
- For a detachable item that hides the hands, face, neck, torso outline or limb gaps in any controlling view, use a character-only construction set and, when the item belongs in the deliverable, generate its own isolated reference from the original or an identified crop. Keep the same item configuration in every panel of each set. Preserve the assembled source or an assembly detail with the side, relative scale, overlap and attachment landmarks needed to position it later. Label newly exposed body surfaces as inferred.
- If a defining garment is integral, or the requested pose specifically shows the item worn or held, retain the assembled view. Add a scoped unobstructed body or attachment detail only where modeling needs it. Label the subject and allowed regions of each file; an item sheet controls the item, and an assembled reference controls placement.

Use the [accessory prompt clauses](references/prompt-recipes.md#accessory-scope-for-character-construction) and review the actual panels for additions, omissions and occlusion [before modeling](references/pre-model-review.md).

### Follow-up from Blender

When modeling or refinement reveals an unclear region, accept the original image, approved views, region and specific question (for example, where a strap attaches behind the shoulder). Generate the missing direction or detail crop at the established pose, orientation and anchors. Return the actual image and its generation record with hashed outputs so the specific Blender finding can be reopened and tested. Preserve approved panels. Compare the supplement with the original and adjoining regions, label hidden construction as inferred, and return its view, crop, provenance and reviewed scope. Blender resumes the affected region and refreshes its comparisons. Independent regions may proceed while the supplement is unresolved.

## Default deliverable for a full design sheet

Choose view count from symmetry before generation:

- For a bilaterally symmetric design, create five controlling views: front, one canonical side, back, top, and bottom.
- For an asymmetric or uncertain design, create six controlling views: front, back, left, right, top, and bottom.
- Add a three-quarter volume reference only when requested or materially useful. It is not a controlling dimensional view.

Use a 4-row by 3-column layout rather than a very wide ten- or twelve-column strip.

Symmetric five-view layout:

| | Column 1 | Column 2 | Column 3 |
|---|---|---|---|
| Render row 1 | front | canonical side | back |
| Render row 2 | top | bottom | optional three-quarter or blank |
| Line row 1 | front | canonical side | back |
| Line row 2 | top | bottom | optional matching three-quarter or blank |

Asymmetric six-view layout:

| | Column 1 | Column 2 | Column 3 |
|---|---|---|---|
| Render row 1 | front | left | right |
| Render row 2 | back | top | bottom |
| Line row 1 | front | left | right |
| Line row 2 | back | top | bottom |

Keep the subject centered, fully visible, at one common orthographic scale, and aligned by stable semantic anchors across panels. Do not normalize each panel independently to its own bounding box when an appendage, weapon, tail, or other movable part changes the extent. Use a uniform solid isolation background that clearly contrasts with the subject: default to saturated magenta, but choose another high-contrast chroma colour when magenta appears prominently in the model. The background must remain distinct from every outer-edge colour and material so the silhouette is easy to identify or mask. Use orthographic-looking projection, subdued studio lighting on renders, and high-contrast line art below. Omit dimensions, branding, watermarks, decorative scenery, and prose unless requested.

For a directional subject, establish one canonical orientation before generation, for example “side and top views point nose-left, tail-right.” For a character or articulated object, read [references/pose-and-configuration-normalization.md](references/pose-and-configuration-normalization.md) and lock one modeling pose or mechanical configuration before generation. Every controlling view must depict that same state as if only the orthographic camera moved; never re-pose a limb, joint, tail, wing, control surface, door, or tool to improve visibility in one panel.

Choose the pose for its downstream use, not merely for cross-view consistency. For reusable/riggable character modeling (including unspecified character-model requests), first prepare and review a neutral bind-pose design image, then generate its multiviews. Use humanoid A/T pose or quadruped four-foot standing rest as anatomy requires. Preserve a seated/action original separately as appearance evidence; a perfectly consistent seated sheet still does not serve as the neutral construction sheet. Honor explicitly fixed-pose/static deliverables without forcing a second pose.

Before detailed modeling, apply the [pre-model review](references/pre-model-review.md) to the actual generated panels and record `passed`, `partial`, or `blocked` with source hashes, controlling regions and conflicts. A partial set authorizes only its explicit allowed regions; repair critical conflicts before shaping affected geometry. A later model render cannot certify an omitted pre-model review.

Treat normalization readiness explicitly:

- **Preview-only:** small pose, configuration, scale, or anchor drift may remain if disclosed.
- **Blender-blockout-ready:** pose/configuration, axes, ground or origin, semantic anchors, and orthographic scale must pass the consistency review. If they do not, deliver the sheet only as design evidence.

## Workflow

1. **Inspect the input.** Treat the source as a reference image, not an edit target. If it exists only as a local file, load it with `view_image` before generation. Record whether it is front, side, rear, top, or three-quarter/perspective.
2. **Separate evidence from invention.** Read [references/inference-contract.md](references/inference-contract.md) and [source fidelity](references/source-fidelity.md). Record the original hashes and critical observed identity/shape/count/attachment invariants before generation. Distinguish reconstruction from deliberate redesign; never silently substitute a generic subject.
3. **Choose view count and fidelity.** For construction, choose the smallest set that constrains the required regions. For a full sheet, use five views only when bilateral symmetry is supported or explicitly chosen. Use six for other full sheets. Default to one coherent interpretation. Generate alternatives only when hidden structure has multiple materially different plausible solutions or the user asks for variants.
4. **Generate the rendered view set.** Use the input image as a design reference. Before prompting, inspect the subject palette and choose a single solid isolation-background colour. Prefer saturated magenta; if it overlaps the subject palette, choose a strongly separated colour in both hue and value. Keep controlling views coherent. For a full sheet, generate the five or six views together in a 2×3 render sheet. For construction, generate the missing views against the trusted anchors and camera conventions. Apply [references/prompt-recipes.md](references/prompt-recipes.md).

   For an image-then-model task, do this before detailed geometry; later model renders are verification, not a substitute for omitted design references. State projection expectations explicitly: a vertical flower disk, wheel or shield reads edge-on from top/bottom; broad upward-facing surfaces read broadly from above and foreshorten from the side. Labeling a panel TOP does not make it a top projection. Review these constraints before generating line art.
5. **Review before line art.** First compare actual generated regions with the original source and fill the [source-fidelity receipt](assets/source-fidelity-review-template.json). Then separately check part count, placement, silhouette, proportions, colour blocking, symmetry, orientation, pose/configuration, anchor alignment, scale and projection across views. A coherent redesign is not a fidelity pass; a faithful-looking front is not a whole-sheet pass. Regenerate or make one targeted edit if a controlling inconsistency remains.
6. **Create the combined sheet if requested.** Preserve approved render panels as immutable sources. Generate matching line art separately and assemble the 4×3 layout without regenerating the accepted render rows. If line art drifts, keep it supplemental or derive contours from a reviewed blockout. Do not ask for a dense fake topology mesh.
7. **Validate.** Apply the applicable checks in [references/consistency-review.md](references/consistency-review.md) and use [pre-model review](references/pre-model-review.md) for the construction handoff. Iterate with one explicit correction at a time; stop when further image edits cause component drift rather than improvement.
8. **Deliver and hand off.** For preview-only work, display the result inline. For project work, preserve original/generated images, generation-record, source-fidelity review and multiview review. When modeling follows, provide separate uncropped views (or exact crop regions), labels, shared scale/origin, anchors, per-region reliability and conflicts. Report source fidelity separately from consistency and calibration. The Blender Skill establishes and visually checks its imported workspace before geometry; a generated sheet alone is not a calibrated setup.

## Escalate to a model-backed sheet

Use `blender-python-modeling` after this Skill when the user needs:

- strict cross-view silhouette consistency;
- a real topology wireframe;
- controllable dimensions or animation-ready geometry;
- repeated revisions without visual drift;
- exportable `.blend`, GLB, FBX, OBJ, or STL output.

In that handoff, treat the generated sheet as inferred design evidence. Build a normalized blockout, render actual orthographic cameras, compare silhouettes, and replace image-generated line art with contours or wireframe derived from the same model.

Do not force a model to reproduce an isolated AI depiction error. Pass observed/inferred/unknown distinctions and contradictory regions to `blender-python-modeling`, where source evidence and coherent anatomy/mechanics guide local corrections. If materially different plausible designs cannot be distinguished, request human judgment on that choice; otherwise record the smallest reasoned correction and continue.

## Completion report

Report:

- source-view classification;
- final sheet and render-only paths when saved;
- canonical orientation and symmetry assumption;
- normalized pose or mechanical configuration, coordinate convention, and alignment anchors;
- which views control which regions and which side is canonical;
- the most consequential inferred features and unresolved unknowns;
- whether the line art is image-generated or model-derived;
- whether the result is preview-only or Blender-blockout-ready, including any normalization conflicts that prevent the latter label.
