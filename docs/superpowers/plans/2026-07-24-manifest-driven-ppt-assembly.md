# Manifest-Driven PPT Assembly Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the verified Stage2 template-page and approved-image assembly contract so one `final-script-pages` production run builds a complete ordered PPTX without generating images for cover, agenda, section, or ending pages.

**Architecture:** Keep `final-script-pages` as the sole production orchestrator. Port Stage2's role partition and native-template assembly into the current mainline, while preserving current prompt compilation, style 9, speaker notes, and artifact structures. `page_image_pairs.json` remains the sole content-image authority; template pages remain in the ordered page set as explicit skipped records.


## Global Constraints

- Migrate proven code from `D:\CyberPPT-Stage2`; do not create a second assembler or prompt source.
- Do not overwrite whole current-mainline files with Stage2 copies.
- Preserve visual styles 1–9, especially the distinct meanings of style 4 and extension-only style 9.
- Preserve speaker notes and current production artifact structures.
- Template roles are exactly `cover`, `agenda`, `section`, and `ending`; input aliases normalize at boundaries.
- Template pages have no prompt, image path, or `full` image record.
- OCR, overlay reconstruction, background derivation, and legacy template rebuild remain excluded.
- Stage only task-owned files; preserve all unrelated dirty-worktree changes.

## File Map

- Modify `scripts/dual_image_overlay/cyberppt_pair_manifest.py`: canonical role classification and content/template manifest partition.
- Modify `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py`: consume approved locks/images, validate roles, derive agenda/section metadata, render four native templates, and gate production export.
- Modify `cyberppt/commands/final_script_pages.py`: pass all approved inputs to project-production assembly and publish readiness only after verified export.
- Create `scripts/dual_image_overlay/rebuild_engine/templates/brands/中电联公共元素_轻量版/02_agenda.svg`: migrated Stage2 agenda template.
- Create `scripts/dual_image_overlay/rebuild_engine/templates/brands/中电联公共元素_轻量版/03_section.svg`: migrated Stage2 section template.
- Modify `scripts/dual_image_overlay/rebuild_engine/templates/brands/中电联公共元素_轻量版/brand_rules.json`: register four templates and their fields.
- Modify `tests/test_dual_image_overlay_pair_manifest.py`: template-skip and partition tests.
- Create `tests/test_brand_templates.py`: migrated native-template unit tests.
- Create `tests/test_template_image_ppt_production.py`: approved-input and ordered-assembly tests.
- Modify `tests/test_final_script_pages.py`: production argument propagation and readiness tests.

---

### Task 1: Port the Template-Page Manifest Partition

**Files:**
- Modify: `scripts/dual_image_overlay/cyberppt_pair_manifest.py:36-158`
- Modify: `tests/test_dual_image_overlay_pair_manifest.py`

**Interfaces:**
- Produces: `TEMPLATE_ONLY_PAGE_ROLES: frozenset[str]`
- Produces: `classify_page_role(page_number: int, title: str, text: str) -> str`
- Produces: manifest keys `requested_pages`, `content_page_numbers`, `skipped_pages`, and `pairs`
- Preserves: `build_manifest(*, script: Path, pages_raw: str, output_dir: Path, project_path: Path | None, style_lock: Path | None, force_pending: bool = False) -> tuple[dict[str, Any], Path, Path, list[int]]`

- [ ] **Step 1: Run required impact analysis**

Run:

```powershell
```


- [ ] **Step 2: Add failing role-classification and partition tests**

Add tests using a temporary final script containing cover, agenda, section, content, and ending pages:

```python
def test_manifest_skips_all_native_template_roles(tmp_path: Path) -> None:
    script = tmp_path / "script.md"
    script.write_text(
        """## P1 封面
本页类型：封面页
## P2 目录
本页类型：目录页
## P3 第一章 工作背景
本页类型：章节过渡页
## P4 核心方案
本页类型：内容页
组件A：统一数据底座
## P5 感谢聆听
本页类型：结束页
""",
        encoding="utf-8",
    )
    manifest, _, _, pages = build_manifest(
        script=script,
        pages_raw="all",
        output_dir=tmp_path / "out",
        project_path=None,
        style_lock=None,
    )

    assert pages == [1, 2, 3, 4, 5]
    assert manifest["requested_pages"] == pages
    assert manifest["content_page_numbers"] == [4]
    assert [item["page_number"] for item in manifest["pairs"]] == [4]
    assert {
        item["page_number"]: item["page_role"]
        for item in manifest["skipped_pages"]
    } == {1: "cover", 2: "agenda", 3: "section", 5: "ending"}
    assert all(
        not ({"prompt", "image_path", "full"} & set(item))
        for item in manifest["skipped_pages"]
    )
```

Also add:

```python
def test_manifest_allows_template_only_selection(tmp_path: Path) -> None:
    script = tmp_path / "template_only.md"
    script.write_text(
        """## P1 封面
本页类型：封面页
## P2 感谢聆听
本页类型：结束页
""",
        encoding="utf-8",
    )
    manifest, _, _, pages = build_manifest(
        script=script,
        pages_raw="all",
        output_dir=tmp_path / "out",
        project_path=None,
        style_lock=None,
    )
    assert pages == [1, 2]
    assert manifest["requested_pages"] == [1, 2]
    assert manifest["content_page_numbers"] == []
    assert manifest["pairs"] == []
```

- [ ] **Step 3: Run the tests and confirm the current behavior fails**

Run:

```powershell
pytest tests/test_dual_image_overlay_pair_manifest.py -q
```

Expected: the new assertions fail because current code creates image pairs for template pages and has no `skipped_pages`.

- [ ] **Step 4: Port the canonical role contract from Stage2**

Add, adapting only naming to current mainline:

```python
TEMPLATE_ONLY_PAGE_ROLES = frozenset({"cover", "agenda", "section", "ending"})


def classify_page_role(page_number: int, title: str, text: str) -> str:
    declared = re.search(r"本页类型\s*[:：]\s*(封面|目录|章节过渡|内容|结束|封底)页", text)
    if declared:
        return {
            "封面": "cover",
            "目录": "agenda",
            "章节过渡": "section",
            "内容": "content",
            "结束": "ending",
            "封底": "ending",
        }[declared.group(1)]
    if page_number == 1 or "封面" in title:
        return "cover"
    if "目录" in title:
        return "agenda"
    if any(marker in title for marker in ("封底", "结束", "感谢", "汇报完毕")):
        return "ending"
    if "章节过渡" in text or re.match(r"第[一二三四五六七八九十]+章", title):
        return "section"
    return "content"
```

In `build_manifest`, resolve every requested role first, compile prompts only for `content_page_numbers`, add explicit skipped records, and iterate only content pages when creating `pairs`:

```python
resolved_roles = {
    page: classify_page_role(page, source_pages[page].title, source_pages[page].text)
    for page in page_numbers
}
content_page_numbers = [
    page for page in page_numbers
    if resolved_roles[page] not in TEMPLATE_ONLY_PAGE_ROLES
]
skipped_pages = [
    {
        "page_number": page,
        "title": source_pages[page].title,
        "page_role": resolved_roles[page],
        "render_mode": "template",
        "status": "skipped",
        "reason": "template_only_page",
        "template": resolved_roles[page],
    }
    for page in page_numbers
    if page not in content_page_numbers
]
```

Do not port Stage2 geometry constants or reduce style choices from 1–9.

- [ ] **Step 5: Make `require_generated` ignore template pages**

Keep its validation over `manifest["pairs"]` only. Add a test showing a generated content image passes even though template pages have no files.

- [ ] **Step 6: Run focused tests**

Run:

```powershell
pytest tests/test_dual_image_overlay_pair_manifest.py tests/test_dual_image_overlay_deliverable_prompt.py -q
```

Expected: PASS.

- [ ] **Step 7: Detect and commit the isolated manifest change**

Run:

```powershell
git add -- scripts/dual_image_overlay/cyberppt_pair_manifest.py tests/test_dual_image_overlay_pair_manifest.py
git commit -m "feat: skip native template pages in image manifest"
```

Expected: staged files are exactly the manifest module and its test; detected flows are limited to pair-manifest/final-script production.

---

### Task 2: Migrate Agenda and Section Brand Templates

**Files:**
- Create: `scripts/dual_image_overlay/rebuild_engine/templates/brands/中电联公共元素_轻量版/02_agenda.svg`
- Create: `scripts/dual_image_overlay/rebuild_engine/templates/brands/中电联公共元素_轻量版/03_section.svg`
- Modify: `scripts/dual_image_overlay/rebuild_engine/templates/brands/中电联公共元素_轻量版/brand_rules.json`
- Create: `tests/test_brand_templates.py`

**Interfaces:**
- Produces: `brand_page_templates.agenda.file == "02_agenda.svg"`
- Produces: `brand_page_templates.section.file == "03_section.svg"`
- Consumes later: `render_brand_template_svg(task: dict, rules: dict) -> str`

- [ ] **Step 1: Add failing brand-registration tests**

Create:

```python
from pathlib import Path

from scripts.dual_image_overlay.rebuild_engine import template_image_ppt_export as exporter


def test_brand_package_registers_all_native_page_templates() -> None:
    rules = exporter.load_brand_rules()
    templates = rules["brand_page_templates"]
    assert {name: record["file"] for name, record in templates.items()} == {
        "cover": "01_cover.svg",
        "agenda": "02_agenda.svg",
        "section": "03_section.svg",
        "ending": "04_ending.svg",
    }
    for record in templates.values():
        assert (exporter.DEFAULT_BRAND_DIR / record["file"]).is_file()
```

- [ ] **Step 2: Run the test and confirm missing agenda/section assets**

Run:

```powershell
pytest tests/test_brand_templates.py::test_brand_package_registers_all_native_page_templates -q
```

Expected: FAIL because agenda and section are not registered.

- [ ] **Step 3: Migrate the verified Stage2 assets without altering their SVG geometry**

Read the two Stage2 SVGs, then add their exact UTF-8 text to the current brand directory with `apply_patch`:

```powershell
Get-Content -Raw -Encoding UTF8 'D:\CyberPPT-Stage2\scripts\dual_image_overlay\rebuild_engine\templates\brands\中电联公共元素_轻量版\02_agenda.svg'
Get-Content -Raw -Encoding UTF8 'D:\CyberPPT-Stage2\scripts\dual_image_overlay\rebuild_engine\templates\brands\中电联公共元素_轻量版\03_section.svg'
```

Use `*** Add File` patches for the two destination paths, preserving every SVG element and placeholder. Verify exact migration with:

```powershell
git diff --no-index -- 'D:\CyberPPT-Stage2\scripts\dual_image_overlay\rebuild_engine\templates\brands\中电联公共元素_轻量版\02_agenda.svg' 'scripts\dual_image_overlay\rebuild_engine\templates\brands\中电联公共元素_轻量版\02_agenda.svg'
git diff --no-index -- 'D:\CyberPPT-Stage2\scripts\dual_image_overlay\rebuild_engine\templates\brands\中电联公共元素_轻量版\03_section.svg' 'scripts\dual_image_overlay\rebuild_engine\templates\brands\中电联公共元素_轻量版\03_section.svg'
```

Expected: both comparisons produce no diff.

Before changing `brand_rules.json`, compare Stage2 and current entries and port only `agenda` and `section` mappings plus their required placeholders. Preserve current-mainline canvas, body region, and existing cover/ending settings.

- [ ] **Step 4: Add asset-content tests**

Add assertions that:

```python
def test_agenda_and_section_templates_have_brand_chrome() -> None:
    agenda = (exporter.DEFAULT_BRAND_DIR / "02_agenda.svg").read_text(encoding="utf-8")
    section = (exporter.DEFAULT_BRAND_DIR / "03_section.svg").read_text(encoding="utf-8")
    assert "logo.png" in agenda
    assert "logo.png" in section
    assert "{{AGENDA_ITEMS}}" in agenda
    assert "{{SECTION_NO}}" in section
    assert "{{SECTION_TITLE}}" in section
```

- [ ] **Step 5: Run brand tests**

Run:

```powershell
pytest tests/test_brand_templates.py -q
```

Expected: PASS for asset registration and required placeholders.

- [ ] **Step 6: Detect and commit the isolated asset migration**

Run:

```powershell
git add -- tests/test_brand_templates.py scripts/dual_image_overlay/rebuild_engine/templates/brands/中电联公共元素_轻量版/02_agenda.svg scripts/dual_image_overlay/rebuild_engine/templates/brands/中电联公共元素_轻量版/03_section.svg scripts/dual_image_overlay/rebuild_engine/templates/brands/中电联公共元素_轻量版/brand_rules.json
git commit -m "feat: add agenda and section brand templates"
```

Expected: LOW risk and no Python execution-flow changes, because this task contains assets, configuration, and tests only.

---

### Task 3: Port Template Role Metadata and Rendering

**Files:**
- Modify: `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py:119-321`
- Modify: `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py:577-655`
- Modify: `tests/test_brand_templates.py`

**Interfaces:**
- Produces: `page_role(block: PageBlock) -> str`
- Produces: `page_template_name(role: str) -> str | None`
- Produces: `agenda_items_from_pages(pages: dict[int, PageBlock], selected: list[int], final_roles: dict[int, str] | None = None, template_locks: dict[int, dict] | None = None) -> list[dict[str, str]]`
- Produces: `section_metadata_from_pages(pages: dict[int, PageBlock], selected: list[int], final_roles: dict[int, str] | None = None, template_locks: dict[int, dict] | None = None) -> dict[int, dict[str, str]]`
- Produces: `validate_task_role_contract(task: dict) -> None`
- Consumes: four template mappings from Task 2

- [ ] **Step 1: Run impact analysis on every edited function**

Run:

```powershell
```

Expected: callers are concentrated in exporter manifest/render paths. Report risks before editing.

- [ ] **Step 2: Add failing role and metadata tests**

Add:

```python
def test_page_role_recognizes_all_native_template_pages() -> None:
    assert exporter.page_role(exporter.PageBlock(1, "项目封面", "本页类型：封面页")) == "cover"
    assert exporter.page_role(exporter.PageBlock(2, "目录", "本页类型：目录页")) == "agenda"
    assert exporter.page_role(exporter.PageBlock(3, "第一章 工作背景", "本页类型：章节过渡页")) == "section"
    assert exporter.page_role(exporter.PageBlock(4, "核心方案", "本页类型：内容页")) == "content"
    assert exporter.page_role(exporter.PageBlock(5, "感谢聆听", "本页类型：结束页")) == "ending"


def test_section_metadata_uses_ordered_approved_locks() -> None:
    pages = {
        1: exporter.PageBlock(1, "封面", ""),
        3: exporter.PageBlock(3, "第一章 旧标题", ""),
        6: exporter.PageBlock(6, "第二章 旧标题", ""),
    }
    roles = {1: "cover", 3: "section", 6: "section"}
    locks = {
        3: {"title": "工作背景", "subtitle": ""},
        6: {"title": "建设方案", "subtitle": "分阶段落地"},
    }
    assert exporter.section_metadata_from_pages(pages, [1, 3, 6], roles, locks) == {
        3: {"label": "01", "title": "工作背景", "subtitle": ""},
        6: {"label": "02", "title": "建设方案", "subtitle": "分阶段落地"},
    }
```

- [ ] **Step 3: Run tests to confirm current cover/ending-only behavior fails**

Run:

```powershell
pytest tests/test_brand_templates.py -q
```

Expected: FAIL on agenda/section recognition and metadata helpers.

- [ ] **Step 4: Port Stage2 role, template-name, agenda, section, and task-contract helpers**

Use canonical `content` consistently in current mainline:

```python
def page_template_name(role: str) -> str | None:
    return role if role in {"cover", "agenda", "section", "ending"} else None
```

`section_metadata_from_pages` must ignore any role-map attempt to turn intrinsic cover, agenda, or ending pages into sections, assign consecutive labels in selected-page order, and use approved lock title/subtitle.

`validate_task_role_contract` must reject `image_path`, `prompt`, and `size` on template tasks, and require approved image fields on content tasks.

- [ ] **Step 5: Extend `render_brand_template_svg`**

Port the Stage2 substitutions:

```python
if template_name == "agenda":
    svg = svg.replace("{{AGENDA_ITEMS}}", agenda_items_svg(task.get("agenda_items", [])))
elif template_name == "section":
    replacements = {
        "{{SECTION_NO}}": str(task.get("section_no", "")),
        "{{SECTION_TITLE}}": str(task.get("section_title", "")),
        "{{SECTION_SUBTITLE}}": str(task.get("section_subtitle", "")),
    }
    for placeholder, value in replacements.items():
        svg = svg.replace(placeholder, xml_escape(value))
```

After all substitutions, fail if `re.search(r"\{\{[^}]+\}\}", svg)` finds a placeholder.

- [ ] **Step 6: Add rendering tests**

Render agenda and section tasks and assert:

```python
assert "01" in agenda_svg and "工作背景" in agenda_svg
assert "02" in section_svg and "建设方案" in section_svg
assert "{{" not in agenda_svg
assert "{{" not in section_svg
```

Also port Stage2 tests for empty agenda copy, section subtitle omission, cover protocol-field filtering, and logo/brand-bar presence.

- [ ] **Step 7: Run focused tests**

Run:

```powershell
pytest tests/test_brand_templates.py -q
```

Expected: PASS.

- [ ] **Step 8: Detect and commit**

Run:

```powershell
git add -- scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py tests/test_brand_templates.py
git commit -m "feat: render all native template page roles"
```

Expected: changes affect exporter role classification and brand-template rendering only.

---

### Task 4: Make Project Production Consume Approved Full Images

**Files:**
- Modify: `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py:436-655`
- Modify: `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py:657-806`
- Create: `tests/test_template_image_ppt_production.py`

**Interfaces:**
- Extends: `build_manifest(script_path: Path, page_numbers: list[int] | None = None, pages: dict[int, PageBlock] | None = None, output_dir: Path | None = None, *, selected_pages: list[int] | None = None, image_style_name: str | None = None, speaker_notes_manifest: Path | None = None, template_text_lock: Path | None = None, page_image_manifest: Path | None = None, visual_style_lock: Path | None = None, project_production: bool = False) -> dict`
- Produces: ordered exporter tasks with `render_mode` equal to `brand-template` or `content-image`
- Produces: `load_approved_full_images(path: Path, pages: list[int]) -> dict[int, Path]`
- Produces: `load_project_page_roles(path: Path) -> dict[int, str]`

- [ ] **Step 1: Run impact analysis**

Run:

```powershell
```


- [ ] **Step 2: Write failing approved-input tests**

Create a fixture that writes:

```python
page_image_pairs = {
    "requested_pages": [1, 2, 3, 4, 5],
    "content_page_numbers": [4],
    "skipped_pages": [
        {"page_number": 1, "page_role": "cover", "status": "skipped"},
        {"page_number": 2, "page_role": "agenda", "status": "skipped"},
        {"page_number": 3, "page_role": "section", "status": "skipped"},
        {"page_number": 5, "page_role": "ending", "status": "skipped"},
    ],
    "pairs": [{
        "page_number": 4,
        "page_role": "content",
        "full": {"path": str(full_image), "status": "Generated"},
    }],
}
```

Assert the project-production manifest contains five ordered tasks, template tasks have no prompt/image fields, and page 4 uses `full_image`.

- [ ] **Step 3: Run the test and confirm current code regenerates project prompts**

Run:

```powershell
pytest tests/test_template_image_ppt_production.py -q
```

Expected: FAIL because current exporter does not accept the approved manifest/text-lock/style-lock contract.

- [ ] **Step 4: Port approved-input loaders and exact-page validation from Stage2**

Port the Stage2 implementations with these current-mainline signatures:

- `load_template_text_lock(path: Path, pages: list[int]) -> dict[int, dict]`
- `load_approved_full_images(path: Path, pages: list[int]) -> dict[int, Path]`
- `load_project_page_roles(path: Path) -> dict[int, str]`
- `_assert_exact_page_set(label: str, actual: set[int], expected: list[int]) -> None`
- `_require_exact_page_records(label: str, records: object, pages: list[int], *, page_key: str) -> list[dict]`

Adapt them to accept `full.status in {"Generated", "Approved"}` and to treat `skipped_pages` as the template page set. Require that requested pages match exactly and that skipped pages plus image pages form a complete disjoint partition.

- [ ] **Step 5: Add visual style lock validation**

Extend `build_manifest` with `visual_style_lock`. In project production require it to exist, load it as JSON, and record:

```python
manifest["visual_style_lock"] = str(Path(visual_style_lock).resolve())
manifest["image_style"] = style_payload["style"]
```

Do not call `load_image_style(DEFAULT_STYLE_NAME)` in project production. Non-production preview keeps existing behavior.

- [ ] **Step 6: Build ordered tasks without project-production prompts**

For template roles create only template fields. For content roles:

```python
task.update({
    "render_mode": "content-image",
    "image_path": str(approved_images[number]),
    "size": approved_size,
    "status": "Approved",
})
```

Do not add `prompt` in project production. Preserve speaker-note assignment for every page.

- [ ] **Step 7: Add negative contract tests**

Parameterized tests must reject:

- a prompt on a skipped template page;
- a skipped content page;
- missing page 4 pair;
- an extra page pair;
- a missing full image;
- a non-generated full status;
- a missing visual style lock;
- a role conflict between text lock and image manifest.

- [ ] **Step 8: Run focused tests**

Run:

```powershell
pytest tests/test_template_image_ppt_production.py tests/test_brand_templates.py -q
```

Expected: PASS.

- [ ] **Step 9: Detect and commit**

Run:

```powershell
git add -- scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py tests/test_template_image_ppt_production.py
git commit -m "feat: consume approved images in project production"
```

Expected: affected flows are limited to image-ppt manifest construction and export.

---

### Task 5: Pass the Four Approved Inputs from `final-script-pages`

**Files:**
- Modify: `cyberppt/commands/final_script_pages.py:334-488`
- Modify: `tests/test_final_script_pages.py`

**Interfaces:**
- Changes: `_run_image_ppt_build(*, script: Path, pages_raw: str, output_dir: Path, name: str, template_text_lock: Path, page_image_manifest: Path, visual_style_lock: Path) -> dict[str, Any]`
- Consumes: Task 4 project-production CLI arguments
- Produces: accurate `production_ready` or `production_failed` summary

- [ ] **Step 1: Run impact analysis**

Run:

```powershell
```

Expected: direct impact on final-script CLI/tests and Stage 02 production flow.

- [ ] **Step 2: Extend the existing failing command-propagation test**

Assert the subprocess command contains:

```python
assert "--project-production" in command
assert command[command.index("--template-text-lock") + 1] == str(lock_path)
assert command[command.index("--page-image-manifest") + 1] == str(manifest_path)
assert command[command.index("--visual-style-lock") + 1] == str(style_lock)
```

Also assert `production_readiness` is populated only when the subprocess returns a verified exported PPTX.

- [ ] **Step 3: Run the focused test and confirm failure**

Run:

```powershell
pytest tests/test_final_script_pages.py -q
```

Expected: FAIL because current `_run_image_ppt_build` passes only script, pages, output directory, and name.

- [ ] **Step 4: Extend the production command**

Build:

```python
command = [
    sys.executable, "-m", "cyberppt", "image-ppt", "run",
    "--script", str(script),
    "--pages", pages_raw,
    "--output-dir", str(output_dir),
    "--name", name,
    "--project-production",
    "--template-text-lock", str(template_text_lock),
    "--page-image-manifest", str(page_image_manifest),
    "--visual-style-lock", str(visual_style_lock),
]
```

Pass `lock_path`, `manifest_path`, and `style_lock` from `run_final_script_pages`.

- [ ] **Step 5: Gate `production_ready` on verified artifacts**

After the subprocess succeeds, require the exported PPTX and exporter readiness report to exist and state `passed`. Set:

```python
status = "production_ready"
production_readiness = readiness_payload
```

On failure, write `production_failed` into the run summary before reraising or returning the structured failure according to the existing command contract. Never mark success merely from return code zero.

- [ ] **Step 6: Run focused tests**

Run:

```powershell
pytest tests/test_final_script_pages.py tests/test_production_readiness.py -q
```

Expected: PASS.

- [ ] **Step 7: Detect and commit**

Run:

```powershell
git add -- cyberppt/commands/final_script_pages.py tests/test_final_script_pages.py
git commit -m "feat: pass approved inputs to PPT production"
```

Expected: affected flow is the final-script-pages production call into image-ppt.

---

### Task 6: Add the Complete Ordered-Deck Acceptance Test

**Files:**
- Modify: `tests/test_template_image_ppt_production.py`
- Modify: `tests/test_final_script_pages.py`

**Interfaces:**
- Verifies: one final-script production run across all five canonical roles
- Verifies: native templates and approved full images coexist in one ordered PPTX

- [ ] **Step 1: Add the eight-page acceptance fixture**

Create the ordered script:

```text
1 cover
2 agenda
3 section
4 content
5 content
6 section
7 content
8 ending
```

Create three small valid PNG fixtures for pages 4, 5, and 7; create approved text/style locks and a page image manifest whose skipped pages are 1, 2, 3, 6, and 8.

- [ ] **Step 2: Add pre-export manifest assertions**

Assert:

```python
assert [task["page_number"] for task in manifest["tasks"]] == list(range(1, 9))
assert [task["render_mode"] for task in manifest["tasks"]] == [
    "brand-template", "brand-template", "brand-template",
    "content-image", "content-image", "brand-template",
    "content-image", "brand-template",
]
```

For every template task assert no `prompt` and no `image_path`. For content tasks assert paths match pages 4, 5, and 7 exactly.

- [ ] **Step 3: Export and inspect the PPTX**

Run the exporter through its public project-production command. Reopen the result with the existing PPTX inspection utility or `python-pptx` and assert:

```python
with zipfile.ZipFile(exported_pptx) as archive:
    slide_parts = sorted(
        name for name in archive.namelist()
        if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
    )
assert len(slide_parts) == 8
```

Also assert the exporter readiness JSON reports template pages `[1, 2, 3, 6, 8]`, content pages `[4, 5, 7]`, and `status == "passed"`.

- [ ] **Step 4: Add atomic-publication failure coverage**

Precreate a valid output file, force a missing `03_section.svg` through a temporary brand directory, run export, and assert:

```python
assert final_output.read_bytes() == previous_bytes
assert failure_report["status"] == "production_failed"
```

- [ ] **Step 5: Run the complete focused suite**

Run:

```powershell
pytest tests/test_dual_image_overlay_pair_manifest.py tests/test_brand_templates.py tests/test_template_image_ppt_production.py tests/test_final_script_pages.py tests/test_production_readiness.py -q
```

Expected: PASS.

- [ ] **Step 6: Detect and commit acceptance coverage**

Run:

```powershell
git add -- tests/test_template_image_ppt_production.py tests/test_final_script_pages.py
git commit -m "test: cover complete manifest-driven PPT assembly"
```

Expected: test-only staged change with no new production symbols.

---

### Task 7: Final Regression and Scope Verification

**Files:**
- Verify only; modify production files only if a failing test demonstrates a requirement gap, with fresh impact analysis before each edit.

**Interfaces:**
- Confirms: complete migration meets the approved design without style or legacy-pipeline regressions.

- [ ] **Step 1: Run the full test suite**

Run:

```powershell
pytest -q
```

Expected: PASS with zero failures.

- [ ] **Step 2: Run targeted style and prompt regressions**

Run:

```powershell
pytest tests/test_extended_style_9.py tests/test_visual_grammar.py tests/test_dual_image_overlay_deliverable_prompt.py -q
```

Expected: PASS; style 4 remains unchanged and style 9 remains an explicit extension.

- [ ] **Step 3: Confirm no legacy production path returned**

Run:

```powershell
rg -n "OCR|overlay|background derivation|template-rebuild" cyberppt/commands/final_script_pages.py scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py
```

Expected: no newly introduced execution path; explanatory exclusion text is acceptable.

- [ ] **Step 4: Inspect task-owned diff**

Run:

```powershell
git diff main...HEAD -- scripts/dual_image_overlay/cyberppt_pair_manifest.py scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py cyberppt/commands/final_script_pages.py scripts/dual_image_overlay/rebuild_engine/templates/brands/中电联公共元素_轻量版 tests/test_dual_image_overlay_pair_manifest.py tests/test_brand_templates.py tests/test_template_image_ppt_production.py tests/test_final_script_pages.py
```

Expected: only the approved migration surface and tests appear; no style-4/9 contract changes.


Run:

```powershell
```

Expected: affected processes are confined to pair-manifest creation, final-script production orchestration, and image-ppt assembly. Investigate any unrelated flow before completion.

- [ ] **Step 6: Verify the working tree and commit any test-proven final correction**

Run:

```powershell
git status --short
```

Expected: pre-existing unrelated changes may remain, but no uncommitted task-owned file remains. If a test-proven correction was necessary, stage only its files, rerun staged `detect-changes`, and commit with a message describing that correction.
