---
name: blender-styles
description: Select and apply Blender art styles through a shared workflow and on-demand style index. Use for soft low-poly clay (柔和低多边形黏土风), rough naive handmade plasticine (稚拙手捏橡皮泥风), or a requested combination of their geometry, surface, lighting and animation traits. Routes to only the relevant style rules and reuses shared material, lighting, timing, rendering and QA tools. Use blender-python-modeling for general modeling and reference alignment. Do not use for 2D-only image generation or physical clay simulation.
metadata:
  compatibility: Blender with bpy, bmesh and mathutils. Shared clay helpers were tested on Blender 4.5.12 LTS; other builds require capability checks. The handmade-plasticine style remains visually uncalibrated. Generic modeling/reference workflows require blender-python-modeling.
---

# Blender Styles

用一个入口选择美术风格，按索引加载必要规则。通用建模、参考定位、绑定、保存和导出交给 [blender-python-modeling](../blender-python-modeling/SKILL.md)；本 Skill 负责造型语言、材质、灯光、动画节奏与风格校准。

## 风格索引

| 风格 ID | 适合的目标 | 入口 | 验证状态 |
|---|---|---|---|
| `soft-clay` | 柔和、圆润、整洁、经济的低多边形黏土造型，柔光微缩场景 | [STYLE.md](styles/soft-clay/STYLE.md) | 有 Blender 4.5.12 工具与示例验证，见该风格证据；不保证任意参考都能还原 |
| `handmade-plasticine` | 稚拙手捏、挤压体积、明显拼接/指纹、局部混色，可选替换贴片五官 | [STYLE.md](styles/handmade-plasticine/STYLE.md) | 风格规范已建立，尚待实际小样视觉校准 |

先根据用户明确指定的风格或最新参考选择一个主风格，读取其 `STYLE.md`，再按该文档的任务索引读取细节。不要默认把所有风格文档、样例和历史报告全部加载。只有选择混合风格或需要另一个风格的工具说明时，才补读相关部分。用户只说“黏土风”时结合参考判断；确实存在明显不同的目标且无法判断时，展示差异并询问偏好。

旧名称 `blender-soft-clay` 和 `blender-handmade-plasticine` 分别映射为上表两个风格 ID，不再是独立 Skill。旧名称出现在上下文时，使用这里的索引继续。

## 共用流程

先阅读 [共用流程与验收](references/workflow-and-review.md)。工作顺序为：

1. 明确交付、现有资产所有权和目标风格；区分风格选择与参考人物身份。
2. 参考驱动建模先按通用流程导入/校准参考工作区，记录关键点、比例和 AI 图的可信区域；处理重大未决设计选择。
3. 确定主风格，记录造型、表面、灯光与动画节奏分别采用的规则。需要混合时使用下述组合规则。
4. 首次或未验证的表现方法先制作相关局部小样；比例、表面朝向、厚度和连接先通过，再添加材质和手作细节。主脉/侧脉、折痕、凹槽和鼓边分别检查，在实际细分、材质和灯光下可读后再跑整套渲染，见[局部形状与细节验收](../blender-python-modeling/references/local-feature-review.md)。
5. 写项目内可复现配方和风格/渲染配置，按需复用 `scripts/`，分阶段构建和查看实际结果。
6. 将参考形状、风格观感与结构交付分别验收，保存对照证据和限制；按通用流程保存/导出。

## 混合风格

按层指定来源，例如“`handmade-plasticine` 的揉压与拼接 + `soft-clay` 的柔光”，而不是把两套预设整体叠加。记录每层最终选择：

- **造型**：参考比例、轮廓、连接方式、风格化变形。
- **表面**：粗糙度、高光、颜色变化、痕迹密度和尺度。
- **灯光/镜头**：照明方向、阴影、背景、曝光与构图。
- **动画**：变形、接触、纹理稳定性和姿态保持节奏。

明确用户约束与可信参考优先。某层出现相互冲突的规则时，为这一层选择一个主规则并记录理由；不能将不规则度、噪声或灯光强度简单相加。无法判断且影响目标外观的冲突，请用户选择，其余已明确部分继续。新混合结果需要自己的小样证据，不能自动继承各风格单独的验证状态。

## 共用工具索引

需要参考评估与自动局部修正时，使用 [通用拟合流程](../blender-python-modeling/references/reference-fitting/workflow.md)。可选 [handmade_surface.py](scripts/handmade_surface.py) 复用基础材质工厂，分区控制低频几何、中频局部压痕/浮雕、高频细颗粒；不改变旧工具默认配置。

| 工具 | 用途和边界 |
|---|---|
| [clay_common.py](scripts/clay_common.py) | 配置合并、颜色转换、所有权、枚举、保存工具；默认配置属于基础柔和黏土 |
| [create_clay_material.py](scripts/create_clay_material.py) | 基础黏土调色与着色；不自动生成全部手捏细节 |
| [setup_clay_lighting.py](scripts/setup_clay_lighting.py) | 可配置柔光、世界与可选相机；检查镜头和已有灯光 |
| [setup_clay_animation.py](scripts/setup_clay_animation.py) | 明确目标上的姿态保持与循环工具，不是绑定/动作生成器 |
| [setup_render.py](scripts/setup_render.py) | EEVEE/Cycles 配置与可恢复图像输出，不改变全局 GPU 偏好 |
| [validate_clay_scene.py](scripts/validate_clay_scene.py) | 基础黏土配置的结构检查，不能证明参考或美术匹配 |
| [build_demo.py](scripts/build_demo.py)、[test_soft_clay.py](scripts/test_soft_clay.py) | 柔和黏土工具的测试场景与集成验证，不是所有风格的成功案例 |

这些是可复用的基础黏土工具，不是要求未来所有风格都使用的统一着色器。读取实际接口后再调用；风格语义记录与工具严格 JSON 配置分开。脚本 API、默认 owner 与 `soft_clay_*` 标签保留兼容性。具体使用见 [soft-clay 工具说明](styles/soft-clay/references/usage.md)。

## 扩展和交付

新增风格只需增加 `styles/<style-id>/STYLE.md`、必要的局部资源并更新上表。描述选择条件、差异、校准方法与真实验证状态；共用内容引用本入口和通用建模，不再复制独立 `SKILL.md` 或工具。只有工具接口确实适合复用时才放入共享 `scripts/`，风格独有内容留在其目录。

交付时报告实际采用的风格 ID、混合规则、配方/配置、参考与校准证据、`.blend`/预览和未验证项。迁移路径与历史结果边界见 [迁移说明](references/migration.md)。不要把结构测试通过、覆盖百分比或目录迁移等同于视觉验收通过。
