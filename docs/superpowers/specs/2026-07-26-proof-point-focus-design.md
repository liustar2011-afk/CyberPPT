# Proof Point Focus Design

## Goal

Ensure each content page selects only evidence that directly supports its single business question and main message.

## Contract

- `proof_points` contains only material used to establish `main_message`.
- `boundary_refs` contains source records used only to constrain status, scope, or wording.
- `proof_points[*].source_refs` and `boundary_refs` must not overlap.
- Page-script input expands proof evidence under `evidence_text` and boundary material separately under `boundary_constraints`.
- Hidden receipts retain both canonical fields.
- Unassigned or boundary-only evidence is not placed in the main authoring evidence block.

## Current project correction

P09 retains S015 and S026 as its two proof sources. S059 is removed from P09 because project range, cycle, investment, procurement, and technical-route decisions do not answer the positioning question.

## Scope

No semantic model, new stage, or workflow controller. The change extends existing JSON, Markdown preparation, and deterministic audits.
