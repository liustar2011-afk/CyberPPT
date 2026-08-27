from __future__ import annotations

from scripts.imagegen_pipeline.content_root_qa import build_content_root_qa


def _receipt() -> dict[str, object]:
    return {
        "text_bindings": [
            {
                "root_id": "P07-T01",
                "rendered_group": 1,
                "role": "root_module",
                "hierarchy_level": 1,
                "text_ids": ["P07-T01", "P07-T02"],
                "exact_text": ["数据服务", "基础查询"],
            },
            {
                "root_id": "P07-T03",
                "rendered_group": 2,
                "role": "root_module",
                "hierarchy_level": 1,
                "text_ids": ["P07-T03"],
                "exact_text": ["模型服务"],
            },
        ]
    }


def test_content_root_qa_reports_exact_missing_text_id_and_root() -> None:
    qa = build_content_root_qa(
        page_number=7,
        debug_receipt=_receipt(),
        text_audit={
            "observed_text": ["数据服务", "模型服务"],
            "ocr_items": [],
        },
    )
    assert qa["status"] == "incomplete"
    assert qa["missing_text_ids"] == ["P07-T02"]
    first = qa["roots"][0]
    assert first["root_id"] == "P07-T01"
    assert first["matched_text_ids"] == ["P07-T01"]
    assert first["missing_text_ids"] == ["P07-T02"]


def test_content_root_qa_passes_with_ocr_segmented_text() -> None:
    qa = build_content_root_qa(
        page_number=7,
        debug_receipt=_receipt(),
        text_audit={
            "observed_text": ["数据服务", "基础查询"],
            "ocr_items": [{"text": "模型服务"}],
        },
    )
    assert qa["status"] == "passed"
    assert all(root["status"] == "passed" for root in qa["roots"])


def test_content_root_qa_does_not_guess_spatial_root_from_ocr() -> None:
    qa = build_content_root_qa(
        page_number=7,
        debug_receipt=_receipt(),
        text_audit={"observed_text": [], "ocr_items": []},
    )
    assert qa["spatial_root_assignment"] == "not_inferred_from_ocr"
