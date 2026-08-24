---
name: cyberppt-workflow
description: Use as the navigation entry when a CyberPPT task asks for the main workflow, script generation, Stage 01/Stage 02 sequence, process location, or route selection. New script-generation work is routed through the standalone script-engine boundary; Stage 02 remains an independent renderer that consumes an approved final script by path. Legacy Stage 01 remains available only for migration and diagnostics.
---

# CyberPPT Workflow Navigation

This is a navigation-only Skill. It prevents agents from reconstructing the process from disconnected Skill files.

## Required action

1. For new work, read [docs/CYBERPPT_WORKFLOW_V2.md](../../../docs/CYBERPPT_WORKFLOW_V2.md) as the routing authority. Read [docs/CYBERPPT_WORKFLOW.md](../../../docs/CYBERPPT_WORKFLOW.md) only when legacy Stage 01 details or deeper Stage 02 implementation details are required.
2. Read the repository root [AGENTS.md](../../../AGENTS.md) before acting.
3. For **new work whose goal is to understand source material and produce a PPT script**, enter the standalone [script-engine](../../../script-engine/README.md). Read `script-engine/AGENTS.md` and route through its `.agents/skills/` sequence.
4. For **existing projects that explicitly depend on legacy Stage 01 Source Truth / Outline / page-contract artifacts**, the former Stage 01 skills remain available as a compatibility and diagnostic route. Do not introduce those internal artifacts into a new Script Engine project.
5. For **Stage 02 visual production from an approved script**, use the existing Stage 02 route. Stage 02 accepts the final script by path and must not depend on Script Engine `foundation.json`, `deck-plan.json`, critique files, or Skill names.
6. For image/screenshot-to-editable-PPTX tasks, invoke `cyberppt-stage02-editable-pptx`. The aliases “高保真+Quick”, “高保真 Quick”, “无字底图+文字 SVG”, “authored SVG”, and “图片转可编辑 PPT” always resolve to `stage02.high_fidelity_quick_editable`.
7. Keep this Skill as a router. Do not create a second workflow, approval chain, status file, or parallel content authority.

## Default route for new script-generation work

`source -> Script Engine UNDERSTAND -> PLAN -> AUTHOR -> final-script.md -> Stage 02 handoff -> visual production -> PPTX QA`

Script Engine internal authorities:

- `foundation.json`
- `deck-plan.json`
- `final-script.md`

Only `final-script.md` crosses the Stage 01 / Stage 02 boundary.

The default Script Engine human gates are:

1. Deck Plan;
2. Final Script.

Targeted page review is invoked on demand through `cyberppt-script-edit-page` and is not a mandatory whole-workflow stop.

## Stage 02 boundary

The host Stage 02 command accepts an external final script path:

```bash
python -m cyberppt prepare-stage02-handoff <project> --script <final-script.md>
```

After this handoff, the existing Stage 02 owns visual structure, style selection, ImageGen, reconstruction, and PPTX QA.

Registered Stage 02 assembly routes remain unchanged:

- `stage02.high_fidelity_quick_editable` -> `--assembly-mode editable`
- `stage02.picture_ppt` -> `--assembly-mode image`
- `stage02.dual_delivery` -> `--assembly-mode both`

## Legacy Stage 01 compatibility route

The following route remains only for projects or diagnostics that explicitly require the old authority model:

`cyberppt-source-foundation -> business-semantic-understanding -> ppt-outline-planning -> cyberppt-handoff -> cyberppt-write-single-page`

Do not treat this compatibility route as the default path for new script authoring.

## Boundary

This router does not parse source materials, write scripts, generate images, or assemble PPTX files. After routing, load the authoritative Script Engine or Stage 02 Skill and follow its contract.
