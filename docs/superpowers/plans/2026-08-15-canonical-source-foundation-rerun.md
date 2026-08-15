# Canonical Source Foundation Rerun Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Source Foundation the only user-facing CyberPPT route and start a clean source-faithful project from the original V16 DOCX without consuming any existing project outputs.

**Architecture:** The repository documents one formal route: `cyberppt-source-foundation` → semantic understanding → `ppt-outline-planning` → `cyberppt-handoff` → page authoring and production. `compile-outline-draft` and other legacy commands remain internal compatibility code only and are not presented as a route. The fresh project will contain only a copied source DOCX before the source-foundation pipeline writes its first derived artifacts.

**Tech Stack:** Python 3.12, repository source-foundation scripts, Markdown/DOCX conversion, JSON semantic contracts, `unittest`.

## Global Constraints

- Do not modify `docs/superpowers/plans/2026-08-15-source-fact-coverage-gate.md`.
- Do not delete the existing V16 project or any existing outputs.
- Do not read or reuse existing semantic models, Source Truth, Outline, scripts, images, approvals, prompts, or QA from the old project.
- The new project must start from the original DOCX only.
- Do not invent source facts or bypass the four conversational authoring gates.
- Keep legacy compiler code only as an internal compatibility implementation; do not expose it as a second route.

### Task 1: Collapse the public workflow to one Source Foundation route

**Files:**
- Modify: `AGENTS.md`
- Modify: `projects/AGENTS.md`
- Modify: `SKILL.md`
- Modify: `.agents/skills/cyberppt-source-foundation/SKILL.md`
- Test: `tests/test_skill_contract.py`

- [ ] Write a failing contract test requiring one formal route and labeling legacy compiler usage as internal compatibility only.
- [ ] Run the contract test and confirm it fails against the current two-route wording.
- [ ] Update all four workflow documents to remove the user-facing route choice and state the single canonical sequence.
- [ ] Run the Skill and Source Foundation contract suites.

### Task 2: Create a clean project from only the original DOCX

**Files:**
- Create: `projects/power-data-infrastructure-cooperation-v16-20260815-foundation/`
- Source only: `projects/power-data-infrastructure-cooperation-v16-20260815-foundation/source/依托电力领域数据基础设施开展行业数据服务和场景服务运营合作方案V16.docx`

- [ ] Create a new project directory with only `source/` and the copied original DOCX.
- [ ] Verify the new project has no `workbench/`, `semantic-argument-model.json`, `source-truth.json`, `outline.json`, scripts, images, prompts, approvals, or QA artifacts before generation.
- [ ] Run `scripts/source_foundation_pipeline.py <new-project>/source/<source.docx> -o <new-project>/workbench/source-foundation --prepare-semantic --report`.
- [ ] Verify the pipeline report and source Markdown/fact-base outputs are generated from the new source path.

### Task 3: Author and validate the new semantic foundation

**Files:**
- Create through the registered semantic Skill: `<new-project>/workbench/source-foundation/semantic/`

- [ ] Invoke `business-semantic-understanding` on the new foundation workpack and author its four semantic outputs from the new source only.
- [ ] Run the semantic validator with `--report` and stop at the first communication-goal conversation gate with one source-faithful recommendation.
- [ ] After user confirmation, invoke `ppt-outline-planning`, validate and render the Outline, then present the Outline gate.

### Task 4: Verify clean handoff and report boundaries

- [ ] Confirm all generated artifacts resolve under the new project path.
- [ ] Confirm no old project path appears in new authoritative outputs.
- [ ] Keep all later page-authoring and production work behind the existing human gates.
