# Legacy Pipeline and Local History Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve CyberPPT's current source-faithful GPT Image 2 and editable-PPT production path while removing the obsolete dual-image/OCR/template-rebuild system, tracked runtime artifacts, and their objects from local Git history.

**Architecture:** First freeze the retained import closure with contract tests, then move each live capability into neutral `imagegen_pipeline`, `ppt_assembly`, and shared QA namespaces without compatibility shims. Only after the retained suite is green may the old tree and outputs be deleted; only after current-tree verification may local branches, worktrees, refs, reflogs, and historical objects be destroyed.

**Tech Stack:** Python 3, `unittest`, repository CLI (`python -m cyberppt`), Node/npm command metadata, Make, Git `filter-branch --index-filter`, Git worktrees.

## Global Constraints

- Do not write to `origin`: no push, force-push, remote branch deletion, or remote API mutation.
- Preserve the source-faithful content chain, nine-part GPT Image 2 artifact prompt, Style09/Style10, ImageGen handoff, image-to-editable SVG/PPT, external PPT title layers, and native template-page generation.
- Default writing behavior remains Chinese government/SOE formal style and source-faithful wording; cleanup must not weaken title/order/fact-strength preservation.
- Rename the formal Stage 02 directory to `workbench/stages/02-imagegen`; do not retain `02-blueprint-dual-image` compatibility.
- Do not retain error-only compatibility entry points for deleted commands or imports.
- Delete old code directly; do not create an archive or backup branch.
- Destructive history work is local-only and may start only after the current tree and retained tests pass.
- Final local state contains only `main` and the primary worktree.
- Working-tree size must decrease by at least 80 MB and Git pack size by at least 60 MB.

---

## File Structure

### New production boundaries

- `scripts/imagegen_pipeline/`: prompt construction, Style09/10, page manifest, ImageGen handoff, provider adapter, and their small shared helpers.
- `scripts/ppt_assembly/`: only native template-page generation and final PPT assembly code that is proven live after dependency tracing.
- `scripts/presentation_qa/`: render/text/geometry helpers shared by current editable-PPT and production-QA paths, if tracing proves they cannot remain within an existing neutral package.
- `tests/test_legacy_pipeline_absence.py`: repository-wide negative contract for removed namespaces, commands, stage names, and tracked runtime paths.
- `docs/cleanup/2026-08-15-legacy-pipeline-cleanup-report.md`: metadata-only before/after paths, sizes, verification commands, and irreversible local operations.

### Existing files that must be updated

- `cyberppt/commands/{run_autonomous,blueprint_gate,production_qa,final_script_pages,semantic_intent_audit,prepare_imagegen_send,produce,script_runner}.py`
- `cyberppt/{page_artifact_spec,image_text_gate}.py`
- `scripts/{body_blueprint_prompt,speaker_notes}.py`
- `scripts/image_to_editable_svg/orchestrator.py`
- `scripts/image_to_pptx_runtime/stage02_adapter.py`
- `.agents/skills/cyberppt-handoff/**` only where the formal stage path or retained command contract is declared.
- `Makefile`, `package.json`, `.gitignore`, and retained tests importing migrated modules.

### Trees to remove after migration

- `scripts/dual_image_overlay/`
- Tests whose sole subject is dual/triple image overlay, OCR refill/alignment, scene-graph reverse engineering, source capture, template rebuild, or compatibility aliases.
- `image2pptx_runs/`, tracked runtime content below `tmp/`, `tmp_image_entry_scan.txt`, and `prompts/attempts/`.

---

### Task 1: Freeze the Retained Boundary and Baseline Metrics

**Files:**
- Create: `tests/test_legacy_pipeline_absence.py`
- Create: `docs/cleanup/2026-08-15-legacy-pipeline-cleanup-report.md`
- Create: `/tmp/cyberppt-legacy-cleanup-paths.txt` (untracked execution input outside the repository)

**Interfaces:**
- Consumes: current tracked file list, Python imports, CLI command map, Git object list.
- Produces: an exact retained-module map and an exact historical deletion manifest used by Tasks 2-8.

- [ ] **Step 1: Record the pre-cleanup metrics and refs**

Run:

```bash
git status --short --branch
git branch --format='%(refname:short) %(objectname)'
git worktree list --porcelain
du -sk . .git image2pptx_runs tmp scripts/dual_image_overlay 2>/dev/null
git count-objects -vH
git ls-files image2pptx_runs tmp prompts/attempts tmp_image_entry_scan.txt scripts/dual_image_overlay > /tmp/cyberppt-legacy-cleanup-paths.txt
git verify-pack -v .git/objects/pack/*.idx | sort -k3nr | head -50
```

Expected: report contains the starting branch/worktree set, tracked-path counts, working-tree size, pack size, and largest objects; no command changes repository state.

- [ ] **Step 2: Add a failing negative contract**

Create tests that scan production sources and command registries:

```python
class LegacyPipelineAbsenceTest(unittest.TestCase):
    def test_production_sources_do_not_reference_legacy_namespace(self):
        offenders = scan_text(PRODUCTION_ROOTS, "scripts.dual_image_overlay")
        self.assertEqual([], offenders)

    def test_deleted_commands_are_not_registered(self):
        self.assertTrue({"source-capture", "template-rebuild", "image-ppt"}.isdisjoint(SCRIPT_MAP))

    def test_formal_stage_uses_imagegen_name(self):
        offenders = scan_text(PRODUCTION_ROOTS, "02-blueprint-dual-image")
        self.assertEqual([], offenders)
```

- [ ] **Step 3: Run the contract and capture the expected failure**

Run: `python -m unittest tests.test_legacy_pipeline_absence -v`

Expected: FAIL listing current legacy imports, commands, and Stage 02 references.

- [ ] **Step 4: Classify every legacy module by transitive production use**

Run:

```bash
rg -n '^(from|import) scripts\.dual_image_overlay|from scripts\.dual_image_overlay' cyberppt scripts --glob '*.py'
rg -n '^(from|import) scripts\.dual_image_overlay|from scripts\.dual_image_overlay' scripts/dual_image_overlay --glob '*.py'
rg -n 'dual_image_overlay|02-blueprint-dual-image|04-template-rebuild' .agents cyberppt scripts Makefile package.json --glob '!scripts/dual_image_overlay/**'
```

Record in the cleanup report a table with columns `old path`, `decision (move/delete)`, `new path`, and `live consumer`. The move set must equal the transitive closure of live consumers; anything not in that closure is deleted.

- [ ] **Step 5: Commit the boundary tests and initial report**

```bash
git add tests/test_legacy_pipeline_absence.py docs/cleanup/2026-08-15-legacy-pipeline-cleanup-report.md
git commit -m "test: freeze legacy pipeline cleanup boundary"
```

### Task 2: Move the Live GPT Image 2 Pipeline

**Files:**
- Create: `scripts/imagegen_pipeline/__init__.py`
- Move: retained prompt, Style, manifest, handoff, readiness, and provider modules from `scripts/dual_image_overlay/` into `scripts/imagegen_pipeline/`
- Modify: `cyberppt/commands/{run_autonomous,blueprint_gate,final_script_pages,semantic_intent_audit,prepare_imagegen_send}.py`
- Modify: `cyberppt/{page_artifact_spec,image_text_gate}.py`
- Modify: `scripts/{body_blueprint_prompt,speaker_notes}.py`
- Modify: retained prompt/Style/ImageGen tests

**Interfaces:**
- Consumes: signatures currently exported by `artifact_prompt`, `deliverable_prompt`, `imagegen_handoff`, `prompt_compiler`, `prompt_diagnostics`, `prompt_send_enrich`, `production_readiness`, `style_library`, `style09_adapter`, page manifest, and provider adapter.
- Produces: the same public functions under `scripts.imagegen_pipeline.*`; no module forwards imports from the old namespace.

- [ ] **Step 1: Change retained tests to the new namespace before moving code**

Representative import change:

```python
from scripts.imagegen_pipeline.artifact_prompt import SECTION_HEADINGS, render_artifact_prompt
from scripts.imagegen_pipeline.imagegen_handoff import compile_page_prompt
from scripts.imagegen_pipeline.style_library import write_project_style_lock
```

Apply this to retained tests for artifact prompts, deliverable prompts, Style09/10, prompt diagnostics, prompt enrichment, semantic intent, production readiness, speaker notes, body blueprint prompts, and final-script pages.

- [ ] **Step 2: Run the migrated tests to verify they fail on missing package**

Run:

```bash
python -m unittest tests.test_artifact_prompt tests.test_source_faithful_artifact_chain tests.test_extended_style_9 tests.test_extended_style_10 tests.test_prompt_send_enrich tests.test_imagegen_prompt_diagnostics tests.test_final_script_pages tests.test_speaker_notes tests.test_body_blueprint_prompt -v
```

Expected: ERROR with `ModuleNotFoundError: scripts.imagegen_pipeline`.

- [ ] **Step 3: Move the exact retained dependency closure**

Use `git mv` for every `move` row from Task 1, preserving package-relative resources such as `style_presets/*.json`. Rewrite all internal imports to `scripts.imagegen_pipeline.*`; place `codex_oauth_image.py`, `config.py`, and `console_encoding.py` under `scripts/imagegen_pipeline/providers/` and update callers accordingly.

The initial expected core set is:

```text
artifact_prompt.py
deliverable_prompt.py
imagegen_handoff.py
prompt_compiler.py
prompt_diagnostics.py
prompt_send_enrich.py
production_readiness.py
style_library.py
style09_adapter.py
style_presets/
page_manifest.py
providers/codex_oauth_image.py
providers/config.py
providers/console_encoding.py
```

Add only dependencies proven by the closure (for example creative-brief/page-semantics/script parsing/atomic-write helpers); do not copy implementations.

- [ ] **Step 4: Switch all production consumers to the new package**

Run after edits:

```bash
rg -n 'scripts\.dual_image_overlay' cyberppt scripts --glob '!scripts/dual_image_overlay/**'
python -m compileall -q cyberppt scripts/imagegen_pipeline scripts/body_blueprint_prompt.py scripts/speaker_notes.py
```

Expected: `rg` returns no matches outside the legacy tree and compileall exits 0.

- [ ] **Step 5: Run the retained prompt and source-faithful suite**

Run:

```bash
python -m unittest tests.test_artifact_prompt tests.test_source_faithful_artifact_chain tests.test_extended_style_9 tests.test_extended_style_10 tests.test_prompt_send_enrich tests.test_imagegen_prompt_diagnostics tests.test_semantic_intent tests.test_final_script_pages tests.test_speaker_notes tests.test_body_blueprint_prompt -v
```

Expected: zero failures and zero errors.

- [ ] **Step 6: Commit the live ImageGen migration**

```bash
git add cyberppt scripts/imagegen_pipeline scripts/body_blueprint_prompt.py scripts/speaker_notes.py tests
git commit -m "refactor: move live imagegen pipeline out of legacy overlay"
```

### Task 3: Separate Current PPT Assembly and QA from Reconstruction Code

**Files:**
- Create as required by the Task 1 closure: `scripts/ppt_assembly/` and/or `scripts/presentation_qa/`
- Modify: `scripts/image_to_editable_svg/orchestrator.py`
- Modify: `scripts/image_to_pptx_runtime/stage02_adapter.py`
- Modify: `cyberppt/commands/{production_qa,produce}.py`
- Modify: `scripts/validate_pptx.py`
- Test: retained image-to-editable SVG/PPT, production-QA, and native template-page tests

**Interfaces:**
- Consumes: current image-to-editable SVG/PPT inputs and native template-page descriptors.
- Produces: current PPTX assembly and QA behavior without OCR refill, dual-image manifests, image-derived template reconstruction, or legacy mode detection.

- [ ] **Step 1: Write/adjust retained tests to import neutral assembly and QA modules**

The retained tests must assert behavior, not the old implementation path:

```python
def test_editable_svg_orchestrator_uses_native_svg_assembly():
    result = build_editable_deck(valid_page_fixture)
    self.assertTrue(result.output_pptx.exists())
    self.assertEqual([], result.text_mismatches)

def test_validate_pptx_has_no_dual_image_mode_branch():
    self.assertFalse(hasattr(validate_pptx, "is_dual_image_overlay_entry"))
```

- [ ] **Step 2: Run the targeted tests and verify the new boundary fails**

Run:

```bash
python -m unittest tests.test_image_to_editable_svg_orchestrator tests.test_image_to_editable_svg_contracts tests.test_image_to_pptx_runtime tests.test_production_qa tests.test_qa_render_page scripts.test_validate_pptx -v
```

Expected: failures identify old imports or the still-present dual-image validation branch.

- [ ] **Step 3: Extract only the live assembly/QA closure**

Move native SVG-to-PPT assembly, render, geometry, and text-content checks into neutral packages only when a current consumer requires them. Delete dual-image-specific branches while preserving the callable signatures used by `image_to_editable_svg`, `image_to_pptx_runtime`, and `production_qa`.

- [ ] **Step 4: Remove dual-image manifest handling from PPT validation**

Delete `is_dual_image_overlay_entry` and its warning downgrades from `scripts/validate_pptx.py`; replace its tests with general native/editable-PPT validation expectations.

- [ ] **Step 5: Run the retained editable-PPT and QA tests**

Run the command from Step 2.

Expected: zero failures and zero errors; environment-dependent Office rendering is skipped only through an explicit availability check already encoded in the test.

- [ ] **Step 6: Commit the assembly boundary**

```bash
git add scripts/ppt_assembly scripts/presentation_qa scripts/image_to_editable_svg scripts/image_to_pptx_runtime scripts/validate_pptx.py scripts/test_validate_pptx.py cyberppt/commands tests
git commit -m "refactor: isolate current ppt assembly from legacy rebuild"
```

If one neutral package is unnecessary, omit that path from `git add`; do not create empty abstractions.

### Task 4: Rename Stage 02 and Remove Compatibility Commands

**Files:**
- Modify: `cyberppt/commands/{run_autonomous,blueprint_gate,final_script_pages,produce,script_runner}.py`
- Modify: `.agents/skills/cyberppt-handoff/**`
- Modify: `Makefile`
- Modify: `package.json`
- Modify: retained CLI, autonomous-run, produce, final-script, and skill-contract tests

**Interfaces:**
- Consumes: existing Stage 02 prompt/image generation inputs.
- Produces: one formal path, `workbench/stages/02-imagegen`, and no registration for deleted commands.

- [ ] **Step 1: Change tests to require the new stage and absent commands**

```python
def test_stage02_path_is_imagegen(self):
    self.assertEqual(Path("workbench/stages/02-imagegen"), STAGE_ROOT)

def test_legacy_commands_are_unknown(self):
    for command in ("source-capture", "template-rebuild", "image-ppt"):
        completed = run_cli(command, "--help")
        self.assertNotEqual(0, completed.returncode)
```

- [ ] **Step 2: Run CLI/stage tests and capture expected failures**

Run:

```bash
python -m unittest tests.test_cli tests.test_script_runner tests.test_run_autonomous tests.test_produce tests.test_final_script_pages tests.test_skill_contract -v
```

Expected: failures show the old path and registered aliases.

- [ ] **Step 3: Rename every formal Stage 02 reference**

Replace `workbench/stages/02-blueprint-dual-image` with `workbench/stages/02-imagegen` in current production code, skills, fixtures, and retained tests. Remove `04-template-rebuild` output assumptions; route current final assembly to the neutral assembly location established in Task 3.

- [ ] **Step 4: Delete command registrations and build aliases**

Remove `source-capture`, `template-rebuild`, `render-dual-image-overlay`, and old `image-ppt` entries from `script_runner.py`, `Makefile`, and `package.json`. Do not replace them with stubs.

- [ ] **Step 5: Run CLI/stage tests and absence contract**

Run:

```bash
python -m unittest tests.test_cli tests.test_script_runner tests.test_run_autonomous tests.test_produce tests.test_final_script_pages tests.test_skill_contract tests.test_legacy_pipeline_absence -v
```

Expected: command and stage assertions pass; only the not-yet-deleted legacy-tree assertion may remain failing.

- [ ] **Step 6: Commit the formal Stage 02 contract**

```bash
git add .agents cyberppt Makefile package.json tests
git commit -m "refactor: make imagegen the only stage02 workflow"
```

### Task 5: Delete the Obsolete Pipeline and Its Tests

**Files:**
- Delete: remaining `scripts/dual_image_overlay/`
- Delete: tests solely covering dual/triple image, OCR overlay, scene graph/container reconstruction, source capture, template rebuild, and removed commands
- Modify: retained tests whose filenames mention the old system but verify moved prompt/Style/page-manifest behavior; rename them to `test_imagegen_*` where appropriate
- Modify: obsolete docs and configuration discovered by the absence scan

**Interfaces:**
- Consumes: green migrated packages from Tasks 2-4.
- Produces: no production or test reference to the old namespace or deleted workflow concepts.

- [ ] **Step 1: Generate the exact delete list and review every row**

Run:

```bash
git ls-files scripts/dual_image_overlay tests | while read -r path; do rg -l "${path##*/}" cyberppt scripts tests >/dev/null 2>&1 || true; done
rg -l 'dual_image_overlay|editable_overlay|template_rebuild|source-capture|scene_graph|ocr_text_locator' tests docs .agents cyberppt scripts Makefile package.json
```

Update the cleanup report so every deleted test names the deleted production capability it covered. Tests for the retained prompt, Style, ImageGen, editable-PPT, or native template-page behavior must be migrated rather than deleted.

- [ ] **Step 2: Delete the confirmed obsolete tree and tests**

Use `apply_patch` deletion hunks for source-controlled files. The resulting tree must not contain `scripts/dual_image_overlay/`.

- [ ] **Step 3: Run repository-wide legacy scans**

Run:

```bash
test ! -e scripts/dual_image_overlay
rg -n 'scripts\.dual_image_overlay|02-blueprint-dual-image|04-template-rebuild|render-dual-image-overlay|template-rebuild|source-capture' cyberppt scripts tests .agents Makefile package.json
```

Expected: the directory test succeeds and `rg` has no matches except the intentional forbidden-string literals in `tests/test_legacy_pipeline_absence.py` and cleanup documentation.

- [ ] **Step 4: Run the absence contract and compile check**

Run:

```bash
python -m unittest tests.test_legacy_pipeline_absence -v
python -m compileall -q cyberppt scripts
```

Expected: all tests pass and compileall exits 0.

- [ ] **Step 5: Commit legacy-code removal**

```bash
git add -A scripts tests docs .agents cyberppt Makefile package.json
git commit -m "refactor: remove obsolete overlay and template rebuild pipeline"
```

### Task 6: Remove Tracked Runtime Outputs and Prevent Recurrence

**Files:**
- Delete: `image2pptx_runs/`
- Delete: tracked runtime contents under `tmp/`
- Delete: `tmp_image_entry_scan.txt`
- Delete: `prompts/attempts/`
- Modify: `.gitignore`
- Modify: `docs/cleanup/2026-08-15-legacy-pipeline-cleanup-report.md`
- Test: `tests/test_legacy_pipeline_absence.py`

**Interfaces:**
- Consumes: exact tracked-output manifest from Task 1.
- Produces: a clean tracked tree and ignore rules for generated decks, renders, OCR/diff intermediates, caches, local dependencies, and temporary Office/PDF/image outputs.

- [ ] **Step 1: Extend the negative contract to tracked artifacts**

```python
def test_runtime_output_roots_are_not_tracked(self):
    tracked = set(git("ls-files").splitlines())
    forbidden = ("image2pptx_runs/", "tmp/", "prompts/attempts/")
    self.assertFalse([p for p in tracked if p == "tmp_image_entry_scan.txt" or p.startswith(forbidden)])
```

Permit only a specifically justified `tmp/.gitkeep`; prefer no tracked `tmp` entry.

- [ ] **Step 2: Run the artifact test and verify it fails**

Run: `python -m unittest tests.test_legacy_pipeline_absence.LegacyPipelineAbsenceTest.test_runtime_output_roots_are_not_tracked -v`

Expected: FAIL listing tracked runtime outputs.

- [ ] **Step 3: Delete the explicit tracked output paths**

Use `apply_patch` for small text artifacts and explicit, validated `git rm -r -- <path>` only for the user-authorized generated trees:

```bash
git rm -r -- image2pptx_runs prompts/attempts
git rm -r -- tmp
git rm -- tmp_image_entry_scan.txt
```

Skip an exact path only if `git ls-files --error-unmatch -- <path>` proves it is absent.

- [ ] **Step 4: Add precise ignore rules**

Add anchored rules for `/image2pptx_runs/`, `/tmp/`, `/prompts/attempts/`, local render/QA/OCR/diff directories, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `node_modules/`, and generated office/PDF/image files only in known output roots. Do not globally ignore legitimate source assets such as all `*.png`, `*.pdf`, or `*.pptx`.

- [ ] **Step 5: Verify ignored examples and tracked assets**

Run:

```bash
python -m unittest tests.test_legacy_pipeline_absence -v
git check-ignore -v image2pptx_runs/example/output.pptx tmp/example.png prompts/attempts/example.md
git ls-files '*.png' '*.pptx' '*.pdf' | sed -n '1,120p'
```

Expected: synthetic output paths are ignored; remaining tracked binary assets are listed in the report with a live product/test-fixture justification.

- [ ] **Step 6: Commit output cleanup**

```bash
git add -A .gitignore image2pptx_runs tmp prompts/attempts tmp_image_entry_scan.txt tests docs/cleanup
git commit -m "chore: remove tracked runtime outputs"
```

### Task 7: Verify and Integrate the Clean Current Tree

**Files:**
- Modify only if a retained current capability fails: the directly responsible production/test file
- Modify: `docs/cleanup/2026-08-15-legacy-pipeline-cleanup-report.md`

**Interfaces:**
- Consumes: Tasks 1-6.
- Produces: a green cleanup commit on local `main`, ready for irreversible branch/ref/history deletion.

- [ ] **Step 1: Run the focused current-mainline suite**

Run:

```bash
python -m unittest tests.test_source_faithful_artifact_chain tests.test_artifact_prompt tests.test_extended_style_9 tests.test_extended_style_10 tests.test_final_script_pages tests.test_prompt_send_enrich tests.test_semantic_intent tests.test_image_to_editable_svg_orchestrator tests.test_image_to_editable_svg_contracts tests.test_image_to_pptx_runtime tests.test_production_qa tests.test_skill_contract tests.test_legacy_pipeline_absence -v
```

Expected: zero failures and zero errors.

- [ ] **Step 2: Run the complete retained suite**

Run:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest scripts.test_validate_pptx -v
python -m compileall -q cyberppt scripts tests
```

Expected: zero failures and zero errors; explicitly supported environment skips are reported as skips.

- [ ] **Step 3: Verify repository contracts and current-tree size**

Run:

```bash
git status --short
git ls-files | rg '^(image2pptx_runs/|tmp/|prompts/attempts/|tmp_image_entry_scan\.txt$|scripts/dual_image_overlay/)'
du -sk . .git
git count-objects -vH
```

Expected: no forbidden tracked paths; only the cleanup report may be modified while recording results.

- [ ] **Step 4: Commit final verification metadata**

```bash
git add docs/cleanup/2026-08-15-legacy-pipeline-cleanup-report.md
git commit -m "docs: record legacy cleanup verification"
```

- [ ] **Step 5: Fast-forward the feature branch into local main**

Run:

```bash
git switch main
git merge --ff-only agent/legacy-pipeline-history-cleanup
git status --short --branch
```

Expected: local `main` points at the verified cleanup commit and the working tree is clean. Do not push.

### Task 8: Remove Other Local Worktrees and Branches

**Files:**
- Delete local worktree directory: `.worktrees/agent-gpt-image2-artifact-prompt`
- Delete local branches: `agent/gpt-image2-artifact-prompt`, `agent/source-faithful-government-defaults`, `agent/legacy-pipeline-history-cleanup`

**Interfaces:**
- Consumes: verified local `main` from Task 7.
- Produces: exactly one local branch (`main`) and one worktree before history rewriting.

- [ ] **Step 1: Resolve and display exact deletion targets**

Run:

```bash
git worktree list --porcelain
git branch --format='%(refname:short) %(objectname)'
git branch --merged main
```

Expected: the worktree and three branch names exactly match the authorized targets above; `agent/legacy-pipeline-history-cleanup` is merged into main.

- [ ] **Step 2: Remove the authorized secondary worktree**

Run:

```bash
git worktree remove --force .worktrees/agent-gpt-image2-artifact-prompt
git worktree prune
```

Expected: `git worktree list` shows only the primary worktree.

- [ ] **Step 3: Delete the authorized local branches**

Run:

```bash
git branch -D agent/gpt-image2-artifact-prompt
git branch -D agent/source-faithful-government-defaults
git branch -d agent/legacy-pipeline-history-cleanup
```

Expected: `git branch --format='%(refname:short)'` prints only `main`.

- [ ] **Step 4: Re-run the focused suite on main**

Run the focused command from Task 7 Step 1.

Expected: zero failures and zero errors.

### Task 9: Rewrite Local Main History and Garbage-Collect Removed Objects

**Files:**
- Rewrite: local `refs/heads/main` only through Git history filtering
- Delete locally: `refs/remotes/origin/*`, `refs/original/*`, reflogs, unreachable objects
- Modify locally: remove all `remote.origin.fetch` values while retaining `remote.origin.url`
- Modify: `docs/cleanup/2026-08-15-legacy-pipeline-cleanup-report.md` before the final history pass if the report needs final command metadata

**Interfaces:**
- Consumes: exact historical deletion paths from Task 1 plus the clean one-branch state from Task 8.
- Produces: a compact local-only `main`; the remote URL remains configured but no remote-tracking ref or automatic fetch refspec remains.

- [ ] **Step 1: Build and validate the historical pathspec**

Create an explicit shell-safe path list containing only user-authorized deleted paths, including:

```text
image2pptx_runs
tmp
tmp_image_entry_scan.txt
prompts/attempts
scripts/dual_image_overlay
```

Add individually confirmed obsolete generated-output paths from the cleanup report. Do not add retained source assets or broad globs.

Run:

```bash
git log --all --name-only --format= | sort -u > /tmp/cyberppt-history-paths.txt
while IFS= read -r path; do test -z "$path" || rg -Fx "$path" /tmp/cyberppt-history-paths.txt >/dev/null || exit 1; done < /tmp/cyberppt-legacy-cleanup-paths.txt
```

Expected: every deletion target existed in local history; the manifest contains no blank, root, wildcard, or parent-traversal target.

- [ ] **Step 2: Record remote state without writing to it**

Run:

```bash
git remote get-url origin
git for-each-ref --format='%(refname) %(objectname)' refs/remotes/origin
git config --get-all remote.origin.fetch
```

Copy the output into the cleanup report and commit the report before rewriting if it changed.

- [ ] **Step 3: Rewrite local main with an index filter**

Use the exact explicit path list, not a dynamically expanding glob:

```bash
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch --force \
  --index-filter 'git rm -r --cached --ignore-unmatch -- image2pptx_runs tmp tmp_image_entry_scan.txt prompts/attempts scripts/dual_image_overlay' \
  --prune-empty --tag-name-filter cat -- main
```

If Task 1 confirmed additional historical output roots, append each literal path to the same `git rm` command before execution. Do not include `-- --all` and do not name remote refs.

- [ ] **Step 4: Remove local refs that retain old objects**

Run:

```bash
git for-each-ref --format='delete %(refname)' refs/remotes/origin refs/original | git update-ref --stdin
git config --unset-all remote.origin.fetch || test $? -eq 5
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

Expected: remote URL still exists; remote-tracking refs, original refs, reflogs, and unreachable deleted objects do not.

- [ ] **Step 5: Verify rewritten history, refs, size, and remote non-mutation**

Run:

```bash
git branch --format='%(refname:short)'
git worktree list --porcelain
git for-each-ref refs/remotes/origin refs/original
git config --get remote.origin.url
git config --get-all remote.origin.fetch || true
git log --all --name-only --format= | rg '^(image2pptx_runs/|tmp/|prompts/attempts/|tmp_image_entry_scan\.txt$|scripts/dual_image_overlay/)'
git count-objects -vH
du -sk . .git
git fsck --full --no-reflogs
git status --short --branch
```

Expected: only `main`; one worktree; no forbidden historical path; no fetch refspec; origin URL retained; `git fsck` has no corrupt objects; working tree and pack reductions meet the 80 MB and 60 MB thresholds.

- [ ] **Step 6: Re-run current-tree verification after history rewrite**

Run:

```bash
python -m unittest tests.test_source_faithful_artifact_chain tests.test_artifact_prompt tests.test_extended_style_9 tests.test_extended_style_10 tests.test_final_script_pages tests.test_image_to_editable_svg_orchestrator tests.test_image_to_pptx_runtime tests.test_production_qa tests.test_skill_contract tests.test_legacy_pipeline_absence -v
python -m compileall -q cyberppt scripts tests
```

Expected: zero failures and zero errors. Do not amend or create a new commit solely to record post-GC numbers, because doing so would require another report/history pass; present the final metrics in the user handoff.

---

## Final Acceptance Checklist

- [ ] No production import or file path contains `scripts.dual_image_overlay`.
- [ ] No old dual-image, OCR overlay, template-rebuild, source-capture, or image-derived reconstruction command remains.
- [ ] Source-faithful government/SOE content contracts and nine-part artifact prompts pass.
- [ ] Style09/Style10, ImageGen handoff, editable SVG/PPT, production QA, and native template pages pass.
- [ ] Runtime outputs are untracked and precisely ignored.
- [ ] Retained test discovery has zero failures and zero errors.
- [ ] Local Git has only `main` and one worktree.
- [ ] Local history contains none of the deleted paths or large output objects.
- [ ] Working tree shrank by at least 80 MB; Git pack shrank by at least 60 MB.
- [ ] `origin` received no write; its URL remains, while local remote-tracking refs and fetch refspec are removed.
