# Remove Legacy Editable Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove every supported CyberPPT legacy editable-rebuild route, leaving `full_image_ppt` as the sole production delivery mode.

**Architecture:** Delete the rebuild runtime as a connected unit, then remove all public routing and scaffold contracts that can reach it. Replace legacy-positive tests with negative contract tests that prove active surfaces expose only the full-image production workflow. Preserve historical plans and specs as non-runtime records.

**Tech Stack:** Python 3.12, unittest/pytest, Make, npm package scripts, GitNexus, CyberPPT CLI.

## Global Constraints

- Do not modify existing user project artifacts under `projects/`.
- Preserve the current `full_image_ppt` `produce prepare -> assemble -> verify` route.
- Delete, rather than deprecate or hide, executable OCR/overlay/template-rebuild capabilities.
- Retain historical files in `docs/superpowers/{plans,specs}`.
- Before each production-symbol edit, run GitNexus upstream impact analysis; do not proceed without resolving HIGH/CRITICAL blast radius.

---

## File Structure

- Delete the legacy runtime rooted at `scripts/dual_image_overlay/template_rebuild.py` and `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`, plus their rebuild-only helpers.
- Modify `cyberppt/cli.py`, `cyberppt/commands/script_runner.py`, `Makefile`, `package.json`, and project initialization to remove public routes and legacy workspace directories.
- Modify active workflow documentation only: `README.md`, `SKILL.md`, `docs/repository-layout.md`, and `references/dual-image-editable-overlay.md`.
- Delete rebuild-only tests and fixtures; update shared CLI, initialization, and contract tests to assert absence of the removed surface.

### Task 1: Lock the public-surface removal contract

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_script_gate.py`
- Modify: `tests/test_skill_contract.py`
- Modify: `tests/test_final_script_pages.py`

**Interfaces:**
- Consumes: `python3 -m cyberppt --help`, `cyberppt.commands.script_runner.SCRIPT_ALIASES`, and `init_project.PROJECT_DIRS`.
- Produces: negative regression coverage that forbids `template-rebuild`, `--run-rebuild`, `--rebuild-arg`, legacy Stage 03/04 directories, and legacy workflow prose in active contracts.

- [ ] **Step 1: Write failing negative tests**

Add assertions with these exact expectations:

```python
self.assertNotIn("template-rebuild", SCRIPT_ALIASES)
self.assertNotIn("template-rebuild", subprocess.run(
    [sys.executable, "-m", "cyberppt", "--help"], text=True,
    capture_output=True, check=True
).stdout)
self.assertFalse((project / "workbench/stages/03-overlay").exists())
self.assertFalse((project / "workbench/stages/04-template-rebuild").exists())
self.assertNotIn("Legacy/Advanced: editable rebuild", SKILL.read_text(encoding="utf-8-sig"))
```

- [ ] **Step 2: Run the focused tests to verify RED**

Run: `python3 -m pytest tests/test_cli.py tests/test_script_gate.py tests/test_skill_contract.py tests/test_final_script_pages.py -q`

Expected: failures that demonstrate the legacy alias, scaffold directories, parser compatibility options, or active contract text still exist.

- [ ] **Step 3: Commit the failing-test checkpoint only if the repository policy permits red commits**

Do not commit a failing worktree by default. Keep the focused failing output in the task record and continue directly to Task 2.

### Task 2: Delete the executable runtime and public routes

**Files:**
- Delete: `scripts/dual_image_overlay/template_rebuild.py`
- Delete: `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`
- Delete: `scripts/dual_image_overlay/rebuild_modes.py`
- Delete: `scripts/dual_image_overlay/rebuild_engine/ocr_quality_gate.py`
- Delete: `scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py`
- Modify: `cyberppt/cli.py`
- Modify: `cyberppt/commands/script_runner.py`
- Modify: `cyberppt/commands/init_project.py`
- Modify: `cyberppt/commands/final_script_pages.py`
- Modify: `Makefile`
- Modify: `package.json`

**Interfaces:**
- Removes: the `template-rebuild` CLI command and script alias; all calls to `run_vendor_rebuild`, `rebuild_from_manifest`, and `resolve_rebuild_mode`.
- Preserves: `image-ppt`, `produce prepare`, `produce assemble`, and `produce verify`.

- [ ] **Step 1: Run upstream impact analysis immediately before edits**

Run:

```text
impact({target: "rebuild_from_manifest", direction: "upstream"})
impact({target: "run_vendor_rebuild", direction: "upstream"})
impact({target: "resolve_rebuild_mode", direction: "upstream"})
```

Expected: all direct callers are inside the files being deleted or edited in this task. If new HIGH/CRITICAL callers appear outside this list, expand the task before deletion.

- [ ] **Step 2: Delete the runtime as one connected component**

Remove the five files listed above. Do not replace them with a compatibility shim, an unsupported-command handler, or dynamically imported fallback code.

- [ ] **Step 3: Remove public command and scaffold references**

Apply these exact removals:

```python
# cyberppt/commands/script_runner.py
# remove the "template-rebuild" SCRIPT_ALIASES entry
# remove "template-rebuild" from CLI_RUNNABLE_ALIASES

# cyberppt/cli.py
# remove the rebuild command handler and parser registration
# remove --run-rebuild and --rebuild-arg compatibility parser arguments

# cyberppt/commands/init_project.py
# remove workbench/stages/03-overlay and workbench/stages/04-template-rebuild
# remove their stage metadata and legacy README copy

# cyberppt/commands/final_script_pages.py
# remove unused template-rebuild artifact/error helper functions and references

# Makefile/package.json
# remove template-rebuild targets/scripts and their phony declarations
```

Keep explicit Stage 02 guards that state the mainline does not invoke OCR or template rebuild only where they still describe current behavior; remove any references that advertise a selectable legacy route.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run: `python3 -m pytest tests/test_cli.py tests/test_script_gate.py tests/test_final_script_pages.py -q`

Expected: PASS. `python3 -m cyberppt --help` lists no rebuild command and `python3 -m cyberppt image-ppt --help` still exits 0.

- [ ] **Step 5: Commit the runtime and public-route removal**

```bash
git add scripts/dual_image_overlay cyberppt/cli.py cyberppt/commands/script_runner.py cyberppt/commands/init_project.py cyberppt/commands/final_script_pages.py Makefile package.json tests/test_cli.py tests/test_script_gate.py tests/test_final_script_pages.py
git commit -m "refactor: remove legacy rebuild runtime"
```

### Task 3: Remove legacy tests, fixtures, and active workflow contracts

**Files:**
- Delete: `tests/test_dual_image_overlay_template_rebuild.py`
- Delete: `tests/test_high_fidelity_text_extractor_integration.py`
- Delete: `tests/test_scene_graph_workflow.py`
- Delete: `tests/test_dual_image_rebuild_engine_assets.py`
- Delete: `tests/run_synthetic_legacy_e2e.py`
- Delete: `tests/fixtures/ocr_golden/`
- Delete: `references/dual-image-editable-overlay.md`
- Modify: `README.md`
- Modify: `SKILL.md`
- Modify: `docs/repository-layout.md`
- Modify: `tests/test_skill_contract.py`
- Modify: any remaining shared test importing a deleted runtime module.

**Interfaces:**
- Removes: the editable-rebuild dual gates, OCR forensic fixture contract, and dual-image rebuild reference.
- Produces: active documentation that describes a single `full_image_ppt` production route and truthful body-content editability.

- [ ] **Step 1: Write a failing documentation-surface test**

Add a test that reads active documentation and asserts:

```python
for text in (README.read_text(encoding="utf-8-sig"), SKILL.read_text(encoding="utf-8-sig"), LAYOUT.read_text(encoding="utf-8")):
    self.assertNotIn("Legacy/Advanced", text)
    self.assertNotIn("editable rebuild", text)
    self.assertNotIn("template-rebuild", text)
```

It must separately assert `full_image_ppt` and `body_content_editable=false` remain in the active contract.

- [ ] **Step 2: Run the documentation contract test to verify RED**

Run: `python3 -m pytest tests/test_skill_contract.py -q`

Expected: FAIL because active documents still describe the deleted path.

- [ ] **Step 3: Delete stale tests/assets and rewrite only active documents**

Delete all listed legacy-only tests, fixture directory, and reference. Remove the complete `Legacy/Advanced: editable rebuild` section from `SKILL.md`, associated table rows, acceptance gates, and user guidance. Rewrite README/layout text so the only delivery statement is the full-image workflow; retain the truthful declaration that body-region content is generally non-editable. Do not edit historical `docs/superpowers/plans/` or `docs/superpowers/specs/` files.

- [ ] **Step 4: Run the documentation and import regression suite to verify GREEN**

Run:

```bash
python3 -m pytest tests/test_skill_contract.py tests/test_cli.py tests/test_script_gate.py -q
python3 -m compileall -q cyberppt scripts
```

Expected: PASS with no import error for deleted rebuild modules.

- [ ] **Step 5: Commit contract cleanup**

```bash
git add README.md SKILL.md docs/repository-layout.md references tests
git commit -m "docs: remove legacy rebuild contract"
```

### Task 4: Prove repository closure and full-image continuity

**Files:**
- Modify: `docs/superpowers/plans/2026-07-11-remove-legacy-rebuild.md` (check off completed steps only)

**Interfaces:**
- Consumes: the cleaned public surface, active documents, and focused tests.
- Produces: evidence that no executable or documented legacy rebuild route remains.

- [ ] **Step 1: Search active repository surfaces**

Run:

```bash
rg -n -i "template_rebuild|template-rebuild|editable_overlay_rebuild|dual_image_editable_overlay|legacy/advanced: editable rebuild" \
  cyberppt scripts Makefile package.json README.md SKILL.md docs/repository-layout.md references tests
```

Expected: no matches. Historical `docs/superpowers/{plans,specs}` are intentionally excluded.

- [ ] **Step 2: Smoke-test the surviving production route**

Run:

```bash
python3 -m cyberppt --help
python3 -m cyberppt image-ppt --help
python3 -m cyberppt produce --help
```

Expected: all commands exit 0 and none advertises editable rebuild or template rebuild.

- [ ] **Step 3: Run the focused final suite**

Run:

```bash
python3 -m pytest tests/test_cli.py tests/test_script_gate.py tests/test_skill_contract.py tests/test_final_script_pages.py -q
```

Expected: PASS.

- [ ] **Step 4: Run GitNexus change detection before final commit**

Run: `detect_changes({scope: "all"})`

Expected: changed symbols and affected flows are limited to the legacy rebuild removal and current documentation/contracts. Investigate any full-image assembly flow regression before committing.

- [ ] **Step 5: Commit closure evidence**

```bash
git add docs/superpowers/plans/2026-07-11-remove-legacy-rebuild.md
git commit -m "docs: record legacy rebuild removal verification"
```

## Self-Review

- Spec coverage: Tasks 1-2 remove routes/runtime/scaffold; Task 3 removes tests, fixtures, and active documentation; Task 4 verifies source closure and the surviving mainline. Existing project artifacts are excluded.
- Placeholder scan: no unfinished markers or implicit implementation steps remain.
- Type consistency: the plan only removes existing public names; no replacement API is introduced.
