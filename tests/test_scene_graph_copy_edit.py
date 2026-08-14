from scripts.dual_image_overlay.scene_graph.copy_edit import (
    edit_scene_graph_copy,
    edit_text_node,
    validate_semantic_safe_revision,
)
from scripts.dual_image_overlay.scene_graph.schema import PageSceneGraph, TextNode


def _node(text: str) -> TextNode:
    return TextNode(
        node_id="text_1",
        text=text,
        truth_source={"kind": "script", "authority": "text_truth"},
        semantic_role="body",
    )


def test_rejects_revision_that_changes_number_or_negation():
    gate = validate_semantic_safe_revision(
        "2027年前不得删除，覆盖率至少85%",
        "2028年前可以删除，覆盖率达到90%",
    )

    assert gate["valid"] is False
    assert gate["issues"][0]["code"] == "protected_fact_changed"


def test_accepts_conservative_cleanup_and_records_source():
    updated, report = edit_text_node(_node("目标  ： 保持稳定\n目标  ： 保持稳定"))

    assert updated.text == "目标：保持稳定"
    assert report["accepted"] is True
    assert report["source_text"] == "目标  ： 保持稳定\n目标  ： 保持稳定"
    assert "remove_duplicate_lines" in report["operations"]


def test_rejected_proposed_revision_falls_back_to_script_truth():
    updated, report = edit_text_node(
        _node("覆盖率至少85%"),
        proposed_text="覆盖率达到90%",
    )

    assert updated.text == "覆盖率至少85%"
    assert report["accepted"] is False
    assert report["final_text"] == "覆盖率至少85%"


def test_scene_graph_copy_edit_report_is_attached():
    graph = PageSceneGraph(
        page=16,
        truth_sources={"script": {"authority": "text_truth"}},
        text_nodes=[_node("统一  表达")],
    )

    updated, report = edit_scene_graph_copy(graph)

    assert report["valid"] is True
    assert report["changed_count"] == 1
    assert updated.metadata["copy_edit"]["schema"] == report["schema"]
