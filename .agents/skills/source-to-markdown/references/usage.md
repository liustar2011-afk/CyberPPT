# Source-to-Markdown Usage

## Install Once

The repository skill can use a local `.venv` inside its folder so it does not modify the user's global Python environment.

### Windows PowerShell

```powershell
cd <repo>/.agents/skills/source-to-markdown
.\scripts\install.ps1
```

Optional OCR dependencies:

```powershell
.\scripts\install.ps1 -Ocr
```

### macOS / Linux

```bash
cd <repo>/.agents/skills/source-to-markdown
./scripts/install.sh
```

Optional OCR dependencies:

```bash
./scripts/install.sh --ocr
```

The scripts create `.venv`, install Microsoft MarkItDown, and optionally install `markitdown-ocr` plus `openai`. The conversion wrapper automatically reuses the Skill-local environment first, then a `.venv` at the enclosing repository root when available.

Alternatively, install the runtime into your existing Python environment:

```bash
../../../.venv/bin/python3 -m pip install 'markitdown[all]'
```

## Single File

```bash
../../../.venv/bin/python3 scripts/convert.py proposal.docx
```

Default output: `proposal.md` beside the source.

Explicit output:

```bash
../../../.venv/bin/python3 scripts/convert.py proposal.docx -o ./out/proposal-source.md
```

Existing outputs are protected. Use `--force` only when replacement is intended.

## Directory

```bash
../../../.venv/bin/python3 scripts/convert.py ./source-materials --recursive -o ./normalized-md
```

## Conversion Report

```bash
../../../.venv/bin/python3 scripts/convert.py proposal.docx --report
```

This writes the Markdown plus `proposal.md.report.json`. Reports contain source/destination paths, text-character count, warnings, and any conversion error. They do not alter source Markdown content.

## OCR

Configure an OpenAI-compatible key and model after installing optional OCR dependencies:

```bash
export OPENAI_API_KEY="..."
export MARKITDOWN_OCR_MODEL="<MODEL>"
../../../.venv/bin/python3 scripts/convert.py scan.pdf --ocr
```

OCR may incur API usage/costs. Do not enable it for ordinary text-native documents without a reason.

## Help

```bash
../../../.venv/bin/python3 scripts/convert.py --help
```
