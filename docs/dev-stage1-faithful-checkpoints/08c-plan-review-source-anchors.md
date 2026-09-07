# Step 8C — PLAN review source anchors

Date: 2026-09-07
Branch: `refactor/stage1-faithful-authoring`

Status: completed.

## Problem fixed

`script_engine/plan_review.py` previously executed `del foundation`, so the human Gate displayed only opaque refs such as `F1 / F2 / F3`. A reviewer could not see whether page question/logic had already drifted away from the source before AUTHOR.

## Production change

`render_plan_review()` now derives a compact, read-only source anchor map from Foundation and adds a `来源锚点` column to the planning table.

Examples:

- `F1 数据资源首先需要完成可识别和可管理的治理。`
- `F2 可信使用机制控制授权、安全和审计。`

Rules:

- each anchor is at most 72 characters;
- relation records are rendered as `from + relation + to`;
- concepts, entities and numbers use their natural source-facing form;
- unknown refs remain unexpanded rather than guessed;
- Foundation is never mutated;
- the review explicitly states that source anchors are for verification only and do not create a page conclusion.

## Tests

Updated `tests/script_engine/test_plan_review.py` to verify:

- `来源锚点` appears in Gate output;
- F1-F4 source excerpts are visible;
- long anchors are truncated with an ellipsis;
- plan/Foundation inputs are not mutated;
- existing analytical/user-authorized/blocking review behavior remains present.

## Authority boundary

This is a derived review projection only. The authoritative artifacts remain Foundation, Deck Plan and Final Script; source anchors do not become a new planning field.
