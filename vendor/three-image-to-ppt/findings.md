# Findings

- The vendored runner supports a default two-image path (`FULL + BACKGROUND + OCR JSON`) and an optional three-image path with a separate `TEXT` image.
- Batch mode accepts a manifest, preserves deterministic page order, isolates page failures, and writes one `qa.json` per page.
- CyberPPT adapts approved `page_image_pairs.json` into a versioned editable-text batch manifest, then passes the resulting BACKGROUND plus OCR/page JSON to `template_image_ppt_export`.
- The template exporter keeps the shared template chrome and places native editable text over the BACKGROUND asset in the approved body region.
- `render_ppt.mjs` uses the CyberPPT root `pptxgenjs@4.0.1` dependency; it no longer imports `@oai/artifact-tool`.
