# cyberppt-script-workflow local authoring authority

This file applies only to `.agents/skills/cyberppt-script-workflow/` and its references.
It specializes the repository-level Stage 01 authoring rule so the active authoring
contract matches `authoring_mode` without creating two simultaneous authorities.

## Single active contract per action

Before `AUTHOR`, `CRITIQUE`, `REWRITE`, targeted page revision, or whole-deck script
review, resolve the approved mode first:

- absent mode defaults to `faithful`;
- `faithful` -> read `references/faithful-authoring-contract.md` completely;
- `analytical` -> read `references/authoring-contract.md` completely.

Exactly one of those two contracts is operational for a given action. Do not merge,
blend, average, or selectively combine their methods. The repository-level phrase
"single operational authority" therefore means one active mode-specific contract,
not that analytical judgment-first rules must govern faithful authoring.

If the Final Script declares `analytical` while the approved Deck Plan is not
analytical, stop and repair the mode mismatch before authoring.

## Faithful exact-source gate

For a faithful content page, exact source resolution is part of AUTHOR execution, not
an optional QA step. When the project has a v2 source index, generate or regenerate the
page's derived packet before drafting or materially rewriting that page:

```bash
.venv/bin/python3 -m script_engine.cli page-source \
  script/deck-plan.json \
  script/foundation.json \
  <PAGE_ID> \
  --output script/.cache/page-source/<PAGE_ID>.json
```

Read the packet before writing `full_copy`. A packet with
`status: rewrite_required` blocks that page until the source boundary is repaired.
The packet is disposable runtime context and never becomes an authoritative content
artifact. Generating it is evidence preparation only; it does not execute AUTHOR.

If a strict/legacy project has no compatible v2 source index, use its strongest exact
Source Truth / source-consumption bindings instead of reconstructing the page from
memory or a shortened preview.

## Shared hard constraints

Both modes remain subject to repository-level `AGENTS.md`, especially source scope,
claim strength, issuer voice, protected facts, formal document identity, visibility,
and the authoritative artifact chain.

`faithful` is source-native editorial transduction. It must not be upgraded to the
analytical contract merely because a page looks sparse, parallel, taxonomic, or lacks
a synthesized conclusion.
