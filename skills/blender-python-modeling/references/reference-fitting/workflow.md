<a id="executable-reference-fitting-workflow-phase-04"></a>

# 可执行的参考拟合流程（阶段 0–4）

适用于需要反复进行参考评估以及参数级局部修改的任务。普通的非字符建模可以继续使用现有的脚本。现有scene/ledger/three-expression工作流程保持不变；新的字符示例仅提供参考的“开心脸”图案。

<a id="environment-and-reproducible-commands"></a>

## 环境与复现命令

已验证：Blender **4.5.12 LTS**，通过此技能现有的uv项目运行Python。NumPy/OpenCV.Blender中未安装任何Python包。其他4.x/5.x各版本需要运行时的功能支持；其他版本在出现突变之前就会失败。CPU Cycles是表现较好的引擎；现有的软黏土工具也具备EEVEE集成功能。

从仓库根目录：

```bash
# Inspect supplied masks, annotation reliability and observed source colors.
uv run --project skills/blender-python-modeling python \
  skills/blender-python-modeling/scripts/fit_character.py analyze \
  --config skills/blender-python-modeling/examples/clay-girl-fit/character.json \
  --output output/my-fit-analysis

# Fresh construction requires a reviewed reference-preparation decision; output directory must be empty.
uv run --project skills/blender-python-modeling python \
  skills/blender-python-modeling/scripts/fit_character.py optimize \
  --config skills/blender-python-modeling/examples/clay-girl-fit/character.json \
  --output output/my-fit-run --rig-test \
  --reference-preparation output/reference-preparation.json \
  --blender /Applications/Blender.app/Contents/MacOS/Blender
```

`build` 创建 model/render/measurement;`render --source accepted.blend` 验证匹配 geometry/material 配置和刷新参考校准 + 渲染 输出而不重建几何；`evaluate` 重新测量一个已有的 渲染 目录；`baseline --source existing.blend` 在可支配的进程中应用实例可配置的遗留对象到标签映射 。`optimize --source accepted/scene.blend --config accepted/config.json` 恢复已有的自有配置，需要 形状、材质 身份 。 Baseline/source 文件永远不会被覆盖 。 每次运行保留 Blender 日志和一个工人超时( 默认 600 秒) 。 现有的输出目录会被拒绝，而不是被过度写入审查证据 。

创建阶段使用本任务专属的空场景，其中没有默认立方体、相机和灯光。配置对比渲染前，先用 CPU 做一次实际的小规模试渲染。若降噪不可用，记录原因，并在最终外观图和白模图中同时关闭，其他错误照常报告。`render-record.json` 保存此决定。本工具用于**静态拟合**。`--rig-test` 只进行临时测试，`worker-result.json` 不能证明生产绑定或最终交付已通过。`validation.max_triangles` 记录最终交付目标；源模型拟合通过 `delivery_budget_passed` 报告是否符合该预算，超过交付预算不代表源几何重建失败。仅显式指定的 `validation.working_max_triangles` 限制重建资源。几何缺陷仍会导致结构检查失败。冻结已审的拟合源模型，然后在独立的优化交付副本上验证最终面数上限。持久骨骼绑定见[绑定与蒙皮](../procedures/characters/rigging-and-skinning.md)。

请参阅 [architecture.md](architecture.md)以获取审核过的重用决策和模块边界。这是一个可扩展性系统；不需要对旧 API 进行迁移。

<a id="phase-0-freeze-evidence"></a>

## 阶段 0：固定原始证据

保留原始可编辑的源文件，参考裁剪部分，相机、引擎、颜色转换、配置和源哈希值。使用原始未拼接的图像，而不是从三列比较中提取掩码。建立标准化的高度单位；绝对单位仍未知。记录源可见性、AI不一致性以及所有推断出的深度。

<a id="phase-1-semantic-evidence-and-repeatable-measurement"></a>

## 阶段 1：语义证据与可重复测量

`reference.image`采用源RGBA格式（首选）；`reference.annotation`的版本为1，具体为`image_size`，并且需要明确指定组件`mask`的路径或`polygon`像素数组。每个注释都需要有来源信息，并且其质量`confidence`应大于等于0.7，才可以进行测量。Low-confidence/covered部分属于`not_evaluable`；没有掩码的情况属于错误。这些数值描述的是注释的可靠性，而不是校准后的模型概率。这里并没有通用的、可靠的自动语义分割工具。新的样本需要重新评估masks/polygons，而不是复制特定于女孩的颜色阈值。

该示例的掩码已本地化，并源自源代码。HSV/color首先进行了边界的确定，然后进行了目视检查。它们的遮挡边界仍然比较近似。被遮挡的躯干是N/A.在检查中发现人为的误操作时，进行正确的注释。crop/semantic边界；保留之前的运行结果，而不是重新计算它们的分数。`input_hashes`对图像、注释和实际掩码数组进行指纹识别。

验证过程会产生前景`beauty`、`silhouette`、`labels`、`albedo`、`clay`，以及side/back/three-quarter美感。ID/silhouette/albedo使用标准参数，曝光为0，伽马值为1，采用确定性种子，并且**不进行去噪**。临时材质会在`finally`中恢复。源材料和模型共享画布尺寸，以及校准后的正交相机。风格美感和反照率保持分离，因此由光照驱动的暗部不会与基础颜色不匹配产生混淆。

注册允许使用 `none` 全局注册（适用于校准的场景），或者一个全局 `bbox_similarity` 注册（统一的比例和平移，包括像素中心校正）。它记录 before/after 变换和 IoU 值。不支持单个组件的扭曲、各向异性缩放或弹性注册。

报告包括可见组件的IoU值、对称边界距离/完整字符高度、实际网格锚点投影误差，以及参考颜色与未照明基础颜色之间的Lab delta-E76中位数。Lab值是**描述性**的，因为光源来源未知。报告未声称能够恢复固有反射率。当前的示例锚点包括下巴和双手中心；可以添加可靠的面部标志点，以进行更精确的表情评估。IoU值是针对带有注释的像素进行测量的，并非体积或生产质量相关的指标。

<a id="phase-2-configurable-structure"></a>

## 阶段 2：可配置的结构

`shape`键是稳定的组件ID。每个键都有`kind`、`material`，以及可选的`label`聚合和状态。支持的构建器：

- `head`：多个`[z, half_width, half_depth, center_x, center_y, rotation]`部分，脸颊的饱满度，下巴的逐渐变细，width/depth/asymmetry.使用有界单调Hermite插值法来避免部分区域出现带状现象。深度地面设计可以防止纸张过薄的优化效果。
- `sweep`：连续路径和匹配的半径轮廓，可选palm/thumb体积，radius/palm比例。肩部关节应完全进入躯干；不要让宽大的服装AABB来替代真实的关节连接。
- `loft`：至少三个弯曲的裙摆部分，明确的厚度，独立的腰带路径以及低频的裙边波浪线。
- `shoe`：鞋头、鞋面、环形开口边缘和薄鞋底，这些是能够独立识别的部件。当前的鞋面与连续的鞋面重叠；这是一个视觉上的开口提示，**并非功能性的鞋腔**。
- `hair`：连续的发髻，明确的导向性流动引导线，以及一些具有方向性的褶皱。造型仍然是一个艺术设计问题；这个例子并没有达到参考中的发型轮廓。
- `surface_patch`：源多边形被三角化，退化的平面边被清理，内部被细分，然后每个顶点被投影到实际头部，再进行浅层拉伸。补丁取决于头部的更新。凸起的椭球体可以使用`head`、`surface_anchor_px`、`surface_offset`（例如鼻子）。

位置、轮廓和引导线属于每个角色配置；没有任何示例坐标存在于通用构建器中。稳定的名称是`<character>::<component>::<role>`。头部更新会重新构建其依赖项；锁定的依赖项会阻止该候选者。现有的表达式交换在原始工作流程中得以保留；这个调整器目前还不会生成任意新的表达式集。

<a id="phase-3-separate-stylematerial-parameters"></a>

## 阶段 3：分离风格与材质参数

`blender-styles/scripts/handmade_surface.py` 重新使用了现有的黏土材料工厂和 sRGB 转换功能。每种材料都有其自己的种子、低频相对几何变形、局部中等 dents/relief、受限的高频凸起、颜色变化和粗糙度。新的几何结构会被重新分配一次；局部种子来自稳定的 ID，因此重建肢体时不会重新打乱头发凹陷。

`analyze`使用稳健的可见掩模中位数来绘制`sampled-colors.json`。在将这些颜色放入配置之前，请先查看它们：参考highlights/shadows应保留在样本中。`materials.*.color_source`记录了来源信息；这并不意味着自动重新照明材料。尽管实现了三波段控制，但示例表面的纹理仍然过于光滑，不符合预期的粗糙粘土风格。形状匹配优先于增加噪声。

<a id="phase-4-local-refinement-and-regression-protection"></a>

## 阶段 4：局部精修与回归检查

结构化的缺陷名称指出了组件和观察到的现象bbox/boundary不匹配、置信度、候选参数以及局部性。坐标搜索进行评估minus/plus一个有限步骤component/parameter每一轮都会重新打开上一个被接受的快照，只重新构建那个依赖集，并对每个未受影响的对象的几何形状、变换、修饰符和着色器数据进行哈希处理。

候选者因结构故障、整体轮廓回归、其他测量部件的回归、地标回归或局部改善不显著而被拒绝。`locked`/`approved`组件不会被重新构建。这些是计算状态；将某事物标记为需要搜索的**并非用户的艺术性认可**。候选项的接受和选择是在两个方向都有所改善时分别记录的。被接受的`.blend`并且配置保持不变；回滚意味着从它们的路径继续，而不是尝试撤销一个已变异的共享场景。

停止原因：测量出的阈值（仅当证据门允许时）、迭代限制，或没有可操作的未锁定参数。锁定的分数较低，或N/A部分内容未被静默接受。失败。subprocesses/timeouts与他们的日志一起留在历史中。

3D QA会评估有限坐标、非流形边缘、退化面、一致的缠绕、正符号体积、深度下限、手掌连接、配置好的端点到凸面的套接以及AABB广相。它**不**会验证任意的自相交、布料碰撞或隐藏几何。`--rig-test`该软件会创建带有两条骨骼的临时骨骼肢体副本，弯曲每个关节并验证有限位移，然后将其移除。这只是一个真正的测试，**并非实际交付的生产设备或变形质量的认证**。

<a id="tests"></a>

## 测试

```bash
uv run --project skills/blender-python-modeling python -m unittest discover \
  -s skills/blender-python-modeling/tests -v

blender --background --factory-startup --python-exit-code 1 \
  --python skills/blender-python-modeling/tests/blender_fit_integration.py \
  -- --output output/fit-integration-check

uv run --project skills/blender-python-modeling python \
  skills/blender-python-modeling/scripts/test_reference_image_analysis.py
uv run --project skills/blender-python-modeling python \
  skills/blender-python-modeling/scripts/test_module_ledger.py
```

保留原有的`blender-styles/scripts/test_soft_clay.py --render`回归套件。有关实际计数和故障情况，请参阅特定运行报告；仅命令成功退出并不能验证参考协议的准确性。

生成一份包含`scripts/report_fit_run.py --baseline BASELINE --run RUN --delivery FINAL_RENDER_DIR --output REPORT_DIR`的配对报告。使用`scripts/verify_fit_run.py --run RUN --baseline BASELINE --output REPORT.json`验证真实的snapshots/candidate历史记录。

<a id="reference-preparation-gate"></a>

## 参考准备验收

新建模型或运行优化流程时，必须通过 --reference-preparation 提供[已审的参考准备决定](../reference-preparation.md)。示例配置本身不能证明其中图片足以指导建模。分析、渲染、评估及依据已有来源进行修复时，无需重新生成视图。诊断实验须同时声明 diagnostic_only 并传入 --diagnostic-only，其结果不能作为已验收的建模产物。工作进程在创建任务场景前会独立核验这一条件。
