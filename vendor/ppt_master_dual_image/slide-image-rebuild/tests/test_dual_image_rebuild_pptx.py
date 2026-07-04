from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.enum.text import MSO_AUTO_SIZE

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "dual_image_rebuild"

from dual_image_rebuild_pptx import (  # noqa: E402
    AlignmentTransform,
    CANVAS,
    CONTAINER_INFERENCE_DEFAULT_PROFILE,
    OverlayTextBox,
    apply_layout_plan,
    apply_typesetting_policy,
    build_text_style_profile,
    build_layout_qa_report,
    build_layout_plan,
    build_overlay_boxes,
    build_production_readiness_report,
    build_text_content_qa_report,
    build_pdf_preview,
    estimate_alignment,
    infer_visual_frameworks_from_containers,
    export_pptx,
    infer_semantic_containers_from_full_style,
    normalize_text_layout,
    normalize_semantic_plan,
    run,
    semantic_plan_owns_geometry,
    validate_semantic_plan,
    _bundled_font_path,
    _estimated_text_width,
    _stack_text_group_in_region,
)


def _write_pair(tmp_path: Path) -> tuple[Path, Path]:
    full = Image.new("RGB", CANVAS, "#F7F8FA")
    full_draw = ImageDraw.Draw(full)
    full_draw.rounded_rectangle((220, 180, 620, 320), radius=18, fill="#FFFFFF", outline="#6B7280", width=3)
    full_draw.text((280, 230), "Editable Title", fill="#111827")

    background = Image.new("RGB", CANVAS, "#F7F8FA")
    bg_draw = ImageDraw.Draw(background)
    bg_draw.rounded_rectangle((232, 176, 632, 316), radius=18, fill="#FFFFFF", outline="#6B7280", width=3)

    full_path = tmp_path / "full.png"
    background_path = tmp_path / "background.png"
    full.save(full_path)
    background.save(background_path)
    return full_path, background_path


def _layout() -> dict[str, object]:
    return {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "Editable Title",
                "bbox": [276, 224, 430, 252],
                "confidence": 0.98,
            }
        ],
    }


def _semantic_plan_path(tmp_path: Path) -> Path:
    plan = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "containers": [
            {
                "id": "card",
                "role": "content_card",
                "bbox": [232, 176, 632, 316],
                "text_safe_bbox": [270, 214, 570, 270],
            }
        ],
        "items": [
            {
                "source_text": "Editable Title",
                "display_text": "Editable Title",
                "container_id": "card",
                "relative_bbox": [0, 0, 1, 1],
                "role": "section_title",
            }
        ],
    }
    path = tmp_path / "semantic_plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    return path


def test_semantic_plan_preflight_rejects_missing_container_id() -> None:
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {"id": "card_a", "role": "content_card", "bbox": [100, 100, 300, 220]},
            ],
            "items": [
                {
                    "display_text": "正文",
                    "source_text": "正文",
                    "container_id": "missing_card",
                    "bbox": [120, 130, 260, 180],
                    "role": "trust_body",
                    "font_size": 12,
                }
            ],
        }
    )

    report = validate_semantic_plan(plan)

    assert report["valid"] is False
    assert ("missing_container", "error") in {
        (issue["code"], issue["severity"]) for issue in report["issues"]
    }


def test_semantic_plan_preflight_rejects_body_in_isolated_region() -> None:
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {"id": "note", "role": "isolated_text_region", "bbox": [100, 100, 300, 220]},
            ],
            "items": [
                {
                    "display_text": "需要授权后提供",
                    "source_text": "需要授权后提供",
                    "container_id": "note",
                    "bbox": [120, 130, 260, 180],
                    "role": "trust_body",
                    "font_size": 12,
                }
            ],
        }
    )

    report = validate_semantic_plan(plan)

    assert report["valid"] is False
    assert ("body_in_isolated_region", "error") in {
        (issue["code"], issue["severity"]) for issue in report["issues"]
    }


def test_estimate_alignment_maps_text_toward_background_shift(tmp_path: Path) -> None:
    full_path, background_path = _write_pair(tmp_path)
    layout = normalize_text_layout(_layout())

    transform = estimate_alignment(full_path, background_path, layout)
    boxes = build_overlay_boxes(layout, background_path, transform)

    assert boxes
    assert transform.dx > 0
    assert transform.dy < 2
    mapped = boxes[0].mapped_bbox or []
    assert mapped[0] > 276


def test_dual_image_run_writes_mapping_svg_and_pptx(tmp_path: Path) -> None:
    full_path, background_path = _write_pair(tmp_path)
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(json.dumps(_layout()), encoding="utf-8")

    result = run(
        argparse.Namespace(
            full=full_path,
            background=background_path,
            text_layout=layout_path,
            semantic_plan=None,
            name="dual_fixture",
            projects_dir=tmp_path / "projects",
            font_family="Arial",
            fill="#111827",
            no_align=True,
        )
    )

    assert result["valid"] is True
    assert result["text_boxes"] == 1
    artifacts = result["artifacts"]
    assert Path(artifacts["text_mapping"]).is_file()
    assert Path(artifacts["layout_qa"]).is_file()
    assert Path(artifacts["text_content_qa"]).is_file()
    assert Path(artifacts["visual_frameworks"]).is_file()
    assert Path(artifacts["composition_contract"]).is_file()
    assert Path(artifacts["svg"]).is_file()
    assert Path(artifacts["pptx"]).is_file()
    assert Path(artifacts["layout_reference"]).is_file()
    assert Path(artifacts["content_mapping"]).is_file()
    assert Path(artifacts["text_region_map"]).is_file()
    assert Path(artifacts["svg_build_plan"]).is_file()

    prs = Presentation(artifacts["pptx"])
    text_frames = [
        shape.text_frame
        for shape in prs.slides[0].shapes
        if getattr(shape, "has_text_frame", False) and shape.text_frame.text.strip()
    ]
    assert text_frames
    assert all(frame.word_wrap is False for frame in text_frames)
    assert all(frame.auto_size == MSO_AUTO_SIZE.NONE for frame in text_frames)

    mapping = json.loads(Path(artifacts["text_mapping"]).read_text(encoding="utf-8"))
    assert mapping["text_display_policy"] == "ai_designed_display_text_from_semantics"
    assert mapping["container_fit_policy"] == "container_first_safe_bbox_then_nudge_shrink_simplify"
    assert Path(mapping["visual_frameworks"]).is_file()
    assert Path(mapping["composition_contract"]).is_file()
    assert Path(mapping["text_content_qa"]).is_file()
    qa = json.loads(Path(artifacts["layout_qa"]).read_text(encoding="utf-8"))
    assert qa["checks"]["container_safe_bbox"] is True
    text_qa = json.loads(Path(artifacts["text_content_qa"]).read_text(encoding="utf-8"))
    assert text_qa["valid"] is True
    assert text_qa["checks"]["pptx_text_matches_mapping"] is True
    assert result["production_ready"] is False
    assert Path(artifacts["production_readiness"]).is_file()
    production_qa = json.loads(Path(artifacts["production_readiness"]).read_text(encoding="utf-8"))
    assert production_qa["valid"] is False
    assert production_qa["checks"]["explicit_semantic_containers"] is False

    with zipfile.ZipFile(artifacts["pptx"]) as package:
        assert "ppt/notesSlides/notesSlide1.xml" in package.namelist()


def test_dual_image_run_with_explicit_containers_is_production_ready(tmp_path: Path) -> None:
    full_path, background_path = _write_pair(tmp_path)
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(json.dumps(_layout()), encoding="utf-8")
    semantic_path = _semantic_plan_path(tmp_path)

    result = run(
        argparse.Namespace(
            full=full_path,
            background=background_path,
            text_layout=layout_path,
            semantic_plan=semantic_path,
            name="explicit_container_fixture",
            projects_dir=tmp_path / "projects",
            font_family="Arial",
            fill="#111827",
            no_align=True,
        )
    )

    assert result["production_ready"] is True
    assert result["production_readiness_error_count"] == 0
    production_qa = json.loads(Path(result["artifacts"]["production_readiness"]).read_text(encoding="utf-8"))
    assert production_qa["valid"] is True
    assert production_qa["checks"]["explicit_semantic_containers"] is True
    assert production_qa["checks"]["default_profile_not_used_as_acceptance_basis"] is True


def test_dual_image_run_stops_before_export_when_semantic_preflight_fails(tmp_path: Path) -> None:
    full_path, background_path = _write_pair(tmp_path)
    semantic_path = tmp_path / "invalid_semantic_plan.json"
    semantic_path.write_text(
        json.dumps(
            {
                "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
                "containers": [
                    {"id": "note", "role": "isolated_text_region", "bbox": [100, 100, 300, 220]},
                ],
                "items": [
                    {
                        "display_text": "需要授权后提供",
                        "source_text": "需要授权后提供",
                        "container_id": "note",
                        "bbox": [120, 130, 260, 180],
                        "role": "trust_body",
                        "font_size": 12,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = run(
        argparse.Namespace(
            full=full_path,
            background=background_path,
            text_layout=None,
            semantic_plan=semantic_path,
            name="invalid_semantic_fixture",
            projects_dir=tmp_path / "projects",
            font_family="Arial",
            fill="#111827",
            no_align=True,
        )
    )

    assert result["valid"] is False
    assert result["semantic_plan_preflight_valid"] is False
    assert result["semantic_plan_preflight_error_count"] == 1
    assert "pptx" not in result["artifacts"]
    preflight = json.loads(Path(result["artifacts"]["semantic_plan_preflight"]).read_text(encoding="utf-8"))
    assert ("body_in_isolated_region", "error") in {
        (issue["code"], issue["severity"]) for issue in preflight["issues"]
    }


def test_main_exits_nonzero_when_production_lacks_explicit_containers(tmp_path: Path) -> None:
    full_path, background_path = _write_pair(tmp_path)
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(json.dumps(_layout()), encoding="utf-8")

    import dual_image_rebuild_pptx as module

    exit_code = module.main(
        [
            "--full",
            str(full_path),
            "--background",
            str(background_path),
            "--text-layout",
            str(layout_path),
            "--name",
            "no_container_fixture",
            "--projects-dir",
            str(tmp_path / "projects"),
            "--no-align",
        ]
    )

    assert exit_code == 3


def test_semantic_plan_uses_display_text_and_container_geometry() -> None:
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {"id": "card", "bbox": [100, 100, 500, 300], "text_safe_bbox": [120, 120, 460, 280]},
            ],
            "items": [
                {
                    "source_text": "联合行业头部企业、技术服务商共同出资成立，负责日常运营、技术维护、市场推广、生态建设",
                    "display_text": "联合出资，负责运营维护",
                    "container_id": "card",
                    "relative_bbox": [0.1, 0.2, 0.9, 0.35],
                    "role": "summary",
                }
            ],
        }
    )

    assert semantic_plan_owns_geometry(plan)
    assert plan["items"][0]["text"] == "联合出资，负责运营维护"
    assert plan["items"][0]["source_text"].startswith("联合行业头部企业")
    assert plan["items"][0]["bbox"] == [140.0, 140.0, 460.0, 170.0]
    assert plan["items"][0]["container_text_safe_bbox"] == [120.0, 120.0, 460.0, 280.0]


def test_container_safe_bbox_nudges_text_inside_available_area(tmp_path: Path) -> None:
    background = Image.new("RGB", CANVAS, "#FFFFFF")
    background_path = tmp_path / "background.png"
    background.save(background_path)
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {"id": "ring", "bbox": [600, 260, 760, 430], "text_safe_bbox": [600, 300, 700, 385]},
            ],
            "items": [
                {
                    "display_text": "双轨协同",
                    "source_text": "双轨协同",
                    "container_id": "ring",
                    "bbox": [650, 310, 750, 336],
                    "font_size": 16,
                    "align": "center",
                    "lock_bbox": True,
                }
            ],
        }
    )

    boxes = build_overlay_boxes(plan, background_path, transform=AlignmentTransform())

    assert boxes[0].x == 600
    assert boxes[0].x + boxes[0].w == 700


def test_build_layout_plan_reports_missing_bbox_with_item_index() -> None:
    with pytest.raises(ValueError, match=r"item\[0\].*bbox"):
        build_layout_plan({"items": [{"text": "缺少坐标", "role": "section_title"}]})


def test_build_overlay_boxes_reports_missing_text_with_item_index(tmp_path: Path) -> None:
    background = Image.new("RGB", CANVAS, "#FFFFFF")
    background_path = tmp_path / "background.png"
    background.save(background_path)

    with pytest.raises(ValueError, match=r"item\[0\].*text"):
        build_overlay_boxes({"items": [{"bbox": [100, 100, 180, 130]}]}, background_path, AlignmentTransform())


def test_layout_plan_stacks_center_container_before_rendering() -> None:
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {
                    "id": "ring",
                    "role": "center_coordination_node",
                    "bbox": [585, 260, 770, 430],
                    "text_safe_bbox": [602, 298, 705, 386],
                },
            ],
            "items": [
                {
                    "display_text": "双轨协同",
                    "source_text": "双轨协同",
                    "container_id": "ring",
                    "bbox": [642, 310, 730, 338],
                    "role": "center_label",
                    "font_size": 17,
                },
                {
                    "display_text": "共促转化",
                    "source_text": "共促转化",
                    "container_id": "ring",
                    "bbox": [642, 345, 730, 373],
                    "role": "center_label",
                    "font_size": 17,
                },
            ],
        }
    )

    layout_plan = build_layout_plan(plan)
    planned = apply_layout_plan(plan, layout_plan)

    assert layout_plan["layout_policy"] == "container_role_and_text_role_first"
    assert [item["strategy"] for item in layout_plan["items"]] == [
        "stack_center_in_container",
        "stack_center_in_container",
    ]
    assert planned["items"][0]["bbox"][0] == 602.0
    assert planned["items"][0]["bbox"][2] == 705.0
    assert planned["items"][0]["font_size"] <= 14.5
    assert planned["items"][0]["align"] == "center"
    assert planned["items"][0]["v_align"] == "middle"
    assert layout_plan["items"][0]["container_safe_bbox"] == [602.0, 298.0, 705.0, 386.0]
    assert layout_plan["items"][0]["semantic_compression_level"] == "preserve"


def test_layout_plan_infers_center_ring_safe_bbox_when_missing() -> None:
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {
                    "id": "ring",
                    "role": "center_coordination_node",
                    "bbox": [600, 260, 760, 420],
                },
            ],
            "items": [
                {
                    "display_text": "协同",
                    "source_text": "双轨协同",
                    "container_id": "ring",
                    "bbox": [645, 320, 715, 350],
                    "role": "center_label",
                    "font_size": 16,
                },
            ],
        }
    )

    layout_plan = build_layout_plan(plan)
    safe_bbox = layout_plan["items"][0]["container_safe_bbox"]

    assert layout_plan["items"][0]["layout_rationale"] == "inferred_inner_ring_safe_bbox"
    assert safe_bbox[0] > 600
    assert safe_bbox[2] < 760
    assert safe_bbox[1] > 260
    assert safe_bbox[3] < 420


def test_layout_plan_centers_single_stage_label_in_badge_container() -> None:
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {
                    "id": "label_subject",
                    "role": "left_stage_label",
                    "bbox": [18, 30, 165, 75],
                },
            ],
            "items": [
                {
                    "display_text": "运营主体",
                    "source_text": "运营主体分工",
                    "container_id": "label_subject",
                    "bbox": [35, 48, 150, 70],
                    "role": "stage_label",
                    "font_size": 16,
                    "font_weight": "700",
                    "align": "center",
                    "lock_bbox": True,
                },
            ],
        }
    )

    layout_plan = build_layout_plan(plan)
    planned = apply_layout_plan(plan, layout_plan)

    assert layout_plan["items"][0]["strategy"] == "center_in_badge"
    assert planned["items"][0]["bbox"] == [18.0, 30.0, 165.0, 75.0]
    assert planned["items"][0]["align"] == "center"
    assert planned["items"][0]["v_align"] == "middle"


def test_layout_plan_stacks_multiline_stage_label_without_using_icon_area() -> None:
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {
                    "id": "label_dual_track",
                    "role": "left_stage_label",
                    "bbox": [18, 244, 172, 390],
                },
            ],
            "items": [
                {
                    "display_text": "公益 + 市场化",
                    "source_text": "公益+市场化双轨模式",
                    "container_id": "label_dual_track",
                    "bbox": [24, 258, 166, 282],
                    "role": "stage_label",
                    "font_size": 15,
                },
                {
                    "display_text": "双轨模式",
                    "source_text": "公益+市场化双轨模式",
                    "container_id": "label_dual_track",
                    "bbox": [45, 292, 145, 316],
                    "role": "stage_label",
                    "font_size": 16,
                },
            ],
        }
    )

    layout_plan = build_layout_plan(plan)
    planned = apply_layout_plan(plan, layout_plan)

    assert [item["strategy"] for item in layout_plan["items"]] == [
        "stack_center_in_badge",
        "stack_center_in_badge",
    ]
    assert planned["items"][0]["bbox"][1] < 270
    assert planned["items"][1]["bbox"][3] < 330
    assert planned["items"][0]["v_align"] == "middle"


def test_layout_plan_adds_vertical_padding_to_top_actor_card() -> None:
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {
                    "id": "subject_celc",
                    "role": "top_actor_card",
                    "bbox": [207, 22, 625, 170],
                },
            ],
            "items": [
                {
                    "display_text": "中电联（科技服务中心）",
                    "source_text": "中电联（科技服务中心）",
                    "container_id": "subject_celc",
                    "bbox": [320, 48, 575, 76],
                    "role": "actor_title",
                    "font_size": 18,
                    "font_weight": "700",
                },
                {
                    "display_text": "统筹标准｜监管指导",
                    "source_text": "行业统筹、标准制定、监管指导",
                    "container_id": "subject_celc",
                    "bbox": [320, 92, 545, 114],
                    "role": "actor_summary",
                    "font_size": 14,
                },
                {
                    "display_text": "公共服务落地｜资源整合",
                    "source_text": "公共服务落地、核心资源整合",
                    "container_id": "subject_celc",
                    "bbox": [320, 120, 560, 142],
                    "role": "actor_summary",
                    "font_size": 14,
                },
                {
                    "display_text": "保障公共属性",
                    "source_text": "保障行业公共属性",
                    "container_id": "subject_celc",
                    "bbox": [320, 148, 455, 170],
                    "role": "actor_summary",
                    "font_size": 14,
                    "font_weight": "700",
                },
            ],
        }
    )

    layout_plan = build_layout_plan(plan)
    planned = apply_layout_plan(plan, layout_plan)

    assert {item["strategy"] for item in layout_plan["items"]} == {"stack_text_group_with_vertical_padding"}
    assert planned["items"][0]["bbox"][1] > 36
    assert planned["items"][-1]["bbox"][3] < 156
    assert all(item["v_align"] == "middle" for item in planned["items"])
    assert all(item["align"] == "left" for item in planned["items"])
    assert planned["items"][1]["bbox"][0] == planned["items"][2]["bbox"][0]
    reserved = layout_plan["items"][0]["reserved_zones"]
    assert reserved and reserved[0]["name"] == "left_icon_zone"
    assert layout_plan["items"][0]["group_align"] == "left"
    assert layout_plan["items"][1]["semantic_compression_level"] == "phrase_label"


def test_layout_plan_reserves_left_icon_zone_for_public_service_panel() -> None:
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {
                    "id": "public_service",
                    "role": "middle_service_panel",
                    "bbox": [180, 254, 640, 414],
                },
            ],
            "items": [
                {
                    "display_text": "公益属性服务（免费）",
                    "source_text": "公益属性服务（免费）",
                    "container_id": "public_service",
                    "bbox": [280, 274, 500, 302],
                    "role": "panel_title",
                    "font_size": 17,
                },
                {
                    "display_text": "基础信息发布",
                    "source_text": "成果基础信息发布",
                    "container_id": "public_service",
                    "bbox": [300, 318, 420, 338],
                    "role": "service_item",
                    "font_size": 13,
                },
                {
                    "display_text": "基础存证",
                    "source_text": "基础存证",
                    "container_id": "public_service",
                    "bbox": [495, 318, 575, 338],
                    "role": "service_item",
                    "font_size": 13,
                },
            ],
        }
    )

    layout_plan = build_layout_plan(plan)
    title = layout_plan["items"][0]
    service = layout_plan["items"][1]

    assert any(zone["name"] == "left_icon_zone" for zone in service["reserved_zones"])
    assert title["bbox"][0] >= 280
    assert service["strategy"] == "service_grid_avoid_icon_zone"
    assert service["bbox"][0] >= 280


def test_layout_plan_reflows_service_panel_away_from_right_icon_zone() -> None:
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {
                    "id": "market_service",
                    "role": "middle_service_panel",
                    "bbox": [705, 254, 1200, 414],
                },
            ],
            "items": [
                {
                    "display_text": "市场化增值服务（收费）",
                    "source_text": "市场化增值服务（收费）",
                    "container_id": "market_service",
                    "bbox": [785, 274, 1035, 302],
                    "role": "panel_title",
                    "font_size": 17,
                    "font_weight": "700",
                },
                {
                    "display_text": "价值评估",
                    "source_text": "成果价值评估",
                    "container_id": "market_service",
                    "bbox": [785, 318, 870, 338],
                    "role": "service_item",
                    "font_size": 13,
                },
                {
                    "display_text": "精准匹配",
                    "source_text": "精准匹配",
                    "container_id": "market_service",
                    "bbox": [960, 318, 1045, 338],
                    "role": "service_item",
                    "font_size": 13,
                },
                {
                    "display_text": "深度数据",
                    "source_text": "深度数据服务",
                    "container_id": "market_service",
                    "bbox": [1080, 318, 1165, 338],
                    "role": "service_item",
                    "font_size": 13,
                },
                {
                    "display_text": "隐私计算",
                    "source_text": "隐私计算服务",
                    "container_id": "market_service",
                    "bbox": [785, 350, 870, 370],
                    "role": "service_item",
                    "font_size": 13,
                },
                {
                    "display_text": "数据建模",
                    "source_text": "定制化数据建模",
                    "container_id": "market_service",
                    "bbox": [960, 350, 1045, 370],
                    "role": "service_item",
                    "font_size": 13,
                },
                {
                    "display_text": "知产链服务",
                    "source_text": "知识产权全链条服务",
                    "container_id": "market_service",
                    "bbox": [785, 382, 885, 402],
                    "role": "service_item",
                    "font_size": 13,
                },
            ],
        }
    )

    layout_plan = build_layout_plan(plan)
    planned = apply_layout_plan(plan, layout_plan)
    depth_data = next(item for item in planned["items"] if item["text"] == "深度数据")
    service_items = [item for item in layout_plan["items"] if item["role"] == "service_item"]

    assert {item["strategy"] for item in service_items} == {"service_grid_avoid_icon_zone"}
    assert depth_data["bbox"][2] <= 1070
    assert depth_data["bbox"][0] == planned["items"][1]["bbox"][0]
    assert planned["items"][0]["bbox"][2] <= 1070
    assert any(zone["name"] == "right_icon_zone" for zone in service_items[0]["reserved_zones"])


def test_layout_plan_centers_profit_index_in_marker_not_raw_ocr_box() -> None:
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {
                    "id": "profit_4",
                    "role": "profit_card",
                    "bbox": [668, 485, 852, 699],
                },
            ],
            "items": [
                {
                    "display_text": "4",
                    "source_text": "4",
                    "container_id": "profit_4",
                    "bbox": [695, 500, 715, 520],
                    "role": "index",
                    "font_size": 13,
                    "font_weight": "700",
                    "align": "center",
                    "lock_bbox": True,
                },
            ],
        }
    )

    layout_plan = build_layout_plan(plan)
    planned = apply_layout_plan(plan, layout_plan)
    box = planned["items"][0]["bbox"]
    center_x = (box[0] + box[2]) / 2
    center_y = (box[1] + box[3]) / 2

    assert layout_plan["items"][0]["strategy"] == "center_in_index_marker"
    assert box[2] - box[0] >= 27
    assert center_x < 695
    assert center_y > 508
    assert planned["items"][0]["v_align"] == "middle"
    assert planned["items"][0]["container_safe_bbox"] == planned["items"][0]["bbox"]


def test_layout_plan_partitions_profit_title_and_body_regions() -> None:
    plan = normalize_semantic_plan(
        {
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {
                    "id": "profit_1",
                    "role": "profit_card",
                    "bbox": [158, 485, 322, 699],
                },
            ],
            "items": [
                {
                    "display_text": "增值技术服务",
                    "source_text": "增值技术服务收入",
                    "container_id": "profit_1",
                    "bbox": [170, 565, 315, 588],
                    "role": "profit_title",
                    "font_size": 14,
                },
                {
                    "display_text": "评估｜匹配｜隐私计算",
                    "source_text": "按次/按项目收取评估、匹配、隐私计算等服务费",
                    "container_id": "profit_1",
                    "bbox": [170, 612, 315, 635],
                    "role": "profit_body",
                    "font_size": 12,
                },
                {
                    "display_text": "按次/项目收费",
                    "source_text": "按次/按项目收取服务费",
                    "container_id": "profit_1",
                    "bbox": [180, 650, 305, 672],
                    "role": "profit_body",
                    "font_size": 12,
                },
            ],
        }
    )

    layout_plan = build_layout_plan(plan)
    planned = apply_layout_plan(plan, layout_plan)
    title, body_1, body_2 = planned["items"]

    assert title["layout_strategy"] == "profit_title_centered_in_title_region"
    assert body_1["layout_strategy"] == "profit_body_stack_centered_in_body_region"
    assert title["bbox"][3] < body_1["bbox"][1]
    assert body_1["bbox"][0] == body_2["bbox"][0]
    assert body_1["align"] == "center"
    assert layout_plan["items"][1]["semantic_compression_level"] == "compact_body"


def test_layout_qa_reports_reserved_zone_overlap(tmp_path: Path) -> None:
    background = Image.new("RGB", CANVAS, "#FFFFFF")
    background_path = tmp_path / "background.png"
    background.save(background_path)
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "压住图标",
                "bbox": [100, 100, 180, 125],
                "role": "service_item",
                "container_id": "service",
                "container_role": "middle_service_panel",
                "container_safe_bbox": [90, 90, 220, 150],
                "reserved_zones": [{"name": "left_icon_zone", "bbox": [120, 90, 220, 150], "reason": "test"}],
                "group_id": "service:service_item",
                "group_align": "center",
                "layout_strategy": "service_grid_avoid_icon_zone",
                "lock_bbox": True,
                "v_align": "middle",
            }
        ],
    }
    boxes = build_overlay_boxes(layout, background_path, AlignmentTransform())
    layout_plan = {
        "items": [
            {
                "bbox": [100, 100, 180, 125],
                "role": "service_item",
                "container_safe_bbox": [90, 90, 220, 150],
                "reserved_zones": [{"name": "left_icon_zone", "bbox": [120, 90, 220, 150], "reason": "test"}],
                "group_id": "service:service_item",
                "group_align": "center",
            }
        ]
    }

    qa = build_layout_qa_report(layout_plan, boxes)

    assert qa["warning_count"] == 1
    assert qa["issues"][0]["code"] == "text_intersects_reserved_zone"


def test_layout_plan_skips_safe_bbox_for_uncontained_items(tmp_path: Path) -> None:
    background = Image.new("RGB", CANVAS, "#FFFFFF")
    background_path = tmp_path / "background.png"
    background.save(background_path)
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "数据可信",
                "bbox": [1131, 412, 1193, 430],
                "role": "trust_title",
                "font_size": 11,
                "lock_bbox": True,
            }
        ],
    }

    layout_plan = build_layout_plan(layout)
    planned = apply_layout_plan(layout, layout_plan)
    boxes = build_overlay_boxes(planned, background_path, AlignmentTransform())
    qa = build_layout_qa_report(layout_plan, boxes)

    assert layout_plan["items"][0]["container_safe_bbox"] is None
    assert [issue["code"] for issue in qa["issues"]] == []


def test_text_style_profile_learns_full_image_typography_without_owning_geometry() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "律师事务所 / 知识产权代理机构",
                "bbox": [642, 634, 855, 654],
                "role": "service_item",
                "font_size": 12,
                "font_weight": "700",
                "fill": "#0B5FD6",
                "align": "center",
            }
        ],
    }

    profile = build_text_style_profile(layout)

    assert profile["geometry_policy"] == "learn_typography_grouping_and_rhythm_but_do_not_use_ocr_ink_bbox_as_final_container"
    assert profile["role_profiles"]["service_item"]["font_size_avg"] == 12
    assert profile["role_profiles"]["service_item"]["fills"] == ["#0B5FD6"]
    assert profile["items"][0]["bbox"] == [642.0, 634.0, 855.0, 654.0]


def test_inferred_stage_card_uses_full_style_safe_area_instead_of_ocr_width() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {"text": "1", "bbox": [219, 73, 241, 97], "role": "index", "font_size": 14, "align": "center"},
            {"text": "研发", "bbox": [255, 75, 312, 99], "role": "stage_label", "font_size": 13, "align": "left"},
            {
                "text": "研发过程产生的创新成果",
                "bbox": [254, 118, 346, 195],
                "role": "stage_body",
                "font_size": 9.5,
                "align": "left",
            },
            {"text": "2", "bbox": [396, 73, 418, 97], "role": "index", "font_size": 14, "align": "center"},
            {"text": "申请", "bbox": [430, 75, 488, 99], "role": "stage_label", "font_size": 13, "align": "left"},
            {
                "text": "申请材料；提交与受理信息",
                "bbox": [426, 118, 518, 195],
                "role": "stage_body",
                "font_size": 9.5,
                "align": "left",
            },
        ],
    }

    inferred, report = infer_semantic_containers_from_full_style(layout)
    layout_plan = build_layout_plan(inferred)
    planned = apply_layout_plan(inferred, layout_plan)
    body = planned["items"][2]

    assert report["summary"]["inferred_containers"] >= 2
    assert body["layout_strategy"] == "stage_body_use_card_text_safe_width"
    assert body["bbox"][2] - body["bbox"][0] >= 84
    assert body["bbox"][0] >= 250
    assert body["bbox"][2] < 360
    assert body["text"] == "研发过程产生的创新成果"


def test_stage_body_uses_left_legal_space_before_shrinking_or_wrapping() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {"text": "4", "bbox": [764, 73, 786, 97], "role": "index", "font_size": 14, "align": "center"},
            {"text": "使用", "bbox": [801, 75, 858, 99], "role": "stage_label", "font_size": 13, "align": "left"},
            {
                "text": "许可、转让、实施及产品应用信息；使用范围与场景数据",
                "bbox": [794, 117, 891, 198],
                "role": "stage_body",
                "font_size": 9.2,
                "align": "left",
            },
            {"text": "5", "bbox": [944, 73, 966, 97], "role": "index", "font_size": 14, "align": "center"},
            {"text": "维权", "bbox": [981, 75, 1038, 99], "role": "stage_label", "font_size": 13, "align": "left"},
            {
                "text": "侵权监测与证据收集；行政维权、司法诉讼等",
                "bbox": [974, 117, 1071, 198],
                "role": "stage_body",
                "font_size": 9.0,
                "align": "left",
            },
        ],
    }

    inferred, _ = infer_semantic_containers_from_full_style(layout)
    layout_plan = build_layout_plan(inferred)
    planned = apply_layout_plan(inferred, layout_plan)
    title = planned["items"][1]
    body = planned["items"][2]

    assert title["bbox"][0] > body["bbox"][0]
    assert body["layout_strategy"] == "stage_body_use_card_text_safe_width"
    assert body["bbox"][0] >= 790
    assert body["bbox"][2] <= 895
    assert body["bbox"][2] - body["bbox"][0] >= 88
    assert body["bbox"][3] >= 214
    assert body["bbox"][3] - body["bbox"][1] >= 96


def test_isolated_text_gets_expanded_container_from_nearby_region() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "孤立说明文字",
                "bbox": [500, 300, 560, 318],
                "role": "body_summary",
                "font_size": 10,
                "align": "left",
            }
        ],
    }

    inferred, report = infer_semantic_containers_from_full_style(layout)
    layout_plan = build_layout_plan(inferred)
    planned = apply_layout_plan(inferred, layout_plan)
    item = planned["items"][0]

    assert report["actions"][0]["code"] == "inferred_isolated_text_safe_bbox"
    assert item["container_role"] == "isolated_text_region"
    assert item["bbox"][0] < 500
    assert item["bbox"][2] > 560
    assert item["bbox"] == item["container_safe_bbox"]


def test_inferred_service_card_reuses_group_safe_width_for_short_title() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "司法鉴定机构",
                "bbox": [462, 634, 558, 654],
                "role": "service_item",
                "font_size": 12,
                "align": "center",
            },
            {
                "text": "侵权鉴定",
                "bbox": [484, 671, 548, 690],
                "role": "service_item",
                "font_size": 10,
                "align": "center",
            },
            {
                "text": "律师事务所 / 知识产权代理机构",
                "bbox": [642, 634, 855, 654],
                "role": "service_item",
                "font_size": 12,
                "align": "center",
            },
            {
                "text": "侵权投诉、行政维权、司法诉讼等全流程在线服务",
                "bbox": [596, 671, 900, 690],
                "role": "service_item",
                "font_size": 10,
                "align": "center",
            },
        ],
    }

    inferred, _ = infer_semantic_containers_from_full_style(layout)
    layout_plan = build_layout_plan(inferred)
    planned = apply_layout_plan(inferred, layout_plan)
    title = planned["items"][2]

    assert title["layout_strategy"] == "service_text_use_card_safe_width"
    assert title["bbox"][0] <= 596
    assert title["bbox"][2] >= 900
    assert title["text"] == "律师事务所 / 知识产权代理机构"


def test_inferred_process_chain_card_keeps_body_inside_its_card_not_arrow_gap() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "数据授权",
                "bbox": [225, 333, 284, 355],
                "role": "chain_label",
                "font_size": 11,
                "align": "center",
            },
            {
                "text": "授权范围、使用期限、访问权限精细化管控",
                "bbox": [197, 374, 294, 437],
                "role": "chain_body",
                "font_size": 9.3,
                "align": "center",
            },
            {
                "text": "受控接入",
                "bbox": [349, 333, 408, 355],
                "role": "chain_label",
                "font_size": 11,
                "align": "center",
            },
            {
                "text": "可用不可见、用途可控可计量",
                "bbox": [319, 375, 417, 425],
                "role": "chain_body",
                "font_size": 9.4,
                "align": "center",
            },
        ],
    }

    inferred, report = infer_semantic_containers_from_full_style(layout)
    layout_plan = build_layout_plan(inferred)
    planned = apply_layout_plan(inferred, layout_plan)
    first_body = planned["items"][1]
    second_body = planned["items"][3]

    assert any(action["code"] == "inferred_process_chain_card_safe_bbox" for action in report["actions"])
    assert first_body["container_role"] == "process_chain_card"
    assert first_body["layout_strategy"] == "process_chain_body_use_card_safe_area"
    assert first_body["bbox"][0] >= 190
    assert first_body["bbox"][2] <= 302
    assert second_body["bbox"][0] >= 315
    assert second_body["bbox"][2] <= 426
    assert first_body["bbox"][2] < second_body["bbox"][0]


def test_typesetting_policy_preserves_explicit_full_image_font_size() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "授权范围 / 期限 / 计量精细化管控，“可用不可见、用途可控可计量”",
                "source_text": "授权范围 / 期限 / 计量精细化管控，“可用不可见、用途可控可计量”",
                "bbox": [1132, 512, 1260, 544],
                "role": "trust_body",
                "font_size": 7.2,
                "align": "center",
            }
        ],
    }

    optimized, report = apply_typesetting_policy(layout)
    item = optimized["items"][0]

    assert item["word_wrap"] is True
    assert item["align"] == "left"
    assert item["v_align"] == "top"
    assert item["font_size"] == 7.2
    assert item["display_text"] == item["text"]
    assert item["text"] == "授权范围 / 期限 / 计量精细化管控，“可用不可见、用途可控可计量”"
    assert item["source_text"].startswith("授权范围")
    assert report["summary"]["auto_wrapped"] == 1
    assert report["summary"]["font_floor_applied"] == 0
    assert report["summary"]["semantic_text_preserved"] == 1


def test_typesetting_policy_preserves_semantic_short_sentence_without_hard_breaks() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "研发过程产生的创新成果",
                "bbox": [254, 117, 346, 152],
                "role": "stage_body",
                "font_size": 9.2,
            }
        ],
    }

    optimized, report = apply_typesetting_policy(layout)
    item = optimized["items"][0]

    assert item["text"] == "研发过程产生的创新成果"
    assert "的\n" not in item["text"]
    assert not item["text"].endswith("\n设计")
    assert report["summary"]["semantic_text_preserved"] == 1


def test_typesetting_policy_reflows_full_image_hard_linebreaks_when_safe_area_can_hold_source() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "· 研发过程产生的\n  创新成果\n· 实验数据、设计\n  文档等",
                "display_text": "· 研发过程产生的\n  创新成果\n· 实验数据、设计\n  文档等",
                "source_text": "研发过程产生的创新成果；实验数据、设计文档等",
                "bbox": [254, 117, 346, 193],
                "container_safe_bbox": [236, 72, 370, 205],
                "role": "stage_body",
                "font_size": 9.5,
            }
        ],
    }

    optimized, report = apply_typesetting_policy(layout)
    item = optimized["items"][0]

    assert item["text"] == "研发过程产生的创新成果；实验数据、设计文档等"
    assert "\n" not in item["text"]
    assert item["word_wrap"] is True
    assert report["summary"]["source_text_restored_when_fit"] == 1
    assert report["summary"]["hard_linebreaks_preserved"] == 0


def test_typesetting_policy_normalizes_full_image_continuation_breaks_to_natural_text_flow() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "· 研发过程产生的\n  创新成果\n· 实验数据、设计\n  文档等",
                "display_text": "· 研发过程产生的\n  创新成果\n· 实验数据、设计\n  文档等",
                "bbox": [254, 117, 346, 193],
                "container_safe_bbox": [236, 72, 370, 205],
                "role": "stage_body",
                "font_size": 9.5,
            }
        ],
    }

    optimized, report = apply_typesetting_policy(layout)
    item = optimized["items"][0]

    assert item["text"] == "· 研发过程产生的创新成果\n· 实验数据、设计文档等"
    assert item["word_wrap"] is True
    assert report["summary"]["hard_linebreaks_normalized"] == 1
    assert report["summary"]["hard_linebreaks_preserved"] == 0


def test_typesetting_policy_preserves_linebreaks_only_when_semantically_locked() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "第一段\n第二段",
                "bbox": [100, 100, 260, 150],
                "role": "stage_body",
                "font_size": 9.5,
                "preserve_linebreaks": True,
            }
        ],
    }

    optimized, report = apply_typesetting_policy(layout)

    assert optimized["items"][0]["text"] == "第一段\n第二段"
    assert optimized["items"][0]["word_wrap"] is False
    assert report["summary"]["explicit_linebreaks_preserved"] == 1


def test_typesetting_policy_keeps_stage_body_phrases_continuous_by_default() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "侵权监测与证据收集",
                "display_text": "侵权监测与证据收集",
                "source_text": "侵权监测与证据收集；行政维权、司法诉讼等",
                "bbox": [970, 117, 1071, 205],
                "container_safe_bbox": [970, 72, 1071, 205],
                "role": "stage_body",
                "font_size": 9.0,
            }
        ],
    }

    optimized, report = apply_typesetting_policy(layout)
    item = optimized["items"][0]

    assert item["text"] == "侵权监测与证据收集；行政维权、司法诉讼等"
    assert "\n" not in item["text"]
    assert item["word_wrap"] is True
    assert report["summary"]["semantic_clause_breaks_inserted"] == 0
    assert report["summary"]["hard_linebreaks_preserved"] == 0


def test_typesetting_policy_does_not_hard_break_short_enumerations_after_dunhao() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "许可、转让、实施及产品应用信息",
                "display_text": "许可、转让、实施及产品应用信息",
                "source_text": "许可、转让、实施及产品应用信息；使用范围与场景数据",
                "bbox": [790, 117, 891, 205],
                "container_safe_bbox": [790, 72, 891, 205],
                "role": "stage_body",
                "font_size": 9.2,
            }
        ],
    }

    optimized, report = apply_typesetting_policy(layout)
    item = optimized["items"][0]

    assert item["text"] == "许可、转让、实施及产品应用信息；使用范围与场景数据"
    assert "许可、\n转让" not in item["text"]
    assert "\n" not in item["text"]
    assert item["word_wrap"] is True
    assert report["summary"]["semantic_clause_breaks_inserted"] == 0


def test_typesetting_policy_restores_continuous_source_for_narrow_actor_and_terminal_chain() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "专利、软著、集成电路\n布图设计、技术秘密等\n知识产权数据，覆盖\n研发、申请、授权、使用、\n维权五阶段",
                "display_text": "专利、软著、集成电路\n布图设计、技术秘密等\n知识产权数据，覆盖\n研发、申请、授权、使用、\n维权五阶段",
                "source_text": "专利、软著、集成电路布图设计、技术秘密等知识产权数据，覆盖研发、申请、授权、使用、维权五阶段",
                "bbox": [18, 185, 142, 294],
                "role": "actor_summary",
                "font_size": 10.5,
            },
            {
                "text": "目录发布\n主体认证\n收益结算\n非本场景原文\n展开重点",
                "display_text": "目录发布\n主体认证\n收益结算\n非本场景原文\n展开重点",
                "source_text": "目录发布；主体认证；收益结算；非本场景原文展开重点",
                "bbox": [979, 324, 1046, 444],
                "role": "chain_body",
                "font_size": 10,
                "align": "center",
            },
        ],
    }

    optimized, report = apply_typesetting_policy(layout)

    assert optimized["items"][0]["text"] == "专利、软著、集成电路布图设计、技术秘密等知识产权数据，覆盖研发、申请、授权、使用、维权五阶段"
    assert optimized["items"][1]["text"] == "目录发布；主体认证；收益结算；非本场景原文展开重点"
    assert all(item["word_wrap"] is True for item in optimized["items"])
    assert report["summary"]["source_text_restored_when_fit"] == 2
    assert "semantic_linebreaks_kept" not in report["summary"]
    assert report["summary"]["hard_linebreaks_preserved"] == 0


def test_inferred_side_actor_and_terminal_chain_use_real_safe_area() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "知识产权权利人",
                "bbox": [28, 158, 133, 181],
                "role": "actor_title",
                "font_size": 14,
                "align": "center",
            },
            {
                "text": "专利、软著、集成电路\n布图设计、技术秘密等\n知识产权数据，覆盖\n研发、申请、授权、使用、\n维权五阶段",
                "bbox": [18, 185, 142, 294],
                "role": "actor_summary",
                "font_size": 10.5,
                "align": "center",
            },
            {
                "text": "知识产权权利人",
                "bbox": [1131, 158, 1254, 181],
                "role": "actor_title",
                "font_size": 14,
                "align": "center",
            },
            {
                "text": "接受全周期保护服务的\n受益者，获得权属证据与\n侵权监测等全流程服务，\n高效保障合法权益",
                "bbox": [1124, 190, 1260, 272],
                "role": "actor_summary",
                "font_size": 10.8,
                "align": "center",
            },
            {
                "text": "目录发布\n主体认证\n收益结算\n非本场景原文\n展开重点",
                "bbox": [979, 324, 1046, 444],
                "role": "chain_body",
                "font_size": 10,
                "align": "center",
            },
        ],
    }

    inferred, report = infer_semantic_containers_from_full_style(layout)
    left_summary = inferred["items"][1]
    right_summary = inferred["items"][3]
    terminal = inferred["items"][4]

    assert report["summary"]["inferred_containers"] >= 3
    assert left_summary["container_role"] == "side_actor_panel"
    assert left_summary["container_safe_bbox"][0] <= 18.0
    assert left_summary["container_safe_bbox"][2] >= 148.0
    assert left_summary["container_safe_bbox"][3] >= 306.0
    assert right_summary["container_role"] == "side_actor_panel"
    assert right_summary["container_safe_bbox"][0] <= 1110.0
    assert right_summary["container_safe_bbox"][2] >= 1260.0
    assert right_summary["container_safe_bbox"][3] >= 306.0
    assert terminal["container_role"] == "chain_terminal_note"
    assert terminal["container_safe_bbox"][0] <= 965.0
    assert terminal["container_safe_bbox"][1] <= 314.0
    assert terminal["container_safe_bbox"][3] >= 454.0

    layout_plan = build_layout_plan(inferred)
    planned = apply_layout_plan(inferred, layout_plan)

    assert planned["items"][1]["bbox"] == planned["items"][1]["container_safe_bbox"]
    assert planned["items"][3]["bbox"] == planned["items"][3]["container_safe_bbox"]
    assert planned["items"][4]["bbox"] == planned["items"][4]["container_safe_bbox"]


def test_typesetting_policy_restores_source_text_when_safe_area_can_hold_it() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "全周期存证固化权属证据",
                "display_text": "全周期存证固化权属证据",
                "source_text": "全生命周期存证固化权属证据",
                "bbox": [1132, 432, 1260, 458],
                "container_safe_bbox": [1129, 420, 1268, 458],
                "role": "trust_body",
                "font_size": 7.1,
            }
        ],
    }

    optimized, report = apply_typesetting_policy(layout)

    assert optimized["items"][0]["text"] == "全生命周期存证固化权属证据"
    assert report["summary"]["source_text_restored_when_fit"] == 1


def test_typesetting_policy_keeps_display_text_when_source_text_will_not_fit() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "完整服务",
                "display_text": "完整服务",
                "source_text": "这是一段明显过长且无法在极小安全区中保持可读性的完整原文说明",
                "bbox": [100, 100, 150, 112],
                "container_safe_bbox": [100, 100, 150, 112],
                "role": "trust_body",
                "font_size": 9.0,
            }
        ],
    }

    optimized, report = apply_typesetting_policy(layout)

    assert optimized["items"][0]["text"] == "完整服务"
    assert report["summary"]["source_text_restored_when_fit"] == 0


def test_typesetting_policy_shrinks_shared_container_siblings_instead_of_colliding() -> None:
    """Real-page regression (page014, 2026-07-03): two actor_summary lines shared
    one container's text_safe_bbox (the whole card, 517x148). Checking each
    line's long source_text against that whole (wide) shared box let
    _fit_font_size_to_box conclude the original 14pt font already fit on one
    line, so font_size was left unchanged at 14 for both. At render time,
    against each item's real (much narrower, ~226px) column width, 14pt no
    longer fit on one line, so both wrapped to two lines and expanded into
    each other -- a ~40% height overlap.

    The fix checks each item against its own (narrower) authored bbox instead
    of the wide shared box whenever a sibling in the same container is also a
    restoration candidate, and persists whatever font size that check used.
    Both lines still restore their full source_text (that content policy is
    unchanged), but now at a font small enough to actually render on one line
    within their real column width, so they no longer collide."""
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "display_text": "联合出资，专业运营",
                "source_text": "联合行业头部企业、技术服务商共同出资成立",
                "bbox": [760, 112, 955, 134],
                "container_id": "subject_market_company",
                "container_text_safe_bbox": [653, 22, 1170, 170],
                "role": "actor_summary",
                "font_size": 14,
            },
            {
                "display_text": "运维推广｜生态建设",
                "source_text": "负责日常运营、技术维护、市场推广、生态建设",
                "bbox": [760, 140, 970, 162],
                "container_id": "subject_market_company",
                "container_text_safe_bbox": [653, 22, 1170, 170],
                "role": "actor_summary",
                "font_size": 14,
            },
        ],
    }

    optimized, report = apply_typesetting_policy(layout)

    assert optimized["items"][0]["text"] == "联合行业头部企业、技术服务商共同出资成立"
    assert optimized["items"][1]["text"] == "负责日常运营、技术维护、市场推广、生态建设"
    assert report["summary"]["source_text_restored_when_fit"] == 2
    # Checked against the item's own ~195px-wide bbox rather than the shared
    # 517px-wide container, both must shrink well below the original 14pt to
    # fit their real column on one line.
    assert optimized["items"][0]["font_size"] < 12.0
    assert optimized["items"][1]["font_size"] < 12.0


def test_typesetting_policy_skips_restoration_when_own_bbox_cannot_hold_it() -> None:
    """When an item's own (narrow) bbox genuinely cannot hold its source_text even
    at the role's font floor, restoration must be skipped -- not silently
    accepted against the wider shared container box, which is exactly the
    mistake that let two page014 sentences collide."""
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "display_text": "成果转化",
                "source_text": "成果转化培训咨询费用及配套服务的详细说明文字非常非常长完全放不下",
                "bbox": [885, 612, 1005, 635],
                "container_id": "profit_5",
                "container_text_safe_bbox": [872, 555, 1016, 690],
                "role": "profit_body",
                "font_size": 12,
            },
            {
                "display_text": "知产管理咨询",
                "source_text": "知产管理等领域培训咨询费",
                "bbox": [880, 650, 1010, 672],
                "container_id": "profit_5",
                "container_text_safe_bbox": [872, 555, 1016, 690],
                "role": "profit_body",
                "font_size": 12,
            },
        ],
    }

    optimized, report = apply_typesetting_policy(layout)

    assert optimized["items"][0]["text"] == "成果转化"
    assert report["summary"]["source_text_restoration_skipped_for_shared_container"] >= 1


def test_estimated_text_width_uses_bundled_font_metrics_when_available() -> None:
    """When a real font file is bundled under templates/fonts/ (e.g. the
    Microsoft YaHei the user copied in from their local Office install on
    2026-07-03), width estimation must measure against its actual glyph
    advances instead of the fixed per-character-ratio heuristic. Measured
    against the bundled font directly: CJK glyphs advance ~1.0x font size and
    ASCII glyphs ~0.605x -- both wider than the old heuristic's 0.95x/0.52x.
    When no bundled font is available (e.g. running this repo on a host that
    hasn't supplied one), the same call must still return a sane, positive
    estimate via the heuristic fallback -- this test doesn't require a font
    to be present to pass, it just checks whichever path is active behaves
    consistently."""
    cjk_width = _estimated_text_width("公益市场化", 100.0)
    ascii_width = _estimated_text_width("ABCDE", 100.0)

    assert cjk_width > 0
    assert ascii_width > 0
    # A CJK glyph is always at least as wide as a Latin one in this typeface
    # family, regardless of which measurement path is active.
    assert (cjk_width / 5) > (ascii_width / 5)

    if _bundled_font_path():
        # Real-metric path: assert against the values measured directly from
        # the bundled font (see module docstring/workflow note), with slack
        # for rounding.
        assert 90.0 <= cjk_width / 5 <= 110.0
        assert 50.0 <= ascii_width / 5 <= 70.0
    else:
        # Heuristic fallback path: exact fixed ratios.
        assert cjk_width == 5 * 100.0 * 0.95
        assert ascii_width == 5 * 100.0 * 0.52


def test_typesetting_policy_skips_restoration_when_siblings_share_identical_source_text() -> None:
    """Real-page regression (page014, label_dual_track container, 2026-07-03):
    two sibling items were authored with distinct, shortened display_text but
    both carry the *same* source_text (one shared original sentence split
    across a title-like line and a body-like line). Each one independently
    passes the per-item fit check, so the old code restored the identical
    full sentence into both boxes -- a content duplication, not a geometry
    collision, so no overlap check catches it.

    Restoration must be skipped for every item in such a group, leaving each
    one's originally authored, distinct display_text untouched."""
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "display_text": "公益+市场化双轨",
                "source_text": "坚持公益属性与市场化运营双轨并行推进模式",
                "bbox": [420, 500, 620, 524],
                "container_id": "label_dual_track",
                "container_text_safe_bbox": [410, 490, 900, 560],
                "role": "label_title",
                "font_size": 14,
            },
            {
                "display_text": "统筹公益保障与市场活力",
                "source_text": "坚持公益属性与市场化运营双轨并行推进模式",
                "bbox": [420, 528, 700, 552],
                "container_id": "label_dual_track",
                "container_text_safe_bbox": [410, 490, 900, 560],
                "role": "label_body",
                "font_size": 12,
            },
        ],
    }

    optimized, report = apply_typesetting_policy(layout)

    assert optimized["items"][0]["text"] == "公益+市场化双轨"
    assert optimized["items"][1]["text"] == "统筹公益保障与市场活力"
    assert report["summary"]["source_text_restored_when_fit"] == 0
    assert report["summary"]["source_text_restoration_skipped_for_duplicate_sibling_text"] == 2


def test_typesetting_policy_persists_fitted_font_size_when_restoring_source_text() -> None:
    """The fit check may shrink the font to make a candidate sentence fit; that
    shrunk size must be written back onto the item, otherwise downstream
    rendering re-fits the restored (longer) text against the old, larger
    preferred size and produces a different height than the check validated."""
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "display_text": "全周期存证",
                "source_text": "全生命周期存证固化权属证据",
                "bbox": [1132, 432, 1260, 458],
                "container_safe_bbox": [1129, 420, 1268, 458],
                "role": "trust_body",
                "font_size": 14.0,
            }
        ],
    }

    optimized, report = apply_typesetting_policy(layout)

    assert optimized["items"][0]["text"] == "全生命周期存证固化权属证据"
    assert report["summary"]["source_text_restored_when_fit"] == 1
    assert optimized["items"][0]["font_size"] <= 14.0


def test_typesetting_policy_normalizes_overfull_hard_breaks_without_shortening_text() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "第一条说明文字很长\n第二条说明文字很长\n第三条说明文字很长",
                "bbox": [100, 100, 190, 132],
                "role": "trust_body",
                "font_size": 9.0,
            }
        ],
    }

    optimized, report = apply_typesetting_policy(layout)
    item = optimized["items"][0]

    assert item["text"] == "第一条说明文字很长第二条说明文字很长第三条说明文字很长"
    assert item["word_wrap"] is True
    assert report["summary"]["hard_linebreaks_normalized"] == 1
    assert report["summary"]["semantic_text_preserved"] == 1


def test_layout_qa_reports_text_density_and_font_floor() -> None:
    box = {
        "text": "这是一个过长的窄栏说明文字，需要AI重新改写后再放入页面",
        "x": 100,
        "y": 100,
        "w": 90,
        "h": 12,
        "font_size": 7.0,
        "font_family": "Arial",
        "fill": "#111827",
        "role": "product_body",
        "word_wrap": True,
        "source_text": "这是一个过长的窄栏说明文字，需要AI重新改写后再放入页面",
    }
    from dual_image_rebuild_pptx import OverlayTextBox  # noqa: E402

    qa = build_layout_qa_report({"items": [{"role": "product_body"}]}, [OverlayTextBox(**box)])
    codes = {issue["code"] for issue in qa["issues"]}

    assert "font_below_role_minimum" in codes
    assert "text_vertical_overflow" in codes
    assert "needs_semantic_revision" in codes


def test_layout_qa_reports_vertical_text_overflow() -> None:
    from dual_image_rebuild_pptx import OverlayTextBox  # noqa: E402

    box = OverlayTextBox(
        text="第一行\n第二行\n第三行",
        x=100,
        y=100,
        w=120,
        h=24,
        font_size=9.0,
        font_family="Arial",
        fill="#111827",
        role="trust_body",
        word_wrap=True,
    )

    qa = build_layout_qa_report({"items": [{"role": "trust_body"}]}, [box])
    codes = {issue["code"] for issue in qa["issues"]}

    assert "text_vertical_overflow" in codes


def test_layout_qa_allows_wide_section_titles() -> None:
    from dual_image_rebuild_pptx import OverlayTextBox  # noqa: E402

    box = OverlayTextBox(
        text="技术支撑方：提供全网侵权监测技术，抓取侵权证据",
        x=400,
        y=240,
        w=460,
        h=24,
        font_size=12.5,
        font_family="Arial",
        fill="#0B5FD6",
        role="section_title",
    )

    qa = build_layout_qa_report({"items": [{"role": "section_title"}]}, [box])

    assert [issue["code"] for issue in qa["issues"]] == []


def test_overlay_box_uses_wrapped_line_width_for_body_font_floor(tmp_path: Path) -> None:
    background = Image.new("RGB", CANVAS, "#FFFFFF")
    background_path = tmp_path / "background.png"
    background.save(background_path)
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "授权范围期限计量\n精细管控用途可控",
                "bbox": [1132, 512, 1260, 544],
                "role": "trust_body",
                "font_size": 9.0,
                "word_wrap": True,
                "lock_bbox": True,
            }
        ],
    }

    boxes = build_overlay_boxes(layout, background_path, AlignmentTransform())

    assert boxes[0].font_size >= 9.0


def test_overlay_box_fits_wrapped_body_by_height_without_hard_linebreaks(tmp_path: Path) -> None:
    background = Image.new("RGB", CANVAS, "#FFFFFF")
    background_path = tmp_path / "background.png"
    background.save(background_path)
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "接受全周期保护服务的受益者，获得权属证据与侵权监测等全流程服务，高效保障合法权益",
                "bbox": [1124, 190, 1260, 272],
                "role": "actor_summary",
                "font_size": 10.8,
                "word_wrap": True,
                "lock_bbox": True,
            }
        ],
    }

    boxes = build_overlay_boxes(layout, background_path, AlignmentTransform())
    qa = build_layout_qa_report({"items": [{"role": "actor_summary"}]}, boxes)

    assert "\n" not in boxes[0].text
    assert 10.0 < boxes[0].font_size <= 10.8
    assert "text_vertical_overflow" not in {issue["code"] for issue in qa["issues"]}


def test_overlay_box_expands_downward_inside_safe_area_before_shrinking_font(tmp_path: Path) -> None:
    background = Image.new("RGB", CANVAS, "#FFFFFF")
    background_path = tmp_path / "background.png"
    background.save(background_path)
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "接受全周期保护服务的受益者，获得权属证据与侵权监测等全流程服务，高效保障合法权益",
                "bbox": [1124, 190, 1260, 212],
                "container_safe_bbox": [1110, 190, 1268, 306],
                "role": "actor_summary",
                "font_size": 10.8,
                "word_wrap": True,
                "lock_bbox": True,
                "container_fit": True,
                "v_align": "top",
            }
        ],
    }

    boxes = build_overlay_boxes(layout, background_path, AlignmentTransform())

    assert boxes[0].h > 22
    assert boxes[0].y == 190
    assert boxes[0].y + boxes[0].h <= 306
    assert boxes[0].font_size == 10.8


def test_build_overlay_boxes_clamp_before_expand_does_not_reclip_expanded_box(tmp_path: Path) -> None:
    """build_overlay_boxes(...) runs _clamp_box_to_bbox before
    _expand_wrapped_box_height_inside_safe_area, not the other order some past
    docs described. Force clamp to actually move the box (both x and y are
    outside the safe area here, not just already-inside-and-unchanged like the
    test above), then confirm expansion still grows height correctly afterward
    and the final box never leaves the safe area -- locking the invariant that
    lets clamp-then-expand be safe instead of a future refactor accidentally
    re-clipping an already-expanded box."""
    background = Image.new("RGB", CANVAS, "#FFFFFF")
    background_path = tmp_path / "background.png"
    background.save(background_path)
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "该阶段需要保存合同、原始设计稿、时间戳等证据材料，以便后续维权举证使用",
                "bbox": [190, 280, 520, 310],
                "container_safe_bbox": [200, 300, 500, 460],
                "role": "stage_body",
                "font_size": 11.0,
                "word_wrap": True,
                "lock_bbox": True,
                "container_fit": True,
                "v_align": "top",
            }
        ],
    }

    boxes = build_overlay_boxes(layout, background_path, AlignmentTransform())
    box = boxes[0]

    # Clamp actually fired: the pre-clamp bbox was wider than and above the
    # safe area, so x/y must have moved to the safe-area edges.
    assert box.x == 200
    assert round(box.x + box.w) == 500
    assert box.y == 300
    # Expand still grew the box past its post-clamp height, and stayed inside
    # the safe area's bottom edge rather than being re-clipped or escaping it.
    assert box.h > 30
    assert box.y + box.h <= 460


def test_layout_plan_separates_trust_title_and_body_inside_card_safe_area() -> None:
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "授权可信",
                "bbox": [1132, 489, 1193, 508],
                "container_id": "trust_1",
                "container_role": "trust_card",
                "container_bbox": [1084, 467, 1273, 540],
                "container_safe_bbox": [1129, 485, 1268, 534],
                "container_text_safe_bbox": [1129, 485, 1268, 534],
                "container_has_text_safe_bbox": True,
                "role": "trust_title",
                "font_size": 11.2,
            },
            {
                "text": "授权范围 / 期限 / 计量精细化管控，“可用不可见、用途可控可计量”",
                "bbox": [1132, 508, 1260, 526],
                "container_id": "trust_1",
                "container_role": "trust_card",
                "container_bbox": [1084, 467, 1273, 540],
                "container_safe_bbox": [1129, 485, 1268, 534],
                "container_text_safe_bbox": [1129, 485, 1268, 534],
                "container_has_text_safe_bbox": True,
                "role": "trust_body",
                "font_size": 7.1,
                "word_wrap": True,
            },
        ],
    }

    layout_plan = build_layout_plan(layout)
    planned = apply_layout_plan(layout, layout_plan)
    title = planned["items"][0]
    body = planned["items"][1]

    assert body["bbox"][1] >= title["bbox"][3] + 5
    assert body["bbox"][3] <= 534
    assert body["layout_strategy"] == "trust_text_use_card_safe_width"


def test_export_pptx_writes_newlines_as_separate_paragraphs(tmp_path: Path) -> None:
    from dual_image_rebuild_pptx import OverlayTextBox  # noqa: E402

    background = Image.new("RGB", CANVAS, "#FFFFFF")
    background_path = tmp_path / "background.png"
    background.save(background_path)
    pptx_path = tmp_path / "out.pptx"
    box = OverlayTextBox(
        text="第一行\n第二行",
        x=100,
        y=100,
        w=160,
        h=50,
        font_size=12,
        font_family="Arial",
        fill="#111827",
        word_wrap=True,
    )

    export_pptx(background_path, [box], pptx_path)
    prs = Presentation(pptx_path)
    frame = next(
        shape.text_frame
        for shape in prs.slides[0].shapes
        if getattr(shape, "has_text_frame", False) and shape.text_frame.text.strip()
    )

    assert [paragraph.text for paragraph in frame.paragraphs] == ["第一行", "第二行"]


def test_build_text_content_qa_report_detects_pptx_text_mismatch(tmp_path: Path) -> None:
    background = Image.new("RGB", CANVAS, "#FFFFFF")
    background_path = tmp_path / "background.png"
    background.save(background_path)
    pptx_path = tmp_path / "out.pptx"
    exported_box = OverlayTextBox(
        text="许可、转让、实施及维权",
        x=100,
        y=100,
        w=260,
        h=36,
        font_size=16,
        font_family="Arial",
        fill="#111827",
    )
    export_pptx(background_path, [exported_box], pptx_path)

    ok = build_text_content_qa_report([exported_box], pptx_path)
    assert ok["valid"] is True
    assert ok["checks"]["pptx_text_matches_mapping"] is True

    expected_box = OverlayTextBox(
        text="许可、转让",
        x=100,
        y=100,
        w=260,
        h=36,
        font_size=16,
        font_family="Arial",
        fill="#111827",
    )
    mismatch = build_text_content_qa_report([expected_box], pptx_path)
    assert mismatch["valid"] is False
    assert mismatch["checks"]["pptx_text_matches_mapping"] is False
    assert mismatch["mismatches"][0]["index"] == 0
    assert mismatch["mismatches"][0]["expected"] == "许可、转让"
    assert mismatch["mismatches"][0]["actual"] == "许可、转让、实施及维权"


def test_build_pdf_preview_writes_stable_pdf_and_page_png(tmp_path: Path, monkeypatch) -> None:
    pptx_path = tmp_path / "deck.pptx"
    pptx_path.write_bytes(b"pptx")
    calls: list[list[str]] = []

    def fake_which(name: str) -> str | None:
        return f"/fake/{name}" if name in {"soffice", "pdftoppm"} else None

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if "--convert-to" in cmd:
            (tmp_path / "qa" / "deck.pdf").write_bytes(b"pdf")
        else:
            (tmp_path / "qa" / "page-1.png").write_bytes(b"png")

    monkeypatch.setattr("dual_image_rebuild_pptx.shutil.which", fake_which)
    monkeypatch.setattr("dual_image_rebuild_pptx.subprocess.run", fake_run)

    result = build_pdf_preview(pptx_path, tmp_path / "qa")

    assert result["valid"] is True
    assert Path(result["pdf"]).name == "slide.pdf"
    assert Path(result["page_png"]).name == "page-1.png"
    assert Path(result["pdf"]).is_file()
    assert Path(result["page_png"]).is_file()
    assert calls[0][0] == "/fake/soffice"
    assert calls[1][0] == "/fake/pdftoppm"


def test_build_pdf_preview_warns_when_font_family_missing(tmp_path: Path, monkeypatch) -> None:
    """LibreOffice will silently substitute a fallback font when the requested CJK
    family is not installed, which can make the QA PDF wrap differently than real
    PowerPoint/WPS. build_pdf_preview must surface that instead of staying quiet."""
    pptx_path = tmp_path / "deck.pptx"
    pptx_path.write_bytes(b"pptx")

    def fake_which(name: str) -> str | None:
        return f"/fake/{name}" if name in {"soffice", "pdftoppm", "fc-list"} else None

    def fake_run(cmd, **kwargs):
        if cmd[0] == "/fake/fc-list":
            return subprocess.CompletedProcess(cmd, 0, stdout="Arial\nDejaVu Sans\n", stderr="")
        if "--convert-to" in cmd:
            (tmp_path / "qa" / "deck.pdf").write_bytes(b"pdf")
        else:
            (tmp_path / "qa" / "page-1.png").write_bytes(b"png")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("dual_image_rebuild_pptx.shutil.which", fake_which)
    monkeypatch.setattr("dual_image_rebuild_pptx.subprocess.run", fake_run)

    result = build_pdf_preview(pptx_path, tmp_path / "qa", font_family="Microsoft YaHei")

    assert result["render_engine"] == "libreoffice_soffice"
    assert result["font_family_requested"] == "Microsoft YaHei"
    assert result["font_available"] is False
    assert any(w.startswith("pdf_preview_font_family_unavailable:") for w in result["warnings"])


def test_build_pdf_preview_silent_when_font_check_unavailable(tmp_path: Path, monkeypatch) -> None:
    """When fc-list itself is missing (e.g. stock macOS), font availability is
    unknown, not false -- the missing-font warning must not fire on a guess."""
    pptx_path = tmp_path / "deck.pptx"
    pptx_path.write_bytes(b"pptx")

    def fake_which(name: str) -> str | None:
        return f"/fake/{name}" if name in {"soffice", "pdftoppm"} else None

    def fake_run(cmd, **kwargs):
        if "--convert-to" in cmd:
            (tmp_path / "qa" / "deck.pdf").write_bytes(b"pdf")
        else:
            (tmp_path / "qa" / "page-1.png").write_bytes(b"png")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("dual_image_rebuild_pptx.shutil.which", fake_which)
    monkeypatch.setattr("dual_image_rebuild_pptx.subprocess.run", fake_run)

    result = build_pdf_preview(pptx_path, tmp_path / "qa", font_family="Microsoft YaHei")

    assert result["font_available"] is None
    assert not any(w.startswith("pdf_preview_font_family_unavailable:") for w in result["warnings"])


def test_layout_qa_promotes_font_below_minimum_to_error() -> None:
    box = OverlayTextBox(
        text="窄栏说明文字",
        x=100,
        y=100,
        w=90,
        h=12,
        font_size=6.5,
        font_family="Arial",
        fill="#111827",
        role="product_body",
        word_wrap=True,
    )

    qa = build_layout_qa_report({"items": [{"role": "product_body"}]}, [box])
    font_issues = [issue for issue in qa["issues"] if issue["code"] == "font_below_role_minimum"]

    assert font_issues and font_issues[0]["severity"] == "error"
    assert qa["error_count"] >= 1
    assert qa["valid"] is False


def test_layout_qa_promotes_isolated_text_region_on_body_role_to_error() -> None:
    box = OverlayTextBox(
        text="本应属于某个卡片的正文，却落入了孤立兜底区域",
        x=100,
        y=100,
        w=220,
        h=40,
        font_size=12.0,
        font_family="Arial",
        fill="#111827",
        role="service_item",
        container_role="isolated_text_region",
    )

    qa = build_layout_qa_report({"items": [{"role": "service_item"}]}, [box])
    codes = {(issue["code"], issue["severity"]) for issue in qa["issues"]}

    assert ("isolated_text_region_used_for_body_role", "error") in codes
    assert qa["valid"] is False


def test_layout_qa_warns_when_non_body_role_uses_isolated_text_region() -> None:
    box = OverlayTextBox(
        text="孤立标题",
        x=100,
        y=100,
        w=180,
        h=32,
        font_size=15.0,
        font_family="Arial",
        fill="#111827",
        role="section_title",
        container_role="isolated_text_region",
    )

    qa = build_layout_qa_report({"items": [{"role": "section_title"}]}, [box])
    codes = {(issue["code"], issue["severity"]) for issue in qa["issues"]}

    assert ("isolated_text_region_used_for_non_body_role", "warning") in codes
    assert qa["valid"] is True


def test_production_readiness_rejects_page012_default_profile_without_explicit_containers() -> None:
    report = build_production_readiness_report(
        semantic_plan=None,
        safe_area_report={"profile_source": "page012_default_unverified"},
        layout_qa={"valid": True},
        text_content_qa={"valid": True},
    )

    codes = {issue["code"] for issue in report["issues"]}
    assert report["valid"] is False
    assert "missing_explicit_semantic_containers_for_production" in codes
    assert "page012_default_profile_used_for_production" in codes


def test_layout_qa_keeps_small_safe_bbox_overflow_as_warning_but_escalates_large_overflow() -> None:
    small_overflow_box = OverlayTextBox(
        text="轻微越界",
        x=95,
        y=100,
        w=50,
        h=20,
        font_size=12.0,
        font_family="Arial",
        fill="#111827",
        role="text",
        container_safe_bbox=[100, 100, 200, 150],
    )
    plan_item = {"role": "text", "container_safe_bbox": [100, 100, 200, 150]}
    qa_small = build_layout_qa_report({"items": [plan_item]}, [small_overflow_box])
    small_issue = next(
        issue for issue in qa_small["issues"] if issue["code"] == "text_outside_container_safe_bbox"
    )
    assert small_issue["severity"] == "warning"
    assert qa_small["valid"] is True

    large_overflow_box = OverlayTextBox(
        text="严重越界",
        x=50,
        y=100,
        w=50,
        h=20,
        font_size=12.0,
        font_family="Arial",
        fill="#111827",
        role="text",
        container_safe_bbox=[100, 100, 200, 150],
    )
    qa_large = build_layout_qa_report({"items": [plan_item]}, [large_overflow_box])
    large_issue = next(
        issue for issue in qa_large["issues"] if issue["code"] == "text_outside_container_safe_bbox"
    )
    assert large_issue["severity"] == "error"
    assert qa_large["valid"] is False


def test_main_exits_nonzero_when_layout_qa_has_errors(tmp_path: Path, monkeypatch) -> None:
    full_path, background_path = _write_pair(tmp_path)
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(
        json.dumps(
            {
                "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
                "items": [
                    {
                        "text": "极窄栏正文占位占位占位占位占位占位占位占位",
                        "bbox": [100, 100, 130, 108],
                        "role": "product_body",
                        "font_size": 5.0,
                        "lock_bbox": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    import dual_image_rebuild_pptx as module

    exit_code = module.main(
        [
            "--full",
            str(full_path),
            "--background",
            str(background_path),
            "--text-layout",
            str(layout_path),
            "--name",
            "qa_gate_fixture",
            "--projects-dir",
            str(tmp_path / "projects"),
            "--no-align",
        ]
    )

    assert exit_code == 3


def test_infer_semantic_containers_profile_override_changes_routing() -> None:
    """Generalization regression: the same two-stage layout must be routable to a
    different container-role gate than the page012 default by passing a profile
    override, instead of only ever working for the one reference slide."""
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {"text": "阶段一", "role": "stage_label", "bbox": [100, 250, 160, 270]},
            {"text": "说明一", "role": "stage_body", "bbox": [90, 280, 200, 320]},
            {"text": "阶段二", "role": "stage_label", "bbox": [400, 250, 460, 270]},
            {"text": "说明二", "role": "stage_body", "bbox": [390, 280, 500, 320]},
        ],
    }

    default_inferred, default_report = infer_semantic_containers_from_full_style(layout)
    assert {item["container_role"] for item in default_inferred["items"]} == {"isolated_text_region"}
    assert default_report["profile_overrides"] == {}
    assert default_report["profile_source"] == "page012_default_unverified"
    assert default_report["default_profile_is_unverified"] is True

    overridden_inferred, overridden_report = infer_semantic_containers_from_full_style(
        layout, profile={"stage_row_max_y": 300.0}
    )
    assert {item["container_role"] for item in overridden_inferred["items"]} == {"stage_card"}
    assert overridden_report["profile_overrides"] == {"stage_row_max_y": 300.0}
    assert overridden_report["profile_source"] == "explicit_override"
    assert overridden_report["default_profile_is_unverified"] is False


def test_infer_semantic_containers_row_anchor_override_moves_constructed_geometry() -> None:
    """Passing the each family's row-anchor profile keys must actually move the
    constructed container/text-safe geometry, not just the eligibility gate: this
    is what lets a non-page012 slide (whose card rows sit at a different height)
    reuse the fallback inference without editing the module defaults."""
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {"text": "阶段一", "role": "stage_label", "bbox": [100, 20, 160, 40]},
            {"text": "说明一", "role": "stage_body", "bbox": [90, 60, 200, 100]},
            {"text": "阶段二", "role": "stage_label", "bbox": [400, 20, 460, 40]},
            {"text": "说明二", "role": "stage_body", "bbox": [390, 60, 500, 100]},
        ],
    }

    default_inferred, _ = infer_semantic_containers_from_full_style(
        layout, profile={"stage_row_max_y": 50.0}
    )
    default_bbox = next(
        item["container_bbox"] for item in default_inferred["items"] if item["role"] == "stage_label"
    )
    assert default_bbox[1] == CONTAINER_INFERENCE_DEFAULT_PROFILE["stage_card_container_top"]
    assert default_bbox[3] == CONTAINER_INFERENCE_DEFAULT_PROFILE["stage_card_container_bottom"]

    moved_inferred, _ = infer_semantic_containers_from_full_style(
        layout,
        profile={
            "stage_row_max_y": 50.0,
            "stage_card_container_top": 400.0,
            "stage_card_container_bottom": 500.0,
            "stage_card_text_top": 410.0,
        },
    )
    moved_bbox = next(
        item["container_bbox"] for item in moved_inferred["items"] if item["role"] == "stage_label"
    )
    moved_safe_bbox = next(
        item["container_safe_bbox"] for item in moved_inferred["items"] if item["role"] == "stage_label"
    )
    assert moved_bbox[1] == 400.0
    assert moved_bbox[3] == 500.0
    assert moved_safe_bbox[1] == 410.0


def test_isolated_text_region_near_miss_reports_closest_failing_gate() -> None:
    """A body-role item that narrowly misses its family's eligibility gate must
    surface a `near_miss` diagnostic naming the gate and the miss distance,
    instead of disappearing into `isolated_text_region` with no trail -- this is
    the P0 silent-misclassification risk from the diagnostic brief."""
    stage_row_max_y = CONTAINER_INFERENCE_DEFAULT_PROFILE["stage_row_max_y"]
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            # 5.0px below the stage_row_max_y gate: a near miss, not a genuine
            # orphan -- should report the exact gate and delta.
            {
                "text": "阶段一",
                "role": "stage_label",
                "bbox": [100, stage_row_max_y + 5.0, 160, stage_row_max_y + 25.0],
            },
            # No family gate applies to a generic "text" role at all.
            {"text": "杂项说明", "role": "text", "bbox": [700, 690, 780, 705]},
        ],
    }

    _, report = infer_semantic_containers_from_full_style(layout)
    isolated_actions = {
        action["role"]: action for action in report["actions"] if action["code"] == "inferred_isolated_text_safe_bbox"
    }

    near_miss = isolated_actions["stage_label"]["near_miss"]
    assert near_miss["gate"] == "stage_row_max_y"
    assert near_miss["miss_by"] == 5.0

    assert isolated_actions["text"]["near_miss"] is None
    assert report["summary"]["isolated_near_miss_count"] == 1
    assert report["summary"]["isolated_count"] == 2


def test_visual_framework_inference_groups_page012_containers_into_parent_frames() -> None:
    """The page012 handoff needs more than local card containers.

    A main-flow rebuild must receive the parent composition frames: lifecycle
    row, processing chain, source/user swimlanes, product output band, service
    row, and trust column. Without this layer, downstream generation sees only
    individual cards and easily loses the full-image structure the user wanted
    to preserve.
    """
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {"text": "数据来源方", "bbox": [22, 14, 128, 38], "role": "actor_title"},
            {"text": "知识产权权利人", "bbox": [28, 158, 133, 181], "role": "actor_title"},
            {"text": "覆盖研发、申请、授权、使用、维权五阶段", "bbox": [18, 185, 142, 294], "role": "actor_summary"},
            {"text": "用户方", "bbox": [1170, 14, 1260, 38], "role": "actor_title"},
            {"text": "知识产权权利人", "bbox": [1131, 158, 1254, 181], "role": "actor_title"},
            {"text": "接受全周期保护服务的受益者", "bbox": [1124, 190, 1260, 272], "role": "actor_summary"},
            {"text": "知识产权全生命周期五阶段", "bbox": [542, 20, 792, 46], "role": "title"},
            {"text": "1", "bbox": [219, 73, 241, 97], "role": "index"},
            {"text": "研发", "bbox": [255, 75, 312, 99], "role": "stage_label"},
            {"text": "研发过程产生的创新成果", "bbox": [254, 117, 346, 193], "role": "stage_body"},
            {"text": "2", "bbox": [396, 73, 418, 97], "role": "index"},
            {"text": "申请", "bbox": [430, 75, 488, 99], "role": "stage_label"},
            {"text": "申请材料提交与受理信息", "bbox": [426, 117, 517, 198], "role": "stage_body"},
            {"text": "技术支撑方：提供全网侵权监测技术", "bbox": [416, 250, 864, 273], "role": "section_title"},
            {"text": "加工链条", "bbox": [404, 286, 875, 309], "role": "section_title"},
            {"text": "数据授权", "bbox": [225, 333, 284, 355], "role": "chain_label"},
            {"text": "授权范围精细化管控", "bbox": [197, 374, 294, 437], "role": "chain_body"},
            {"text": "受控接入", "bbox": [349, 333, 408, 355], "role": "chain_label"},
            {"text": "可用不可见用途可控可计量", "bbox": [319, 375, 417, 425], "role": "chain_body"},
            {"text": "目录发布主体认证收益结算", "bbox": [979, 324, 1046, 444], "role": "chain_body"},
            {"text": "技术支撑方与底座加工", "bbox": [28, 354, 133, 402], "role": "left_stage_label"},
            {"text": "服务产品", "bbox": [69, 506, 150, 530], "role": "left_stage_label"},
            {"text": "固化的权属证据", "bbox": [347, 497, 473, 519], "role": "product_title"},
            {"text": "可独立用于权属举证", "bbox": [347, 525, 472, 544], "role": "product_body"},
            {"text": "侵权鉴定报告", "bbox": [713, 497, 831, 519], "role": "product_title"},
            {"text": "对接司法鉴定机构出具", "bbox": [713, 525, 954, 544], "role": "product_body"},
            {"text": "空间运营方", "bbox": [87, 599, 199, 623], "role": "left_stage_label"},
            {"text": "中电联统筹知识产权保护规则", "bbox": [88, 642, 334, 685], "role": "actor_summary"},
            {"text": "第三方服务方", "bbox": [465, 598, 590, 622], "role": "section_title"},
            {"text": "司法鉴定机构", "bbox": [462, 634, 558, 654], "role": "service_item"},
            {"text": "侵权鉴定", "bbox": [484, 671, 548, 690], "role": "service_item"},
            {"text": "律师事务所 / 知识产权代理机构", "bbox": [642, 634, 855, 654], "role": "service_item"},
            {"text": "侵权投诉、行政维权、司法诉讼", "bbox": [596, 671, 900, 690], "role": "service_item"},
            {"text": "可信机制贯穿全程", "bbox": [1130, 343, 1261, 366], "role": "section_title"},
            {"text": "数据可信", "bbox": [1131, 412, 1193, 430], "role": "trust_title"},
            {"text": "全周期存证固化权属证据", "bbox": [1132, 432, 1260, 458], "role": "trust_body"},
            {"text": "授权可信", "bbox": [1131, 489, 1193, 507], "role": "trust_title"},
            {"text": "授权范围期限计量精细管控", "bbox": [1132, 508, 1260, 536], "role": "trust_body"},
        ],
    }

    inferred, _ = infer_semantic_containers_from_full_style(layout)
    framed, framework_report, composition_contract = infer_visual_frameworks_from_containers(inferred)

    required_roles = {
        "lifecycle_outer_frame",
        "processing_chain_frame",
        "left_role_swimlane_frame",
        "right_trust_frame",
        "service_product_frame",
        "third_party_service_frame",
        "actor_endpoint_frame",
    }
    present_roles = {framework["role"] for framework in framework_report["frameworks"]}

    assert required_roles <= present_roles
    assert framework_report["framework_coverage"]["valid"] is True
    assert framework_report["framework_coverage"]["covered_container_ratio"] >= 0.9
    assert composition_contract["framework_coverage"]["valid"] is True
    assert {zone["role"] for zone in composition_contract["layout_zones"]} >= required_roles
    assert framework_report["relation_edge_coverage"]["valid"] is True
    assert {
        "source_to_lifecycle",
        "lifecycle_stage_flow",
        "lifecycle_to_user",
        "lifecycle_to_processing",
        "processing_chain_flow",
        "processing_to_product_outputs",
        "third_party_supports_outputs",
    } <= {edge["role"] for edge in framework_report["relation_edges"]}
    assert composition_contract["relation_edge_coverage"]["valid"] is True
    assert composition_contract["relation_edges"]
    assert {
        item["parent_framework_id"]
        for item in framed["items"]
        if item.get("container_role") == "stage_card"
    } == {"lifecycle_outer_frame"}
    assert {
        item["parent_framework_id"]
        for item in framed["items"]
        if item.get("container_role") == "trust_card"
    } == {"right_trust_frame"}


def test_layout_qa_flags_overlapping_sibling_text_boxes() -> None:
    """Real-page regression (page014, 2026-07-03): apply_typesetting_policy's
    per-item 'restore source_text when it fits' check has no visibility into a
    sibling item sharing the same container, so two adjacent lines can each
    individually pass their own fit check and still expand into each other.
    Neither container_safe_bbox containment nor reserved-zone checks catch this
    because both boxes can be fully inside their own safe area while still
    overlapping each other. This must be a hard error, not a warning: two
    distinct non-empty text runs visually colliding is never an acceptable
    render."""
    box_a = OverlayTextBox(
        text="联合行业头部企业、技术服务商共同出资成立",
        x=760,
        y=80.08,
        w=226,
        h=40.14,
        font_size=14.0,
        font_family="Microsoft YaHei",
        fill="#111827",
        role="actor_summary",
        container_id="subject_market_company",
    )
    box_b = OverlayTextBox(
        text="负责日常运营、技术维护、市场推广、生态建设",
        x=760,
        y=104.08,
        w=226,
        h=40.14,
        font_size=14.0,
        font_family="Microsoft YaHei",
        fill="#111827",
        role="actor_summary",
        container_id="subject_market_company",
    )

    qa = build_layout_qa_report(
        {"items": [{"role": "actor_summary"}, {"role": "actor_summary"}]}, [box_a, box_b]
    )
    overlap_issues = [issue for issue in qa["issues"] if issue["code"] == "text_boxes_overlap"]

    assert overlap_issues and overlap_issues[0]["severity"] == "error"
    assert overlap_issues[0]["overlap_ratio"] > 0.08
    assert qa["error_count"] >= 1
    assert qa["valid"] is False


def test_layout_qa_does_not_flag_adjacent_non_overlapping_boxes() -> None:
    """Two legitimately stacked lines that merely touch (or sit a few px apart)
    must not trip the overlap check -- that is normal multi-line layout, not a
    collision."""
    box_a = OverlayTextBox(
        text="第一行标签",
        x=100,
        y=100,
        w=150,
        h=24,
        font_size=13.0,
        font_family="Microsoft YaHei",
        fill="#111827",
        role="stage_label",
        container_id="label_x",
    )
    box_b = OverlayTextBox(
        text="第二行标签",
        x=100,
        y=126,
        w=150,
        h=24,
        font_size=13.0,
        font_family="Microsoft YaHei",
        fill="#111827",
        role="stage_label",
        container_id="label_x",
    )

    qa = build_layout_qa_report(
        {"items": [{"role": "stage_label"}, {"role": "stage_label"}]}, [box_a, box_b]
    )

    assert [issue for issue in qa["issues"] if issue["code"] == "text_boxes_overlap"] == []


def test_stack_text_group_in_region_places_entries_without_overlap() -> None:
    entries = [
        {"text": "标题", "preferred_font_size": 18.0, "word_wrap": False},
        {"text": "第一段简短说明", "preferred_font_size": 14.0, "word_wrap": True},
        {"text": "第二段简短说明", "preferred_font_size": 14.0, "word_wrap": True},
    ]

    slots = _stack_text_group_in_region(entries, [0, 0, 200, 200], gap=5.0, min_font_size=9.0)

    assert len(slots) == 3
    for previous, current in zip(slots, slots[1:]):
        assert current["bbox"][1] >= previous["bbox"][3] - 0.01
    for slot in slots:
        assert slot["bbox"][1] >= 0 and slot["bbox"][3] <= 200 + 1.0


def test_stack_text_group_in_region_shrinks_uniformly_when_group_does_not_fit() -> None:
    """Real-page regression (page014 profit_card, 2026-07-03): stacking two body
    lines using a fixed assumed line height (rather than each line's real,
    wrap-aware height) let a longer restored sentence overflow its assumed slot
    and collide with the sibling below it. The stacker must measure real height
    with the same estimator QA uses, and if the group still does not fit at the
    preferred size, shrink every entry by the same factor rather than letting
    any one entry silently overflow into its neighbor's slot."""
    entries = [
        {"text": "成果转化培训咨询费", "preferred_font_size": 12.0, "word_wrap": True},
        {"text": "知产管理等领域培训咨询费", "preferred_font_size": 12.0, "word_wrap": True},
    ]

    slots = _stack_text_group_in_region(entries, [872, 555, 1016, 690], gap=5.0, min_font_size=9.0)

    assert slots[1]["bbox"][1] >= slots[0]["bbox"][3] - 0.01
    assert slots[0]["font_size"] == slots[1]["font_size"]


def test_build_layout_plan_stacks_profit_card_body_without_overlap_when_restored_text_is_long() -> None:
    """Integration regression for the exact page014 profit_5 card: two
    profit_body items sharing one container, where apply_typesetting_policy has
    already restored a long source_text into the second line. build_layout_plan
    must not hand back overlapping bboxes for the two."""
    layout = {
        "image_size": {"width": CANVAS[0], "height": CANVAS[1]},
        "items": [
            {
                "text": "培训与咨询服务收入",
                "bbox": [875, 565, 1015, 588],
                "role": "profit_title",
                "container_id": "profit_5",
                "container_bbox": [860, 500, 1020, 698],
                "container_text_safe_bbox": [860, 500, 1020, 698],
                "container_role": "profit_card",
                "font_size": 14,
            },
            {
                "text": "成果转化培训咨询费",
                "bbox": [885, 612, 1005, 635],
                "role": "profit_body",
                "container_id": "profit_5",
                "container_bbox": [860, 500, 1020, 698],
                "container_text_safe_bbox": [860, 500, 1020, 698],
                "container_role": "profit_card",
                "font_size": 12,
            },
            {
                "text": "知产管理等领域培训咨询费",
                "bbox": [880, 650, 1010, 672],
                "role": "profit_body",
                "container_id": "profit_5",
                "container_bbox": [860, 500, 1020, 698],
                "container_text_safe_bbox": [860, 500, 1020, 698],
                "container_role": "profit_card",
                "font_size": 12,
            },
        ],
    }

    layout_plan = build_layout_plan(layout)
    body_records = [item for item in layout_plan["items"] if item["role"] == "profit_body"]

    assert len(body_records) == 2
    first, second = sorted(body_records, key=lambda record: record["bbox"][1])
    assert second["bbox"][1] >= first["bbox"][3] - 0.01
    assert first["container_safe_bbox"] == first["bbox"]
    assert second["container_safe_bbox"] == second["bbox"]


def test_page012_real_fixture_auto_inferred_fallback_has_zero_layout_qa_errors() -> None:
    """Real regression fixture, not synthetic data: the actual page012 slide
    image pair and its semantic plan (fixtures/dual_image_rebuild/page012/),
    which is the same reference slide CONTAINER_INFERENCE_DEFAULT_PROFILE was
    reverse-engineered from and historically drove several fixes documented in
    docs/zh/dual-image-rebuild-workflow-diagnostic-brief.md (process_chain_card
    cross-boundary text, trust_card title/body crowding, stage-card body not
    using available vertical space). Past validation of this exact page lived
    only in gitignored projects/ runs with no committed fixture behind it; this
    test makes that real-world validation reproducible in CI instead.

    This semantic plan predates the containers[] schema, so it exercises the
    auto-inferred fallback path (infer_semantic_containers_from_full_style),
    not the production explicit-containers path -- see the page014 test below
    for that path. It is run through the pipeline functions directly (not the
    CLI) because passing this plan to the CLI's --semantic-plan flag now hits
    validate_semantic_plan's missing_container hard-gate: current code has
    become stricter than workflow.md's documented "still exports for
    inspection" behavior for a semantic plan supplied without containers. That
    drift is a known, separate issue -- this test intentionally exercises the
    same fallback-inference code path run() would reach if that gate did not
    exist, since the fallback path itself is the P0 generalization risk this
    fixture is meant to guard.
    """
    fixture_dir = FIXTURES_DIR / "page012"
    raw_plan = json.loads((fixture_dir / "semantic_plan.json").read_text(encoding="utf-8"))
    semantic_plan = normalize_semantic_plan(raw_plan)

    layout = {"image_size": {"width": CANVAS[0], "height": CANVAS[1]}, "items": semantic_plan["items"]}
    layout, safe_area_report = infer_semantic_containers_from_full_style(layout)
    layout, _typesetting_report = apply_typesetting_policy(layout)
    layout_plan = build_layout_plan(layout)
    layout = apply_layout_plan(layout, layout_plan)
    boxes = build_overlay_boxes(layout, fixture_dir / "background.png", AlignmentTransform())
    layout_qa = build_layout_qa_report(layout_plan, boxes)

    assert layout_qa["error_count"] == 0, layout_qa["issues"]
    error_codes = {issue["code"] for issue in layout_qa["issues"] if issue["severity"] == "error"}
    assert "isolated_text_region_used_for_body_role" not in error_codes
    assert "text_boxes_overlap" not in error_codes
    assert safe_area_report["summary"]["isolated_near_miss_count"] == 0


def test_page014_real_fixture_explicit_containers_is_fully_production_ready(tmp_path: Path) -> None:
    """Real regression fixture covering the *other* container-role vocabulary:
    fixtures/dual_image_rebuild/page014/ has an author-supplied containers[]
    with items linked by container_id, exercising the preferred, formally
    specified path (build_layout_plan / _container_layout_context) instead of
    the page012 fixture's auto-inferred fallback. This is the same real page
    that drove the documented 2026-07-03 top_actor_card / profit_card sibling
    text-restoration collision fixes.

    The checked-in semantic_plan.json has one deliberate correction versus the
    original authored file: the `dual_coordination` container's `bbox` left
    edge was widened from 615 to 602 so it actually contains its own declared
    `text_safe_bbox` ([602, 298, 705, 386]) -- every one of the several
    semantic-plan variants generated for this page during development shares
    this same off-by-~13px authoring bug (safe_bbox_outside_container), so it
    was fixed here rather than picking a variant that happened to avoid it.

    Runs the real CLI end-to-end (not just the pipeline functions) so this
    also locks in that semantic_plan_preflight, layout_qa, text_content_qa,
    and production_readiness all agree the page is clean -- the full bar
    workflow.md sets for treating a new visual family as reusable.
    """
    import dual_image_rebuild_pptx as module

    fixture_dir = FIXTURES_DIR / "page014"
    exit_code = module.main(
        [
            "--full",
            str(fixture_dir / "full.png"),
            "--background",
            str(fixture_dir / "background.png"),
            "--text-layout",
            str(fixture_dir / "text_layout.json"),
            "--semantic-plan",
            str(fixture_dir / "semantic_plan.json"),
            "--name",
            "page014_fixture_regression",
            "--projects-dir",
            str(tmp_path / "projects"),
            "--no-align",
        ]
    )

    assert exit_code == 0

    project_dir = next((tmp_path / "projects").glob("page014_fixture_regression_ppt169_*"))
    analysis = project_dir / "analysis" / "dual_image_rebuild"

    layout_qa = json.loads((analysis / "P01_layout_qa.json").read_text(encoding="utf-8"))
    assert layout_qa["error_count"] == 0, layout_qa["issues"]

    preflight = json.loads((analysis / "P01_semantic_plan_preflight.json").read_text(encoding="utf-8"))
    assert preflight["valid"] is True, preflight["issues"]

    text_content_qa = json.loads((analysis / "P01_text_content_qa.json").read_text(encoding="utf-8"))
    assert text_content_qa["valid"] is True

    production_readiness = json.loads((analysis / "P01_production_readiness.json").read_text(encoding="utf-8"))
    assert production_readiness["valid"] is True, production_readiness
