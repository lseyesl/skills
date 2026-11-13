# glTF/GLB 导出、规范验证与消费端验收

适用：要求 glTF/GLB 的资产；FBX/其他格式沿用 [导出约定](../../export-and-packaging.md)。依据：[Khronos I/O、Validator 与样本](../../sources/production-sources.md)。

## 三层检查

1. **源场景与交付副本**：记录对象、材质、UV、纹理、骨架/动作/形态键和扩展需求。保留可编辑源；程序化着色、约束和模拟不自动等于导出格式支持，按目标路线烘焙或转换。
2. **格式/资源检查**：对导出文件运行 [gltf_audit.py](../../../scripts/gltf_audit.py)，记录 Validator 版本、输入 SHA-256、errors/warnings 与完整 JSON。错误必须处理；警告按目标和 issue code 逐条解释，不一律当成通过或失败。
3. **隔离重载与消费者检查**：复用 [现有 GLB round-trip](../../export-and-packaging.md#static-textured-glb-audit) 的适用范围。再在目标查看器/引擎验证尺度、轴、轮轴/挂点、材质、透明、切线、动画/根运动与形态键。静态检查不能代替动画交付。

## 运行方式

在消费项目显式安装/提供 gltf-validator 的已锁定版本及 Node.js；库安装器不替用户安装外部工具。host 侧调用示例：

```shell
python <skill-dir>/scripts/gltf_audit.py <asset.glb> --validator-module <project>/node_modules/gltf-validator --report <run-dir>/gltf-report.json
```

工具仅本地读取文件，不上传。缺依赖、超时或工具异常是 blocked，不等于资产不合法；输出不能覆盖输入或旧报告。外部 .gltf 资源限制在资产目录内，跨目录资源需先明确整理为交付包。

格式合法但目标扩展不支持时回到导出路线；Blender 正常而重载异常时检查选择、烘焙/动作范围、轴和导出器版本；材质不同则检查色彩、贴图和支持的节点/扩展。按 [交付与优化验收](../../acceptance/gltf-delivery.md) 交付。
