from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

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


def test_container_workspace_subtracts_visual_registry_occupied_zone() -> None:
    workspace = build_container_workspace(
        page_number=6,
        stage="template",
        containers=[
            {
                "id": "service_1",
                "role": "service_card",
                "bbox": [100, 100, 300, 180],
                "text_safe_bbox": [100, 100, 300, 180],
            }
        ],
        text_items=[
            {
                "text": "基础评估服务",
                "role": "service_title",
                "container_id": "service_1",
                "bbox": [150, 104, 290, 130],
            },
            {
                "text": "标准化评估服务",
                "role": "body",
                "container_id": "service_1",
                "bbox": [150, 134, 290, 160],
            },
        ],
        visual_elements=[
            {
                "element_id": "service_icon",
                "element_type": "icon",
                "blueprint_bbox_px": [100, 112, 142, 166],
                "source": {"kind": "visual_element_registry"},
            }
        ],
    )

    container = workspace["containers"][0]
    body_slot = next(slot for slot in container["work_slots"] if slot["id"] == "service_1_body_slot")
    assert workspace["valid"] is True
    assert container["occupied_zones"][0]["element_id"] == "service_icon"
    assert body_slot["bbox"]["x"] > 142
    assert body_slot["slot_adjustments"][0]["code"] == "subtract_occupied_zone"


def test_container_workspace_subtracts_background_dark_region(tmp_path: Path) -> None:
    background = tmp_path / "background.png"
    image = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 120, 150, 170), fill=(0, 60, 120))
    image.save(background)

    workspace = build_container_workspace(
        page_number=6,
        stage="overlay",
        containers=[
            {
                "id": "card",
                "role": "ability_card",
                "bbox": [90, 90, 300, 210],
                "text_safe_bbox": [100, 110, 290, 190],
            }
        ],
        text_items=[
            {
                "text": "证据管理",
                "role": "ability_title",
                "container_id": "card",
                "bbox": [160, 114, 280, 140],
            },
            {
                "text": "证据采集接入",
                "role": "body",
                "container_id": "card",
                "bbox": [160, 144, 280, 170],
            },
        ],
        background_image=background,
    )

    container = workspace["containers"][0]
    assert [zone["source"] for zone in container["occupied_zones"]] == ["background_image_dark_region"]
    assert any(slot.get("slot_adjustments") for slot in container["work_slots"])
