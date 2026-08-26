# Uncommitted Change Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the remaining mixed working-tree changes into reproducible, tested, independently reversible commits while excluding permission, line-ending, project-output, and one-off-script noise.

**Architecture:** Keep the existing CyberPPT CLI and Stage 01/02 modules. Split work by responsibility: prompt grammar, workspace hygiene, Stage 01 manuscript/audit, and Stage 02 image/template export. No new framework, service, or workflow engine is introduced.


## Global Constraints

- Do not overwrite or discard files with real content differences.
- Do not add `scripts/format_procurement_docx.py` or project run artifacts.

---

### Task 1: Commit compact visual grammar

**Files:**
- Modify: `scripts/dual_image_overlay/visual_grammar.py`
- Test: `tests/test_visual_grammar.py`
- Test: `tests/test_imagegen_no_visual_structure.py`

**Interfaces:**
- Consumes: `default_visual_grammar() -> VisualGrammarContract`
- Produces: three compact English prompt hygiene lines from `VisualGrammarContract.render()`

- [ ] Run upstream impact for `VisualGrammarContract` and `default_visual_grammar`.
- [ ] Run `PYTHONPATH=. pytest -q tests/test_visual_grammar.py tests/test_imagegen_no_visual_structure.py`.
- [ ] Stage only `scripts/dual_image_overlay/visual_grammar.py`.
- [ ] Run staged checks and commit as `fix(imagegen): commit compact visual grammar`.

### Task 2: Remove permission and line-ending noise

**Files:**
- Restore only tracked files whose normalized working-tree bytes equal `HEAD`.

**Interfaces:**
- Consumes: Git index and `HEAD` file content.
- Produces: a smaller dirty worktree containing only real content changes.

- [ ] Build the exact list by comparing `HEAD` bytes and working bytes after CRLF-to-LF normalization.
- [ ] Restore file mode and content for that exact list with a pathspec file.
- [ ] Re-run the normalized comparison and require zero mode/line-ending-only files.
- [ ] Do not commit: cleanup returns files to `HEAD`.

### Task 3: Validate and commit Stage 01 manuscript/audit feature

**Files:**
- Create: `cyberppt/commands/assemble_final_script.py`
- Modify: `cyberppt/cli.py`
- Modify: `cyberppt/commands/init_project.py`
- Modify: `cyberppt/commands/script_audit.py`
- Modify: `cyberppt/script_quality_contract.py`
- Modify: `cyberppt/stage01_controls.py`
- Modify: `tests/fixtures/script_audit/power_foundation_premature_scope.md`
- Modify: `tests/fixtures/script_audit/power_scene_matrix.md`
- Modify: `tests/test_script_audit_command.py`
- Modify: `tests/test_script_quality_contract.py`
- Create: `tests/test_assemble_final_script.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `assemble_final_script(project, drafts_dir=None, output_path=None, title="") -> dict[str, object]`
- Produces: CLI command `python -m cyberppt assemble-final-script PROJECT`
- Produces: `extract_speaker_notes`, `audit_final_manuscript_form`, and `build_communication_review`

- [ ] Run upstream impact for each modified callable.
- [ ] Reproduce the CLI style-choice assertion failure and determine whether the test or command gate order is stale.
- [ ] Make the minimum contract-consistent correction.
- [ ] Run `PYTHONPATH=. pytest -q tests/test_assemble_final_script.py tests/test_cli.py tests/test_script_audit_command.py tests/test_script_quality_contract.py`.
- [ ] Stage only the listed Stage 01 files, run staged checks, and commit as `feat(stage01): assemble and audit final manuscripts`.

### Task 4: Test and commit Stage 02 image/template export

**Files:**
- Modify: `scripts/dual_image_overlay/rebuild_engine/codex_oauth_image.py`
- Modify: `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py`
- Modify: `tests/test_dual_image_template_body_region.py`
- Test or extend: focused tests for output normalization, page role, cover fields, and notes.

**Interfaces:**
- Produces: `ensure_output_size(output_path: Path, size: str) -> tuple[int, int]`
- Preserves: `run_codex_image` and `run_codex_multi_image_once` return contracts
- Produces: 1680×944-compatible body slot and template-role selection

- [ ] Run upstream impact for modified callables.
- [ ] Add focused tests that fail without output normalization and template metadata behavior.
- [ ] Run the tests to confirm the intended boundary.
- [ ] Apply only minimal fixes exposed by those tests.
- [ ] Run Stage 02 focused regression tests.
- [ ] Stage only the Stage 02 files, run staged checks, and commit as `feat(stage02): normalize image and template export`.

### Task 5: Final audit

- [ ] Confirm the four task scopes have no staged leftovers.
- [ ] Report remaining real user changes and untracked project artifacts without modifying them.
- [ ] Report every new commit and focused test result.
