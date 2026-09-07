# Stage1 Faithful Authoring Refactor — Development Progress

Branch: `refactor/stage1-faithful-authoring`

Purpose: persist every completed implementation step so work survives interruption.

## 2026-09-07

### Step 0 — Development branch and persistence log

Status: completed.

Completed:
- Created branch `refactor/stage1-faithful-authoring` from `main`.
- Re-read `.agents/skills/independent-technical-judgment/SKILL.md` before implementation.
- Confirmed verdict: `SUPPORT WITH CONDITIONS`.
- Scope discipline: land P0 first; keep `analytical` behavior; avoid introducing a fourth semantic authority; keep backward-compatible optional fields rather than deleting them.

### Step 1 — Unlock faithful Final Script structure

Status: completed.

Changed:
- `contracts/final-script.schema.json`
  - Content pages now require only `full_copy`, `onscreen`, and `source_refs` in addition to the common page fields.
  - `mission`, `core_message`, `argument`, `visual_thesis`, `relationships`, and `speaker_notes` remain supported but are no longer mandatory for source-faithful pages.
  - `source_refs` entries must be non-empty strings and content pages require at least one ref.
- `script_engine/author_contracts.py`
  - Added mode-aware field validation.
  - `faithful` requires the source-native minimum and does not require an argument object or relational visual thesis.
  - `analytical` retains the stronger mission/core-message/argument/visual supporting-field contract.
  - Optional faithful relations no longer receive remediation that asks AUTHOR to invent a mechanism; unsupported abstract edges should be removed instead.

Compatibility decision:
- Kept Final Script `version: 1.0`; current schema loader has no version routing, so the change is intentionally backward-compatible rather than introducing a partially implemented schema version.

### Step 2A — Stop forcing judgment-led `full_copy` in faithful mode

Status: completed.

Changed:
- `script_engine/full_copy_contracts.py`
  - Added authoring-mode detection.
  - Faithful paragraphs may begin with source-native definitions, task labels, taxonomy labels, stages, or other source-native structures; they are no longer required to begin with a substantive business judgment.
  - Numbered faithful branches are no longer required to invent independent business sub-conclusions.
  - Analytical mode retains the existing judgment-led paragraph and numbered-subconclusion requirements.
  - Kept the concrete-source-matter safeguard that rejects author-created abstraction of source actions/status/milestones into generic summary dimensions.
  - Reworded the long-chain structure check so it no longer treats every authored structure as an "argument".

### Step 2B — Make faithful onscreen projection `full_copy`-led

Status: completed.

Changed:
- `script_engine/onscreen_contracts.py`
  - Added mode-aware onscreen validation.
  - Faithful headings may remain source-native category/task/stage labels and no longer need to be rewritten into judgment sentences.
  - Faithful detail lines are no longer forced to add an action/result merely because they begin with a method/scope phrase; hidden-context and generic-detail safeguards remain.
  - `check_onscreen_core_alignment()` now dispatches by mode: analytical pages retain `core_message → onscreen`; faithful pages use `full_copy → onscreen` semantic-anchor alignment.
  - Added a faithful per-visible-line alignment check that flags new onscreen propositions with insufficient semantic anchoring in `full_copy`.
  - Reworded the multi-module self-read check around explanatory/source-backed payload rather than an argument layer.

### Step 3 — Remove residual high-level `core_message` / argument assumptions

Status: completed for active call path.

Changed:
- `script_engine/analysis_audits/final_onscreen.py`
  - `_audit_authored_onscreen_composition()` now accepts `authoring_mode`.
  - In faithful `evidence_first`, remediation no longer says "move the judgment to core_message"; it preserves source-native peer facts and allows a lead only when the source itself contains one.
  - Density remediation now warns against adding unsupported summary judgments.
- `script_engine/analysis_audits/final_authoring_expression.py`
  - `_author_execution_issues()` now accepts `authoring_mode`.
  - Mechanical source concatenation in faithful mode is repaired as coherent source-faithful page prose, explicitly without inventing a new argument.
  - `phrase_led` faithful pages are no longer required to turn every visible detail into a complete analytical action/relation/result; raw table fragments remain blocked.
  - Reworded evidence-first hierarchy guidance so selective leads require a source or approved analytical lead proposition.
- `script_engine/analysis_audits/final_orchestrator.py`
  - Passes `final_authoring_mode` into the mode-aware high-level checks.
  - Fixed a lean-plan evidence bug: final semantic audits now union `page.source_refs` with optional proof/analysis refs. Previously, v2 lean pages could present an empty evidence set to faithful relation checking even though the approved page had source refs.

Deferred intentionally:
- `final_lean.py` still contains some legacy wording about "argument paragraphs"; its underlying source-retention checks are useful and remain active. Functional wording cleanup is deferred until the source-addition audit is added, to avoid changing a large file without corresponding regression tests.

Next:
- Step 4: strengthen faithful semantic-addition auditing (outside narrator, added numbers/formal instruments, relation/status promotion) using page source evidence.
