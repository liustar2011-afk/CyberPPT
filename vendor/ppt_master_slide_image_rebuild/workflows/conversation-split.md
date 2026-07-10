---
description: Multi-chat execution for slide-image-rebuild to reduce Agent token use without changing strict gates.
---

# Conversation Split — Slide Image Rebuild

> Disk artifacts are the single source of truth. Strict gates do not change across chats.
> Index: [`../SKILL.md`](../SKILL.md). Token plan: `docs/zh/slide-image-rebuild-strict-token-optimization.md` (ppt-master monorepo only; not present in this standalone checkout).

## Why split

One long chat accumulates SKILL text, layout JSON, SVG, validator stdout, and repeated reference images. Splitting by phase keeps each session focused while the project directory carries state forward.

## Recommended chats

| Chat | Phase | Agent does | Open with |
|------|-------|------------|-----------|
| **1** | A — Intake + Layout | init, manifest, extract, mapping, plan, **`--stage mapped --skip-export`** | Reference image + `projects/<name>/` |
| **2** | B — Executor | Build `svg_output/` from plan + overlay | **New chat.** Only: project path, `design_spec.md` / `svg_build_plan.md` pointers |
| **3** | C — Notes + QA | `notes/total.md`, local `run_slide_image_rebuild_strict.py` | **New chat.** Project path + prior `strict_run_summary.json` if repairing |

## Handoff payload (minimal)

Do not paste prior chat history. Pass:

```text
Project: projects/<name>
Phase: B | C
Manifest: slide_image_rebuild_manifest.json (rebuild_mode, export_mode)
Read: workflows/strict-path.md § Phase <B|C>
```

Phase C failure handoff add:

```text
Summary: exports/qa/strict_run_summary.json
Failed step: <failed_step_id>
Resume: <next_action.resume_command>
```

## Rules

| Rule | Requirement |
|------|-------------|
| Reference image | Attach **once** in Chat 2 (Phase B) only |
| Required reads | Per [`required-reads.md`](../references/required-reads.md) for current phase |
| QA | Chat 3: local strict runner; read `strict_run_summary.json` only |
| Repair | Same chat or new Chat 3 with summary — max 3 attempts per `failed_step_id` |
| Multi-page | Repeat B→C per page or batch SVG in Chat 2, single Chat 3 for deck export |

## Resume phrases

User may open a fresh chat with:

- `继续图转 projects/<name> Phase B` → Executor only
- `继续图转 projects/<name> Phase C` → notes + strict QA
- `继续修复 projects/<name> strict` → read `strict_run_summary.json`, apply `next_action`

Agent must read project artifacts before continuing; do not assume prior chat content.
