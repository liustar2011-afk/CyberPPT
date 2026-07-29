# Style 09 Hybrid Generation Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add content-driven layout variation and separate short generated labels from editable body text.

**Architecture:** Keep `上屏文字` as the content authority. Optional page overrides plus a batch-aware resolver select a visual motif and scene role; the prompt uses only bounded short text, while the existing editable-overlay route receives the full body through the template lock.

**Tech Stack:** Python 3, dataclasses, JSON, pytest.

## Global Constraints

- New fields are optional; legacy scripts continue to parse and compile.
- Style 09 locks elegant, composed, formal visual character, never a single layout or scene.
- Adjacent pages in one batch cannot use the same motif; any four-page window has at most two `primary_scene` decisions.
- Explicit script values override automatic decisions.
- Do not add dependencies, services, or workflow phases.

---

### Task 1: Parse optional presentation overrides

**Files:**
- Modify: `cyberppt/script_quality_contract.py:85-270`
- Test: `tests/test_script_quality_contract.py`

**Interfaces:** `ScriptPage` gains `layout_motif: str = ""`, `scene_role: str = ""`, and `image_locked_text: str = ""`.

- [ ] **Step 1: Write failing tests**

```python
def test_parse_optional_presentation_fields() -> None:
    page = parse_script_markdown(
        "## 第1页：示例\n- 页面类型：内容页\n- 上屏结论：结论\n"
        "- 上屏文字：正文\n- 版式母题：process_atlas\n"
        "- 场景角色：no_scene\n- 生图锁定文字：短标签\n"
    ).pages[0]
    assert (page.layout_motif, page.scene_role, page.image_locked_text) == (
        "process_atlas", "no_scene", "短标签"
    )

def test_legacy_page_defaults_presentation_fields_to_empty() -> None:
    page = parse_script_markdown(
        "## 第1页：示例\n- 页面类型：内容页\n- 上屏结论：结论\n- 上屏文字：正文\n"
    ).pages[0]
    assert (page.layout_motif, page.scene_role, page.image_locked_text) == ("", "", "")
```

- [ ] **Step 2: Run the focused test**

Run: `python3 -m pytest tests/test_script_quality_contract.py -q`  
Expected: fail because the fields do not exist.

- [ ] **Step 3: Implement parser fields**

```python
image_locked_text=fields.get("生图锁定文字", "").strip(),
layout_motif=fields.get("版式母题", "").strip(),
scene_role=fields.get("场景角色", "").strip(),
```

Add the dataclass fields with empty defaults after existing optional judgment fields.

- [ ] **Step 4: Verify and commit**

Run: `python3 -m pytest tests/test_script_quality_contract.py -q`  
Expected: PASS.  
Commit: `git add cyberppt/script_quality_contract.py tests/test_script_quality_contract.py && git commit -m "feat: parse hybrid presentation overrides"`

### Task 2: Resolve presentation decisions by content and batch history

**Files:**
- Modify: `scripts/dual_image_overlay/creative_brief.py`
- Modify: `scripts/dual_image_overlay/imagegen_handoff.py:540-1230`
- Test: `tests/test_imagegen_creative_brief.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class PresentationDecision:
    layout_motif: str
    scene_role: str
    source: str
    reason: str

def resolve_presentation_decision(
    page: ScriptPage, relation: str, prior_decisions: tuple[PresentationDecision, ...] = ()
) -> PresentationDecision: ...
```

- [ ] **Step 1: Write failing resolver tests**

```python
def test_explicit_presentation_values_override_router() -> None:
    page = make_page(layout_motif="process_atlas", scene_role="no_scene")
    decision = resolve_presentation_decision(page, "phase")
    assert (decision.layout_motif, decision.scene_role, decision.source) == (
        "process_atlas", "no_scene", "script"
    )

def test_router_avoids_adjacent_duplicate_motif() -> None:
    first = resolve_presentation_decision(make_page(), "capability_relationship")
    second = resolve_presentation_decision(make_page(), "capability_relationship", (first,))
    assert first.layout_motif != second.layout_motif

def test_router_caps_primary_scene_density() -> None:
    prior = tuple(PresentationDecision("control_room_bridge", "primary_scene", "auto", "") for _ in range(2))
    decision = resolve_presentation_decision(make_page(), "closed_loop", prior)
    assert decision.scene_role != "primary_scene"
```

- [ ] **Step 2: Run the focused test**

Run: `python3 -m pytest tests/test_imagegen_creative_brief.py -q`  
Expected: fail on missing resolver symbols.

- [ ] **Step 3: Implement resolver**

Implement candidate sets from the approved specification: each relation gets two motifs, explicit script values win, automatic routing chooses the first motif different from the immediately prior decision, and `primary_scene` is demoted to `supporting_evidence` when two of the latest three decisions are primary scenes. Add the decision to `CreativeBrief.to_dict()`. In `write_chapter_handoff()`, carry decisions in page order and pass them into prompt compilation.

- [ ] **Step 4: Verify and commit**

Run: `python3 -m pytest tests/test_imagegen_creative_brief.py -q`  
Expected: PASS.  
Commit: `git add scripts/dual_image_overlay/creative_brief.py scripts/dual_image_overlay/imagegen_handoff.py tests/test_imagegen_creative_brief.py && git commit -m "feat: route content-driven presentation motifs"`

### Task 3: Bound ImageGen text and preserve editable body text

**Files:**
- Modify: `scripts/dual_image_overlay/imagegen_handoff.py:618-900`
- Test: `tests/test_imagegen_no_visual_structure.py`
- Test: `tests/test_imagegen_creative_brief.py`

**Interfaces:**

```python
MAX_IMAGE_LOCKED_LINES = 7
MAX_IMAGE_LOCKED_LINE_CHARS = 14
MAX_IMAGE_LOCKED_CHARS = 84

def select_image_locked_text(
    page: ScriptPage, visual_context: dict[str, str] | None = None
) -> str: ...
```

- [ ] **Step 1: Write failing text-boundary tests**

```python
def test_explicit_image_locked_text_wins() -> None:
    page = make_page(image_locked_text="能力框架\n运行保障｜贯穿各层")
    assert select_image_locked_text(page) == "能力框架\n运行保障｜贯穿各层"

def test_long_body_is_marked_editable_not_verbatim_generated() -> None:
    page = make_page(onscreen_text="**模块A**\n- " + "正文" * 100)
    _, prompt = render_content_first_prompt(page, style_lock=style_lock())
    assert "【生图锁定文字】" in prompt
    assert "【可编辑正文层】" in prompt
    assert "不得要求 ImageGen 逐字渲染该正文层" in prompt

def test_numeric_line_is_retained_in_generated_text() -> None:
    page = make_page(onscreen_text="**模块A**\n- 2025年完成率 95%")
    assert "2025年完成率 95%" in select_image_locked_text(page)
```

- [ ] **Step 2: Run the focused test**

Run: `python3 -m pytest tests/test_imagegen_no_visual_structure.py tests/test_imagegen_creative_brief.py -q`  
Expected: fail on missing selector and prompt sections.

- [ ] **Step 3: Implement the boundary**

Use explicit `image_locked_text` if supplied. Otherwise start from `locked_onscreen_text()`, retain module titles and numeric lines first, de-duplicate, and enforce all three thresholds. Render the decision immediately after `【页面逻辑】`; render complete semantics as contextual meaning, then add `【可编辑正文层】` with a direct instruction that it must be expressed through editable overlay rather than required verbatim in the bitmap.

- [ ] **Step 4: Verify and commit**

Run: `python3 -m pytest tests/test_imagegen_no_visual_structure.py tests/test_imagegen_creative_brief.py -q`  
Expected: PASS.  
Commit: `git add scripts/dual_image_overlay/imagegen_handoff.py tests/test_imagegen_no_visual_structure.py tests/test_imagegen_creative_brief.py && git commit -m "feat: separate generated labels from editable body text"`

### Task 4: Persist the decision and editable body in template locks

**Files:**
- Modify: `cyberppt/commands/final_script_pages.py:83-145`
- Test: `tests/test_final_script_pages.py`

**Interfaces:** Every `cyberppt.template_text_lock.v1.records[]` item gains `editable_body_text`, `image_locked_text`, `layout_motif`, and `scene_role`; existing fields remain unchanged.

- [ ] **Step 1: Write a failing lock test**

```python
def test_template_lock_records_hybrid_text_contract(tmp_path: Path) -> None:
    summary = run_final_script_pages(
        project=project_with_approved_script(tmp_path),
        script=approved_script,
        pages_raw="1",
        production_mode="editable-overlay",
    )
    lock = json.loads(Path(summary["artifacts"]["template_text_lock"]).read_text())
    record = lock["records"][0]
    assert record["editable_body_text"]
    assert record["image_locked_text"]
    assert record["layout_motif"]
    assert record["scene_role"]
```

- [ ] **Step 2: Run the focused test**

Run: `python3 -m pytest tests/test_final_script_pages.py -q`  
Expected: fail on absent record fields.

- [ ] **Step 3: Implement lock persistence**

Parse the source script once, index pages by sequence, use the same resolver and short-text selector as the handoff compiler, and write `onscreen_text` as `editable_body_text`. Do not alter title, approval, or manifest fields.

- [ ] **Step 4: Verify and commit**

Run: `python3 -m pytest tests/test_final_script_pages.py -q`  
Expected: PASS.  
Commit: `git add cyberppt/commands/final_script_pages.py tests/test_final_script_pages.py && git commit -m "feat: persist hybrid text layer contract"`

### Task 5: Verify a Style 09 prompt batch without production generation

**Files:**
- Modify: none unless a test exposes a defect.
- Verify: tasks 1–4 and the current P09–P12 final script.

- [ ] **Step 1: Run all focused tests**

Run: `python3 -m pytest tests/test_script_quality_contract.py tests/test_imagegen_creative_brief.py tests/test_imagegen_no_visual_structure.py tests/test_final_script_pages.py -q`  
Expected: PASS.

- [ ] **Step 2: Compile a non-production batch**

Run: `python3 scripts/dual_image_overlay/imagegen_handoff.py projects/power-supply-forecast-warning-prestudy-20260724 --script projects/power-supply-forecast-warning-prestudy-20260724/workbench/scripts/final/script-final.md --style-lock projects/power-supply-forecast-warning-prestudy-20260724/workbench/locks/visual_style_lock.json --pages 9-12 --batch-name hybrid-contract-smoke`  
Expected: diagnostics records non-repeating motifs and bounded image text.

- [ ] **Step 3: Inspect compiler metadata**

Run: `jq '.pages[] | {page_id, creative_brief, image_locked_text, editable_body_text}' projects/power-supply-forecast-warning-prestudy-20260724/workbench/prompts/imagegen/hybrid-contract-smoke-imagegen-diagnostics.json`  
Expected: no adjacent duplicate motifs and no more than two primary scenes.

- [ ] **Step 4: Commit only regression fixes if any**

Run: `git status --short`  
Expected: no unrelated paths are staged. Commit only files changed to repair a failing focused test.

---

## Self-Review

- Tasks 1–2 cover optional overrides and content-driven variation.
- Task 3 covers the text split and preserves numeric constraints.
- Task 4 propagates the full editable truth to the existing rebuild route.
- Task 5 validates compatibility and batch-level variation without creating production images.
