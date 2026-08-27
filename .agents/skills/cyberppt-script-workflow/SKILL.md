---
name: cyberppt-script-workflow
description: Natural-language router for CyberPPT-Script. Generate or revise PPT scripts from formal source materials while preserving source chapter structure by default and allowing source-supported analytical deepening inside that structure. Never require the user to know internal stages, schemas, or CLI commands.
---

# CyberPPT Script Engine — Natural-Language Workflow

## 1. Routing principle

The source controls content boundary and default chapter order. The engine controls semantic understanding, analytical deepening, page decomposition and PPT expression.

Do not reply by asking the user to choose an internal stage when the route can be inferred from the request and current project artifacts.

Read:

1. `AGENTS.md`;
2. `docs/SOURCE_FIDELITY_AND_ANALYSIS.md`;
3. the stage Skill needed for the current route.

## 2. New source-to-script

Internal route:

`UNDERSTAND -> PLAN -> Gate A -> AUTHOR -> CRITIQUE -> REWRITE -> DELIVER`

Automatically:

1. scaffold `projects/<slug>/` and retain source files;
2. extract/index source structure when possible;
3. build a Foundation with atomic facts, explicit relations and supported inferred relations;
4. preserve source chapters by default and plan PPT pages within that structure;
5. present **脚本规划待确认**;
6. after ordinary approval language, author the complete script;
7. run Critic, rewrite, deterministic audits and delivery validation;
8. report **最终脚本已生成**.

## 3. Re-plan

Distinguish two cases.

### Expression / pagination re-plan

Examples:

- `重新做分页`
- `第3章页数太多`
- `这几节怎么合页更好`
- `整套PPT表达逻辑再优化`

Keep `source_structure_mode: preserve`. Re-plan page split/merge, chapter-internal logic, analysis model and page arguments.

### User-authorized source restructuring

Examples:

- `把合作机会提前到第二章`
- `重新安排五章顺序`
- `删掉建设背景，重点讲合作`

Set `source_structure_mode: user_authorized_restructure` and record `user_authorized_cross_chapter` only where the request requires it.

Do not infer restructuring permission merely from a request for a better PPT.

## 4. Continue

Identify the active project and run `cyberppt-script status projects/<slug>`. Resume from the next unresolved gate. Approval language after an approved plan authorizes whole-deck writing; never ask the user to say an internal stage name.

## 5. Targeted page edit

Read:

- target page and adjacent pages;
- corresponding deck-plan entry;
- `source_scope`;
- relevant Foundation facts/relations/boundaries;
- `analysis_basis` where present.

Preserve source chapter boundaries unless the requested edit explicitly authorizes a structural change.

## 6. Whole-deck review / rewrite

Run Critic + Rewrite against Foundation, plan and current script. Review source structure, inference boundary, analytical depth, group-claim strength, classification/progression, optionality, visibility, compression loss and formal register.

Do not expose Critic self-dialogue. Return only the rewritten result and a concise summary of material changes when useful.

## 7. Planning gate

Show a readable **脚本规划待确认** containing:

- source chapter structure to be preserved;
- planned page allocation by chapter;
- each page's question, core message and dominant analysis/logic when useful;
- split/merge decisions that materially change Word-to-PPT projection;
- inferred relationships or source conflicts that merit user attention;
- any restricted/internal material requiring an exposure decision.

Do not dump internal JSON by default.

Run `cyberppt-script review-plan <deck-plan.json> <foundation.json>` and present
its Markdown reading strip at this gate. The command is a derived review view and
must not create another authoritative artifact or approval state. For internal
and mixed audiences, apply the internal-expert voice check: enterprise operating
topics remain valid, while external-consultant address and viewpoint are rejected.

## 8. Stage 02 boundary

Visual style, image generation, SVG reconstruction and PPTX production remain outside this repository. Only `projects/<slug>/dist/final-script.md` crosses the boundary.
