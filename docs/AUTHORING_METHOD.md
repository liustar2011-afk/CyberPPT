# Authoring Method v0.5

## Goal

Convert formal source material into a source-faithful, analytically strong PPT
script with three authoritative content artifacts:

`foundation.json -> deck-plan.json -> final-script.md`

## 1. Foundation from the source

The default `script` profile builds one deterministic source index and authors
one Foundation. Foundation preserves source structure, thesis, argument order,
facts, numbers, responsibilities, constraints, boundaries, assets and open
questions with stable source-unit references.

Direct reading covers bounded material. Long reading preserves the complete
argument skeleton, shows mapped previews, and deep-reads the selected 15%–30%
of source text before precise claims are authored. Selection and exclusion
reasons remain visible at the first human review stop.

Contract, regulation, fact-by-fact verification and legacy migrations route to
the `strict/legacy` profile and its complete Source Foundation chain.

## 2. Source-constrained narrative planning

PLAN writes the argument twice inside the same `deck-plan.json`:

1. establish the deck thesis, recognition path, page necessity and peak;
2. write each page question, disputable message, selected evidence, content
   units, beat and spoken thread.

Complex material develops two or three source-constrained narrative candidates.
The Plan Critic compares their divergence, rejects strawman options, selects one
path, then rewrites weak messages, duplicate pages and affected handoffs. Review
notes remain internal working context.

Source chapter order is preserved by default. A page may preserve or split one
source section, or merge closely related content inside one source chapter.
Cross-chapter movement requires explicit user authorization.

## 3. Deck Plan contracts

v2 lean is the production Deck Plan contract for every new project. It preserves
source thesis, source argument order and chapter/page argument-node bindings
while leaving judgments, evidence selection, onscreen hierarchy and
relationships to AUTHOR. Machine audits continue to enforce source identity,
reference resolution, argument intersection, visibility and inference
boundaries.

The Foundation profile is independent from this planning contract.
strict/legacy retains Source Truth, full semantic modelling and stronger source
fidelity checks; `script` retains the lightweight UNDERSTAND route. v1 strict
Deck Plans must be migrated to v2 lean before authoring.
- independent review accepts Foundation readability and long-reading selection;
- v2 wins at least three of four blind-review dimensions;
- average manually authored planning fields fall by at least 40%.

Run `benchmarks/run.py` for the current evidence ledger. Synthetic shape fixtures
never count as real projects or human quality evidence.

## 4. Page authoring closed loop

AUTHOR uses this sequence:

`full page argument -> onscreen selection -> expression candidates -> qualitative review -> whole-page rewrite`

High-density pages, peak pages, conclusions and Critic priorities develop a
judgment-led candidate and an evidence-led candidate. The selected expression
must preserve the approved Plan message, decisive evidence, responsibilities,
numbers, conditions and boundaries. Candidate drafts and review notes do not
become additional authorities.

## 5. Inference and visibility

Source-supported analysis may explain how several facts fit together. New
facts, unsupported causal mechanisms, rankings, forecasts and commitments stay
outside the authoritative script. External current facts require explicit
verification and provenance.

Audience scope controls exposure. Restricted evidence remains available to the
internal proof process and appears in audience-facing prose only after explicit
approval.

## 6. Critic priorities

The whole-deck Critic prioritizes source structure, section coverage, page
necessity, narrative advancement, relation basis, inference boundaries,
compression loss, peak-page strength, composed claims and chart wrong-reading
risk. Deterministic audits provide provenance and contract baselines; readable
before/after samples and reviewer scores provide content-quality evidence.

## 7. User experience

The natural-language entry remains:

`根据这个 Word 生成 PPT 脚本。`

The user-facing stops remain:

1. `脚本规划待确认`;
2. `最终脚本已生成`.
