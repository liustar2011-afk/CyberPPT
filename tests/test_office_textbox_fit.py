from __future__ import annotations

from PIL import Image, ImageDraw

from scripts.dual_image_overlay.office_textbox_fit import apply_office_textbox_fit


def test_office_textbox_fit_expands_slot_before_reducing_below_minimum() -> None:
    boxes = [
        {
            "text": "证书签发管理",
            "bbox": [752.0, 384.0, 826.0, 397.0],
            "font_size": 6.38,
            "semantic_role": "body",
            "wrap": False,
        }
    ]

    fitted, report = apply_office_textbox_fit(boxes, canvas={"width": 1280, "height": 720})

    box = fitted[0]
    assert box["font_size"] == 9.0
    assert box["bbox"][0] == 752.0
    assert box["bbox"][2] > 826.0
    assert box["wrap"] is False
    assert report["expanded_count"] == 1
    assert report["below_minimum_count"] == 0


def test_office_textbox_fit_keeps_centered_expansion_bbox_valid() -> None:
    boxes = [
        {
            "text": "证书审核",
            "bbox": [738.0, 335.0, 797.0, 351.0],
            "font_size": 10.5,
            "semantic_role": "parallel_title",
            "align": "center",
            "wrap": False,
        }
    ]

    fitted, report = apply_office_textbox_fit(boxes, canvas={"width": 1280, "height": 720})

    x1, y1, x2, y2 = fitted[0]["bbox"]
    assert x1 < x2
    assert y1 < y2
    assert fitted[0]["font_size"] >= 9.0
    assert report["below_minimum_count"] == 0


def test_office_textbox_fit_expands_height_around_text_for_office_line_box() -> None:
    boxes = [
        {
            "text": "结果合规审核",
            "bbox": [752.0, 365.0, 826.0, 378.0],
            "font_size": 9.0,
            "semantic_role": "body",
            "wrap": False,
        }
    ]

    fitted, _report = apply_office_textbox_fit(boxes, canvas={"width": 1280, "height": 720})

    x1, y1, x2, y2 = fitted[0]["bbox"]
    assert y1 < 365.0
    assert y2 > 378.0
    assert y2 - y1 >= 14.0


def test_office_textbox_fit_compacts_numbered_title_detail_group() -> None:
    boxes = [
        {"text": "6", "bbox": [1159.0, 611.5, 1177.0, 630.5], "font_size": 6.8, "semantic_role": "index"},
        {
            "text": "审计追踪",
            "bbox": [1197.0, 622.1, 1262.1, 638.9],
            "font_size": 10.5,
            "semantic_role": "parallel_title",
            "align": "center",
            "wrap": False,
        },
        {"text": "•", "bbox": [1188.0, 651.5, 1192.0, 666.0], "font_size": 7.0, "semantic_role": "bullet_marker"},
        {
            "text": "全链路操作",
            "bbox": [1194.0, 651.8, 1263.75, 666.2],
            "font_size": 9.0,
            "semantic_role": "body",
            "wrap": False,
        },
        {"text": "•", "bbox": [1188.0, 666.5, 1192.0, 681.0], "font_size": 7.0, "semantic_role": "bullet_marker"},
        {
            "text": "日志留存审计",
            "bbox": [1194.0, 666.8, 1277.7, 681.2],
            "font_size": 9.0,
            "semantic_role": "body",
            "wrap": False,
        },
    ]

    fitted, report = apply_office_textbox_fit(boxes, canvas={"width": 1280, "height": 720})

    by_text = {box["text"]: box for box in fitted if box["text"] != "•"}
    assert by_text["审计追踪"]["bbox"][1] < 622.1
    assert by_text["全链路操作"]["bbox"][1] < 651.8
    title_gap = by_text["全链路操作"]["bbox"][1] - by_text["审计追踪"]["bbox"][3]
    detail_gap = by_text["日志留存审计"]["bbox"][1] - by_text["全链路操作"]["bbox"][3]
    assert title_gap <= 6.0
    assert detail_gap <= 2.0
    assert by_text["全链路操作"]["font_size"] == 9.0
    assert report["generic_title_detail_compacted_count"] >= 1


def test_office_textbox_fit_moves_title_detail_group_up_when_bottom_is_tight() -> None:
    boxes = [
        {
            "text": "证书审核",
            "bbox": [734.95, 334.6, 800.05, 351.4],
            "font_size": 10.5,
            "semantic_role": "parallel_title",
            "align": "center",
            "wrap": False,
        },
        {"text": "•", "bbox": [743.0, 364.0, 747.0, 378.0], "font_size": 7.0, "semantic_role": "bullet_marker"},
        {"text": "结果合规审核", "bbox": [752.0, 364.3, 835.7, 378.7], "font_size": 9.0, "semantic_role": "body", "wrap": False},
        {"text": "•", "bbox": [743.0, 383.0, 747.0, 397.0], "font_size": 7.0, "semantic_role": "bullet_marker"},
        {"text": "证书签发管理", "bbox": [752.0, 383.3, 835.7, 397.7], "font_size": 9.0, "semantic_role": "body", "wrap": False},
        {"text": "•", "bbox": [743.0, 403.0, 747.0, 417.0], "font_size": 7.0, "semantic_role": "bullet_marker"},
        {"text": "证书状态管理", "bbox": [752.0, 403.3, 835.7, 417.7], "font_size": 9.0, "semantic_role": "body", "wrap": False},
        {"text": "•", "bbox": [743.0, 422.0, 747.0, 436.0], "font_size": 7.0, "semantic_role": "bullet_marker"},
        {"text": "撤销与更新", "bbox": [752.0, 422.3, 821.75, 436.7], "font_size": 9.0, "semantic_role": "body", "wrap": False},
    ]

    fitted, report = apply_office_textbox_fit(boxes, canvas={"width": 1280, "height": 720})

    by_text = {box["text"]: box for box in fitted if box["text"] != "•"}
    assert by_text["结果合规审核"]["bbox"][1] < 364.3
    assert by_text["撤销与更新"]["bbox"][3] <= 432.0
    assert by_text["结果合规审核"]["font_size"] == 9.0
    assert report["generic_title_detail_compacted_count"] >= 1


def test_office_textbox_fit_compacts_generic_title_detail_group_without_region_hardcoding() -> None:
    boxes = [
        {
            "text": "生态协作服务",
            "bbox": [996.0, 621.0, 1071.0, 637.8],
            "font_size": 10.5,
            "semantic_role": "parallel_title",
            "align": "center",
            "wrap": False,
        },
        {"text": "•", "bbox": [995.0, 648.0, 999.0, 662.0], "font_size": 7.0, "semantic_role": "bullet_marker"},
        {"text": "合作生态对接", "bbox": [1004.0, 648.3, 1087.7, 662.7], "font_size": 9.0, "semantic_role": "body", "wrap": False},
        {"text": "•", "bbox": [995.0, 667.0, 999.0, 681.0], "font_size": 7.0, "semantic_role": "bullet_marker"},
        {"text": "能力开放共享", "bbox": [1004.0, 667.3, 1087.7, 681.7], "font_size": 9.0, "semantic_role": "body", "wrap": False},
        {"text": "•", "bbox": [995.0, 685.0, 999.0, 699.0], "font_size": 7.0, "semantic_role": "bullet_marker"},
        {"text": "生态共建共赢", "bbox": [1004.0, 685.3, 1087.7, 699.7], "font_size": 9.0, "semantic_role": "body", "wrap": False},
    ]

    fitted, report = apply_office_textbox_fit(boxes, canvas={"width": 1280, "height": 720})

    by_text = {box["text"]: box for box in fitted if box["text"] != "•"}
    assert by_text["合作生态对接"]["bbox"][1] < 648.3
    assert by_text["生态共建共赢"]["bbox"][3] <= 690.0
    assert by_text["合作生态对接"]["font_size"] == 9.0
    assert report["generic_title_detail_compacted_count"] >= 1


def test_office_textbox_fit_assigns_details_to_nearest_preceding_title_not_parent_title() -> None:
    boxes = [
        {
            "text": "数据基础",
            "bbox": [58.0, 18.0, 127.0, 37.0],
            "font_size": 10.5,
            "semantic_role": "parallel_title",
            "align": "center",
            "wrap": False,
        },
        {
            "text": "企业/业务数据",
            "bbox": [49.618, 76.6, 156.382, 93.4],
            "font_size": 10.5,
            "semantic_role": "parallel_title",
            "align": "center",
            "wrap": False,
        },
        {"text": "•", "bbox": [71.0, 99.0, 75.0, 112.0], "font_size": 7.0, "semantic_role": "bullet_marker"},
        {"text": "经营管理数据", "bbox": [80.0, 99.0, 163.7, 113.4], "font_size": 9.0, "semantic_role": "body", "wrap": False},
        {"text": "•", "bbox": [71.0, 118.0, 75.0, 131.0], "font_size": 7.0, "semantic_role": "bullet_marker"},
        {"text": "项目执行数据", "bbox": [80.0, 118.0, 163.7, 132.4], "font_size": 9.0, "semantic_role": "body", "wrap": False},
    ]

    fitted, report = apply_office_textbox_fit(boxes, canvas={"width": 1280, "height": 720})

    by_text = {box["text"]: box for box in fitted if box["text"] != "•"}
    assert by_text["经营管理数据"]["bbox"][1] > by_text["企业/业务数据"]["bbox"][3]
    assert by_text["经营管理数据"]["bbox"][1] > 95.0
    assert by_text["经营管理数据"]["bbox"][1] - by_text["企业/业务数据"]["bbox"][3] <= 7.0
    assert report["generic_title_detail_compacted_count"] >= 1


def test_office_textbox_fit_skips_bullet_markers_and_indexes() -> None:
    boxes = [
        {"text": "•", "bbox": [700.0, 100.0, 704.0, 112.0], "font_size": 5.6, "semantic_role": "bullet_marker"},
        {"text": "9", "bbox": [690.0, 90.0, 710.0, 110.0], "font_size": 7.2, "semantic_role": "index"},
    ]

    fitted, report = apply_office_textbox_fit(boxes)

    assert fitted == boxes
    assert report["skipped_count"] == 2


def test_office_textbox_fit_places_isolated_label_inside_clear_horizontal_band(tmp_path) -> None:
    background = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(background)
    draw.line([(350, 448), (930, 448)], fill=(10, 59, 117), width=2)
    draw.line([(350, 465), (930, 465)], fill=(10, 59, 117), width=2)
    background_path = tmp_path / "background.png"
    background.save(background_path)
    boxes = [
        {
            "text": "关系标签",
            "bbox": [571.0, 454.1, 636.1, 470.9],
            "font_size": 10.5,
            "semantic_role": "parallel_title",
            "align": "left",
            "wrap": False,
        }
    ]

    fitted, report = apply_office_textbox_fit(
        boxes,
        canvas={"width": 1280, "height": 720},
        background_image=background_path,
    )

    label = fitted[0]
    assert label["font_size"] == 9.0
    assert label["bbox"][1] > 448.0
    assert label["bbox"][3] < 465.0
    assert report["isolated_label_adjusted_count"] == 1
