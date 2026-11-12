修复 inputs/source.blend 中名为 Wheel 的车轮。旋转时轮胎中心会绕圈，应让它绕自身轮轴中心旋转。

保留静止帧中所有轮胎顶点的世界位置，以及 PreserveMe 对象和原文件。保存为 output.blend，并将诊断、选用方法、实际验证和限制写入 result.md。

本任务明确提供命令行 Blender（可用 blender --background），允许后台执行；本评测没有 MCP 服务，不需要启动或配置 MCP。可用的 Skill 在 .agents/skills 中，按需检索和读取。不得修改 inputs/source.blend。
