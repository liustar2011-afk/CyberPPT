# 精简 evidence_fit_review 的 counter_case 强制校验

## 背景

延续 [2026-08-28-source-comprehension-skill-proposal.md](2026-08-28-source-comprehension-skill-proposal.md) 里"单人单机小工具，来源追溯只服务于不丢失源材料"的定位，追查 Stage 01 里还有哪些机制属于"agent 撰写的结构化论证 + 硬阻断质检"这一类真正的时间成本来源。

发现 `cyberppt-script-plan`/`cyberppt-script-author` 的 `evidence_fit_review`（由 [script_engine/analysis_audit.py](../../script_engine/analysis_audit.py) 的 `audit-plan`/`audit-final` 强制校验）比语义层的 `counter_case` 规模更大：要求每一页、每一个带证据的上屏模块都写一份包含 `question`/`items`/`counter_case`/`verdict` 的结构化自审。

## 独立技术判断

最初建议整体放松这套机制、改由人工审查兜底，被用户否决：本仓库的目标就是提高自动化水平，把自动质检换成人工审查是方向性倒退，不是"减负"。

重新拆解后发现 `evidence_fit_review` 内部两类字段性质不同：

- **真正的自动化质检**（`fit` 枚举阻断 `topic_only`/`no`/`uncertain`、`evidence_refs` 缺失/重复/未分配检查、`verdict` 阻断）——脚本能确定性判断对错，删掉就是把工作转嫁给人工，不能动。
- **纯撰写成本、无对应自动校验价值的字段**（`counter_case`）——脚本只检查"是否写了非空、非'无'的文字"（长度 ≥4、不在几个禁用词列表里），不校验这段反例是否真的成立、是否真的够强。也就是说，这个字段能被自动验证的只有"有没有写"，不是"写得对不对"，要求它只增加撰写时间，不增加自动质检能力。

`SUPPORT`：只去掉 `counter_case` 的强制校验，其余全部保留。

## 改动

1. [script_engine/analysis_audit.py](../../script_engine/analysis_audit.py)：`_evidence_fit_review_issues` 删除 `counter_case` 的存在性/非空/禁用词校验。`fit` 阻断、`evidence_refs` 覆盖检查、`verdict` 阻断均未改动。
2. [script_engine/plan_review.py](../../script_engine/plan_review.py)：只读渲染的"最强反例"行改为按 `counter_case` 是否存在条件输出，不再假设它总有值。
3. [.agents/skills/cyberppt-script-plan/SKILL.md](../../.agents/skills/cyberppt-script-plan/SKILL.md)：删除"strongest alternative parent"作为必答问题；`counter_case` 改为可选，说明它不再机器校验。
4. [.agents/skills/cyberppt-script-author/SKILL.md](../../.agents/skills/cyberppt-script-author/SKILL.md)：同步移除 `counter_case` 的必填措辞。
5. [docs/CYBERPPT_WORKFLOW.md](../CYBERPPT_WORKFLOW.md)：两处提及 `evidence_fit_review`/来源适配质询的段落同步移除"最强反例"作为必填项。
6. [tests/script_engine/test_semantic_guardrails.py](../../tests/script_engine/test_semantic_guardrails.py)：原测试断言"写`counter_case: 无`会被拦截"，已按新行为改写；新增一条测试锁定"`counter_case` 可选且不参与校验"的行为，防止未来被无意改回强制。

## 验证

`.venv/bin/python3 -m pytest tests/` 前后对比：改动前后均为 21 项失败（全部是与本次改动无关的既有失败——缺失的 fixture 文件、imagegen/script_quality 模块化基线等），通过数从 1429 增至 1430（新增的一条测试）。未引入新的失败。

## 未改动

- `fit: topic_only`/`no`/`uncertain` 的阻断行为。
- `verdict` 为 `rename`/`move`/`split`/`reject` 时阻断 AUTHOR、退回 PLAN 修复的行为。
- `evidence_refs` 缺失/重复/未分配的结构化检查。
- 存量项目数据（按此前约定，不处理迁移）。
