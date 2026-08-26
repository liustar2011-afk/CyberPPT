# Lightweight page traceability

## Goal

Keep enough provenance to verify that a page's claims come from registered
source material, without making traceability a duplicated authoring product or
a Stage 02 visual-production input.

## Scope

The canonical provenance chain is reduced to:

`source unit -> Source Truth atomic record -> outline/page source_refs`

`source_unit_refs` remains on each atomic record.  A content page keeps only
the `source_refs` needed to support its content and the optional
`boundary_refs` needed to state a limit.  These references remain internal;
they are not presentation text and are not semantic inputs to visual design or
image-generation prompts.

## Changes

1. Source Truth no longer persists reverse `page_refs` or conclusion/page
   bidirectional traceability as authored requirements.  Diagnostics may derive
   those relations from the forward page references when a source audit needs
   them.
2. Stage 01 contracts retain forward source references for page claims,
   content units, relations, and boundaries.  They remove requirements whose
   only purpose is preserving a duplicate evidence inventory.
3. The page-script format retains `证据` and `边界依据` as internal metadata for
   script audit.  `证据映射` becomes optional explanatory editorial metadata and
   ceases to be a traceability gate.
4. Stage 02 handoff binds the approved script and outline.  It no longer binds
   Source Truth or forwards per-page source identifiers into visual-design
   inputs.  Stage 02 continues to consume locked text, page mission, core
   message, relationships, and onscreen-expression decisions.

## Compatibility and failure behavior

Existing projects and legacy payloads remain readable.  A missing obsolete
reverse field is accepted; a forward reference to a missing Source Truth record
still fails Stage 01 audit.  Any source or script change still invalidates the
Stage 02 handoff through the remaining content bindings.

## Verification

Targeted tests will cover: Source Truth acceptance without reverse mappings,
failure for dangling forward page references, script audit without an evidence
map, Stage 02 handoff without a Source Truth binding, and visual-design input
without source IDs.  Existing Stage 01 and Stage 02 tests will be run for
regressions.
