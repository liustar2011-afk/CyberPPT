#!/usr/bin/env python3
"""Create the three aligned source images and canonical line OCR for script page 007."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).parents[1]
OUT = ROOT / "outputs" / "page-007"
SOURCE = Path("/Users/liuxing/.codex/generated_images/019f4fab-39ce-7ea1-835c-0f69b9a16964/exec-1a2ddd3f-0077-4ea6-bb2f-40467de8a653.png")
FONT = "/Users/liuxing/Library/Fonts/msyh.ttc"
CANVAS = (1600, 900)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    # Microsoft YaHei collection: index 0 regular, index 1 bold on this Mac.
    return ImageFont.truetype(FONT, size, index=1 if bold else 0)


def add_line(draw: ImageDraw.ImageDraw, lines: list[dict], text: str, x: int, y: int,
             size: int, color: str = "#303030", bold: bool = False, width: int | None = None) -> None:
    face = font(size, bold)
    left, top, right, bottom = draw.textbbox((x, y), text, font=face, stroke_width=0)
    actual_width, actual_height = right - left, bottom - top
    box_width = max(actual_width + 4, width or 0)
    draw.text((x, y), text, font=face, fill=color)
    lines.append({
        "text": text,
        "bbox": [x, y, box_width, actual_height + 5],
        "score": 0.99,
        "runs": [{
            "text": text,
            "font_family": "Microsoft YaHei",
            "font_size": size * 0.75,
            "color": color.removeprefix("#"),
            "bold": bold,
        }],
    })


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    background = Image.new("RGB", CANVAS, "#F7F6F0")
    frame = ImageDraw.Draw(background)
    # Only the page-007 body composition: no template frame, header/footer, logo, or side decoration.
    frame.rounded_rectangle((70, 55, 1530, 300), radius=12, fill="#FFFFFF", outline="#12355B", width=3)
    route_left, route_top, route_width, route_height = 70, 370, 360, 112
    route_colors = ("#12355B", "#1B466D", "#12355B", "#1B466D")
    for index, color in enumerate(route_colors):
        x = route_left + index * route_width
        points = [(x, route_top), (x + route_width - 25, route_top),
                  (x + route_width, route_top + route_height // 2),
                  (x + route_width - 25, route_top + route_height), (x, route_top + route_height)]
        if index:
            points.insert(0, (x + 25, route_top + route_height // 2))
        frame.polygon(points, fill=color)
    frame.rounded_rectangle((70, 530, 705, 835), radius=12, fill="#FFFFFF", outline="#12355B", width=2)
    frame.rounded_rectangle((735, 530, 1530, 835), radius=12, fill="#FFFFFF", outline="#12355B", width=2)
    background.save(OUT / "background.png")

    text_layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    lines: list[dict] = []

    # Script-defined structural labels and construction master line.
    add_line(draw, lines, "总体思路", 115, 82, 30, "#12355B", True, 220)
    add_line(draw, lines, "以中电联履职需要为牵引，以统计与数智部电力供需分析处为牵头，以可信数据流通和统一指标口径为基础，", 115, 143, 20, "#101820", width=1330)
    add_line(draw, lines, "以多模型协同和场景化推演为支撑，以报告自动化、领导驾驶舱、专题会商和风险预警为主要产品，分阶段建设电力供需形势预测能力体系。", 115, 188, 17, "#303030", width=1360)

    # Middle: exact four technical-route labels, one editable textbox per visual line.
    add_line(draw, lines, "总体技术路线", 75, 323, 26, "#12355B", True, 280)
    add_line(draw, lines, "治理先行、数据可信", 125, 409, 20, "#FFFFFF", True, 250)
    add_line(draw, lines, "平台承载、批流并举", 483, 409, 20, "#FFFFFF", True, 250)
    add_line(draw, lines, "模型驱动、稳健可释", 841, 409, 20, "#FFFFFF", True, 250)
    add_line(draw, lines, "场景闭环、持续运营", 1199, 409, 20, "#FFFFFF", True, 250)

    # Lower left: public-capability positioning.
    add_line(draw, lines, "能力定位", 105, 570, 24, "#12355B", True, 260)
    add_line(draw, lines, "中电联电力供需形势预测的行业级公共能力建设工程", 105, 632, 18, "#303030", width=560)
    add_line(draw, lines, "支撑全国、区域、省级和重点行业多层级供需形势研判", 105, 695, 18, "#303030", width=560)

    # Lower right: service scope and product set, all original terms retained.
    add_line(draw, lines, "服务层级与成果", 770, 570, 24, "#12355B", True, 320)
    add_line(draw, lines, "服务国家部委政策咨询、行业运行分析、会员单位服务、重点时段保供会商和中电联内部管理决策", 770, 632, 15, "#303030", width=710)
    add_line(draw, lines, "中长期供需研判、重点时段预测预警、月度和季度滚动分析、场景化专题服务", 770, 690, 16, "#303030", width=710)
    add_line(draw, lines, "年度报告、季度判断、风险清单、专题专报、月报、区域热力图、情景比较和指标接口", 770, 748, 16, "#303030", width=710)

    text_layer.save(OUT / "text.png")
    full = Image.alpha_composite(background.convert("RGBA"), text_layer)
    full.convert("RGB").save(OUT / "full.png")
    (OUT / "ocr.json").write_text(json.dumps({"canonical": {"lines": lines}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "registration.json").write_text(json.dumps({"transform_id": "TF-PAGE007-IDENTITY", "matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
