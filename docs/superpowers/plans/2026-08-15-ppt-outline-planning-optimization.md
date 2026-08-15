# PPT Outline Planning Optimization Implementation Plan

> For agentic workers: execute this bounded plan task-by-task with tests after each contract change.

Goal: 将正式 `ppt-outline-planning` 补齐为来源绑定、作者化、分层门禁和可交接的一体化 Outline 规划阶段。

Architecture: 保留现有 `prepare.py`、`generate.py`、`validate.py`、`render.py` 的单一生产链，在其上增加作者化输入准备器和编排入口。层四只消费已验证的层三语义产物；概念、关系和论点节点只做确定性绑定，不重新解释源材料。handoff 只接受作者化完成且 Outline 门禁通过的层四产物。

Tech Stack: Python 3.12、stdlib JSON/pathlib、现有 unittest/pytest、Graft。

Global Constraints

- 保留所有现有未提交修改，不覆盖用户文件。
- 唯一路线为 `cyberppt-source-foundation → business-semantic-understanding → ppt-outline-planning → cyberppt-handoff → cyberppt-write-single-page`。
- 候选 `mechanical_draft` 可以结构校验，但不得通过交接门禁。
- 不新增审批、哈希、回执、attempt、ledger 或平行事实源。
- 不把核心判断、受众、场景、行动目标交给确定性生成器猜测。
- 生成器修改后必须重新生成并验证真实 V16 派生产物。

## Task 1: 定义作者化准备器、语义绑定和分层门禁

Files:

- Create: `.agents/skills/ppt-outline-planning/ppt_outline_planning/authoring_spec.py`
- Create: `.agents/skills/ppt-outline-planning/ppt_outline_planning/status.py`
- Modify: `.agents/skills/ppt-outline-planning/ppt_outline_planning/generate.py`
- Modify: `.agents/skills/ppt-outline-planning/ppt_outline_planning/validate.py`
- Test: `tests/test_ppt_outline_generator.py`

接口：

- `prepare_authoring_spec(semantic_dir, outline_dir, output_path, force=False) -> dict`
- `build_layer4_status(deck, plan, validation) -> dict`
- 生成器为每个内容页写入 `primary_argument_node_id`、`source_argument_node_ids`、`source_evidence_node_ids`、节点角色/权重/状态、`concept_ids`、`relation_ids`。

## Task 2: 增加页面预算、合并和附件处置规则

Files:

- Modify: `.agents/skills/ppt-outline-planning/ppt_outline_planning/generate.py`
- Modify: `.agents/skills/ppt-outline-planning/ppt_outline_planning/validate.py`
- Modify: `.agents/skills/ppt-outline-planning/ppt_outline_planning/authoring.py`
- Modify: `.agents/skills/ppt-outline-planning/references/outline-contract.md`
- Test: `tests/test_ppt_outline_generator.py`

接口：

- authoring spec 可声明 `merge_groups`、`page_budget`、`attachment_disposition`。
- 生成器只按明确声明合并；附件默认 `trace_only`，未经作者决定不得进入主内容页。
- 校验报告同时给出页面预算、合并、附件和事实处置结果。

## Task 3: 提供一键生成—校验—渲染编排

Files:

- Create: `.agents/skills/ppt-outline-planning/ppt_outline_planning/pipeline.py`
- Create: `.agents/skills/ppt-outline-planning/scripts/plan.py`
- Modify: `.agents/skills/ppt-outline-planning/ppt_outline_planning/__init__.py`
- Modify: `.agents/skills/ppt-outline-planning/SKILL.md`
- Test: `tests/test_ppt_outline_generator.py`

命令：

```bash
python scripts/plan.py <semantic-dir> -o <outline-dir> --force
python scripts/plan.py <semantic-dir> -o <outline-dir> --authoring-spec <authoring-spec.json> --force
```

编排顺序固定为生成、校验、写入报告、渲染；校验失败不得渲染。

## Task 4: 收紧 handoff 交接资格

Files:

- Modify: `.agents/skills/cyberppt-handoff/cyberppt_handoff/io.py`
- Modify: `.agents/skills/cyberppt-handoff/references/handoff-contract.md`
- Test: handoff focused tests and Outline regression tests

规则：`outline-report.json.status=ok` 只代表结构和来源校验通过；当 Outline 的作者化状态不是 `author_edited` 时，handoff 明确返回 `OUTLINE_AUTHORING_INCOMPLETE`。

## Task 5: 文档、回归和真实项目验证

Files:

- Modify: `.agents/skills/ppt-outline-planning/references/authoring-spec.md`
- Modify: `.agents/skills/ppt-outline-planning/SKILL.md`
- Test: focused planning/handoff tests and repository regression suite

验证：运行定向测试、相关回归测试、`git diff --check`，再以真实 V16 semantic 目录生成临时 candidate，运行一键编排、检查分层状态、渲染 Markdown，并对现有正式产物执行 handoff validation；不覆盖用户已有正式 Outline，除非明确确认。
