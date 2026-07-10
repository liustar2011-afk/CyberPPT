# Task 3 Report

## Status

Complete. Project-production exporter planning and running now consume the approved template text lock, full-image pair manifest, and speaker-notes manifest. The legacy `extract_content` parser was not changed.

## Impact Boundary

- Required upstream impact commands were run before edits.
- `extract_content` reported CRITICAL and was left read-only after the user narrowed the boundary.
- Disambiguated exporter impacts were LOW for `build_manifest`, `command_run`, and `build_parser`.
- The existing `command_plan` symbol was not changed; a new dispatcher preserves its standalone behavior.
- Staged `detect-changes` reported HIGH aggregate risk across 12 expected exporter flows. Review confirmed the real behavioral changes are confined to planning, running, manifest construction, and export; additional downstream symbols were attributed because inserted loaders shifted their indexed line locations.

## Implementation

- Added `load_template_text_lock()` with exact page-set, record-presence, and approval validation.
- Added `load_approved_full_images()` with exact page-set and resolved `full.path` file validation.
- Extended `build_manifest()` with `selected_pages`, project-production inputs, lock-owned title/subtitle/template settings, approved full-image paths, and approved speaker notes.
- Added project-production `plan` and `run` flags. `run` writes the project and exports without calling image generation.
- Fixed package-module and direct-script import compatibility for the image client.
- Kept standalone/direct script planning and generation behavior backward compatible.

## TDD Evidence

RED command:

```bash
python3 -m unittest tests.test_dual_image_rebuild_engine_assets tests.test_dual_image_overlay_template_rebuild
```

Observed expected failures for missing loader functions, unsupported `build_manifest` inputs, absent CLI flags, and package-module `ModuleNotFoundError`.

GREEN command:

```bash
python3 -m unittest tests.test_dual_image_rebuild_engine_assets tests.test_dual_image_overlay_template_rebuild
```

Result: 37 tests passed, 1 optional fixture skipped because it lacks the Task 1 project contract.

Expanded regression command:

```bash
python3 -m unittest tests.test_dual_image_template_body_region tests.test_dual_image_rebuild_engine_assets tests.test_dual_image_overlay_template_rebuild tests.test_final_script_pages tests.test_cli
```

Result: 79 tests passed, 1 optional fixture skipped.

Additional checks:

- `python3 -m scripts.dual_image_overlay.rebuild_engine.script_text_overlay --help`: pass.
- `python3 scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py --help`: pass.
- `python3 -m scripts.dual_image_overlay.rebuild_engine.template_image_ppt_export --help`: pass.
- `git diff --check`: pass.

## Concerns

- Project-production now validates the project contract, image-review approval, speaker-notes approval, manifest hashes, image hashes, and exact page cardinality before export.
- The legacy pages 12/13 regression uses a temporary copy and direct legacy script entry so it does not weaken the production CLI gate or mutate tracked project artifacts.
- Wiring these exporter inputs into the later produce-assemble command remains outside Task 3 scope.

## Review Fixes

The independent reviewer found a critical approval-bypass gap and duplicate-page acceptance. The fix added project-root discovery from all explicit approved inputs, validation of both approval records and current hashes, duplicate requested/declared/record pages rejection, and valid temporary PNG fixtures.

Focused verification after the fixes:

```bash
python3 -m unittest tests.test_dual_image_rebuild_engine_assets tests.test_dual_image_overlay_template_rebuild
```

Result: 48 tests passed.
