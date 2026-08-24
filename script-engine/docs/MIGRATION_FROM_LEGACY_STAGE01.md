# Migration from legacy CyberPPT Stage 01

## Target

Replace the current multi-authority Stage 01 content pipeline with a standalone Script Engine while keeping CyberPPT Stage 02 intact.

## Capability mapping

| Legacy responsibility | Script Engine v2 | Migration decision |
|---|---|---|
| source extraction / source structure | UNDERSTAND | retain capability, collapse downstream authority into `foundation.json` |
| business semantic understanding | UNDERSTAND | merge into unified semantic foundation |
| communication strategy | PLAN | integrate into deck goal and narrative planning |
| `ppt-outline-planning` | PLAN | replace with lightweight `deck-plan.json` |
| `cyberppt-author-stage01-outline` | PLAN | retire as separate authoring route |
| Source Truth → CyberPPT projection / Stage 01 handoff | boundary adapter only | remove from authoring workflow |
| `cyberppt-write-single-page` as default production | AUTHOR / EDIT PAGE | whole-deck AUTHOR becomes default; single-page becomes targeted editor |
| `chapter-structure-review` | AUTHOR Critic | integrate into whole-deck critique pass |
| page preflight / page lint | optional diagnostics | do not make them the primary authoring method |
| full script audit | delivery QA | keep deterministic checks where useful, but do not require legacy Outline / Source Truth authority for Stage 02 |

## New authority surface

Only three content artifacts are authoritative:

1. `foundation.json`
2. `deck-plan.json`
3. `final-script.md`

`final-script.json` is an optional machine-readable mirror. Everything else is a cache, report, diagnostic, or compatibility artifact.

## Human gates

Legacy Stage 01 uses multiple fixed stops. Script Engine v2 defaults to two:

1. Deck Plan approval;
2. Final Script approval.

Targeted page review remains available on demand.

## Stage 02 integration

The host repository already accepts an external script path for Stage 02 handoff. Migration therefore does not require Stage 02 to understand `foundation.json` or `deck-plan.json`.

Host integration pattern:

```text
script-engine/dist/final-script.md
        ↓
CyberPPT prepare-stage02-handoff --script <external path>
        ↓
visual structure / style / image generation / editable PPTX
```

## Safe migration sequence

### Phase 1 — side-by-side

Keep legacy Stage 01 unchanged. Run Script Engine on selected projects and send only `final-script.md` into Stage 02.

### Phase 2 — make Script Engine the default authoring route

Update workflow routing so new content-generation tasks enter Script Engine. Keep legacy Stage 01 skills as migration/diagnostic tools.

### Phase 3 — retire redundant legacy authorities

After representative projects pass regression comparison, archive or remove duplicated Outline authoring, handoff projection, and default single-page production routes.

## Regression criteria

Before retiring the legacy path, compare at least:

- source-critical content coverage;
- factual and responsibility-boundary fidelity;
- chapter narrative quality;
- page-level argument quality;
- onscreen readability;
- Stage 02 handoff success;
- visual production success;
- targeted page edit behavior.
