# Source-to-Markdown Output Contract

## Purpose

This contract defines the stable interface between `source-to-markdown` and downstream structure parsing, fact extraction, semantic understanding, solution drafting, and PPT-script generation.

## One Source = One Markdown File

Each source file produces one `.md` file. Batch conversion never concatenates unrelated sources. Recursive conversion preserves relative subdirectory structure under the chosen output directory.

## Provenance Front Matter

Every generated file starts with YAML front matter:

```yaml
---
source_file: "proposal.docx"
source_format: ".docx"
conversion_engine: "Microsoft MarkItDown"
converted_at: "2026-08-14T14:00:00+08:00"
ocr_requested: false
---
```

Field semantics:

- `source_file`: original local filename only; no semantic interpretation.
- `source_format`: lowercase suffix of the source file.
- `conversion_engine`: fixed engine identity.
- `converted_at`: conversion timestamp with local timezone offset.
- `ocr_requested`: whether the wrapper was explicitly asked to enable OCR.

Downstream agents must treat this front matter as conversion metadata, not as claims extracted from the source.

## Source Body Invariants

The Markdown body follows these invariants:

1. Source wording is not intentionally summarized, paraphrased, translated, completed, corrected, or inferred.
2. CRLF/CR newlines are normalized to LF.
3. Outside fenced code/text blocks, trailing spaces are removed.
4. Outside fenced code/text blocks, three or more consecutive blank lines collapse to two line breaks.
5. Outside fenced code/text blocks, Markdown headings are separated from following body text by one blank line.
6. Fenced code/text block contents are preserved except for global newline normalization.
7. Heading/list/table/link structure returned by MarkItDown is retained where possible.
8. Warnings are never inserted into the source body.

Whitespace normalization is allowed; semantic rewriting is not.

## Quality Warnings

The wrapper may emit non-destructive warnings:

- `empty_output`: no text was produced.
- `low_text_yield`: very little text was produced relative to source file size; scanned/image-heavy material may need OCR.
- `no_headings`: a long output contains no Markdown headings; structure should be checked.
- `ocr_content_present`: OCR-marked content exists in output.
- `conversion_placeholder`: output may contain a converter error/placeholder string.

Warnings are written to stderr. With `--report`, they are also written to `<output>.md.report.json`.

## Empty Output Policy

Empty output is an error by default. `--allow-empty` is only for workflows that must retain a conversion record even when no source text was extracted.

## OCR Policy

OCR is opt-in. When enabled, the wrapper requests Microsoft MarkItDown plugin support and an OpenAI-compatible LLM client. The wrapper must fail clearly if OCR dependencies, credentials, or model configuration are missing rather than silently claim OCR occurred.

OCR text is still source extraction; downstream agents should distinguish it from native text when MarkItDown includes OCR markers.

## Page and Layout Provenance

Page numbers, bounding boxes, and pixel-perfect layout are **not guaranteed** by this contract. If the upstream converter emits page markers, preserve them; do not manufacture page boundaries that are absent.

For tasks requiring exact page citations or layout reconstruction, use a page-aware document extraction or rendering pipeline in addition to this skill.

## Security Boundary

This wrapper accepts local filesystem paths and prefers MarkItDown's local-file conversion API when available. It intentionally does not expose URL conversion. Do not run untrusted files with unnecessary filesystem or network privileges.
