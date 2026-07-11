---
name: cyber-ppt
description: 将材料转化为适用于央企、政府内部汇报的高密度图片型 PPTX。
---

# CyberPPT

CyberPPT 的唯一生产交付模式是 `full_image_ppt`。正文内容由经审批的 full 图承载；标题、副标题、Logo、页码、页脚和公共模板元素由 PowerPoint 模板层生成。正文区主要文字通常不可编辑，交付必须如实记录 `body_content_editable=false`、`template_text_editable=true` 和 `speaker_notes_required=true`。

## 强制流程

1. 读取 `references/source-analysis.md`、`references/storyline.md`、`references/page-design.md`、`references/quality-assurance.md` 和 `references/internal-reporting-style.md`。
2. 在项目工作区完成材料分析、汇报方向、汇报结构、页面设计和业务稿五道确认门；任何候选稿均不得自动批准。
3. 锁定视觉风格、页面内容和 `template_text_lock`，生成可人工审阅的 `imagegen_script.md`。
4. 审批正文 full 图和 speaker notes 后，按生产状态机装配并验证。

```bash
python3 -m cyberppt produce prepare <project> --pages <range>
python3 -m cyberppt produce assemble <project> --pages <range>
python3 -m cyberppt produce verify <project> --pages <range>
```

`produce prepare` 只准备已批准输入并停在 speaker-notes 审批；`produce assemble` 只消费已批准的 notes、template text lock 和 full 图；`produce verify` 完成渲染比对、严格 manifest 校验、依赖 hash 校验与 delivery promotion。只有 verify 全部通过才可写入 `deliverable_ready`。

## 项目与阶段成果物

使用 `python3 -m cyberppt init projects/<name>` 新建项目。每个项目必须维护 `workbench/artifact-ledger.json`；每条工件记录必须包含 `stage`、`page`、`path`、`status`、`depends_on`、`supersedes`、`resume_command` 和可用时的 SHA-256。

| 阶段 | 位置 | 最小成果 |
|---|---|---|
| 分析 | `workbench/stages/01-analysis/` | 证据表、冲突、逐页计划、密度与组件清单 |
| full-image 生产 | `workbench/stages/02-blueprint-dual-image/` | 风格锁、内容锁、template text lock、提示词、full 图、notes、装配报告 |
| QA 与交付 | `workbench/stages/05-qa-delivery/` | 渲染报告、严格校验、交付 manifest、最终 PPTX |

`02-blueprint-dual-image` 是历史目录名；其当前语义为 full-image PPT 生产。所有项目工件必须存于项目工作区，不能写入仓库根目录 `images/` 或 `assets/`。

## 分析表达确认门

确认顺序固定为：`source_analysis` → `reporting_direction` → `report_structure` → `page_design` → `business_script`。每道门需要保存 Markdown 源、候选选项、推荐理由、待确认记录与审批记录；上一道门未批准不得进入下一道门。

默认采用央企、政府内部汇报文风：先识别材料类型、任务和受众，再确定叙事与页面结构。SCR、假设树和对标矩阵仅在适配任务时使用；不得强制固定章节顺序或咨询式口吻。

## 提示词与文字 QA

`imagegen_script.md` 是可人工修改的提示词源；页面可见文字只能来自已批准内容锁定。页面类型、构图指令、审阅意见、过程说明、证据编号、来源位置、提示词元数据与调试标记均不得进入页面。

生成 full 图后必须运行：

```bash
python3 -m cyberppt image-text-qa <project> --pages <range>
python3 -m cyberppt produce verify <project> --pages <range>
```

文字 QA 只用于检查生成图中是否出现未锁定或过程性文字；`failed` 和 `review_required` 都阻断交付。发现问题时回到内容锁定、提示词或 full 图返工。

## 生产门禁

- Reference Gate：进入阶段前读取规定参考资料。
- Evidence Gate：事实、数字、判断和建议可追溯至源材料。
- Density Gate：每页有信息密度、组件和图表计划。
- Style Gate：视觉风格已确认并记录。
- Template Text Gate：模板文字层来自批准的 `template_text_lock`。
- Speaker Notes Gate：`speaker_notes_manifest.json` 已审批且 hash 未变化。
- Render QA Gate：PPTX 正文区与 approved full 图完成渲染比对。
- Strict QA Gate：delivery manifest 通过严格 PPTX 校验。
- Dependency Freshness Gate：assembly、图、notes、锁定、QA 与最终 PPTX 依赖 hash 均为当前。

任一门禁失败不得交付；不得把中间 PPTX 冒充最终成果。需要返工时必须沿 artifact ledger 的依赖链定位到脚本、内容锁定、full 图或模板文字层的真实来源。

## 重要约束

- 不得从 full 图、文件名或人工目测推断模板标题和副标题。
- 不得重新生成已批准 full 图，除非质量不足或用户明确要求，并记录返工原因。
- 图片生成不得包含 Logo、页码、页脚、模板边框、证据编号、来源编号、提示词元数据或调试标记。
- 用户可以要求在 `script_locked`、`full_generated`、`image_ppt_exported`、`qa_rendered` 或 `deliverable_ready` 停止；停点必须记录已完成工件、未执行步骤和恢复命令。
