# Migration from legacy CyberPPT Stage 01

## Target

Use this standalone Script Engine for new script-generation work while keeping CyberPPT Stage 02 intact.

## Capability mapping

| Legacy responsibility | Script Engine | Decision |
|---|---|---|
| source extraction / structure | UNDERSTAND | retain capability, collapse authority into `foundation.json` |
| business semantic understanding | UNDERSTAND | merge into unified semantic foundation |
| communication strategy | PLAN | integrate into deck goal and narrative planning |
| outline planning | PLAN | replace with lightweight `deck-plan.json` |
| single-page default production | AUTHOR / EDIT PAGE | whole-deck AUTHOR becomes default |
| chapter review | AUTHOR Critic | integrate into whole-deck critique |
| page lint / preflight | optional diagnostics | do not make them the primary authoring method |

## Safe migration

1. Side-by-side test with legacy Stage 01.
2. Make Script Engine the default for new script work.
3. Retire redundant legacy authorities after representative regression tests.
