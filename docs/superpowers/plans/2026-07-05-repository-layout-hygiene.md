# Repository Layout Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CyberPPT repository layout rules explicit and align low-risk scaffolding/ignore behavior with the existing project mechanism.

**Architecture:** Preserve the current CyberPPT workflow contract in `SKILL.md` and the dual-image runtime paths. Add a repository layout contract, align generated project directories with that contract, and clean ignored local caches without moving existing ledgers or absolute-path run artifacts.

**Tech Stack:** Python package/CLI, Makefile, Markdown workflow docs, gitignored local artifacts.

## Global Constraints

- `SKILL.md` remains the authoritative workflow contract.
- Do not split or relocate `scripts/dual_image_overlay/rebuild_engine/` or `vendor/ppt_master_slide_image_rebuild/`.
- Do not move existing `image2pptx_runs/` artifacts in this pass because many JSON ledgers contain absolute paths.
- Formal CyberPPT outputs must live in project workspaces and be registered in `workbench/artifact-ledger.json`.
- Root-level `images/` is a legacy scratch location, not a default output target.

---

### Task 1: Repository Layout Contract

**Files:**
- Create: `docs/repository-layout.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `SKILL.md` stage directory rules and `cyberppt init` project structure.
- Produces: A documented placement contract for code, references, vendor runtime, project workspaces, generated runs, and legacy scratch artifacts.

- [x] **Step 1: Add `docs/repository-layout.md`**

Create a concise layout contract that names each top-level directory, allowed contents, and disallowed contents.

- [x] **Step 2: Link the contract from `README.md`**

Add one short section near "本地工程入口" so users can find the layout contract before creating projects.

- [x] **Step 3: Check for stale root-output wording**

Run: `rg -n "root-level|根目录|images/|image2pptx_runs|repository-layout" README.md docs/repository-layout.md`

Expected: root `images/` is described only as legacy scratch; default output locations point at project workspaces.

### Task 2: Project Scaffold Alignment

**Files:**
- Modify: `cyberppt/commands/init_project.py`
- Modify: `.gitignore`
- Test: `tests/test_script_gate.py`

**Interfaces:**
- Consumes: `PROJECT_DIRS` and generated `manifest.yml` from `init_project.py`.
- Produces: New project workspaces with `source/`, `workbench/stages/`, `workbench/runs/`, `outputs/`, and `delivery/`.

- [x] **Step 1: Add explicit run/archive directories**

Extend `PROJECT_DIRS` with `workbench/runs`, `workbench/archive`, and `workbench/tmp`.

- [x] **Step 2: Add manifest directory mappings**

Add `runs`, `archive`, and `tmp` entries to the generated `manifest.yml`.

- [x] **Step 3: Update scaffold README wording**

State that ad hoc generated images and intermediate run attempts belong in `workbench/runs/` or `workbench/tmp/`, not repo-root `images/`.

- [x] **Step 4: Update ignore rules**

Ignore root-level generated workspaces such as `image2pptx_runs/` and root-level scratch `images/`, while preserving `assets/` sample media and icon assets.

- [x] **Step 5: Extend tests**

Update `tests/test_script_gate.py` to assert the new scaffold directories exist.

### Task 3: Ignored Cache Cleanup

**Files:**
- Remove ignored local cache directories only.

**Interfaces:**
- Consumes: `.gitignore` cache rules.
- Produces: A cleaner working tree without Python/pytest cache noise.

- [x] **Step 1: List ignored caches**

Run: `find . -name '__pycache__' -o -name '.pytest_cache' | sort`

- [x] **Step 2: Remove listed caches**

Run: `rm -rf .pytest_cache cyberppt/__pycache__ cyberppt/commands/__pycache__ scripts/__pycache__ scripts/dual_image_overlay/__pycache__ scripts/dual_image_overlay/rebuild_engine/__pycache__ scripts/dual_image_overlay/scene_graph/__pycache__ tests/__pycache__ vendor/ppt_master_slide_image_rebuild/scripts/__pycache__ vendor/ppt_master_slide_image_rebuild/scripts/svg_to_pptx/__pycache__`

- [x] **Step 3: Verify no cache directories remain**

Run: `find . -name '__pycache__' -o -name '.pytest_cache' | sort`

Expected: no output.

### Task 4: Verification

**Files:**
- No additional edits unless tests reveal a narrow issue.

**Interfaces:**
- Consumes: completed Tasks 1-3.
- Produces: evidence that CLI scaffold and documented workflow remain valid.

- [x] **Step 1: Run scaffold-focused tests**

Run: `python3 -m unittest tests.test_script_gate`

Expected: all tests pass.

- [x] **Step 2: Run broader test suite**

Run: `make test`

Expected: all tests pass, or report exact failures without hiding them.

- [x] **Step 3: Review git status**

Run: `git status --short`

Expected: only intentional docs, scaffold, ignore, and cache-removal changes appear.
