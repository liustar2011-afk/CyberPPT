# ImageGen Prompt Processing Quality Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate prompt-processing rules from page content, revalidate the human-edited `imagegen_script.md`, and add a hard final-image text QA gate before a PPTX can be promoted for delivery.

**Architecture:** Keep `imagegen_script.md` as the human-editable source immediately upstream of image generation. Move the compiler's forbidden-content policy into a reusable machine-readable module; the compiler applies that policy when constructing prompts, while the model receives only the necessary page content and composition controls. Add a generated-image OCR report that checks observed text against allowed page content and blocks `produce verify` when forbidden process text or unexplained visible text is found.

**Tech Stack:** Python standard library, existing CyberPPT CLI, existing Codex vision text transport, JSON/Markdown artifacts, pytest/unittest.

## Global Constraints

- Do not put the operator's processing requirements into page-visible content or business script text.
- Keep `imagegen_script.md` human-editable and treat it as the source for `page_image_pairs.json` and `full.prompt`.
- Revalidate an edited `imagegen_script.md` before it can be consumed by the image-generation manifest.
- Keep the Stage 02 `full_image_ppt` contract: full content-region image, template chrome generated separately, no OCR/overlay/template-rebuild in the default path.
- Do not add a new runtime dependency; use the existing Codex vision transport for OCR text extraction and deterministic Python checks for policy enforcement.
- An image-text QA failure must prevent `deliverable_ready`; it must not be downgraded to a warning.
- Preserve existing manifest fields and add new fields compatibly.
- Every task ends with focused tests, `git diff --check`, and a small commit containing only that task's files.

---

## Current Contracts To Preserve

1. `scripts/dual_image_overlay/deliverable_prompt.py` cleans source-script lines through `visible_deliverable_lines()` and `layout_density_directives()`, then renders a model-facing prompt with `【页面类型】`, `【内容锁定】`, `【构图指令】`, and `【结构密度】` sections.
2. `scripts/dual_image_overlay/cyberppt_pair_manifest.py` writes `imagegen_script.md`, parses it, and sets `pair["full"]["prompt"]` from the parsed page text.
3. `cyberppt/commands/final_script_pages.py` exposes the MD path as both `compiled_deliverable_prompt` and `imagegen_script` for compatibility.
4. `cyberppt/commands/produce.py` is the legal Stage 02 production state machine and must consume the new QA artifact before promotion.
5. `scripts/validate_pptx.py` validates PPTX structure and QA declarations, but does not itself prove that text baked into a full PNG is free of process instructions. The new image-text report must close that gap.

## Artifact Contract

Each Stage 02 page-range output will contain:

```text
imagegen_script.md                         # human-editable prompt source
page_image_pairs.json                      # manifest compiled from the MD
image_text_qa/                              # generated-image text QA
  page_001.json
  page_002.json
  image_text_qa_summary.json
production_readiness.json                  # must depend on the QA summary
```

Each page QA report must use this shape:

```json
{
  "schema": "cyberppt.image_text_qa.v1",
  "page": 1,
  "image_path": "/absolute/path/page_001_full.png",
  "allowed_text_source": "/absolute/path/imagegen_script.md",
  "observed_text": ["资源保障", "风险管控"],
  "forbidden_matches": [],
  "unexpected_text": [],
  "status": "passed",
  "deliverable_allowed": true
}
```

`status` values are `passed`, `review_required`, or `failed`. `failed` is used for forbidden process/metadata text. `review_required` is used for OCR text that cannot be matched to the page's allowed content; `produce verify` must also block on `review_required` until a human resolves it.

---

### Task 1: Extract A Reusable Prompt-Processing Policy

**Files:**
- Create: `scripts/dual_image_overlay/prompt_policy.py`
- Modify: `scripts/dual_image_overlay/deliverable_prompt.py`
- Test: `tests/test_prompt_policy.py`
- Test: `tests/test_dual_image_overlay_deliverable_prompt.py`

**Interfaces:**
- Create `PromptPolicy` as an immutable dataclass with `schema`, `visible_text_source`, `forbidden_classes`, and `required_sections`.
- Create `classify_forbidden_text(text: str) -> tuple[str, ...]`.
- Create `validate_visible_text(lines: Iterable[str]) -> list[dict[str, str]]`.
- Keep `visible_deliverable_lines()`, `layout_density_directives()`, `compile_pages()`, and `assert_deliverable_prompt()` backward-compatible.

- [ ] **Step 1: Write failing tests**

```python
def test_processing_policy_classifies_process_and_metadata_text() -> None:
    assert "process_instruction" in classify_forbidden_text("本页说明：请将内容放入左侧")
    assert "placeholder" in classify_forbidden_text("待补充")
    assert "metadata" in classify_forbidden_text("target_language=zh-CN")
    assert classify_forbidden_text("全国用电量同比增长5.0%") == ()


def test_compiler_policy_is_not_rendered_as_page_content() -> None:
    page = parse_page_blocks("## 第1页：测试\n本页说明：仅用于构图\n真实业务内容\n")[1]
    assert visible_deliverable_lines(page) == ["真实业务内容"]
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
python3 -m pytest tests/test_prompt_policy.py tests/test_dual_image_overlay_deliverable_prompt.py -q
```

Expected: FAIL because the reusable policy module and classification function do not exist.

- [ ] **Step 3: Implement the policy module and connect the compiler**

Use one policy table for the following classes:

```python
FORBIDDEN_TEXT_CLASSES = {
    "process_instruction": (r"本页说明", r"生成要求", r"布局说明", r"构图说明", r"请将", r"请生成"),
    "review_note": (r"待补充", r"待核对", r"仅供参考", r"核对内容", r"审阅意见"),
    "placeholder": (r"占位", r"placeholder", r"示意图", r"TBD", r"TODO"),
    "metadata": (r"target_language", r"language_source", r"effective_language", r"source_unit", r"E\d+"),
    "debug": (r"debug", r"调试", r"trace_id", r"generation_id"),
}
```

The compiler must use this table to remove source-script process lines and to validate visible business lines. The control sections added by `render_prompt()` remain model-facing instructions and are not treated as page content.

- [ ] **Step 4: Run the focused tests and verify pass**

Run:

```bash
python3 -m pytest tests/test_prompt_policy.py tests/test_dual_image_overlay_deliverable_prompt.py -q
```

Expected: PASS, with existing deliverable-prompt tests unchanged except for assertions that the policy is applied.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/prompt_policy.py scripts/dual_image_overlay/deliverable_prompt.py tests/test_prompt_policy.py tests/test_dual_image_overlay_deliverable_prompt.py
git commit -m "feat: centralize image prompt processing policy"
```

### Task 2: Revalidate Human-Edited `imagegen_script.md`

**Files:**
- Modify: `scripts/dual_image_overlay/deliverable_prompt.py`
- Modify: `scripts/dual_image_overlay/cyberppt_pair_manifest.py`
- Test: `tests/test_dual_image_overlay_pair_manifest.py`
- Test: `tests/test_dual_image_overlay_deliverable_prompt.py`

**Interfaces:**
- Create `validate_imagegen_script(script_path: Path, pages: Iterable[int]) -> dict[str, object]`.
- `build_manifest()` must call this validator for both newly compiled MD and an already existing human-edited MD.
- Preserve the existing behavior that an edited MD is not rewritten before parsing.

- [ ] **Step 1: Write failing tests**

```python
def test_edited_imagegen_script_with_process_text_is_rejected(tmp_path: Path) -> None:
    script = tmp_path / "imagegen_script.md"
    script.write_text(
        "## 第1页：测试\n\n"
        "【内容锁定】\n- 真实业务内容\n\n"
        "【构图指令】\n本页说明：请放入左侧\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="process_instruction"):
        validate_imagegen_script(script, [1])
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_pair_manifest.py::test_edited_imagegen_script_with_process_text_is_rejected -q
```

Expected: FAIL because an edited MD currently bypasses prompt validation.

- [ ] **Step 3: Implement fail-closed MD validation**

Validation must:

1. Parse every requested page.
2. Require the four control sections generated by the compiler.
3. Run the policy against visible content and layout directives.
4. Reject forbidden content classes with page and line context.
5. Return a report containing the MD hash, pages checked, violations, and status.

`build_manifest()` must validate before creating `page_image_pairs.json`; an invalid MD must not produce a stageable manifest.

- [ ] **Step 4: Run focused and regression tests**

```bash
python3 -m pytest tests/test_dual_image_overlay_pair_manifest.py tests/test_dual_image_overlay_deliverable_prompt.py -q
```

Expected: PASS, including the existing test that manual MD edits are preserved.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/deliverable_prompt.py scripts/dual_image_overlay/cyberppt_pair_manifest.py tests/test_dual_image_overlay_pair_manifest.py tests/test_dual_image_overlay_deliverable_prompt.py
git commit -m "feat: validate edited imagegen scripts before manifest build"
```

### Task 3: Record Prompt Layers And Policy Metadata

**Files:**
- Modify: `scripts/dual_image_overlay/cyberppt_pair_manifest.py`
- Modify: `cyberppt/commands/final_script_pages.py`
- Modify: `docs/repository-layout.md`
- Test: `tests/test_dual_image_overlay_pair_manifest.py`
- Test: `tests/test_final_script_pages.py`

**Interfaces:**
- Add `manifest["prompt_contract"]` with `schema`, `visible_text_source`, `control_sections_non_visible`, `human_editable_source`, and `policy_schema`.
- Add `manifest["prompt_policy_report"]` with the validation report path and SHA-256.
- Preserve `source_script`, `imagegen_script`, `imagegen_script_sha256`, and `compiled_deliverable_prompt`.

- [ ] **Step 1: Write failing tests**

```python
def test_manifest_records_prompt_layer_contract(tmp_path: Path) -> None:
    script = tmp_path / "script.md"
    script.write_text("## 第1页：测试\n真实业务内容\n", encoding="utf-8")
    style_lock = write_project_style_lock(project=tmp_path / "project", style_id=5, source_script=script)
    output_dir = tmp_path / "output"
    manifest, _, _, _ = build_manifest(
        script=script,
        pages_raw="1",
        output_dir=output_dir,
        project_path=tmp_path / "project",
        style_lock=style_lock,
    )
    assert manifest["prompt_contract"]["visible_text_source"] == "content_lock"
    assert manifest["prompt_contract"]["control_sections_non_visible"] is True
    assert manifest["prompt_contract"]["human_editable_source"] is True
    assert manifest["prompt_policy_report"]["status"] == "passed"
```

- [ ] **Step 2: Run the test and verify failure**

```bash
python3 -m pytest tests/test_dual_image_overlay_pair_manifest.py::test_manifest_records_prompt_layer_contract -q
```

Expected: FAIL because the manifest has no prompt-layer contract.

- [ ] **Step 3: Implement compatible manifest metadata**

Write the policy report beside `imagegen_script.md`, include its hash in the manifest, and expose the same paths through `run_final_script_pages()` and its artifact ledger records. Do not put policy metadata into the page prompt body.

- [ ] **Step 4: Run focused tests**

```bash
python3 -m pytest tests/test_dual_image_overlay_pair_manifest.py tests/test_final_script_pages.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/cyberppt_pair_manifest.py cyberppt/commands/final_script_pages.py docs/repository-layout.md tests/test_dual_image_overlay_pair_manifest.py tests/test_final_script_pages.py
git commit -m "feat: record image prompt layer contract"
```

### Task 4: Add Deterministic Generated-Image Text QA

**Files:**
- Create: `scripts/dual_image_overlay/image_text_qa.py`
- Test: `tests/test_image_text_qa.py`
- Modify: `scripts/dual_image_overlay/rebuild_engine/codex_oauth_image.py` only if a small adapter is needed for the existing vision-text response function

**Interfaces:**
- Create `inspect_image_text(*, page: int, image_path: Path, allowed_lines: Iterable[str], ocr_text: str) -> dict[str, object]`.
- Create `run_image_text_qa(*, image_path: Path, allowed_lines: Iterable[str], page: int, model: str | None = None) -> dict[str, object]`.
- Create `write_image_text_qa(report: dict[str, object], output: Path) -> Path`.

- [ ] **Step 1: Write failing tests**

```python
def test_image_text_qa_fails_on_process_instruction() -> None:
    report = inspect_image_text(
        page=16,
        image_path=Path("page_016_full.png"),
        allowed_lines=["资源保障", "风险管控"],
        ocr_text="资源保障\n本页说明：请将风险放在右侧",
    )
    assert report["status"] == "failed"
    assert report["deliverable_allowed"] is False
    assert report["forbidden_matches"][0]["class"] == "process_instruction"


def test_image_text_qa_requires_review_for_unexpected_business_text() -> None:
    report = inspect_image_text(
        page=16,
        image_path=Path("page_016_full.png"),
        allowed_lines=["资源保障", "风险管控"],
        ocr_text="资源保障\n风险管控\n新增未经锁定的判断",
    )
    assert report["status"] == "review_required"
    assert report["deliverable_allowed"] is False
```

- [ ] **Step 2: Run the tests and verify failure**

```bash
python3 -m pytest tests/test_image_text_qa.py -q
```

Expected: FAIL because the image-text QA module does not exist.

- [ ] **Step 3: Implement OCR normalization and policy checks**

Normalize whitespace and punctuation for matching, preserve the raw OCR lines in the report, and apply the centralized policy to every observed line. Treat exact/near-exact matches to allowed content as allowed. Treat forbidden classes as `failed`; treat unmatched non-empty text as `review_required`. Do not silently delete unexpected OCR text from the report.

Use `run_codex_vision_text()` only to obtain OCR text. The vision model must not decide pass/fail; deterministic code owns the status.

- [ ] **Step 4: Run focused tests**

```bash
python3 -m pytest tests/test_image_text_qa.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/image_text_qa.py tests/test_image_text_qa.py scripts/dual_image_overlay/rebuild_engine/codex_oauth_image.py
git commit -m "feat: add deterministic generated image text QA"
```

### Task 5: Add Image-Text QA CLI And Stage 02 Artifact Ledger Records

**Files:**
- Modify: `cyberppt/cli.py`
- Modify: `cyberppt/commands/produce.py`
- Modify: `scripts/dual_image_overlay/image_text_qa.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_produce.py`

**Interfaces:**
- Add `cyberppt image-text-qa <project> --pages <range> [--model <model>] [--ocr-json <path>]`.
- The command writes `image_text_qa/page_<page>.json` and `image_text_qa_summary.json` under the page-range output directory.
- Add `assert_image_text_qa_ready(project: Path, pages_raw: str) -> Path` to the production command module.

- [ ] **Step 1: Write failing CLI and production-gate tests**

```python
def test_image_text_qa_command_writes_summary(tmp_path: Path) -> None:
    ocr_json = ROOT / "tests/fixtures/image_text_qa/clean_ocr.json"
    code = main(["image-text-qa", str(tmp_path), "--pages", "16", "--ocr-json", str(ocr_json)])
    assert code == 0
    assert (tmp_path / "workbench/stages/02-blueprint-dual-image/pages_016_016/image_text_qa_summary.json").is_file()


def test_produce_verify_blocks_without_current_image_text_qa(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="image-text QA"):
        assert_image_text_qa_ready(tmp_path, "16")
```

- [ ] **Step 2: Run the tests and verify failure**

```bash
python3 -m pytest tests/test_cli.py tests/test_produce.py -q
```

Expected: FAIL because the command and production gate do not exist.

- [ ] **Step 3: Implement the CLI and readiness gate**

The command must support deterministic fixture OCR through `--ocr-json` for tests and review, while the normal path obtains OCR from the existing vision-text transport. The summary must record page/image hashes, prompt-policy hash, OCR source, model, status, and resume command.

`produce verify` must require a current passed summary for every requested page before it can write `deliverable_ready`. A missing, stale, failed, or `review_required` summary must return a blocked result and must not copy the PPTX to `delivery/`.

- [ ] **Step 4: Run focused tests**

```bash
python3 -m pytest tests/test_cli.py tests/test_produce.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cyberppt/cli.py cyberppt/commands/produce.py scripts/dual_image_overlay/image_text_qa.py tests/test_cli.py tests/test_produce.py
git commit -m "feat: gate production on generated image text QA"
```

### Task 6: Add Reviewable QA Fixtures And Documentation

**Files:**
- Create: `tests/fixtures/image_text_qa/allowed_page_016.txt`
- Create: `tests/fixtures/image_text_qa/clean_ocr.json`
- Create: `tests/fixtures/image_text_qa/process_text_ocr.json`
- Create: `tests/fixtures/image_text_qa/unexpected_text_ocr.json`
- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `references/quality-assurance.md`
- Modify: `docs/repository-layout.md`
- Test: `tests/test_skill_contract.py`

**Interfaces:**
- Documentation must distinguish `imagegen_script.md` as the human-editable prompt source from the internal compiler policy.
- Documentation must state that prompt control sections are model-facing and never page-visible content.
- Documentation must state that image-text QA is a hard gate for `deliverable_ready`.

- [ ] **Step 1: Write failing contract tests**

```python
def test_docs_describe_prompt_layers_and_image_text_gate() -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "imagegen_script.md" in text
    assert "image-text QA" in text
    assert "不得进入页面可见文字" in text
```

- [ ] **Step 2: Run the test and verify failure**

```bash
python3 -m pytest tests/test_skill_contract.py -q
```

Expected: FAIL until the canonical workflow documents are updated.

- [ ] **Step 3: Update documentation and fixtures**

Document the exact sequence:

```text
approved content lock
  -> prompt compiler filters source material
  -> imagegen_script.md review/edit
  -> edited-MD validation
  -> page_image_pairs.json/full.prompt
  -> full image generation
  -> OCR image-text QA
  -> produce verify
```

Add the three OCR fixtures so the documented gate can be reproduced without a network call.

- [ ] **Step 4: Run documentation and prompt regression tests**

```bash
python3 -m pytest tests/test_skill_contract.py tests/test_prompt_policy.py tests/test_image_text_qa.py tests/test_dual_image_overlay_pair_manifest.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add SKILL.md README.md references/quality-assurance.md docs/repository-layout.md tests/test_skill_contract.py tests/fixtures/image_text_qa
git commit -m "docs: define prompt layers and image text delivery gate"
```

### Task 7: Shadow-Run The Current Project And Review The Gate

**Files:**
- Modify/create: `/Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709/workbench/stages/02-blueprint-dual-image/pages_001_019/imagegen_script.md`
- Create: `/Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709/workbench/stages/02-blueprint-dual-image/pages_001_019/image_text_qa/`
- Modify: the corresponding `page_image_pairs.json`, run summary, production readiness and artifact ledger records

**Interfaces:**
- Consumes: approved blueprint input, visual style lock, existing full images, and the human-reviewed `imagegen_script.md`.
- Produces: validated prompt policy report, per-page image-text QA reports, a passed summary only when all requested pages pass.

- [ ] **Step 1: Recompile the current project's prompt MD without generating images**

Run:

```bash
python3 -m cyberppt final-script-pages \
  /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709 \
  --script /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709/workbench/stages/02-blueprint-dual-image/blueprint_input.md \
  --pages 1-19 \
  --style-lock /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709/workbench/locks/visual_style_lock.json
```

- [ ] **Step 2: Review the MD before OCR/generation**

Check that each page contains business content and composition controls only; no evidence IDs, source notes, review notes, or process text may appear in visible-content lines. Pause here for user review before changing images.

- [ ] **Step 3: Run image-text QA against the existing full images**

Run:

```bash
python3 -m cyberppt image-text-qa \
  /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709 \
  --pages 1-19
```

Expected: each page report exists, the summary records image and MD hashes, and any process-text or unexpected-text finding is explicit rather than silently accepted.

- [ ] **Step 4: Run the full production readiness check**

Run:

```bash
python3 -m cyberppt produce verify \
  /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709 \
  --pages 1-19
```

Expected: the command either produces a `deliverable_ready` result with the image-text QA summary as a dependency or blocks with the exact pages and lines requiring review.

- [ ] **Step 5: Run final repository verification**

```bash
python3 -m pytest tests/test_prompt_policy.py tests/test_image_text_qa.py tests/test_dual_image_overlay_deliverable_prompt.py tests/test_dual_image_overlay_pair_manifest.py tests/test_final_script_pages.py tests/test_produce.py tests/test_skill_contract.py -q
git diff --check
node .gitnexus/run.cjs detect-changes --scope staged --repo CyberPPT --limit 100
```

Expected: all tests pass; only expected prompt-processing, QA, documentation, and current-project artifacts are changed; `produce verify` cannot pass without a current image-text QA summary.

- [ ] **Step 6: Commit the current-project review artifacts only after user confirmation**

```bash
git add projects/power-supply-demand-forecast-0709/workbench/stages/02-blueprint-dual-image/pages_001_019/imagegen_script.md projects/power-supply-demand-forecast-0709/workbench/stages/02-blueprint-dual-image/pages_001_019/image_text_qa projects/power-supply-demand-forecast-0709/workbench/stages/02-blueprint-dual-image/pages_001_019/page_image_pairs.json projects/power-supply-demand-forecast-0709/workbench/stages/02-blueprint-dual-image/pages_001_019/pages_001_019_final_script_pages_run.json
git commit -m "qa: verify current project image prompt and generated text"
```

## Verification Matrix

| Requirement | Enforced by | Blocking result |
|---|---|---|
| Processing rules do not become page content | `prompt_policy.py` + `visible_deliverable_lines()` | compiler removes or rejects the line |
| Human MD edits remain controllable | `imagegen_script.md` source contract | MD is never silently overwritten |
| Human MD edits cannot bypass policy | `validate_imagegen_script()` in `build_manifest()` | manifest build fails |
| Prompt and manifest remain traceable | manifest prompt contract + hashes | stale dependency blocks downstream use |
| Generated images contain no process text | `image_text_qa.py` OCR report | page `failed`, delivery blocked |
| Generated images contain only approved visible text | allowed-content comparison | page `review_required`, delivery blocked |
| Final PPTX is not promoted without QA | `produce verify` | no `deliverable_ready` and no delivery copy |

## Self-Review

- The plan keeps the editable MD source while adding mandatory validation after edits.
- The plan does not require the operator's explanatory requirement to be copied into page content; it turns that requirement into compiler policy and QA behavior.
- The plan covers source cleaning, prompt compilation, manifest consumption, image generation, OCR QA, production verification, documentation, fixtures, and current-project shadow review.
- The plan explicitly leaves the user review pause before any current-project image regeneration.
