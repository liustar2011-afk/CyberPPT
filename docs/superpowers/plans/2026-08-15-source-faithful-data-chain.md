# Source-Faithful Data Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the approved source-faithful planning policy and typed business relationships from Source Material Foundation through Stage 02 and the final nine-section GPT Image 2 prompt.

**Architecture:** The optional `outline-workpack.json` becomes the policy authority consumed by `cyberppt-handoff`, while `page-plan.json.evidence.relation_ids` selects page relationships from the authoritative relation graph and concept base. The projected Outline, Stage 02 handoff, visual spec, immutable PageArtifactSpec, and prompt compiler carry the same semantic relationship fields; visual connectors remain a separate composition concern.

**Tech Stack:** Python 3.12 standard library, dataclasses, JSON artifacts, repository Skills, `unittest`.

## Global Constraints

- Default writing style remains `government_official`.
- Default source structure, title, order, and content modes remain `locked`, `locked`, `locked`, and `preserve`.
- Source titles, source order, page order, factual strength, conditions, status, actors, and responsibilities may not be rewritten downstream.
- Capacity-driven splitting and true duplicate-content merging remain the only default structural adjustments.
- `page-plan.json.evidence.relation_ids` is the page relationship-selection authority.
- `relation-graph.json` and `concept-base.json` are the relationship-semantics authority.
- A relationship may not broaden the page's authorized normalized facts.
- A missing relationship must remain missing; the adapter may not synthesize `contains`.
- Business relationships and Stage 02 visual connectors remain separate contracts.
- Backend IDs and provenance refs never enter the ImageGen prompt.
- No new approval, state, attempt, receipt, ledger, or parallel-run artifacts may be added.
- Legacy projects without `outline-workpack.json` remain readable.

---

### Task 1: Project planning policy and authoritative page relationships

**Files:**
- Modify: `.agents/skills/cyberppt-handoff/cyberppt_handoff/io.py`
- Modify: `.agents/skills/cyberppt-handoff/cyberppt_handoff/outline_projection.py`
- Modify: `.agents/skills/cyberppt-handoff/cyberppt_handoff/project.py`
- Modify: `.agents/skills/cyberppt-handoff/cyberppt_handoff/validate.py`
- Create: `.agents/skills/cyberppt-handoff/tests/fixtures/outline/outline-workpack.json`
- Modify: `.agents/skills/cyberppt-handoff/tests/fixtures/outline/deck-brief.json`
- Modify: `.agents/skills/cyberppt-handoff/tests/fixtures/outline/page-plan.json`
- Test: `tests/test_source_foundation_integration.py`

**Interfaces:**
- Consumes: optional `outline-workpack.json.planning_policy`, deck task modes, page source-heading ownership, `page-plan.json.evidence.relation_ids`, `relation-graph.json`, and `concept-base.json`.
- Produces: `cyberppt.outline.v2.planning_policy`, unchanged page source-heading/subtitle-policy fields, and typed `content_relations`.

- [ ] **Step 1: Add failing projection tests**

Extend the existing fixture integration test with literal assertions:

```python
self.assertEqual(
    "government_official",
    outline["planning_policy"]["writing_style_mode"],
)
self.assertEqual("locked", outline["planning_policy"]["source_structure_mode"])
self.assertEqual(["sec-0001"], content_page["source_heading_ids"])
self.assertEqual("sec-0001", content_page["primary_source_heading_id"])
self.assertEqual(
    {
        "subject": "项目",
        "relation": "has_goal",
        "objects": ["统一服务入口"],
        "direction": "subject_to_objects",
        "condition": "",
        "modality": "",
        "basis": "explicit",
        "confidence": "high",
        "source_refs": ["ST0002"],
        "authority_ref": "rel-0001",
    },
    content_page["content_relations"][0],
)
self.assertNotIn("contains", {item["relation"] for item in content_page["content_relations"]})
```

Add a second direct projection test that removes `relation_ids` from one fixture page and asserts `content_relations == []`.

- [ ] **Step 2: Run the projection test and verify RED**

Run:

```bash
python -m unittest -v tests.test_source_foundation_integration
```

Expected: FAIL because the current adapter does not load the workpack, does not preserve source-heading ownership, and emits `contains`.

- [ ] **Step 3: Load the optional workpack without breaking old projects**

In `load_inputs`, read `outline-workpack.json` when present and expose it as `payloads["workpack"]`; otherwise expose an empty object. Keep all existing required files unchanged.

```python
workpack = outline_dir / "outline-workpack.json"
payloads["workpack"] = read_json(workpack) if workpack.is_file() else {}
```

- [ ] **Step 4: Implement deterministic policy and relationship projection**

Add focused helpers to `outline_projection.py`:

```python
POLICY_FIELDS = (
    "writing_style_mode", "source_structure_mode", "source_title_mode",
    "source_order_mode", "source_content_mode", "capacity_split_allowed",
    "duplicate_content_merge_allowed", "reframing_requires_explicit_user_request",
    "agenda_mode",
)

def _project_planning_policy(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    workpack_policy = (payloads.get("workpack") or {}).get("planning_policy") or {}
    task = (payloads["deck"].get("task_understanding") or {})
    return {
        field: workpack_policy[field] if field in workpack_policy else task[field]
        for field in POLICY_FIELDS
        if field in workpack_policy or field in task
    }
```

Implement `_project_page_relationships(page, payloads, nf_to_st)` so it:

- iterates only the page's declared `relation_ids` in their existing order;
- resolves `from_concept_id` and `to_concept_id` to `canonical_name`;
- intersects relation fact IDs with the page's direct normalized-fact IDs;
- copies `relation_type`, `basis`, `confidence`, optional `condition`, optional `modality`, and optional `direction`;
- defaults semantic direction to `subject_to_objects` only when the source relation has no explicit direction;
- raises `ValueError` for unknown relation or concept IDs;
- returns `[]` when the page declares no relation IDs.

Copy page `source_heading_ids`, `primary_source_heading_id`, and `subtitle_policy` only when present. Add root `planning_policy` to the projected Outline.

- [ ] **Step 5: Bind and validate the new authority fields**

Add optional workpack hash coverage to `authority_map.authoritative_inputs`. Add `page_direct_relation_ids` to the authority map. In `validate_projection`, assert:

- projected `planning_policy` equals the workpack policy subset when a workpack exists;
- each projected page `authority_ref` maps to its expected relation IDs;
- relation `authority_ref` values exactly equal the page's declared relation IDs;
- relation `source_refs` are a subset of page `source_refs`;
- locked pages preserve source-heading ownership fields from the page plan.

- [ ] **Step 6: Run projection tests and verify GREEN**

Run:

```bash
python -m unittest -v \
  tests.test_source_foundation_integration \
  tests.test_ppt_outline_planning_defaults
```

Expected: all tests PASS.

- [ ] **Step 7: Commit Task 1**

```bash
git add .agents/skills/cyberppt-handoff tests/test_source_foundation_integration.py
git commit -m "feat: preserve source policy and typed page relations"
```

---

### Task 2: Preserve policy and typed relations in Stage 02 handoff

**Files:**
- Modify: `cyberppt/stage02_handoff.py`
- Test: `tests/test_stage02_handoff.py`
- Test: `tests/test_visual_structure_stage.py`

**Interfaces:**
- Consumes: `cyberppt.outline.v2.planning_policy`, page source-heading ownership, subtitle policy, and typed `content_relations`.
- Produces: root `stage02-handoff.json.planning_policy`, page trace fields, exact `business_relationships`, and structured Stage 01 relationship features.

- [ ] **Step 1: Add failing Stage 02 handoff tests**

Add literal assertions to `_page_record` coverage:

```python
outline_page = {
    "argument_role": "evidence",
    "source_heading_ids": ["sec-0002"],
    "primary_source_heading_id": "sec-0002",
    "subtitle_policy": {"mode": "not_needed", "subtitle": ""},
    "content_relations": [{
        "subject": "项目", "relation": "has_goal",
        "objects": ["统一服务入口"], "direction": "subject_to_objects",
        "condition": "", "modality": "", "basis": "explicit",
        "confidence": "high", "source_refs": ["ST0002"],
        "authority_ref": "rel-0001",
    }],
}
record = _page_record(page, outline_page)
self.assertEqual(["sec-0002"], record["source_heading_ids"])
self.assertEqual(outline_page["content_relations"], record["stage02_visual_input"]["business_relationships"])
```

Add a `build_stage02_handoff` test asserting that root `planning_policy` is copied exactly from Outline and no default policy is invented for legacy Outline fixtures.

- [ ] **Step 2: Run handoff tests and verify RED**

Run:

```bash
python -m unittest -v tests.test_stage02_handoff tests.test_visual_structure_stage
```

Expected: FAIL because root policy and page source-heading fields are currently absent.

- [ ] **Step 3: Implement exact handoff projection**

In `_page_record`, copy the optional page trace fields without transformation:

```python
for field in ("source_heading_ids", "primary_source_heading_id", "subtitle_policy"):
    if field in outline:
        record[field] = outline[field]
```

Retain existing `business_relationships` copying. Extend `_stage01_relationship_features` so the action records keep `direction`, `condition`, `modality`, `basis`, and `confidence` when present; never derive these fields from visual notes. Visual-note clause extraction remains advisory only.

In `build_stage02_handoff`, add root `planning_policy` only when the loaded Outline contains a dictionary with that name.

- [ ] **Step 4: Strengthen handoff audit**

For each content page, compare `stage02_visual_input.business_relationships` with the Outline page's `content_relations` and emit a blocking `HANDOFF_BUSINESS_RELATIONSHIP_DRIFT` issue on any difference. Compare root planning policy when present and emit `HANDOFF_PLANNING_POLICY_DRIFT` on a mismatch.

- [ ] **Step 5: Run handoff tests and verify GREEN**

Run:

```bash
python -m unittest -v tests.test_stage02_handoff tests.test_visual_structure_stage
```

Expected: all tests PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add cyberppt/stage02_handoff.py tests/test_stage02_handoff.py tests/test_visual_structure_stage.py
git commit -m "feat: carry source policy into Stage 02 handoff"
```

---

### Task 3: Separate authoritative business relations from visual connectors

**Files:**
- Modify: `cyberppt/commands/visual_structure_stage.py`
- Modify: `cyberppt/visual_structure_contract.py`
- Modify: `vendor/skills/ppt-visual-structure-designer/assets/page-visual-spec.schema.json`
- Test: `tests/test_visual_structure_stage.py`
- Test: `tests/test_visual_structure_contract.py`

**Interfaces:**
- Consumes: `visual-design-input.json.business_relationships` and selected visual execution design.
- Produces: `deck-visual-spec.json.semantic_graph.business_relationships` plus independent `connectors`.

- [ ] **Step 1: Add failing visual-spec tests**

Add a test with one typed relationship and a deliberately different selected reading path:

```python
page = _build_executable_page(source, decision)
self.assertEqual(
    source["business_relationships"],
    page["semantic_graph"]["business_relationships"],
)
self.assertEqual("has_goal", page["semantic_graph"]["business_relationships"][0]["relation"])
self.assertNotEqual(
    page["semantic_graph"]["business_relationships"],
    page["connectors"],
)
```

Add a contract test that mutates one relationship object after spec generation and expects a blocking `BUSINESS_RELATIONSHIP_DRIFT` issue.

- [ ] **Step 2: Run visual-structure tests and verify RED**

Run:

```bash
python -m unittest -v \
  tests.test_visual_structure_stage \
  tests.test_visual_structure_contract
```

Expected: FAIL because the semantic graph currently stores only the rendered summary and generated edges.

- [ ] **Step 3: Preserve the authoritative relationship list**

Add a deep JSON-safe copy of `source["business_relationships"]` to `semantic_graph.business_relationships`. Keep `decision_relationship`, `edges`, and `connectors` for visual execution, but do not use them to rewrite the authoritative list.

Update the page visual-spec JSON schema so `semantic_graph.business_relationships` requires an array of objects with `subject`, `relation`, and `objects`; allows the optional semantic fields from Task 1; and disallows undeclared fields except `source_refs` and `authority_ref` needed for audit.

- [ ] **Step 4: Add relationship-drift validation**

At the visual contract boundary, compare each page's semantic graph relationship list with its Stage 02 design-input relationship list. Preserve order and exact present-value fields. Emit a blocking issue instead of normalizing differences away.

- [ ] **Step 5: Run visual-structure tests and verify GREEN**

Run:

```bash
python -m unittest -v \
  tests.test_visual_structure_stage \
  tests.test_visual_structure_contract
```

Expected: all tests PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add cyberppt/commands/visual_structure_stage.py cyberppt/visual_structure_contract.py vendor/skills/ppt-visual-structure-designer/assets/page-visual-spec.schema.json tests/test_visual_structure_stage.py tests/test_visual_structure_contract.py
git commit -m "feat: separate business relations from visual connectors"
```

---

### Task 4: Compile structured relationships into PageArtifactSpec and prompt section 4

**Files:**
- Modify: `cyberppt/page_artifact_spec.py`
- Modify: `scripts/dual_image_overlay/artifact_prompt.py`
- Test: `tests/test_page_artifact_spec.py`
- Test: `tests/test_artifact_prompt.py`

**Interfaces:**
- Consumes: exact handoff business relationships, matching visual-spec semantic relationships, and the optional root planning policy passed by the project loader.
- Produces: `RelationshipSpec` values and a deterministic, ID-free Evidence & relationships section.

- [ ] **Step 1: Add failing PageArtifactSpec tests**

Add the same typed relationship to handoff and visual fixtures, then assert:

```python
relationship = spec.relationships[0]
self.assertEqual("项目", relationship.subject)
self.assertEqual("has_goal", relationship.relation)
self.assertEqual(("统一服务入口",), relationship.objects)
self.assertEqual("explicit", relationship.basis)
```

Add drift cases for changed relation type, object, condition, or basis and expect `ValueError("artifact spec business relationships drifted")`.

- [ ] **Step 2: Add failing prompt tests**

Construct `RelationshipSpec` in `_spec()` and assert the fourth section contains exactly one semantic line such as:

```text
- 项目 --has_goal--> 统一服务入口 | direction=subject_to_objects | basis=explicit | confidence=high
```

Assert `rel-0001`, `ST0002`, and `contains` are absent.

- [ ] **Step 3: Run artifact tests and verify RED**

Run:

```bash
python -m unittest -v tests.test_page_artifact_spec tests.test_artifact_prompt
```

Expected: FAIL because `relationships` is currently a string tuple built from `decision_relationship`.

- [ ] **Step 4: Implement the immutable relationship contract**

Add:

```python
@dataclass(frozen=True)
class RelationshipSpec:
    subject: str
    relation: str
    objects: tuple[str, ...]
    direction: str
    condition: str
    modality: str
    basis: str
    confidence: str
```

Change `PageArtifactSpec.relationships` to `tuple[RelationshipSpec, ...]`. Add optional `planning_policy: Mapping[str, object] | None = None` to `build_page_artifact_spec`; `load_project_page_artifact_specs` passes the root handoff policy to every content-page build. Build the relationship tuple from the handoff relationship list only after verifying that the visual-spec list is semantically identical. Deliberately omit `source_refs` and `authority_ref` from `RelationshipSpec` so backend provenance cannot be serialized into the prompt.

When the current visual spec lacks `business_relationships`, preserve the legacy `decision_relationship` fallback only for legacy projects whose handoff also lacks typed relationships. New typed handoffs must fail rather than downgrade.

- [ ] **Step 5: Render deterministic relationship lines**

Add a pure formatter in `artifact_prompt.py` that renders subject, relation, joined objects, and only non-empty semantic qualifiers in the fixed order `direction`, `condition`, `modality`, `basis`, `confidence`. Continue to use section 6 for visual connectors.

If root planning policy is locked, include the already-compiled source-fidelity sentence in `HardConstraintSpec.page_constraints`; do not add policy field names or metadata to the visible prompt.

- [ ] **Step 6: Run artifact tests and verify GREEN**

Run:

```bash
python -m unittest -v tests.test_page_artifact_spec tests.test_artifact_prompt
```

Expected: all tests PASS.

- [ ] **Step 7: Commit Task 4**

```bash
git add cyberppt/page_artifact_spec.py scripts/dual_image_overlay/artifact_prompt.py tests/test_page_artifact_spec.py tests/test_artifact_prompt.py
git commit -m "feat: render typed relations in artifact prompts"
```

---

### Task 5: Add a Chinese government-enterprise end-to-end canary

**Files:**
- Create: `tests/test_source_faithful_artifact_chain.py`
- Modify: `.agents/skills/cyberppt-handoff/references/handoff-contract.md`
- Modify: `docs/superpowers/specs/2026-08-15-source-faithful-data-chain-design.md` only if implementation names differ from the approved design.

**Interfaces:**
- Consumes: repository Source Foundation fixture, projected Outline page, Stage 02 handoff page, executable visual page, Style10 lock fixture, PageArtifactSpec, and prompt renderer.
- Produces: one reproducible cross-layer regression test and documented authority contract.

- [ ] **Step 1: Write the failing cross-layer test**

The test must use real repository functions rather than source-text assertions:

```python
projection = build_projection(foundation_dir, semantic_dir, outline_dir)
outline_page = next(page for page in projection["outline"]["pages"] if page["page_type"] == "content")
record = _page_record(script_page, outline_page)
visual_page = _build_executable_page(visual_input_from(record), selected_decision_fixture())
spec = build_page_artifact_spec(
    handoff_page=record,
    visual_page=visual_page,
    style_lock=style_lock,
    handoff_sha256="a" * 64,
    visual_source_sha256="b" * 64,
)
first = render_artifact_prompt(spec)
second = render_artifact_prompt(spec)
```

Assert exact title/order preservation at projection, locked government policy, `has_goal` relationship continuity, exact visible text, nine-section order, no backend IDs, identical prompt text, and identical SHA-256.

- [ ] **Step 2: Run the canary and verify RED**

Run:

```bash
python -m unittest -v tests.test_source_faithful_artifact_chain
```

Expected: FAIL until Tasks 1–4 expose the complete real chain to the test.

- [ ] **Step 3: Complete only the minimum fixture adapters required by the canary**

Use test-local builders for `ScriptPage` and the selected visual decision. Do not add production-only test hooks, mock the relationship projection, or create generated project directories in the repository.

- [ ] **Step 4: Update the handoff contract**

Document the optional workpack input, the exact relationship authority, empty-relation behavior, source-heading field preservation, business-relation/visual-connector separation, and backend-ID exclusion.

- [ ] **Step 5: Run the canary and full targeted regression set**

Run:

```bash
python -m unittest -v \
  tests.test_source_faithful_artifact_chain \
  tests.test_source_foundation_integration \
  tests.test_ppt_outline_planning_defaults \
  tests.test_stage02_handoff \
  tests.test_visual_structure_stage \
  tests.test_visual_structure_contract \
  tests.test_page_artifact_spec \
  tests.test_artifact_prompt
```

Expected: all targeted tests PASS.

- [ ] **Step 6: Commit Task 5**

```bash
git add tests/test_source_faithful_artifact_chain.py .agents/skills/cyberppt-handoff/references/handoff-contract.md docs/superpowers/specs/2026-08-15-source-faithful-data-chain-design.md
git commit -m "test: add source-faithful artifact chain canary"
```

---

### Task 6: Verify and prepare the branch for repository integration

**Files:**
- Review all branch changes.

**Interfaces:**
- Consumes: all verified commits from Tasks 1–5.
- Produces: a clean, reviewable development branch ready to push and merge.

- [ ] **Step 1: Run focused behavioral verification**

Run the full targeted command from Task 5 and confirm zero failures and zero errors.

- [ ] **Step 2: Run the established mainline regression baseline**

Run:

```bash
python -m unittest -v \
  tests.test_source_foundation_integration \
  tests.test_skill_contract \
  tests.test_ppt_outline_planning_defaults \
  tests.test_outline_review
```

Expected: the established 40-test baseline remains green.

- [ ] **Step 3: Run repository integrity checks**

Run:

```bash
git diff --check main...HEAD
git status --short --branch
python -m compileall -q cyberppt .agents/skills/cyberppt-handoff/cyberppt_handoff scripts/dual_image_overlay
```

Confirm there are no generated caches, test outputs, unrelated fixtures, or modified user artifacts in the diff. Remove newly created `__pycache__` directories only if they are untracked and were produced by this task.

- [ ] **Step 4: Review requirements against the approved design**

Check each of the eight acceptance criteria in `docs/superpowers/specs/2026-08-15-source-faithful-data-chain-design.md` against code and fresh test evidence. Record any unmet item as a blocker rather than weakening the design.

- [ ] **Step 5: Finish the development branch**

Invoke `superpowers:finishing-a-development-branch`. Push only after the user-authorized repository workflow is confirmed, then open a reviewable pull request or merge through the previously established safe branch process.
