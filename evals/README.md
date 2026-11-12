# 评测入口

检索：`python tools/run_evals.py retrieval --split test --output .tmp/retrieval.json`。种子查询包含中英文、错误对象、明确不适用条件和域外问题；此集合用于回归，不宣称独立盲测。

任务契约在 Blender Skill evals/task-suite.json，包含手/轮/绑定的创建、修复、优化与回归。Agent 或操作者需先准备真实输入资产、记录哈希并在隔离工作区执行；不能只转述 prompt 作为运行。技术夹具只校准工具与错误检测，不等于这些任务已通过。

外部记录格式见 [运行记录 schema](schemas/task-run.schema.json)。metadata 包括 revision/model/environment/budget/rubric_version；records 每项有 task_id/repeat/status/severe_error/elapsed_seconds/context_tokens/human_interventions/checks。checks 按任务检查 ID 记录 status；passed 附 evidence 数组（path、sha256），visual 还需 reviewer；unknown/skipped 必须 reason。证据路径相对 evidence-root，禁止逃逸或过期哈希。结构校验不鉴定图片中的内容，审阅者仍承担判断责任。

验证：`python tools/run_evals.py tasks --suite skills/blender-python-modeling/evals/task-suite.json --records <run.json> --evidence-root <run-dir> --output <report.json>`。

比较：`python tools/compare_evals.py <base-report.json> <head-report.json> --output <comparison.json>`。环境/模型/预算/评分版本不同则拒绝比较；缺配对或未验证标记为证据不足。当前比较器仅给任务成功率的保守建议，成本变化单独列出，不能据此自动宣称成本目标达成。发布前仍需核对预先声明的收益目标与回归限制。

技术实机测试：`python tools/check.py --group blender --blender /path/to/blender`。隔离临时目录生成带正确/错误权重的最小夹具、偏心运动反例及可导出绑定；它们不是生产级手/车轮样例。新规范仍为 experimental，真实任务和视觉验收需独立执行。

独立验收：`python tests/test_reconstruction_acceptance.py` 覆盖自然语言检索、近域排除、未知事实、收益判定控制记录及正式提交快照的锁定安装；这些测试不调用模型。Blender group 还运行真实几何的偏心与缺失权重修复实验，生成诊断渲染。详见 [重构能力验证](../docs/verification-results.md)。
