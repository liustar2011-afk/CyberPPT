---
name: cyberppt-workflow
description: Use as the navigation entry when a CyberPPT task asks for the main workflow, Stage 01/Stage 02 sequence, process location, or route selection. Read the canonical workflow overview, classify the task, and route to the authoritative stage Skill; do not duplicate or replace stage-specific rules.
---

# CyberPPT Workflow Navigation

This is a navigation-only Skill. It prevents agents from reconstructing the process from disconnected Skill files.

## Required action

1. Read [docs/CYBERPPT_WORKFLOW.md](../../../docs/CYBERPPT_WORKFLOW.md) completely enough to identify the task stage, required human stop, authoritative inputs and completion gate.
2. Read the repository root [AGENTS.md](../../../AGENTS.md) before acting.
3. For any task involving source materials, Source Truth, semantic models, Outline, page plans or their audits, invoke `cyberppt-source-foundation` as the mandatory first Stage 01 Skill.
4. For a request to convert an image, screenshot, or rendered visual into an editable PPTX, invoke `cyberppt-stage02-editable-pptx`. It owns the Stage 02 route and forbids direct adapter invocation. For other pure visual, image, SVG or PPTX QA tasks, route to the corresponding Stage 02 or page Skill identified by the overview.
5. Keep this Skill as a router. Do not create a second workflow, approval chain, status file or parallel authority.

## Route at a glance

`source -> Source Foundation -> business semantics -> communication goal -> Outline/page plan -> handoff -> page script -> final script -> Stage 02 visual production -> PPTX QA`

Formal Stage 01 sequence:

`cyberppt-source-foundation` -> `business-semantic-understanding` -> `ppt-outline-planning` -> `cyberppt-handoff` -> `cyberppt-write-single-page`

The four human stops are communication goal, chapter and page outline, detailed page content, and final full script.

## Boundary

This Skill does not parse source materials, author semantic outputs, plan pages, write scripts, generate images or assemble PPTX files. After routing, load the relevant stage Skill and follow its detailed contract.
