# Stage 02 Production Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Stage 02 from a blueprint/image-pair preparation step into a production PPTX build pipeline that consumes source capture, semantic binding, workspace, text fitting, visual registry, render comparison, and QA gates in one auditable run.

**Architecture:** Keep `final-script-pages` as the user-facing stage entrypoint, but add an explicit `--production-build` mode that orchestrates the existing rebuild/QA tools and fails closed when any required tool is not consumed. Add one focused semantic binding module that derives `semantic_plan`-equivalent containers and text bindings from script truth, OCR boxes, scene graph, source capture, and visual registry evidence. Add a production readiness report that records every tool's input, output artifact, and pass/fail state.

**Tech Stack:** Python 3.11+, pytest, existing CyberPPT CLI, existing dual-image overlay modules, PowerPoint generation via existing Node/Python render stack.

## Global Constraints

- Do not make hand-authored `semantic_plans/` mandatory for production.
- Semantic binding is mandatory for production and may be generated automatically or supplied explicitly.
- Stage 02 `production_ready` requires every required tool to report `ran: true` and an artifact path.
- If any text item has no semantic container/work slot, Stage 02 must fail before PPTX is marked production ready.
- Validate semantic plans after script-truth reconciliation, not only before reconciliation.
- Remove page-specific hardcoded container IDs from production logic; use role, alias, geometry, and script-section evidence.
- Preserve old blueprint-only behavior, but do not let it report production success.
- Run GitNexus `detect_changes` before committing.

---

## File Structure

- Create `scripts/dual_image_overlay/semantic_binding.py`
  - Owns automatic text-to-container binding and conversion to explicit semantic plan payloads.
- Create `scripts/dual_image_overlay/production_readiness.py`
  - Owns Stage 02 tool-consumption summaries and success/failure status.
- Modify `cyberppt/commands/final_script_pages.py`
  - Adds `production_build` orchestration and records tool consumption in the Stage 02 run summary.
- Modify `cyberppt/cli.py`
  - Adds `--production-build` and `--blueprint-only` CLI switches.
- Modify `scripts/dual_image_overlay/template_rebuild.py`
  - Accepts generated semantic binding/plan inputs and records render compare/readiness artifacts.
- Modify `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`
  - Generates semantic binding when no explicit semantic plan exists and validates after reconciliation.
- Modify `scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py`
  - Replaces hardcoded `application_N` and `governance_N` assumptions with alias-aware reconciliation.
- Modify `scripts/dual_image_overlay/qa_registry.py`
  - Adds strict rules for semantic binding, workspace assignment, text fitting, and render compare consumption.
- Modify `scripts/dual_image_overlay/default_quality_rules.json`, `preflight_quality_rules.json`, `build_quality_rules.json`, `postflight_quality_rules.json`
  - Adds Stage 02 production gates.
- Test `tests/test_semantic_binding.py`
- Test `tests/test_production_readiness.py`
- Test `tests/test_final_script_pages.py`
- Test `tests/test_dual_image_overlay_template_rebuild.py`
- Test `tests/test_dual_image_overlay_qa_registry.py`

---

### Task 1: Semantic Binding Component

**Files:**
- Create: `scripts/dual_image_overlay/semantic_binding.py`
- Test: `tests/test_semantic_binding.py`

**Interfaces:**
- Produces:
  - `build_semantic_binding(*, page_number: int, script_sections: dict, ocr_items: list[dict], scene_graph: dict | None, source_capture_page: dict | None, visual_registry: dict | None) -> dict`
  - `semantic_binding_to_plan(binding: dict) -> dict`
- Consumes:
  - OCR text boxes with `text` and `bbox`
  - scene graph visual/text nodes
  - source capture page objects
  - optional visual registry elements

- [ ] **Step 1: Write failing tests for geometry-based text binding**

Add to `tests/test_semantic_binding.py`:

```python
from scripts.dual_image_overlay.semantic_binding import build_semantic_binding, semantic_binding_to_plan


def test_builds_binding_from_ocr_boxes_and_scene_graph_containers():
    scene_graph = {
        "visual_nodes": [
            {
                "node_id": "left_card",
                "element_type": "container",
                "semantic_role": "source_card",
                "bbox": [0, 0, 200, 100],
            },
            {
                "node_id": "right_card",
                "element_type": "container",
                "semantic_role": "application_card",
                "bbox": [300, 0, 500, 100],
                "aliases": ["application_1"],
            },
        ]
    }
    ocr_items = [
        {"text": "企业与业务数据", "bbox": [20, 20, 160, 50]},
        {"text": "企业应用", "bbox": [320, 20, 460, 50]},
    ]

    binding = build_semantic_binding(
        page_number=6,
        script_sections={},
        ocr_items=ocr_items,
        scene_graph=scene_graph,
        source_capture_page=None,
        visual_registry=None,
    )

    assert binding["schema"] == "cyberppt.semantic_binding.v1"
    assert binding["page_number"] == 6
    assert binding["checks"]["unassigned_text_count"] == 0
    assert {item["container_id"] for item in binding["items"]} == {"left_card", "right_card"}

    plan = semantic_binding_to_plan(binding)
    assert plan["schema"] == "cyberppt.explicit_semantic_plan.v1"
    assert len(plan["containers"]) == 2
    assert len(plan["items"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_semantic_binding.py::test_builds_binding_from_ocr_boxes_and_scene_graph_containers -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.dual_image_overlay.semantic_binding'`.

- [ ] **Step 3: Implement minimal semantic binding**

Create `scripts/dual_image_overlay/semantic_binding.py`:

```python
from __future__ import annotations

from typing import Any


CANVAS = {"width": 1280, "height": 720}


def _rect(value: Any) -> list[float] | None:
    if isinstance(value, list) and len(value) == 4:
        return [float(item) for item in value]
    if isinstance(value, dict):
        x = float(value.get("x", 0) or 0)
        y = float(value.get("y", 0) or 0)
        w = float(value.get("w", value.get("width", 0)) or 0)
        h = float(value.get("h", value.get("height", 0)) or 0)
        if w > 0 and h > 0:
            return [x, y, x + w, y + h]
    return None


def _center(bbox: list[float]) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _contains(container: list[float], point: tuple[float, float]) -> bool:
    return container[0] <= point[0] <= container[2] and container[1] <= point[1] <= container[3]


def _container_nodes(scene_graph: dict[str, Any] | None) -> list[dict[str, Any]]:
    nodes = []
    if not isinstance(scene_graph, dict):
        return nodes
    for index, node in enumerate(scene_graph.get("visual_nodes", []), start=1):
        if not isinstance(node, dict):
            continue
        bbox = _rect(node.get("bbox") or node.get("blueprint_bbox_px") or node.get("render_bbox_px"))
        if bbox is None:
            continue
        element_type = str(node.get("element_type") or node.get("node_type") or "")
        role = str(node.get("semantic_role") or node.get("role") or element_type or "container")
        if element_type != "container" and "card" not in role and "cell" not in role and "segment" not in role:
            continue
        node_id = str(node.get("node_id") or node.get("element_id") or f"container_{index:03d}")
        nodes.append(
            {
                "id": node_id,
                "role": role,
                "bbox": bbox,
                "text_safe_bbox": bbox,
                "aliases": [str(item) for item in node.get("aliases", []) if item],
                "source": {"kind": "scene_graph"},
                "confidence": 0.8,
            }
        )
    return nodes


def build_semantic_binding(
    *,
    page_number: int,
    script_sections: dict[str, Any],
    ocr_items: list[dict[str, Any]],
    scene_graph: dict[str, Any] | None,
    source_capture_page: dict[str, Any] | None,
    visual_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    containers = _container_nodes(scene_graph)
    items = []
    unassigned = []
    for index, item in enumerate(ocr_items, start=1):
        bbox = _rect(item.get("bbox") or item.get("blueprint_bbox_px"))
        text = str(item.get("text") or item.get("display_text") or "").strip()
        if not text or bbox is None:
            continue
        point = _center(bbox)
        container = next((candidate for candidate in containers if _contains(candidate["bbox"], point)), None)
        if container is None:
            unassigned.append({"text": text, "bbox": bbox})
            continue
        items.append(
            {
                "id": f"text_{index:03d}",
                "container_id": container["id"],
                "display_text": text,
                "source_text": text,
                "role": f"{container['role']}_text",
                "bbox": bbox,
                "word_wrap": True,
                "source": {"kind": "ocr_locator"},
                "confidence": 0.75,
            }
        )
    return {
        "schema": "cyberppt.semantic_binding.v1",
        "page_number": page_number,
        "image_size": CANVAS,
        "inputs": {
            "script_sections": bool(script_sections),
            "ocr_items": len(ocr_items),
            "scene_graph": bool(scene_graph),
            "source_capture_page": bool(source_capture_page),
            "visual_registry": bool(visual_registry),
        },
        "containers": containers,
        "items": items,
        "unassigned_text": unassigned,
        "checks": {
            "container_count": len(containers),
            "item_count": len(items),
            "unassigned_text_count": len(unassigned),
        },
    }


def semantic_binding_to_plan(binding: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "cyberppt.explicit_semantic_plan.v1",
        "page_number": binding.get("page_number"),
        "image_size": binding.get("image_size", CANVAS),
        "inputs": {
            "source_capture": bool(binding.get("inputs", {}).get("source_capture_page")),
            "visual_element_registry": bool(binding.get("inputs", {}).get("visual_registry")),
            "script_truth": bool(binding.get("inputs", {}).get("script_sections")),
            "geometry_truth": "semantic_binding",
        },
        "geometry_truth": "semantic_containers",
        "text_truth": "script_truth_plus_ocr_locator",
        "containers": binding.get("containers", []),
        "items": binding.get("items", []),
    }
```

- [ ] **Step 4: Run tests**

Run:

```bash
python3 -m pytest tests/test_semantic_binding.py -q
```

Expected: PASS.

- [ ] **Step 5: Add alias test for governance/safety**

Append:

```python
def test_binding_preserves_aliases_for_governance_safety_strip():
    scene_graph = {
        "visual_nodes": [
            {
                "node_id": "safety_1",
                "element_type": "container",
                "semantic_role": "governance_step",
                "bbox": [1174, 160, 1260, 199],
                "aliases": ["governance_1"],
            }
        ]
    }
    binding = build_semantic_binding(
        page_number=6,
        script_sections={},
        ocr_items=[{"text": "分类分级", "bbox": [1182, 166, 1252, 193]}],
        scene_graph=scene_graph,
        source_capture_page=None,
        visual_registry=None,
    )
    container = binding["containers"][0]
    assert container["id"] == "safety_1"
    assert "governance_1" in container["aliases"]
    assert binding["items"][0]["container_id"] == "safety_1"
```

- [ ] **Step 6: Run targeted tests**

Run:

```bash
python3 -m pytest tests/test_semantic_binding.py -q
```

Expected: PASS.

---

### Task 2: Alias-Aware Script Truth Reconciliation

**Files:**
- Modify: `scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py`
- Test: `tests/test_dual_image_overlay_semantic_plan.py`

**Interfaces:**
- Consumes: semantic plan containers with optional `aliases: list[str]`
- Produces: reconciled plan where every item `container_id` points to an existing container id

- [ ] **Step 1: Write failing test for alias-aware reconciliation**

Add to `tests/test_dual_image_overlay_semantic_plan.py`:

```python
def test_reconcile_uses_container_alias_for_governance_ids(tmp_path: Path) -> None:
    script = tmp_path / "script.md"
    script.write_text(
        "\n".join(
            [
                "## 第6页：总体架构",
                "### 右侧竖条：安全合规",
                "- 分类分级",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    plan = {
        "schema": "cyberppt.explicit_semantic_plan.v1",
        "page_number": 6,
        "image_size": {"width": 1280, "height": 720},
        "inputs": {"script_truth": str(script), "geometry_truth": "semantic_containers"},
        "geometry_truth": "semantic_containers",
        "text_truth": "script_truth",
        "containers": [
            {
                "id": "safety_1",
                "role": "governance_step",
                "bbox": [1174, 160, 1260, 199],
                "text_safe_bbox": [1182, 166, 1252, 193],
                "aliases": ["governance_1"],
            }
        ],
        "items": [],
    }

    reconciled = reconcile_semantic_plan_with_script_truth(plan, script, 6)

    assert reconciled["items"][0]["container_id"] == "safety_1"
    report = validate_explicit_semantic_plan(reconciled)
    assert report["valid"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_semantic_plan.py::DualImageOverlaySemanticPlanTests::test_reconcile_uses_container_alias_for_governance_ids -q
```

Expected: FAIL because reconciliation appends `container_id: governance_1`.

- [ ] **Step 3: Implement alias-aware resolution**

In `scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py`, update `reconcile_semantic_plan_with_script_truth` by adding a resolver before `replace_item_text`:

```python
    def resolve_container_id(requested_id: str) -> str:
        for container in reconciled.get("containers", []):
            if not isinstance(container, dict):
                continue
            container_id = str(container.get("id") or "")
            aliases = [str(item) for item in container.get("aliases", []) if item]
            if container_id == requested_id or requested_id in aliases:
                return container_id
        return requested_id
```

Then change the first line of `replace_item_text`:

```python
        container_id = resolve_container_id(container_id)
```

- [ ] **Step 4: Run targeted semantic plan tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_semantic_plan.py -q
```

Expected: PASS.

---

### Task 3: Production Readiness Report

**Files:**
- Create: `scripts/dual_image_overlay/production_readiness.py`
- Test: `tests/test_production_readiness.py`

**Interfaces:**
- Produces:
  - `build_production_readiness(*, stage: str, artifacts: dict[str, str | None], reports: dict[str, dict]) -> dict`
- Consumes artifact paths and report payloads from Stage 02 orchestration

- [ ] **Step 1: Write failing readiness tests**

Create `tests/test_production_readiness.py`:

```python
from scripts.dual_image_overlay.production_readiness import build_production_readiness


def test_production_readiness_requires_all_required_tools():
    readiness = build_production_readiness(
        stage="02-production-build",
        artifacts={
            "source_capture": "/tmp/source_capture.json",
            "semantic_binding": None,
            "semantic_plan": "/tmp/semantic_plan.json",
            "container_workspace": "/tmp/container_workspace.json",
            "workspace_assignment": "/tmp/workspace_assignment.json",
            "office_textbox_fit": "/tmp/office_textbox_fit.json",
            "editable_pptx": "/tmp/out.pptx",
            "render_compare": "/tmp/render_compare.json",
            "qa_registry": "/tmp/page_quality_report.json",
        },
        reports={},
    )

    assert readiness["status"] == "production_rework_required"
    assert readiness["tool_consumption"]["semantic_binding"]["ran"] is False
    assert readiness["checks"]["all_required_tools_consumed"] is False


def test_production_readiness_passes_when_all_required_tools_have_artifacts():
    artifacts = {
        "source_capture": "/tmp/source_capture.json",
        "semantic_binding": "/tmp/semantic_binding.json",
        "semantic_plan": "/tmp/semantic_plan.json",
        "scene_graph": "/tmp/scene_graph.json",
        "visual_registry": "/tmp/visual_registry",
        "container_workspace": "/tmp/container_workspace.json",
        "workspace_assignment": "/tmp/workspace_assignment.json",
        "office_textbox_fit": "/tmp/office_textbox_fit.json",
        "editable_pptx": "/tmp/out.pptx",
        "render_compare": "/tmp/render_compare.json",
        "qa_registry": "/tmp/page_quality_report.json",
    }

    readiness = build_production_readiness(stage="02-production-build", artifacts=artifacts, reports={})

    assert readiness["status"] == "production_ready"
    assert readiness["checks"]["all_required_tools_consumed"] is True
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_production_readiness.py -q
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement readiness module**

Create `scripts/dual_image_overlay/production_readiness.py`:

```python
from __future__ import annotations

from typing import Any


REQUIRED_TOOLS = (
    "source_capture",
    "semantic_binding",
    "semantic_plan",
    "scene_graph",
    "visual_registry",
    "container_workspace",
    "workspace_assignment",
    "office_textbox_fit",
    "editable_pptx",
    "render_compare",
    "qa_registry",
)


def build_production_readiness(
    *,
    stage: str,
    artifacts: dict[str, str | None],
    reports: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    tool_consumption = {}
    for name in REQUIRED_TOOLS:
        artifact = artifacts.get(name)
        tool_consumption[name] = {
            "ran": bool(artifact),
            "artifact": artifact,
        }
    all_consumed = all(item["ran"] for item in tool_consumption.values())
    blocking = [
        {"tool": name, "code": "tool_not_consumed"}
        for name, item in tool_consumption.items()
        if not item["ran"]
    ]
    return {
        "schema": "cyberppt.stage02.production_readiness.v1",
        "stage": stage,
        "status": "production_ready" if all_consumed else "production_rework_required",
        "valid": all_consumed,
        "checks": {
            "all_required_tools_consumed": all_consumed,
            "blocking_count": len(blocking),
        },
        "tool_consumption": tool_consumption,
        "blocking_errors": blocking,
        "reports": reports,
    }
```

- [ ] **Step 4: Run readiness tests**

Run:

```bash
python3 -m pytest tests/test_production_readiness.py -q
```

Expected: PASS.

---

### Task 4: Stage 02 CLI Mode and Orchestration Contract

**Files:**
- Modify: `cyberppt/cli.py`
- Modify: `cyberppt/commands/final_script_pages.py`
- Test: `tests/test_final_script_pages.py`

**Interfaces:**
- Produces: Stage 02 run summary with `stage: "02-production-build"` and `tool_consumption`
- Consumes: existing `template-rebuild` command as subprocess

- [ ] **Step 1: Write failing CLI orchestration test**

Add to `tests/test_final_script_pages.py`:

```python
def test_production_build_records_required_tool_consumption(tmp_path: Path) -> None:
    from cyberppt.commands.final_script_pages import final_script_pages

    project = tmp_path / "project"
    script = project / "source" / "script.md"
    style_lock = project / "workbench" / "locks" / "visual_style_lock.json"
    script.parent.mkdir(parents=True)
    style_lock.parent.mkdir(parents=True)
    script.write_text("## 第1页：测试\n正文", encoding="utf-8")
    style_lock.write_text('{"style_id": 4, "name": "test"}\n', encoding="utf-8")

    summary = final_script_pages(
        project=project,
        script=script,
        pages_raw="1",
        style_lock=style_lock,
        require_images=False,
        run_rebuild=False,
        production_build=True,
    )

    assert summary["stage"] == "02-production-build"
    assert "tool_consumption" in summary
    assert summary["status"] == "production_rework_required"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m pytest tests/test_final_script_pages.py::FinalScriptPagesTests::test_production_build_records_required_tool_consumption -q
```

Expected: FAIL because `final_script_pages()` has no `production_build` argument.

- [ ] **Step 3: Add CLI switch**

In `cyberppt/cli.py`, add:

```python
    final_script_pages_parser.add_argument(
        "--production-build",
        action="store_true",
        help="Run Stage 02 as a production PPTX build with all required tool gates.",
    )
    final_script_pages_parser.add_argument(
        "--blueprint-only",
        action="store_true",
        help="Only create image prompts and page_image_pairs.json; never report production_ready.",
    )
```

Pass `production_build=args.production_build` through `_final_script_pages_command`.

- [ ] **Step 4: Extend `final_script_pages` signature and summary**

In `cyberppt/commands/final_script_pages.py`, add `production_build: bool = False` to `final_script_pages(...)`.

Import:

```python
from scripts.dual_image_overlay.production_readiness import build_production_readiness
```

When `production_build` is true, set:

```python
stage_name = "02-production-build"
readiness = build_production_readiness(
    stage=stage_name,
    artifacts={
        "source_capture": None,
        "semantic_binding": None,
        "semantic_plan": None,
        "scene_graph": None,
        "visual_registry": None,
        "container_workspace": None,
        "workspace_assignment": None,
        "office_textbox_fit": None,
        "editable_pptx": None,
        "render_compare": None,
        "qa_registry": None,
    },
    reports={},
)
```

Add to `run_summary`:

```python
        "stage": stage_name,
        "status": readiness["status"] if production_build else ("ready_for_image_generation" if not require_images else "image_assets_verified"),
        "tool_consumption": readiness["tool_consumption"] if production_build else {},
        "production_readiness": readiness if production_build else None,
```

- [ ] **Step 5: Run targeted tests**

Run:

```bash
python3 -m pytest tests/test_final_script_pages.py::FinalScriptPagesTests::test_production_build_records_required_tool_consumption -q
```

Expected: PASS.

---

### Task 5: Template Rebuild Consumes Generated Semantic Binding

**Files:**
- Modify: `scripts/dual_image_overlay/template_rebuild.py`
- Modify: `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`
- Test: `tests/test_dual_image_overlay_template_rebuild.py`

**Interfaces:**
- Consumes:
  - `semantic_binding_to_plan(binding: dict) -> dict`
- Produces:
  - `analysis/semantic_binding/page_XXX_semantic_binding.json`
  - `analysis/semantic_plan/page_XXX_semantic_plan.json`

- [ ] **Step 1: Write failing template rebuild test**

Add to `tests/test_dual_image_overlay_template_rebuild.py`:

```python
def test_template_rebuild_generates_semantic_binding_when_explicit_plan_missing(self) -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        project = root / "template-project"
        _write_template_project(project)
        _write_scene_graph_gate(project, page_number=2, valid=True)
        manifest = _write_pair_manifest(root, project)

        result = subprocess.run(
            [
                "python3",
                str(ROOT / "scripts/dual_image_overlay/template_rebuild.py"),
                str(manifest),
                "--skip-rebuild",
                "--no-export",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 3, result.stdout + result.stderr
        assert (project / "analysis/semantic_binding/page_002_semantic_binding.json").is_file()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_template_rebuild.py::DualImageOverlayTemplateRebuildTests::test_template_rebuild_generates_semantic_binding_when_explicit_plan_missing -q
```

Expected: FAIL because no semantic binding file is written.

- [ ] **Step 3: Generate binding in rebuild flow**

In `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`, when `explicit_semantic is None`, call `build_semantic_binding(...)` after OCR layout and scene graph are available, then write the binding and derived plan before building boxes.

Use this import:

```python
from scripts.dual_image_overlay.semantic_binding import build_semantic_binding, semantic_binding_to_plan
```

Write files:

```python
semantic_binding_dir = project_path / "analysis" / "semantic_binding"
semantic_binding_dir.mkdir(parents=True, exist_ok=True)
semantic_binding_path = semantic_binding_dir / f"page_{page_number:03d}_semantic_binding.json"
```

Use the existing OCR layout items as `ocr_items`, existing scene graph payload as `scene_graph`, and write:

```python
semantic_binding_path.write_text(
    json.dumps(binding, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
```

- [ ] **Step 4: Run template rebuild tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_template_rebuild.py -q
```

Expected: PASS.

---

### Task 6: Production Tool Consumption from Rebuild Artifacts

**Files:**
- Modify: `cyberppt/commands/final_script_pages.py`
- Modify: `scripts/dual_image_overlay/template_rebuild.py`
- Test: `tests/test_final_script_pages.py`

**Interfaces:**
- Consumes template rebuild readiness artifacts
- Produces Stage 02 summary `tool_consumption` with real paths

- [ ] **Step 1: Write failing test for completed production build consumption**

Add to `tests/test_final_script_pages.py`:

```python
def test_production_build_summary_uses_template_rebuild_artifacts(tmp_path: Path, monkeypatch) -> None:
    from cyberppt.commands.final_script_pages import final_script_pages

    project = tmp_path / "project"
    script = project / "source" / "script.md"
    style_lock = project / "workbench" / "locks" / "visual_style_lock.json"
    analysis = project / "analysis"
    script.parent.mkdir(parents=True)
    style_lock.parent.mkdir(parents=True)
    analysis.mkdir(parents=True)
    script.write_text("## 第1页：测试\n正文", encoding="utf-8")
    style_lock.write_text('{"style_id": 4, "name": "test"}\n', encoding="utf-8")
    for rel in [
        "source_capture.json",
        "semantic_binding/page_001_semantic_binding.json",
        "semantic_plan/page_001_semantic_plan.json",
        "scene_graph/page_001_scene_graph.json",
        "visual_registry/page_001_visual_element_registry.json",
        "container_workspace/container_workspace_index.json",
        "workspace_assignment/workspace_assignment_index.json",
        "office_textbox_fit.json",
        "render_compare/page_001_render_compare.json",
        "page_quality_report.json",
    ]:
        path = analysis / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
    exports = project / "exports"
    exports.mkdir()
    (exports / "out.pptx").write_bytes(b"pptx")

    class Completed:
        returncode = 0

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: Completed())

    summary = final_script_pages(
        project=project,
        script=script,
        pages_raw="1",
        style_lock=style_lock,
        require_images=False,
        run_rebuild=True,
        production_build=True,
    )

    assert summary["status"] == "production_ready"
    assert summary["tool_consumption"]["source_capture"]["ran"] is True
    assert summary["tool_consumption"]["render_compare"]["ran"] is True
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m pytest tests/test_final_script_pages.py::FinalScriptPagesTests::test_production_build_summary_uses_template_rebuild_artifacts -q
```

Expected: FAIL because `tool_consumption` still contains empty paths.

- [ ] **Step 3: Implement artifact discovery**

In `cyberppt/commands/final_script_pages.py`, add:

```python
def _stage02_production_artifacts(project: Path) -> dict[str, str | None]:
    analysis = project / "analysis"
    exports = project / "exports"
    latest_pptx = max(exports.glob("*.pptx"), key=lambda path: path.stat().st_mtime, default=None) if exports.exists() else None
    def first(pattern: str) -> str | None:
        matches = sorted(analysis.glob(pattern))
        return str(matches[0]) if matches else None
    return {
        "source_capture": str(analysis / "source_capture.json") if (analysis / "source_capture.json").is_file() else None,
        "semantic_binding": first("semantic_binding/page_*_semantic_binding.json"),
        "semantic_plan": first("semantic_plan/page_*_semantic_plan.json"),
        "scene_graph": first("scene_graph/page_*_scene_graph.json"),
        "visual_registry": str(analysis / "visual_registry") if (analysis / "visual_registry").exists() else None,
        "container_workspace": str(analysis / "container_workspace/container_workspace_index.json") if (analysis / "container_workspace/container_workspace_index.json").is_file() else None,
        "workspace_assignment": str(analysis / "workspace_assignment/workspace_assignment_index.json") if (analysis / "workspace_assignment/workspace_assignment_index.json").is_file() else None,
        "office_textbox_fit": str(analysis / "office_textbox_fit.json") if (analysis / "office_textbox_fit.json").is_file() else None,
        "editable_pptx": str(latest_pptx) if latest_pptx else None,
        "render_compare": first("render_compare/page_*_render_compare.json") or first("page_*_render_compare.json"),
        "qa_registry": str(analysis / "page_quality_report.json") if (analysis / "page_quality_report.json").is_file() else None,
    }
```

Use this artifact map after rebuild when `production_build` is true.

- [ ] **Step 4: Run final script page tests**

Run:

```bash
python3 -m pytest tests/test_final_script_pages.py -q
```

Expected: PASS.

---

### Task 7: QA Registry Strict Production Rules

**Files:**
- Modify: `scripts/dual_image_overlay/qa_registry.py`
- Modify: `scripts/dual_image_overlay/default_quality_rules.json`
- Test: `tests/test_dual_image_overlay_qa_registry.py`

**Interfaces:**
- Consumes `production_readiness` report
- Produces blocking errors for missing semantic binding, workspace assignment, text fit, or render compare

- [ ] **Step 1: Write failing QA test**

Add to `tests/test_dual_image_overlay_qa_registry.py`:

```python
def test_production_readiness_rule_blocks_missing_tool_consumption(tmp_path: Path) -> None:
    from scripts.dual_image_overlay.qa_registry import write_page_quality_report

    report = write_page_quality_report(
        tmp_path / "page_quality_report.json",
        stage="stage02-production",
        page_number=6,
        project_path=tmp_path,
        artifacts={},
        reports={
            "production_readiness": {
                "schema": "cyberppt.stage02.production_readiness.v1",
                "valid": False,
                "checks": {"all_required_tools_consumed": False},
                "blocking_errors": [{"tool": "semantic_binding", "code": "tool_not_consumed"}],
            }
        },
        rules=[
            {
                "id": "stage02.production_readiness_pass",
                "severity": "error",
                "kind": "production_readiness_required",
                "report": "production_readiness",
            }
        ],
    )

    assert report["valid"] is False
    assert report["blocking_errors"][0]["id"] == "stage02.production_readiness_pass"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_qa_registry.py::test_production_readiness_rule_blocks_missing_tool_consumption -q
```

Expected: FAIL because `production_readiness_required` is unknown.

- [ ] **Step 3: Add QA registry check**

In `scripts/dual_image_overlay/qa_registry.py`, add:

```python
def _check_production_readiness_required(report: Any) -> tuple[bool, dict[str, Any]]:
    if not isinstance(report, dict):
        return False, {"reason": "production_readiness_missing"}
    return bool(report.get("valid")), {
        "schema": report.get("schema"),
        "status": report.get("status"),
        "checks": report.get("checks"),
        "blocking_errors": report.get("blocking_errors", []),
    }
```

In the rule dispatch, add:

```python
    elif kind == "production_readiness_required":
        passed, observed = _check_production_readiness_required(observed)
```

- [ ] **Step 4: Run QA registry tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_qa_registry.py -q
```

Expected: PASS.

---

### Task 8: End-to-End Regression for Page 6 and Page 3

**Files:**
- Test: `tests/test_stage02_production_build_regression.py`

**Interfaces:**
- Consumes production build CLI
- Produces regression proof that Stage 02 does not report success without tool consumption

- [ ] **Step 1: Write regression tests**

Create `tests/test_stage02_production_build_regression.py`:

```python
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_blueprint_only_stage02_never_reports_production_ready(tmp_path: Path) -> None:
    project = tmp_path / "project"
    script = project / "source" / "script.md"
    style_lock = project / "workbench" / "locks" / "visual_style_lock.json"
    script.parent.mkdir(parents=True)
    style_lock.parent.mkdir(parents=True)
    script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")
    style_lock.write_text('{"style_id": 4, "name": "test"}\n', encoding="utf-8")

    result = subprocess.run(
        [
            "python3",
            "-m",
            "cyberppt",
            "final-script-pages",
            str(project),
            "--script",
            str(script),
            "--pages",
            "1",
            "--style-lock",
            str(style_lock),
            "--blueprint-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    run_file = next((project / "workbench/stages/02-blueprint-dual-image").glob("**/*_final_script_pages_run.json"))
    summary = json.loads(run_file.read_text(encoding="utf-8"))
    assert summary["status"] != "production_ready"
    assert summary.get("tool_consumption", {}) == {}
```

- [ ] **Step 2: Run regression test**

Run:

```bash
python3 -m pytest tests/test_stage02_production_build_regression.py -q
```

Expected: PASS after Tasks 4-7 are complete.

- [ ] **Step 3: Run full relevant suite**

Run:

```bash
python3 -m pytest \
  tests/test_semantic_binding.py \
  tests/test_production_readiness.py \
  tests/test_final_script_pages.py \
  tests/test_dual_image_overlay_template_rebuild.py \
  tests/test_dual_image_overlay_qa_registry.py \
  tests/test_stage02_production_build_regression.py -q
```

Expected: PASS.

- [ ] **Step 4: Run GitNexus change detection before commit**

Run:

```bash
git diff --check
```

Expected: no output.

Run GitNexus:

```text
detect_changes(repo="CyberPPT", scope="all", worktree="/Volumes/DOC/CyberPPT")
```

Expected: risk summary reviewed; warn user before commit if HIGH or CRITICAL.

---

## Self-Review

**Spec coverage:** The plan explicitly covers Stage 02 production output, all previously developed tools, semantic binding generation, no mandatory hand-authored `semantic_plans/`, tool consumption evidence, render comparison, QA gates, and regression tests for the failure mode that caused repeated reruns.

**Placeholder scan:** No task uses TBD/TODO/later wording. Each task includes concrete files, interfaces, test snippets, commands, and expected outcomes.

**Type consistency:** `build_semantic_binding`, `semantic_binding_to_plan`, and `build_production_readiness` signatures are consistent across producer and consumer tasks. Tool names match the final `tool_consumption` schema.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-05-stage02-production-build.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session with checkpoint reviews.
