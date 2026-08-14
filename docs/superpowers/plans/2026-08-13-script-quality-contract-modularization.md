# Script Quality Contract Modularization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the script-quality audit implementation into focused modules while preserving every currently supported `cyberppt.script_quality_contract` import and its observable audit behavior.

**Architecture:** Add `cyberppt/script_quality/` as the implementation package. Retain `cyberppt/script_quality_contract.py` as an explicit re-export facade. Move source blocks without policy changes: models first, parser and heuristics second, then rules and communication review.

**Tech Stack:** Python 3.12, standard library, optional PyYAML, pytest.

## Global Constraints

- Preserve current uncommitted actor/lane regular-expression changes during source moves.
- Preserve all issue codes, severities, ordering, thresholds, regular expressions, parser fields, report schema, CLI behavior, and consumer imports.
- Retain test-imported underscore helpers through the facade.
- Use `PYTHONPATH=.` for pytest and run `graft build` before `graft check`.

---

## File Structure

- Create `cyberppt/script_quality/models.py`: data classes, configuration constants, shared low-level text and outline/source-truth helpers.
- Create `cyberppt/script_quality/parser.py`: Markdown/sidecar parsing and path loading.
- Create `cyberppt/script_quality/heuristics.py`: regular-expression, keyword, polarity, token, and classification helpers.
- Create `cyberppt/script_quality/rules.py`: issue factory, rule functions, readiness, retry, final-form, and audit orchestration.
- Create `cyberppt/script_quality/review.py`: `build_communication_review` only.
- Create `cyberppt/script_quality/__init__.py`: curated package exports.
- Modify `cyberppt/script_quality_contract.py`: compatibility re-exports only.
- Modify `tests/test_script_quality_contract.py`: package/facade parity and export-surface tests.

### Task 1: Extract models and parser

**Files:** Create `models.py`, `parser.py`, `__init__.py`; modify `script_quality_contract.py` and `tests/test_script_quality_contract.py`.

**Interfaces:** `ScriptPage`, `ScriptDocument`, `ScriptQualityIssue`, `load_page_contract_sidecar(path)`, `parse_script_markdown(text, page_contracts=None) -> ScriptDocument`, and `parse_script_path(path) -> ScriptDocument` retain their signatures.

- [ ] Add this failing parity test:

```python
def test_legacy_facade_and_package_parser_match() -> None:
    from cyberppt.script_quality import parse_script_markdown as package_parse
    from cyberppt.script_quality_contract import parse_script_markdown as legacy_parse
    text = "## 第1页：标题\n\n- 页面类型：内容页\n- 页面标题：标题\n- 上屏文字：\n**模块**\n"
    assert legacy_parse(text) == package_parse(text)
```

- [ ] Run `PYTHONPATH=. pytest -q tests/test_script_quality_contract.py -k legacy_facade_and_package_parser_match`; it must initially fail with missing package imports.
- [ ] Move unchanged source blocks for data classes, parser constants, section/field/source-reference helpers, sidecar loading, and parse functions. Put only shared primitives in `models.py`; preserve the dirty actor/lane regex edits verbatim.
- [ ] Add explicit imports in `__init__.py` and the facade, e.g. `from cyberppt.script_quality.parser import parse_script_markdown, parse_script_path`; leave unmoved functions temporarily in the facade.
- [ ] Run `PYTHONPATH=. pytest -q tests/test_script_quality_contract.py`; expected PASS.
- [ ] Commit: `git add cyberppt/script_quality/models.py cyberppt/script_quality/parser.py cyberppt/script_quality/__init__.py cyberppt/script_quality_contract.py tests/test_script_quality_contract.py && git commit -m "refactor(audit): extract script parser models"`.

### Task 2: Extract semantic and lexical heuristics

**Files:** Create `heuristics.py`; modify `models.py`, `parser.py`, `script_quality_contract.py`, `tests/test_script_quality_contract.py`, and `tests/test_script_audit_command.py`.

**Interfaces:** Existing `_prohibited_contrast_hits`, `_polarity_dropped_terms`, `_onscreen_false_parallel_semantics`, `normalized_tokens`, and `text_similarity` remain facade exports.

- [ ] Add this failing compatibility test:

```python
def test_package_and_facade_keep_negation_helper_behavior() -> None:
    from cyberppt.script_quality.heuristics import _prohibited_contrast_hits as package_hits
    from cyberppt.script_quality_contract import _prohibited_contrast_hits as legacy_hits
    text = "建设定位不是内部工具，而是行业公共能力。"
    assert legacy_hits(text) == package_hits(text) == ("不是内部工具，而是",)
```

- [ ] Run `PYTHONPATH=. pytest -q tests/test_script_audit_command.py -k package_and_facade_keep_negation_helper_behavior`; expected initial FAIL because the heuristic module is absent.
- [ ] Move lexical match, semantic-line role, parallel/hierarchy classification, visible-copy/prose hit, token similarity, overlap, and polarity source blocks with constants and ordering intact. Do not place audit orchestration in this module.
- [ ] Re-export every moved private/public helper explicitly from the facade; no wildcard imports.
- [ ] Run `PYTHONPATH=. pytest -q tests/test_script_quality_contract.py tests/test_script_audit_command.py`; expected PASS including `ProhibitedContrastTests`.
- [ ] Commit: `git add cyberppt/script_quality/heuristics.py cyberppt/script_quality/models.py cyberppt/script_quality/parser.py cyberppt/script_quality_contract.py tests/test_script_quality_contract.py tests/test_script_audit_command.py && git commit -m "refactor(audit): extract semantic heuristics"`.

### Task 3: Extract rules and communication review

**Files:** Create `rules.py`, `review.py`; modify `__init__.py`, `script_quality_contract.py`, and `tests/test_script_quality_contract.py`.

**Interfaces:** `audit_script_quality(script, outline, source_truth) -> list[ScriptQualityIssue]`, `audit_final_manuscript_form(text)`, `is_final_script_path(path)`, `script_retry_directive(issues, previous_strategy='')`, and `build_communication_review(script, outline)` remain identical.

- [ ] Add an audit/review parity test using the existing test module's valid script, outline, and Source Truth fixture:

```python
assert package_audit(script, outline, source_truth) == legacy_audit(script, outline, source_truth)
assert package_review(script, outline) == legacy_review(script, outline)
```

- [ ] Run the test before package exports; expected FAIL with absent package audit/review imports.
- [ ] Move `_issue`, all `*_issues` functions, ImageGen readiness, retry directives, final-manuscript checks, and `audit_script_quality` to `rules.py`. Move only review-only helpers and `build_communication_review` to `review.py`. Preserve audit call order verbatim, especially prohibited-contrast and negative-foreground checks.
- [ ] Make `__init__.py` and `script_quality_contract.py` explicit complete export lists. The facade must have zero implementation `def` or `class` blocks.
- [ ] Run `PYTHONPATH=. pytest -q tests/test_script_quality_contract.py tests/test_script_audit_command.py tests/test_assemble_final_script.py tests/test_final_script_pages.py tests/test_semantic_intent.py tests/test_visual_proof_preflight_diagnostics.py tests/test_visual_structure_stage.py`; expected PASS.
- [ ] Commit: `git add cyberppt/script_quality/rules.py cyberppt/script_quality/review.py cyberppt/script_quality/__init__.py cyberppt/script_quality_contract.py tests/test_script_quality_contract.py && git commit -m "refactor(audit): separate rules and communication review"`.

### Task 4: Verify full compatibility and repository graph

**Files:** Modify `script_quality_contract.py`, `script_quality/__init__.py`, `tests/test_script_quality_contract.py`, and `tests/test_script_audit_command.py` only if verification exposes a missing export.

**Interfaces:** Existing command, Stage 02, script, and test imports remain unchanged and import successfully.

- [ ] Add a facade-surface test importing every distinct external name found by `graft grep 'from cyberppt.script_quality_contract import|import cyberppt.script_quality_contract'`, including `ScriptPage`, `audit_script_quality`, `extract_speaker_notes`, `parse_script_markdown`, `parse_script_path`, and `strip_authoring_group_marker`.
- [ ] Run `PYTHONPATH=. pytest -q tests/test_script_quality_contract.py -k legacy_facade_exports_consumer_surface`; expected PASS.
- [ ] Run `git diff --check && rg -n '^def |^class ' cyberppt/script_quality_contract.py`; expected no whitespace errors and no facade implementation definitions.
- [ ] Run `PYTHONPATH=. pytest -q tests/test_script_quality_contract.py tests/test_script_audit_command.py tests/test_assemble_final_script.py tests/test_final_script_pages.py tests/test_semantic_intent.py tests/test_visual_proof_preflight_diagnostics.py tests/test_visual_structure_stage.py tests/test_imagegen_creative_brief.py tests/test_imagegen_no_visual_structure.py tests/test_extended_style_10.py`; expected PASS, with separately documented pre-existing failures if any.
- [ ] Run `npx --no-install graft build && npx --no-install graft check`; expected `graft check` reports `OK`.
- [ ] Commit only task paths: `git add cyberppt/script_quality cyberppt/script_quality_contract.py tests/test_script_quality_contract.py tests/test_script_audit_command.py && git commit -m "refactor(audit): modularize script quality contract"`.

## Self-Review

- The four tasks cover the specified layout, facade compatibility, unchanged behavior, the present dirty edits, targeted consumer tests, and Graft refresh.
- All paths, commands, interfaces, test names, and expected outcomes are explicit.
- Parser output (`ScriptDocument`) and audit inputs (`dict[str, object]`) are consistent across tasks.
