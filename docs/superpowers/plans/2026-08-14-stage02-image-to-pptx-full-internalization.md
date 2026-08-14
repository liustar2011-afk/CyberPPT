# Stage 02 Image-to-PPTX Full Internalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CyberPPT own PPT-Master’s complete image-to-PPTX Quick reconstruction runtime, with CyberPPT Stage 02 used only before and after reconstruction.

**Architecture:** Vendor the image-to-PPTX-specific PPT-Master runtime into a package-local CyberPPT namespace, including its image preparation, SVG quality, local editor and native export dependencies. Add a Stage 02 adapter that creates a runtime project from audited full images and accepts only a reviewed, passing SVG roster before CyberPPT performs its existing delivery assembly.

**Tech Stack:** Python 3.12, Pillow, SVG/XML, OpenXML/PPTX, OfficeCLI, existing Codex reference-image capability, pytest, Graft.

## Global Constraints

- No production import, script invocation, Skill link or test fixture may reference `/Volumes/DOC/ppt-master` after migration.
- The input image must already be `Generated` and pass CyberPPT’s existing full-image typo audit.
- The canonical full-page source is comparison evidence only and must never become a hidden full-slide delivered image.
- Text is native, verbatim and script-bound; OCR supplies locators only.
- Data/identity graphics are exact-source/native-and-verified or block release.
- The acceptance bar is visually equivalent at normal slide size with only a very small number of local human SVG edits allowed; it is not pixel-perfect equality.
- Preserve existing unrelated dirty-worktree changes and stage only paths assigned by each task.

---

## Target File Structure

| Path | Responsibility |
|---|---|
| `scripts/image_to_pptx_runtime/` | CyberPPT-owned import of the image-to-PPTX Quick runtime and all required local dependencies. |
| `scripts/image_to_pptx_runtime/quick.py` | Create/open a reconstruction project, canonical roster, evidence inventory, review state and release boundary. |
| `scripts/image_to_pptx_runtime/stage02_adapter.py` | Map CyberPPT audited manifests into runtime projects and return passing SVG rosters to Stage 02. |
| `scripts/image_to_pptx_runtime/review.py` | Canonical/reference versus recomposed review material and bounded reviewer issue contract. |
| `scripts/image_to_pptx_runtime/svg_editor/` | Local editor copied from PPT-Master, namespaced and project-root confined. |
| `scripts/image_to_pptx_runtime/svg_quality/` | Complete PPT-Master SVG contract checker, namespaced. |
| `scripts/image_to_pptx_runtime/svg_to_pptx/` | Complete native SVG-to-PPTX converter and DrawingML dependencies, namespaced. |
| `.agents/skills/cyberppt-image-to-editable-svg/` | Path-correct full CyberPPT image-to-PPTX Quick workflow. |
| `cyberppt/commands/final_script_pages.py` | Call the local adapter after full-image typo audit and before CyberPPT delivery assembly. |
| `tests/test_image_to_pptx_runtime_*.py` | Unit/integration/regression coverage for the imported runtime and Stage 02 boundary. |

## Task 1: Vendor and namespace the image-to-PPTX runtime

**Files:**
- Create: `scripts/image_to_pptx_runtime/__init__.py`
- Create: `scripts/image_to_pptx_runtime/project_management/`
- Create: `scripts/image_to_pptx_runtime/svg_quality/`
- Create: `scripts/image_to_pptx_runtime/svg_to_pptx/`
- Create: `scripts/image_to_pptx_runtime/svg_editor/`
- Create: `scripts/image_to_pptx_runtime/{slide_roster,analyze_images,image_treat,slice_images,visual_review,svg_authoring_view,pptx_delivery_check}.py`
- Create: `tests/test_image_to_pptx_runtime_imports.py`

**Interfaces:**
- Consumes: only paths inside `scripts/image_to_pptx_runtime/` and Python dependencies already declared by CyberPPT.
- Produces: `runtime_root() -> Path`, `assert_internal_runtime() -> None`, and importable quality/export/editor modules.

- [ ] **Step 1: Write import-isolation tests**

```python
def test_runtime_imports_are_self_contained() -> None:
    import scripts.image_to_pptx_runtime.svg_quality.checker  # noqa: F401
    import scripts.image_to_pptx_runtime.svg_to_pptx.pptx_package.builder  # noqa: F401
    assert assert_internal_runtime() is None

def test_runtime_source_has_no_ppt_master_checkout_reference() -> None:
    offenders = find_forbidden_references(runtime_root(), "/Volumes/DOC/ppt-master")
    assert offenders == []
```

- [ ] **Step 2: Run the test to verify the current runtime is absent**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_image_to_pptx_runtime_imports.py`

Expected: FAIL because `scripts.image_to_pptx_runtime` does not exist.

- [ ] **Step 3: Copy only image-to-PPTX dependencies and rewrite imports**

Copy the required PPT-Master source modules into the target package: project/roster utilities; `analyze_images.py`, `image_treat.py`, `slice_images.py`; `svg_quality/` plus `svg_quality_checker.py`; `svg_editor/`; `svg_authoring_view.py`; `visual_review.py`; `pptx_delivery_check.py`; and the complete `svg_to_pptx/` tree. Rewrite imports such as:

```python
# Before
from svg_to_pptx.drawingml.converter import convert_svg

# After
from scripts.image_to_pptx_runtime.svg_to_pptx.drawingml.converter import convert_svg
```

Add a package-level guard:

```python
def assert_internal_runtime() -> None:
    root = runtime_root()
    for source in root.rglob("*.py"):
        if "/Volumes/DOC/ppt-master" in source.read_text(encoding="utf-8"):
            raise RuntimeError(f"external PPT-Master dependency: {source}")
```

- [ ] **Step 4: Run import and source-isolation tests**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_image_to_pptx_runtime_imports.py`

Expected: PASS.

- [ ] **Step 5: Commit the self-contained runtime import**

```bash
git add scripts/image_to_pptx_runtime tests/test_image_to_pptx_runtime_imports.py
git commit -m "feat(stage02): vendor image-to-pptx runtime"
```

## Task 2: Implement the local Quick reconstruction project and evidence contract

**Files:**
- Create: `scripts/image_to_pptx_runtime/quick.py`
- Create: `scripts/image_to_pptx_runtime/contracts.py`
- Create: `tests/test_image_to_pptx_runtime_quick.py`

**Interfaces:**
- Consumes: ordered `list[tuple[int, Path]]` canonical pages and approved text by page.
- Produces: `QuickProject`, `create_quick_project(...) -> QuickProject`, `write_inventory(...) -> Path`, `release_gate(...) -> dict[str, Any]`.

- [ ] **Step 1: Write failing roster/inventory/gate tests**

```python
def test_quick_project_archives_source_and_records_canonical_roster(tmp_path: Path) -> None:
    project = create_quick_project(tmp_path / "rebuild", pages=[(1, source)], text_by_page={1: ["结论"]})
    assert (project.root / "sources" / source.name).is_file()
    assert project.roster[0].normalized_path.is_file()

def test_release_gate_rejects_hidden_canonical_full_page(tmp_path: Path) -> None:
    report = release_gate(project, svg_files=[svg_using_canonical_source])
    assert report["valid"] is False
    assert report["blocking_errors"][0]["code"] == "canonical_page_embedded"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_image_to_pptx_runtime_quick.py`

Expected: FAIL because the Quick project APIs are not defined.

- [ ] **Step 3: Implement project-local paths and evidence**

```python
@dataclass(frozen=True)
class QuickProject:
    root: Path
    roster: tuple[CanonicalPage, ...]
    text_by_page: Mapping[int, tuple[str, ...]]

def create_quick_project(root: Path, *, pages: list[tuple[int, Path]], text_by_page: Mapping[int, Iterable[str]]) -> QuickProject:
    # Copy originals to sources/, normalize each page once, write one visible
    # inventory per page and never create an external-workspace reference.
    ...
```

The inventory records observed regions, source sufficiency, occlusion,
identity/data verification and z-order. It must not contain hidden approval
receipts or a second Stage 02 script authority.

- [ ] **Step 4: Run Quick project tests**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_image_to_pptx_runtime_quick.py`

Expected: PASS.

- [ ] **Step 5: Commit Quick evidence runtime**

```bash
git add scripts/image_to_pptx_runtime/quick.py scripts/image_to_pptx_runtime/contracts.py tests/test_image_to_pptx_runtime_quick.py
git commit -m "feat(stage02): add internal reconstruction quick project"
```

## Task 3: Port image preparation, review and bounded local correction

**Files:**
- Create: `scripts/image_to_pptx_runtime/review.py`
- Modify: `scripts/image_to_pptx_runtime/svg_editor/server.py`
- Modify: `scripts/image_to_pptx_runtime/visual_review.py`
- Create: `tests/test_image_to_pptx_runtime_review.py`

**Interfaces:**
- Consumes: `QuickProject`, prepared layer records and SVG roster.
- Produces: `build_review(...) -> ReviewReport`, `start_editor(project: QuickProject, port: int | None) -> EditorSession`, `apply_local_edit(...) -> EditReceipt`.

- [ ] **Step 1: Write failing review/editor tests**

```python
def test_review_records_only_local_corrections(tmp_path: Path) -> None:
    report = build_review(project, svg_files=[page_svg], canonical_pages=project.roster)
    receipt = report.record_issue(page=1, category="spacing", scope="local", description="标题右移 2px")
    assert receipt.requires_rebuild is False

def test_review_blocks_whole_page_rebuild_request(tmp_path: Path) -> None:
    receipt = build_review(project, svg_files=[page_svg], canonical_pages=project.roster).record_issue(
        page=1, category="layout", scope="whole_page", description="需要重新设计"
    )
    assert receipt.requires_rebuild is True
```

- [ ] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_image_to_pptx_runtime_review.py`

Expected: FAIL because the review contract has not been defined.

- [ ] **Step 3: Implement review material and constrained editor integration**

Render canonical and recomposed pages into review pairs, write
`analysis/visual-review.json`, and confine editor file reads/writes to
`QuickProject.root / "svg_output"`. The local correction receipt must include
the SVG path, element id, changed properties and timestamp. It must rerun the
imported SVG checker after an edit.

```python
def apply_local_edit(session: EditorSession, *, page: int, element_id: str, props: Mapping[str, str]) -> EditReceipt:
    assert session.project.svg_path(page).is_relative_to(session.project.root)
    receipt = session.apply(page=page, element_id=element_id, props=dict(props))
    quality = check_svg(session.project.svg_path(page), quick_generate=True)
    if not quality.passed:
        raise ValueError("local edit broke SVG quality")
    return receipt
```

- [ ] **Step 4: Run review/editor tests**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_image_to_pptx_runtime_review.py`

Expected: PASS.

- [ ] **Step 5: Commit review and editor boundary**

```bash
git add scripts/image_to_pptx_runtime/review.py scripts/image_to_pptx_runtime/svg_editor scripts/image_to_pptx_runtime/visual_review.py tests/test_image_to_pptx_runtime_review.py
git commit -m "feat(stage02): add image reconstruction review loop"
```

## Task 4: Add the CyberPPT Stage 02 adapter and retire automatic coordinate authoring

**Files:**
- Create: `scripts/image_to_pptx_runtime/stage02_adapter.py`
- Modify: `scripts/image_to_editable_svg/orchestrator.py`
- Modify: `cyberppt/commands/final_script_pages.py`
- Modify: `scripts/image_to_editable_svg/reconstruct.py`
- Create: `tests/test_image_to_pptx_runtime_stage02_adapter.py`
- Modify: `tests/test_final_script_pages.py`

**Interfaces:**
- Consumes: the existing audited full-image manifest and final script.
- Produces: `run_stage02_reconstruction(project, manifest_path, output_dir, requested_pages) -> dict[str, Any]` with `runtime_project`, `svg_roster`, `visual_review`, `editor_session`, and `export_input` artifacts.

- [ ] **Step 1: Write failing Stage 02 adapter tests**

```python
def test_adapter_requires_generated_audited_full_before_runtime(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="passed text audit"):
        run_stage02_reconstruction(project=project, manifest_path=manifest_without_text_audit, output_dir=out, requested_pages=[1])

def test_production_uses_passing_runtime_svg_roster(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(adapter, "complete_reconstruction", lambda **_: passing_runtime_result)
    result = run_final_script_pages(..., production_build=True, production_mode="image-to-editable-svg")
    assert result["artifacts"]["runtime_svg_roster"] == passing_runtime_result["svg_roster"]
```

- [ ] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_image_to_pptx_runtime_stage02_adapter.py tests/test_final_script_pages.py`

Expected: FAIL because production still invokes `author_page_svg` coordinate reconstruction.

- [ ] **Step 3: Implement the adapter and remove the fallback from production**

```python
def run_stage02_reconstruction(*, project: Path, manifest_path: Path, output_dir: Path, requested_pages: list[int]) -> dict[str, Any]:
    manifest = load_and_require_audited_full_manifest(manifest_path)
    runtime = create_quick_project(output_dir / "image_to_pptx_runtime", pages=audited_pages(manifest, requested_pages), text_by_page=script_truth(...))
    result = complete_reconstruction(runtime)
    if not result["release_gate"]["valid"]:
        raise ValueError("image-to-pptx reconstruction requires rework")
    return result
```

Delete the automatic `author_page_svg` OCR/rectangle path from the production
branch. Keep only validators that are directly reused by the imported runtime.
`final_script_pages` must call `run_stage02_reconstruction` and then hand the
accepted SVG roster to CyberPPT assembly.

- [ ] **Step 4: Run adapter and command regressions**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_image_to_pptx_runtime_stage02_adapter.py tests/test_final_script_pages.py tests/test_image_to_editable_svg_orchestrator.py`

Expected: PASS; no production test references the old automatic author.

- [ ] **Step 5: Commit the Stage 02 boundary**

```bash
git add scripts/image_to_pptx_runtime/stage02_adapter.py scripts/image_to_editable_svg/orchestrator.py scripts/image_to_editable_svg/reconstruct.py cyberppt/commands/final_script_pages.py tests/test_image_to_pptx_runtime_stage02_adapter.py tests/test_final_script_pages.py tests/test_image_to_editable_svg_orchestrator.py
git commit -m "feat(stage02): route audited images through internal image-to-pptx"
```

## Task 5: Complete the internal Skill, command interface and migration regression fixture

**Files:**
- Modify: `.agents/skills/cyberppt-image-to-editable-svg/SKILL.md`
- Create: `.agents/skills/cyberppt-image-to-editable-svg/references/{visual-review,svg-quality,svg-editor}.md`
- Modify: `scripts/image_to_pptx_runtime/__main__.py`
- Create: `tests/test_image_to_pptx_runtime_palette09.py`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: internal runtime path and audited image manifest.
- Produces: `python3 -m scripts.image_to_pptx_runtime --project ... --manifest ...` and a Skill whose every local reference resolves under CyberPPT.

- [ ] **Step 1: Write failing portability and palette-09 regression tests**

```python
def test_skill_has_no_external_ppt_master_links() -> None:
    assert "/Volumes/DOC/ppt-master" not in SKILL.read_text(encoding="utf-8")
    assert all((SKILL.parent / relative).is_file() for relative in linked_local_references(SKILL))

def test_palette09_fixture_is_internal_and_native(tmp_path: Path) -> None:
    result = run_stage02_reconstruction(...)
    assert result["release_gate"]["valid"] is True
    assert native_texts(result["svg_roster"][0]) >= {"总体要求", "建设节点", "持续运营评价原则"}
```

- [ ] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_image_to_pptx_runtime_palette09.py tests/test_skill_contract.py`

Expected: FAIL because the internal Skill has incomplete reference coverage and no internal regression fixture.

- [ ] **Step 3: Complete workflow instructions and CLI**

Port the profile’s Quick-only routing, source inventory, preparation, manual
SVG authoring, review/editor, final SVG check and postflight instructions with
CyberPPT-local commands. Do not instruct an agent to call external PPT-Master.
CLI JSON output must name the runtime project, review report, edit receipt
directory, SVG roster, PPTX and delivery gate.

- [ ] **Step 4: Run fixture and Skill tests**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_image_to_pptx_runtime_palette09.py tests/test_skill_contract.py`

Expected: PASS.

- [ ] **Step 5: Commit complete local workflow**

```bash
git add .agents/skills/cyberppt-image-to-editable-svg scripts/image_to_pptx_runtime/__main__.py tests/test_image_to_pptx_runtime_palette09.py tests/test_skill_contract.py
git commit -m "feat(stage02): complete internal image-to-pptx workflow"
```

## Task 6: Run end-to-end validation and close migration

**Files:**
- Modify: `tests/test_image_to_pptx_runtime_stage02_adapter.py`
- Create: `tests/test_image_to_pptx_runtime_e2e.py`
- Modify: `docs/superpowers/specs/2026-08-14-stage02-image-to-pptx-full-internalization-design.md`

**Interfaces:**
- Consumes: two audited full-image fixtures and the new production command.
- Produces: a two-page runtime project, review evidence, accepted SVG roster and CyberPPT-assembled editable PPTX.

- [ ] **Step 1: Write the two-page end-to-end test**

```python
def test_two_audited_pages_produce_reviewed_editable_pptx(tmp_path: Path) -> None:
    result = run_stage02_reconstruction(project=project, manifest_path=two_page_manifest, output_dir=tmp_path / "out", requested_pages=[1, 2])
    assert result["release_gate"]["valid"] is True
    assert len(result["svg_roster"]) == 2
    assert Path(result["artifacts"]["exported_pptx"]).is_file()
    assert officecli_validate(result["artifacts"]["exported_pptx"]) == []
```

- [ ] **Step 2: Run end-to-end test and fix only production defects**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_image_to_pptx_runtime_e2e.py`

Expected: PASS.

- [ ] **Step 3: Run the full focused verification**

Run:

```bash
PYTHONPATH=. python3 -m pytest -q \
  tests/test_image_to_pptx_runtime_imports.py \
  tests/test_image_to_pptx_runtime_quick.py \
  tests/test_image_to_pptx_runtime_review.py \
  tests/test_image_to_pptx_runtime_stage02_adapter.py \
  tests/test_image_to_pptx_runtime_palette09.py \
  tests/test_image_to_pptx_runtime_e2e.py \
  tests/test_final_script_pages.py \
  tests/test_skill_contract.py
npx --no-install graft build
npx --no-install graft check
```

Expected: all selected tests pass and `graph check: OK`.

- [ ] **Step 4: Validate the produced PPTX**

Run: `officecli validate <exported-pptx>` and `officecli view <exported-pptx> text`.

Expected: OpenXML validation passes and all approved native text is present.

- [ ] **Step 5: Commit migration closure**

```bash
git add tests/test_image_to_pptx_runtime_stage02_adapter.py tests/test_image_to_pptx_runtime_e2e.py docs/superpowers/specs/2026-08-14-stage02-image-to-pptx-full-internalization-design.md
git commit -m "test(stage02): verify internal image-to-pptx delivery"
```

## Plan Self-Review

- Spec coverage: Tasks 1–3 import the complete image-to-PPTX runtime, preparation, quality, review and editor; Task 4 owns the distinct CyberPPT Stage 02 adapter; Task 5 completes local workflow/CLI; Task 6 verifies the complete delivery chain.
- Placeholder scan: no `TODO`, `TBD`, deferred behavior or undefined external runtime dependency appears in the plan.
- Type consistency: `QuickProject`, `run_stage02_reconstruction`, `ReviewReport`, `EditorSession` and `EditReceipt` are introduced before their dependent tasks and retain the same names throughout.
