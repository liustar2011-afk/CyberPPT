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
