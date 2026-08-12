---
name: cyberppt-author-stage01-outline
description: Professionally author or revise a CyberPPT lightweight Stage 01 Outline from the current semantic argument model, Source Truth, communication goal, and candidate Outline. Use after compile-outline-draft, when proposing chapters/pages at the Outline human gate, or when an audit-passing Outline is coverage-driven, mechanical, overlong, poorly merged, or promotes appendix details to onscreen modules. This is the default authoring step before formal Outline audit; do not use for page-script prose, Stage 02, images, or PPTX assembly.
---

# CyberPPT Stage 01 专业提纲编辑

把 `compile-outline-draft` 视为证据与候选页清单，不视为正式提纲。正式 Outline 必须由作者根据交流目标、来源论证和受众理解路径完成编辑判断。

## 工作边界

- 读取适用 `AGENTS.md`，先运行 `graft map` 和相关 `graft ask ... --source`。
- 只消费当前项目的语义模型、Source Truth、communication goal 和候选 Outline，不参考旧项目产物。
- 只修改权威 `outline.json`；若发现 Source Truth 的重要级别、职责或状态与来源明显不相容，停止并报告上游根因，不用 Outline 掩盖。
- 轻量流程不创建 approval、receipt、attempt、ledger 或平行审阅状态文件。
- 不写页面完整稿或上屏文字，不进入 Stage 02。

## 必读输入

1. `semantic-argument-model.json` 的全文语义、章节节点、论证关系和状态；
2. `source-truth.json` 的 P0/P1/P2、职责、边界、主体和来源单元；
3. communication goal；
4. 候选 `outline.json` 的章节、页面、节点处置和相邻页；
5. [references/outline-authoring-contract.md](references/outline-authoring-contract.md)。

## 作者流程

### 1. 先确定整套叙事

明确受众从什么已知状态出发、需要理解或决定什么、最终到达什么判断。章节是不同的理解任务，不是来源标题的机械复制。

### 2. 为每页完成编辑简报

逐页作者化：

- `audience_question`：受众必须由本页独立回答的一个问题；
- `page_mission`：本页在整套叙事中完成的内部责任；
- `core_message`：来源支持、状态准确的单句命题；
- `non_substitutable_value`：删除或合并本页后丢失的不可替代价值；
- `argument_chain`：一条支配阅读顺序的主论证链；
- `evidence_roles`：按 claim、reason、instance、boundary、trace_only 分组；
- `excluded_from_onscreen`：保留但明确不形成受众模块的证据及理由；
- `reserved_for_later`：防止抢写后页。

### 3. 先做必要性判断，再分配证据

证据与主题相关不等于它直接推进页面命题。对每个拟上屏内容单元执行删除测试：删除后本页仍能完整回答受众问题，就不得设为 `onscreen_required=true`。

附件登记字段、材料清单、操作表单、逐项流程要求和实施明细默认进入完整稿、备注或 `detail_refs`；只有它们直接决定页面判断时才形成页面模块。

### 4. 决定拆分、合并与页序

只有页面共享同一受众问题、同一主题和一条主业务关系时才合并。页数压力、关键词相关和证据同章均不是合并理由。相邻页必须形成明确的接收与交付关系。

### 5. 完成证据层级

- P0/P1 只有在直接承担页面职责时进入 content unit；
- P2 默认进入 `detail_refs`；
- 边界证据可组合为一个 boundary unit，但不得成为普通页面的多个平级模块；
- 重要事项不得删除，只能在页面结构、完整稿、讲解和追溯之间调整层级；
- Source Truth 的优先级与实际论证职责冲突时，修正上游根因后重新审计。

### 6. 标记作者完成并验证

全部页面完成上述判断后，将根字段：

```json
"editorial_authoring_mode": "author_driven",
"editorial_authoring_status": "author_edited"
```

然后运行一次：

```powershell
python -m cyberppt outline-audit '<project>' --input '<project>/workbench/stages/01-analysis/outline.json' --lightweight
```

审计失败时修复编辑根因；不得为了消除错误码添加无业务价值模块或重复锚点。

## 人工门交付

完整展示章节与页面提纲、每页受众问题、主判断、不可替代价值、主论证链、证据取舍、建议理由、风险和权威产物绝对路径，然后停下等待确认。审计通过只是底线，仍须进行专业人工复核。

## 分工

- 语义模型存在具体错误：使用 `cyberppt-diagnose-stage01-editing`。
- 单页完整稿、上屏和视觉结构：使用 `cyberppt-write-single-page`。
- 章节脚本跨页审阅：使用 `chapter-structure-review`。
