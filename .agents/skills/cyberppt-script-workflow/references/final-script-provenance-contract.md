# Final Script 1.1 Provenance Contract

This reference is a shared Stage 01 hard contract for every new `AUTHOR`, regardless of `authoring_mode`. Read it before the active faithful or analytical authoring contract.

## 1. Version boundary

- New projects author Final Script contract `cyberppt.final-script` version `1.1`.
- Version `1.0` remains readable for legacy projects; do not silently invent provenance when loading legacy artifacts.
- A new 1.1 content page that lacks module provenance is invalid and must fail deterministic validation before delivery.

## 2. Stable visible-copy identity

Every 1.1 content-page `onscreen` module has a stable `id` beginning with `M`. Every authored `items` entry is an object with its own stable `id` and `text`.

IDs identify semantic output units, not layout boxes. Preserve an ID while revising wording when the unit keeps the same semantic role. Allocate a new ID when one unit is split, merged or replaced by a materially different proposition. Module and item IDs are globally unique within one Final Script artifact.

## 3. Explicit provenance only

Every module carries a `provenance` object with:

- `derivation`: `direct`, `synthesis`, or `relation`;
- `claim_refs`: the Foundation records that authorize the module-level proposition;
- `bindings`: one explicit binding for every visible target in the module.

Visible targets are:

- `heading` when the module has a heading;
- `text` when the module has text;
- each item ID when the module has an item.

Each visible target has exactly one binding. A binding contains `target`, `source_refs`, and one relation from `expresses`, `supports`, `qualifies`, `implements`, `contrasts`, or `sequences`.

Do not infer a binding from keyword overlap, adjacency, shared actors, topic similarity, layout position, professional common sense, or an LLM-generated explanation. If the binding is not defensible from Foundation and the page source boundary, rewrite or remove the visible proposition.

## 4. Derivation semantics

`direct` means one Foundation claim directly authorizes the module proposition. It uses exactly one `claim_ref`.

`synthesis` means the page proposition intentionally summarizes two or more compatible Foundation claims without inventing a new relationship. It uses at least two `claim_refs`. Preserve the weakest applicable status, condition, responsibility and claim strength across the synthesized claims.

`relation` means the module expresses a relationship authorized by two or more Foundation claims/relations. It uses at least two `claim_refs`. The relationship direction must already be source-explicit in faithful mode or explicitly approved as analytical inference in analytical mode.

## 5. Evidence scope

Every `claim_ref` and every binding `source_ref` must:

1. resolve to an indexed Foundation semantic record;
2. appear in the current Final Script slide `source_refs`;
3. remain inside the matching Deck Plan page source boundary.

Foundation remains the structured semantic authority. Provenance does not create facts or a parallel source parser.

## 6. JSON / Markdown synchronization

The JSON Final Script is the structured provenance authority. Delivery renders module provenance under the audit-only heading:

`### 证据映射（模块级｜不上屏）`

The block uses canonical JSON records so it can be parsed back to the exact module provenance without punctuation heuristics. `check-sync` treats the rendered Markdown as stale when the JSON provenance changes.

The evidence block is QA metadata. It is never part of `onscreen` visible copy, Stage 02 locked text, image-generation copy, speaker notes, or audience-facing slide content.

## 7. Revision behavior

For targeted revision, Critic, or Rewrite:

- preserve existing module/item IDs when semantic ownership is unchanged;
- update bindings whenever visible copy changes its evidence parentage;
- remove obsolete bindings when visible targets are removed;
- never retain a binding merely to make an old audit pass;
- never auto-fill missing provenance from lexical similarity.

A revision is complete only when schema validation, provenance validation, source-boundary validation, and JSON/Markdown synchronization all pass.
