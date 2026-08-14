---
name: cyberppt-diagnose-stage01-editing
description: Diagnose and locally repair CyberPPT lightweight Stage 01 semantic understanding or Outline editing quality. Use when the user reports shallow or incorrect semantic understanding, confused business objects/actors/statuses, missing atomic evidence, unreasonable chapter or page merges, excessive page count, weak page sequence, lost evidence mapping, or an Outline that passes basic checks but is still hard to present. Work only on semantic-argument-model.json or outline.json and their affected evidence scope; do not use for normal deterministic Source Truth/Outline compilation, page-script writing, chapter-script review, Stage 02, image generation, or PPTX assembly.
---

# CyberPPT Stage 01 编辑诊断

把本 Skill 作为按需根因诊断器，不作为正常 Outline 作者步骤。正式候选提纲的首次作者编辑使用 `cyberppt-author-stage01-outline`；本 Skill 只处理已经出现的语义错误、Source Truth 角色冲突或审计通过后仍存在的局部结构问题。

## 工作边界

- 先读取适用 `AGENTS.md`，并按仓库要求先运行 `graft map`、再用 `graft ask ... --source` 获取当前正式契约。
- 只消费用户指定的当前项目；不得参考任何旧项目的语义理解、Source Truth、Outline、脚本、图片或中间产物。
- 只使用正式 `python -m cyberppt ... --lightweight` 命令和当前权威路径。
- 分析请求保持只读；用户明确要求修改时，才修改受影响的 `semantic-argument-model.json` 或 `outline.json`。
- 不创建 approval、receipt、attempt、escalation、ledger、审阅清单、平行 review 文件或新的人工门。
- 不写页面脚本，不进入 Stage 02，不生成图片或 PPTX。

## 先判断是否应该调用

仅在存在具体问题时继续：

- 语义问题：业务主语错误、对象混淆、主体/动作/处理对象缺失、状态或条件被提升、跨章节关系错误、正文单元未处置、atomic item 过度概括。
- Outline 问题：章节归属不合理、主题应拆未拆或应合未合、页数过多、页序跳跃、标题不严谨、证据职责不清、受保护事项消失、封底缺失。
- 审计通过但质量不足：提纲机械映射来源节点、页面问题不可讲、相邻页重复、合作推进建议等章节过度展开。

若只是正常生成 Source Truth 或 Outline 初稿，退出本 Skill，先使用正式编译命令，再调用 `cyberppt-author-stage01-outline` 完成作者编辑：

```powershell
python -m cyberppt compile-source-truth <project> --lightweight
python -m cyberppt compile-outline-draft <project> --communication-goal <goal> --lightweight
```

## 确定诊断范围

先把问题分为 `semantic` 或 `outline`，不得同时全量重做两层。

### 语义范围

读取：

1. `workbench/stages/00-semantic-understanding/semantic-argument-model.json`
2. `workbench/stages/00-source-map/source-heading-tree.json`
3. `workbench/stages/00-source-map/source-units.jsonl` 中问题节点引用及其相邻来源单元
4. 必要时读取确定概念边界所需的跨章节 occurrence 单元

局部节点问题只读相关节点、关系和来源单元。只有全文主语、主论点、一级结构或系统性覆盖问题才允许扩大到全部 source units；扩大范围前说明原因。

### Outline 范围

读取：

1. `workbench/stages/01-analysis/outline.json`
2. `workbench/stages/01-analysis/source-truth.json`
3. `semantic-argument-model.json` 中被涉及的节点
4. 目标章节及前后相邻页面合同
5. 当前用户确认的 communication goal

默认不回读源 DOCX；只有 Source Truth 与语义模型无法消除证据歧义时，才读取对应 `SU-*` 来源单元。

## 语义诊断

依次检查：

1. **全文身份**：`document_role`、`subject_of_report`、`primary_thesis`、`author_purpose`、`decision_intent` 是否各司其职。
2. **业务对象边界**：平台、基础设施、运营主体、行业服务体系、合作方、客户、服务对象是否被错误合并。
3. **原子事项完整性**：每项是否保留主体、动作、处理对象、条件、状态、数字和至少两个来源特征锚点。
4. **角色与状态相容**：`claim_role`、`evidence_role`、`importance`、`status` 与目标节点是否一致。
5. **来源处置**：正文、列表、表格单元是否进入 assignment/atomic item，受保护证据是否被完整覆盖。
6. **论证关系**：因果、支撑、组成、阶段、边界和建议是否有来源依据，是否被误写成更强关系。

修改时只改根因字段，不重新措辞无关节点。完成后运行一次：

```powershell
python -m cyberppt semantic-check <project> --lightweight
```

若语义修改会改变既有 Source Truth 或 Outline，停止自动下游重编，列明受影响节点、证据和页面，等待用户决定。绝不得自动覆盖已人工编辑的 Outline。

## Outline 编辑诊断

### 章节与页序

- 每章必须回答一个明确问题；章节顺序应体现来源逻辑与受众理解路径，而不是照搬标题目录。
- 页面必须接收前页结论并为后页提供前提；只写“继续介绍”不构成页序逻辑。
- 平台架构、平台运营、行业服务体系、合作机制、推进建议等主题按其业务职责归章，不按关键词邻近归章。

### 合并判断

只有同时满足以下条件才合并页面或章节：

1. 回答同一个受众问题；
2. 共享一个页面主题；
3. 能由一个主业务关系统领；
4. 主体、状态与成熟度相容；
5. 合并后没有受保护事项降为不可见细节；
6. 上屏仍能形成完整逻辑闭环。

“减少页数”“内容相关”“都属于合作”不能单独构成合并理由。无法满足时保持独立；若两个主题可分别成立、分别承担决策作用，也应分开。

### 页面压缩

- 先删除重复表达、空泛过渡和无独立任务的页面，不先牺牲来源事实。
- 将同一证据职责的记录聚合为一个 `content_unit`；不得让每条 Source Truth 记录机械对应一个上屏模块。
- 合作推进建议优先聚合为阶段、责任或决策动作，不把每项建议扩成独立页。
- 保留正式封面和封底；不得把封底当作可选的“独立结束页”删除。

### 证据映射

- Source Truth 保持事实权威，不向其中写页面归属。
- 页面 `source_refs` 必须由 `content_units`、`detail_refs` 和必要的 `boundary_refs`完整消费。
- P0/P1、边界、关键状态、责任主体和决策数字不得因合并消失。
- `merged_page` 必须有真实 `shared_page_topic`、`merge_reason` 和正确的 `source_argument_node_ids`；证据引用不等于主题已经被消费。

修改后只运行一次：

```powershell
python -m cyberppt outline-audit <project> --input <project>/workbench/stages/01-analysis/outline.json --lightweight
```

不得重新运行语义理解、Source Truth 编译或无关全稿检查。

## 交付格式

在对话中完整给出：

1. 问题定位及证据；
2. 建议修改和专业理由；
3. 不修改的替代方案及风险；
4. 修改后的实际语义节点或 Outline 章节/页面内容；
5. 所有真实修改产物的绝对可点击路径；
6. 已运行的轻量检查、结果和未验证风险。

若本轮只分析没有写文件，明确写“本环节无文件产出”。

## 与其他 Skills 的分工

- 单张内容页的完整稿、上屏文字和视觉结构：使用 `cyberppt-write-single-page`。
- 已写完章节脚本的跨页结构审阅：使用 `chapter-structure-review`。
- 本 Skill 止于语义模型或 Outline；不得越界替代上述 Skills。
