# Blender 制作流程扩充与验证（2026-11-13）

## 本轮范围

在现有 blender-python-modeling 内增加四组、七条处理流程，没有新增 Skill：

1. 生成/扫描网格恢复，及重拓扑后的数据迁移。
2. 关节形变修正、原生修正形态键与可选 Pose Shape Keys 维护。
3. UV/法线烘焙错误，及布料接触异常诊断。
4. glTF/GLB 规范验证、重载/消费端验收，及实时优化回归。

配套五份验收规范、一份一手来源表、七个任务评测契约、只读制作诊断工具和独立 Khronos Validator 适配器。知识目录由 92 条增至 105 条；全部新增内容保持 experimental。外部插件不自动安装，glTF 验证器只在显式提供依赖时执行。

## 实际验证

- 完整轻量入口 14 套通过；新增制作工具/检索/来源关联测试通过。
- Blender 4.3.2：18 个技术检查通过。覆盖开放薄片合法、闭合要求下缺面判错、闭合体合法、空间权重迁移、同数量不能证明身份、顶点重排拒绝拓扑对应、骨骼角度驱动局部修正、错误符号识别、Basis 保留、平面切线法线烘焙、碰撞配置正反例、合法无自碰撞配置、20 帧平面布料接触。
- 实测平面法线图中心为约 (0.502, 0.502, 1.0)；短布料测试最终最低点 z 约 0.0179（场景单位），在此夹具中没有超过声明容差的穿透。
- 使用真实 gltf-validator 2.0.0-dev.3.10：有效文件、坏引用、外置同目录资源、跨目录资源限制及 Blender 实际导出的 GLB 均按预期处理。
- 第一次导出发现 MESH_PRIMITIVE_GENERATED_TANGENT_SPACE 警告；在含法线贴图的交付样例显式导出切线后重新验证，errors=0、warnings=0。旧报告保留，未将警告隐藏。
- 检索回归发现宽泛“UV 接缝”被新流程抢占；增加通用精确别名排序信号后，仍先返回 UV 总体指导，“法线贴图接缝”返回具体处理路径。原测试期望保持，布料明确故障则转向新增诊断流程。

原始运行日志、报告、PNG、GLB 和生成的 .blend 位于 .tmp/production-research 与 .tmp/tests/blender-production，不混入 Skill 源码。来源表包含官方手册、Blender Studio、Khronos 和工具作者资料；X 线索未复现，未升级为正式操作规则。

## 复现

```shell
python tools/check.py
python tools/check.py --group blender --blender /path/to/blender
python tools/check.py --group gltf --blender /path/to/blender --validator-module /path/to/node_modules/gltf-validator
```

默认轻量测试不要求 Node 或 Blender。glTF group 必须提供真实 Blender 和显式安装的模块；缺工具是 blocked，不会自动变成通过。当前适配器禁止外部资源越出资产目录，需要先整理完整交付包。

显式 Blender 双版本工作流已补制作样例与 pinned Validator 的执行/报告配置；未在本轮执行远端 CI 或 Blender 4.5。

## 未覆盖的交付能力

本轮没有认证完整人手/肩部形变、真实扫描资产恢复、复杂薄层属性迁移、高低模 cage 烘焙、完整服装、最终纹理 mip、真实目标查看器/引擎或 gltfpack 性能收益。技术检查不能替代这些验收。既有真实 Agent 对照的 CLI 鉴权阻塞没有在本轮重新尝试，也未宣称已解决。
