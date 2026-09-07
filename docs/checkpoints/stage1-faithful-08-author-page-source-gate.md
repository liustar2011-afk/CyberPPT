# Checkpoint — Faithful AUTHOR exact page-source gate

Date: 2026-09-07
Branch: `refactor/stage1-faithful-authoring`

Status: completed.

## Landed

- Faithful AUTHOR contract now requires exact per-page source resolution before drafting.
- Default `script` projects with `script/.cache/source-index.json` v2 must run `page-source` for each content page.
- Packets are written under `script/.cache/page-source/` as disposable `derived_runtime_context`.
- `status: rewrite_required` blocks page authoring until source refs/bindings are repaired.
- Targeted faithful edits and page-level rewrites regenerate the packet after source-boundary changes.
- `strict/legacy` uses the same packet when a compatible v2 index exists; otherwise it must use exact Source Truth/source-consumption bindings.
- Workflow router and local `AGENTS.md` both enforce the gate.

## Authority boundary

The authoritative content chain remains:

`source -> foundation -> deck_plan -> final_script`

Page Source Packet is evidence preparation only. It is not a fourth content authority and generating it does not execute AUTHOR.
