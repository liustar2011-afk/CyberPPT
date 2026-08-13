# Source Chapter Placement Diagnostics Design

## Goal

Help the Stage 01 author identify source units whose original document heading is likely not the best home for their reporting role. The feature produces recommendations only. It must never move source content, change Source Truth, or rewrite the authoritative Outline.

## Scope

The diagnostic runs after semantic understanding and Source Truth are available, and before the author completes the formal Outline. It consumes only existing artifacts:

- source heading tree and `SU-*` source units;
- semantic argument model;
- Source Truth records and their source-unit / semantic-node references;
- the current Outline when it exists.

It returns a bounded set of candidate placement suggestions. Each suggestion contains source-unit and source-heading identifiers, the current source-heading path, the inferred semantic role, one or more suggested reporting chapter IDs when the Outline is present, an evidence summary expressed as identifiers and structured roles, and a confidence level.

## Decision policy

The diagnostic must classify only three outcomes:

1. `keep_source_context`: the original heading remains a suitable source context, or evidence is insufficient.
2. `suggest_reporting_rehome`: the semantic role strongly aligns with a different approved reporting chapter topic scope.
3. `suggest_cross_chapter_reference`: the item is supporting evidence for more than one reporting chapter and should have one author-selected primary home plus references elsewhere.

No outcome is an error or changes audit status. Suggestions are emitted only when structural evidence is sufficient; text length, keyword matching, generic similarity, and an original heading title alone must not create a suggestion.

## Integration

Add a pure diagnostic function beside the existing semantic-evidence cross-audit. It builds indexes for source-unit heading paths, Source Truth record semantic roles, and Outline chapter topic scopes. The command layer attaches the result to an existing Stage 01 diagnostic report rather than creating an approval, status, binding, or parallel project artifact.

If no Outline exists, the result may identify an inconsistent source context and semantic role, but must not invent a target chapter. Once an Outline exists, target chapters are limited to declared `storyline.chapter_missions[].topic_categories` and must cite the matching semantic evidence.

The author reviews the list and makes any accepted change in the existing authoritative Outline. Existing outline audits remain the enforcement layer: topic scope, one-topic-per-page, page order, and evidence traceability validate the author-selected result.

## Error handling and output limits

- Missing optional inputs yield no candidate, not a failure.
- Unknown IDs are ignored by the diagnostic and remain the responsibility of existing blocking audits.
- Limit output to a small deterministic maximum per source document and omit source-body text.
- Include `reason_codes`, relevant IDs, and a minimal suggested author action; do not include an automatic patch.

## Tests and acceptance

1. A source unit under an implementation heading that is structurally mapped to an approved mechanism chapter yields `suggest_reporting_rehome` with identifier-based evidence.
2. A source unit with evidence for two approved chapter scopes yields `suggest_cross_chapter_reference`, without duplicating content or choosing a primary home automatically.
3. A source unit with only a heading-title mismatch yields no suggestion.
4. A missing Outline yields no invented target chapter.
5. Existing Source Truth and Outline audit statuses, exit codes, and outputs remain unchanged.
6. The report is deterministic and contains no copied source prose.
