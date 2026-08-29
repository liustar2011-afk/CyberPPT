# Strict/legacy Source Foundation integration

This document covers the full Source Truth path for contracts, regulation,
fact-by-fact verification and old-project compatibility. Ordinary new script
projects use the lighter `script` profile described in `CYBERPPT_WORKFLOW.md`.

## Recommended setup

From the repository root:

```bash
python -m pip install -e .
```

Install Microsoft MarkItDown only for the required fallback format:

```bash
python -m pip install markitdown
python -m pip install 'markitdown[pdf]'  # only when PDF support is required
```

Optional OCR:

```bash
python -m pip install markitdown-ocr openai
```

## Project flow

Assume the project is `projects/example` and the source is `projects/example/source/方案.docx`.

### 1. Convert, parse, and prepare semantic work

```bash
python scripts/source_foundation_pipeline.py \
  projects/example/source/方案.docx \
  -o projects/example/workbench/source-foundation \
  --prepare-semantic \
  --report
```

The command creates normalized Markdown, structure/fact-base artifacts, and a semantic workpack. The semantic outputs themselves are authored by the `business-semantic-understanding` Skill and then validated.

### 2. Prepare and author the PPT outline

After semantic validation:

```bash
python scripts/source_foundation_outline.py \
  projects/example/workbench/source-foundation/semantic/方案 \
  -o projects/example/workbench/source-foundation/outline/方案 \
  --request-text '面向领导汇报，突出为什么做、建设什么、如何推进'
```

Use `ppt-outline-planning` to author `deck-brief.json` and `page-plan.json`, validate them, and render `ppt-outline.md` for the human gate.

### 3. Project into CyberPPT downstream contracts

After outline approval:

```bash
python scripts/source_foundation_handoff.py \
  projects/example/workbench/source-foundation/foundation/方案 \
  projects/example/workbench/source-foundation/semantic/方案 \
  projects/example/workbench/source-foundation/outline/方案 \
  -o projects/example \
  --cyberppt-root . \
  --force
```

This creates compatibility views under the existing CyberPPT Stage 00/01 paths and records `integration/authority-map.json` plus `integration/cyberppt-handoff-report.json`.

### 4. Continue with existing CyberPPT production

Use `cyberppt-write-single-page`, then the existing script assembly/audit and Stage 02 visual/image/SVG/PPTX pipeline.

## Key invariant

`workbench/source-foundation/**` is authoritative for source understanding and deck planning. The projected CyberPPT `semantic-argument-model.json`, `source-truth.json`, and `outline.json` are downstream compatibility artifacts only.
