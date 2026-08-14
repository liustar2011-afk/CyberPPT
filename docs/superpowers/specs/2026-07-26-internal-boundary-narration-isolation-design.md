# Internal Boundary and Narration Isolation Design

## Goal

Prevent internal scope, evidence-state, and cross-page controls from becoming
visible briefing content or defensive speaker coaching.

## Diagnosis

The current writing contract requires every content page to complete a
"boundary and handoff" beat and routes analysis asides into `边界` or
`讲解提示`. At the same time, `reserved_for_later`, `boundary_refs`, and
`boundary_constraints` are always supplied to the author. This combination
encourages repeated phrases such as "avoid misunderstanding", "not a
commitment", and "distinguish direction from phase one", even when those
qualifications are not the page's business topic.

## Contract

- `boundary_refs`, `boundary_constraints`, and `reserved_for_later` remain
  internal authoring and audit controls.
- Internal controls do not enter `完整文字稿`, `上屏文字`, `讲解提示`, or
  `【演讲者备注】`.
- The default prose structure is judgment, support, and implication. A
  boundary is not a mandatory fourth beat.
- `讲解提示` may state the order or emphasis of the business explanation. It
  must not coach the speaker to prevent misunderstanding or repeatedly
  distinguish commitment states.
- Speaker notes narrate the page's business judgment and support. They must
  not consume internal boundary fields.
- A constraint may remain visible only when the page's own `page_job`,
  `business_question`, or `main_message` makes that constraint the business
  subject, such as a scope, admission-condition, investment-assumption, or
  decision-condition page.

## Implementation

1. Update the repository writing reference and generated page-script authoring
   input to label boundary fields as internal-only.
2. Remove the requirement that every page end with a boundary beat.
3. Extend script parsing to retain `讲解提示` separately from speaker notes.
4. Add deterministic audit rules for defensive coaching phrases in
   `讲解提示` and for internal-boundary leakage into speaker notes.
5. Exempt pages whose declared theme is itself a constraint, using the three
   canonical theme fields rather than evidence type alone.
6. Regenerate and re-audit the current project, removing all matching
   narration leakage across the deck rather than editing only P11.

## Tests and Acceptance

- A normal business page fails when its coaching or notes contain phrases such
  as "避免听众误解", "不要讲成", "不是承诺", or "反复区分".
- A genuine scope or decision-condition page may state its substantive
  constraint without failure.
- Internal boundary fields continue to be present in receipts and evidence
  audits.
- Existing Stage 01 and script tests remain green.
- The current project's Source Truth, Outline, and final script audits pass
  after regeneration, with no defensive boundary coaching in ordinary pages.

## Scope

No new workflow stage, model call, semantic service, or automatic rewriting
engine. This is a small extension to the existing authoring and audit
contracts.
