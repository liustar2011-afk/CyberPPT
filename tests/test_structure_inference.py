from __future__ import annotations

from scripts.dual_image_overlay.structure_inference import infer_structure_containers


def test_infers_reusable_containers_from_text_geometry() -> None:
    text_items = [
        _text("top_summary", 150, 140, 900, 24),
        _text("top_detail", 150, 176, 760, 24),
        _text("1", 70, 250, 14, 22),
        _text("A title", 114, 250, 130, 20),
        _text("A body 1", 110, 316, 180, 18),
        _text("A body 2", 110, 386, 180, 18),
        _text("2", 390, 250, 14, 22),
        _text("B title", 432, 250, 130, 20),
        _text("B body 1", 424, 316, 180, 18),
        _text("B body 2", 424, 386, 180, 18),
        _text("3", 696, 250, 14, 22),
        _text("C title", 730, 250, 130, 20),
        _text("C body 1", 728, 316, 180, 18),
        _text("C body 2", 728, 386, 180, 18),
        _text("4", 990, 250, 14, 22),
        _text("D title", 1034, 250, 130, 20),
        _text("D body 1", 1028, 316, 180, 18),
        _text("D body 2", 1028, 386, 180, 18),
        _text("bottom 1", 194, 620, 162, 31),
        _text("bottom 2", 451, 620, 162, 31),
        _text("bottom 3", 714, 620, 162, 31),
        _text("bottom 4", 969, 620, 162, 31),
    ]

    result = infer_structure_containers(page_number=3, text_items=text_items)

    assert result["schema"] == "cyberppt.dual_image.structure_inference.v1"
    assert result["valid"] is True
    assert result["container_count"] == 6
    roles = [item["role"] for item in result["containers"]]
    assert roles.count("row_band") == 2
    assert roles.count("repeated_panel") == 4
    assert all(item.get("container_id") for item in result["text_items"])
    assert len({item["container_id"] for item in result["text_items"] if item["text"].startswith(("A", "B", "C", "D", "1", "2", "3", "4"))}) == 4


def test_structure_inference_reassigns_stale_container_ids_to_inferred_geometry() -> None:
    text_items = [
        _text("1", 570, 347, 9, 10, container_id="stale_panel"),
        _text("审计留痕", 560, 370, 50, 13, container_id="stale_panel"),
        _text("投后管理可视化报告", 555, 447, 66, 46, container_id="stale_panel"),
        _text("2", 720, 347, 9, 10, container_id="stale_panel"),
        _text("收益结算", 710, 370, 50, 13, container_id="stale_panel"),
        _text("全流程线上化", 704, 447, 120, 46, container_id="stale_panel"),
    ]

    result = infer_structure_containers(page_number=13, text_items=text_items, canvas={"width": 1280, "height": 720})

    assert result["valid"] is True
    container_ids = {item["container_id"] for item in result["text_items"]}
    assert "stale_panel" not in container_ids
    assert len(container_ids) == 2
    for container in result["containers"]:
        assigned = [item for item in result["text_items"] if item["container_id"] == container["id"]]
        assert len(assigned) == container["text_count"]


def test_structure_inference_preserves_overlapping_column_membership() -> None:
    text_items = [
        _text("成果输出", 480.16, 370.4, 49.41, 12.33, container_id="stale_panel"),
        _text("投股匹配推荐清单、\n投后管理报告", 471.44, 446.87, 67.81, 34.53, container_id="stale_panel"),
        _text("主体认证、受控接入、调用计量非本场景原文展开重点", 320.31, 552.11, 299.34, 13.16, container_id="stale_panel"),
        _text("5", 581.88, 347.38, 8.72, 9.87, container_id="stale_panel"),
        _text("审计留痕", 560.56, 370.4, 49.41, 12.33, container_id="stale_panel"),
        _text("投后管理可视化报告（分析报告类）：项目转化进度、经营数据、履约情况全程可视可溯", 554.75, 446.87, 65.88, 46.04, container_id="stale_panel"),
        _text("6", 665.19, 347.38, 8.72, 9.87, container_id="stale_panel"),
        _text("收益结算", 645.81, 370.4, 49.41, 12.33, container_id="stale_panel"),
        _text("融资申请→风控审核\n→放款→还款\n全流程线上化", 633.22, 446.87, 162.97, 46.87, container_id="stale_panel"),
    ]

    result = infer_structure_containers(page_number=13, text_items=text_items, canvas={"width": 1280, "height": 720})

    assert result["valid"] is True
    for container in result["containers"]:
        assigned = [item for item in result["text_items"] if item["container_id"] == container["id"]]
        assert len(assigned) == container["text_count"]


def test_structure_inference_splits_stacked_cards_in_same_column() -> None:
    text_items = [
        _text("融资需求方", 1158.28, 242.96, 63.94, 11.51, container_id="stale_panel"),
        _text("（决策转化项目方）", 1134.06, 260.23, 87.19, 11.51, container_id="stale_panel"),
        _text("获得融资对接服务的", 1118.56, 293.93, 103.66, 11.51, container_id="stale_panel"),
        _text("受益者", 1150.53, 309.97, 40.69, 11.51, container_id="stale_panel"),
        _text("金融机构", 1156.34, 421.79, 53.28, 11.51, container_id="stale_panel"),
        _text("（银行/创投/保险/", 1131.16, 439.07, 90.09, 11.51, container_id="stale_panel"),
        _text("担保/产业基金）", 1147.62, 464.13, 75.56, 11.51, container_id="stale_panel"),
        _text("获得可信风控依据的", 1118.56, 498.67, 103.66, 11.51, container_id="stale_panel"),
        _text("受益者", 1150.53, 516.76, 40.69, 11.51, container_id="stale_panel"),
    ]

    result = infer_structure_containers(page_number=13, text_items=text_items, canvas={"width": 1280, "height": 720})

    assert result["valid"] is True
    assert result["container_count"] == 2
    container_by_text = {item["text"]: item["container_id"] for item in result["text_items"]}
    assert container_by_text["融资需求方"] == container_by_text["获得融资对接服务的"]
    assert container_by_text["金融机构"] == container_by_text["获得可信风控依据的"]
    assert container_by_text["融资需求方"] != container_by_text["金融机构"]


def _text(
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    container_id: str | None = None,
) -> dict[str, object]:
    return {
        "text": text,
        "bbox": {"x": x, "y": y, "w": w, "h": h},
        "role": "body",
        **({"container_id": container_id} if container_id else {}),
    }
