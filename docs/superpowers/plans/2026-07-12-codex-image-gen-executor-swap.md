# Codex IMAGE_GEN Executor Swap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change only the CyberPPT main workflow's FULL-image execution method from the repository OAuth backend to Codex built-in `IMAGE_GEN`, while preserving every existing upstream prompt contract, project path, size behavior, run artifact, QA gate, and PPT assembly step.

**Architecture:** The existing Stage 02 workflow remains authoritative: `imagegen_script.md` compiles into `page_image_pairs.json`, and each content page keeps its current `full.prompt` and `full.path`. The active Codex agent replaces the OAuth call at the execution boundary: it sends the exact existing prompt to built-in `IMAGE_GEN` and places the returned bitmap at the existing `full.path`. Repository Python continues to consume the same file and metadata contracts; no new receive CLI, size normalizer, manifest field, or downstream branch is introduced.

**Tech Stack:** Codex built-in `IMAGE_GEN`, existing CyberPPT skill contract, Python contract tests, existing Stage 02 project artifacts.

## Global Constraints

- This is an executor-only change.
- Do not modify `cyberppt/commands/imagegen_run.py`, `cyberppt/cli.py`, `page_image_pairs.json` schema, image-text QA, blueprint approval, editable-text conversion, or PPT assembly.
- Do not add `--input-image`, `--force`, a receive command, or a second image directory.
- Do not add crop, resize, padding, or normalization behavior. Existing size handling remains unchanged and is outside this plan.
- `imagegen_script.md` remains the human-editable source; `page_image_pairs.json` remains the authority for eligible pages, exact prompts, and output paths.
- The Codex agent must send `full.prompt` without rewriting, shortening, expanding, or merging pages.
- The Codex agent must generate exactly one content page per `IMAGE_GEN` call.
- The returned image must be copied to the existing manifest-owned `full.path`; do not invent a new filename or destination.
- Template-only pages in `skipped_pages[]` remain excluded from image generation.
- The OAuth helper remains available for explicit legacy/debug flows but is not used by the main Codex-operated FULL-image workflow.
- Preserve all unrelated dirty-worktree changes and current project artifacts.

---

## File Structure

- Modify `SKILL.md`: replace the main workflow's OAuth/imagegen-run execution instruction with an explicit Codex built-in `IMAGE_GEN` executor contract.
- Modify `references/visual-system.md`: state that the main FULL-image bitmap must be produced by built-in `IMAGE_GEN` and written to the existing `full.path`.
- Modify `README.md`: describe the executor choice without changing commands, schemas, directories, size rules, or downstream stages.
- Modify `tests/test_skill_contract.py`: enforce that the main skill selects built-in `IMAGE_GEN`, uses manifest prompt/path verbatim, and does not route the main FULL-image stage through `run_codex_image`.
- Use one existing project for a read-only contract check and an isolated temporary project for the real one-page generation verification.

### Task 1: Lock the Executor-Only Boundary in Tests

**Files:**
- Modify: `tests/test_skill_contract.py`
- Read: `SKILL.md`
- Read: `references/visual-system.md`

**Interfaces:**
- Consumes: repository workflow documentation.
- Produces: tests that fail unless the main FULL-image workflow uses Codex built-in `IMAGE_GEN`, exact `full.prompt`, and exact `full.path`, with no new receive or size behavior.

- [ ] **Step 1: Write the failing executor-selection contract test**

Add to the existing `SkillContractTests` class in `tests/test_skill_contract.py`:

```python
def test_main_full_image_executor_is_codex_builtin_image_gen(self) -> None:
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    self.assertIn("Codex 内置 `IMAGE_GEN`", skill)
    self.assertIn("`full.prompt`", skill)
    self.assertIn("`full.path`", skill)
    self.assertIn("逐页", skill)
    self.assertNotIn("主流程调用 `run_codex_image`", skill)
```

- [ ] **Step 2: Write the failing no-scope-expansion contract test**

Add:

```python
def test_executor_swap_does_not_add_receive_or_size_contracts(self) -> None:
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    self.assertNotIn("--input-image", skill)
    self.assertNotIn("--force", skill)
    self.assertNotIn("居中留白", skill)
    self.assertNotIn("居中裁切", skill)
    self.assertNotIn("归一到 1680", skill)
```

- [ ] **Step 3: Run the focused tests and confirm RED**

Run:

```bash
python3 -m unittest \
  tests.test_skill_contract.SkillContractTests.test_main_full_image_executor_is_codex_builtin_image_gen \
  tests.test_skill_contract.SkillContractTests.test_executor_swap_does_not_add_receive_or_size_contracts -v
```

Expected: the executor-selection test fails because `SKILL.md` does not yet name built-in `IMAGE_GEN` as the main executor. If the scope test fails because old unrelated text exists, narrow the assertion to the Stage 02 generation section instead of deleting legitimate historical documentation.

- [ ] **Step 4: Confirm production Python is outside the change set**

Run:

```bash
git diff -- cyberppt/commands/imagegen_run.py cyberppt/cli.py cyberppt/commands/image_text_qa.py cyberppt/commands/produce.py
```

Expected: this task adds no new diff to those files. Pre-existing user changes may appear; record them and do not edit or stage them.

### Task 2: Switch the Main Workflow Instruction to Built-In IMAGE_GEN

**Files:**
- Modify: `SKILL.md:50-65`
- Modify: `references/visual-system.md:111-153`
- Modify: `README.md:54-65`
- Test: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: one approved `page_image_pairs.json` content pair with `page_number`, `full.prompt`, and `full.path`.
- Produces: one Codex built-in `IMAGE_GEN` call and one bitmap at that exact `full.path`.
- Leaves unchanged: image dimensions, file-content processing, run/QA artifacts, and downstream consumers.

- [ ] **Step 1: Replace only the executor instruction in `SKILL.md`**

Add this exact operational contract to the Stage 02 FULL-image generation section, adapting surrounding prose without changing other stages:

```markdown
### FULL 图生图执行器

主流程的 FULL 图由 Codex 内置 `IMAGE_GEN` 逐页生成，不调用仓库 OAuth
执行器 `run_codex_image`。

对 `page_image_pairs.json` 中每个 `pairs[]` 内容页：

1. 原样读取该页 `full.prompt`，不得改写、压缩、扩写或与其他页面合并。
2. 调用一次 Codex 内置 `IMAGE_GEN`；一次调用只生成一页。
3. 将返回的图片保存到该页既有的 `full.path`。
4. 图片落盘后继续执行仓库现有检查、运行记录、image-text QA、图片审批和 PPT 生产流程。

不得为此新增接收目录、CLI 参数、尺寸规则或旁路 manifest。`skipped_pages[]`
中的模板页不得调用 `IMAGE_GEN`。
```

- [ ] **Step 2: Align `references/visual-system.md` without changing quality rules**

In the existing ImageGen authenticity and output-record section, add:

```markdown
CyberPPT 主流程中的 FULL 图执行器是 Codex 内置 `IMAGE_GEN`。执行时必须消费
`page_image_pairs.json` 中当前页的 `full.prompt`，并把返回 bitmap 放到当前页的
`full.path`。执行器替换不得改变现有画布、尺寸、OCR、QA、审批或 PPT 组装规则。
```

Do not alter the existing content-lock, authenticity, blueprint-quality, text-accuracy, or editable-PPT requirements.

- [ ] **Step 3: Update `README.md` with one concise executor note**

Add under “ImageGen 提示词与交付文字 QA”:

```markdown
主流程逐页 FULL 图由 Codex 内置 `IMAGE_GEN` 执行：原样消费
`page_image_pairs.json` 的 `full.prompt`，并将结果写入同一条记录的 `full.path`。
这只替换生图执行器；现有尺寸处理、运行记录、image-text QA、审批和 PPT 组装不变。
```

- [ ] **Step 4: Run the focused contract tests and confirm GREEN**

Run:

```bash
python3 -m unittest \
  tests.test_skill_contract.SkillContractTests.test_main_full_image_executor_is_codex_builtin_image_gen \
  tests.test_skill_contract.SkillContractTests.test_executor_swap_does_not_add_receive_or_size_contracts -v
```

Expected: both PASS.

- [ ] **Step 5: Run the complete skill contract test module**

Run:

```bash
python3 -m unittest tests.test_skill_contract -v
```

Expected: PASS; existing script, gate, QA, and workflow wording contracts remain intact.

- [ ] **Step 6: Review the executor-only diff**

Run:

```bash
git diff -- SKILL.md references/visual-system.md README.md tests/test_skill_contract.py
```

Expected: the diff changes only executor selection and its contract tests. It must not introduce image resizing, new CLI arguments, new manifest fields, or new directories.

### Task 3: Verify Existing Project Prompt and Destination Contracts

**Files:**
- Read: `projects/power-supply-demand-forecast-0712/workbench/stages/02-blueprint-dual-image/pages_001_019/page_image_pairs.json`
- Read: existing FULL images in the same directory.
- No project files modified.

**Interfaces:**
- Consumes: a real project `pairs[]` entry.
- Produces: evidence that the existing prompt and destination are sufficient for built-in `IMAGE_GEN`; no new receive schema is needed.

- [ ] **Step 1: Inspect one current content-page pair**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path

manifest_path = Path(
    "projects/power-supply-demand-forecast-0712/"
    "workbench/stages/02-blueprint-dual-image/pages_001_019/page_image_pairs.json"
)
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
pair = next(item for item in manifest["pairs"] if item["page_number"] == 4)
assert isinstance(pair["full"]["prompt"], str) and pair["full"]["prompt"].strip()
assert Path(pair["full"]["path"]).parent == manifest_path.parent.resolve()
print(pair["page_number"])
print(pair["full"]["path"])
print(len(pair["full"]["prompt"]))
PY
```

Expected: page `4`, an existing Stage 02 `*_full.png` destination, and a non-zero prompt length.

- [ ] **Step 2: Confirm current downstream artifacts already consume that location**

Run:

```bash
rg -n "page_004_形势变化和工作要求_full.png" \
  projects/power-supply-demand-forecast-0712/workbench/stages/02-blueprint-dual-image \
  projects/power-supply-demand-forecast-0712/workbench/stages/05-qa-delivery
```

Expected: the same FULL-image path is referenced by Stage 02 editable-text/assembly artifacts and downstream QA/delivery records. Do not rewrite those records.

- [ ] **Step 3: Record the read-only finding in the implementation handoff**

The implementation report must state:

```text
Existing project evidence confirms that page_image_pairs.json already supplies both the exact
IMAGE_GEN input prompt and the project-owned FULL-image destination. No new receive path or
manifest schema was introduced.
```

### Task 4: Run One Real Built-In IMAGE_GEN Shadow Verification

**Files:**
- Temporary source/output only under `/tmp/cyberppt-imagegen-executor-shadow/`.
- Read: one approved `full.prompt` from the current project.
- Do not overwrite the current project's existing FULL image.

**Interfaces:**
- Consumes: page 4 `full.prompt` exactly as stored.
- Produces: one real built-in `IMAGE_GEN` bitmap in an isolated directory, plus recorded returned path and actual dimensions.

- [ ] **Step 1: Prepare the isolated shadow directory and exact prompt artifact**

Run:

```bash
rm -rf /tmp/cyberppt-imagegen-executor-shadow
mkdir -p /tmp/cyberppt-imagegen-executor-shadow
python3 - <<'PY'
import json
from pathlib import Path

manifest = json.loads(Path(
    "projects/power-supply-demand-forecast-0712/"
    "workbench/stages/02-blueprint-dual-image/pages_001_019/page_image_pairs.json"
).read_text(encoding="utf-8"))
pair = next(item for item in manifest["pairs"] if item["page_number"] == 4)
Path("/tmp/cyberppt-imagegen-executor-shadow/prompt.txt").write_text(
    pair["full"]["prompt"], encoding="utf-8"
)
PY
```

Expected: `/tmp/cyberppt-imagegen-executor-shadow/prompt.txt` contains the exact manifest prompt.

- [ ] **Step 2: Call Codex built-in IMAGE_GEN once with the exact prompt**

The implementing Codex agent must:

1. Read `/tmp/cyberppt-imagegen-executor-shadow/prompt.txt` verbatim.
2. Call built-in `IMAGE_GEN` once.
3. Copy the returned bitmap to `/tmp/cyberppt-imagegen-executor-shadow/page_004_full.png`.
4. Leave the original generated file in the Codex generated-images directory.

Expected: one image only; no OAuth call and no current-project overwrite.

- [ ] **Step 3: Measure and report the actual return without modifying it**

Run:

```bash
sips -g pixelWidth -g pixelHeight \
  /tmp/cyberppt-imagegen-executor-shadow/page_004_full.png
```

Expected: readable landscape dimensions are reported. Do not crop, resize, pad, or normalize the shadow result in this task.

- [ ] **Step 4: Confirm the executor boundary**

The implementation report must distinguish:

```text
Prompt source: existing page_image_pairs.json/full.prompt
Executor: Codex built-in IMAGE_GEN
Project destination contract: existing page_image_pairs.json/full.path
Size behavior: unchanged and outside this executor-swap task
Downstream behavior: unchanged
```

### Task 5: Regression and Change-Scope Verification

**Files:**
- No additional production files.

**Interfaces:**
- Consumes: Tasks 1-4 changes and evidence.
- Produces: verified executor-only diff suitable for user review.

- [ ] **Step 1: Run relevant workflow tests**

Run:

```bash
python3 -m unittest \
  tests.test_skill_contract \
  tests.test_final_script_pages \
  tests.test_imagegen_run \
  tests.test_produce -v
```

Expected: PASS. The existing Python imagegen-run, manifest, run-record, QA, and production contracts remain unchanged.

- [ ] **Step 2: Run the full test suite**

Run:

```bash
python3 -m pytest -q
```

Expected: PASS with no new failures.

- [ ] **Step 3: Verify no production Python or project artifacts changed**

Run:

```bash
git diff --name-only
```

Expected task-owned paths only:

```text
SKILL.md
README.md
references/visual-system.md
tests/test_skill_contract.py
```

Pre-existing user changes may also be listed; compare against the initial status and do not stage them. No file under `projects/`, `cyberppt/`, or `scripts/` may be newly changed by this task.

- [ ] **Step 4: Run diff hygiene**

Run:

```bash
git diff --check -- SKILL.md README.md references/visual-system.md tests/test_skill_contract.py
```

Expected: no whitespace errors.

- [ ] **Step 5: Run GitNexus change detection before any commit**

Run:

```text
detect_changes({scope: "compare", base_ref: "main", repo: "CyberPPT", worktree: "/Volumes/DOC/CyberPPT"})
```

Expected: no changed Python symbols or execution flows caused by this task; only workflow documentation and contract tests are affected. If production symbols appear, stop and remove the unintended scope expansion.

- [ ] **Step 6: Stage only executor-contract changes after user approval**

Run:

```bash
git add SKILL.md README.md references/visual-system.md tests/test_skill_contract.py
git diff --cached --check
git diff --cached --stat
```

Expected: no current project output, Python production file, generated image, or unrelated dirty-worktree file is staged.

## Plan Self-Review

- Spec coverage: the plan changes only the main Codex-operated FULL-image executor from OAuth to built-in `IMAGE_GEN`.
- Interface stability: prompt source, page selection, destination path, CLI, manifests, run artifacts, QA, approval, and PPT production remain unchanged.
- Size boundary: no crop, resize, padding, normalization, dimension contract, or size metadata is added or modified.
- Runtime truth: because built-in `IMAGE_GEN` is available only to the active Codex agent, the executor selection is implemented in the repository's durable Codex workflow contract rather than falsely pretending ordinary Python can call the tool.
- Scope check: optional OAuth legacy/debug and BACKGROUND/TEXT edit paths remain untouched.
- Completeness: every code/document change, test command, real-generation verification, and expected result is explicit.

