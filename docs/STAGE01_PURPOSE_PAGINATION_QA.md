# Stage 01 用途与分页：代码变更及验证

本次将用途接入 Deck Plan 合同、规划审阅、作者预检和最终交付校验。分页仍由主 Agent 对照来源执行，代码提供用途相关审阅重点与确定性阻断。

## 实际行为

| 环节 | 当前行为 |
|---|---|
| PLAN 输入 | `delivery_mode` 必须选择 `presented` 或 `self_read`；`pagination_rationale` 必须说明实际拆分合并理由，可同时记录已知时长、页数约束 |
| 共同分页原则 | 一页只表达一项核心内容；两种用途对多事项使命或多个问句统一产生 `PLAN_SINGLE_CORE_REVIEW`，供主 Agent 对照来源判断 |
| 演讲辅助审阅 | 围绕核心内容突出关键支撑，核对解释层级与讲解负担 |
| 独立阅读审阅 | 围绕同一核心内容补足上下文、解释与条件；相邻页共享来源时检查连续性，仅同一核心内容可考虑合并 |
| 人工规划稿 | 展示用途、分页理由及对应审阅重点 |
| Author Preflight | 当前 v2 规划用途或分页理由缺失时阻断；用途变化后现有输入绑定失效 |
| 最终审计与交付 | 最终脚本用途必须与规划一致；不一致时阻断，保留已有 Markdown 交付文件 |

没有新增字数配额、自动分页算法或上屏文案字段。填写分页理由只证明字段完整，主 Agent 仍须核对其与来源及实际页面边界相符。现有 v2 规划缺少新字段时，按用户意图补齐后继续；不静默赋予独立阅读用途。

## 验证

- 修改前相关回归测试：541 项通过。
- 用途链路新增 15 项测试，共同分页原则再新增 6 项测试；合计相关回归测试：562 项通过。
- 验证缺失用途、未知用途、缺失或空白分页理由会使实际 `review-plan` CLI 返回失败。
- 同一套页面范围切换用途，审阅策略与定向提示随之变化，输入内容保持不变。
- 两种用途均在实际 `review-plan` CLI 中显示多主题提示和共同原则；同一主题的多条支撑或完整流程不因条目数量被强制拆分。
- 验证完整来源 Packet 不能绕过用途缺失；修改用途使原预检失效。
- 两种用途均经真实交付函数写入 Markdown；最终用途漂移被交付函数和最终审计阻断。
- `git diff --check` 通过。

测试命令：

```bash
.venv/bin/python3 -m pytest tests/script_engine tests/test_content_route.py tests/test_stage02_field_contract.py -q --tb=short
```

尚未执行真实源材料的两套生成式分页对比，亦未生图。本次测试证明代码传递、用途相关审阅与阻断行为，实际分页质量仍需主 Agent 的来源审阅。

## 修改文件

- [Deck Plan 合同](../contracts/deck-plan.schema.json)
- [规划策略与一致性校验](../script_engine/plan_quality.py)
- [规划审计](../script_engine/analysis_audits/deck_plan.py)
- [人工规划审阅](../script_engine/plan_review.py)
- [作者预检](../script_engine/author_preflight.py)
- [最终语义审计](../script_engine/semantic_contract/audit.py)
- [正式脚本交付](../script_engine/delivery_commands.py)
- [规划示例](../examples/deck-plan.example.json)
- [新增用途测试](../tests/script_engine/test_plan_purpose.py)
- [预检与交付测试](../tests/script_engine/test_author_preflight_gate.py)
- [规划测试样例更新](../tests/script_engine/test_content_planning_fusion.py)
- [规划审阅测试样例更新](../tests/script_engine/test_plan_review_and_internal_voice.py)
- [项目状态测试样例更新](../tests/script_engine/test_project_status_stage1_gate.py)
- [来源忠实度测试样例更新](../tests/script_engine/test_v04_source_fidelity.py)
- [仓库规则](../AGENTS.md)
- [Stage 01 Skill](../.agents/skills/cyberppt-script-workflow/SKILL.md)
- [主流程文档](CYBERPPT_WORKFLOW.md)

本次未修改其他任务的源材料映射与图片文字审计代码，未创建提交。
