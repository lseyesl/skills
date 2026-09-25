# Validate generated action images

Use the Blender PNG with the same frame ID as the expected motion for each generated image. Inspect images in playback order, then inspect the last-to-first transition for loops.

Before generating character images from side-view references, inspect every Blender PNG at full size and the sequence contact sheet. For each frame, trace both arms (shoulder → hand) and both legs (hip → foot), and identify their near/far side, bend, swing, and foot contact. Record a `pass` or the ambiguous frame IDs in task QA notes. When visible limbs are still ambiguous, increase the far-side contrast within the renderer's permitted range and inspect the rerender. A fully occluded limb cannot be validated from contrast; choose another timestamp when possible or mark that limb unverified. Do not silently treat a four-limb pose as known when it is not visible.

1. **Frame match:** facing, head direction, named left/right limbs, stance/flight, hand and foot positions, body lean, and crop correspond to that Blender frame. Do not treat a visually attractive image as correct when it changes the action.
2. **Contact and weight:** a foot planted in the Blender frame remains planted in the generated image; a jump's lift, apex, and landing do not become another movement. For walking and running, check contact alternation and both arms through the cycle.
3. **Identity:** face, hair, clothes, colours, proportions, props, camera, and lighting stay stable across adjacent generated images unless the request intentionally changes them.
   In side views, confirm the Blender reference makes the near/far arms and legs distinguishable (near side at normal brightness; far side about 10%–20% darker with a cool cue). Confirm final generated frames use the character's original limb colors rather than copying the reference's diagnostic shading.
4. **Timing and seam:** image order follows `manifest.json`. For a cyclic clip, compare the final image with the next first image for body motion and root displacement. A duplicate pose can cause a pause; a root reset can cause a jump. Mark the loop unverified if either is unresolved.

Record a failure with its frame ID, the matching Blender PNG, the observed difference, and the correction attempted. Regenerate the affected image with its Blender PNG as the image reference and the same appearance instructions. If a defect comes from the source clip or a missing action, ask the user how to proceed instead of inventing a new motion source.
