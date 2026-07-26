# Page Visual Intent Compiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile a short, page-specific visual intent from existing Stage 01 fields and place it between drawable on-screen text and the global Style 09 contract in every content-page ImageGen prompt.

**Architecture:** Add one deterministic pure function to the existing ImageGen handoff module. It classifies the page into one of five relationship types from `business_question`, `main_message`, module titles, and on-screen text, then emits four non-rendering prompt-context lines. Existing callers continue to work through default arguments; generic and project-local handoff paths additionally pass optional Outline overrides.

**Tech Stack:** Python 3, existing `ScriptPage` parser, JSON Outline files, `unittest`/`pytest`, existing Style 09 prompt compiler.

## Global Constraints

- Keep CyberPPT a small single-machine script tool; add no service, database, model call, dependency, or independent workflow.
- Do not rewrite on-screen text.
- Do not replace or weaken the Style 09 global contract.
- Do not send boundary, evidence, visual-structure, or speaker-note fields to ImageGen.
- Page mission, core judgment, and page visual intent are prompt context only and must not be rendered.
- Do not call ImageGen; stop at the existing Stage 02 script approval gate.
- Preserve unrelated dirty-worktree changes and commit only files named by each task.
- Before modifying an existing function, run GitNexus upstream impact analysis and warn before proceeding if the result is HIGH or CRITICAL.
- Before every commit, run GitNexus `detect_changes` on the staged scope.

---

### Task 1: Add the deterministic page visual intent compiler

**Files:**
- Modify: `tests/test_imagegen_no_visual_structure.py`
- Modify: `scripts/dual_image_overlay/imagegen_handoff.py`

**Interfaces:**
- Consumes: `ScriptPage`, `page_mission: str`, optional `override: dict[str, str] | None`.
- Produces: `build_page_visual_intent(page: ScriptPage, page_mission: str, override: dict[str, str] | None = None) -> str`.

- [ ] **Step 1: Add failing classification and fallback tests**

Add `build_page_visual_intent` to the imports, add `_page` above the existing test class, and add the three `test_...` methods inside `ImageGenNoVisualStructureTests`:

```python
def _page(main_message: str, mission_text: str, modules: str):
    return parse_script_markdown(
        f"""## 第19页：测试页
- 页面类型：内容页
- 页面标题：测试页
- 主判断：{main_message}
- 上屏文字：

{modules}
"""
    ).pages[0], mission_text


def test_visual_intent_classifies_decision_and_admission(self) -> None:
    page, mission = _page(
        "首期场景由成熟度条件共同决定",
        "首期场景如何选定、后续场景如何分期推进",
        """  **筛选依据｜五维共同决定**
  - 按成熟度选择。
  **首期取舍｜双场景**
  - 首期进入。
  **后续准入｜条件成熟再纳入**
  - 后续验证。""",
    )
    intent = build_page_visual_intent(page, mission)
    self.assertIn("[Prompt context] Page-specific visual intent", intent)
    self.assertIn("readiness gates", intent)
    self.assertIn("decision structure, not an implementation process", intent)
    self.assertIn("Five equal-weight criterion cards", intent)


def test_visual_intent_classifies_causal_closed_loop_and_phase(self) -> None:
    cases = [
        ("为什么现有研判不足", "问题、原因与影响共同形成能力需求", "cause-and-effect"),
        ("业务如何形成闭环", "输入、处理、输出、反馈与复盘", "closed-loop"),
        ("能力如何分期推进", "当前、近期和中长期分阶段建设", "stage progression"),
    ]
    for mission, message, marker in cases:
        page, _ = _page(message, mission, "  **支撑模块**\n  - 支撑内容。")
        self.assertIn(marker, build_page_visual_intent(page, mission))


def test_visual_intent_uses_safe_fallback_and_partial_override(self) -> None:
    page, mission = _page(
        "形成稳定的行业公共能力",
        "拟建设什么能力",
        "  **能力基础**\n  - 形成支撑。",
    )
    intent = build_page_visual_intent(
        page,
        mission,
        {"recommended_composition": "Use one evidence-led editorial composition."},
    )
    self.assertIn("judgment supported by evidence", intent)
    self.assertIn("Use one evidence-led editorial composition.", intent)
    self.assertIn("Avoid on this page:", intent)
```

- [ ] **Step 2: Run the new tests and verify failure**

Run:

```bash
PYTHONPATH=. pytest -q \
  tests/test_imagegen_no_visual_structure.py::ImageGenNoVisualStructureTests::test_visual_intent_classifies_decision_and_admission \
  tests/test_imagegen_no_visual_structure.py::ImageGenNoVisualStructureTests::test_visual_intent_classifies_causal_closed_loop_and_phase \
  tests/test_imagegen_no_visual_structure.py::ImageGenNoVisualStructureTests::test_visual_intent_uses_safe_fallback_and_partial_override
```

Expected: collection/import failure because `build_page_visual_intent` does not exist.

- [ ] **Step 3: Implement the minimal compiler**

Add relationship signal constants and the pure function immediately after `_clean_onscreen_for_imagegen`:

```python
VISUAL_INTENT_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("decision_admission", ("筛选", "选择", "首期", "后续", "准入", "条件")),
    ("causal", ("问题", "原因", "影响", "需求", "为什么")),
    ("closed_loop", ("输入", "处理", "输出", "反馈", "复盘", "闭环")),
    ("phase", ("当前", "近期", "中长期", "阶段", "分期")),
)

VISUAL_INTENT_TEMPLATES: dict[str, dict[str, str]] = {
    "decision_admission": {
        "visual_thesis": "Explain why the initial selection is justified and how later items qualify for entry.",
        "decision_relationship": (
            "Selection criteria jointly justify the initial choice; later items remain "
            "behind explicit readiness gates. Treat this as a decision structure, not an implementation process."
        ),
        "recommended_composition": (
            "Give the selected initial scope dominant visual weight; use compact criteria "
            "evidence to support it, and place later scope in a secondary gated-entry area."
        ),
        "avoid_on_this_page": (
            "Five equal-weight criterion cards, a generic three-step flow, timeline, "
            "or scenario thumbnail wall."
        ),
    },
    "causal": {
        "visual_thesis": "Make the page judgment visible through a clear cause-and-effect argument.",
        "decision_relationship": "Causes or changes lead to a business consequence and explain the need for action.",
        "recommended_composition": "Use one dominant consequence supported by compact causal evidence.",
        "avoid_on_this_page": "A list of unrelated facts, equal cards, or decorative trend arrows.",
    },
    "closed_loop": {
        "visual_thesis": "Show how business inputs become usable results and improve through feedback.",
        "decision_relationship": "Use a closed-loop relationship with explicit input, result, validation, and feedback.",
        "recommended_composition": "Use one integrated operational loop anchored in a real work context.",
        "avoid_on_this_page": "A software workflow, lifecycle icon circle, or numbered administration steps.",
    },
    "phase": {
        "visual_thesis": "Show stage progression while preserving the different purpose of each phase.",
        "decision_relationship": "Current, near-term, and later work form a stage progression with explicit readiness conditions.",
        "recommended_composition": "Give the current or near-term decision primary weight and later stages secondary weight.",
        "avoid_on_this_page": "An equal-weight timeline, generic roadmap arrows, or milestone decoration.",
    },
    "judgment_evidence": {
        "visual_thesis": "Express the page as one judgment supported by evidence.",
        "decision_relationship": "Supporting modules jointly explain or substantiate the core judgment.",
        "recommended_composition": "Use one dominant judgment area with compact, unequal-weight supporting evidence.",
        "avoid_on_this_page": "An equal card wall, one icon per bullet, or an unrelated decorative scene.",
    },
}


def build_page_visual_intent(
    page: ScriptPage,
    page_mission: str,
    override: dict[str, str] | None = None,
) -> str:
    if page.page_type != "content":
        raise ValueError(f"page {page.page_id} is {page.page_type}; no visual intent")
    signal_text = "\n".join(
        (
            page_mission,
            page.main_message,
            "\n".join(page.module_titles),
            page.onscreen_text,
        )
    )
    relation = "judgment_evidence"
    for candidate, signals in VISUAL_INTENT_SIGNALS:
        if any(signal in signal_text for signal in signals):
            relation = candidate
            break
    values = dict(VISUAL_INTENT_TEMPLATES[relation])
    if isinstance(override, dict):
        for key in values:
            value = override.get(key)
            if isinstance(value, str) and value.strip():
                values[key] = value.strip()
    return "\n".join(
        (
            "[Prompt context] Page-specific visual intent "
            "(composition guidance only; do not render field names or instruction text)",
            f"- Visual thesis: {values['visual_thesis']}",
            f"- Decision relationship: {values['decision_relationship']}",
            f"- Recommended composition: {values['recommended_composition']}",
            f"- Avoid on this page: {values['avoid_on_this_page']}",
        )
    )
```

- [ ] **Step 4: Run the focused tests**

Run:

```bash
PYTHONPATH=. pytest -q tests/test_imagegen_no_visual_structure.py
```

Expected: all tests in the file pass.

- [ ] **Step 5: Commit the compiler and tests**

Before committing:

```bash
git add -- scripts/dual_image_overlay/imagegen_handoff.py tests/test_imagegen_no_visual_structure.py
node .gitnexus/run.cjs detect_changes -r CyberPPT --scope staged
git diff --cached --check
```

Commit:

```bash
git commit -m "feat(imagegen): compile page visual intent"
```

---

### Task 2: Integrate visual intent and optional Outline overrides into handoff

**Files:**
- Modify: `tests/test_imagegen_no_visual_structure.py`
- Modify: `scripts/dual_image_overlay/imagegen_handoff.py`

**Interfaces:**
- Consumes: `build_page_visual_intent(...)` from Task 1.
- Produces: `build_page_prompt(page, style_lock, page_mission="", visual_intent_override=None) -> str` and `_page_visual_intent_overrides(project: Path) -> dict[str, dict[str, str]]`.

- [ ] **Step 1: Run GitNexus impact analysis before editing existing symbols**

Run:

```bash
node .gitnexus/run.cjs impact build_page_prompt -r CyberPPT -f scripts/dual_image_overlay/imagegen_handoff.py -d upstream
node .gitnexus/run.cjs impact write_chapter_handoff -r CyberPPT -f scripts/dual_image_overlay/imagegen_handoff.py -d upstream
```

Record direct callers and affected processes. If either result is HIGH or CRITICAL, warn before editing.

- [ ] **Step 2: Add failing integration and override-loader tests**

Add:

```python
def test_page_prompt_places_visual_intent_after_onscreen_before_style(self) -> None:
    page = parse_script_markdown(SCRIPT_WITH_VISUAL_STRUCTURE).pages[0]
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(
            page,
            lock,
            page_mission="首期场景如何选择",
            visual_intent_override={
                "visual_thesis": "Explain the approved page-specific decision."
            },
        )
    self.assertLess(prompt.index("上屏文字"), prompt.index("Page-specific visual intent"))
    self.assertLess(prompt.index("Page-specific visual intent"), prompt.index("Industry scene anchor:"))
    self.assertIn("Explain the approved page-specific decision.", prompt)
    self.assertIn("do not render field names or instruction text", prompt)
```

Add `import json` and `_page_visual_intent_overrides` to the test imports, then add:

```python
def test_page_visual_intent_override_loader_ignores_invalid_values(self) -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory)
        outline = project / "workbench/stages/01-analysis/outline.json"
        outline.parent.mkdir(parents=True)
        outline.write_text(
            json.dumps(
                {
                    "pages": [
                        {
                            "page_id": "p19",
                            "visual_intent": {
                                "visual_thesis": "  Approved thesis.  ",
                                "decision_relationship": "",
                                "unknown_field": "ignored",
                            },
                        },
                        {"page_id": "p20", "visual_intent": "invalid"},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        overrides = _page_visual_intent_overrides(project)
    self.assertEqual(
        {"p19": {"visual_thesis": "Approved thesis."}},
        overrides,
    )
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
PYTHONPATH=. pytest -q \
  tests/test_imagegen_no_visual_structure.py::ImageGenNoVisualStructureTests::test_page_prompt_places_visual_intent_after_onscreen_before_style
```

Expected: failure because `build_page_prompt` does not accept `visual_intent_override`.

- [ ] **Step 4: Implement prompt integration and override loading**

Add:

```python
def _page_visual_intent_overrides(project: Path) -> dict[str, dict[str, str]]:
    outline_path = project / "workbench" / "stages" / "01-analysis" / "outline.json"
    if not outline_path.is_file():
        return {}
    payload = json.loads(outline_path.read_text(encoding="utf-8-sig"))
    pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(pages, list):
        return {}
    result: dict[str, dict[str, str]] = {}
    for item in pages:
        if not isinstance(item, dict) or not item.get("page_id"):
            continue
        raw = item.get("visual_intent")
        if not isinstance(raw, dict):
            continue
        cleaned = {
            key: value.strip()
            for key, value in raw.items()
            if key in VISUAL_INTENT_TEMPLATES["judgment_evidence"]
            and isinstance(value, str)
            and value.strip()
        }
        if cleaned:
            result[str(item["page_id"])] = cleaned
    return result
```

Extend `build_page_prompt`:

```python
def build_page_prompt(
    page: ScriptPage,
    style_lock: Path,
    page_mission: str = "",
    visual_intent_override: dict[str, str] | None = None,
) -> str:
    prompt_text = "\n".join(
        (
            content_lock_text(page, page_mission=page_mission).rstrip(),
            "",
            build_page_visual_intent(
                page,
                page_mission,
                override=visual_intent_override,
            ),
        )
    )
    block = PageBlock(
        page_number=int(page.page_id[1:]),
        title=page.title or page.page_id,
        text=prompt_text,
    )
```

In `write_chapter_handoff`, load overrides once and pass `overrides.get(page.page_id)` to `build_page_prompt`. Update the review rules to state that page visual intent is sent as non-rendering composition context.

- [ ] **Step 5: Run integration tests**

Run:

```bash
PYTHONPATH=. pytest -q \
  tests/test_imagegen_no_visual_structure.py \
  tests/test_dual_image_overlay_deliverable_prompt.py
```

Expected: all tests pass.

- [ ] **Step 6: Commit handoff integration**

Before committing:

```bash
git add -- scripts/dual_image_overlay/imagegen_handoff.py tests/test_imagegen_no_visual_structure.py
node .gitnexus/run.cjs detect_changes -r CyberPPT --scope staged
git diff --cached --check
```

Commit:

```bash
git commit -m "feat(imagegen): hand off page visual intent"
```

---

### Task 3: Update and regenerate the current Style 09 project

**Files:**
- Modify: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/02-blueprint-dual-image/_refresh_style09_prompts.py`
- Modify: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/02-blueprint-dual-image/_batch_regen_style09.py`
- Modify: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/02-blueprint-dual-image/_regen_page12.py`
- Regenerate: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/prompts/imagegen/slide-*-imagegen-final.md`
- Regenerate: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/prompts/imagegen/style09-industry-scene-20260726-imagegen-review.md`
- Regenerate: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/02-blueprint-dual-image/pages_001_032/script-final_cyberppt_deliverable_p1_p32.md`

**Interfaces:**
- Consumes: extended `build_page_prompt(...)` and optional Outline `visual_intent`.
- Produces: 24 refreshed content prompts and two 32-page review/compiled scripts.

- [ ] **Step 1: Run GitNexus impact analysis on the three project entry points**

Run:

```bash
node .gitnexus/run.cjs impact main -r CyberPPT -f projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/02-blueprint-dual-image/_refresh_style09_prompts.py -d upstream
node .gitnexus/run.cjs impact main -r CyberPPT -f projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/02-blueprint-dual-image/_batch_regen_style09.py -d upstream
node .gitnexus/run.cjs impact main -r CyberPPT -f projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/02-blueprint-dual-image/_regen_page12.py -d upstream
```

Warn before editing if any result is HIGH or CRITICAL.

- [ ] **Step 2: Pass optional visual-intent overrides from Outline**

In each script, build:

```python
page_visual_intents = {
    str(item.get("page_id")): {
        key: value.strip()
        for key, value in (item.get("visual_intent") or {}).items()
        if isinstance(value, str) and value.strip()
    }
    for item in outline.get("pages", [])
    if isinstance(item, dict)
    and item.get("page_id")
    and isinstance(item.get("visual_intent"), dict)
}
```

Pass:

```python
visual_intent_override=page_visual_intents.get(page.page_id)
```

Keep automatic compilation active when no override exists.

- [ ] **Step 3: Add project-refresh assertions**

For every content-page prompt assert:

```python
assert "[Prompt context] Page-specific visual intent" in prompt
assert "Visual thesis:" in prompt
assert "Decision relationship:" in prompt
assert "Recommended composition:" in prompt
assert "Avoid on this page:" in prompt
assert prompt.index("上屏文字") < prompt.index("Page-specific visual intent")
assert prompt.index("Page-specific visual intent") < prompt.index("Industry scene anchor:")
```

For page 19 additionally assert:

```python
assert "readiness gates" in prompt
assert "decision structure, not an implementation process" in prompt
assert "Five equal-weight criterion cards" in prompt
```

- [ ] **Step 4: Run syntax and focused regression tests**

Run:

```bash
python3 -m py_compile \
  scripts/dual_image_overlay/imagegen_handoff.py \
  projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/02-blueprint-dual-image/_refresh_style09_prompts.py \
  projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/02-blueprint-dual-image/_batch_regen_style09.py \
  projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/02-blueprint-dual-image/_regen_page12.py

PYTHONPATH=. pytest -q \
  tests/test_imagegen_no_visual_structure.py \
  tests/test_dual_image_overlay_deliverable_prompt.py
```

Expected: syntax succeeds and all focused tests pass.

- [ ] **Step 5: Regenerate Style 09 prompts without calling ImageGen**

Run:

```bash
python3 projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/02-blueprint-dual-image/_refresh_style09_prompts.py
```

Expected:

- `refreshed_content_pages=24`;
- review script regenerated;
- compiled 32-page script regenerated;
- Stage 02 gate remains `waiting_for_user_modify_or_approve`.

- [ ] **Step 6: Verify the generated artifacts**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import re

root = Path("projects/power-supply-forecast-warning-prestudy-20260724/workbench")
review = root / "prompts/imagegen/style09-industry-scene-20260726-imagegen-review.md"
compiled = root / "stages/02-blueprint-dual-image/pages_001_032/script-final_cyberppt_deliverable_p1_p32.md"
page19 = root / "prompts/imagegen/slide-19-imagegen-final.md"

for path in (review, compiled):
    text = path.read_text(encoding="utf-8")
    assert len(re.findall(r"^## 第\\d+页：", text, re.M)) == 32
    assert text.count("[Prompt context] 页面使命 / Page mission") == 24
    assert text.count("[Prompt context] 核心判断 / Core judgment") == 24
    assert text.count("[Prompt context] Page-specific visual intent") == 24

text = page19.read_text(encoding="utf-8")
for required in (
    "readiness gates",
    "decision structure, not an implementation process",
    "Five equal-weight criterion cards",
    "Industry scene anchor:",
    "People are supporting contextual elements only",
    "Moderate-to-high information density, low visual density",
):
    assert required in text, required
print("verified: 32 page headings, 24 visual intents, page 19 decision/admission contract")
PY

rg -n "run_codex_image|imagegen\\(" \
  projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/02-blueprint-dual-image/_refresh_style09_prompts.py
```

Expected: the checker prints its success line, and the final search returns no ImageGen-call matches from the refresh-only script.

- [ ] **Step 7: Commit only the implementation scope**

Stage only the global handoff, focused tests, the three current-project scripts, and regenerated Markdown prompts named above. Then run:

```bash
node .gitnexus/run.cjs detect_changes -r CyberPPT --scope staged
git diff --cached --check
git diff --cached --stat
```

Verify no unrelated files are staged, then commit:

```bash
git commit -m "feat(imagegen): add page-specific visual intent"
```

Report the exact commit, focused test count, regenerated artifact paths, and unchanged Stage 02 approval status.
