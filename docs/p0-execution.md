# P0 执行链路与本轮状态

## 知识查找

知识索引扩展到现有活动参考资料。knowledge.json 的 excluded_paths 必须给出迁移/测量等非执行资料的排除理由；新增活动 Markdown 没有索引或排除声明将使 CI 失败。既有 Skill 名称与安装闭包保持不变。

检索使用知识卡片（标题、别名、领域、正文标题）的二值词频 BM25。context_exclusions 仅排除无目标领域证据的其他领域查询；domain_terms 支持混合背景，如 React 展示页面的 Blender GLB 导出。query_exclusions 保留具体不支持的意图，不声称解决任意语义或否定理解。新增回归案例放 dev，不冒充盲测。

## 收益约束

比较必须指定预先声明的 objective、minimum_distinct_tasks、所有成本的 max_mean_increase/max_per_run 和 protected_checks。示例在 evals/policies/success-with-cost-limits.json；数值仅为示例，真实项目须在运行前确定并锁定。

执行器在模型调用前计算 policy SHA-256，写入两个运行的 metadata.comparison_policy_sha256；比较时不匹配会拒绝正向结论，起始资产指纹也必须一致。缺策略、实际模型身份未观测、缺配对或样本不足保持 insufficient-evidence。成功率改善但越过成本限制判为 negative。成本目标也可直接选择耗时、tokens 或人工介入，使用预先声明的上界进行保守分析。结果依赖任务采样独立性，不能从少数相关任务推断整个能力。

## 真实 Agent 执行

任务胶囊：evals/capsules/wheel-origin。输入、用户任务、独立评分器、校准程序分别保存；Agent 只能看到任务、只读输入与安装的 Skill（移除 tests/evals/history 与测试脚本），无法看到仓库、评分器、黄金修复和其他运行。执行器使用 PID/文件系统隔离，关闭继承的远程执行入口，保留必要的代理和托管会话配置，不传递 GH/HF 凭据。使用当前 CLI 默认模型，不改写模型设置。

先执行评分器校准：

```shell
python tools/calibrate_capsule.py --capsule evals/capsules/wheel-origin --output .tmp/wheel-calibration
```

报告同时验证正确修复、合法的顶点重排修复、未修复偏心、误改受保护对象，并绑定任务/评分器/准备脚本哈希和 Blender 版本。任一文件或环境版本变化后必须重跑。

再显式运行（Linux bubblewrap 和可用的 Codex CLI 登录为前提）：

```shell
python tools/agent_benchmark.py --base bdf36e5 --head working-tree --policy evals/policies/success-with-cost-limits.json --calibration .tmp/wheel-calibration/calibration.json --output .tmp/live-wheel --repeats 3 --timeout 300
```

若当前命令所在外层沙箱无法建立用户映射，应在已获授权的外层执行同一隔离程序；执行器拒绝降级成无隔离模型评测。working-tree 是带内容指纹的开发快照；正式对比使用两个固定 Git 提交。输出目录必须是新的，失败记录不得覆盖。

每次输出冻结 Skill 指纹、源资产哈希、完整 JSONL 轨迹、耗时/用量、独立评分及结果。凭据副本只供 CLI 使用，退出后移除；不纳入证据归档。未获得完整模型回合和用量的运行标记 unknown，不计作 Skill 失败，也不产生正向结论。行为评分器不证明人体造型或视觉品质。

## 本轮实测

- 库索引由 23 条增至 92 条；现有参考资料显式索引或排除。
- 布料、UV、混合 React/Blender 导出及原有检索回归通过。
- 正向/负向/取舍/证据不足和成本超限控制案例通过；未绑定策略与未观察模型身份会阻断结论。
- Blender 4.3.2 中独立 wheel grader 的正确修复、合法替代、未修复、非目标对象破坏四个控制案例校准通过。
- 真实 CLI 尝试的文件系统隔离与任务准备通过，但模型服务返回 401 Unauthorized（认证令牌无法解析），并有附带远程服务 451 错误；没有完成模型回合。失败轨迹保留在 .tmp/p0/live-wheel-02 和 live-wheel-03，结论为 insufficient-evidence。需要恢复 CLI 有效登录后再执行；未创建或修改凭据。

因此，P0 的检索、约束和执行机制已落地；实际旧版/新版 Agent 效果对比仍被鉴权阻塞。P1 已补独立车轮评分校准与内容绑定证据机制，生产级手/车轮/角色的成套视觉校准仍待完成。P2 已增加分支/定期轻量检查及手动 Blender 双版本流水线配置，未宣称远端工作流、4.5 或目标引擎已运行。
