<a id="blender-result-verification"></a>

# Blender 结果验证

根据交付成果选择检查项。仅结构上的成功并不足以构成一个视觉场景，仅有一个好的截图也不足以生成一个可输出的模型。

新的创作从一个空的、未被占用的工作场景开始，此时没有任何启动对象。请验证保存的文件能够在该场景中打开，并且无需用户手动选择该文件即可。在进行渲染对比之前，请先执行并记录[渲染预检](production-workspace.md)。在最终确认之前，请应用[特定用途的接受](acceptance/usable-asset.md)；一个静态的装配器或一次性使用的测试装置无法证明动画资产的可靠性。

<a id="structural-checks"></a>

## 结构检查

- 预期的收集、对象、材质、相机、灯光、骨架、动作以及节点组的名称都存在。
- 对象类型和parent/constraint关系与设计相匹配。
- 重新运行脚本并不会复制生成的数据。
- 现有的超出范围的对象和数据块仍然存在且保持不变。
- 没有任务拥有的临时对象或材料被无意中保留下来。

使用 `get_scene_info`表示库存物品，使用 `get_object_info`表示重要物品。

<a id="geometry-checks"></a>

## 几何检查

- 尺寸和位置与要求的比例和坐标约定一致。
- Vertex/edge/face或三角形计数对于目标用途来说是合理的。
- 法线始终一致；没有偶然出现零面积的面、重复的顶点、孤立的几何图形，也没有未应用的变换导致输出出现问题。
- Watertight/manifold在需要用于制造、布尔实体、碰撞或体积检查时通过。
- 修改器按正确顺序排列，在可编辑性、绑定或形状键需要的情况下，保持未应用状态。
- 对称性、间隙、厚度、枢轴、原点位置以及零件的对齐都符合模型的要求。

在持久性脚本中加入详细的检查，并打印出一个简洁的pass/fail摘要。在检查最终修改结果时，使用计算后的网格。

<a id="visual-checks"></a>

## 视觉检查

多张建模视图导入 Blender 前，须按适用范围通过[建模前多视图审查](../../concept-multiview-sheet/references/pre-model-review.md)。检查姿态是否适用、尺度和特征点是否一致、投影与遮挡、结构与颜色以及轴向。关键冲突尚未解决的部位不能进入细节建模。下面的工作区校准是导入后的第二次检查；源图仍须先通过一致性审查。

对于以参考为导向的工作，首先需要在相应的正交视图中检查导入并校准后的 Image Empty 工作空间：源图像、方向、比例、地标对齐。opacity/front显示、视图过滤和锁定变换。重新打开派生文件以确认图像已打包或通过可移植路径解决。仅仅找到参考对象并不是视觉处理过程。

在每个几何阶段，保留一个匹配视图reference/model叠加或并排比较，并检查局部特征以及外部轮廓。对于角色来说，需要检查与头部相关的面部标志点、从侧面看到的头骨深度，以及四肢。width/continuity通过关节连接；为道具使用等效的功能性标志。固定主要部分position/proportion在材料精加工之前出现的错误。对于在结构证据上被拒绝的AI生成结果，需要解释原因，或者在材料存在模糊不清的情况时寻求人工判断。网格的完整性、表情切换的成功以及账本验证并不能证明参考资料的准确性。

在每个有意义的视觉阶段之后调用 `get_viewport_screenshot`。至少检查：

- 轮廓与比例；
- 相机构图和裁剪；
- 交叉点、间隙、浮动部件以及z向冲突；
- 平滑处理、阴影处理、法线翻转、材质分配以及纹理方向；
- 光线方向、曝光度、色彩平衡、阴影质量以及可读性。

对于最终需要生成最终图像或动画的场景，需要渲染具有代表性的输出结果；仅使用实体模式的视口截图无法验证渲染材质或光照效果。

在视觉对比记录中保留当前的几何形状和外观特征。着色器inputs/groups, 源纹理,UV/region属性，灯光、世界环境, 相机和渲染、颜色设置可以在不改变顶点的情况下使图像判断无效。可执行的比较门会同时检查这两点；外部caches/engines需要明确的额外依赖项。请参阅[staged-execution.md](staged-execution.md)有效的收据证明了产品的新鲜度，并表明了经过检验，而非仅凭图片来确认。

<a id="animation-and-simulation-checks"></a>

## 动画与模拟检查

使用 [字符接受等级](character-delivery.md#separate-animation-acceptance-levels) 进行骨骼设置：小型 FK 姿势、完整的运动范围变形，以及完整的移动 contact/loop 检查是不同的。需要检查实际评估的鞋底和预期材料；有限的顶点和权重总和无法证明行走的可行性。

- 清洗或采样起始、中间、结束以及重要的接触帧。
- 确认帧率、帧范围、插值、循环、约束以及对象原点。
- 检查穿透问题、不稳定的模拟、依赖循环以及未烘焙的缓存。
- 请不要应用会破坏骨骼、形状键或缓存模拟的修改器或变换。

<a id="save-and-export-checks"></a>

## 保存与导出检查

- 使用绝对输出路径，仅创建预期的父目录。
- 未经用户明确指示，请勿覆盖现有的源 `.blend`。
- 对于GLB/FBX，请验证返回的导出对象列表和文件字节大小，然后确认文件确实存在。
- 确认轴、比例、材质normals/tangents针对目标应用程序，进行动画、修改器、纹理打包以及选择范围的处理。
- 保留导入的外部资源的许可证和归属信息。

<a id="completion-evidence"></a>

## 完成证据

对于通用参考驱动构建，在最终确认之前，请从 [reference-workspace-tool.md](reference-workspace-tool.md) 运行实时 workspace/review 门。附上当前的校准和模型比较记录、已使用的地标绑定以及实际参考可见的视口捕获。存储在混合文件中的源图像或导入计数并不能表明它影响了几何形状。

报告：

- 持久脚本路径；
- objects/collections 创建或修改了；
- Blender版本以及实时MCP执行是否成功；
- 已進行結構和視覺檢查；
- 渲染时，`.blend`、GLB或FBX路径和大小应保持不变；
- 未解决的警告或假设。

<a id="source-evaluated-triangles-and-reimport-are-distinct-layers"></a>

## 分别检查源数据、求值后的三角面与回读结果

使用 production_checks.inspect_mesh 进行源拓扑和计算的三角剖分。现有的 degenerate_faces 字段以网格本地坐标测量原始多边形面积；degenerate_triangles 则以世界坐标测量实际的分片情况，包括对象变换。正面积的 n 边形可以包含零面积的三角形。默认值为 min_triangle_area=5e-13 世界单位平方；记录一个 purpose/scale-derived 的容差，而不是将其视为一个通用的物理阈值。报告包括违规的 triangle/polygon 标识符、保留的源诊断信息以及计算的 structural_issues。由修饰符封闭的合法开放控制笼子被视为两种不同的表示方式。

在完全明确的资产白名单上使用 inspect_asset / require_asset_geometry 进行筛选和交付。它们会汇总计算评估的三角形数量；缺失的 max_triangles 被视为 budget_passed=null，并不表示预算成功。例外情况会保留测量报告，但不修复几何形状。模板会在 modeling-plan.json 中绑定限制；静态拟合器使用验证.working_max_triangles 和验证.min_triangle_area 进行源检查，并单独报告最终的验证结果.max_triangles 交付目标。使用 resource_limits(计划, 阶段)：最终 max_triangles 仅适用于 delivery/reimport； blockout_max_triangles 和 working_max_triangles 是可选的明确的工作资源上限，没有回退到最终上限。无效的几何形状或失败的明确工作上限会阻塞该阶段。其他有效的细化源可能超过交付上限，并进入源精度审查，而不是预算交付验收。冻结已审查的源，然后单独验证其优化后的副本；参见 [实时优化](procedures/delivery/realtime-optimization.md)。

asset_delivery.export_glb可以接受max_triangles、min_triangle_area和require_closed。在导出之前，它会先检查当前评估的几何图形是否合格，并在一次性包中检查每个声卡样本的实际重新导入情况。源代码的预检和工人故障报告会被保留；即使格式正确的GLB文件仍可能通过这些检查。

GLB attribute/normal接缝可能会分割顶点，即使对于封闭的立方体也是如此。原始重新导入的边界计数仍会保留在报告中；当 require_closed被请求时，工作人员还会在临时焊接的副本上测量几何闭合性，以符合声明中的空间公差要求。但这并不会修改 imported/source网格，也不会消除真正的孔洞或确保可打印性、自相交或薄壁强度。请检查记录的公差以及 raw/seam-welded的结果；切勿将这一检查重新命名为原始拓扑连通性的证明。

恒定的 PBR 传输检查并不能证明源图像的效果。应保留原始源图像之间的对比，而不考虑构建掩模的一致性，并保留这些对比结果。来源、白模、材质在优化拓扑结构或资源时查看视图。
