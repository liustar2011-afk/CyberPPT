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

## Current Final Script contract

New projects author Final Script contract `cyberppt.final-script` version `1.2`.
A 1.2 content page uses:

- `full_copy` as the complete Stage 01 semantic manuscript;
- `fidelity_text` as the narrow exact-literal contract;
- page-level `source_provenance` from the current Author Preflight;
- no authored `onscreen` field.

`fidelity_text` items declare `required` or `if_rendered`. Ordinary full-copy prose,
page conclusions and stylistic wording are not exact-copy literals merely because they
may later appear in a generated image.

Final Script 1.0/1.1 remains read-compatible for existing projects. Before revising an
existing 1.1 artifact, read `references/final-script-provenance-contract.md` completely.
That legacy shared delivery contract still governs 1.1 stable module/item IDs and module
provenance. It is not a second authoring method and it does not make those 1.1 visible-
module requirements part of new 1.2 authoring.

All content pages continue to carry page-level `source_provenance`: `packet_sha256`,
`source_refs`, and `unit_ids`. This page-level lineage proves that the page consumed the
current exact-source gate and remains required independently of the 1.1 module/item
provenance compatibility path.

Stage 02 derives runtime `onscreen_text` from 1.2 `full_copy` and carries
`fidelity_text` separately through handoff, manifest, prompt compilation, reuse identity
and image-text QA. Stage 02 may rewrite ordinary content. Only fidelity literals receive
exact-copy semantics.

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

After `full_copy` passes the active mode-specific Critic, extract narrow `fidelity_text`
from exact source-backed literals. Do not create an authored `onscreen` projection for
Final Script 1.2. After writing the Final Script, run `audit-final`. Stage02 delivery must
use `render-stage02` with the current `--plan` and `--foundation`; that command revalidates
the Preflight, page lineage and native-source fidelity before writing output.

## Shared hard constraints

Both modes remain subject to repository-level `AGENTS.md`, especially source scope,
claim strength, issuer voice, protected facts, formal document identity and the
authoritative artifact chain. Where repository-level text still describes the legacy
1.0/1.1 authored-`onscreen` contract, the current Final Script 1.2 contract above governs
new authoring; legacy behavior applies only to existing 1.0/1.1 artifacts.

`faithful` is source-native editorial transduction. It must not be upgraded to the
analytical contract merely because a page looks sparse, parallel, taxonomic, or lacks
a synthesized conclusion.
