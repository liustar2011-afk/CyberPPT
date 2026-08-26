# CyberPPT Outline 生成质量问题与修复方案

## 1. 问题结论

当前 `ppt-outline-planning` 生成的 V16 Outline 不得作为正式 Outline 使用。

当前候选产物能够通过结构校验、来源绑定校验和事实覆盖校验，但页面作者化质量不合格。结构合法不等于页面判断正确，也不等于可以进入 handoff。

已核验的实际候选产物：

- [page-plan.json](/private/tmp/cyberppt-v16-outline-CCx4pp/outline/page-plan.json)
- [ppt-outline.md](/private/tmp/cyberppt-v16-outline-CCx4pp/outline/ppt-outline.md)

真实 V16 项目的 Source Foundation 和语义产物可以继续复用，不需要重新读取 DOCX 或重建上游语义层。需要整体修复的是 Outline 生成、作者化质量校验和交接门禁。

## 2. 已确认的问题

### 2.1 P04 的核心判断取错

P04「一、建设背景」实际生成的核心判断为：

```text
依托电力领域数据基础设施开展
```

该内容是文档标题类首条事实的截断，不能承担建设背景页面的核心判断。

源材料中建设背景的有效事实至少包括：

- 电力业务数字化、市场化和智能化程度持续提升，跨主体数据协同需求不断增长；
- 分散的数据资源和专业能力尚未形成稳定、规模化的服务供给；
- 数据供需对接、产品封装、授权执行、服务计量和价值结算尚未形成完整机制；
- 行业需要建立统一的连接、可信使用和服务运营基础；
- 通过统一组织数据、知识、模型和专业能力，形成可管理、可交付、可计量的数据服务和场景服务。

对应归一化事实主要为 `NF-0042` 至 `NF-0061`，不能用 `NF-0001` 这种标题类事实代替。

### 2.2 全部内容页都存在机器占位字段

当前候选稿共有 24 个内容页，核验结果如下：

- 24/24 页页面使命使用“按源材料说明……”通用模板；
- 24/24 页受众问题使用“源材料如何说明……”通用模板；
- 24/24 页前后衔接使用“承接源材料前页”“交给源材料下一页继续展开”；
- 24/24 页使用通用的 `must_not_include`；
- 24/24 页 `excluded_from_onscreen` 为空；
- 24/24 页缺少 `authoring_decisions`；
- 24/24 页使用 `source_fact_inventory` 作为内容策略。

因此，当前问题不应按单页修补。所有内容页都需要重新进入作者化质量处理。

### 2.3 顶层状态容易造成误判

当前候选生成流程可能返回：

```json
{
  "status": "ok",
  "authoring_status": "pending",
  "handoff_status": "blocked"
}
```

这种状态表达会让调用方误以为 Outline 已完成。`status=ok` 实际只代表结构和来源绑定校验通过，不能代表页面判断、页面使命和作者取舍完成。

### 2.4 校验覆盖不足

现有校验覆盖了以下内容：

- JSON 结构；
- 来源事实绑定；
- 论证节点绑定；
- 概念和关系引用；
- 事实覆盖；
- handoff 的 authoring 状态。

现有校验没有阻止以下问题：

- 标题、目录、日期或文档元数据被当作核心判断；
- 页面使命全部使用通用占位语；
- 受众问题全部使用通用占位语；
- 页面没有明确的不上屏取舍；
- 页面没有作者化证据选择和删除检验；
- 事实覆盖很多，但页面没有一个可交流的主判断。

## 3. 代码根因

根因位于：

[generate.py:680](/Users/liuxing/.codex/worktrees/2962/CyberPPT/.agents/skills/ppt-outline-planning/ppt_outline_planning/generate.py:680)

当前逻辑：

```python
judgment = _text(page_facts[0].get("statement"))
```

`page_facts` 是来源事实集合，不保证第一条事实就是页面主判断。集合中可能包含：

- 文档标题；
- 章节标题；
- 目录条目；
- 日期和落款；
- 元数据；
- 事实正文。

因此，`page_facts[0]` 不能作为页面判断来源。

此外，生成器当前同时自动填写了 `page_mission`、`audience_question`、`transition_from_previous`、`transition_to_next` 等作者化字段，导致机械候选稿看起来像正式 Outline。

## 4. 修复目标

修复目标是建立清晰的四层边界：

```text
Source Foundation
    ↓
语义论点、概念、关系和事实绑定
    ↓
候选页面清单
    ↓
作者填写页面判断与取舍
    ↓
作者化质量校验
    ↓
cyberppt-handoff
```

生成器负责来源绑定和页面结构，不替作者决定正式页面判断。

## 5. 具体修复要求

### 5.1 修复 `generate.py`

删除“第一条事实即核心判断”的逻辑。

候选稿应从主论证节点提供来源上下文，但不自动伪造正式判断：

```json
{
  "key_judgment": "",
  "judgment_status": "authoring_required",
  "primary_argument_node_id": "ARG-002",
  "source_argument_node_ids": ["ARG-002"],
  "source_evidence_node_ids": ["NF-0042", "...", "NF-0061"]
}
```

正式作者化 spec 存在且完整时，才允许写入：

```python
judgment = authored_fields["key_judgment"]
```

如果需要为候选稿提供预览判断，只能使用明确标记的 `planning_inference` 或 `candidate_summary` 字段，不能写入正式的 `key_judgment`。

必须继续保留：

- `primary_argument_node_id`；
- `source_argument_node_ids`；
- `source_evidence_node_ids`；
- `evidence.normalized_fact_ids`；
- `evidence.concept_ids`；
- `evidence.relation_ids`；
- `judgment_derivation` 的来源绑定信息。

### 5.2 区分候选状态和正式状态

建议将 pipeline 顶层状态调整为：

```json
{
  "status": "authoring_required",
  "validation_status": "ok",
  "structural_status": "ok",
  "source_binding_status": "ok",
  "authoring_status": "pending",
  "handoff_status": "blocked"
}
```

状态含义必须明确：

- `validation_status=ok`：结构和来源绑定合法；
- `authoring_status=pending`：页面判断尚未完成人工作者化；
- `handoff_status=blocked`：禁止进入下游；
- 顶层 `status=authoring_required`：候选稿不能被称为完成稿。

候选稿可以渲染供人审阅，但不能以 `status=ok` 对外报告为完成。

### 5.3 加强 `validate.py`

增加页面作者化质量门禁。对所有内容页检查：

```python
page_mission != f"按源材料说明{title}"
audience_question != f"源材料如何说明{title}？"
transition_from_previous != "承接源材料前页。"
transition_to_next != "交给源材料下一页继续展开。"
must_not_include != ["后续章节的独立页面使命"]
excluded_from_onscreen 非空
authoring_decisions 完整
```

增加以下错误码：

- `OUTLINE_EDITORIAL_PLACEHOLDER`：页面作者化字段仍为通用占位内容；
- `OUTLINE_JUDGMENT_FROM_METADATA`：核心判断来自标题、目录、日期或其他元数据；
- `OUTLINE_AUTHORING_REQUIRED`：候选稿尚未完成人工作者化；
- `OUTLINE_PAGE_MISSION_UNDER_SPECIFIED`：页面使命无法说明该页在整篇中的不可替代职责；
- `OUTLINE_EVIDENCE_SELECTION_REQUIRED`：事实覆盖存在，但没有作者选定的直接证据和不上屏取舍。

候选稿可以报告结构和来源绑定通过，但不能报告正式作者化通过。

### 5.4 保持 handoff 硬门禁

`cyberppt-handoff` 必须继续拒绝：

```text
editorial_authoring_status != author_edited
```

不得因为事实覆盖完整、语义节点绑定完整或结构报告为 `ok` 而放行 mechanical draft。

正式路线保持不变：

```text
cyberppt-source-foundation
→ business-semantic-understanding
→ ppt-outline-planning
→ cyberppt-handoff
→ cyberppt-write-single-page
```

不得使用 `compile-outline-draft` 或 `cyberppt-author-stage01-outline` 作为新项目的第二路线。

## 6. 测试要求

至少增加以下测试：

1. 首条事实是文档标题时，不能成为 `key_judgment`。
2. P04 建设背景不能生成“依托电力领域数据基础设施开展”。
3. 24 页存在通用页面使命时，作者化质量门禁必须失败或返回 `authoring_required`。
4. 候选稿顶层状态不能为正式完成状态。
5. 空白 authoring spec 不能生成 `author_edited`。
6. 页面缺少 `excluded_from_onscreen` 或 `authoring_decisions` 时必须失败。
7. handoff 必须拒绝 mechanical draft。
8. 完整作者化 spec 能够通过结构、来源、作者化和 handoff 校验。
9. 真实 V16 重新生成后，P04 的来源绑定应覆盖建设背景事实链，不能引用标题类事实作为核心判断。

## 7. 真实 V16 验收

项目：

```text
/Volumes/DOC/CyberPPT/projects/power-data-infrastructure-cooperation-v16-20260815-foundation
```

语义目录：

```text
/Volumes/DOC/CyberPPT/projects/power-data-infrastructure-cooperation-v16-20260815-foundation/workbench/source-foundation/semantic/依托电力领域数据基础设施开展行业数据服务与场景服务运营合作方案V16
```

验收步骤：

1. 不重建 Source Foundation。
2. 使用修复后的正式 generator 生成候选 Outline。
3. 验证候选稿顶层状态为 `authoring_required`，handoff 为 `blocked`。
4. 检查 24 个内容页不存在错误的默认核心判断和通用占位字段。
5. 使用完整作者化输入重新生成正式 Outline。
6. 验证 `outline-report.json` 的结构、来源和作者化门禁全部通过。
7. 验证 handoff 成功进入下一阶段。
8. 重新渲染 `ppt-outline.md`，逐页检查 P04 至 P32。

不得手工修改 `page-plan.json`、`deck-brief.json` 或 `outline-report.json` 作为修复方式。任何生成错误都必须修复上游代码，然后重新生成和验证派生产物。

## 8. 完成标准

只有同时满足以下条件，才能报告 Outline 完成：

- 生成器不再从 `page_facts[0]` 生成核心判断；
- 候选稿和正式作者化稿状态清晰分离；
- 24 个内容页不存在默认占位页面使命；
- 24 个内容页都有作者化的核心判断、证据选择和不上屏取舍；
- P04 建设背景判断忠于源材料事实链；
- `audit_outline_consumption` 通过；
- `outline-report.json` 结构、来源和作者化门禁通过；
- mechanical draft 无法通过 handoff；
- 真实 V16 重新生成、渲染和验证完成；
- 所有验证命令和实际产物路径已记录。

## 9. 当前工作区约束

- 保留所有既有未提交改动；
- 不修改受保护的 `docs/superpowers/plans/2026-08-15-source-fact-coverage-gate.md`；
- 不覆盖用户现有正式项目 Outline；
- 不把临时生成物强行纳入代码提交；
- 不删除旧项目；
- 不新增确认文件、审批文件、回执、哈希或平行运行目录。
