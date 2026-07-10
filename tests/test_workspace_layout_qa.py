from __future__ import annotations

from scripts.dual_image_overlay.workspace_layout_qa import (
    check_page_layout_overlaps,
    check_workspace_assignment_layout,
)


def _assignment(text_index: int, text: str, x: float, y: float, w: float, h: float) -> dict:
    return {
        "text_index": text_index,
        "text": text,
        "final_bbox": {"x": x, "y": y, "w": w, "h": h},
    }


def test_no_overlap_reports_valid() -> None:
    assignments = [
        _assignment(0, "经营管理数据", 97.5, 193.62, 73.87, 11.07),
        _assignment(1, "项目执行数据", 97.5, 208.38, 73.87, 11.07),
    ]
    report = check_page_layout_overlaps(assignments)
    assert report["valid"] is True
    assert report["overlap_count"] == 0
    assert report["box_count"] == 2


def test_detects_ocr_bbox_collision_between_siblings() -> None:
    # Reproduces the real defect found in page_006: two distinct OCR lines
    # placed at an identical y coordinate within the same slot.
    assignments = [
        _assignment(5, "合同订单数据", 97.5, 223.14, 73.87, 11.07),
        _assignment(6, "绩效与指标数据", 97.5, 223.14, 87.19, 11.07),
    ]
    report = check_page_layout_overlaps(assignments)
    assert report["valid"] is False
    assert report["overlap_count"] == 1
    overlap = report["overlaps"][0]
    assert overlap["text_index_a"] == 5
    assert overlap["text_index_b"] == 6


def test_detects_cross_container_title_body_overlap() -> None:
    # Reproduces the other real defect: a title box and the first body line
    # of an unrelated-looking pair overlapping because their slots were
    # placed too tightly together.
    title = _assignment(0, "授权管理", 437.68, 99.71, 100.0, 30.0)
    body = _assignment(1, "访问主体与", 440.0, 105.0, 80.0, 20.0)
    report = check_page_layout_overlaps([title, body])
    assert report["valid"] is False
    assert report["overlap_count"] == 1


def test_ignores_whisker_thin_edge_contact() -> None:
    a = _assignment(0, "A", 0.0, 0.0, 100.0, 20.0)
    b = _assignment(1, "B", 100.0, 0.0, 100.0, 20.0)
    report = check_page_layout_overlaps([a, b])
    assert report["valid"] is True
    assert report["overlap_count"] == 0


def test_check_workspace_assignment_layout_aggregates_pages() -> None:
    workspace_assignment = {
        "schema": "cyberppt.dual_image.workspace_assignment_set.v1",
        "pages": [
            {
                "page_number": 6,
                "assignments": [
                    _assignment(0, "合同订单数据", 97.5, 223.14, 73.87, 11.07),
                    _assignment(1, "绩效与指标数据", 97.5, 223.14, 87.19, 11.07),
                ],
            },
            {
                "page_number": 7,
                "assignments": [
                    _assignment(0, "经营管理数据", 97.5, 193.62, 73.87, 11.07),
                    _assignment(1, "项目执行数据", 97.5, 208.38, 73.87, 11.07),
                ],
            },
        ],
    }
    report = check_workspace_assignment_layout(workspace_assignment)
    assert report["valid"] is False
    assert report["page_count"] == 2
    assert report["overlap_count"] == 1
    assert report["pages"][0]["page_number"] == 6
    assert report["pages"][0]["overlap_count"] == 1
    assert report["pages"][1]["overlap_count"] == 0


def test_check_workspace_assignment_layout_valid_when_no_overlaps() -> None:
    workspace_assignment = {
        "pages": [
            {
                "page_number": 6,
                "assignments": [
                    _assignment(0, "经营管理数据", 97.5, 193.62, 73.87, 11.07),
                    _assignment(1, "项目执行数据", 97.5, 208.38, 73.87, 11.07),
                ],
            }
        ]
    }
    report = check_workspace_assignment_layout(workspace_assignment)
    assert report["valid"] is True
    assert report["overlap_count"] == 0


def test_font_floor_flags_body_text_below_minimum():
    from scripts.dual_image_overlay.workspace_layout_qa import check_page_font_floor

    assignments = [
        {"text_index": 0, "text": "正文太小了", "role": "body", "font_size_pt": 7.0},
        {"text_index": 1, "text": "正文正常", "role": "body", "font_size_pt": 9.0},
    ]
    report = check_page_font_floor(assignments)
    assert report["valid"] is False
    assert report["issue_count"] == 1
    assert report["issues"][0]["text_index"] == 0


def test_font_floor_ignores_items_without_font_size():
    from scripts.dual_image_overlay.workspace_layout_qa import check_page_font_floor

    assignments = [{"text_index": 0, "text": "无字号信息", "role": "body"}]
    report = check_page_font_floor(assignments)
    assert report["valid"] is True
    assert report["checked_count"] == 0


def test_font_floor_uses_role_specific_threshold():
    from scripts.dual_image_overlay.workspace_layout_qa import check_page_font_floor

    # 10pt clears the body floor (9.0) but not the title floor (14.0).
    assignments = [{"text_index": 0, "text": "标题", "role": "title", "font_size_pt": 10.0}]
    report = check_page_font_floor(assignments)
    assert report["valid"] is False
    assert report["issues"][0]["minimum_pt"] == 14.0


def test_check_page_layout_combines_overlap_and_font_floor():
    from scripts.dual_image_overlay.workspace_layout_qa import check_page_layout

    assignments = [
        {
            "text_index": 0,
            "text": "正文太小了",
            "role": "body",
            "font_size_pt": 7.0,
            "final_bbox": {"x": 0.0, "y": 0.0, "w": 100.0, "h": 20.0},
        },
        {
            "text_index": 1,
            "text": "另一行",
            "role": "body",
            "font_size_pt": 9.0,
            "final_bbox": {"x": 0.0, "y": 100.0, "w": 100.0, "h": 20.0},
        },
    ]
    report = check_page_layout(assignments)
    assert report["valid"] is False
    assert report["overlap_count"] == 0
    assert report["font_floor_issue_count"] == 1
