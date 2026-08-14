---
name: source-to-markdown
description: Use when Word, PDF, PowerPoint, Excel, HTML, image, archive, or text source materials need conversion to Markdown before structure parsing, source review, fact extraction, semantic analysis, knowledge-base ingestion, or RAG.
---

# Source to Markdown

## Overview

Use Microsoft MarkItDown as the conversion engine, then apply deterministic normalization and provenance metadata. Conversion is a **source-preservation step**, not a writing or interpretation step.

## Core Rule

**Do not summarize source content. Do not paraphrase, translate, complete, correct, or infer source content while converting it.** Preserve the wording and ordering produced by the converter. Keep conversion warnings outside the source body.

## Workflow

1. Identify whether the input is one local file or a directory of local files.
2. Run `python scripts/convert.py <input>` from this skill directory, or invoke the script by its absolute skill path.
3. For a directory, add `--recursive` only when nested folders should be included.
4. Inspect stderr warnings. If a PDF or Office file yields empty or unusually sparse text and is image-heavy/scanned, retry with OCR only when credentials are available or the user explicitly wants OCR.
5. Pass the generated Markdown to downstream structure/semantic skills. Treat YAML front matter as provenance metadata, not source assertions.

Run `python scripts/convert.py --help` for all flags. Detailed output invariants are in `references/markdown-contract.md`; installation and platform examples are in `references/usage.md`.

## Common Commands

```bash
# one file
python scripts/convert.py proposal.docx

# folder
python scripts/convert.py ./sources

# recursive folder + reports
python scripts/convert.py ./sources --recursive --report

# scanned/image-heavy source; optional plugin/API use
python scripts/convert.py scan.pdf --ocr --ocr-model <MODEL>
```

## OCR Decision

Use normal extraction first. OCR is appropriate when the source is scanned, critical text exists only inside embedded images, or normal extraction produces empty/suspiciously sparse output. OCR requires the optional official `markitdown-ocr` plugin and an OpenAI-compatible client configuration.

## Boundaries

- Local files only; do not add URL fetching through this wrapper.
- Do not invent page numbers or missing structure.
- Do not claim pixel-perfect layout preservation.
- Do not merge multiple source files into one Markdown file during conversion.
- If conversion fidelity is uncertain, preserve the output and surface the warning for downstream review rather than silently rewriting it.
