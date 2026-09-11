# Stage 1 页面使命与核心判断：实现说明

日期：2026年9月11日。

## 最终行为

- 页面使命在PLAN中使用既有logic字段。内容页缺失、空白或非字符串使命，audit-plan报PLAN_PAGE_MISSION_REQUIRED；“说明相关情况”等明显泛化使命只提示人工复核。
- page-source把logic作为page_mission带入精确证据上下文，不把使命加入来源事实，也不从标题或问题自动推造使命。
- AUTHOR依据原文及完整稿选择判断形式：单一有据判断可填写core_message；多个并列判断保留在完整稿和上屏模块；定义、分类、任务页可以没有总判断。
- 忠实模式填写core_message时，保持来源原生段落和分类标题。只有显式argument或analytical模式启用对应的论证结构要求。来源关系、数字、状态等既有检查继续执行。
- Final Script的可选mission与PLAN logic措辞不同时，audit-final提示AUTHOR_MISSION_PLAN_REVIEW。措辞差异不被直接认定为业务冲突；页面职责变化时先调整PLAN。
- Critic上下文同时提供页面使命，并分别审查使命落实、来源判断保全、阅读层级与语义完整性。

## 实现位置

- [流程合同](/Volumes/DOC/CyberPPT/.agents/skills/cyberppt-script-workflow/SKILL.md)与[忠实写作合同](/Volumes/DOC/CyberPPT/.agents/skills/cyberppt-script-workflow/references/faithful-authoring-contract.md)：明确生成时点、职责、判断的三种处理方式。
- [规划审计](/Volumes/DOC/CyberPPT/script_engine/analysis_audits/deck_plan.py)、[规划复核提示](/Volumes/DOC/CyberPPT/script_engine/plan_quality.py)：检查使命缺失和泛化，明确相邻比较的对象是页面使命。
- [精确来源上下文](/Volumes/DOC/CyberPPT/script_engine/page_source_packet.py)、[上屏Critic上下文](/Volumes/DOC/CyberPPT/script_engine/onscreen_quality.py)：传递既有使命，区分使命和来源判断。
- [作者字段检查](/Volumes/DOC/CyberPPT/script_engine/author_contracts.py)、[完整稿检查](/Volumes/DOC/CyberPPT/script_engine/full_copy_contracts.py)、[上屏检查](/Volumes/DOC/CyberPPT/script_engine/onscreen_contracts.py)：解除core_message对论证式结构检查的隐含触发。
- [最终脚本审计](/Volumes/DOC/CyberPPT/script_engine/analysis_audits/final_orchestrator.py)：增加可选使命与规划的复核提示。

## 验证

执行仓库.venv/bin/python3：

```text
-m pytest tests/script_engine tests/test_faithful_authoring_mode.py -q
319 passed
```

[新增回归测试](/Volumes/DOC/CyberPPT/tests/script_engine/test_mission_and_judgment.py)覆盖使命缺失、来源上下文传递、PLAN禁止预写核心判断、有或无核心判断的忠实页面、两个并列来源判断、来源外必要性关系提示、使命差异提示及使命不进入上屏正文。既有analytical字段要求测试继续通过。

此前表达诊断会对示例中的两处标题与正文重复给出真实提示。本轮同步更新[CLI测试](/Volumes/DOC/CyberPPT/tests/script_engine/test_cli.py)、[质量策略集成测试](/Volumes/DOC/CyberPPT/tests/script_engine/test_quality_policy_cli_integration.py)及[上下文测试](/Volumes/DOC/CyberPPT/tests/script_engine/test_content_planning_fusion.py)的预期，保留提示并继续验证未知硬错误会阻止交付。

当前电力合作方案项目：audit-plan、audit-final和check-sync均通过；规划原有P17使命范围提示仍保留。实际page-source p05返回使命“呈现分散供给问题及连接、可信使用和服务运营要求。”，来源解析无错误。以上项目检查均为只读，本轮没有修改项目脚本或重新生产图片。

## 能力边界

代码可确定字段是否存在、传递使命并定位可疑表达。使命与内容是否一致、综合判断是否充分受来源支持，仍需主Agent阅读原文和完整稿确认。没有新增自动作者生成器、强制核心结论字段、平行内容权威或审批文件。
