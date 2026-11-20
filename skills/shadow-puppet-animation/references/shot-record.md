# 记录与示例

复用项目已有记录结构；下列是最小信息契约，不是新增渲染器 API，也不要求重复生产总控。拆件仍保留 splitter 的原生 manifest；由项目适配层关联这些记录。

## 最小记录

| 记录 | 内容 |
|---|---|
| 参考 | URI／本地路径、SHA-256、时间码、审阅方法、实见／推断／建议、限制 |
| 风格 | 身份锚点、角色与环境配色、纹样尺度、平面程度、材质光感、目标参考维度 |
| 资产 | ID／版本／文件引用、朝向状态、控制父级、绘制层序、枢轴、接触锚点、隐藏区策略、目标和已验收范围 |
| 镜头 | shot_id、fps、帧区间及时间原点、场所、相机、开始／结束状态、注意力中心、上下镜连续性 |
| 动作事件 | actor、target、动作意图、阶段、接触／释放／命中时间、锚点、结果、声音同步点 |
| 审阅 | 产物版本／哈希、范围、方法、时间码、通过／失败／未验证、证据与剩余问题 |

## 可执行到后端前的镜头示例

这是原创制作示例，不是对参考 A/B 的逐帧转录。具体数字为排练起点，必须实播调整。

```yaml
shot_id: SH010
status: planned
purpose: 行人停下，把篮子交给同伴后离开
clock:
  fps: 30
  space: shot-local-frame
  interval: '[0, 180)'
  global_start_frame: 900
assets:
  - id: walker
    state: right-facing-carry
    manifest_ref: resolve-existing-character-manifest
  - id: receiver
    state: left-facing-wait
    manifest_ref: resolve-existing-character-manifest
  - id: basket
    anchors: [handle, base]
movement_owners:
  root_paths: project-backend
  limb_pose: character-animation
  basket: contact-state-controller
  background: static
  camera: static-orthographic
beats:
  - frames: '[0, 60)'
    intent: 持篮靠近
    contacts: ['walker.hand -> basket.handle', 'alternate support feet -> ground']
    result: 到达同伴前
  - frames: '[60, 90)'
    intent: 停步并递出
    contacts: ['walker.hand -> basket.handle', 'both feet -> ground']
    result: 篮子进入双方手可及空间
  - frames: '[90, 105)'
    intent: 对方接稳
    contacts: ['walker.hand -> basket.handle', 'receiver.hand -> basket.handle']
    result: 双方短暂共同持握
  - frames: '[105, 135)'
    intent: 交出篮子
    contacts: ['receiver.hand -> basket.handle']
    result: walker 松手；basket 切换控制时保持世界位置连续
  - frames: '[135, 180)'
    intent: 行人离开
    contacts: ['receiver.hand -> basket.handle', 'walker support feet -> ground']
    result: 同伴持篮留在场内；延续到下一镜
occlusion:
  - 递物时袖片不得盖住双方手与提手的关系
review_required:
  - 原速确认停步、递物与离开的意图
  - 逐帧确认接触重叠阶段和控制切换无跳变
  - 检查宽袖搭接、脚底支撑、篮子尺寸与下一镜状态
```

示例未绑定真实资产，不可直接称可渲染。执行时解析资产引用，填写真实锚点与层序，按后端支持转换为实际时间线；不能将示例中的文字约束直接当作已实现的 IK。

## 原速不可用时的记录示例

```yaml
scope: SH010
artifact_sha256: actual-output-hash-required
methods:
  still_frames: reviewed
  sampled_sequence: reviewed
  continuous_original_speed: unavailable
  audio: not-reviewed
conclusion: 采样中未见明显轮廓断裂；接触连续性、节奏与音画同步未验证
quality_claim: 不可声明达到参考片动态品质
```

## 风险任务走查

发布或升级本技能时可用 [行为评估案例](../evals/evals.json) 对指令进行前向测试。给执行者原始任务与必要素材，再对照判据，不把期待答案预先塞进任务。无真实资产／渲染和原速审阅时，只能记录为规划走查，不能记为作品验证通过。
