# Page-Theme Evidence Focus Design

## Goal

Ensure every project selects page evidence around one page theme instead of
merely checking that cited evidence exists. The theme is defined by the
combination of `page_job`, `business_question`, and `main_message`.

## Diagnosis

The current contract validates source membership and field completeness, but
does not validate topical contribution. An unrelated record can therefore be
assigned to a page, copied into `proof_points`, and pass the deterministic
audit. The previous project correction exposed this gap across multiple pages,
not only P09.

## Design

Keep the existing Stage 01 workflow and add a small focus contract:

1. The Outline authoring input instructs the author to screen candidate
   evidence against all three theme fields before creating `proof_points`.
2. `proof_points` contains only evidence that establishes `main_message` or a
   necessary step in answering `business_question`.
3. Boundary and unresolved records default to `boundary_refs`; they may enter
   `proof_points` only when the page role is itself scope or decision and the
   boundary is part of the page's stated judgment.
4. Multiple raw records that establish one implication are consolidated into
   one proof point. A page must not become a catalogue of unrelated claims.
5. Page-script input expands only selected proof evidence under
   `evidence_text`; boundary material remains under `boundary_constraints`.

## Deterministic audits

Extend the existing argument-flow audit rather than adding a workflow stage:

- flag proof claims with no meaningful textual relationship to the page theme;
- flag boundary or unresolved records used as primary proof when the page role
  does not allow that use;
- flag pages whose primary proof points exceed the small single-theme limit;
- preserve the existing source-membership, overlap, and receipt checks.

The similarity rule is a conservative warning-grade gate: it uses normalized
Chinese character n-grams across the proof claim and the three theme fields.
It does not attempt semantic rewriting and does not reject supporting records
solely because their raw source wording differs from the synthesized claim.

## Data flow

`Source Truth` → focused Outline authoring instructions → Outline focus audit →
page-script authoring input with separated evidence → existing script audit.

Audit failure returns a focused retry strategy (`refocus_page_evidence`) so the
Outline is corrected before downstream prose or image-generation prompts are
created.

## Tests and acceptance

- unit tests cover an off-topic primary proof point, improper boundary use,
  excessive independent primary proof points, and valid synthesized evidence;
- existing Stage 01 and script tests remain green;
- regenerate the current power-supply project through the normal commands;
- Source Truth, Outline, and script audits must all pass without hand-editing
  the generated authoring input or final script.

## Scope

No semantic model, automatic rewriter, new stage, external dependency, or
workflow controller. This remains a small single-machine script tool.
