# 制作知识来源与采用边界

整理日期：2026-11-13。以下链接用于追溯原理；本库流程为重新编写的条件化工作方法，没有复制插件源码或第三方模型。针对 4.5 手册编写的规则仍须在实际 Blender 版本验证。来源可信度不等于本库实现已经通过生产验收。

| 来源 ID | 一手资料 | 采用内容与边界 |
|---|---|---|
| blender-remesh | [Blender 4.5 重网格/重拓扑](https://docs.blender.org/manual/en/4.5/modeling/meshes/retopology.html) | 按用途选择表示；自动重网格不自动等于可变形角色拓扑 |
| blender-transfer | [Data Transfer](https://docs.blender.org/manual/en/4.5/modeling/modifiers/modify/data_transfer.html) | 拓扑映射与空间映射前提、距离与区域控制 |
| blender-corrective | [Corrective Smooth](https://docs.blender.org/manual/en/4.5/modeling/modifiers/deform/corrective_smooth.html) | 静止参考、修改器顺序和局部修正；不是骨轴/权重错误的替代修复 |
| studio-pose-keys | [Blender Studio Pose Shape Keys](https://studio.blender.org/tools/addons/pose_shape_keys) | 姿势关联修正形体、蒙皮迭代后的维护；插件是可选路径 |
| blender-bake | [Cycles 烘焙](https://docs.blender.org/manual/en/4.5/render/cycles/baking.html) | 烘焙对象、目标图像、射线/cage 与贴图类型 |
| blender-colour | [色彩管理](https://docs.blender.org/manual/en/4.5/render/color_management.html) | 颜色与数据贴图的区分、显示变换与可比较条件 |
| blender-cloth | [布料碰撞](https://docs.blender.org/manual/en/4.5/physics/cloth/settings/collisions.html) | 碰撞参与、距离/质量取舍与自碰撞 |
| khronos-io | [glTF Blender I/O](https://github.com/KhronosGroup/glTF-Blender-IO) | 导出行为和版本分支；按实际 Blender 版本查对应分支 |
| khronos-validator | [glTF Validator](https://github.com/KhronosGroup/glTF-Validator) | 独立格式/引用/数据检查，不能代替视觉或消费端验收 |
| khronos-samples | [glTF Sample Assets](https://github.com/KhronosGroup/glTF-Sample-Assets) | 功能测试资产候选；逐资产核对版本、许可和署名后才引入 |
| meshoptimizer | [gltfpack](https://github.com/zeux/meshoptimizer/tree/master/gltf) | 优化可能合并节点、量化和重采样；先声明可操作身份与扩展支持 |
| retopoflow | [RetopoFlow](https://github.com/CGCookie/retopoflow) | 受控投射/局部重拓扑的可选工具；代码与非代码资源许可不同 |

CloudRig、Pose Shape Keys、RetopoFlow 不成为默认安装依赖。未安装时使用原生可复现步骤，或明确特定路径未执行。需要直接复用第三方代码/模型时另行记录版本、许可证和署名，不把公开可读等同于可任意分发。

X 上的 Daniel Bystedt、Simon Thommes、Pierrick Picaut 内容只保留为研究线索；本次没有把未完整读取/复现的帖子升级为操作规范。上游 MCP 指南中的固定面数、固定减面率和一键重拓扑结论也不作为本库通用标准。
