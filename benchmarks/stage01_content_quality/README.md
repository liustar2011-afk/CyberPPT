# Stage 01 Content Quality Benchmark

This benchmark proves editorial quality with real-page before/after samples and
a readable scorecard. Schema validation, lint and audit results remain separate
contract evidence.

## Baseline

- Reliable semantic baseline: CyberPPT `8726f23e97241efbf11bc59029bab55a92a2692b`
- Failure sample only: `f6a3745bbb08c27e35c8b6d92acf6e7c7eda826e`
- Reference implementation: `addsumtech/slides_maker@0b38732543f62920f094a18c1621992068a18f57`
- Initial real sample: pages P03/P04 from the power-data infrastructure project

The case file contains only page-level planning and visible-copy material. It
does not copy the source document, full Foundation, project state, approvals or
runtime receipts.

## Review protocol

1. Present before and after candidates as A/B without commit labels.
2. Score every rubric dimension from 1 to 5.
3. Record concrete evidence for each change in score.
4. Reveal candidate identity after scoring.
5. Keep source recall and contract audits as separate checks.

The first review is an agent-performed blinded comparison using the same source
scope. It is human-readable evidence, with no claim of independent human-panel
validation. A later human reviewer can append a second score column without
changing the case fixture.

## Files

- `rubric.json`: stable scoring dimensions and anchors
- `cases/power-p03-p04.json`: real before/after page samples
- `review-power-p03-p04.md`: readable blinded scorecard and reveal
- `f6a3745-disposition.md`: one-time failure-increment treatment record
