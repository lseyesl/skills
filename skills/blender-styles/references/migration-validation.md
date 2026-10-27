# 迁移复核

本页记录统一目录后的复核，独立于 soft-clay 的历史验证。检查范围为文件/引用完整性及迁移后的工具执行；不构成手捏橡皮泥风格已通过视觉校准的证明。

## 执行方式

```bash
blender --background --factory-startup -t 2 --python-exit-code 1 \
  --python skills/blender-styles/scripts/test_soft_clay.py -- \
  --output .tmp/blender-styles/migration-check --render
```

输出目录需要为空。集成套件覆盖结构、重复执行、源数据保护、配置、材质、时间采样、绑定、独立场景，以及低分辨率 Cycles/EEVEE、图像序列和原生视频输出。自动检查不证明目标参考或风格外观匹配。

## 2026-10-27 执行结果

- Blender **4.5.12 LTS**、Python **3.11.11**，在新的 `blender-styles/scripts/` 路径执行原集成套件，**25/25 检查通过**。机器摘要见 [migration-validation-summary.json](migration-validation-summary.json)，完整运行报告位于 `.tmp/blender-styles/migration-check/test-report.json`。
- 26 张 PNG 经过解码检查：Cycles 横向预览、EEVEE 竖向预览和 24 帧低分辨率序列；原生 H.264 输出检查通过。本轮没有额外执行完整视频解码/播放验收。
- 查看了 Cycles 和 EEVEE 的实际静帧。示例保持柔和黏土的颜色与形状；低采样 EEVEE 预览仍有远处地板边缘，属于工具测试画面，不是最终镜头。
- 静态检查通过：唯一风格 Skill 入口、两套风格索引、本地链接、YAML/JSON/Python 语法与字段、活动配方导入和 `git diff --check`。
- 8 个 Python 源文件、2 个示例配置和 1 张风格参考图与迁移前的 SHA256 相同。脚本 API 与所有权标签保持兼容。

本轮证明迁移后的共享工具继续执行。手捏橡皮泥没有新增校准样模，仍为待视觉校准状态；既有模型的参考匹配问题也没有因目录迁移得到修复。
