from __future__ import annotations

from cyberppt.content_integrity_contract import (
    CONTENT_INTEGRITY_SCHEMA,
    build_content_integrity_contract,
    structure_hash_from_node_dicts,
)
from cyberppt.script_quality.models import ScriptPage


def _page(onscreen_text: str, *, page_id: str = "p05", sequence: int = 5) -> ScriptPage:
    return ScriptPage(
        page_id=page_id,
        sequence=sequence,
        heading="",
        page_type="content",
        title="",
        main_message="",
        full_prose="",
        selection_notes="",
        evidence_map="",
        evidence_map_refs=(),
        source_refs=(),
        boundary_source_refs=(),
        boundary="",
        visual_structure="",
        onscreen_text=onscreen_text,
        module_titles=(),
    )


def test_flat_page_is_all_roots_with_no_children() -> None:
    page = _page("服务国家\n赋能行业\n支撑内部发展")
    contract = build_content_integrity_contract(page)

    assert contract.schema == CONTENT_INTEGRITY_SCHEMA
    assert contract.page_id == "P05"
    assert list(contract.root_nodes) == ["P05-T01", "P05-T02", "P05-T03"]
    assert all(node.parent_id is None for node in contract.nodes)
    assert all(node.children == () for node in contract.nodes)
    assert all(node.content_role == "root_module" for node in contract.nodes)
    assert all(node.promotion_policy == "root_only" for node in contract.nodes)
    assert all(node.source_level == 1 for node in contract.nodes)


def test_nested_page_builds_correct_parent_child_tree() -> None:
    page = _page(
        "多层次服务体系\n"
        "  服务国家\n"
        "  赋能行业\n"
        "  为新型电力系统建设提供数据底座\n"
        "支撑内部发展"
    )
    contract = build_content_integrity_contract(page)
    by_id = {node.text_id: node for node in contract.nodes}

    assert list(contract.root_nodes) == ["P05-T01", "P05-T05"]

    root = by_id["P05-T01"]
    assert root.content_role == "root_module"
    assert root.promotion_policy == "root_only"
    assert root.parent_id is None
    assert root.source_level == 1
    assert list(root.children) == ["P05-T02", "P05-T03", "P05-T04"]

    for child_id in ("P05-T02", "P05-T03", "P05-T04"):
        child = by_id[child_id]
        assert child.parent_id == "P05-T01"
        assert child.root_id == "P05-T01"
        assert child.source_level == 2
        assert child.content_role == "detail"
        assert child.promotion_policy == "forbidden"
        assert child.children == ()

    second_root = by_id["P05-T05"]
    assert second_root.parent_id is None
    assert second_root.content_role == "root_module"
    assert second_root.promotion_policy == "root_only"


def test_duplicate_lines_are_deduplicated_without_dangling_parents() -> None:
    page = _page("模块\n  细节\n  细节\n  细节")
    contract = build_content_integrity_contract(page)

    # "细节" collapses to a single node under dedup, same as locked_text_items.
    assert [node.text for node in contract.nodes] == ["模块", "细节"]
    assert contract.nodes[1].parent_id == contract.nodes[0].text_id
    assert list(contract.nodes[0].children) == [contract.nodes[1].text_id]


def test_promotion_eligible_detail_text_does_not_change_structural_role() -> None:
    """Text content (e.g. containing '底座', or reading as highly drawable)
    must never influence content_role/promotion_policy -- only tree position
    does. This is the P0 guard for negative examples 1 and 2 in the
    architecture plan (a detail line must not silently become root-eligible
    just because a keyword or "most paintable" quality makes it attractive
    as a visual focus later in the pipeline).
    """

    page = _page("多层次服务体系\n  为新型电力系统建设提供数据底座")
    contract = build_content_integrity_contract(page)
    detail = next(node for node in contract.nodes if "底座" in node.text)

    assert detail.content_role == "detail"
    assert detail.promotion_policy == "forbidden"
    assert detail.parent_id is not None


def test_structure_hash_is_stable_for_identical_input() -> None:
    text = "模块甲\n  细节一\n模块乙"
    first = build_content_integrity_contract(_page(text))
    second = build_content_integrity_contract(_page(text))

    assert first.structure_hash == second.structure_hash
    assert first.source_hash == second.source_hash


def test_source_hash_changes_when_text_changes() -> None:
    base = build_content_integrity_contract(_page("模块甲\n  细节一"))
    edited = build_content_integrity_contract(_page("模块甲\n  细节二"))

    assert base.source_hash != edited.source_hash


def test_structure_hash_changes_when_indentation_topology_changes() -> None:
    # Swapping two peer roots keeps an identical shape (root, root) at
    # ordinals (1, 2), so structure_hash is unaffected -- only source_hash
    # (covered above) detects that kind of reorder. Promoting a line from
    # child to sibling root, however, changes the parent/level pattern
    # itself and must change structure_hash.
    nested = build_content_integrity_contract(_page("模块甲\n  子项一\n  子项二"))
    flattened = build_content_integrity_contract(_page("模块甲\n  子项一\n子项二"))

    assert nested.structure_hash != flattened.structure_hash
    assert list(nested.root_nodes) != list(flattened.root_nodes)


def test_structure_hash_from_node_dicts_matches_builder_output() -> None:
    contract = build_content_integrity_contract(_page("模块甲\n  细节一\n模块乙"))
    recomputed = structure_hash_from_node_dicts([node.to_dict() for node in contract.nodes])

    assert recomputed == contract.structure_hash
