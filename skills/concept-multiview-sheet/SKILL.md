---
name: concept-multiview-sheet
description: Turn a single-view concept image, sketch, product design, vehicle, prop, or character reference into an inferred five-view symmetric or six-view asymmetric orthographic concept sheet with corresponding technical line art. Use when hidden views must be designed consistently for later modeling or visualization. Do not use to claim measured geometry, recover real dimensions, edit an existing 3D model, or produce a true topology wireframe.
---

# Concept Multiview Sheet

Expand one visible design into a coherent inferred design sheet. Preserve observed evidence, make hidden-view assumptions explicit, and never present generated geometry or dimensions as recovered facts.

## Boundaries

- This is generative design completion, not photogrammetry or geometric reconstruction.
- A single image underdetermines depth, back-side construction, attachments, symmetry, and scale. Label these as inferred or unknown.
- Keep the evidence labels explicit: **Observed** comes from the source, **Inferred** completes hidden design, and **Unknown** remains unresolved.
- “Line art” means clean design/technical contours and panel lines. A true topology wireframe must come from a 3D model; hand that request to `blender-python-modeling`.
- If the user needs manufacturing, assembly, fit, or dimensionally accurate views, require measurements/CAD/multiple calibrated views instead of inventing them.
- Use the built-in image generation tool by default. Use a CLI/API fallback only when the user explicitly requests or confirms it.

## Default deliverable

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

Treat normalization readiness explicitly:

- **Preview-only:** small pose, configuration, scale, or anchor drift may remain if disclosed.
- **Blender-blockout-ready:** pose/configuration, axes, ground or origin, semantic anchors, and orthographic scale must pass the consistency review. If they do not, deliver the sheet only as design evidence.

## Workflow

1. **Inspect the input.** Treat the source as a reference image, not an edit target. If it exists only as a local file, load it with `view_image` before generation. Record whether it is front, side, rear, top, or three-quarter/perspective.
2. **Separate evidence from invention.** Read [references/inference-contract.md](references/inference-contract.md). Summarize observed features, inferred hidden features, unknowns, canonical orientation, symmetry, repeated-part counts, pose or configuration state, semantic alignment anchors, and invariants.
3. **Choose view count and fidelity.** Use five views only when bilateral symmetry is supported or explicitly chosen; otherwise use six. Default to one coherent interpretation. Generate alternatives only when hidden structure has multiple materially different plausible solutions or the user asks for variants.
4. **Generate the rendered view set.** Use the input image as a design reference. Before prompting, inspect the subject palette and choose a single solid isolation-background colour. Prefer saturated magenta; if it overlaps the subject palette, choose a strongly separated colour in both hue and value. Ask for all five or six orthographic-looking views in one 2×3 render sheet so the model sees them together. Apply [references/prompt-recipes.md](references/prompt-recipes.md).

   For an image-then-model task, do this before detailed geometry; later model renders are verification, not a substitute for omitted design references. State projection expectations explicitly: a vertical flower disk, wheel or shield reads edge-on from top/bottom; broad upward-facing surfaces read broadly from above and foreshorten from the side. Labeling a panel TOP does not make it a top projection. Review these constraints before generating line art.
5. **Review before line art.** Check part count, placement, silhouette, proportions, colour blocking, symmetry, orientation, pose/configuration, anchor alignment, common orthographic scale, and whether any panel is actually three-quarter. Regenerate or make one targeted edit if a controlling inconsistency remains.
6. **Create the combined sheet.** Edit the approved 2×3 render sheet into the 4×3 layout. Preserve the first two rows exactly and add matching line-art rows. Do not ask for a dense fake topology mesh.
7. **Validate.** Apply [references/consistency-review.md](references/consistency-review.md). Iterate with one explicit correction at a time; stop when further image edits cause component drift rather than improvement.
8. **Deliver and hand off.** For preview-only work, display the result inline. For project work, copy the reviewed image into the workspace and preserve the render-only source when useful. When Blender modeling follows, provide separate uncropped view images (or exact crop regions), view/axis labels, shared scale/origin and semantic alignment anchors, plus per-region reliability and unresolved conflicts. Report final paths, prompt summary, generation mode, and important inferred/unknown structure. The Blender Skill establishes and visually checks its imported reference workspace before geometry; a generated sheet alone is not a calibrated Blender reference setup.

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
- whether five or six controlling views were used and which side is canonical;
- the most consequential inferred features and unresolved unknowns;
- whether the line art is image-generated or model-derived;
- whether the result is preview-only or Blender-blockout-ready, including any normalization conflicts that prevent the latter label.
