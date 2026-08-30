# CyberPPT project workflow override

This file applies to `projects/**` and mirrors the current repository-wide source-material-to-PPT route for work under this directory. If this file ever conflicts with `AGENTS.md` or `docs/CYBERPPT_WORKFLOW.md`, the repository-wide authority wins and this file must be corrected rather than treated as an alternate workflow.

## Default source-material route

New source-to-script projects use the `strict/legacy` profile by default:

1. `prepare-source-map` creates the deterministic source map and stable source units.
2. `cyberppt-source-foundation` / `business-semantic-understanding` establish the validated whole-document semantic model and Source Truth projection.
3. `project-foundation` mechanically projects validated Source Truth into `script/foundation.json`.
4. `cyberppt-script-workflow` performs lightweight PLAN followed by AUTHOR, CRITIQUE, REWRITE and DELIVER.
5. Stage 02 starts only from the locked `script/dist/final-script.md`.

Use the lightweight `script` profile only when the user explicitly selects that route. In that case:

1. `prepare-source-context` creates the deterministic source index.
2. `cyberppt-script-understand` performs one whole-document UNDERSTAND pass and writes `script/foundation.json` directly.
3. `cyberppt-script-workflow` performs PLAN/AUTHOR against that Foundation.
4. Stage 02 still starts from the locked final script and does not inspect Stage 01 state.

For an existing strict project with approved source-foundation outputs, reuse and validate those outputs before downstream work; do not rebuild them merely to satisfy the invocation.

## Default writing and structure policy

默认采用政府公文式、央企正式交流语体。Foundation 保留来源章节身份、边界和顺序；Deck Plan 可以按共同受众问题和论证角色归并相邻来源章节，汇报章节通常控制在 4 个以内、默认不超过 6 个，且来源映射展开后保持原顺序和完整覆盖。

不得增加源材料缺乏支撑的章节逻辑、咨询式金句或营销标题。标题采用简洁、正式的主题表达；核心判断、副标题和完整论证由 AUTHOR 基于页面来源证据形成。跨来源顺序重排仍需用户明确授权。

## Authority

Authority and projection boundaries are defined in `docs/CYBERPPT_AUTHORITY_MAP.md`:

- strict whole-document writable semantic authority: `semantic-argument-model.json`;
- PLAN/AUTHOR semantic contract: `script/foundation.json`;
- planning authority: `script/deck-plan.json`;
- Stage 02 cross-stage content authority: `script/dist/final-script.md`.

`source-truth.json`, audit reports, caches, manifests and QA receipts are derived artifacts and may not become a second independently authored semantic authority.

## Human gates

Two conversational gates: **脚本规划待确认** (deck plan — chapter structure, page decomposition, communication goal) and **最终脚本已生成** (the full `final-script.md`). Deterministic audits run after authoring as validation and diagnostics; they do not replace AUTHOR/Critic judgment.
