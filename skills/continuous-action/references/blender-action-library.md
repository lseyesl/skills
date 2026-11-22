<a id="ablend-action-library"></a>

# A.blend 动作库

`assets/A.blend` 包含了字符网格和导入的动作。`assets/A.catalog.json` 是动作ID、源FBX名称、帧范围、循环提示、审核过的阶段标记以及基础剪辑的单一来源。与其在这里维护一个动作表，不如直接阅读它。构建器首先导入基础剪辑，然后根据骨骼名称检查其他动作。

目录中的`loop_hint`只是一个采样提示，并非经过验证的无缝循环证书。在提供循环之前，请检查从最后到第一的过渡以及根运动。每个片段的`phase_markers`都标识了一个观察到的运动事件、Blender帧以及优先级。`phase_frame_range`必须与片段的当前范围相匹配；如果发生了变化，旧的相位时间戳将无法被静默重用，从而导致重建停止。在更新任何源FBX文件后，即使其帧范围保持不变，也请检查各个阶段。

<a id="render"></a>

## 渲染

从仓库根目录运行：

```bash
blender -b skills/continuous-action/assets/A.blend -t 2 \
  --python skills/continuous-action/scripts/render_keyframes.py -- \
  --action ACTION_ID_FROM_CATALOG --count 8 --view front --project /absolute/production-project
```

该脚本会读取其Skill目录中的A.blend/catalog信息，并在消费项目的`.tmp/continuous-action/`下创建一个新目录。默认情况下，它会为每个姿势生成一个编号的透明PNG文件，外加`manifest.json`。它选择目录阶段的标记，而不是等间距的帧。如果请求的图像数量少于标注的阶段数量，它会优先选择覆盖更多事件且优先级更高的图像。如果标注的阶段数量超过实际请求的数量，则会在更多事件被审核和添加之前出现失败。清单记录了每个阶段的名称、Blender帧数、源动作、FBX、视图、图像路径以及侧视图参考调色板。使用`timing.source_fps`和每个帧的`duration_seconds`来重新播放非均匀阶段，包括最终间隔到循环结束或剪辑结束。在查看姿势后，可以传递`--phase-frame PHASE=FRAME`以进行附近的单次修正；这样可以保留阶段的身份，并记录覆盖信息。在图像生成过程中，帧ID保持不变，其输出也会放入该临时任务目录中。`--format sheet`则发出一个有序的`action-reference.png`，并在清单中记录每个姿势的区域。当每个生成的帧必须与特定的Blender姿势匹配时，使用单独的PNG文件；只有当整个动作行参考足够时，才使用该文件。只有在真正需要该相机时，才使用`--view left`、`right`或`back`进行渲染。技能中不应包含任何角度预览或生成的图像。

在管理下的安装中，使用已安装的绝对 asset/script 路径。 `--project` 覆盖所推断的消耗工程根；`--output` 可以在技能资源和安装容器之外选择不同的空任务目录。 一次性修改使用`--phase-frame`; 持久目录编辑和重建属于源检出，之后是明确的技能update/install.

对于`left`和`right`，渲染器使用骨骼权重来使远侧的手臂、手、腿和脚的亮度降低15%，并使其略微偏冷，同时保留近侧肢体的原始亮度和颜色。这种偏冷的效果能够保持所选的亮度降低效果。引导颜色差异仅用于识别肢体的深度；最终生成的角色帧必须恢复到角色的原始调色板。Manifest文件记录了仅作为参考的色调。

在渲染完成后，请检查每个全尺寸 PNG 文件中的所有四个肢体以及序列接触图。如果某个可见的胳膊或腿无法被分配到近侧或远侧或其关节上，请进行调整。bend/contact无法读取，重新渲染到一个新的临时目录中`--far-limb-dim 0.20 --far-limb-cool-strength 1.5`然后再次进行检查。第一个标志接受的值为 0.10–0.20，第二个标志接受的值为 0–1.5。在任务QA备注中记录已检查的帧ID以及任何剩余的遮挡情况。对比度无法恢复隐藏在身体后面的肢体；尽可能选择附近的时间戳，并保留预期的动作阶段。

Blender 4.5 使用动作槽。通过脚本更改动作时，需要同时设置 `rig.animation_data.action` 和 `rig.animation_data.action_slot = action.slots[0]`；否则，一些导入的动作可能会出现冻结现象。渲染脚本会执行此操作。如果可见的字符裁剪在画布之外，请调整 A 或渲染脚本中的 `ReferenceCamera`，并通过一次帧选择重新生成整个序列。

<a id="rebuild"></a>

## 重建

仅在源代码检查阶段，从仓库根目录运行 `blender -b -t 2 --python skills/continuous-action/scripts/build_action_library.py`。构建器会从目录中读取 `base_clip` 和每个 `clips.*.source_fbx`，从 `.tmp/fbx` 导入这些文件，检查匹配的骨骼名称，打包纹理，保存 A.blend，并更新测量的帧范围。重建后，至少从每个已更改的操作中渲染一帧，并检查结果。对于普通的图像生成，重建是不必要的。

请不要默默地替换其他操作资源。当请求的操作不存在时，询问用户是提供新的 FBX 文件，还是批准从 A 点得到的近似值，或者停止操作。
