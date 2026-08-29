# CyberPPT project workflow override

This file applies to `projects/**` and describes the current source-material-to-PPT route for work under this directory.

## Default source-material route

Ordinary new projects use the `script` profile:

1. `prepare-source-context` creates the single deterministic source index.
2. `cyberppt-script-understand` performs one whole-document UNDERSTAND pass and writes `script/foundation.json` directly.
3. `cyberppt-script-workflow` performs lightweight PLAN followed by AUTHOR, CRITIQUE, REWRITE and DELIVER.
4. Stage 02 starts from the locked `script/dist/final-script.md`.

Do not run `prepare-source-map`, `prepare-semantic-understanding`, Source Truth
compilation or `project-foundation` for a `script` profile project. AUTHOR loads
the deck thesis and structure once, then reads only the source evidence bound to
the current page. Critic and Rewrite reuse that evidence boundary.

Use `cyberppt-source-foundation` → `business-semantic-understanding` →
`project-foundation` only for an explicitly selected `strict/legacy` profile:
contracts, regulation, fact-by-fact verification, full Source Truth work or old
project migration. Reuse validated strict artifacts when they already exist.

## Default writing and structure policy

默认采用政府公文式、央企正式交流语体。Foundation 保留来源章节身份、边界和顺序；Deck Plan 可以按共同受众问题和论证角色归并相邻来源章节，汇报章节通常控制在 4 个以内、默认不超过 6 个，且来源映射展开后保持原顺序和完整覆盖。

不得增加源材料缺乏支撑的章节逻辑、咨询式金句或营销标题。标题采用简洁、正式的主题表达；核心判断、副标题和完整论证由 AUTHOR 基于页面来源证据形成。跨来源顺序重排仍需用户明确授权。

For an existing project with approved source-foundation outputs, reuse and validate those outputs before downstream work; do not rebuild them merely to satisfy the invocation.

## Authority

Three authoritative content artifacts for the plan/author segment: `script/foundation.json`, `script/deck-plan.json`, `script/dist/final-script.md`. `script/dist/final-script.json` is an optional machine-readable mirror; `script/.cache/source-index.json` and diagnostic reports are derived, non-authoritative.

## Human gates

Two conversational gates: **脚本规划待确认** (deck plan — chapter structure, page decomposition, communication goal) and **最终脚本已生成** (the full `final-script.md`). `cyberppt-script lint`/`audit-foundation`/`audit-plan` run after writing as diagnostics; they are not a per-page blocking precondition.
