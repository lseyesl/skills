# Reference Fidelity and Completion Gates

Use this workflow for any model reconstructed from concept art, turnarounds,
photos, diagrams, or AI-generated multi-view sheets. A silhouette match proves
only the outer envelope. It does not prove that the visible design has been
modeled at the requested level of detail.

## Source acceptance and optimized delivery are separate

First review the reconstructed source against the original images, local signature features and structural requirements. Final consumer polygon limits are not a reason to omit those features. Freeze the reviewed source, ledger and evidence with content hashes; optimization uses a separate copy and a separate ledger/review. Reuse this completion gate for each representation within its declared scope. A source can pass reconstruction yet remain unsuitable for budgeted delivery; an optimized copy can fit its budget yet fail fidelity preservation. Never transfer matched statuses to a decimated mesh without reinspection. Follow [realtime optimization](procedures/delivery/realtime-optimization.md).

## Module versus Blender object

A **module** is a semantic assembly that a reviewer can identify and judge,
such as a viewport, manipulator arm, propulsion ring, hatch, seat, or sensor
mast. A Blender object is only an implementation unit. One module may contain
many objects, and a high object count says nothing about reference coverage.

Count modules before modeling. Split a coarse assembly into child modules when
the reference gives them an independently readable silhouette, material,
mechanical role, attachment, or repeated count. For example, do not record
"submarine details" as one module when the sheet separately shows a mast,
radome, antenna, service hatch, vents, lights, and sonar.

## Build a module ledger first

Copy [module-ledger-template.json](../assets/module-ledger-template.json) into
the task output directory and populate it before detailed geometry. Record:

- stable module ID and human-readable name;
- observed, inferred, or unknown evidence;
- source views where it is visible;
- primary, secondary, or tertiary priority;
- expected repeated-instance count;
- visible signature features that make the module recognizable;
- the subset of signature features actually verified in rendered views;
- current status and its Blender objects or collection;
- whether the user explicitly approved a simplification.

Use these priority meanings:

- **Primary:** controls the overall silhouette, proportions, or identity.
- **Secondary:** a separately recognizable assembly or large design feature.
- **Tertiary:** panel seams, fasteners, small vents, labels, and micro-detail.

Repeated asymmetric parts need separate ledger entries. Symmetric repeated
parts may share one entry only when `expected_instances` records the count and
the implementation is genuinely shared.

## Do not silently coarsen the ledger

Use the following test: if a reviewer could point to a visible item and say
"this part is missing or wrong" without referring to the whole model, it needs
its own module or signature feature.

Before leaving reference analysis, inspect every supplied view at full
resolution and account for:

- outer silhouette and negative spaces;
- attachments and connection geometry;
- repeated-part counts;
- front/back/top/bottom-only equipment;
- interiors visible through glass or openings;
- material boundaries and large colour blocks;
- service panels, vents, lights, sensors, rails, and handles;
- deliberate asymmetry.

## Completion stages

### Evidence required for `matched`

An object being present, named correctly, or editable does not make its module
matched. Before assigning that status, record the controlling view/region,
comparison screenshot or overlay, relevant landmarks/proportions and local
profiles, observed differences, and the reason those differences are acceptable
for the requested target. Use the module's `notes` and a linked comparison record
using structured `feature_reviews` records.

For each matched signature, add a `feature_reviews` entry with `feature` (the
exact signature), `status: "matched"`, `reference` (source region), `candidate`
(render/crop artifact), `view`, and `comparison` (observed agreement and remaining
differences). A filename alone or "object exists" is insufficient comparison.
Reuse one crop for several features only after checking each. For orientation,
thickness and relief, follow [local-feature-review.md](local-feature-review.md).

At final, fill `final_review` with `status: "passed"`, `structural_report`,
`contact_sheet`, `perspective_view`, and `unresolved_issues: []`, referring to
reports/images actually inspected. Do not fill these at build time. The validator
checks record completeness, not whether images look correct. Older ledgers stay
readable but matched/final claims fail until evidence records are provided;
do not backfill evidence for unreviewed assets.

After user correction, clear the affected match and set a concrete
`review_invalidated` reason; reopen final review. Clear the reason only after
repair and comparison evidence. User rejection overrides a previous agent pass.

Include reference-specific shape and placement in signature features. Conditions
such as "has two eyes", "round head" or "two thin legs" are insufficient when
eye spacing, head depth or limb thickness is visible and defines the design.
Compare those features explicitly; do not batch-copy every expected signature
into `matched_signature_features` or infer matches from implemented counts.
Known shape/placement errors keep a present module at `blockout` or an honestly
explained `simplified` status until corrected or the tradeoff is authorized.

For contradictory AI depictions, use the interpretation and human-judgment policy
in [reference-image-analysis.md](reference-image-analysis.md). Record the selected
constraint and why it overrides a panel. Do not invent measurement certainty or
silently lower the target to turn a discrepancy into a pass.

Use stage names literally. Never present an earlier stage as a finished model.

### Blockout

Purpose: validate axes, cameras, proportions, primary masses, and major
attachments.

Gate:

- every required primary module exists at least as `blockout`;
- matching orthographic renders have been inspected;
- the calibrated in-Blender reference workspace and front/side comparisons
  have been inspected; known primary proportion failures are reported as
  unresolved, not described as "primary proportions pass";
- report missing secondary and tertiary modules explicitly.

Allowed report language: "blockout complete" or "primary proportions pass".
Do not say "model complete".

For complex creation, also require the scoped [blockout acceptance](acceptance/blockout.md). Record the selected modeling method and inspection evidence in the project modeling plan/review, and reference their paths in the existing task record or ledger notes. Do not change ledger schema or duplicate its module completion labels. A successful builder or object-presence count cannot authorize refinement. A built but unreviewed coarse model is reported as "blockout built, review pending".

A blockout inspection signature ties the reviewed scope to the actual source state and dependencies. After a relevant change, an unchanged old review cannot simply be recorded again. Retain a coarse snapshot/control state for continued refinement and invalidate affected detailed visual evidence separately. Existing reference-fitting snapshots can implement equivalent checks; a 2D threshold alone is not equivalent.

### Feature-complete

Purpose: establish the complete recognizable design before micro-detail.

Gate:

- every required primary module is `matched`;
- no required primary or secondary module is `missing`;
- repeated instance counts match the reference;
- each primary and secondary module includes its signature features or is
  marked `simplified` with a concrete reason;
- front, back, both sides for asymmetric designs, top, and bottom have been
  visually reviewed where references exist.

Allowed report language: "feature-complete with N simplified and M missing
tertiary modules". Do not collapse those counts into a single percentage.

### Final

Purpose: deliver the user-requested finished asset.

Gate:

- every required module is `matched`; or a `simplified` module has explicit
  user approval recorded in the ledger;
- required repeated counts and signature features are present;
- `missing == 0` and `unapproved_simplified == 0`;
- structural, geometric, visual, render, save, and requested export checks
  pass;
- both a contact sheet and at least one perspective/hero view are inspected.

Only this gate authorizes unqualified language such as "finished" or
"complete".

## Presence and fidelity are different metrics

Always report both:

- `presence_coverage = (matched + simplified + blockout) / required`;
- `full_fidelity_coverage = matched / required`.

These are ledger-label statistics, not measured image similarity or reconstruction
accuracy. Identify them as such if included in a report; do not advertise a model
as "94% matched" because 16 of 17 labels were set to `matched`. Unsupported labels
invalidate the coverage conclusion even when the validator returns `ok: true`.
Local failures such as wrong facial placement, head depth or limb width cannot be
averaged away by many unrelated present modules. Retract affected matches and
the claimed stage when review reveals them.

Also report absolute counts for `matched`, `simplified`, `blockout`, and
`missing`. A model with 18 of 20 modules present but only 12 matched is not
"90% complete"; it has 90% presence coverage and 60% full-fidelity coverage.

Silhouette or image-similarity scores are separate evidence. Never use them as
a substitute for module and signature-feature coverage.

## Acceptable reasons for simplification

Simplification must be visible in the ledger and final report. Acceptable
reasons include:

- the user requested a blockout, low-poly budget, distant background asset, or
  another constrained output target;
- supplied views contradict each other and the chosen interpretation is
  recorded;
- a hidden surface is genuinely unobservable and does not affect the requested
  function;
- the user explicitly approved the tradeoff.

The following are not sufficient reasons:

- a primitive was easier to script;
- the silhouette already looks close;
- the object count is high;
- the part is visible only in the top, bottom, or back view;
- the render is attractive enough to conceal the omission.

## Iteration policy

After each render pass:

1. Update module statuses from visual evidence, not from code intent.
2. Find the largest primary or secondary fidelity gap.
3. Fix that gap in the persistent script.
4. Re-render every affected controlling view.
5. Re-run the ledger validator.

Do not spend time on tertiary fasteners while a primary or secondary module is
missing, incorrectly oriented, or represented by an unrelated primitive.

Run the deterministic ledger check with the skill environment:

```bash
uv run --project /absolute/path/to/blender-python-modeling \
  python /absolute/path/to/blender-python-modeling/scripts/validate_module_ledger.py \
  /absolute/task/module-ledger.json \
  --stage final --model /absolute/task/model.glb --review /absolute/task/delivery-review.json \
  --output /absolute/task/module-coverage-report.json
```

The validator checks bookkeeping and completion claims. It cannot decide
whether a mesh visually matches the reference; that still requires rendered
view inspection.

## Fixed-camera refinement loop

1. 粗模验收后，保存已组装的模型和与控制视图配准的镜头。在第一次精修前，按视图保存原图或已审参考、模型渲染和叠图，登记轮廓、比例、遮挡、接合与材质分区差异。锁定相机变换、投影、取景、分辨率和比较用光照。后续局部裁切取自同一套渲染；若校准有误，先修正校准并重渲基线。
2. 从影响整体比例或遮挡关系最大的差异开始，每次记录目标部位、诊断、修改方法、受影响部位和修改前版本。图中看不清形状或连接时，携带原图、已审视图和具体疑点回到多视图技能补相应角度或特写。复审后标明原图可见与隐藏推定的界限；新证据触及已审部位时重新打开该项。
3. 在固定镜头下同时比较参考、修改前与候选版本。先看目标特写，再扩大到相邻、对称、连接以及共享网格、材质或骨架的部位，最后查看各控制视角下的整模。记录改善、无变化和退化。候选破坏已确认特征时，回到上一个较好版本或缩小修改范围，重新比较。例如改肩宽还要对照衣领、袖口、两手位置和整身剪影。
4. 多次尝试仍未匹配时，把该部位暂缓并继续队列中的其他部位。在项目的逐部位日志中记录部位、参考视角、最佳版本、参考／修改前／候选对比图路径、各次尝试和结果、残差、已知原因或待证假设，以及重开条件。使用原有模块台账的实际验收状态；暂缓只影响工作顺序。有新参考、相邻结构变化或新的可检验修法时重开。
5. 局部队列走完后，做整体精修，重新检查体量、重心、比例、剪影、连续性以及材质关系，对发现的问题重复上述循环。最后以同一模型版本重渲所有固定视图，检查整模和受影响的局部，并复核暂缓项。尚有可验证的改进就继续；尝试次数本身不能作为全局停止条件。
6. 所有可执行项均已处理，且最终复核找不到有参考依据、能改善模型并保住已确认特征的下一步时，导出最佳已审版本，附固定镜头对比和剩余差异日志。有未匹配项时标明当前证据下的最佳结果，并保留原有完成门槛与导出回读检查。

### Final evidence file

For reference-model delivery use the final command above on the actual exported file. Earlier stages can run without delivery arguments. Treat an export without a passing report as a preview or a disclosed best-reviewed version with residuals. Rerun the command after edits and compare the reported model digest with the file being handed off.

In the review JSON, each file reference contains its path relative to this JSON and the SHA-256 of its bytes. Provide file references for `ledger`, `model`, `preparation`, `multiview_review` (multiple construction views), `structural_report`, `contact_sheet`, and `perspective_view`. The last three also correspond to the paths in the ledger's final review.

- In `views`, use one record per controlling direction with its design-review `name`, `reference` file, exported `model_sha256`, `comparison` file, and `before` and `after` render records. Each render record contains an `image` file and the actual `camera` settings captured at render time: flattened 16-number `world_matrix`, flattened 16-number `projection_matrix`, and pixel `resolution` [width, height]. Keep the full frame when cropping detail comparisons.
- In `regions`, key records by module ID. Each has a `local` comparison file, a wider `surroundings` comparison file, and a `state` of `reviewed` or `residual`. For residuals include the `attempt_log` file and a specific `reason`. Continue other regions. Supply `actionable_items` as a list after the whole-model review.
- Archive the CLI report alongside the reviewed revision. A ledger-only API result reports `ledger_final_passed`; only the final CLI can set `ready_to_claim_complete`. The checks verify declared settings and artifact freshness; a reviewer still inspects the images.
