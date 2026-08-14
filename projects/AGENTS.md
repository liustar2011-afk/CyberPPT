# CyberPPT project workflow override

This file applies to `projects/**` and intentionally overrides the repository-level legacy Stage 00 / early Stage 01 source-analysis path for new source-material-to-PPT work.

## Default source-material route

For new projects that begin from DOCX, PDF, PPTX, XLSX, Markdown, or similar source material, use the repository skill `cyberppt-source-foundation` as the default front end:

1. `source-to-markdown`
2. `source-structure-factbase`
3. `business-semantic-understanding`
4. `ppt-outline-planning`
5. `cyberppt-handoff`
6. existing `cyberppt-write-single-page`
7. existing final-script, Stage 02, image/SVG/PPTX pipeline

## Default writing and structure policy

默认采用政府公文式、央企正式交流语体，默认按源材料内容写作并保留章节标题、内容标题和先后顺序。只允许因 PPT 单页容量进行连续拆页，或在不改变主题归属、事实强度、责任、条件、状态和源顺序的前提下合并重复内容。

不得自行增加“问题路径”“交流路径”、咨询式金句、营销标题或源材料没有的章节逻辑。目录使用源材料目录标题，源材料没有明确目录标题时使用“目录”。只有用户明确要求重构叙事、咨询化、路演化、改名、重排或压缩重组时，才可解除默认锁定；一般的领导汇报、合作交流或高端交流用途不构成重构授权。

Do not rerun `prepare-semantic-understanding`, `compile-source-truth`, or `compile-outline-draft` over approved source-foundation outputs unless the user explicitly asks to use the legacy CyberPPT front end.

## Authority

The authoritative source-understanding artifacts live under `workbench/source-foundation/`. Files written into `workbench/stages/00-*` and `workbench/stages/01-analysis/` by `cyberppt-handoff` are compatibility projections for existing downstream consumers, not a second fact source.

A compatibility projection may map IDs and fields only. It must not add evidence to a page, infer a new relation, merge facts, change responsibility, or raise the maturity/status of a source claim.

## Human gates

Keep the existing conversational gates for communication goal, PPT outline, page detail, and final script. The outline gate must show the generated `ppt-outline.md` and its page missions, audience questions, core judgments, non-substitutable values, governing argument chains, evidence roles, exclusions, and reserved-later content.

## Legacy route

The old Stage 00 / early Stage 01 chain remains available only for backward compatibility or explicit user requests. Existing projects are not automatically migrated.
