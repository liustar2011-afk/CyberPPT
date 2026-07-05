#!/usr/bin/env python3
"""
Shared helpers for 复刻流程2 (layout-reference-rebuild-2).

Structure contract validation, SVG executor contract checks, and intake heuristics.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

SVG_NS = "{http://www.w3.org/2000/svg}"
WORKFLOW_ID = "layout-reference-rebuild-2"
PLACEHOLDER_TOKENS = (
    "to_be_completed_by_agent",
    "to_be_completed",
    "tbd",
    "todo",
)

PRIMITIVE_MARKERS = {
    "chevron_column_header": "data-primitive",
    "horizontal_arrow_connector": "data-chain-connector",
    "section_label_pill": "data-primitive",
    "footer_principle_chips": "data-primitive",
    "guidance_banner": "data-primitive",
}

FLOW_RELATIONSHIP_KEYWORDS = (
    "arrow",
    "directed",
    "flow",
    "chain",
    "connector",
    "sequential",
)

ALLOWED_PAGE_TYPE_HINTS = {
    "cover",
    "agenda",
    "comparison",
    "timeline",
    "process",
    "matrix",
    "dashboard",
    "quote",
    "summary",
    "custom",
}


def is_rebuild2(data: dict[str, Any]) -> bool:
    if data.get("workflow") == WORKFLOW_ID:
        return True
    if str(data.get("version", "")).strip() == "2.0":
        return True
    contract = data.get("structure_contract")
    return isinstance(contract, dict) and contract.get("fidelity") == "reference"


def _zones(data: dict[str, Any]) -> list[dict[str, Any]]:
    zones = data.get("zones", [])
    return [zone for zone in zones if isinstance(zone, dict)]


def _chain_nodes(data: dict[str, Any]) -> list[dict[str, Any]]:
    chain = data.get("main_chain", {})
    if not isinstance(chain, dict):
        return []
    nodes = chain.get("nodes", [])
    return [node for node in nodes if isinstance(node, dict)]


def _icons(data: dict[str, Any]) -> list[dict[str, Any]]:
    icon_ref = data.get("icon_reconstruction", {})
    if not isinstance(icon_ref, dict):
        return []
    icons = icon_ref.get("icons", [])
    return [icon for icon in icons if isinstance(icon, dict)]


def _has_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.strip().lower()
    return any(token in lowered for token in PLACEHOLDER_TOKENS)


def _column_zone_ids(zones: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for zone in zones:
        zone_id = zone.get("id")
        if not isinstance(zone_id, str):
            continue
        role = str(zone.get("role", "")).lower()
        component = str(zone.get("component", "")).lower()
        if "column" in role or "column" in component or zone_id.startswith("zone_col_"):
            out.append(zone_id)
    return out


def _minimum_icon_count(data: dict[str, Any], mapping: dict[str, Any] | None = None) -> int:
    zones = _zones(data)
    columns = _column_zone_ids(zones)
    section_total = 0
    if mapping:
        modules = mapping.get("renderable_content", {}).get("modules", [])
        if isinstance(modules, list):
            for module in modules:
                if not isinstance(module, dict):
                    continue
                sections = module.get("sections", [])
                if isinstance(sections, list):
                    section_total += len(sections)
    if section_total:
        return max(4, section_total + len(columns) + 2)
    return max(8, len(columns) * 4 + 2)


def _is_navy(rgb: tuple[int, int, int], *, strict: bool = False) -> bool:
    r, g, b = rgb
    if strict:
        return r < 70 and g < 90 and b > 110
    return r < 90 and g < 110 and b > 95 and b > r + 20


def _is_red_accent(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return r > 180 and g < 80 and b < 80


def _dominant_color(samples: list[tuple[int, int, int]], *, quant: int = 8) -> str:
    if not samples:
        return ""
    buckets: dict[tuple[int, int, int], int] = {}
    for r, g, b in samples:
        key = (r // quant * quant, g // quant * quant, b // quant * quant)
        buckets[key] = buckets.get(key, 0) + 1
    best = max(buckets, key=buckets.get)
    return f"#{best[0]:02X}{best[1]:02X}{best[2]:02X}"


def _ratio(value: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round(max(0.0, min(1.0, value / total)), 4)


def classify_layout_page_type(
    detected: dict[str, Any],
    *,
    looks_like_four_stage_cards: bool | None = None,
) -> dict[str, Any]:
    """Classify a reference page family from lightweight intake signals."""
    columns = int(detected.get("estimated_column_count") or 0)
    has_top_band = bool(detected.get("has_top_guidance_band"))
    has_bottom_band = bool(detected.get("has_bottom_principle_band"))

    if looks_like_four_stage_cards is True:
        hint = "process"
        confidence = 0.84
        reason = "four stage card/connector geometry detected"
    elif columns >= 3 and has_top_band and has_bottom_band:
        hint = "matrix"
        confidence = 0.72
        reason = "multi-column body with top guidance and bottom band"
    elif columns >= 3:
        hint = "comparison"
        confidence = 0.62
        reason = "multi-column body detected without strong process/footer signals"
    elif has_top_band or has_bottom_band:
        hint = "summary"
        confidence = 0.52
        reason = "banded page structure detected without reliable body columns"
    else:
        hint = "custom"
        confidence = 0.35
        reason = "insufficient deterministic structure signals"

    needs_review: list[str] = []
    if confidence < 0.7:
        needs_review.append("Confirm page_type_hint by visual inspection before SVG rebuild.")
    return {
        "page_type_hint": hint,
        "confidence": round(confidence, 2),
        "reason": reason,
        "signals": {
            "estimated_column_count": columns,
            "has_top_guidance_band": has_top_band,
            "has_bottom_principle_band": has_bottom_band,
            "looks_like_four_stage_cards": bool(looks_like_four_stage_cards),
        },
        "needs_review": needs_review,
    }


def _column_boxes_degenerate(boxes: list[list[int]]) -> bool:
    """True when detected column boxes pile up on the same x-range.

    A healthy multi-column page yields side-by-side boxes; near-identical
    x-ranges mean the CV column scan collapsed (e.g. hub-and-spoke pages or
    low-contrast columns) and the geometry must be re-measured by hand.
    """
    for i, (x0_a, w_a) in enumerate(boxes):
        for x0_b, w_b in boxes[i + 1:]:
            overlap = min(x0_a + w_a, x0_b + w_b) - max(x0_a, x0_b)
            if overlap > 0.6 * max(1, min(w_a, w_b)):
                return True
    return False


def measure_layout_geometry_from_image(
    image_path: Path,
    *,
    target_w: int = 1280,
    target_h: int = 720,
) -> dict[str, Any]:
    """
    CV heuristics on the reference image → zone ratios, band Y positions, palette.

    Used at 复刻流程2 intake so layout_reference.json is grounded in pixels, not
    agent guesses. Vision models (e.g. Codex) still refine semantics; geometry should
    start from this measurement.
    """
    try:
        from PIL import Image
    except ImportError:
        return {"error": "Pillow required for layout geometry measurement"}

    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        analysis_w = 640
        analysis_h = max(1, int(analysis_w * image.height / max(image.width, 1)))
        small = rgb.resize((analysis_w, analysis_h))
        pixels = small.load()
        aw, ah = small.size

        row_navy = [0] * ah
        row_red = [0] * ah
        for y in range(ah):
            navy_count = 0
            red_count = 0
            for x in range(aw):
                px = pixels[x, y]
                if _is_navy(px):
                    navy_count += 1
                if _is_red_accent(px):
                    red_count += 1
            row_navy[y] = navy_count / aw
            row_red[y] = red_count / aw

        footer_start = ah - 1
        for y in range(ah - 1, int(ah * 0.55), -1):
            if row_navy[y] >= 0.28:
                footer_start = y
            elif y < ah - 5 and row_navy[y] < 0.12:
                break

        title_end = int(ah * 0.12)
        for y in range(int(ah * 0.05), int(ah * 0.22)):
            if row_red[y] >= 0.12:
                title_end = min(ah, y + max(2, int(ah * 0.02)))
                break

        header_row = -1
        for y in range(int(ah * 0.18), int(ah * 0.30)):
            navy_span = sum(1 for x in range(aw) if _is_navy(pixels[x, y], strict=True)) / aw
            if navy_span >= 0.32:
                header_row = y
                break
        if header_row < 0:
            header_row = int(ah * 0.24)

        guidance_y0 = title_end
        guidance_y1 = max(guidance_y0 + 4, header_row - max(4, int(ah * 0.02)))
        if guidance_y1 <= guidance_y0:
            guidance_y1 = guidance_y0 + max(8, int(ah * 0.035))

        body_y0 = header_row + max(3, int(ah * 0.03))
        body_y1 = footer_start - 2
        if body_y1 <= body_y0:
            body_y1 = int(ah * 0.78)

        col_profile = [0.0] * aw
        y_scan0 = max(0, header_row - 2)
        y_scan1 = min(ah, header_row + max(8, int(ah * 0.08)))
        for y in range(y_scan0, y_scan1):
            for x in range(aw):
                if _is_navy(pixels[x, y], strict=True):
                    col_profile[x] += 1.0

        threshold = max(col_profile) * 0.35 if col_profile else 0
        in_run = False
        runs: list[tuple[int, int]] = []
        start = 0
        for x, score in enumerate(col_profile):
            active = score >= threshold
            if active and not in_run:
                start = x
                in_run = True
            elif not active and in_run:
                runs.append((start, x))
                in_run = False
        if in_run:
            runs.append((start, aw - 1))

        chevron_runs: list[tuple[int, int]] = []
        for y in range(int(ah * 0.18), int(ah * 0.30)):
            span_start = -1
            for x in range(aw):
                if _is_navy(pixels[x, y], strict=True):
                    if span_start < 0:
                        span_start = x
                elif span_start >= 0:
                    if x - span_start >= aw * 0.12:
                        chevron_runs.append((span_start, x))
                    span_start = -1
            if span_start >= 0 and aw - span_start >= aw * 0.12:
                chevron_runs.append((span_start, aw - 1))
        if len(chevron_runs) >= 4:
            chevron_runs = sorted(chevron_runs, key=lambda item: item[1] - item[0], reverse=True)[:4]
            chevron_runs.sort(key=lambda item: item[0])
            runs = chevron_runs

        if len(runs) >= 4:
            runs = sorted(runs, key=lambda item: item[1] - item[0], reverse=True)[:4]
            runs.sort(key=lambda item: item[0])
        elif len(runs) >= 2:
            while len(runs) < 4:
                widest = max(runs, key=lambda item: item[1] - item[0])
                mid = (widest[0] + widest[1]) // 2
                idx = runs.index(widest)
                runs[idx : idx + 1] = [(widest[0], mid), (mid, widest[1])]
        else:
            margin = int(aw * 0.03)
            usable = aw - 2 * margin
            step = usable / 4
            runs = [
                (int(margin + step * i), int(margin + step * (i + 1)))
                for i in range(4)
            ]

        margin_x = int(aw * 0.03)
        full_w = aw - 2 * margin_x

        def sample_box(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int, int]]:
            samples: list[tuple[int, int, int]] = []
            x0 = max(0, min(aw - 1, x0))
            x1 = max(x0 + 1, min(aw, x1))
            y0 = max(0, min(ah - 1, y0))
            y1 = max(y0 + 1, min(ah, y1))
            for y in range(y0, y1, max(1, (y1 - y0) // 12)):
                for x in range(x0, x1, max(1, (x1 - x0) // 12)):
                    samples.append(pixels[x, y])
            return samples

        style = {
            "background": _dominant_color(sample_box(0, 0, aw, title_end)),
            "primary_color": _dominant_color(
                sample_box(margin_x, header_row - 1, aw - margin_x, header_row + 3)
            ),
            "guidance_bg": _dominant_color(sample_box(margin_x, guidance_y0, aw - margin_x, guidance_y1)),
            "card_body": _dominant_color(
                sample_box(runs[0][0] + 4, body_y0 + 6, runs[0][1] - 4, body_y0 + max(20, int(ah * 0.12)))
            ),
            "footer_fill": _dominant_color(sample_box(margin_x, footer_start, aw - margin_x, ah)),
        }

        scale_y = target_h / ah
        scale_x = target_w / aw
        rule_y = title_end
        for y in range(int(ah * 0.05), int(ah * 0.14)):
            if row_red[y] >= 0.12:
                rule_y = y + 1
                break
        guide_h_px = int((guidance_y1 - guidance_y0) * scale_y)
        if guide_h_px > 52:
            guide_h_px = max(28, int((header_row - guidance_y0) * scale_y) - 4)
        px_bands = {
            "title_bottom_px": int(title_end * scale_y),
            "rule_y_px": int(rule_y * scale_y),
            "guidance_y_px": int(guidance_y0 * scale_y),
            "guidance_h_px": guide_h_px,
            "header_y_px": int(header_row * scale_y),
            "header_h_px": int(max(42, (y_scan1 - y_scan0) * scale_y)),
            "body_y_px": int(body_y0 * scale_y),
            "body_h_px": int((body_y1 - body_y0) * scale_y),
            "footer_y_px": int(footer_start * scale_y),
            "footer_h_px": int((ah - footer_start) * scale_y),
            "column_boxes_px": [
                [int(x0 * scale_x), int((x1 - x0) * scale_x)] for x0, x1 in runs[:4]
            ],
        }
        run_widths = [(x1 - x0) / max(aw, 1) for x0, x1 in runs[:4]]
        looks_like_four_stage_cards = (
            len(runs) >= 4
            and 0.18 <= header_row / max(ah, 1) <= 0.34
            and guidance_y1 <= header_row
            and footer_start / max(ah, 1) >= 0.80
            and all(0.12 <= width <= 0.28 for width in run_widths)
        )

        def zone(
            zone_id: str,
            *,
            role: str,
            component: str,
            hint: str,
            x0: int,
            y0: int,
            w: int,
            h: int,
        ) -> dict[str, Any]:
            bbox_px = [
                int(x0 * scale_x),
                int(y0 * scale_y),
                int(w * scale_x),
                int(h * scale_y),
            ]
            bbox_ratio = [
                _ratio(x0, aw),
                _ratio(y0, ah),
                _ratio(w, aw),
                _ratio(h, ah),
            ]
            return {
                "id": zone_id,
                "role": role,
                "component": component,
                "position_hint": hint,
                "bbox_px": bbox_px,
                "bbox_ratio": bbox_ratio,
                "x_ratio": bbox_ratio[0],
                "y_ratio": bbox_ratio[1],
                "w_ratio": bbox_ratio[2],
                "h_ratio": bbox_ratio[3],
                "visual_weight": "primary" if "col" in zone_id else "secondary",
                "editable": True,
            }

        zones: list[dict[str, Any]] = [
            zone(
                "zone_title",
                role="page_title",
                component="title_block",
                hint="top centered title and red rule",
                x0=margin_x,
                y0=0,
                w=full_w,
                h=title_end,
            ),
            zone(
                "zone_guidance",
                role="design_guidance",
                component="guidance_banner",
                hint="full width guidance strip under title",
                x0=margin_x,
                y0=guidance_y0,
                w=full_w,
                h=guidance_y1 - guidance_y0,
            ),
        ]

        if looks_like_four_stage_cards:
            col_ids = ["zone_stage_01", "zone_stage_02", "zone_stage_03", "zone_stage_04"]
            col_labels = ["阶段1", "阶段2", "阶段3", "阶段4"]
            column_role = "process_step"
            column_hint = "stage card"
            layout_family = "four_stage_cards_with_connectors_consensus_and_action_bands"
            chain_type = "four_stage_process_flow"
            support_layer = "zone_footer"
        else:
            col_ids = ["zone_col_public", "zone_col_member", "zone_col_product", "zone_col_ecosystem"]
            col_labels = ["公共支撑层", "会员服务层", "专题产品层", "生态合作层"]
            column_role = "supply_column"
            column_hint = "column"
            layout_family = "parallel_chevron_columns_with_connectors"
            chain_type = "directed_supply_flow"
            support_layer = "zone_guidance"
        section_keys = ["content", "audience", "value"]
        icons: list[dict[str, Any]] = [
            {
                "id": "icon-guidance",
                "semantic_intent": "operating design note",
                "parent_zone_id": "zone_guidance",
                "level": "intro",
                "source": {"kind": "semantic_vector"},
                "text_anchor": {
                    "text_left_px": int((margin_x + 52) * scale_x),
                    "text_top_px": int((guidance_y0 + 6) * scale_y),
                    "text_height_px": 18,
                },
                "slot": {
                    "cx_ratio": _ratio(margin_x + 28, aw),
                    "cy_ratio": _ratio((guidance_y0 + guidance_y1) / 2, ah),
                    "size_ratio": 0.025,
                    "fit": "contain",
                },
            }
        ]

        for idx, (x0, x1) in enumerate(runs[:4]):
            zone_id = col_ids[idx]
            zones.append(
                zone(
                    zone_id,
                    role=column_role,
                    component="chevron_column",
                    hint=f"{column_hint} {idx + 1} header + body",
                    x0=x0,
                    y0=max(0, header_row - 2),
                    w=x1 - x0,
                    h=body_y1 - max(0, header_row - 2),
                )
            )
            prefix = zone_id.replace("zone_col_", "")
            header_cx = int(((x0 + x1) / 2) * scale_x)
            header_cy = int((header_row + 4) * scale_y)
            icons.append(
                {
                    "id": f"icon-h-{prefix}",
                    "semantic_intent": col_labels[idx],
                    "parent_zone_id": zone_id,
                    "level": "card_section",
                    "source": {"kind": "semantic_vector"},
                    "text_anchor": {
                        "text_left_px": int((x0 + 34) * scale_x),
                        "text_top_px": header_cy - 6,
                        "text_height_px": 16,
                    },
                    "slot": {
                        "cx_ratio": _ratio((x0 + x1) / 2 - (x1 - x0) * 0.32, aw),
                        "cy_ratio": _ratio(header_row + 4, ah),
                        "size_ratio": 0.02,
                        "fit": "contain",
                    },
                }
            )
            sec_span = (body_y1 - body_y0) / 3
            for s_idx, key in enumerate(section_keys):
                sec_y = body_y0 + sec_span * s_idx + sec_span * 0.35
                icons.append(
                    {
                        "id": f"icon-c-{prefix}-{key}",
                        "semantic_intent": key,
                        "parent_zone_id": zone_id,
                        "level": "card_section",
                        "source": {"kind": "semantic_vector"},
                        "text_anchor": {
                            "text_left_px": int((x0 + 28) * scale_x),
                            "text_top_px": int(sec_y * scale_y),
                            "text_height_px": 14,
                        },
                        "slot": {
                            "cx_ratio": _ratio(x0 + 14, aw),
                            "cy_ratio": _ratio(sec_y, ah),
                            "size_ratio": 0.018,
                            "fit": "contain",
                        },
                    }
                )

        zones.append(
            zone(
                "zone_footer",
                role="operating_principles",
                component="footer_principle_chips",
                hint="bottom navy principle bar",
                x0=margin_x,
                y0=footer_start,
                w=full_w,
                h=ah - footer_start,
            )
        )
        for f_idx in range(1, 6):
            icons.append(
                {
                    "id": f"icon-f-{f_idx}",
                    "semantic_intent": "footer principle",
                    "parent_zone_id": "zone_footer",
                    "level": "footer_action_icon",
                    "source": {"kind": "semantic_vector"},
                    "text_anchor": {
                        "text_left_px": int((margin_x + 100 + f_idx * 180) * scale_x),
                        "text_top_px": int((footer_start + 8) * scale_y),
                        "text_height_px": 14,
                    },
                    "slot": {
                        "cx_ratio": _ratio(margin_x + 24 + f_idx * 36, aw),
                        "cy_ratio": _ratio(footer_start + (ah - footer_start) / 2, ah),
                        "size_ratio": 0.018,
                        "fit": "contain",
                    },
                }
            )

        nodes = [
            {
                "id": f"stage_{i + 1:02d}" if looks_like_four_stage_cards else f"layer_{col_ids[i].replace('zone_col_', '')}",
                "label": col_labels[i],
                "zone_id": col_ids[i],
            }
            for i in range(min(4, len(runs)))
        ]
        connectors = [
            {"from": nodes[i]["id"], "to": nodes[i + 1]["id"], "style": "arrow"}
            for i in range(len(nodes) - 1)
        ]
        visual_anchors = [
            {
                "id": "title_bottom_edge",
                "type": "horizontal_edge",
                "x": 0,
                "y": px_bands["title_bottom_px"],
                "confidence": 0.78,
            },
            {
                "id": "guidance_band",
                "type": "band",
                "bbox_px": [0, px_bands["guidance_y_px"], target_w, px_bands["guidance_h_px"]],
                "bbox_ratio": [
                    0,
                    _ratio(px_bands["guidance_y_px"], target_h),
                    1,
                    _ratio(px_bands["guidance_h_px"], target_h),
                ],
                "confidence": 0.72,
            },
            {
                "id": "header_top_edge",
                "type": "horizontal_edge",
                "x": 0,
                "y": px_bands["header_y_px"],
                "confidence": 0.74,
            },
            {
                "id": "footer_top_edge",
                "type": "horizontal_edge",
                "x": 0,
                "y": px_bands["footer_y_px"],
                "confidence": 0.82,
            },
        ]
        for idx, box in enumerate(px_bands.get("column_boxes_px", []), start=1):
            if not isinstance(box, list) or len(box) != 2:
                continue
            x_px, w_px = box
            visual_anchors.append({
                "id": f"column_{idx:02d}_center",
                "type": "center",
                "x": int(x_px + w_px / 2),
                "y": int(px_bands["header_y_px"] + px_bands["body_h_px"] / 2),
                "confidence": 0.7,
            })
        crop_candidates = [
            {
                "id": "footer_visual_band",
                "bbox_px": [0, px_bands["footer_y_px"], target_w, px_bands["footer_h_px"]],
                "bbox_ratio": [
                    0,
                    _ratio(px_bands["footer_y_px"], target_h),
                    1,
                    _ratio(px_bands["footer_h_px"], target_h),
                ],
                "reason": "bottom band may contain decorative dense line art or texture; exclude text, cards, arrows, and conclusion boxes",
                "recommended_treatment": "local_crop_allowed",
                "contains_text": "unknown",
                "mode_fit": ["vector-hifi", "hifi", "wps-hifi"],
            }
        ]
        text_background_relation = [
            {
                "text_region_id": "zone_title",
                "background_complexity": "plain_or_low",
                "requires_text_underlay_removal": False,
                "related_anchor_id": "title_bottom_edge",
            },
            {
                "text_region_id": "zone_guidance",
                "background_complexity": "banner",
                "requires_text_underlay_removal": False,
                "related_anchor_id": "guidance_band",
            },
            {
                "text_region_id": "zone_footer",
                "background_complexity": "decorative_or_dense",
                "requires_text_underlay_removal": True,
                "related_anchor_id": "footer_top_edge",
            },
        ]
        detected_layout_signals = {
            "estimated_column_count": len(runs[:4]),
            "has_top_guidance_band": guidance_y1 > guidance_y0,
            "has_bottom_principle_band": footer_start / max(ah, 1) >= 0.80,
        }
        page_type_classifier = classify_layout_page_type(
            detected_layout_signals,
            looks_like_four_stage_cards=looks_like_four_stage_cards,
        )
        layout_grammar = {
            "primary_axis": "left_to_right",
            "reading_order": ["zone_title", "zone_guidance", *[node["zone_id"] for node in nodes], "zone_footer"],
            "composition_type": layout_family,
            "alignment_system": "column_grid",
            "repetition_pattern": f"{len(nodes)}_stage_equal_columns",
            "page_type_hint": page_type_classifier["page_type_hint"],
        }

        columns_degenerate = _column_boxes_degenerate(px_bands.get("column_boxes_px", []))
        confidence = {
            "layout_type": 0.82 if looks_like_four_stage_cards else 0.72,
            "main_chain": 0.74,
            "text_regions": 0.42,
            "crop_candidates": 0.58,
        }
        needs_review = [
            "Confirm text_region_map draft text before final PPT export.",
            "Confirm whether footer_visual_band contains text before local cropping.",
        ]
        if columns_degenerate:
            confidence["layout_type"] = min(confidence["layout_type"], 0.35)
            confidence["main_chain"] = min(confidence["main_chain"], 0.3)
            needs_review.insert(
                0,
                "Column detection is degenerate (boxes share the same x-range); "
                "re-measure zones/main_chain by hand before trusting this geometry "
                "(possible hub-and-spoke or non-column layout).",
            )

        return {
            "measured": True,
            "analysis_size": [aw, ah],
            "target_canvas": [target_w, target_h],
            "layout_family": layout_family,
            "chain_type": chain_type,
            "support_layer": support_layer,
            "column_runs_px": runs,
            "column_boxes_px": px_bands.get("column_boxes_px", []),
            "px_bands": px_bands,
            "zones": zones,
            "style_reference": style,
            "main_chain_nodes": nodes,
            "main_chain_connectors": connectors,
            "icon_slots": icons,
            "layout_grammar": layout_grammar,
            "page_type_classifier": page_type_classifier,
            "visual_anchors": visual_anchors,
            "crop_candidates": crop_candidates,
            "text_background_relation": text_background_relation,
            "confidence": confidence,
            "needs_review": needs_review,
            "detected_layout_signals": {
                **detected_layout_signals,
                "looks_like_four_stage_cards": looks_like_four_stage_cards,
                "column_boxes_degenerate": columns_degenerate,
            },
        }


def write_layout_measurement_artifacts(
    image_path: Path,
    output_dir: Path,
    measured: dict[str, Any],
) -> dict[str, str]:
    """Write measurement JSON and a visual overlay for quick human review."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "layout_measurement_report.json"
    overlay_path = output_dir / "layout_measurement_overlay.png"
    report = {
        "workflow": WORKFLOW_ID,
        "version": "1.0",
        "source_image": str(image_path),
        "measured": bool(measured.get("measured")),
        "analysis_size": measured.get("analysis_size", []),
        "target_canvas": measured.get("target_canvas", []),
        "layout_family": measured.get("layout_family", ""),
        "px_bands": measured.get("px_bands", {}),
        "column_boxes_px": measured.get("column_boxes_px", []),
        "visual_anchors": measured.get("visual_anchors", []),
        "zones": measured.get("zones", []),
        "crop_candidates": measured.get("crop_candidates", []),
        "confidence": measured.get("confidence", {}),
        "needs_review": measured.get("needs_review", []),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return {"report": str(report_path), "overlay": ""}

    target = measured.get("target_canvas", [1280, 720])
    try:
        target_w = int(target[0])
        target_h = int(target[1])
    except (TypeError, ValueError, IndexError):
        target_w, target_h = 1280, 720
    with Image.open(image_path) as image:
        canvas = image.convert("RGB").resize((target_w, target_h))
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    def box(values: Any) -> tuple[int, int, int, int] | None:
        if not isinstance(values, list) or len(values) != 4:
            return None
        try:
            x, y, w, h = [int(round(float(item))) for item in values]
        except (TypeError, ValueError):
            return None
        return x, y, x + w, y + h

    band_colors = {
        "guidance": (0, 170, 255, 70),
        "header": (255, 180, 0, 70),
        "body": (80, 220, 120, 45),
        "footer": (80, 80, 255, 70),
        "title": (255, 80, 80, 50),
    }
    bands = measured.get("px_bands", {})
    if isinstance(bands, dict):
        for name, key_y, key_h in [
            ("title", "title_bottom_px", None),
            ("guidance", "guidance_y_px", "guidance_h_px"),
            ("header", "header_y_px", "header_h_px"),
            ("body", "body_y_px", "body_h_px"),
            ("footer", "footer_y_px", "footer_h_px"),
        ]:
            if key_y not in bands:
                continue
            y = int(bands.get(key_y) or 0)
            h = int(bands.get(key_h) or 2) if key_h else max(2, y)
            y0 = 0 if name == "title" else y
            rect = (0, y0, target_w, min(target_h, y0 + h))
            draw.rectangle(rect, fill=band_colors[name], outline=band_colors[name][:3] + (220,), width=2)
            draw.text((8, max(4, y0 + 4)), name, fill=band_colors[name][:3] + (255,))
        for idx, col in enumerate(bands.get("column_boxes_px", []) or [], start=1):
            if isinstance(col, list) and len(col) == 2:
                x, w = int(col[0]), int(col[1])
                y = int(bands.get("header_y_px") or 0)
                h = int(bands.get("body_y_px", y) + bands.get("body_h_px", 0) - y)
                draw.rectangle((x, y, x + w, y + max(h, 2)), outline=(255, 255, 0, 240), width=3)
                draw.text((x + 4, y + 4), f"col {idx}", fill=(255, 255, 0, 255))

    for zone in measured.get("zones", []) if isinstance(measured.get("zones"), list) else []:
        if not isinstance(zone, dict):
            continue
        rect = box(zone.get("bbox_px"))
        if rect is None:
            continue
        draw.rectangle(rect, outline=(0, 255, 180, 240), width=2)
        draw.text((rect[0] + 4, rect[1] + 18), str(zone.get("id", "")), fill=(0, 255, 180, 255))

    composited = Image.alpha_composite(canvas.convert("RGBA"), overlay)
    composited.save(overlay_path)
    return {"report": str(report_path), "overlay": str(overlay_path)}


def apply_measured_geometry_to_layout(draft: dict[str, Any], measured: dict[str, Any]) -> None:
    """Merge CV measurement into a layout_reference draft (in-place)."""
    if measured.get("error") or not measured.get("measured"):
        return
    layout_family = measured.get("layout_family") or "parallel_chevron_columns_with_connectors"
    draft["layout_type"] = layout_family
    if _has_placeholder(draft.get("page_role", "")):
        draft["page_role"] = "product_system"

    draft["zones"] = measured.get("zones", [])
    for field in [
        "layout_grammar",
        "page_type_classifier",
        "visual_anchors",
        "crop_candidates",
        "text_background_relation",
        "confidence",
        "needs_review",
    ]:
        value = measured.get(field)
        if value:
            draft[field] = value
    px_bands = measured.get("px_bands", {})
    if isinstance(px_bands, dict):
        draft["geometry_measurement"] = px_bands

    style = measured.get("style_reference", {})
    if isinstance(style, dict):
        ref = draft.setdefault("style_reference", {})
        for key, value in style.items():
            if value and (not ref.get(key) or _has_placeholder(str(ref.get(key, "")))):
                ref[key] = value
        if style.get("primary_color"):
            ref["column_header_colors"] = [style["primary_color"]] * 4

    icons = measured.get("icon_slots", [])
    if icons:
        icon_ref = draft.setdefault("icon_reconstruction", {})
        icon_ref["icons"] = icons

    nodes = measured.get("main_chain_nodes", [])
    connectors = measured.get("main_chain_connectors", [])
    chain = draft.setdefault("main_chain", {})
    if nodes:
        chain["chain_type"] = measured.get("chain_type") or "directed_supply_flow"
        chain["direction"] = "left_to_right"
        chain["relationship_style"] = "directed_flow_with_arrow_connectors"
        chain["nodes"] = nodes
        chain["connectors"] = connectors
        chain["support_layer"] = measured.get("support_layer") or "zone_guidance"

    contract = draft.get("structure_contract")
    if isinstance(contract, dict):
        contract["geometry_source"] = "measure_layout_geometry_from_image"
        contract["layout_type"] = layout_family
        detected = contract.setdefault("detected_signals", {})
        if isinstance(detected, dict):
            detected.update(measured.get("detected_layout_signals", {}))
            if nodes:
                detected["estimated_column_count"] = len(nodes)

    try:
        from geometry_locks_lib import seed_geometry_locks_from_measurement

        locks = seed_geometry_locks_from_measurement(measured)
        if locks:
            draft["geometry_locks"] = locks
    except ImportError:  # pragma: no cover
        pass

    try:
        from layout_family_lib import build_detected_layout_family

        draft["detected_layout_family"] = build_detected_layout_family(draft, measured=measured)
    except ImportError:  # pragma: no cover
        pass


def detect_structure_signals(image_path: Path) -> dict[str, Any]:
    """Lightweight column/band heuristics from the reference image."""
    try:
        from PIL import Image
    except ImportError:
        return {"error": "Pillow required for --rebuild2 intake heuristics"}

    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        small = rgb.resize((320, int(320 * image.height / max(image.width, 1))))
        pixels = small.load()
        width, height = small.size

        column_scores: list[float] = []
        strip = max(8, width // 40)
        for x in range(0, width, strip):
            edge = 0.0
            for y in range(1, height):
                left = pixels[x, y]
                right = pixels[min(x + 1, width - 1), y]
                edge += sum(abs(left[i] - right[i]) for i in range(3))
            column_scores.append(edge / max(height, 1))

        threshold = max(column_scores) * 0.42 if column_scores else 0
        peaks = sum(1 for score in column_scores if score >= threshold)
        estimated_columns = max(2, min(6, peaks // 2 or 4))

        top_band = 0.0
        bottom_band = 0.0
        for y in range(int(height * 0.12)):
            for x in range(width):
                r, g, b = pixels[x, y]
                top_band += (255 - r) + (255 - g) + (255 - b)
        for y in range(int(height * 0.82), height):
            for x in range(width):
                r, g, b = pixels[x, y]
                bottom_band += (255 - r) + (255 - g) + (255 - b)

    payload = {
        "estimated_column_count": estimated_columns,
        "has_top_guidance_band": top_band > width * height * 40,
        "has_bottom_principle_band": bottom_band > width * height * 20,
        "image_width_px": image.width,
        "image_height_px": image.height,
    }
    payload["page_type_classifier"] = classify_layout_page_type(payload)
    return payload


def seed_structure_contract(detected: dict[str, Any]) -> dict[str, Any]:
    columns = int(detected.get("estimated_column_count") or 4)
    classifier = detected.get("page_type_classifier", {})
    page_type_hint = classifier.get("page_type_hint") if isinstance(classifier, dict) else ""
    primitives = ["guidance_banner"]
    if columns >= 2:
        primitives.extend(["chevron_column_header", "horizontal_arrow_connector", "section_label_pill"])
    if detected.get("has_bottom_principle_band"):
        primitives.append("footer_principle_chips")
    return {
        "fidelity": "reference",
        "layout_type": "four_stage_process_flow" if page_type_hint == "process" else "parallel_chevron_columns_with_connectors",
        "required_primitives": primitives,
        "forbidden_substitutes": [
            "isolated_rounded_card_grid",
            "footer_chevron_chain_without_principle_chips",
        ],
        "detected_signals": detected,
    }


def validate_structure_contract(data: dict[str, Any], mapping: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    contract = data.get("structure_contract")
    if not isinstance(contract, dict):
        errors.append("structure_contract is required for 复刻流程2 (object with fidelity=reference).")
        return errors
    if contract.get("fidelity") != "reference":
        errors.append("structure_contract.fidelity must be reference for 复刻流程2.")

    layout_type = contract.get("layout_type", "")
    if not isinstance(layout_type, str) or not layout_type.strip() or _has_placeholder(layout_type):
        errors.append("structure_contract.layout_type must be a concrete layout identifier (no placeholders).")

    primitives = contract.get("required_primitives", [])
    if not isinstance(primitives, list) or not primitives:
        errors.append("structure_contract.required_primitives must be a non-empty list.")
    else:
        for item in primitives:
            if not isinstance(item, str) or not item.strip():
                errors.append("structure_contract.required_primitives entries must be non-empty strings.")

    forbidden = contract.get("forbidden_substitutes", [])
    if not isinstance(forbidden, list) or not forbidden:
        errors.append("structure_contract.forbidden_substitutes must list layouts that must not replace the reference.")

    for field in ["layout_type", "page_role"]:
        if _has_placeholder(data.get(field, "")):
            errors.append(f"{field} still contains placeholder text; complete 复刻流程2 extraction.")

    zones = _zones(data)
    if len(zones) < 5:
        errors.append("复刻流程2 expects finer zones (title, guidance, columns, footer chips) — at least 5 zones.")

    nodes = _chain_nodes(data)
    column_zones = _column_zone_ids(zones)
    if nodes and column_zones and len(nodes) != len(column_zones):
        errors.append(
            f"main_chain.nodes ({len(nodes)}) should match column zones ({len(column_zones)})."
        )

    chain = data.get("main_chain", {})
    if isinstance(chain, dict):
        relationship = str(chain.get("relationship_style", "")).lower()
        connectors = chain.get("connectors", [])
        needs_connectors = any(keyword in relationship for keyword in FLOW_RELATIONSHIP_KEYWORDS)
        needs_connectors = needs_connectors or (
            isinstance(contract.get("required_primitives"), list)
            and "horizontal_arrow_connector" in contract.get("required_primitives", [])
        )
        if needs_connectors:
            if not isinstance(connectors, list) or len(connectors) < max(1, len(nodes) - 1):
                errors.append(
                    "main_chain.connectors must list directed links between columns when the reference shows a flow."
                )

    icons = _icons(data)
    minimum = _minimum_icon_count(data, mapping)
    if len(icons) < minimum:
        errors.append(
            f"icon_reconstruction.icons needs at least {minimum} entries for 复刻流程2 (found {len(icons)})."
        )

    for index, icon in enumerate(icons):
        if not icon.get("text_anchor"):
            errors.append(
                f"icon_reconstruction.icons[{index}] ({icon.get('id', '')}) should include text_anchor for strict rebuild."
            )

    source_path = data.get("source_reference", {}).get("path")
    if isinstance(source_path, str) and not data.get("geometry_measurement"):
        errors.append(
            "geometry_measurement missing — run extract_layout_reference_from_image.py --rebuild2 "
            "or merge measure_layout_geometry_from_image() output; hand-guessed zone ratios often drift from the reference."
        )

    return errors


def build_zone_components(layout: dict[str, Any], mapping: dict[str, Any]) -> list[dict[str, Any]]:
    modules = {
        module.get("zone_id"): module
        for module in mapping.get("renderable_content", {}).get("modules", [])
        if isinstance(module, dict) and isinstance(module.get("zone_id"), str)
    }
    components: list[dict[str, Any]] = []
    for zone in _zones(layout):
        zone_id = str(zone.get("id", ""))
        role = str(zone.get("role", ""))
        component = str(zone.get("component", ""))
        module = modules.get(zone_id, {})
        recipe = "layout_reference_components.svg_paragraph_text"
        subcomponents: list[dict[str, Any]] = []

        if role in {"page_title"} or zone_id == "zone_title":
            component = component or "title_band"
            recipe = "layout_reference_components.svg_title_band"
        elif role == "design_guidance" or zone_id == "zone_guidance":
            component = component or "guidance_banner"
            recipe = "layout_reference_components.svg_guidance_banner"
        elif component == "resource_card" or role == "resource_card":
            component = component or "resource_card"
            recipe = "layout_reference_components.svg_resource_card"
        elif role in {"main_chain", "flow_chain"} or zone_id in {"zone_main_chain", "zone_flow_chain"}:
            component = component or "bottom_flow_chain"
            recipe = "layout_reference_components.svg_bottom_flow_chain"
        elif "column" in role or "column" in component or zone_id.startswith("zone_col_") or zone_id.startswith("zone_stage_"):
            component = component or "column_panel"
            recipe = "layout_reference_components.svg_column_panel"
            sections = module.get("sections", [])
            if isinstance(sections, list):
                for sec in sections:
                    if isinstance(sec, dict):
                        subcomponents.append({
                            "role": "section",
                            "label_style": "section_label_pill",
                            "label": sec.get("label", ""),
                        })
                        if sec.get("body"):
                            subcomponents.append({
                                "role": "resource_card",
                                "recipe": "layout_reference_components.svg_resource_card",
                                "label": sec.get("label", ""),
                            })
        elif role == "operating_principles" or zone_id == "zone_footer":
            component = component or "footer_principle_chips"
            recipe = "layout_reference_components.svg_footer_principle_chips"

        components.append({
            "zone_id": zone_id,
            "component": component,
            "recipe": recipe,
            "markers": [f"data-zone-id={zone_id}"],
            "subcomponents": subcomponents,
        })
    return components


def build_executor_obligations(layout: dict[str, Any], plan_icons: list[dict[str, Any]]) -> list[str]:
    obligations = [
        "Emit data-zone-id on every zone root group.",
        "Emit data-icon-id for every icon_reconstruction.icons[].id.",
        "Emit data-primitive on structural groups matching structure_contract.required_primitives.",
    ]
    chain = layout.get("main_chain", {})
    if isinstance(chain, dict) and chain.get("connectors"):
        obligations.append("Emit data-chain-connector for each main_chain.connectors[] entry.")
    contract = layout.get("structure_contract", {})
    if isinstance(contract, dict):
        for forbidden in contract.get("forbidden_substitutes", []):
            obligations.append(f"Do not substitute reference layout with: {forbidden}")
    if plan_icons:
        obligations.append(f"Implement all {len(plan_icons)} planned icons — missing data-icon-id fails pre-export.")
    obligations.extend(extend_executor_obligations_for_crops(build_crop_plan(layout)))
    return obligations


def _executor_hint_for_crop(intent: str, needs_review: bool) -> str:
    if needs_review:
        return "Marked needs_review: do not auto-export without human confirmation."
    if intent == "asset":
        return "Embed as localized raster only if decorative; never replace card/connector vectors."
    if intent == "fallback":
        return "Prefer vector rebuild; use raster only if similarity QA fails."
    return "Keep editable as vector text/shapes where possible."


def build_crop_plan(layout: dict[str, Any]) -> list[dict[str, Any]]:
    raw = layout.get("crop_candidates", [])
    if not isinstance(raw, list):
        return []
    plan: list[dict[str, Any]] = []
    for candidate in raw:
        if not isinstance(candidate, dict):
            continue
        intent = str(candidate.get("editability_intent", "editable"))
        needs_review = candidate.get("needs_review") is True
        precrop = candidate.get("precrop", {})
        if not isinstance(precrop, dict):
            precrop = {}
        plan.append({
            "id": candidate.get("id", ""),
            "bbox_px": candidate.get("bbox_px"),
            "editability_intent": intent,
            "needs_review": needs_review,
            "precrop": {
                "enabled": precrop.get("enabled") is True,
                "file": str(precrop.get("file", "")),
            },
            "executor_hint": _executor_hint_for_crop(intent, needs_review),
        })
    return plan


def extend_executor_obligations_for_crops(crop_plan: list[dict[str, Any]]) -> list[str]:
    if not crop_plan:
        return []
    obligations: list[str] = []
    asset_ids = [str(item.get("id", "")) for item in crop_plan if item.get("editability_intent") == "asset"]
    fallback_ids = [str(item.get("id", "")) for item in crop_plan if item.get("editability_intent") == "fallback"]
    review_ids = [str(item.get("id", "")) for item in crop_plan if item.get("needs_review") is True]
    if asset_ids:
        obligations.append(
            "For crop_plan entries with editability_intent=asset: use localized raster only; "
            "never full-slide underlay or structural substitutes."
        )
    if fallback_ids:
        obligations.append(
            "For crop_plan entries with editability_intent=fallback: prefer vector rebuild; "
            "raster only if verify_reference_similarity fails after vector attempt."
        )
    if review_ids:
        obligations.append(
            f"Resolve needs_review crop_plan entries before export: {', '.join(review_ids)}."
        )
    return obligations


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _svg_root(svg_path: Path) -> ET.Element | None:
    try:
        return ET.parse(svg_path).getroot()
    except (ET.ParseError, OSError):
        return None


def _count_attr(root: ET.Element, attr: str, *, value: str | None = None) -> int:
    count = 0
    for elem in root.iter():
        got = elem.get(attr)
        if got is None:
            continue
        if value is None or got == value or (attr == "data-primitive" and value in got):
            count += 1
    return count


def _count_primitives(root: ET.Element, primitive: str) -> int:
    marker_values = {
        "chevron_column_header": "chevron_column_header",
        "horizontal_arrow_connector": None,
        "section_label_pill": "section_label_pill",
        "footer_principle_chips": "footer_principle_chip",
        "guidance_banner": "guidance_banner",
    }
    if primitive == "horizontal_arrow_connector":
        return _count_attr(root, "data-chain-connector")
    expected = marker_values.get(primitive, primitive)
    total = 0
    for elem in root.iter():
        if elem.get("data-primitive") == expected:
            total += 1
        if primitive == "chevron_column_header" and elem.get("data-primitive") == "chevron_column":
            total += 1
    return total


def verify_executor_contract(
    layout: dict[str, Any],
    svg_path: Path,
    *,
    plan: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    root = _svg_root(svg_path)
    if root is None:
        return [f"Cannot parse SVG: {svg_path}"], warnings

    zones = _zones(layout)
    for zone in zones:
        zone_id = zone.get("id")
        if not isinstance(zone_id, str):
            continue
        if _count_attr(root, "data-zone-id", value=zone_id) < 1 and _count_attr(root, "data-layout-zone", value=zone_id) < 1:
            errors.append(f"SVG missing data-zone-id for zone `{zone_id}`.")

    icons = _icons(layout)
    if plan:
        plan_icons = plan.get("icon_plan", {}).get("icons", [])
        if isinstance(plan_icons, list):
            for icon in plan_icons:
                if isinstance(icon, dict) and icon.get("id"):
                    icons.append(icon)
    for icon in icons:
        icon_id = icon.get("id") if isinstance(icon, dict) else None
        if not icon_id:
            continue
        if _count_attr(root, "data-icon-id", value=str(icon_id)) < 1:
            errors.append(f"SVG missing data-icon-id `{icon_id}`.")

    chain = layout.get("main_chain", {})
    if isinstance(chain, dict):
        connectors = chain.get("connectors", [])
        if isinstance(connectors, list) and connectors:
            found = _count_attr(root, "data-chain-connector")
            if found < len(connectors):
                errors.append(
                    f"Expected at least {len(connectors)} data-chain-connector elements, found {found}."
                )

    contract = layout.get("structure_contract", {})
    if isinstance(contract, dict):
        primitives = contract.get("required_primitives", [])
        columns = len(_column_zone_ids(zones))
        if isinstance(primitives, list):
            for primitive in primitives:
                if not isinstance(primitive, str):
                    continue
                count = _count_primitives(root, primitive)
                if primitive == "chevron_column_header" and count < columns:
                    errors.append(
                        f"Primitive `{primitive}`: expected >={columns}, found {count}."
                    )
                elif primitive == "section_label_pill" and count < max(3, columns * 2):
                    warnings.append(
                        f"Primitive `{primitive}`: expected many pills, found {count}."
                    )
                elif primitive == "footer_principle_chips" and count < 3:
                    errors.append(
                        f"Primitive `{primitive}`: expected >=3 chips, found {count}."
                    )
                elif primitive == "guidance_banner" and count < 1:
                    errors.append(f"Primitive `{primitive}` not found in SVG.")
                elif primitive == "horizontal_arrow_connector":
                    # Hub-and-spoke pages declare fewer connectors than columns-1;
                    # the declared main_chain.connectors count is the contract.
                    declared = layout.get("main_chain", {})
                    declared = declared.get("connectors", []) if isinstance(declared, dict) else []
                    expected = len(declared) if isinstance(declared, list) and declared else max(1, columns - 1)
                    if count < expected:
                        errors.append(
                            f"Primitive `{primitive}`: expected >={expected}, found {count}."
                        )

        forbidden = contract.get("forbidden_substitutes", [])
        if isinstance(forbidden, list) and "isolated_rounded_card_grid" in forbidden:
            rects = sum(1 for elem in root.iter() if _strip_ns(elem.tag) == "rect")
            connectors = _count_attr(root, "data-chain-connector")
            chevrons = _count_primitives(root, "chevron_column_header")
            if rects >= columns * 2 and chevrons < columns and connectors < 1:
                errors.append(
                    "Layout resembles isolated_rounded_card_grid (many rects, no chevrons/connectors)."
                )

    return errors, warnings
