# Pre-model multiview review

Use before handing generated construction views to Blender. Inspect actual images before detailed geometry; neither successful generation, a completed JSON form, nor later model renders can retroactively certify this step.

## Review in this order

1. **Pose suitability:** intended use, head-to-spine orientation (a camera-facing head can contradict a neutral torso), shoulder/pelvis state, joint bends, limb separation and tail/wing clearance. Static sculptures retain their specified pose.
2. **Axes and projection:** establish anatomical left/right, forward/up and camera directions from geometry, not labels. Check strict front/side/top/bottom projection and physically correct occlusion. Never re-pose a hidden limb merely to show it.
3. **Scale and correspondence:** align ground/origin, centerline and shared scale. Compare joint centres, head/eye/nose heights, body length/depth, limb widths and attachments in the applicable views. Use regional overlays or a landmark table; choose tolerances appropriate to the design, not a universal pixel threshold. Record uniform scale corrections; do not warp panels to conceal pose or anatomy conflicts.
4. **Identity, structure and colour:** repeated counts, asymmetry, connections, grey/white regions, ear fronts/backs, chest/belly, paw tops/soles and appendage tips. Prefer source evidence and coherent anatomy when resolving an AI error; retain inferred/unknown labels.
5. **Line-art correspondence:** approve the rendered views first. Preserve those source panels as immutable assets; create line art separately and assemble the layout without regenerating approved render rows. If it drifts, keep it supplemental or derive actual contours from a reviewed blockout.

Review every generated panel, including rejected/supplemental views; record which regions and dimensions each trusted view controls. A few individually attractive panels do not establish one coherent 3D configuration.

## Decision and construction scope

- **passed:** the declared construction scope is consistent and has usable controlling evidence.
- **partial:** only explicit regions may be modeled. Name allowed and blocked regions, select trusted views, and disclose unresolved conflicts. A view that is merely supplemental must not become a dimensional guide silently.
- **blocked:** an unresolved global pose/axis/projection conflict, or insufficient evidence for the requested region. Repair the source first. Independent, well-constrained work can continue only under a separate explicit partial scope.

Use hierarchical region names consistently, such as `head.skull`, `head.muzzle`, `body`, `tail`; allowing `head` also includes its children. Do not claim that a parent is approved while its muzzle remains blocked. When a conflict is resolved by choosing a controlling source, record the actual selected evidence, dimension authority and reasoning. Do not resolve an identity-changing ambiguity by relabeling it a harmless simplification; use the normal human-judgment policy when needed.

When image edits repeatedly break previously valid panels, use a cheap diagnostic blockout and real orthographic cameras to test whether one anatomy/configuration can explain the views. Diagnostic geometry may investigate blocked regions, but it is not an accepted detailed build and cannot certify the original images. Revise/review the design constraints before promoting those regions to construction authority.

## Handoff receipt

Keep `multiview-review.json` beside the project references. Minimum two-guide example below; a generated five/six-view set must list the other panels with their roles/findings too. Replace hashes and findings only after actual inspection:

```json
{
  "schema_version": 1,
  "purpose": "reusable quadruped for later rigging",
  "pose": "four-foot balanced stand; head aligned with spine; slight elbow/hock bends; relaxed tail clear of back/legs",
  "readiness": "passed",
  "checks": {
    "pose": {"status": "passed", "finding": "Record the observed joint/head state across views"},
    "proportions": {"status": "passed", "finding": "Record common scale, ground and landmark comparisons"},
    "projection": {"status": "passed", "finding": "Record actual camera direction and occlusion checks"},
    "structure": {"status": "passed", "finding": "Record counts, attachments and inferred hidden anatomy"},
    "appearance": {"status": "passed", "finding": "Record mask, ear-back, underside and asymmetry checks"},
    "axes": {"status": "passed", "finding": "Forward -Y, up +Z; verified nose-left source is +X right view"}
  },
  "allowed_regions": ["head", "body", "tail"],
  "blocked_regions": [],
  "conflicts": [],
  "views": {
    "front": {"image": "reference/front.png", "sha256": "actual-file-sha256", "role": "controlling", "controls": ["head", "body"], "finding": "Record frontal landmark/shape observations"},
    "right": {"image": "reference/right.png", "sha256": "actual-file-sha256", "role": "controlling", "controls": ["head", "body", "tail"], "finding": "Record sagittal profile and joints"}
  },
  "review_artifacts": ["review/reference-landmarks.png"]
}
```

View roles are `controlling`, `supplemental`, or `rejected`. Each conflict records `severity` (`critical`/`local`), `status` (`resolved`/`unresolved`), `finding`, affected `regions`, and a `resolution` when resolved. For a partial review, `build_regions` in the Blender reference config must explicitly select an allowed subset. Critical unresolved regions must be blocked; global failures use `blocked` readiness.

Image/artifact paths above resolve relative to the review file. Guide paths resolve relative to the Blender config. With `blender-python-modeling` installed, `scripts/reference_review.py <reference-setup.json>` checks source hashes, evidence declarations, view roles and permitted scope. Its workspace helper applies this before importing multiple guides. The checker does not judge image contents, decide anatomy or prove that a builder used the declared scope honestly; inspect the actual reference and mesh.
