# Stage 02 双路径 PPT 组装 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use inline execution with the approved plan and run each listed verification step.

**Goal:** 在当前 Stage 02 生图和 Quick authoring SVG 路线上，提供模板正文区图片式 PPT 与模板正文区可编辑 PPT 两种输出。

**Architecture:** 新增一个中性的模板正文区组装模块，读取当前仓库 `assets/presentation-templates/cec-lightweight/`，将 2:1 图片或 2:1 authoring SVG 包装到 1280×720 模板页面；`stage02_adapter.py` 负责生产门禁和模式分流，`final_script_pages.py` 与 CLI 只传递 assembly mode，不复制 Stage 02 事实源。

**Tech Stack:** Python 3.12、现有 SVGQualityChecker、现有 native SVG/PPTX builder、OfficeCLI、仓库已有 pytest/unittest 测试。

## Global Constraints

- 保留现有 `image-to-editable-svg` production mode。
- 默认 assembly mode 为 `editable`，显式 `image` 生成图片式 PPT，`both` 同时生成两份。
- 正文图片和 authoring SVG 均必须保持 2:1；模板正文区固定为 1214×607。
- 不恢复 OCR、legacy overlay 或 `scripts/dual_image_overlay/`。
- 不覆盖当前工作区已有用户修改。

### Task 1: Add the template body assembly module

**Files:**
- Create: `scripts/image_to_pptx_runtime/template_assembly.py`
- Test: `tests/test_template_assembly.py`

**Interfaces:**
- `assemble_template_svg(source_svg, output_svg, title, subtitle, page_number, body_mode, body_path)` creates one 1280×720 wrapper SVG.
- `assemble_template_pptx(svg_files, output_path, notes)` calls the existing native exporter.
- `load_template_contract()` reads the current CEC lightweight brand rules.

- [ ] Write tests for the exact 2:1 body slot, image mode, editable SVG mode, template chrome, and page-number substitution.
- [ ] Implement brand rule loading and strict 2:1 validation.
- [ ] Implement image wrapper with native title and public chrome.
- [ ] Implement SVG wrapper with one uniform transform from source viewBox to `1214×607` at `33,89`.
- [ ] Reject non-2:1 source SVGs and unresolved template placeholders.
- [ ] Run `pytest -q tests/test_template_assembly.py`.

### Task 2: Add dual assembly modes to Stage 02 adapter

**Files:**
- Modify: `scripts/image_to_pptx_runtime/stage02_adapter.py`
- Test: `tests/test_image_to_pptx_runtime.py`

**Interfaces:**
- Extend `run_stage02_reconstruction(..., assembly_mode="editable")` with `image`, `editable`, and `both`.
- Return `artifacts.exported_pptx_by_mode` with explicit paths.

- [ ] Preserve current audited-pair and graphic-text-policy gates.
- [ ] Build the Quick authoring SVG once when `editable` or `both` is requested.
- [ ] Build the template image output from the audited `full.path` when `image` or `both` is requested.
- [ ] Build the template editable output from the 2:1 authoring SVG when `editable` or `both` is requested.
- [ ] Keep `exports/editable_svg.pptx` as the compatible editable output path.
- [ ] Add tests proving both modes share one manifest and produce separate outputs.
- [ ] Run focused adapter tests.

### Task 3: Wire assembly mode through final-script-pages and CLI

**Files:**
- Modify: `cyberppt/commands/final_script_pages.py`
- Modify: `cyberppt/cli.py`
- Modify: `tests/test_final_script_pages.py`
- Modify: `tests/test_cli.py`

- [ ] Add `assembly_mode` to the project command function with default `editable`.
- [ ] Add `--assembly-mode image|editable|both` to `final-script-pages`.
- [ ] Forward the value to Stage 02 production build and the run receipt.
- [ ] Preserve existing behavior when the flag is omitted.
- [ ] Add CLI and summary assertions for explicit mode selection.
- [ ] Run focused CLI and final-script-pages tests.

### Task 4: Add real-artifact verification and documentation

**Files:**
- Modify: `docs/CYBERPPT_WORKFLOW.md`
- Modify: `SKILL.md`
- Test: `tests/test_stage02_dual_assembly_integration.py`

- [ ] Document both production outputs and their exact artifact paths.
- [ ] Verify a known 2:1 Quick SVG can be assembled into the template正文区.
- [ ] Verify the image path contains one body picture and the editable path contains native text objects.
- [ ] Run OfficeCLI stats, issues, validate, and SVG/PPTX geometry checks on both outputs.
- [ ] Run the focused suite and distinguish unrelated pre-existing failures.
