from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one patch target, found {count}: {old[:120]!r}")
    write(path, content.replace(old, new, 1))


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


# PageArtifactSpec: capacity is an explicit content-engineering contract, while
# visual budget no longer reacts to dense text.
page = "cyberppt/page_artifact_spec.py"
if "TextCapacityAssessment, assess_text_capacity" not in read(page):
    replace_once(
        page,
        "from cyberppt.text_capacity import assess_text_capacity\n",
        "from cyberppt.text_capacity import TextCapacityAssessment, assess_text_capacity\n",
    )
if "    text_capacity: TextCapacityAssessment | None = None" not in read(page):
    replace_once(
        page,
        "    copy_contract: CopyContractSpec | None = None\n",
        "    copy_contract: CopyContractSpec | None = None\n"
        "    text_capacity: TextCapacityAssessment | None = None\n",
    )

dense_branch = '''    if is_text_dense(visible_text) and resolved != "required":\n        return VisualBudgetSpec(\n            mode="relationship_field_only",\n            max_auxiliary_fragments=0,\n            scope="page",\n            region_local_visuals=False,\n        )\n'''
if dense_branch in read(page):
    replace_once(
        page,
        dense_branch,
        "    # Text density is governed by TextCapacityAssessment before visual planning.\n"
        "    # It must never suppress or choose the page's visual medium/budget.\n",
    )

old_capacity = '''    content_nodes = content_integrity.get("nodes") if isinstance(content_integrity, dict) else None\n    root_nodes = content_integrity.get("root_nodes") if isinstance(content_integrity, dict) else None\n    content_root_count = len(root_nodes) if isinstance(root_nodes, list) else 0\n    if str(handoff_page.get("onscreen_source") or "authored") == "full_prose_fallback":\n        hierarchy_levels = tuple(\n            int(node.get("level") or 1)\n            for node in (content_nodes or [])\n            if isinstance(node, dict)\n        )\n        capacity = assess_text_capacity(\n            visible_text,\n            root_count=content_root_count,\n            hierarchy_levels=hierarchy_levels,\n            canvas=(handoff_canvas[0], handoff_canvas[1]),\n        )\n        if capacity.status == "blocked" or capacity.character_count >= 520:\n            raise ValueError(\n                "STAGE02_FALLBACK_TEXT_CAPACITY_EXCEEDED: the manuscript has no authored "\n                "onscreen text and its verbatim full-prose fallback exceeds "\n                "the current canvas capacity; split the page or provide explicit onscreen text. "\n                f"score={capacity.pressure_score}; characters={capacity.character_count}"\n            )\n'''
new_capacity = '''    content_nodes = content_integrity.get("nodes") if isinstance(content_integrity, dict) else None\n    root_nodes = content_integrity.get("root_nodes") if isinstance(content_integrity, dict) else None\n    content_root_count = len(root_nodes) if isinstance(root_nodes, list) else 0\n    hierarchy_levels = tuple(\n        int(node.get("source_level") or node.get("level") or 1)\n        for node in (content_nodes or [])\n        if isinstance(node, dict)\n    )\n    capacity = assess_text_capacity(\n        visible_text,\n        root_count=content_root_count,\n        hierarchy_levels=hierarchy_levels,\n        canvas=(handoff_canvas[0], handoff_canvas[1]),\n    )\n    if capacity.status == "blocked":\n        raise ValueError(\n            "STAGE02_TEXT_CAPACITY_EXCEEDED: content_action=return_to_stage01; "\n            "revise approved onscreen text before visual-medium resolution. "\n            f"score={capacity.pressure_score}; reasons={','.join(capacity.reasons)}"\n        )\n    if (\n        str(handoff_page.get("onscreen_source") or "authored") == "full_prose_fallback"\n        and capacity.character_count >= 520\n    ):\n        raise ValueError(\n            "STAGE02_FALLBACK_TEXT_CAPACITY_EXCEEDED: content_action=return_to_stage01; "\n            "the manuscript has no authored onscreen text and its verbatim full-prose fallback "\n            "requires Stage 01 content engineering before visual planning. "\n            f"score={capacity.pressure_score}; characters={capacity.character_count}"\n        )\n'''
if old_capacity in read(page):
    replace_once(page, old_capacity, new_capacity)
if "        text_capacity=capacity," not in read(page):
    replace_once(
        page,
        "        copy_contract=copy_contract,\n    )\n",
        "        copy_contract=copy_contract,\n        text_capacity=capacity,\n    )\n",
    )

# Visual Stage: capacity gate runs before _decision_execution_design(), which is
# the first place Visual Medium Resolver v2 can be invoked.
compiler = "cyberppt/visual_stage/compiler.py"
if "from cyberppt.text_capacity import TextCapacityAssessment, assert_text_capacity" not in read(compiler):
    replace_once(
        compiler,
        "from cyberppt.page_artifact_spec import is_text_dense\n",
        "from cyberppt.text_capacity import TextCapacityAssessment, assert_text_capacity\n",
    )

old_budget = '''def _visual_budget(dense_text_page: bool, medium_policy: dict[str, object] | str) -> dict[str, object]:\n    if isinstance(medium_policy, str):\n        medium_policy = resolve_visual_medium_policy(None, scene_policy=medium_policy).to_dict()\n    if dense_text_page:\n        return {\n            "mode": "relationship_field_only",\n            "max_auxiliary_fragments": 0,\n            "scope": "page",\n            "region_local_visuals": False,\n        }\n    preferred = str(medium_policy.get("preferred") or "")\n'''
new_budget = '''def _visual_budget(_dense_text_page: bool, medium_policy: dict[str, object] | str) -> dict[str, object]:\n    """Resolve visual budget from medium policy only.\n\n    The first argument remains for legacy private callers but is intentionally\n    ignored: dense copy is a Stage01 content-engineering concern.\n    """\n    if isinstance(medium_policy, str):\n        medium_policy = resolve_visual_medium_policy(None, scene_policy=medium_policy).to_dict()\n    preferred = str(medium_policy.get("preferred") or "")\n'''
if old_budget in read(compiler):
    replace_once(compiler, old_budget, new_budget)

if "def _stage02_text_capacity(" not in read(compiler):
    marker = "\ndef _build_executable_page(source: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:\n"
    helper = '''\ndef _stage02_text_capacity(source: dict[str, Any], page_id: str) -> TextCapacityAssessment:\n    locked = source.get("locked_text_items")\n    if not isinstance(locked, list) or not locked:\n        _fail(f"{page_id}: visual input has no locked body text")\n    texts = [\n        str(item.get("text") or "")\n        for item in locked\n        if isinstance(item, dict) and str(item.get("text") or "")\n    ]\n    if len(texts) != len(locked):\n        _fail(f"{page_id}: locked body text is invalid")\n    integrity = source.get("content_integrity")\n    integrity = integrity if isinstance(integrity, dict) else {}\n    roots = integrity.get("root_nodes")\n    root_count = len(roots) if isinstance(roots, list) else 0\n    nodes = integrity.get("nodes")\n    hierarchy_levels = tuple(\n        int(node.get("source_level") or node.get("level") or 1)\n        for node in (nodes or [])\n        if isinstance(node, dict)\n    )\n    canvas = source.get("body_image_canvas")\n    canvas = canvas if isinstance(canvas, dict) else {}\n    width = int(canvas.get("width") or 2048)\n    height = int(canvas.get("height") or 1024)\n    try:\n        return assert_text_capacity(\n            texts,\n            root_count=root_count,\n            hierarchy_levels=hierarchy_levels,\n            canvas=(width, height),\n        )\n    except ValueError as exc:\n        _fail(f"{page_id}: {exc}")\n    raise AssertionError("unreachable")\n\n'''
    replace_once(compiler, marker, helper + marker)

if "    capacity_assessment = _stage02_text_capacity(source, page_id)" not in read(compiler):
    replace_once(
        compiler,
        "    focus_policy = _resolve_focus_policy(selected, topology, page_id)\n"
        "    design = _decision_execution_design(source, decision, selected, page_id, focus_policy)\n",
        "    focus_policy = _resolve_focus_policy(selected, topology, page_id)\n"
        "    # Capacity must pass before medium resolution or any visual-budget decision.\n"
        "    capacity_assessment = _stage02_text_capacity(source, page_id)\n"
        "    design = _decision_execution_design(source, decision, selected, page_id, focus_policy)\n",
    )

if "    dense_text_page = is_text_dense(expected_text)" in read(compiler):
    replace_once(
        compiler,
        "    dense_text_page = is_text_dense(expected_text)\n"
        "    scene_policy = str(design[\"scene_policy\"])\n"
        "    medium_policy = dict(design[\"visual_medium_policy\"])\n"
        "    visual_budget = _visual_budget(dense_text_page, medium_policy)\n",
        "    scene_policy = str(design[\"scene_policy\"])\n"
        "    medium_policy = dict(design[\"visual_medium_policy\"])\n"
        "    visual_budget = _visual_budget(False, medium_policy)\n",
    )

if '        "text_capacity": {' not in read(compiler):
    replace_once(
        compiler,
        '        "visual_budget": visual_budget,\n        "expression_contract": expression_contract,\n',
        '        "visual_budget": visual_budget,\n'
        '        "text_capacity": {\n'
        '            "status": capacity_assessment.status,\n'
        '            "content_action": capacity_assessment.content_action,\n'
        '            "pressure_score": capacity_assessment.pressure_score,\n'
        '            "item_count": capacity_assessment.item_count,\n'
        '            "character_count": capacity_assessment.character_count,\n'
        '            "root_count": capacity_assessment.root_count,\n'
        '            "max_hierarchy_level": capacity_assessment.max_hierarchy_level,\n'
        '            "reasons": list(capacity_assessment.reasons),\n'
        '        },\n'
        '        "expression_contract": expression_contract,\n',
    )

# Tests isolate capacity from visual semantics and prove dense text cannot zero
# the visual budget after it has passed the content gate.
test = ROOT / "tests/test_text_capacity_v2.py"
test.write_text(
    '''import pytest\n\nfrom cyberppt.page_artifact_spec import _visual_budget as artifact_visual_budget\nfrom cyberppt.text_capacity import (\n    CONTENT_ACTION_CONTINUE, CONTENT_ACTION_RETURN_STAGE01,\n    assert_text_capacity, assess_text_capacity,\n)\nfrom cyberppt.visual_stage.compiler import (\n    _stage02_text_capacity, _visual_budget as compiler_visual_budget,\n)\n\n\ndef test_passed_capacity_declares_continue_stage02_action():\n    assessment = assess_text_capacity(\n        ["主判断", "支撑事实", "业务结果"],\n        root_count=2, hierarchy_levels=(1, 2, 2), canvas=(2048, 1024),\n    )\n    assert assessment.status == "passed"\n    assert assessment.content_action == CONTENT_ACTION_CONTINUE\n\n\ndef test_blocked_capacity_declares_return_to_stage01_action():\n    texts = ["高密度正文" * 30 for _ in range(30)]\n    assessment = assess_text_capacity(\n        texts, root_count=12, hierarchy_levels=(5,) * 30, canvas=(2048, 1024),\n    )\n    assert assessment.status == "blocked"\n    assert assessment.content_action == CONTENT_ACTION_RETURN_STAGE01\n    with pytest.raises(ValueError, match="content_action=return_to_stage01"):\n        assert_text_capacity(\n            texts, root_count=12, hierarchy_levels=(5,) * 30, canvas=(2048, 1024),\n        )\n\n\ndef test_dense_text_no_longer_forces_zero_visual_budget_in_artifact_spec():\n    dense = tuple("正文" * 30 for _ in range(16))\n    budget = artifact_visual_budget(\n        {}, topology="parallel_set", scene_policy="allowed", visible_text=dense,\n    )\n    assert budget.mode == "integrated_scene"\n    assert budget.max_auxiliary_fragments > 0\n\n\ndef test_dense_flag_no_longer_forces_zero_visual_budget_in_visual_compiler():\n    budget = compiler_visual_budget(\n        True,\n        {"preferred": "business_scene", "scene_policy": "allowed"},\n    )\n    assert budget["mode"] == "integrated_scene"\n    assert budget["max_auxiliary_fragments"] > 0\n\n\ndef test_visual_stage_capacity_gate_blocks_before_visual_planning():\n    source = {\n        "locked_text_items": [\n            {"text_id": f"T{i}", "text": "高密度正文" * 30}\n            for i in range(30)\n        ],\n        "content_integrity": {\n            "root_nodes": [f"R{i}" for i in range(12)],\n            "nodes": [{"source_level": 5} for _ in range(30)],\n        },\n        "body_image_canvas": {"width": 2048, "height": 1024},\n    }\n    with pytest.raises(ValueError, match="return_to_stage01"):\n        _stage02_text_capacity(source, "P09")\n''',
    encoding="utf-8", newline="\n",
)

run(
    "python", "-m", "pytest", "-q",
    "tests/test_text_capacity_v2.py",
    "tests/test_visual_medium_policy.py",
    "tests/test_visual_medium_resolver_v2.py",
    "tests/test_region_graph_composition_strategy.py",
)

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", page, compiler, "tests/test_text_capacity_v2.py")
if run("git", "diff", "--cached", "--quiet", check=False).returncode != 0:
    run("git", "commit", "-m", "stage2-v3: separate text capacity from visual planning")
    run("git", "push", "origin", "HEAD:feature/stage2-artifact-contract-v3")
