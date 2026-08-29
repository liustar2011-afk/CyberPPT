# power-data-infrastructure-standard-system-research-20260828-002

CyberPPT Stage 01 workspace (`script` profile).

## Flow

The current `script/foundation.json` is validated and remains the semantic
authority for this project. Continue from it.

1. Do not rerun source mapping, semantic understanding, Source Truth compilation or `project-foundation` unless the source changes or Foundation validation fails.
2. Use the lean `script/deck-plan.json` for chapter grouping, page allocation, page mission and source boundaries.
3. AUTHOR loads the deck thesis and structure once, then reads only each page's bound source evidence and adjacent-page scope.
4. Critic and Rewrite reuse the same page evidence boundary; they do not rebuild whole-document semantics.

The two conversational stops are **脚本规划待确认** and **最终脚本已生成**.

## Stage 02

After `script/dist/final-script.md` is locked, regenerate the stale Stage 02
handoff once and continue to visual production. Do not rerun Stage 01 semantics.

The authoritative Stage 01 content artifacts are `script/foundation.json`,
`script/deck-plan.json` and `script/dist/final-script.md`.
