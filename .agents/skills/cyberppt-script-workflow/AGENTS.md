# cyberppt-script-workflow local authoring authority

This file applies only to `.agents/skills/cyberppt-script-workflow/` and its references.
It specializes the repository-level Stage 01 authoring rule so the active authoring
contract matches `authoring_mode` without creating two simultaneous authorities.

## Shared Final Script provenance contract

Before every new-project `AUTHOR`, and before any revision of a Final Script 1.1 artifact,
read `references/final-script-provenance-contract.md` completely. This is a shared delivery
contract, not a second authoring method.

New projects author Final Script contract `cyberppt.final-script` version `1.1`. Version
`1.0` remains readable only for legacy compatibility and must not be silently upgraded by
inventing evidence bindings. A 1.1 content module must carry stable module/item IDs and
explicit provenance for every visible target. Missing provenance blocks deterministic
validation and delivery.

The shared provenance contract does not authorize analytical inference. Source meaning,
claim strength, relationship construction and prose methods still come exclusively from
the active mode-specific authoring contract below.

## Single active contract per action

Before `AUTHOR`, `CRITIQUE`, `REWRITE`, targeted page revision, or whole-deck script
review, resolve the approved mode first:

- absent mode defaults to `faithful`;
- `faithful` -> read `references/faithful-authoring-contract.md` completely;
- `analytical` -> read `references/authoring-contract.md` completely.

Exactly one of those two mode-specific contracts is operational for a given action. Do not merge,
blend, average, or selectively combine their methods. The shared provenance contract above only
defines Final Script identity, evidence binding and synchronization; it does not alter the selected
authoring mode.

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
