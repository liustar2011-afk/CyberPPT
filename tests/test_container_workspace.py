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


def test_container_workspace_accepts_safe_area_alias_as_text_safe_bbox() -> None:
    workspace = build_container_workspace(
        page_number=6,
        stage="overlay",
        containers=[
            {
                "id": "ability_10",
                "role": "ability_card",
                "bbox": [800, 420, 1040, 560],
                "safe_area": {"x": 900, "y": 438, "w": 120, "h": 102},
            }
        ],
        text_items=[
            {
                "text": "证书状态管理",
                "role": "body",
                "container_id": "ability_10",
                "bbox": [900, 472, 1020, 500],
            },
        ],
    )

    container = workspace["containers"][0]
    assert workspace["valid"] is True
    assert container["container_bbox"] == {"x": 800.0, "y": 420.0, "w": 240.0, "h": 140.0}
    assert container["text_safe_bbox"] == {"x": 900.0, "y": 438.0, "w": 120.0, "h": 102.0}
    assert container["work_slots"][0]["bbox"] == container["text_safe_bbox"]


def test_container_workspace_prefers_page_understanding_text_safe_regions() -> None:
    workspace = build_container_workspace(
        page_number=13,
        stage="template",
        containers=[],
        text_items=[],
        visual_elements=[],
        page_understanding={
            "containers": [
                {
                    "id": "stage_6_card",
                    "kind": "explicit_container",
                    "bbox": [624.0, 420.0, 714.0, 530.0],
                    "text_safe_bbox": [630.0, 464.0, 709.0, 506.0],
                }
            ]
        },
    )

    container = workspace["containers"][0]
    assert workspace["slot_count"] == 1
    assert container["id"] == "stage_6_card"
    assert container["work_slots"][0]["bbox"] == {"x": 630.0, "y": 464.0, "w": 79.0, "h": 42.0}
    assert container["work_slots"][0]["source"] == "page_understanding"


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


def test_container_workspace_does_not_subtract_background_panel_as_text_obstacle() -> None:
    workspace = build_container_workspace(
        page_number=11,
        stage="template",
        containers=[
            {
                "id": "service_product",
                "role": "service_card",
                "bbox": [620, 205, 808, 560],
                "text_safe_bbox": [622, 388, 792, 556],
            }
        ],
        text_items=[
            {
                "text": "公证合同：对接公证处实现合同公证，具备法定证据效力，可独立用于举证维权",
                "role": "body",
                "container_id": "service_product",
                "bbox": [631, 471, 790, 538],
            },
        ],
        visual_elements=[
            {
                "element_id": "background_panel",
                "element_type": "shape",
                "blueprint_bbox_px": [620, 106, 1266, 544],
                "source": {
                    "kind": "source_capture_inventory",
                    "inventory_source": "background_visual_component",
                },
            },
            {
                "element_id": "certificate_art",
                "element_type": "shape",
                "blueprint_bbox_px": [638, 193, 764, 384],
                "source": {
                    "kind": "source_capture_inventory",
                    "inventory_source": "background_visual_component",
                },
            },
        ],
    )

    container = workspace["containers"][0]
    body_slot = container["work_slots"][0]
    assert workspace["valid"] is True
    assert body_slot["bbox"]["w"] == 170.0
    assert all(zone["element_id"] != "background_panel" for zone in container["occupied_zones"])


def test_container_workspace_treats_source_text_overlap_as_writable_container() -> None:
    workspace = build_container_workspace(
        page_number=11,
        stage="template",
        containers=[
            {
                "id": "service_product",
                "role": "service_card",
                "bbox": [620, 205, 808, 560],
                "text_safe_bbox": [622, 388, 792, 556],
            }
        ],
        text_items=[
            {
                "text": "公证合同：对接公证处实现合同公证，具备法定证据效力，可独立用于举证维权",
                "role": "body",
                "container_id": "service_product",
                "bbox": [631, 471, 790, 538],
            },
        ],
        visual_elements=[
            {
                "element_id": "text_surface",
                "element_type": "shape",
                "blueprint_bbox_px": [626, 460, 794, 546],
                "source": {
                    "kind": "source_capture_inventory",
                    "inventory_source": "background_visual_component",
                },
            },
            {
                "element_id": "side_icon",
                "element_type": "icon",
                "blueprint_bbox_px": [622, 410, 646, 442],
                "source": {
                    "kind": "source_capture_inventory",
                    "inventory_source": "background_visual_component",
                },
            },
        ],
    )

    container = workspace["containers"][0]
    body_slot = container["work_slots"][0]
    assert workspace["valid"] is True
    assert body_slot["bbox"]["w"] >= 140.0
    assert all(zone["element_id"] != "text_surface" for zone in container["occupied_zones"])
    assert any(zone["element_id"] == "side_icon" for zone in container["occupied_zones"])


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
