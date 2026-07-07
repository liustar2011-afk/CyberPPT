from __future__ import annotations

from scripts.dual_image_overlay.workspace_assignment import build_workspace_assignment


def test_workspace_assignment_assigns_text_to_preferred_slot() -> None:
    workspace = {
        "containers": [
            {
                "id": "ability_9",
                "work_slots": [
                    {
                        "id": "ability_9_title_slot",
                        "bbox": {"x": 900, "y": 438, "w": 120, "h": 28},
                        "preferred_roles": ["ability_title"],
                    },
                    {
                        "id": "ability_9_body_slot",
                        "bbox": {"x": 900, "y": 470, "w": 120, "h": 70},
                        "preferred_roles": ["body"],
                    },
                ],
            }
        ]
    }

    assignment = build_workspace_assignment(
        page_number=6,
        stage="overlay",
        workspace=workspace,
        text_items=[
            {
                "text": "证书审核",
                "role": "ability_title",
                "container_id": "ability_9",
                "bbox": [900, 438, 1020, 465],
            }
        ],
    )

    assert assignment["valid"] is True
    assert assignment["assignment_count"] == 1
    assert assignment["assignments"][0]["assigned_slot"] == "ability_9_title_slot"
    assert assignment["assignments"][0]["inside_slot"] is True


def test_workspace_assignment_blocks_text_without_slot() -> None:
    assignment = build_workspace_assignment(
        page_number=6,
        stage="overlay",
        workspace={"containers": []},
        text_items=[
            {
                "text": "证书审核",
                "role": "ability_title",
                "container_id": "missing",
                "bbox": [900, 438, 1020, 465],
            }
        ],
    )

    assert assignment["valid"] is False
    assert assignment["issues"][0]["code"] == "text_has_no_work_slot"


def test_workspace_assignment_consumes_page_understanding_binding() -> None:
    assignment = build_workspace_assignment(
        page_number=13,
        stage="template",
        text_items=[
            {
                "id": "stage_6_flow",
                "text": "融资申请→风控审核\n→放款→还款\n全流程线上化",
                "bbox": [630.0, 464.0, 709.0, 506.0],
            }
        ],
        workspace={
            "containers": [
                {
                    "id": "stage_6_card",
                    "work_slots": [
                        {
                            "id": "stage_6_slot",
                            "bbox": {"x": 630.0, "y": 464.0, "w": 79.0, "h": 42.0},
                            "preferred_roles": ["body"],
                        }
                    ],
                }
            ]
        },
        page_understanding={
            "container_text_bindings": [
                {"text_block_id": "stage_6_flow", "container_id": "stage_6_card", "confidence": 0.95}
            ]
        },
    )

    assert assignment["assignments"][0]["text_id"] == "stage_6_flow"
    assert assignment["assignments"][0]["assigned_slot"] == "stage_6_slot"
    assert assignment["assignments"][0]["source"] == "page_understanding"


def test_workspace_assignment_falls_back_when_page_understanding_binding_slot_is_missing() -> None:
    assignment = build_workspace_assignment(
        page_number=13,
        stage="template",
        text_items=[
            {
                "id": "stage_6_flow",
                "text": "融资申请→风控审核",
                "container_id": "legacy_card",
                "bbox": [630.0, 464.0, 709.0, 486.0],
            }
        ],
        workspace={
            "containers": [
                {
                    "id": "legacy_card",
                    "work_slots": [
                        {
                            "id": "legacy_slot",
                            "bbox": {"x": 630.0, "y": 464.0, "w": 79.0, "h": 42.0},
                            "preferred_roles": ["body"],
                        }
                    ],
                }
            ]
        },
        page_understanding={
            "container_text_bindings": [
                {"text_block_id": "stage_6_flow", "container_id": "stale_missing_card", "confidence": 0.95}
            ]
        },
    )

    assert assignment["valid"] is True
    assert assignment["assignments"][0]["container_id"] == "legacy_card"
    assert assignment["assignments"][0]["assigned_slot"] == "legacy_slot"
    assert assignment["assignments"][0].get("source") != "page_understanding"
    assert assignment["issues"][0]["severity"] == "warning"
    assert assignment["issues"][0]["code"] == "page_understanding_binding_missing_slot"


def test_workspace_assignment_allows_clamped_float_boundary_contact() -> None:
    assignment = build_workspace_assignment(
        page_number=12,
        stage="template",
        workspace={
            "containers": [
                {
                    "id": "inferred_panel_04",
                    "work_slots": [
                        {
                            "id": "inferred_panel_04_body_slot",
                            "bbox": {"x": 503.81, "y": 365.18, "w": 160.97, "h": 143.26},
                            "preferred_roles": ["body"],
                        }
                    ],
                }
            ]
        },
        text_items=[
            {
                "text": "全生命周期数据上链存证",
                "container_id": "inferred_panel_04",
                "bbox": {"x": 593.5, "y": 445.22, "w": 104.84, "h": 45.22},
            }
        ],
    )

    assert assignment["valid"] is True
    assert assignment["issues"] == []
    assert assignment["assignments"][0]["inside_slot"] is True


def test_workspace_assignment_resolves_ocr_sibling_bbox_collision() -> None:
    # Reproduces a real OCR defect: two distinct adjacent lines in the same body
    # slot get placed at an identical y coordinate by the vision OCR backend,
    # which _clamp_to_slot (per-item, sibling-unaware) does not detect.
    workspace = {
        "containers": [
            {
                "id": "inferred_row_band_top",
                "work_slots": [
                    {
                        "id": "inferred_row_band_top_body_slot",
                        "bbox": {"x": 437.68, "y": 99.71, "w": 459.63, "h": 207.34},
                        "preferred_roles": ["body"],
                    }
                ],
            }
        ]
    }
    text_items = [
        {"text": "经营管理数据", "role": "body", "container_id": "inferred_row_band_top",
         "bbox": {"x": 97.5, "y": 193.62, "w": 73.87, "h": 11.07}},
        {"text": "项目执行数据", "role": "body", "container_id": "inferred_row_band_top",
         "bbox": {"x": 97.5, "y": 208.38, "w": 73.87, "h": 11.07}},
        {"text": "合同订单数据", "role": "body", "container_id": "inferred_row_band_top",
         "bbox": {"x": 97.5, "y": 223.14, "w": 73.87, "h": 11.07}},
        {"text": "绩效与指标数据", "role": "body", "container_id": "inferred_row_band_top",
         "bbox": {"x": 97.5, "y": 223.14, "w": 87.19, "h": 11.07}},
    ]

    assignment = build_workspace_assignment(
        page_number=6,
        stage="overlay",
        workspace=workspace,
        text_items=text_items,
    )

    boxes = assignment["assignments"]
    assert len(boxes) == 4
    for previous, current in zip(boxes, boxes[1:]):
        prev_bottom = previous["final_bbox"]["y"] + previous["final_bbox"]["h"]
        assert current["final_bbox"]["y"] >= prev_bottom - 1e-6
    assert "resolve_sibling_overlap" in boxes[3]["fit_actions"]
    # Untouched, already-well-spaced siblings should not be needlessly moved.
    assert boxes[0]["final_bbox"]["y"] == 193.62
    assert boxes[1]["final_bbox"]["y"] == 208.38
