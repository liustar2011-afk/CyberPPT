# CyberPPT Script Engine

> Standalone PPT script-generation subsystem for CyberPPT.

This directory is intentionally self-contained. It can live inside the current monorepo during migration and later be split into an independent Git repository without changing its internal layout.

## What it owns

The Script Engine owns only:

1. **UNDERSTAND** — source understanding and unified semantic foundation;
2. **PLAN** — communication goal, narrative, chapters, and page plan;
3. **AUTHOR** — whole-deck writing, critique, rewrite, and final script;
4. **EDIT PAGE** — targeted page revision after whole-deck authoring;
5. validation of its own delivery contracts.

It does not own visual style selection, ImageGen, SVG reconstruction, editable PPTX assembly, or Stage 02 QA.

## Workflow

```text
SOURCE
  ↓
UNDERSTAND
  ↓
foundation.json
  ↓
PLAN
  ↓
deck-plan.json
  ↓
Gate A — Deck Plan
  ↓
AUTHOR
  ├─ whole-deck narrative
  ├─ section writing
  ├─ page writing
  ├─ critic
  └─ rewrite
  ↓
final-script.md
  ↓
Gate B — Final Script
```

The default authoring unit is the whole deck. Single-page writing is an editing capability, not the primary production path.

## Authority model

Only three content artifacts are authoritative:

- `foundation.json`
- `deck-plan.json`
- `final-script.md`

`final-script.json` is an optional machine-readable mirror. Other files are cache, reports, diagnostics, or adapter outputs.

## Skills

The single routing entry is:

```text
.agents/skills/cyberppt-script-workflow/
```

It routes to:

```text
.agents/skills/
├─ cyberppt-script-understand/
├─ cyberppt-script-plan/
├─ cyberppt-script-author/
└─ cyberppt-script-edit-page/
```

## Contracts

- `contracts/foundation.schema.json`
- `contracts/deck-plan.schema.json`
- `contracts/final-script.schema.json`

The downstream contract is versioned as:

```json
{
  "contract": "cyberppt.final-script",
  "version": "1.0"
}
```

Internal Foundation and Plan schemas are private to the Script Engine and are not Stage 02 dependencies.

## CLI

Install in editable mode from this directory:

```bash
python -m pip install -e .
```

Validate artifacts:

```bash
cyberppt-script validate foundation foundation.json
cyberppt-script validate plan deck-plan.json
cyberppt-script validate final dist/final-script.json
```

Render a JSON final script into the Markdown contract accepted by the current CyberPPT Stage 02 parser:

```bash
cyberppt-script render-stage02 dist/final-script.json --output dist/final-script.md
```

## Loose coupling with CyberPPT Stage 02

The existing CyberPPT Stage 02 already accepts an external final-script path. The integration boundary is therefore only the final script file:

```bash
python -m cyberppt prepare-stage02-handoff <project> \
  --script <script-engine>/dist/final-script.md
```

After that, the host repository owns visual structure, style selection, image production, editable reconstruction, and PPTX QA.

Stage 02 must not read:

- `foundation.json`
- `deck-plan.json`
- Script Engine critique drafts
- semantic caches
- authoring state
- Script Engine Skill names

See `docs/BOUNDARY_CONTRACT.md`, `docs/MIGRATION_FROM_LEGACY_STAGE01.md`, and `docs/SPLIT_TO_STANDALONE.md`.

## Repository layout

```text
script-engine/
├─ .agents/skills/
├─ .github/workflows/
├─ contracts/
├─ references/
├─ script_engine/
├─ adapters/cyberppt-stage02/
├─ docs/
├─ examples/
├─ tests/
├─ workbench/
└─ dist/
```
