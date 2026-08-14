# Source-Faithful Government Defaults Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make government-official writing and source-locked titles, order, content, and factual strength the default behavior for source-material PPT workflows.

**Architecture:** The outline workpack becomes the authoritative default-policy carrier and includes a compact source-heading index plus request/policy bindings. The outline authoring Skill consumes that policy, and the validator enforces workpack freshness, strategy alignment, source-title ownership, source order, and agenda metadata rules before handoff. Existing projects without a workpack remain compatible; explicit structured or clearly authorized text requests can opt into flexible/consulting mode.

**Tech Stack:** Python 3.12 standard library, JSON artifacts, repository Skills in Markdown, `unittest`.

## Global Constraints

- Default writing style is `government_official`.
- Default source structure, title, order, and content modes are `locked`, `locked`, `locked`, and `preserve`.
- Capacity-driven page splitting and duplicate-content merging are allowed.
- Splitting or merging must not change source titles, order, factual strength, responsibility, conditions, or status.
- Reframing requires an explicit user request.
- Agenda pages list source sections only and may not use an interpretive “problem path” or “communication path” title.
- `cyberppt-handoff` remains a deterministic projection and must not re-plan titles or order.
- Existing projects without `outline-workpack.json` remain compatible.

---

### Task 1: Add default-policy and source-heading workpack tests

**Files:**
- Create: `tests/test_ppt_outline_planning_defaults.py`
- Modify: `.agents/skills/ppt-outline-planning/ppt_outline_planning/prepare.py`

**Interfaces:**
- Consumes: layer-three semantic payloads and optional layer-two `structure.json`.
- Produces: `build_outline_workpack(..., source_structure=None)` with `planning_policy`, `source_heading_outline`, `source_metadata`, and `binding`.

- [ ] **Step 1: Write failing workpack tests**

```python
def test_default_workpack_locks_government_style_and_source_structure(self):
    workpack = build_outline_workpack(
        semantic_payloads(),
        source_structure=source_structure_payload(),
    )
    self.assertEqual("government_official", workpack["planning_policy"]["writing_style_mode"])
    self.assertEqual("locked", workpack["planning_policy"]["source_structure_mode"])
    self.assertEqual("preserve", workpack["planning_policy"]["source_content_mode"])
    self.assertEqual("sec-0001", workpack["source_heading_outline"][0]["section_id"])

def test_explicit_consulting_request_can_unlock_structure(self):
    workpack = build_outline_workpack(
        semantic_payloads(),
        request_text="请重构叙事并改为咨询式表达",
        source_structure=source_structure_payload(),
    )
    self.assertEqual("consulting", workpack["planning_policy"]["writing_style_mode"])
    self.assertEqual("flexible", workpack["planning_policy"]["source_structure_mode"])

def test_negated_reframing_request_keeps_source_lock(self):
    workpack = build_outline_workpack(
        semantic_payloads(),
        request_text="不要重构叙事，老老实实按原文写",
        source_structure=source_structure_payload(),
    )
    self.assertEqual("locked", workpack["planning_policy"]["source_structure_mode"])
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest -v tests.test_ppt_outline_planning_defaults`

Expected: FAIL because `source_structure` and the new policy fields do not exist.

- [ ] **Step 3: Implement the minimal workpack policy**

Add:

```python
DEFAULT_PLANNING_POLICY = {
    "writing_style_mode": "government_official",
    "source_structure_mode": "locked",
    "source_title_mode": "locked",
    "source_order_mode": "locked",
    "source_content_mode": "preserve",
    "capacity_split_allowed": True,
    "duplicate_content_merge_allowed": True,
    "reframing_requires_explicit_user_request": True,
    "agenda_mode": "source_sections_only",
}
```

Implement source-outline flattening, source agenda metadata discovery, safe explicit-reframing detection, and request/policy SHA-256 bindings. `prepare_outline_workpack()` discovers the standard sibling `foundation/<name>/structure.json` when available.

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `python -m unittest -v tests.test_ppt_outline_planning_defaults`

Expected: workpack tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ppt_outline_planning_defaults.py .agents/skills/ppt-outline-planning/ppt_outline_planning/prepare.py
git commit -m "feat: default outline workpacks to source-locked government style"
```

---

### Task 2: Enforce workpack freshness and source-title ownership

**Files:**
- Modify: `tests/test_ppt_outline_planning_defaults.py`
- Modify: `.agents/skills/ppt-outline-planning/ppt_outline_planning/validate.py`
- Modify: `.agents/skills/ppt-outline-planning/references/outline-contract.md`

**Interfaces:**
- Consumes: optional `outline-workpack.json`, `deck-brief.json.workpack_binding`, `task_understanding.writing_style_mode`, `task_understanding.source_structure_mode`, and page `source_heading_ids` / `primary_source_heading_id`.
- Produces: explicit validation errors for stale workpacks, binding mismatches, strategy conflicts, invalid agenda titles, unknown heading IDs, rewritten source titles, and source-order reversals.

- [ ] **Step 1: Add failing validator tests**

```python
def test_locked_validator_rejects_interpretive_agenda_title(self):
    result = validate_locked_outline(agenda_title="四个合作问题构成交流路径")
    self.assertIn("invalid_locked_agenda_title", error_codes(result))

def test_locked_validator_accepts_source_title_and_capacity_split(self):
    result = validate_locked_outline(
        content_titles=["建设背景", "商务报价与收益分配（一）", "商务报价与收益分配（二）"],
        source_heading_ids=["sec-0002", "sec-0003", "sec-0003"],
    )
    self.assertEqual("ok", result["status"])

def test_validator_rejects_stale_workpack_semantic_hash(self):
    result = validate_outline_with_tampered_semantic_input()
    self.assertIn("stale_outline_workpack", error_codes(result))
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest -v tests.test_ppt_outline_planning_defaults`

Expected: FAIL because the validator ignores `outline-workpack.json` and source heading ownership.

- [ ] **Step 3: Implement minimal validation gates**

Add optional workpack loading. When the workpack is present and locked:

- verify semantic artifact hashes;
- verify deck request/policy bindings;
- verify deck style and structure fields;
- require source heading ownership on section/content pages;
- compare normalized titles against the primary source heading;
- allow `源标题（一）` / `源标题（二）` and source child-heading titles;
- verify primary source heading order is nondecreasing;
- require the locked agenda title to match source metadata or standard `目录`;
- retain current behavior when no workpack exists.

- [ ] **Step 4: Document the page contract**

Document `source_heading_ids`, `primary_source_heading_id`, locked-title normalization, capacity split naming, and duplicate-merge ownership.

- [ ] **Step 5: Run the tests and verify GREEN**

Run: `python -m unittest -v tests.test_ppt_outline_planning_defaults`

Expected: validator tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_ppt_outline_planning_defaults.py .agents/skills/ppt-outline-planning/ppt_outline_planning/validate.py .agents/skills/ppt-outline-planning/references/outline-contract.md
git commit -m "feat: validate source-locked outline titles and workpack freshness"
```

---

### Task 3: Align authoring Skills and project defaults

**Files:**
- Modify: `tests/test_skill_contract.py`
- Modify: `.agents/skills/ppt-outline-planning/SKILL.md`
- Modify: `.agents/skills/cyberppt-write-single-page/SKILL.md`
- Modify: `.agents/skills/cyberppt-write-single-page/references/professional-page-authoring.md`
- Modify: `projects/AGENTS.md`

**Interfaces:**
- Consumes: workpack locked/flexible policy and validated Outline titles.
- Produces: default source-faithful, government-official authoring behavior from outline through page script.

- [ ] **Step 1: Add failing Skill contract tests**

```python
def test_source_foundation_defaults_to_government_style_and_source_titles(self):
    planning = OUTLINE_SKILL.read_text(encoding="utf-8")
    project_rules = PROJECT_AGENTS.read_text(encoding="utf-8")
    self.assertIn("政府公文式", planning)
    self.assertIn("默认保留源材料章节标题、内容标题和顺序", planning)
    self.assertIn("仅因单页容量拆页", planning)
    self.assertIn("合并重复内容", planning)
    self.assertNotIn("never mechanically copy them into a deck", planning)
    self.assertIn("只有用户明确要求", project_rules)

def test_single_page_writer_cannot_rewrite_validated_outline_title_by_default(self):
    text = PAGE_SKILL.read_text(encoding="utf-8")
    self.assertIn("不得改写已验证 Outline 的页面标题", text)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest -v tests.test_skill_contract`

Expected: FAIL on the new default-style and title-lock assertions.

- [ ] **Step 3: Update Skill and project contracts**

Replace default reordering language with source-lock rules. Preserve evidence roles, one-page-one-core-point, capacity splitting, duplicate merging, explicit flexible-mode opt-in, and deterministic handoff. Make government-official writing the default in `projects/AGENTS.md`. Prevent the single-page writer from changing a validated Outline title unless the upstream Outline is revised and revalidated.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python -m unittest -v tests.test_skill_contract tests.test_ppt_outline_planning_defaults`

Expected: all targeted tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skill_contract.py .agents/skills/ppt-outline-planning/SKILL.md .agents/skills/cyberppt-write-single-page/SKILL.md .agents/skills/cyberppt-write-single-page/references/professional-page-authoring.md projects/AGENTS.md
git commit -m "docs: enforce source-faithful government authoring defaults"
```

---

### Task 4: Verify deterministic handoff and the V16 real workflow

**Files:**
- Reuse without modification: `.agents/skills/cyberppt-handoff/cyberppt_handoff/outline_projection.py`
- Update outside repository for test fixture only: `/workspace/scratch/de7e21fc86af/cyberppt-v16-offline-test/tools/author_outline.py`
- Regenerate outside repository: `/workspace/scratch/de7e21fc86af/cyberppt-v16-offline-test/workbench/ppt-outline/*`

**Interfaces:**
- Consumes: locked workpack, source-heading-owned V16 deck brief/page plan, current semantic and foundation artifacts.
- Produces: validated V16 outline whose P02 is `目录`, whose section/content titles trace to source headings, and whose handoff projection preserves those titles exactly.

- [ ] **Step 1: Run targeted repository regression tests**

Run:

```bash
python -m unittest -v \
  tests.test_skill_contract \
  tests.test_ppt_outline_planning_defaults
```

The locked-outline tests import the handoff package directly and assert that projected template/content titles and page order are unchanged.

- [ ] **Step 2: Regenerate the V16 workpack with the current request**

Run `scripts/source_foundation_outline.py --force --request-text` with the approved source-faithful request. Confirm the workpack contains the default locked policy, source headings, and current bindings.

- [ ] **Step 3: Add V16 source heading ownership and regenerate**

Update the test-project author generator so each section/content page records `source_heading_ids` and `primary_source_heading_id`, while P02 remains the source directory metadata page.

- [ ] **Step 4: Validate, render, and inspect the real outline**

Run the official validator and renderer. Assert:

```text
status=ok
errors=0
warnings=0
P02 title=目录
source structure mode=locked
writing style mode=government_official
all 136 NF-0042..NF-0177 facts retained exactly once
```

- [ ] **Step 5: Run the executable repository test suite**

Run: `python -m unittest discover -s tests -p 'test_*.py'`

Record any pre-existing failures separately. Do not hide unrelated failures.

- [ ] **Step 6: Confirm no handoff production change is required**

Inspect the regression assertion and `outline_projection.py`: `title_intent` and `order` must be copied exactly. If the assertion passes, leave the deterministic handoff implementation unchanged.

---

### Task 5: Finish and integrate the branch

**Files:**
- Review all branch changes.

**Interfaces:**
- Consumes: verified commits from Tasks 1–4.
- Produces: a clean branch ready to merge into `main`.

- [ ] **Step 1: Run final verification**

Run targeted tests, full executable `unittest` discovery, `git diff --check`, V16 outline validation, and branch status checks.

- [ ] **Step 2: Review branch diff**

Confirm no unrelated code, generated caches, test artifacts, or V16 scratch files were added to the repository.

- [ ] **Step 3: Merge after verification**

Use `superpowers:finishing-a-development-branch`. Because the user previously requested repository delivery and the current change is on an isolated branch, present the verified integration result and merge only through the repository's safe branch workflow.
