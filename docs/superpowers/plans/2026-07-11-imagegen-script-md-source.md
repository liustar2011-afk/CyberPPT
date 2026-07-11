# Imagegen Script MD Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Stage 02 generate a reviewable `imagegen_script.md` and compile `page_image_pairs.json` from that MD so users can inspect and control image generation prompts.

**Architecture:** Keep `page_image_pairs.json` as the machine manifest, but make `imagegen_script.md` the human-editable source immediately upstream of it. `final-script-pages` will expose both artifacts, and tests will assert that manifest prompts come from the MD file.

**Tech Stack:** Python standard library, CyberPPT CLI, existing `deliverable_prompt.parse_page_blocks` and `compile_pages`.

## Global Constraints

- Do not change the existing `page_image_pairs.json` schema in a breaking way.
- Keep Stage 02 full-image-only behavior.
- The generated MD must live beside `page_image_pairs.json` under the page-range output directory.
- JSON manifests must record the MD path and hash for review traceability.

---

### Task 1: Generate MD Before Manifest

**Files:**
- Modify: `scripts/dual_image_overlay/cyberppt_pair_manifest.py`
- Test: `tests/test_dual_image_overlay_pair_manifest.py`

**Interfaces:**
- Consumes: `compile_pages(script, page_numbers, style_lock_path=style_lock)`
- Produces: `imagegen_script.md`, `manifest["imagegen_script"]`, `manifest["imagegen_script_sha256"]`

- [ ] Write a test that `main()` creates `imagegen_script.md`, manifest `source_script` points to it, and `full.prompt` equals the page text parsed from the MD.
- [ ] Implement helpers to write `imagegen_script.md` and hash it.
- [ ] In `build_manifest`, write the MD first, parse page blocks from the MD, then build `pairs` from parsed MD content.
- [ ] Run `python3 -m pytest tests/test_dual_image_overlay_pair_manifest.py -q`.

### Task 2: Expose MD In Final Script Pages

**Files:**
- Modify: `cyberppt/commands/final_script_pages.py`
- Test: `tests/test_final_script_pages.py`

**Interfaces:**
- Consumes: `build_manifest(...) -> (manifest, manifest_path, compiled_script, page_numbers)`
- Produces: `summary["artifacts"]["imagegen_script"]`

- [ ] Add a test assertion that `run_final_script_pages()` returns an `imagegen_script` artifact and ledger records it.
- [ ] Add `imagegen_script` to artifacts while preserving `compiled_deliverable_prompt` for compatibility.
- [ ] Update next-step text to direct users to review or edit `imagegen_script.md` before image generation.
- [ ] Run `python3 -m pytest tests/test_final_script_pages.py -q`.

### Task 3: Regenerate Current Project Artifacts

**Files:**
- Modify/create: `projects/power-supply-demand-forecast-0709/workbench/stages/02-blueprint-dual-image/pages_001_019/imagegen_script.md`
- Modify: corresponding run summary and manifest files.

**Interfaces:**
- Consumes: existing project approvals and `blueprint_input.md`
- Produces: refreshed Stage 02 artifacts with MD as source.

- [ ] Run `python3 -m cyberppt final-script-pages /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709 --script /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709/workbench/stages/02-blueprint-dual-image/blueprint_input.md --pages 1-19 --style-lock /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709/workbench/locks/visual_style_lock.json`.
- [ ] Verify `page_image_pairs.json` references `imagegen_script.md`.
- [ ] Run focused tests and GitNexus `detect_changes` before reporting.
