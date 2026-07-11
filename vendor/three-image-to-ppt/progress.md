# Progress

- 2026-07-11: Started workflow redesign after user approved two-image JSON as default and requested batch support.
- 2026-07-11: Added `--input-mode two-image|three-image` (two-image default) and `--manifest` batch scheduling. Verified the existing test suite and a two-page manifest; both page jobs completed independently with review QA.
- 2026-07-11: User confirmed the target is replacement of CyberPPT's non-editable full-image body path, not a separate PPT producer. The next implementation boundary is `BACKGROUND + editable JSON -> CyberPPT template_image_ppt_export`.
- 2026-07-11: Closed the CyberPPT integration plan. The adapter, editable-body template export, mode-aware production/batch routing, delivery gates, and regression tests are implemented. The renderer now uses PptxGenJS instead of `@oai/artifact-tool`.
