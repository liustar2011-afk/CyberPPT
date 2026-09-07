# Step 8A — Page Source Packet core

Date: 2026-09-07
Branch: `refactor/stage1-faithful-authoring`

Status: completed; CLI wiring deferred to the next step.

## Purpose

AUTHOR must not write a faithful page from a long-mode `mapped-preview` when the page's exact source units are available. This step adds a deterministic runtime resolver:

`page.source_refs -> Foundation item -> source-unit refs -> exact source-index.v2 unit text`

The packet is explicitly derived runtime context and is not a new semantic authority.

## Added

### `script_engine/page_source_packet.py`

`build_page_source_packet(page, foundation, source_index)` returns:

- `schema: cyberppt.page_source_packet.v1`
- `authority: derived_runtime_context`
- explicit authoritative chain: source / Foundation / Deck Plan / Final Script
- page ID/title/source refs
- each resolved Foundation record
- exact source units with complete, untruncated `text`
- semantic units where present
- protected actors, numbers, conditions, status, strength, claim origin and visibility
- blocking `issues` for unknown page refs
- non-blocking `warnings` for legacy/unresolved exact-unit bindings

Important behavior:

- source-unit refs are resolved without relying on the `SU-` prefix, so compatibility namespaces can be reported rather than silently discarded;
- direct page refs to source units are supported as a fallback;
- the function does not rewrite or summarize exact source text;
- missing exact source text does not create a fake replacement; it is surfaced as a warning while Foundation text remains available.

### `tests/script_engine/test_page_source_packet.py`

Covers:

1. a long conceptual paragraph that lacks the normal long-mode critical markers and must still be returned in full, including an end marker beyond preview range;
2. expansion of linked actor, number, condition, status, strength and visibility payload;
3. blocking unknown page source refs;
4. legacy Foundation refs that cannot resolve in source-index.v2, reported as warnings rather than fabricated text.

## Boundary

No CLI command or Deck Plan schema change is included in this step. This isolates the exact-source resolution primitive before wiring it into AUTHOR workflow/CLI.
