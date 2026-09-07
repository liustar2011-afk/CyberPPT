# Step 8B — Page Source Packet CLI

Date: 2026-09-07
Branch: `refactor/stage1-faithful-authoring`

Status: completed.

## Added CLI surface

New command:

```bash
.venv/bin/python3 -m script_engine.cli page-source \
  script/deck-plan.json \
  script/foundation.json \
  P01 \
  --output script/.cache/page-source/P01.json
```

Optional override:

```bash
--source-index <path-to-source-index.v2.json>
```

When omitted, `page-source` resolves:

`<foundation-dir>/.cache/source-index.json`

## Production changes

- `script_engine/cli_parser.py`
  - added `page-source` arguments;
- `script_engine/cli.py`
  - loads plan/Foundation/source-index;
  - validates source-index schema is `cyberppt.source_index.v2`;
  - resolves requested page;
  - injects the Deck Plan's root `authoring_mode` into the derived page context;
  - calls `build_page_source_packet()`;
  - optionally writes the derived packet under `.cache`;
  - fails closed for missing source index, unknown page or packet blocking issues.

The saved JSON does not include the CLI's `output` convenience field; the persisted packet remains a pure derived context record.

## Tests

Added `tests/script_engine/test_page_source_cli.py` covering:

- default sibling `.cache/source-index.json` resolution;
- exact source text in CLI output;
- derived `.cache/page-source/P01.json` persistence;
- unknown page failure;
- missing source-index failure.

## Authority boundary

The command does not mutate `foundation.json` or `deck-plan.json`. It does not create a new approval gate or semantic authority. Its output is disposable exact-source runtime context for AUTHOR.
