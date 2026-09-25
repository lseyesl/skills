# Continuity between generated frames

Keep one character identity, canvas size, camera view, crop, scale, ground line, background treatment, and image style for the sequence. Use the A.blend render for the corresponding frame's motion. Track anatomical left and right hands and feet through adjacent images; do not let limbs swap sides, disappear, or teleport.

For an in-place cycle, compare local foot travel against the Blender frames. For a translating action, compare body motion after aligning the character root, then inspect screen position separately. A repeating pose does not make a translating strip a seamless displayed loop. In a sprite sheet, retain fixed cell size and preserve the manifest's playback order; avoid scaling each character independently to fill its cell.
