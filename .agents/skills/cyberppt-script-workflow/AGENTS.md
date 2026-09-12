# cyberppt-script-workflow local authoring authority

This file applies only to `.agents/skills/cyberppt-script-workflow/` and its references.
It specializes the repository-level Stage 01 authoring rule so the active authoring
contract matches `authoring_mode` without creating parallel content authorities.

## Mandatory Stage1 source gate contract

Before every `AUTHOR`, `CRITIQUE`, `REWRITE`, targeted content-page revision, whole-deck
script review, Final Audit, or Stage02 handoff, read
`references/stage1-faithful-gate-contract.md` completely.

That contract defines the deterministic source gate and cannot be replaced by prompt
instructions or agent memory. The operational chain is:

```text
source-index.v2
  → Page Source Packet v2
  → Author Preflight v2
  → AUTHOR
  → Final Script source_provenance
  → Native-source Fidelity Audit
  → Stage02
```

A faithful content page is not authorable unless its current Page Source Packet is
`passed` and `fresh`, exact source text is available, and the persisted Author Preflight
Manifest reports the page and project as passed. Missing, stale, invalid, partially
resolved or blocked source evidence stops the action.

There is no Foundation-preview fallback and no no-source-index fallback for the current
Stage1 faithful route. Repair the source index or source binding first.

## Shared Final Script provenance contract

Before every new-project `AUTHOR`, and before any revision of a Final Script 1.1 artifact,
read `references/final-script-provenance-contract.md` completely. This is a shared delivery
contract, not a second authoring method.

Final Script content pages also carry page-level `source_provenance` from the current
Author Preflight: `packet_sha256`, `source_refs`, and `unit_ids`. This page-level lineage
proves that the page consumed the current exact-source gate. It is separate from the
module/item provenance defined by `final-script-provenance-contract.md` and cannot be
substituted by it.

New projects author Final Script contract `cyberppt.final-script` version `1.1`. A 1.1
content module must carry stable module/item IDs and explicit module provenance for every
visible target. Missing module provenance or page-level source provenance blocks
deterministic validation and delivery.

The shared provenance contracts do not authorize analytical inference. Source meaning,
claim strength, relationship construction and prose methods still come exclusively from
the active mode-specific authoring contract below.

## Single active contract per action

Before `AUTHOR`, `CRITIQUE`, `REWRITE`, targeted page revision, or whole-deck script
review, resolve the approved mode first:

- absent mode defaults to `faithful`;
- `faithful` -> read `references/faithful-authoring-contract.md` completely;
- `analytical` -> read `references/authoring-contract.md` completely.

Exactly one of those two mode-specific contracts is operational for a given action. Do not merge,
blend, average, or selectively combine their methods. The Stage1 source gate and shared
provenance contracts define evidence identity and delivery safety; they do not alter the
selected authoring method.

If the Final Script declares `analytical` while the approved Deck Plan is not analytical,
stop and repair the mode mismatch before authoring.

## Faithful exact-source execution

For every faithful content page, generate or regenerate its exact-source Packet before
drafting or materially rewriting it:

```bash
.venv/bin/python3 -m script_engine.cli page-source \
  script/deck-plan.json \
  script/foundation.json \
  <PAGE_ID> \
  --source-index script/.cache/source-index.json \
  --output script/.cache/page-source/<PAGE_ID>.json
```

After all required page packets are current, build the project-level gate:

```bash
.venv/bin/python3 -m script_engine.cli author-preflight \
  script/deck-plan.json \
  script/foundation.json \
  --source-index script/.cache/source-index.json \
  --packet-dir script/.cache/page-source \
  --output script/.cache/author-preflight.json
```

Read the page Packet before writing `full_copy`. AUTHOR may proceed only when current
Preflight `summary.overall_status` is `passed`. Packet and Preflight are derived runtime
evidence and do not become new semantic authorities. Generating them is evidence
preparation only; it does not execute AUTHOR.

After writing the Final Script, run `audit-final`. Stage02 delivery must use
`render-stage02` with the current `--plan` and `--foundation`; that command revalidates the
Preflight, page lineage and native-source fidelity before writing output.

## Shared hard constraints

Both modes remain subject to repository-level `AGENTS.md`, especially source scope,
claim strength, issuer voice, protected facts, formal document identity, visibility,
and the authoritative artifact chain.

`faithful` is source-native editorial transduction. It must not be upgraded to the
analytical contract merely because a page looks sparse, parallel, taxonomic, or lacks
a synthesized conclusion.
