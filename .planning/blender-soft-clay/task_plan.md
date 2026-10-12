# Blender Soft Clay

## 目标与范围
在 skills/blender-soft-clay 实现跨项目的柔和低多边形黏土风规范、bpy 工具、示例与执行验收。保留已有工作。初始要求不提交；用户随后明确授权提交并推送本任务改动。

## 阶段
1. [complete] 分析现有 Blender Skills、脚本、依赖及可用 Blender。
2. [complete] 设计能力边界、配置、所有权与版本兼容策略。
3. [complete] 实现精简 Skill、渐进式参考、材质/灯光/渲染/动画/质量工具。
4. [complete] 通用场景执行验证、渲染视觉检查、跨工程和异常测试。
5. [complete] 交付示例、测试报告和限制；检查无关文件未变动。

## 决策
- 独立新任务；现有 .planning/blender-skill 是通用 Blender Skill 任务，使用本目录。
- 优先遵循当前仓库的所有权、数据 API、持久脚本和渐进式文档约定。
- 测试生成物放 .tmp/blender-soft-clay，Skill 内仅保留可复现源文件及报告。
- 工具仅依赖 bpy/bmesh/mathutils 和标准库；与通用 Blender Skill 为工作流依赖，无 Python 跨 Skill 导入。
- JSON 配置统一风格参数；严格拒绝未知键和无效值，运行时探测引擎、色彩枚举、节点插槽与 Action 通道。
- 灯光/材质按 owner + scene 分域；动画仅修改明确列出的目标并复制非自有或共享 Action。
- 分开结构检查、图像有效性与人工视觉验收，不把自动检查通过等同于动画无穿模。

## 错误
- 首次 smoke test：OCIO RNA 枚举仅返回静态 NONE 占位，误拒绝 AgX。改用属性赋值校验真实动态枚举并保留 RNA 诊断。
- 首轮渲染成功但结构 QA 拒绝前景 pebble 包围盒取景；扩大默认相机距离和留白后回归。
- 后台 Blender 沙箱内 Metal 启动崩溃（Python 未执行）；获准沙箱外执行后正常。
- 新负例发现 Cycles 修改器必须位于首位，循环工具增加对任何艺术修改器的前置冲突检查；负例恢复需在 FCurve.update 后重新获取关键帧 RNA 指针。
