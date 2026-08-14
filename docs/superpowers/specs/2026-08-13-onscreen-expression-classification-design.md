# On-Screen Expression Classification and Balance Design

## Purpose

Raise the professionalism, structural symmetry, and reading order of visible
content-page copy.  Each content page will be assigned an on-screen expression
form from a controlled set of ten forms.  The selected form will determine
which text hierarchy and balance rules apply; it will not dictate a fixed
visual layout.

The system must infer the form from authoritative semantic inputs wherever
possible and retain a concise author override for pages whose relationship is
an intentional exception.

## Scope

The change covers final-script parsing, Stage 02 handoff metadata, expression
classification, script-quality diagnostics, and focused tests.  It preserves
the existing distinction between editable on-screen text and bitmap-safe
ImageGen text.

It does not alter source registration, Source Truth, the approved Outline
interaction gates, page facts, page claims, or the Stage 02 visual-style
contract.  An expression form describes how an audience reads the content; it
does not prescribe rows, columns, card count, coordinates, illustration
choice, or a prompt recipe.

## Design

### 1. Separate page role from on-screen expression form

`page_type` retains the existing values `cover`, `agenda`, `section`,
`content`, and `ending`.  The new optional field applies only to content pages:

```markdown
- 上屏表达结构：framework_4
```

The parser exposes it as `ScriptPage.onscreen_expression_form`.  A missing
field is valid because the classifier supplies a result.  An unrecognised
explicit value produces an audit error.

### 2. Ten controlled expression forms

The registry lives in `cyberppt/onscreen_expression.py`.  Every registered
form declares its label, module range, heading grammar, hierarchy expectation,
and balance thresholds.

| Key | Chinese label | Primary use | Structural rule |
| --- | --- | --- | --- |
| `framework_4` | 四模块框架 | 体系、机制、能力 | Four parallel modules |
| `key_points_3` | 三要素结构 | 原则、价值、重点 | Three parallel points |
| `flow_3_5` | 三至五步链路 | 流程、路径、阶段 | Ordered action chain |
| `operation_loop` | 运营闭环 | 运营、治理、反馈 | Loop with a return relation |
| `architecture_layers` | 分层架构 | 制度、平台、应用、运营 | Three or four levels |
| `pyramid_argument` | 金字塔归纳 | 总判断与分论点 | One conclusion with supports |
| `comparison_2col` | 双列对照 | 状态、主体、方案 | Matched left/right dimensions |
| `matrix_2x2` | 四象限分群 | 客群、优先级、策略 | Two independent axes, four cells |
| `causal_chain` | 因果链 | 驱动、制约、影响 | Directed causal sequence |
| `actions_3` | 三项举措 | 重点任务、行动 | Three verb-object actions |

The registry remains open for later special forms such as data dashboards,
timelines, geographic distributions, and case profiles.  New forms enter
through registration and tests; the classifier dispatch flow remains stable.

### 3. Multi-source classification

`resolve_onscreen_expression()` returns a typed decision:

```python
@dataclass(frozen=True)
class ExpressionDecision:
    form: str
    source: str  # explicit | relation | scored | fallback
    confidence: float
    evidence: tuple[str, ...]
    candidates: tuple[tuple[str, float], ...]
```

The resolution order is deterministic:

1. a valid author-declared `上屏表达结构`;
2. authoritative Stage 01 business relationships;
3. structured Stage 01 subject-action-object features;
4. page mission, topic category, top-level modules, module grammar, and
   visible hierarchy;
5. `key_points_3` fallback with a low-confidence diagnostic.

The classifier consumes existing semantic inputs already carried by the Stage
02 handoff: `page_mission`, `topic_category`, `business_relationships`,
`stage01_relationship_features.actions`, `module_titles`, and
`top_level_module_titles`.  It must not classify from title keywords alone.

Relationship routing has priority over surface wording:

- `composed_of`, `contains`, `supports` favour `framework_4`;
- `sequence_before`, `sequence_after` favour `flow_3_5`;
- `layered_as`, `part_of` favour `architecture_layers`;
- `causes` favours `causal_chain`;
- explicit feedback or return relations favour `operation_loop`;
- paired correspondence relations favour `comparison_2col`.

The classifier records the winning evidence and ranked alternatives.  A
declared override remains visible in the result and does not erase the
machine-scored candidates.

### 4. Confidence handling

- `>= 0.80`: adopt automatically.
- `0.60–0.79`: adopt and emit `ONSCREEN_EXPRESSION_REVIEW_RECOMMENDED`.
- `< 0.60`: use `key_points_3`, emit `ONSCREEN_EXPRESSION_LOW_CONFIDENCE`, and
  request an author declaration during the normal script-review loop.

This keeps production moving while exposing ambiguous semantic shapes before
Stage 02 production.  It introduces no approval receipt, manifest, or new
interaction gate.

### 5. Form-specific balance diagnostics

`audit_expression_balance(page, decision)` returns normal
`ScriptQualityIssue` values and is called from `_presentation_issues()` after
existing hierarchy and natural-language checks.

The rules measure form-appropriate regularity rather than demand identical
copy lengths:

- `framework_4`: exactly four top-level modules, heading length spread at
  most two meaningful characters, child-count spread at most one, parallel
  noun or noun-verb grammar.
- `key_points_3`: exactly three peer points, common grammatical role, one or
  two child details per point.
- `flow_3_5`: three to five steps, action-bearing headings, one direction of
  progression, concise step names.
- `operation_loop`: three to five action-bearing nodes plus an explicit return
  relation.
- `architecture_layers`: three or four levels, same-level naming, no false
  parent-child indentation.
- `pyramid_argument`: one visible conclusion, three supporting propositions,
  evidence attached to its proposition.
- `comparison_2col`: two sides expose the same dimensions in the same order.
- `matrix_2x2`: two named axes and four cells at a common semantic level.
- `causal_chain`: three or four directed cause/effect nodes with no competing
  main chain.
- `actions_3`: exactly three action-object headings with consistent verb form.

New diagnostics include:

```text
ONSCREEN_EXPRESSION_FORM_INVALID
ONSCREEN_EXPRESSION_LOW_CONFIDENCE
ONSCREEN_MODULE_COUNT_MISMATCH
ONSCREEN_HEADING_LENGTH_IMBALANCED
ONSCREEN_DETAIL_LENGTH_IMBALANCED
ONSCREEN_PARALLEL_SYNTAX_MISMATCH
ONSCREEN_CHILD_COUNT_IMBALANCED
ONSCREEN_COMPARISON_DIMENSION_MISMATCH
ONSCREEN_CONTRASTIVE_TEMPLATE
ONSCREEN_GENERIC_MODULE_LABEL
```

`ONSCREEN_CONTRASTIVE_TEMPLATE` rejects contrastive and debate-like templates,
including “不是……而是……”, “并非……而是……”, “不是……而在于……”, “不能只……更要……”,
and “从……转向……”.  Its repair guidance asks for a definition, condition,
capability, or directional judgment that matches the page mission.

### 6. Handoff and downstream consumers

The Stage 02 handoff gains an `onscreen_expression` object containing `form`,
`source`, `confidence`, `evidence`, and `candidates`.  It is advisory semantic
input for visual design and carries no geometry.

The final script remains the authority for visible editable copy.  The
separate `image_locked_text` path remains the authority for text that ImageGen
may render.  Expression classification must not merge those two text domains.

### 7. Verification

Implementation verification on 2026-08-13: the focused expression, script,
authoring, Stage 02 handoff, manifest-boundary, script-audit, and visual-stage
suites passed with `194 passed, 2 skipped, 4 subtests passed`. The complete
suite ran with `1008 passed, 3 skipped, 8 subtests passed`; its 11 remaining
failures are pre-existing environment or baseline failures outside this change,
including missing `pptxgenjs`, alignment expectations, fixture-count drift,
and prompt/renderer baseline assertions.

- Parser tests cover a valid declaration, an absent declaration, and an
  invalid declaration.
- Classifier tests cover each of the ten forms, relationship precedence,
  action/grammar scoring, low-confidence fallback, and explicit override.
- Quality-audit tests cover one passing and one failing balance case for every
  form, plus contrastive-template and generic-label diagnostics.
- Stage 02 tests verify propagation of decision provenance.
- Prompt regression verifies that expression metadata remains semantic context
  and does not become visible ImageGen text or a fixed layout recipe.
- Run targeted tests, then `PYTHONPATH=. pytest -q` from the repository root.

## Non-goals

- No universal visual template for the ten forms.
- No mechanical rewriting of existing approved scripts.
- No change to source-supported facts or approved page missions.
- No new approval files, hashes, receipts, manifests, or parallel project
  directories.
