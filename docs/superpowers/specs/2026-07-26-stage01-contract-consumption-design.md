# Stage 01 Contract Consumption Design

## Goal

Make the new Outline fields provably flow into content-page scripts instead of remaining advisory Markdown.

## Design

All machine-facing artifacts use the same canonical `snake_case` names:
`page_job`, `business_question`, `main_message`, `new_value_vs_previous`,
`reserved_for_later`, and `proof_points`. Human-readable `主判断` remains in
the final manuscript, but must equal `main_message`.

1. `prepare-outline-input` reads Source Truth only. It exports coverage targets, evidence records, conclusions, and the required page-contract schema. It no longer reads an already completed Outline.
2. `prepare-page-script-input` continues to read the approved Outline and Source Truth. For each content page it emits the page job, business question, main message, new value, reserved content, proof points, evidence, and a hidden `cyberppt-page-contract` receipt template.
3. Content-page scripts retain that receipt as an HTML comment. It is not on-screen text and is ignored by ImageGen.
4. `script-audit` requires the receipt in strict mode and verifies:
   - page identity and contract fields match the approved Outline;
   - `main_message` matches the script's `主判断`;
   - every proof point is declared consumed;
   - `new_value_realized` and `reserved_for_later_respected` are true.

## Scope

No new workflow stage, database, model call, or external dependency. Existing legacy-mode projects remain compatible.
