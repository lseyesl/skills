<a id="fail-closed-stages-and-selective-rendering"></a>

# 分阶段核验与按需渲染

使用项目本地入口点来处理分布在构建、设置、验证、保存和渲染过程中的任务。当现有的 fitter/worker 已经提供了相应的检查功能时，可以复用它；不要为一步编辑操作创建第二个 orchestration 系统。

<a id="never-infer-success-from-transport-status"></a>

## 单独检查操作的执行结果

MCP在文本报告中可能返回`isError: false`，同时出现`Error executing code`、回溯信息或通信失败。检查实际结果，并在进行依赖工作之前要求获得新的项目阶段收据。每次尝试之前，清除旧的成功标记；如果文件与昨天的`build_ok=True`相同，则无法授权重新构建操作。

`scripts/stage_guard.py`提供了标准库的辅助功能。在项目入口点中，每个收据路径使用一个写入器：

```python
from stage_guard import file_input, run_stage, require_stage

# Resolve inputs inside run_stage so missing files also invalidate prior success.
def build_inputs():
    return {"recipe": file_input(script_path), "references": file_input(reference_config),
            "parameters": actual_model_parameters}

result = run_stage(build_receipt, "build", build_inputs, [saved_blend],
                   work=build_and_save,
                   validate=validate_build_result)  # must return True or raise
# The current attempt, input fingerprint and artifact hashes must still agree.
receipt = require_stage(build_receipt, "build", build_inputs)
run_stage(render_receipt, "render", {"build_run": receipt["run_id"],
          "blend": file_input(saved_blend), "views": affected_views,
          "render_config": actual_render_parameters}, expected_images,
          work=render_affected_views, validate=validate_render_outputs)
```

上述回调是项目实现，并非捆绑在一起。geometry/render函数。不要捕获阶段异常并继续依赖步骤。失败的尝试会被记录下来。`failed`; 中断了`running`收据无法传递。请在指纹中包含所有实际依赖项：recipe/helper/config/source哈希值、参数、装备版本、渲染设置以及前代尝试。`BUILD_RECEIPT`在任务模板中启用相同的构建保护；设置`BUILD_OUTPUTS`当项目构建器保存文件时。仅包含收据的实时文件，没有文件输出，这证明了该阶段的检查，而不是后续场景的新鲜度；比较当前geometry/appearance在使用之前，请先签署。

记录每个阶段的耗时（包括失败情况），与生成调用、用户等待时间和总任务时长分开。仅在测量时报告总数。阶段记录用于确定执行情况和作品的新鲜度，与艺术性或动画审批无关。

<a id="spend-rendering-effort-where-evidence-changed"></a>

## 对受变更影响的部分重新渲染

- 在完全交付视图之前，请先查看一个代表性的本地样本。materials/light.解决头部、口鼻部、关节在整体润色之前，先对形状和签名进行润色。
- 在进行了本地编辑之后，请先重新渲染受影响的裁剪和控制视图；保留具有来源信息的未更改的伪影。当本地检查通过之后，再运行最终的通用规模多视图渲染。
- 明确做出受影响的视图决策。Head/pose/geometry这些更改会影响相关的轮廓；全局调色板、照明、曝光或共享着色器的更改可能会影响所有视图。不要仅仅因为只有一个参数发生了变化就跳过必要的重新渲染。
- 检查背面、顶部、底部在早期阶段，投影区域可能会出现泄漏：耳朵的前部与后部。喉部、胸部与腹部相比，与爪尖相比；与脚底相比，与尾巴根部相比。
- 避免重新生成整个图像页来修复单个视图或添加线条艺术。保留已认可的源面板；以模型为基准orthographic/contour一旦有了经过审核的遮挡信息，使用“sheet”方式更为理想。

<a id="fresh-visual-comparisons"></a>

## 使用最新渲染做视觉对比

保持几何，外观，动画验收 分开。 `model_signature(objects)` 轨迹评价shape/transforms.`appearance_signature(scene, objects, extra=...)` 额外指纹材料和嵌入式节点组，纹理content/bindings,UV/custom属性，其它制成的几何，灯光、世界环境, 相机，渲染、颜色 设置和混凝土节点。 比较验收记录 需要两个签名。 修改其中之一，即使文件仍然打开，也会使其先前的视觉发现无效 。

内置的指纹功能并非针对外部 movies/UDIM 瓦片、模拟缓存、自定义渲染引擎、序列编辑器内容、视口 shading/environment 覆盖或每个附加节点的完整依赖扫描工具。需要将这些依赖项包含在 `appearance_extra` 中，并作为输入进行阶段处理，然后检查渲染结果。对于外部 animated/unstable 输入，需要捕获评审过程中使用的确切 frames/caches 信息。没有外观签名的旧比较 JSON 必须被检查和更新，而不是机械地填充过去。

在发生变化后，保留无关证据并重新进行受影响的比较。Calibration/reference-design审批永远不能替代网格的逼真度；有限的坐标和权重总和永远不能替代可见性。deformation/contact检查。

<a id="scoped-blockout-prerequisite"></a>

## 粗模阶段的范围与前提

请使用 blockout_gate.py与现有的 stage_guard结合使用，而不是添加另一个通用的执行引擎。在 modeling-plan.json中定义模块方法、对象、依赖关系和检查。多个语义模块可以共享一个连续的网格；默认签名会保守地跟踪整个网格。不要为了使记录独立而分割一个连续的表面。

在检查之前，使用 `make_review_draft(plan, scope, state_provider, dependencies)` 创建一份待审核文件。该文件会记录 inspection_signature 和未知的审核情况。将其保存为新的审核文件；在填写 reviewer/findings/status. `record_blockout_review` 之前，先检查实际证据，对于那些 inspection_signature 与当前 plan/state/dependencies 不同的通过文件，拒绝接受；同时，不要对更改后的几何图形进行旧的批准。

在细化回调之前调用 `require_blockout_review`。生产模板将 blockout/review/refine 与 `refinement_inputs()` 分开处理，因此在 `require_stage(refinement_receipt, 'refine', refinement_inputs)` 中也会检查源代码的新鲜度。保持粗源不变，并细化副本；仅对详细副本进行更改不会使粗源失效。在细化失败期间修改粗源会被检测，但不会自动回滚；可以从保存的项目快照中恢复，并重新生成证据。

每个范围使用单独的收据。depends_on将状态扩展到必要的相邻模块；更改独立模块不需要进行无关的审查。默认的配方依赖是整个项目脚本，这是比较保守的做法。使用单独的粗配方文件，并声明所有相关的BLOCKOUT_INPUT_FILES/parameters，以缩小无效范围；不要省略真实的依赖关系，以避免使证据过时。使用--stage或运行时设置来切换阶段，而不是通过文件编辑来改变配方哈希值。

审核人员可以是检查代理，也可以是人类。没有引入统一的用户审批流程。门控环节会验证声明的检查内容、范围以及新鲜度，而不是艺术性判断。对于上下文敏感的检查，需要在项目依赖项中包含相关的摄像头、遮挡物、外部缓存以及场景设置；仅默认的源签名是无法发现所有这些元素的。

<a id="resume-modeling-loop"></a>

## 上下文压缩后继续返修

在当前任务施工计划旁保存 `repair-loop.json`，记录与计划一致的 task_id 和计划路径，由负责该模型的执行者更新。独立文件让返修进度更新时仍能复用有效的粗模计划签名。已有任务交接记录中写下计划路径；接续时从当前任务目录或交接记录定位它。首次接续旧项目且缺少进度文件时，从已有模块台账、最后已审快照和实际渲染恢复，无法确定的项目进入待验证队列。沿用原有预算、参考版本和验收条件。

| 字段 | 接手执行所需的信息 |
| --- | --- |
| `phase` | 下一步为 edit、verify、final_review、blocked 或 complete |
| `baseline`、`candidate` | 最佳已审场景与本轮候选的路径、SHA-256。首次尚无已审模型时记录起始快照及其未审状态；编辑前先分配独立候选路径，保存后补哈希 |
| `open_items` | 指向模块台账中的未关闭项，注明正在修哪项、控制视角、通过条件和需要保护的邻区 |
| `last_check`、`next_action` | 本轮证据路径、对应模型哈希、实际结论，以及可直接执行的一步操作；受阻时写明恢复条件 |

编辑前先落盘本轮意图和候选路径。保存候选后立即改为 verify。核对固定镜头及邻区后，把结果、保留或回退的决定与下一步一起写回；更新进度文件时用同目录临时文件原子替换。只在复验通过后关闭对应条目。拟合命令产生的 result.json、续修配置和场景直接引用到进度文件。长时间渲染仍在运行时，先接续原进程或核对其产物。

几何与外观分步验收时，在 `open_items` 保留待查的表面、贴图通道与控制视角。例如交领白模已通过，可将 `next_action` 写为“从侧前方核对外领色带，并单显 AO 检查胸前旧阴影”。在 `last_check` 引用相应模型与贴图版本的渲染；恢复时遇到外部贴图已替换，重开受影响的着色检查。

恢复时逐项核对当前任务、场景、参考和回执。中断发生在编辑与写回之间时，检查预分配的候选：存在且能重开则先验证，文件缺失或损坏则从已核验基线重做未完成的一步。验证中断、证据过期、文件哈希变化或用户新增反馈时，重开受影响条目并复验；在新证据到位前保留最佳快照。局部通过后继续处理队列，清空后进入 final_review。只有本版导出回读、适用的正式验收和视觉复核全都通过，才写 complete。blocked 记录具体阻塞，恢复条件满足时回到相应阶段。
