# 装配比较与转轴优化

入口 `scripts/assembly_diagnostics.py`，Python 3.10+ 和 Pillow；不新增模型服务。所有输出必须选新目录。这里是诊断工具，可读取编译失败版，不会修改 manifest、签发资产批准或改变目标范围。诊断图的检查范围和连续动画审阅分开。

## 像素比较

```bash
python scripts/assembly_diagnostics.py pixels --reference source-subject.png --candidate reassembled.png --output /project/qa/pixels-v1
```

相同画布和坐标下比较 alpha 与预乘 RGB，忽略完全透明区的 RGB。输出差异像素数、最大/平均/RMS 的逐像素最大通道误差、变化包围盒、非零 alpha 支持区 IoU、误差灰度图和红色叠加图。默认阈值 0；`--threshold 2` 仅改变统计阈值，不更改编译验收。不同尺寸拒绝；不自动缩放或对齐，以免把装配偏移抵消。IoU 不是半透明度相似度。

先比较原姿态，再比较相同姿态下的修复前后。原姿态零差分不能证明转轴正确：错误转轴在零旋转时也能完全回组。

## 转轴与层级比较

```bash
python scripts/assembly_diagnostics.py axes --reference approved/manifest.json --candidate candidate/manifest.json --pose pose.json --tolerance 1 --output /project/qa/axes-v1
```

`pose.json` 使用原生 `angles/translations/scales`。可省略以比较静止关节。按节点 ID 报告缺失/新增节点、父级改变、姿态下关节位置误差（像素）和世界 X 轴方向差（度），绘制参考绿色、候选红色与误差连线。相同坐标/尺度是前提；动姿态比较要求节点集合一致。`--tolerance` 只标记关节位置是否在容差内，不代表轴向或父级通过。

参考 manifest 必须来自独立观察或已审版本，不能拿同一个错误骨架自己比自己。全局画布的 X 轴正向和顺时针角度沿用 manifest；工具不处理真实三维骨轴、透视或相机配准。

## 扫转连接

配置示例，坐标仅说明格式：

```json
{
  "node": "forearm", "range": [-30,30], "step": 1,
  "parts": ["upper_sleeve","fore_sleeve"], "radius": 20,
  "anchors": [[210,300],[210,300]],
  "base_pose": {"angles":{"body":5}}
}
```

```bash
python scripts/assembly_diagnostics.py sweep --manifest character/manifest.json --config sweep.json --output /project/qa/sweep-v1
```

每个采样角度输出双色组件图、关节邻域圈、两锚点连线；报告邻域重叠像素、两指定锚点距离、alpha 是否触及画布边缘，及端点/中间汇总图。`anchors` 是两个部件各自参考画布上的真实连接点，可省略；省略后没有接触距离结果。父级运动会被计算；目标范围可超出当前限位以诊断失败，不因此修改允许范围。采样包括终点，至多约 721 个样本。

圈内相交不代表整条宽袖无裂缝；透明镂空、前后遮挡和片间有意间隙都可能产生零重叠。触边只作可能裁剪提醒。必须看整条接缝与连续运动；图像序列可交现有 `toolbox media` 生成 MP4，不另写编码器。

## 从测量拟合建议转轴

```bash
python scripts/assembly_diagnostics.py fit-pivot --config observed-landmarks.json --output /project/qa/fit-v1
```

配置 `source_size: [宽,高]` 和至少两条 `observations`：每条含 `angle`、`before: [x,y]`、`after: [x,y]`。采用已知顺时针旋转角，通过最小二乘拟合 `after = R(before-pivot)+pivot`，输出建议 pivot、每条观测残差、RMS 和图。零旋转等退化输入拒绝。

适用条件：父级固定、片件刚性、无相机运动/缩放，特征点为独立测量，角度有证据。视频存在父级/相机运动时先可靠变换到共同父级坐标，否则不可直接拟合。残差大时先检查模型假设、角度和标点，不用增加自由度把错误拟合成低误差。此工具不自动从视频跟踪特征点，也不从同一错误 rig 生成观测来证明自己正确。

建议只写入候选 manifest，新版本重编译后重做：原姿态像素 → 轴比较 → 目标扫转 → 正式镜头。优化目标同时包括连接、轮廓、纹样和动作，不能只追求邻域相交面积最大。

## 前后层级与运动父级校验

```bash
python scripts/assembly_diagnostics.py layers --manifest character/manifest.json --config layers.json --output /project/qa/layers-v1
```

配置示例：

```json
{
  "occlusion_rules": [
    {"front":"hand", "back":"torso"},
    {"front":"upper_sleeve", "back":"elbow_patch", "frames":[10,30], "region":[100,120,250,300]}
  ],
  "expected_parents": {"forearm":"upper_arm", "hand":"forearm", "body":null},
  "frames": [
    {"frame":0,"pose":{}},
    {"frame":10,"pose":{"angles":{"forearm":-30}}}
  ],
  "alpha_threshold":1
}
```

规则也可保存在原生 manifest／编译标注的 `occlusion_rules`、`expected_parents` 中，编译时保留。配置同名字段显式覆盖 manifest 规则，报告只验证实际传入规则；不要用空规则来冒充已验证。`front/back` 指绘制片 ID，父级规则指控制节点 ID；两者不可混用。

- 帧段为闭区间，缺省对所有帧有效；`region` 可选，采用该采样帧的画布坐标半开矩形 `[x0,y0,x1,y1]`。区域不跟随关节移动。
- 先检查引用、帧段及预期父级，再按规则生效区间检查遮挡环。只在同一有效时间内构成环才报冲突，不把不同帧段的合法前后切换合并成假环。
- 实际顺序遵循现有渲染器：z 值升序，同值按 parts 数组顺序。顺序错误但组件不重叠只报 warning；实际可见的错误重叠报 fail。
- 晚绘制的不透明第三片完全遮住该处时，记录隐藏的错误顺序，保留 warning；半透明第三片不会消除底下错层的风险。
- 每帧输出组件 RGB ID 图、颜色映射及红色违规叠加图；报告重叠面积、可见违规面积、未采样规则、父级错误和遮挡环。ID 图表示超过阈值的最上层 alpha 支持归属，不等同皮革材质的最终颜色贡献。
- 默认 alpha 阈值 1，包含微弱透明边缘；调整阈值只改变此诊断，不改变原图或编译差分。

`fail` 退出码 2；`warning` 和 `pass-sampled` 退出码 0，报告必须保留 warning。不存在任何声明规则时拒绝执行，不输出虚假的通过。只检查显式帧姿态，不推断两帧间运动，不批准连续片段。动态规则可以发现静态 z 顺序在某帧失效，但当前 IO 不会因此自动生成换层动画；需另做换层后端或拆成前后绘制片并验证。

新编译资产在参考帧 0 自动检查携带的规则：父级错误、遮挡环和该姿态的可见错层会将编译置为 blocked，细节保存在 `preview/layers/`。仅在其他帧生效的规则仍须另行传入实际动作姿态验证；原姿态通过不覆盖动作阶段。历史 manifest 不因兼容加载而获得新的层级验收事实。
