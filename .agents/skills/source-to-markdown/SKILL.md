---
name: source-to-markdown
description: Use when Word, PDF, PowerPoint, Excel, HTML, image, archive, or text source materials need conversion to Markdown before structure parsing, source review, fact extraction, semantic analysis, knowledge-base ingestion, or RAG.
---

# Source to Markdown

## Overview

Use the repository's native parsers first for DOCX, text formats, PPTX and
simple XLSX. Use Microsoft MarkItDown as a format-specific fallback, then apply
deterministic normalization and provenance metadata. Conversion is a
**source-preservation step**, not a writing or interpretation step.

For a CyberPPT project, `prepare-source-context` already performs native DOCX,
text and PPTX extraction and uses optional `openpyxl` for XLSX. Invoke this
conversion Skill only when the native result is missing, sparse or unsupported.

## Core Rule

**Do not summarize source content. Do not paraphrase, translate, complete, correct, or infer source content while converting it.** Preserve the wording and ordering produced by the converter. Keep conversion warnings outside the source body.

## Workflow

Run the commands below from this Skill directory with the repository interpreter at `../../../.venv/bin/python3`.

1. Identify whether the input is one local file or a directory of local files.
2. Use this wrapper only when the native parser is unavailable or produced sparse/failed extraction. Install the base package or the one required extra; never install `markitdown[all]` for the normal script path.
3. Run `../../../.venv/bin/python3 scripts/convert.py <input>` from this skill directory, or invoke the script by its absolute skill path with the same interpreter.
4. For a directory, add `--recursive` only when nested folders should be included.
5. Inspect stderr warnings. If a PDF or Office file yields empty or unusually sparse text and is image-heavy/scanned, retry with OCR only when credentials are available or the user explicitly wants OCR.
6. Pass the generated Markdown to downstream structure/semantic skills. Treat YAML front matter as provenance metadata, not source assertions.

Run `../../../.venv/bin/python3 scripts/convert.py --help` for all flags. Detailed output invariants are in `references/markdown-contract.md`; installation and platform examples are in `references/usage.md`.

## Common Commands

```bash
# one file
../../../.venv/bin/python3 scripts/convert.py proposal.docx

# folder
../../../.venv/bin/python3 scripts/convert.py ./sources

# recursive folder + reports
../../../.venv/bin/python3 scripts/convert.py ./sources --recursive --report

# scanned/image-heavy source; optional plugin/API use
../../../.venv/bin/python3 scripts/convert.py scan.pdf --ocr --ocr-model <MODEL>
```

## OCR Decision

Use normal extraction first. OCR is appropriate when the source is scanned, critical text exists only inside embedded images, or normal extraction produces empty/suspiciously sparse output. OCR requires the optional official `markitdown-ocr` plugin and an OpenAI-compatible client configuration.

## Boundaries

- Local files only; do not add URL fetching through this wrapper.
- Do not invent page numbers or missing structure.
- Do not claim pixel-perfect layout preservation.
- Do not merge multiple source files into one Markdown file during conversion.
- If conversion fidelity is uncertain, preserve the output and surface the warning for downstream review rather than silently rewriting it.
