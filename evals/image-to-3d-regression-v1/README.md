# 图片模型失败样本的技术回归

本目录是对已知失败的局部修复实验，**不是新一轮独立 Agent 图片重建评分**。沿用此前输入和原始输出，不修改 `image-to-3d-baseline-v1` 或其分数；新结果分别保存于新输出目录。

- `replay_repairs.py`：从已知杯子和轮毂诊断模型派生副本，重放已确定的轴心封口、把手距离和辐条连接修复；验证真实旋转与隔离导出。保留源文件哈希。杯把只是表面可达，连续陶瓷焊接/打印验收仍未认证；轮毂的胎纹、文字、强度和参考形状仍不完整。
- `rig_character.py`：从已见女孩静态模型制作预算派生网格，使用明确关节及分区权重创建持久骨架和基础关节 clip，再比较 GLB 重载的 skin、层级、材质与采样表面。材质明确采用源记录调色板的常量 PBR 近似，未烘焙原程序材质；不是外观等价或完整动画角色认证。

两者都拒绝已有输出目录。每次候选尝试保留失败和 source/recipe 哈希，不能把开发中的多次修复当成第一次就成功。其预算和任务起点与初轮从图片开始的模型任务不同，不得直接比较总分或成功率。

```shell
blender --background --factory-startup -t 4 --python-exit-code 1 \
  --python evals/image-to-3d-regression-v1/replay_repairs.py -- \
  --baseline .tmp/image3d-baseline-20261113 --output /new/output/known-defects

blender --background --factory-startup -t 4 --python-exit-code 1 \
  --python evals/image-to-3d-regression-v1/rig_character.py -- \
  --source /static-fitter-output/scene.blend \
  --config skills/blender-python-modeling/examples/clay-girl-fit/character.json \
  --output /new/output/character-derivative
```

正式泛化/收益评测仍需运行前绑定的同条件协议、可观测模型身份/成本、隔离任务和独立评分。已知缺陷修复记录不代替这些证据。
