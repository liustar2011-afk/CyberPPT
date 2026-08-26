# On-Screen Expression Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically classify each content page into one of ten professional on-screen expression forms, enforce form-appropriate balance rules, and preserve the classified decision through the Stage 02 handoff.

**Architecture:** Add a focused expression registry/classifier module whose deterministic decision consumes existing script and Stage 01 semantic signals. Extend the final-script parser with an optional explicit override, invoke form-specific diagnostics from the existing presentation audit, and serialize the decision as semantic-only Stage 02 handoff metadata. ImageGen bitmap text and editable text remain separate contracts.

**Tech Stack:** Python 3.12, dataclasses, `unittest`/pytest, existing CyberPPT script-quality and Stage 02 handoff modules.

## Global Constraints

- `page_type` remains limited to `cover`, `agenda`, `section`, `content`, and `ending`; expression forms apply only to content pages.
- Use exactly these first-release form keys: `framework_4`, `key_points_3`, `flow_3_5`, `operation_loop`, `architecture_layers`, `pyramid_argument`, `comparison_2col`, `matrix_2x2`, `causal_chain`, `actions_3`.
- Resolve from author override, then authoritative relations, then structured actions and visible text signals, then a low-confidence `key_points_3` fallback.
- Do not add approvals, manifests, receipts, hashes, parallel directories, geometry, fixed layouts, or ImageGen-visible instructions.
- `上屏文字` remains editable-text truth; `生图锁定文字` remains bitmap-text truth.
- Reject contrastive or debate-style templates in visible copy, including “不是……而是……”, “并非……而是……”, “不是……而在于……”, “不能只……更要……”, and “从……转向……”.
- Preserve existing dirty-worktree content; stage only files named by the task being committed.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `cyberppt/onscreen_expression.py` | Expression registry, deterministic classifier, balance evaluator, typed decision/result objects. |
| `cyberppt/script_quality_contract.py` | Parse the optional override, expose it on `ScriptPage`, invoke the expression audit, retain contrastive-template reporting. |
| `cyberppt/stage02_handoff.py` | Build, serialize, render, and validate semantic expression-decision metadata. |
| `cyberppt/commands/compile_page_script_authoring.py` | Render an optional authoring override into the final-script page field. |
| `tests/test_onscreen_expression.py` | Isolated registry, precedence, confidence, and balance cases for all ten forms. |
| `tests/test_script_quality_contract.py` | Parser, audit integration, and visible-copy anti-pattern regressions. |
| `tests/test_stage02_handoff.py` | Handoff decision provenance and audit coverage. |
| `tests/test_compile_page_script_authoring.py` | Optional authoring override rendering. |

## Task 1: Build the expression registry and deterministic resolver

**Files:**
- Create: `cyberppt/onscreen_expression.py`
- Create: `tests/test_onscreen_expression.py`

**Interfaces:**
- Consumes: a page-shaped object with `page_type`, `top_level_module_titles`, `module_titles`, `onscreen_judgment`, `onscreen_text`, and optional `onscreen_expression_form`; `page_mission`; relation dictionaries; action strings; `topic_category`.
- Produces: `ExpressionDecision`, `resolve_onscreen_expression(...)`, `EXPRESSION_SPECS`, and `VALID_EXPRESSION_FORMS`.

- [ ] **Step 1: Write failing registry and precedence tests**

```python
from cyberppt.onscreen_expression import (
    VALID_EXPRESSION_FORMS,
    resolve_onscreen_expression,
)

def test_relation_precedence_selects_flow_before_surface_module_count():
    decision = resolve_onscreen_expression(
        page=_page(top_level_module_titles=("汇聚治理", "授权流通", "运营服务")),
        page_mission="形成数据运营主链",
        business_relationships=[{"relation": "sequence_before"}],
        actions=["汇聚数据", "授权使用", "运营服务"],
        topic_category="运营链路",
    )
    assert decision.form == "flow_3_5"
    assert decision.source == "relation"
    assert decision.confidence >= 0.80

def test_explicit_override_has_priority_and_preserves_scored_candidates():
    decision = resolve_onscreen_expression(
        page=_page(onscreen_expression_form="framework_4"),
        page_mission="形成数据运营主链",
        business_relationships=[{"relation": "sequence_before"}],
        actions=["汇聚数据", "授权使用", "运营服务"],
        topic_category="运营链路",
    )
    assert decision.form == "framework_4"
    assert decision.source == "explicit"
    assert ("flow_3_5", 0.0) not in decision.candidates

def test_registry_has_exactly_ten_initial_forms():
    assert VALID_EXPRESSION_FORMS == {
        "framework_4", "key_points_3", "flow_3_5", "operation_loop",
        "architecture_layers", "pyramid_argument", "comparison_2col",
        "matrix_2x2", "causal_chain", "actions_3",
    }
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_onscreen_expression.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'cyberppt.onscreen_expression'`.

- [ ] **Step 3: Implement the registry, decision model, and resolver**

```python
@dataclass(frozen=True)
class ExpressionDecision:
    form: str
    source: str
    confidence: float
    evidence: tuple[str, ...]
    candidates: tuple[tuple[str, float], ...]

def resolve_onscreen_expression(
    page: Any,
    *,
    page_mission: str,
    business_relationships: Sequence[Mapping[str, object]] = (),
    actions: Sequence[str] = (),
    topic_category: str = "",
) -> ExpressionDecision:
    explicit = str(getattr(page, "onscreen_expression_form", "") or "").strip()
    if explicit:
        return _explicit_decision(explicit, page, page_mission, business_relationships, actions, topic_category)
    relation = _relation_decision(business_relationships)
    if relation is not None:
        return relation
    return _score_decision(page, page_mission, business_relationships, actions, topic_category)
```

Implement relation mapping for `composed_of`/`contains`/`supports`, `sequence_before`/`sequence_after`, `layered_as`/`part_of`, `causes`, explicit feedback/return relations, and correspondence relations.  `_score_decision()` must return a sorted candidate tuple and use `key_points_3` with `source="fallback"` and confidence below `0.60` when no score clears the review threshold.

- [ ] **Step 4: Add parameterized cases for all ten forms and confidence thresholds**

```python
@pytest.mark.parametrize("relation,expected", [
    ("composed_of", "framework_4"),
    ("sequence_after", "flow_3_5"),
    ("layered_as", "architecture_layers"),
    ("causes", "causal_chain"),
    ("corresponds_to", "comparison_2col"),
])
def test_authoritative_relation_routes_to_expected_form(relation, expected):
    decision = resolve_onscreen_expression(
        _page(), page_mission="测试", business_relationships=[{"relation": relation}],
    )
    assert decision.form == expected
    assert decision.source == "relation"
```

Add dedicated action/module fixtures for `key_points_3`, `operation_loop`, `pyramid_argument`, `matrix_2x2`, and `actions_3`; add an ambiguous fixture that asserts `key_points_3`, `fallback`, and confidence `< 0.60`.

- [ ] **Step 5: Run focused tests**

Run: `PYTHONPATH=. pytest tests/test_onscreen_expression.py -q`

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

```bash
git add cyberppt/onscreen_expression.py tests/test_onscreen_expression.py
git commit -m "feat: classify onscreen expression forms"
```

## Task 2: Parse and render the optional author override

**Files:**
- Modify: `cyberppt/script_quality_contract.py:280-341,792-878`
- Modify: `cyberppt/commands/compile_page_script_authoring.py:71-260`
- Modify: `tests/test_script_quality_contract.py`
- Modify: `tests/test_compile_page_script_authoring.py`

**Interfaces:**
- Consumes: authoring-page optional key `onscreen_expression_form` and final-script field `上屏表达结构`.
- Produces: `ScriptPage.onscreen_expression_form: str`; rendered final scripts retain a declared valid author choice.

- [ ] **Step 1: Write failing parser and compiler tests**

```python
def test_parser_reads_onscreen_expression_form():
    page = parse_script_markdown("""## 第1页：测试
- 页面类型：内容页
- 上屏表达结构：framework_4
- 上屏文字：\n  权属确认\n  授权管理\n  流转审计\n  责任闭环
""").pages[0]
    assert page.onscreen_expression_form == "framework_4"

def test_compiler_emits_optional_expression_form(tmp_path):
    output = compile_page_script_authoring(project, output_dir=tmp_path / "drafts")
    assert "- 上屏表达结构：framework_4" in Path(output["drafts"][0]).read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=. pytest tests/test_script_quality_contract.py tests/test_compile_page_script_authoring.py -q`

Expected: FAIL because `ScriptPage` has no `onscreen_expression_form` and compiled output omits the field.

- [ ] **Step 3: Extend the data model and renderer without making the field required**

```python
@dataclass(frozen=True)
class ScriptPage:
    # existing fields
    onscreen_expression_form: str = ""

# parse_script_markdown()
onscreen_expression_form=fields.get("上屏表达结构", "").strip(),

# _content_page()
expression_form = str(authored.get("onscreen_expression_form") or "").strip()
if expression_form:
    lines.append(f"- 上屏表达结构：{expression_form}")
```

`_validate_authoring()` must allow the optional key.  It validates a supplied value against `VALID_EXPRESSION_FORMS`; it keeps existing authoring JSON valid when the key is absent.

- [ ] **Step 4: Run focused tests**

Run: `PYTHONPATH=. pytest tests/test_script_quality_contract.py tests/test_compile_page_script_authoring.py -q`

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add cyberppt/script_quality_contract.py cyberppt/commands/compile_page_script_authoring.py tests/test_script_quality_contract.py tests/test_compile_page_script_authoring.py
git commit -m "feat: support onscreen expression overrides"
```

## Task 3: Add form-specific balance and formal-language diagnostics

**Files:**
- Modify: `cyberppt/onscreen_expression.py`
- Modify: `cyberppt/script_quality_contract.py:2106-2156,4022-4434`
- Modify: `tests/test_onscreen_expression.py`
- Modify: `tests/test_script_quality_contract.py`

**Interfaces:**
- Consumes: `ScriptPage`, `ExpressionDecision`, and the applicable page contract.
- Produces: `audit_expression_balance(page, decision) -> list[ScriptQualityIssue]`; issue codes defined in the approved design.

- [ ] **Step 1: Write failing balance and contrastive-template tests**

```python
def test_framework_reports_unbalanced_heading_lengths():
    issues = audit_expression_balance(
        _page(top_level_module_titles=("权属确认", "授权管理", "跨主体数据流通全周期责任治理机制", "责任闭环")),
        _decision("framework_4"),
    )
    assert {issue.code for issue in issues} == {"ONSCREEN_HEADING_LENGTH_IMBALANCED"}

def test_visible_contrastive_template_is_rejected():
    issues = audit_script_quality(parse_script_markdown(_script_with(
        onscreen_judgment="可信流通不是附加能力，而是运营前提"
    )), outline, source_truth)
    assert "ONSCREEN_CONTRASTIVE_TEMPLATE" in {issue.code for issue in issues}
```

Add one pass and one failure fixture for every form.  The failing fixture must target the form’s own constraint: module count for `framework_4`, missing action for `flow_3_5`, missing return relation for `operation_loop`, inconsistent dimensions for `comparison_2col`, missing axes for `matrix_2x2`, and nonparallel verbs for `actions_3`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=. pytest tests/test_onscreen_expression.py tests/test_script_quality_contract.py -q`

Expected: FAIL because the balance evaluator and `ONSCREEN_CONTRASTIVE_TEMPLATE` are absent.

- [ ] **Step 3: Implement diagnostics and integration**

```python
def audit_expression_balance(page: Any, decision: ExpressionDecision) -> list[Any]:
    if decision.form == "framework_4":
        return _framework_issues(page)
    if decision.form == "flow_3_5":
        return _flow_issues(page)
    # one explicit branch for every remaining registered form
    return []

def _presentation_issues(page: ScriptPage, contract: dict[str, object] | None = None, *, strict_detail_phrase_length: bool = False) -> list[ScriptQualityIssue]:
    # retain existing diagnostics
    decision = resolve_onscreen_expression(
        page,
        page_mission=str((contract or {}).get("page_mission") or ""),
        business_relationships=page.content_relations,
        topic_category=str((contract or {}).get("topic_category") or ""),
    )
    issues.extend(audit_expression_balance(page, decision))
```

Refactor the existing `_prohibited_contrast_hits()` only when needed to return the approved contrastive patterns.  Preserve existing issue codes for existing callers; add `ONSCREEN_CONTRASTIVE_TEMPLATE` as the visible-copy-specific diagnosis.

- [ ] **Step 4: Run focused tests**

Run: `PYTHONPATH=. pytest tests/test_onscreen_expression.py tests/test_script_quality_contract.py -q`

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add cyberppt/onscreen_expression.py cyberppt/script_quality_contract.py tests/test_onscreen_expression.py tests/test_script_quality_contract.py
git commit -m "feat: audit onscreen expression balance"
```

## Task 4: Propagate classification through the Stage 02 handoff

**Files:**
- Modify: `cyberppt/stage02_handoff.py:169-428`
- Modify: `tests/test_stage02_handoff.py`

**Interfaces:**
- Consumes: `resolve_onscreen_expression(...)`, outline `topic_category`, relation list, action features, and `ScriptPage`.
- Produces: `record["onscreen_expression"]` and `record["stage02_visual_input"]["onscreen_expression"]`, each with `form`, `source`, `confidence`, `evidence`, and `candidates`.

- [ ] **Step 1: Write a failing handoff-provenance test**

```python
def test_handoff_preserves_expression_decision_provenance(project, final_script):
    payload = build_stage02_handoff(
        project, script=final_script, lightweight_stage01_confirmed=True,
    )
    page = payload["pages"][0]
    decision = page["onscreen_expression"]
    assert decision["form"] == "flow_3_5"
    assert decision["source"] == "relation"
    assert decision["confidence"] >= 0.80
    assert decision["evidence"]
    assert page["stage02_visual_input"]["onscreen_expression"] == decision
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_stage02_handoff.py -q`

Expected: FAIL with missing `onscreen_expression`.

- [ ] **Step 3: Serialize, render, and validate handoff metadata**

```python
decision = resolve_onscreen_expression(
    page,
    page_mission=page_mission,
    business_relationships=business_relationships,
    actions=relationship_features["actions"],
    topic_category=str(outline.get("topic_category") or ""),
)
expression_payload = {
    "form": decision.form,
    "source": decision.source,
    "confidence": decision.confidence,
    "evidence": list(decision.evidence),
    "candidates": [[form, score] for form, score in decision.candidates],
}
```

Place `expression_payload` in the page record and `stage02_visual_input`.  Extend `audit_stage02_handoff()` to require a valid registered `form`, known `source`, numeric `confidence` from `0.0` through `1.0`, a list of evidence strings, and candidate pairs.  Extend `render_handoff_markdown()` to show the selected form and confidence as review information.

- [ ] **Step 4: Run focused tests**

Run: `PYTHONPATH=. pytest tests/test_stage02_handoff.py -q`

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add cyberppt/stage02_handoff.py tests/test_stage02_handoff.py
git commit -m "feat: hand off onscreen expression decisions"
```

## Task 5: Validate the full production boundary and documentation

**Files:**
- Modify: `tests/test_dual_image_overlay_pair_manifest.py:121-178`
- Modify: `docs/superpowers/specs/2026-08-13-onscreen-expression-classification-design.md`

**Interfaces:**
- Consumes: a Stage 02 handoff containing `onscreen_expression` and the image-prompt manifest builder.
- Produces: proof that semantic expression metadata remains non-visible, while strict bitmap text continues to follow the locked-text contract.

- [ ] **Step 1: Write the failing prompt-boundary regression**

```python
def test_expression_metadata_is_semantic_only_in_compact_blueprint_prompt(self):
    manifest, _, _, _ = build_manifest(..., compact_blueprint=True)
    prompt = manifest["pairs"][0]["full"]["prompt"]
    assert "framework_4" not in prompt
    assert "四模块框架" not in prompt
    assert "【严格上屏文字】\n权属确认\n授权管理" in prompt
```

- [ ] **Step 2: Run the regression to verify its current outcome**

Run: `PYTHONPATH=. pytest tests/test_dual_image_overlay_pair_manifest.py::CyberpptPairManifestTests::test_expression_metadata_is_semantic_only_in_compact_blueprint_prompt -q`

Expected: PASS after Task 4; a failure shows metadata leaked into visible prompt sections and blocks completion.

- [ ] **Step 3: Update the design verification record**

Add a short implementation-status note under `## Verification` in the design document listing the targeted suites and the final full-suite command.  Do not alter the approved architectural decisions.

- [ ] **Step 4: Run targeted and full regression suites**

Run:

```bash
PYTHONPATH=. pytest \
  tests/test_onscreen_expression.py \
  tests/test_script_quality_contract.py \
  tests/test_compile_page_script_authoring.py \
  tests/test_stage02_handoff.py \
  tests/test_dual_image_overlay_pair_manifest.py -q
PYTHONPATH=. pytest -q
```

Expected: targeted suite PASS; full suite PASS or a clear report separating pre-existing failures from this change.

- [ ] **Step 5: Commit Task 5**

```bash
git add tests/test_dual_image_overlay_pair_manifest.py docs/superpowers/specs/2026-08-13-onscreen-expression-classification-design.md
git commit -m "test: protect onscreen expression prompt boundary"
```

## Self-Review

- Spec coverage: Tasks 1–2 implement the ten-form registry, automatic resolution, parser field, and author override; Task 3 implements form-specific balance and formal-language diagnostics; Task 4 carries provenance through Stage 02; Task 5 verifies the ImageGen boundary and full regression path.
- Placeholder scan: no unfinished markers or deferred implementation instructions remain.
- Type consistency: `ExpressionDecision`, `resolve_onscreen_expression`, `audit_expression_balance`, `onscreen_expression_form`, and `onscreen_expression` use the same names across tasks.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-13-onscreen-expression-classification.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints for review.
