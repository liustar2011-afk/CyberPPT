from scripts.dual_image_overlay.page_acceptance import build_page_acceptance_manifest, select_representative_pages


def test_select_representative_pages_prefers_complex_pages_deterministically():
    pages = [
        {"page_number": 1, "page_role": "cover"},
        {"page_number": 2, "page_role": "content", "visual_node_count": 3, "relation_count": 1},
        {"page_number": 3, "page_role": "process", "visual_node_count": 2, "relation_count": 4, "has_curve": True},
    ]
    assert select_representative_pages(pages, max_pages=2) == [2, 3]


def test_acceptance_manifest_requires_full_deck_artifacts_and_confirmation(tmp_path):
    pages = [{"page_number": 2}, {"page_number": 3}]
    artifacts = {}
    for page in pages:
        root = tmp_path / str(page["page_number"])
        root.mkdir()
        artifacts[page["page_number"]] = {key: str(root / f"{key}.json") for key in ("full", "background", "scene_graph", "page_svg_ir", "qa_fusion")}
        for path in artifacts[page["page_number"]].values():
            (tmp_path / str(page["page_number"]) / path.split("/")[-1]).write_text("{}", encoding="utf-8")
        artifacts[page["page_number"]]["qa_valid"] = True
        artifacts[page["page_number"]]["user_confirmed"] = page["page_number"] == 2
    report = build_page_acceptance_manifest(pages, artifacts, require_user_confirmation=True)
    assert report["valid"] is False
    assert report["accepted_page_count"] == 1
    assert report["pages"][0]["representative"] is True

