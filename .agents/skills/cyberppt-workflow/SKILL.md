---
name: cyberppt-workflow
description: Use as the navigation entry when a CyberPPT task asks for the main workflow, Stage 01/Stage 02 sequence, process location, or route selection. Read the canonical workflow overview, classify the task, and route to the authoritative stage Skill; do not duplicate or replace stage-specific rules.
---

# CyberPPT Workflow Navigation

This is a navigation-only Skill. It prevents agents from reconstructing the process from disconnected Skill files.

## Required action

1. Read [docs/CYBERPPT_WORKFLOW.md](../../../docs/CYBERPPT_WORKFLOW.md) completely enough to identify the task stage, required human stop, authoritative inputs and completion gate.
2. Read the repository root [AGENTS.md](../../../AGENTS.md) before acting.
3. For ordinary new source-to-script work, use `cyberppt-script-understand` after deterministic source indexing. Invoke `cyberppt-source-foundation` for strict/legacy work involving contracts, regulation, fact-by-fact verification, Source Truth, full semantic models, or old-project migration. For deck planning or page writing/rewriting, invoke `cyberppt-script-workflow` after a validated `script/foundation.json` exists.
4. For a request to convert an image, screenshot, or rendered visual into an editable PPTX, invoke `cyberppt-stage02-editable-pptx`. It owns the Stage 02 route and forbids direct adapter invocation. For other pure visual, image, SVG or PPTX QA tasks, route to the corresponding Stage 02 or page Skill identified by the overview.
   The aliases “高保真+Quick”, “高保真 Quick”, “无字底图+文字 SVG”,
   “authored SVG”, and “图片转可编辑 PPT” always resolve to
   `stage02.high_fidelity_quick_editable`; load the Stage 02 Skill instead of
   searching legacy `scripts/image_to_editable_svg/` code.
5. Keep this Skill as a router. Do not create a second workflow, approval chain, status file or parallel authority.

## Route at a glance

Default: `source index -> foundation -> deck plan -> author -> final script -> Stage 02 visual production -> PPTX QA`

Strict/legacy: `source -> Source Foundation -> business semantics -> project-foundation -> deck plan -> author -> final script -> Stage 02 visual production -> PPTX QA`

Registered Stage 02 assembly routes:

- `stage02.high_fidelity_quick_editable` -> `--assembly-mode editable`
- `stage02.picture_ppt` -> `--assembly-mode image`
- `stage02.dual_delivery` -> `--assembly-mode both`

Strict/legacy Stage 01 sequence:

`cyberppt-source-foundation` -> `business-semantic-understanding` -> `project-foundation` -> `cyberppt-script-workflow` (PLAN/AUTHOR)

The two human stops in the plan/author segment are **脚本规划待确认** (deck plan) and **最终脚本已生成** (final script).

## Boundary

This Skill does not parse source materials, author semantic outputs, plan pages, write scripts, generate images or assemble PPTX files. After routing, load the relevant stage Skill and follow its detailed contract.
