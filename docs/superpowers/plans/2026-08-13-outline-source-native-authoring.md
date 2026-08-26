# Outline Source-Native Authoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent formal Outlines from losing their source-native chapter structure or passing audience-facing author judgments that lack complete evidence derivations.

**Architecture:** Extend existing Stage 01 audit modules instead of adding a compiler path. `outline_audit_semantics.py` owns evidence-derived meaning checks; `outline_audit_authoring.py` owns author-edited fields; `source_argument_model.py` owns source-node/chapter/disposition mapping. `outline_contract.audit_outline()` remains the sole aggregator.

**Tech Stack:** Python 3.12+, standard library `unittest`, existing `PYTHONPATH=. pytest` test workflow.

## Global Constraints

- Preserve v1 and non-author-edited Outline compatibility.
- Preserve the current lightweight Stage 01 workflow; create no approvals, manifests, receipts or parallel artifacts.
- Never have the compiler invent source chapter mappings, editorial judgments or retained destinations.
- A source-native chapter title is authoritative; an editorial label is secondary metadata.
- Run `PYTHONPATH=. pytest -q` from the repository root for the final suite.

---

### Task 1: Add source-native chapter mapping tests

**Files:**
- Modify: `tests/test_outline_contract.py:58-526`
- Modify: `tests/test_source_argument_model.py:167-693`

**Interfaces:**
- Consumes: `audit_outline(outline, source_truth, semantic_argument_model)`.
- Produces: regression fixtures defining `source_section_node_id`, `source_section_title`, and `editorial_chapter_label` behaviour.

- [ ] **Step 1: Write failing source-chapter tests**

Add tests that construct a strict v2 author-edited Outline with two chapter pages and a model containing two core top-level section nodes. Assert these codes:

```python
self.assertIn("SOURCE_SECTION_MAPPING_MISSING", codes)
self.assertIn("SOURCE_SECTION_TITLE_DRIFTED", codes)
self.assertIn("SOURCE_SECTION_ORDER_DRIFTED", codes)
self.assertNotIn("SOURCE_SECTION_MAPPING_MISSING", valid_codes)
```

The valid chapter page must use its original `source_heading` as both `title` and `source_section_title`, and set a distinct `editorial_chapter_label`.

- [ ] **Step 2: Run the new tests to verify failure**

Run: `PYTHONPATH=. pytest tests/test_outline_contract.py -q`

Expected: FAIL because source-chapter mapping is not audited.

- [ ] **Step 3: Implement minimal source-chapter validation**

In `cyberppt/source_argument_model.py`, add a pure helper called by `audit_outline_consumption()` that:

```python
def audit_source_section_mapping(outline: dict[str, Any], model: dict[str, Any]) -> list[dict[str, str]]:
    ...
```

It must index top-level `section_nodes` whose `argument_weight == "core"`, compare them to non-template chapter pages in sequence, and return the three codes above. Skip this helper unless `editorial_authoring_status == "author_edited"` and `semantic_argument_model_mode == "required"`.

- [ ] **Step 4: Run the source-chapter tests**

Run: `PYTHONPATH=. pytest tests/test_outline_contract.py tests/test_source_argument_model.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cyberppt/source_argument_model.py tests/test_outline_contract.py tests/test_source_argument_model.py
git commit -m "feat(outline): preserve source-native chapter mappings"
```

### Task 2: Formalize and audit editorial judgments

**Files:**
- Modify: `cyberppt/outline_audit_semantics.py:15-111`
- Modify: `cyberppt/outline_audit_authoring.py:96-146`
- Modify: `tests/test_outline_contract.py:58-526`

**Interfaces:**
- Consumes: `page.editorial_judgment`, `page.editorial_judgment_derivation`, `page.source_refs`, Source Truth records.
- Produces: `EDITORIAL_JUDGMENT_DERIVATION_MISSING`, `EDITORIAL_JUDGMENT_DERIVATION_INVALID`, and `EDITORIAL_JUDGMENT_INTRODUCES_MEANING` audit issues.

- [ ] **Step 1: Write failing editorial-judgment tests**

Add cases for a page that supplies an `editorial_judgment` with no derivation, with a source ref outside `page.source_refs`, and with an introduced modality. Assert each corresponding new code. Add a valid two-record derivation case and assert it has none of those codes.

- [ ] **Step 2: Run the new tests to verify failure**

Run: `PYTHONPATH=. pytest tests/test_outline_contract.py -q`

Expected: FAIL because the audit ignores `editorial_judgment`.

- [ ] **Step 3: Extract reusable derivation validation**

In `cyberppt/outline_audit_semantics.py`, extract the existing receipt checks into:

```python
def _derivation_issues(
    *, page_id: str, text: str, derivation: object,
    page_source_refs: list[str], records: dict[str, dict[str, object]], prefix: str,
) -> list[AuditIssue]:
    ...
```

Call it for `core_message` with the current issue-code behaviour unchanged, and for `editorial_judgment` with the new prefix. It must verify non-empty subset refs, supporting statements, derivation text, absence of introduced relations/modalities, semantic strength, and strong-relation support.

- [ ] **Step 4: Require the paired field only for author-edited pages**

In `_author_driven_editorial_issues()`, emit `EDITORIAL_JUDGMENT_DERIVATION_MISSING` only when `editorial_judgment` exists but its paired derivation does not. Do not read or validate the uncontracted `editorial_core_judgment` field.

- [ ] **Step 5: Run the focused tests**

Run: `PYTHONPATH=. pytest tests/test_outline_contract.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add cyberppt/outline_audit_semantics.py cyberppt/outline_audit_authoring.py tests/test_outline_contract.py
git commit -m "feat(outline): audit author judgment derivations"
```

### Task 3: Make argument chains and evidence roles source-addressable

**Files:**
- Modify: `cyberppt/outline_audit_authoring.py:96-146`
- Modify: `tests/test_outline_contract.py:58-526`

**Interfaces:**
- Consumes: `argument_chain: list[dict[str, object]]`, `evidence_roles: list[dict[str, object]]`.
- Produces: `ARGUMENT_CHAIN_INVALID`, `EVIDENCE_ROLE_INVALID`, `EVIDENCE_ROLE_CLAIM_UNCOVERED`.

- [ ] **Step 1: Write failing structure tests**

Create an author-edited page with a chain step missing `source_refs`, an evidence-role record whose refs are outside `page.source_refs`, and a claim role that omits all editorial-judgment derivation refs. Assert the three new codes. Add a passing page whose `claim` role covers every editorial derivation ref.

- [ ] **Step 2: Run the tests to verify failure**

Run: `PYTHONPATH=. pytest tests/test_outline_contract.py -q`

Expected: FAIL because current fields are only checked for non-emptiness.

- [ ] **Step 3: Implement strict authoring-field validation**

Add private validators in `cyberppt/outline_audit_authoring.py`. In an author-edited strict Outline, require list-shaped records. Each chain step needs a non-empty `statement`, allowed relationship string, and non-empty `source_refs` subset. Each evidence role needs `role` in `claim/reason/instance/boundary/trace_only` and a non-empty source-ref subset. Validate claim coverage against editorial derivation refs.

- [ ] **Step 4: Preserve compatibility explicitly**

Return no issue for legacy dictionary-shaped `evidence_roles` unless the page declares `editorial_judgment`; this prevents old projects from becoming invalid without opting in.

- [ ] **Step 5: Run focused regression tests**

Run: `PYTHONPATH=. pytest tests/test_outline_contract.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add cyberppt/outline_audit_authoring.py tests/test_outline_contract.py
git commit -m "feat(outline): bind author chains to source evidence"
```

### Task 4: Record downstream destinations for omitted details

**Files:**
- Modify: `cyberppt/source_argument_model.py:1078-1364`
- Modify: `tests/test_source_argument_model.py:167-693`

**Interfaces:**
- Consumes: `argument_node_dispositions[].retained_for`, `related_page_ids`, `source_heading_path`.
- Produces: `OUTLINE_OMISSION_RETAINED_FOR_MISSING` and `OUTLINE_OMISSION_RELATED_PAGE_UNKNOWN`.

- [ ] **Step 1: Write failing omission tests**

Extend the existing intentional-omission fixtures with an author-edited strict Outline. Assert omission fails when `retained_for` is absent and when `related_page_ids` contains an unknown page. Assert it passes with `retained_for=["implementation_plan"]`, a valid page id, and the original heading path.

- [ ] **Step 2: Run the tests to verify failure**

Run: `PYTHONPATH=. pytest tests/test_source_argument_model.py -q`

Expected: FAIL because omission destination metadata is not validated.

- [ ] **Step 3: Implement omission destination checks**

Within the existing `intentional_omission` branch of `audit_outline_consumption()`, require a non-empty list of values from `page_script`, `implementation_plan`, `single_item_confirmation`, or `traceability_only` when the Outline is author-edited strict. When `related_page_ids` exists, require each ID to identify an Outline page. Do not make `source_heading_path` mandatory because the Stage 00 node remains its authoritative heading source.

- [ ] **Step 4: Run the source-argument tests**

Run: `PYTHONPATH=. pytest tests/test_source_argument_model.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cyberppt/source_argument_model.py tests/test_source_argument_model.py
git commit -m "feat(outline): trace retained omitted detail"
```

### Task 5: Verify end-to-end compatibility and migrate V16 deliberately

**Files:**
- Modify: `projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline.json`
- Modify: `projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline-human-review.md`
- Modify: `projects/power-data-infrastructure-cooperation-v16-20260813/review/00-stage01-outline-source-alignment-review.md`

**Interfaces:**
- Consumes: completed audit contracts and current V16 authoritative artifacts.
- Produces: a source-native, author-evidence-complete V16 Outline and passed audit report.

- [ ] **Step 1: Run the complete contract suite before migration**

Run: `PYTHONPATH=. pytest tests/test_outline_contract.py tests/test_source_argument_model.py tests/test_outline_audit_command.py -q`

Expected: PASS.

- [ ] **Step 2: Update only the V16 authoritative Outline**

Restore the five original chapter titles, set secondary editorial labels, replace `editorial_core_judgment` with the formal pair, bind all author chains and evidence roles, and add downstream destinations for each omitted attachment node. Do not change Stage 00 or Source Truth.

- [ ] **Step 3: Regenerate dependent review artifacts**

Regenerate `outline-human-review.md` from the updated Outline and revise the source-alignment review to close the seven page-level evidence gaps.

- [ ] **Step 4: Run the production audit**

Run: `PYTHONPATH=. python3 -m cyberppt outline-audit projects/power-data-infrastructure-cooperation-v16-20260813 --input projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline.json`

Expected: JSON `status: "passed"` with no issues.

- [ ] **Step 5: Run the full repository test suite**

Run: `PYTHONPATH=. pytest -q`

Expected: PASS, or report pre-existing failures separately without masking them.

- [ ] **Step 6: Commit the fixed boundary**

```bash
git add cyberppt/outline_audit_authoring.py cyberppt/outline_audit_semantics.py cyberppt/source_argument_model.py tests/test_outline_contract.py tests/test_source_argument_model.py projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline.json projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline-human-review.md projects/power-data-infrastructure-cooperation-v16-20260813/review/00-stage01-outline-source-alignment-review.md
git commit -m "feat(outline): enforce source-native authoring contracts"
```

## Self-review

- Source-native chapter preservation is covered by Task 1.
- Editorial judgment derivation is covered by Task 2.
- Argument-chain and evidence-role traceability is covered by Task 3.
- Attachment/detail downscoping is covered by Task 4.
- Current-project and full-suite verification are covered by Task 5.
- All introduced fields, issue codes, test placement, commands, and migration boundaries are explicit.
