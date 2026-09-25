# A.blend action library

`assets/A.blend` contains the character mesh and the imported actions. `assets/A.catalog.json` is the single source for action IDs, source FBX names, frame ranges, loop hints, reviewed phase markers, and the base clip. Read it rather than maintaining an action table here. The builder imports the base clip first and checks the other actions against its bone names.

The `loop_hint` in the catalog is a sampling hint, not a verified seamless-loop certificate. Inspect the last-to-first transition and root motion before delivering a loop. Each clip's `phase_markers` names an observed motion event, Blender frame, and priority. The `phase_frame_range` must match the clip's current range; rebuilding stops if it changed so old phase timestamps cannot silently be reused. After any source FBX update, review the phases even when its frame range stays the same.

## Render

From the repository root, run:

```bash
blender -b skills/continuous-action/assets/A.blend -t 2 \
  --python skills/continuous-action/scripts/render_keyframes.py -- \
  --action ACTION_ID_FROM_CATALOG --count 8 --view front
```

The script creates a fresh directory under `.tmp/continuous-action/` and, by default, emits one numbered transparent PNG per pose plus `manifest.json`. It selects catalog phase markers instead of equally spaced frames. If fewer images are requested than annotated phases, it favors coverage and higher-priority events. A count above the annotated phase count fails until more events are reviewed and added. The manifest records each phase name, Blender frame, source action, FBX, view, image path, and side-view reference palette. For a nearby one-off correction after viewing the poses, pass `--phase-frame PHASE=FRAME`; this retains the phase identity and records the override. Frame IDs stay the same through image generation, whose outputs go in that temporary task directory too. `--format sheet` instead emits one ordered `action-reference.png` and records each pose's region in the manifest. Use the individual PNGs when each generated frame must match a specific Blender pose; use the sheet only when a whole-action row reference is sufficient. Render again with `--view left`, `right`, or `back` only when a real request calls for that camera. No angle previews or generated images belong in the skill.

For `left` and `right`, the renderer uses bone weights to darken far-side arms, hands, legs, and feet by 15% and shift them slightly cooler, while leaving near-side limbs at their original brightness and color. The cool shift preserves the chosen luminance reduction. The guide color difference identifies limb depth only; the final generated character frames must return to the character's original palette. The manifest records the reference-only tint.

After rendering, inspect all four limbs in every full-size PNG and the sequence contact sheet. If a visible arm or leg cannot be assigned to the near or far side or its joint bend/contact cannot be read, rerender into a new temporary directory with `--far-limb-dim 0.20 --far-limb-cool-strength 1.5`, then inspect again. The first flag accepts 0.10–0.20 and the second 0–1.5. Record the checked frame IDs and any remaining occlusion in task QA notes. Contrast cannot recover a limb hidden behind the body; choose a nearby timestamp when possible and preserve the intended action phase.

Blender 4.5 uses action slots. When changing actions by script, set both `rig.animation_data.action` and `rig.animation_data.action_slot = action.slots[0]`; otherwise some imported actions appear frozen. The render script does this. If the visible character clips outside the canvas, adjust `ReferenceCamera` in A or the render script and regenerate the whole sequence with one framing choice.

## Rebuild

Run `blender -b -t 2 --python skills/continuous-action/scripts/build_action_library.py` from the repository root. The builder reads `base_clip` and each `clips.*.source_fbx` from the catalog, imports those files from `.tmp/fbx`, checks matching bone names, packs textures, saves A.blend, and updates measured frame ranges. After a rebuild, render at least one frame from each changed action and inspect the result. Rebuilding is unnecessary for ordinary image generation.

Do not substitute another action asset silently. When the requested action is absent, ask the user whether to supply a new FBX, approve an approximation from A, or stop.
