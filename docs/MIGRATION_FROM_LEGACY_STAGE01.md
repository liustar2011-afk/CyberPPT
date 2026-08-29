# Migration from legacy CyberPPT Stage 01

## Target

Use the `script` profile for new script-generation work while keeping the
strict/legacy Source Truth route and CyberPPT Stage 02 intact.

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

1. New work runs `.venv/bin/python3 -m cyberppt prepare-source-context <project>`
   and `.venv/bin/python3 -m cyberppt prepare-script-foundation <project>
   --profile script`, then writes one `foundation.json` from the returned task.
2. Contract, regulation and fact-by-fact verification retain strict Stage 01.
3. Existing Source Truth projects remain readable and project mechanically to the same Foundation contract.
4. Retire redundant legacy authorities only after representative script/strict comparison tests.
