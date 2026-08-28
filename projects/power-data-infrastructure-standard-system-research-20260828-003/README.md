# power-data-infrastructure-standard-system-research-20260828-003

CyberPPT authoritative Stage 01 workspace (lightweight controls).

## Flow

**Understand** (source-material parsing, unchanged):

1. Put the only authoritative source materials in `source/`; run `prepare-source-map` and one `source-map-check`.
2. Run `prepare-semantic-understanding`, complete the canonical semantic understanding, then run one `semantic-check`. Preserve source-native thesis, actors, status, argument roles, weights, relations, concept distinctions and source gaps.
3. Build canonical `workbench/stages/01-analysis/source-truth.json`; run one `source-truth-audit`. Source Truth remains factual authority and never stores page assignments.

**Plan and author** (vendored `script_engine`, see `.agents/skills/cyberppt-script-workflow/SKILL.md`):

4. Run `project-foundation` to mechanically project the validated Source Truth into `script/foundation.json` (no re-analysis; every fact keeps its source refs).
5. Follow `cyberppt-script-workflow` to reach `script/deck-plan.json` (stop at **脚本规划待确认** for user confirmation) and then `script/dist/final-script.md` (stop at **最终脚本已生成**). `cyberppt-script lint`/`audit-foundation`/`audit-plan` are diagnostics run after writing, not per-page blocking gates.

**Hand off to Stage 02**:

6. Run `prepare-stage02-handoff --script script/dist/final-script.md`, then `stage02-handoff-check`.

Use `python -m cyberppt status <project>` for a read-only live view across Stage 01 and Stage 02. The `manifest.yml` status block records initialization metadata only.

The authoritative lightweight path creates no page-script-authoring JSON, approval JSON, interaction state, generation receipt, retry attempt, escalation, artifact ledger or hash-freshness gate. `script/foundation.json`, `script/deck-plan.json` and `script/dist/final-script.md` are the three authoritative Stage 01 planning/writing artifacts.
