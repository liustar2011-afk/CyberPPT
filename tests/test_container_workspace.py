from __future__ import annotations

from scripts.dual_image_overlay.container_workspace import build_container_workspace


def test_container_workspace_builds_title_and_body_slots() -> None:
    workspace = build_container_workspace(
        page_number=6,
        stage="overlay",
        containers=[
            {
                "id": "ability_9",
                "role": "ability_card",
                "bbox": [800, 420, 1040, 560],
                "text_safe_bbox": [900, 438, 1020, 540],
            }
        ],
        text_items=[
            {
                "text": "证书审核",
                "role": "ability_title",
                "container_id": "ability_9",
                "bbox": [900, 438, 1020, 465],
            },
            {
                "text": "结果合规审核",
                "role": "body",
                "container_id": "ability_9",
                "bbox": [900, 472, 1020, 500],
            },
        ],
    )

    assert workspace["schema"] == "cyberppt.dual_image.container_workspace.v1"
    assert workspace["valid"] is True
    assert workspace["container_count"] == 1
    assert workspace["slot_count"] == 2
    assert [slot["id"] for slot in workspace["containers"][0]["work_slots"]] == [
        "ability_9_title_slot",
        "ability_9_body_slot",
    ]


def test_container_workspace_fails_when_container_has_no_work_slot() -> None:
    workspace = build_container_workspace(
        page_number=6,
        stage="overlay",
        containers=[
            {
                "id": "empty",
                "role": "card",
                "bbox": [10, 10, 20, 20],
                "text_safe_bbox": [10, 10, 20, 20],
            }
        ],
        text_items=[],
    )

    assert workspace["valid"] is False
    assert workspace["error_count"] == 1
    assert workspace["issues"][0]["code"] == "container_has_no_work_slots"
