# Internal Reporting Default Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make formal central SOE and government internal-reporting language the CyberPPT default without imposing a fixed presentation structure.

**Architecture:** Add two defaults to generated project manifests and make stage-one references the authoritative writing-policy source. The policy constrains title and prose style, requires source-and-task-adaptive structure selection, and treats SCR and consulting frameworks as optional analytical tools rather than default visible output structures.

**Tech Stack:** Python 3.10+, unittest, Markdown workflow contracts, YAML project manifests.

## Global Constraints

- New projects must contain writing_style.default: internal_public_sector.
- New projects must contain writing_style.structure_strategy: source_and_task_adaptive.
- Do not impose a fixed whole-deck or per-slide chapter order.
- Preserve evidence traceability, confirmation gates, visual-style selection, template text locks, and PPTX production behavior.
- Do not silently migrate existing projects or alter approved scripts and locks.
- External-consulting, commercial-proposal, board, and investor wording may be used only when explicitly requested.
- The current CyberPPT semantic-plan canvas is 1672x941; retain legacy 1280x720 input compatibility, but do not assert it as the default output canvas.

---

### Task 0: Align semantic-plan tests with the current canvas contract

**Files:**

- Modify: tests/test_dual_image_overlay_semantic_plan.py:35-578
- Modify: tests/test_dual_image_overlay_alignment.py:12-16

**Interfaces:**

- Consumes: scripts/dual_image_overlay/normalize.py:CANVAS and scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py:NORMALIZED_CANVAS_SIZE.
- Produces: tests that assert current 1672x941 normalization while retaining explicit legacy-input compatibility coverage.

- [ ] **Step 1: Confirm the stale expectations fail against the runtime contract**

    python3 -m unittest tests.test_dual_image_overlay_semantic_plan tests.test_dual_image_overlay_alignment

Expected: failures show 1280x720 expectations against the 1672x941 runtime canvas.

- [ ] **Step 2: Replace only stale default-canvas expectations**

Update failing assertions to use the current CANVAS value or current 1672x941 coordinates. Keep tests that intentionally exercise legacy 1280x720 input normalization.

- [ ] **Step 3: Verify the repaired test scope**

    python3 -m unittest tests.test_dual_image_overlay_semantic_plan tests.test_dual_image_overlay_alignment

Expected: OK.

- [ ] **Step 4: Commit the isolated regression repair**

    git add tests/test_dual_image_overlay_semantic_plan.py tests/test_dual_image_overlay_alignment.py
    git commit -m "test: align semantic plan expectations with current canvas"

---

### Task 1: Persist the default writing policy in new project workspaces

**Files:**

- Modify: cyberppt/commands/init_project.py:31-68
- Modify: tests/test_script_gate.py:13-37

**Interfaces:**

- Consumes: _project_manifest(name: str) -> str and init_project(path: Path, force: bool = False) -> list[Path].
- Produces: new manifest.yml files carrying the stable writing_style mapping for all downstream workflow agents.

- [ ] **Step 1: Write the failing manifest assertion**

Add this assertion after the existing template-text-lock assertion in ScriptGateTests.test_init_project_creates_stage_artifact_ledger_and_stage_dirs:

    self.assertIn(
        "writing_style:\n  default: internal_public_sector\n  structure_strategy: source_and_task_adaptive",
        manifest,
    )

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

    python3 -m unittest tests.test_script_gate.ScriptGateTests.test_init_project_creates_stage_artifact_ledger_and_stage_dirs

Expected: FAIL because the generated manifest has no writing_style mapping.

- [ ] **Step 3: Add the minimal generated manifest mapping**

In _project_manifest, add this top-level YAML block between schema: cyberppt.project.v1 and directories::

    writing_style:
      default: internal_public_sector
      structure_strategy: source_and_task_adaptive

Replace generated README flow item 2 with:

    2. Use $cyber-ppt to complete evidence analysis, material-type and reporting-task identification, adaptive storyline planning, and page planning. New projects default to the formal central-SOE/government internal-reporting writing style; do not impose a fixed chapter order.

- [ ] **Step 4: Run the focused test to verify it passes**

Run the command from Step 2. Expected: OK.

- [ ] **Step 5: Commit the independently testable workspace contract**

    git add cyberppt/commands/init_project.py tests/test_script_gate.py
    git commit -m "feat: default projects to internal reporting style"

### Task 2: Add the canonical internal-reporting writing policy

**Files:**

- Create: references/internal-reporting-style.md
- Modify: SKILL.md:77-141
- Modify: tests/test_skill_contract.py:9-47

**Interfaces:**

- Consumes: the first-stage reference requirement in SKILL.md and references/source-analysis.md / references/storyline.md.
- Produces: references/internal-reporting-style.md as the authoritative specification for default wording and dynamic structure selection.

- [ ] **Step 1: Write failing workflow-contract assertions**

Add this test method to SkillContractTests:

    def test_default_writing_style_uses_internal_reporting_and_adaptive_structure(self) -> None:
        text = SKILL.read_text(encoding="utf-8-sig")

        self.assertIn("references/internal-reporting-style.md", text)
        self.assertIn("央企、政府及其直属单位内部汇报", text)
        self.assertIn("source_and_task_adaptive", text)
        self.assertIn("不得固定全篇或单页目录顺序", text)
        self.assertIn("SCR、假设树、对标矩阵可作为分析工具", text)

- [ ] **Step 2: Run the focused contract test to verify it fails**

    python3 -m unittest tests.test_skill_contract.SkillContractTests.test_default_writing_style_uses_internal_reporting_and_adaptive_structure

Expected: FAIL because the policy file and required language do not exist.

- [ ] **Step 3: Create the policy and route the main skill through it**

Create references/internal-reporting-style.md with the following rules:

    # 央企政府内部汇报文风

    ## 默认范围

    本规范适用于央企、政府及其直属单位的内部汇报。默认采用正式、客观、审慎、依据充分、任务清晰、责任可落的表达。

    ## 自适应组织

    先识别材料类型、汇报任务和受众，再确定全篇主线及页面组织。不得固定全篇或单页目录顺序；工作方案、阶段进展、形势研判和专题请示可使用不同的组织方式。没有足够材料识别任务时，必须列为第一次确认事项。

    ## 标题与正文

    页面标题以事项、进展、安排、依据、需请示或需协调内容为中心，正式、客观、完整。正文按源材料需要组合事实依据、工作内容、任务安排、责任分工、时限节点、风险边界、需协调事项和请示事项；不得补写未被材料支持的内容。

    ## 分析工具与例外

    SCR、假设树、对标矩阵可作为分析工具，但不作为默认最终呈现话术。只有用户明确指定外部咨询、商业提案、董事会或投资者材料时，才可采用相应表达方式，并在项目工件中记录覆盖原因。

In SKILL.md, revise the first-stage reference requirement so it names this file alongside source-analysis.md and storyline.md, and add a default-writing-style subsection containing the five strings asserted above. Keep all evidence and confirmation gates intact.

- [ ] **Step 4: Run the focused contract test to verify it passes**

Run the command from Step 2. Expected: OK.

- [ ] **Step 5: Commit the writing-policy contract**

    git add SKILL.md references/internal-reporting-style.md tests/test_skill_contract.py
    git commit -m "feat: add internal reporting writing policy"

### Task 3: Make stage-one analysis and storyline guidance adaptive by default

**Files:**

- Modify: references/source-analysis.md:1-83
- Modify: references/storyline.md:1-109
- Modify: README.md:1-25
- Modify: pyproject.toml:8-17
- Modify: tests/test_skill_contract.py:9-65

**Interfaces:**

- Consumes: the canonical policy from references/internal-reporting-style.md.
- Produces: consistent user-visible workflow guidance without consulting-first terminology or hardcoded chapter sequencing.

- [ ] **Step 1: Write failing reference and public-description assertions**

Extend tests/test_skill_contract.py with path constants and this test:

    SOURCE_ANALYSIS = ROOT / "references" / "source-analysis.md"
    STORYLINE = ROOT / "references" / "storyline.md"
    README = ROOT / "README.md"

    def test_stage_one_references_default_to_adaptive_internal_reporting(self) -> None:
        source_text = SOURCE_ANALYSIS.read_text(encoding="utf-8-sig")
        storyline_text = STORYLINE.read_text(encoding="utf-8-sig")
        readme_text = README.read_text(encoding="utf-8-sig")

        self.assertIn("材料类型与汇报任务识别", source_text)
        self.assertIn("不得固定章节顺序", storyline_text)
        self.assertIn("页面标题或页面要点", storyline_text)
        self.assertIn("央企、政府内部汇报", readme_text)
        self.assertNotIn("咨询风格的 PowerPoint", readme_text)

- [ ] **Step 2: Run the focused test to verify it fails**

    python3 -m unittest tests.test_skill_contract.SkillContractTests.test_stage_one_references_default_to_adaptive_internal_reporting

Expected: FAIL because the stage-one references and README still define consulting style as the default.

- [ ] **Step 3: Update the stage-one and package language**

Apply these focused content changes:

- In references/source-analysis.md, add “材料类型与汇报任务识别” before content brainstorming. Require material type, reporting purpose, audience, recommended organization, rationale, and confirmation items. State that no fixed chapter order may be presumed.
- In references/storyline.md, rename the narrative section to “构建汇报主线与页面组织”, make SCR optional, change “结论标题” to “页面标题或页面要点”, and require task-adaptive titles without fixed chapter sequencing.
- In README.md, replace the consulting/MBB default definition with “适用于央企、政府内部汇报的高信息密度、证据可追溯、可编辑 PPTX”; state that the structure adapts to materials and task, and consulting frameworks require explicit request.
- In pyproject.toml, set the description to “CyberPPT project tooling for evidence-based, editable internal-reporting PowerPoint workflows.” and replace the consulting keyword with internal-reporting.

Do not alter visual, production, or QA instructions.

- [ ] **Step 4: Run focused and broad regression tests**

    python3 -m unittest tests.test_skill_contract tests.test_script_gate
    python3 -m unittest discover -s tests -p 'test*.py'

Expected: both commands finish with OK.

- [ ] **Step 5: Review changed scope and commit documentation alignment**

Run:

    git diff --check
    git status --short

Then run GitNexus detect_changes with repo CyberPPT and scope all. Verify only the intended initialization and workflow-contract scope appears. Commit only the Task 3 files:

    git add references/source-analysis.md references/storyline.md README.md pyproject.toml tests/test_skill_contract.py
    git commit -m "docs: make internal reporting the default narrative"

### Task 4: Verify the new default from the public CLI

**Files:**

- No source changes expected.

**Interfaces:**

- Consumes: python3 -m cyberppt init and the persisted manifest mapping from Task 1.
- Produces: an end-to-end verification record that the public entry point emits the declared default.

- [ ] **Step 1: Create an isolated temporary project through the CLI**

    tmpdir="$(mktemp -d)"
    python3 -m cyberppt init "$tmpdir/internal-reporting-check"

Expected: command exits 0 and reports the initialized project path.

- [ ] **Step 2: Assert the generated configuration**

    rg -n "writing_style:|default: internal_public_sector|structure_strategy: source_and_task_adaptive" "$tmpdir/internal-reporting-check/manifest.yml"
    rm -rf "$tmpdir"

Expected: all three manifest lines are found before the temporary directory is removed.

- [ ] **Step 3: Run final repository checks**

    python3 -m cyberppt doctor
    git diff --check
    git status --short

Expected: doctor prints ok for every check; no unexpected tracked changes remain. Do not commit temporary files or existing untracked project directories.
