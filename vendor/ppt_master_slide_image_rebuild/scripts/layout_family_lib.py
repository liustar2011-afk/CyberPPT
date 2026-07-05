#!/usr/bin/env python3
"""
Canonical slide-image rebuild page families and template requirements.
"""

from __future__ import annotations

import re
from typing import Any

TEMPLATE_VERSION = "1.0"
ARCHETYPE_VERSION = "1.0"

CANONICAL_FAMILIES = (
    "five_column_closed_loop",
    "central_platform_with_side_columns",
    "bottom_chain_with_feedback",
    "dense_cards_with_icons",
    "hub_and_spoke",
    "custom",
)

FAMILY_ALIASES: dict[str, str] = {
    "parallel_chevron_columns_with_connectors": "five_column_closed_loop",
    "four_stage_cards_with_connectors_consensus_and_action_bands": "dense_cards_with_icons",
    "four_stage_process_flow": "dense_cards_with_icons",
    "left_intake_center_hub_right_output": "central_platform_with_side_columns",
    "directed_supply_flow": "five_column_closed_loop",
    "four_stage_process_flow_with_footer": "bottom_chain_with_feedback",
    "hub_and_spoke_resource_consensus": "hub_and_spoke",
    "cards_around_central_hub": "hub_and_spoke",
}

FAMILY_TEMPLATES: dict[str, dict[str, Any]] = {
    "five_column_closed_loop": {
        "label": "五列闭环流程页",
        "min_column_zones": 4,
        "min_zones": 5,
        "requires_main_chain": True,
        "min_connectors": 2,
        "requires_footer_band": True,
        "column_zone_roles": {"supply_column", "process_step", "chevron_column"},
    },
    "central_platform_with_side_columns": {
        "label": "中央平台 + 侧列",
        "min_column_zones": 2,
        "min_zones": 2,
        "requires_main_chain": True,
        "min_connectors": 1,
        "requires_central_node": True,
        "column_zone_roles": {"content_panel", "supply_column", "central_node"},
    },
    "bottom_chain_with_feedback": {
        "label": "底部运行主链 + 反馈沉淀",
        "min_zones": 4,
        "requires_main_chain": True,
        "min_connectors": 2,
        "requires_footer_band": True,
        "footer_roles": {"footer", "footer_chain", "principle_band"},
    },
    "dense_cards_with_icons": {
        "label": "密集图标卡片页",
        "min_column_zones": 3,
        "min_zones": 4,
        "requires_main_chain": True,
        "requires_icon_slots": True,
        "column_zone_roles": {"process_step", "card", "chevron_column"},
    },
    "hub_and_spoke": {
        "label": "中心汇聚 / 辐射页",
        "min_column_zones": 2,
        "min_zones": 4,
        "requires_main_chain": True,
        "min_connectors": 1,
        "requires_central_node": True,
        "requires_icon_slots": True,
        "column_zone_roles": {"process_step", "card", "content_panel"},
    },
    "custom": {
        "label": "未分类 / Agent 自定义",
        "min_zones": 0,
    },
}

ARCHETYPES: dict[str, dict[str, Any]] = {
    "three_stage_goal_timeline": {
        "label": "三阶段目标 / 路线图",
        "required_objects": ["title", "stage_cards", "chain_connectors"],
        "tokens": {"three", "stage", "goal", "timeline", "short", "mid", "long", "roadmap"},
    },
    "policy_pathway": {
        "label": "政策路径 / 建设路径",
        "required_objects": ["title", "process_nodes", "chain_connectors"],
        "tokens": {"policy", "pathway", "process", "flow", "chevron", "closed_loop"},
    },
    "capability_matrix": {
        "label": "能力矩阵 / 责任矩阵",
        "required_objects": ["title", "row_headers", "column_headers", "matrix_cells"],
        "tokens": {"matrix", "capability", "responsibility", "table"},
    },
    "left_right_comparison": {
        "label": "前后对比 / 方案对比",
        "required_objects": ["title", "left_panel", "right_panel", "contrast_labels"],
        "tokens": {"comparison", "compare", "left_right", "before_after", "versus"},
    },
    "four_quadrant_framework": {
        "label": "四象限分析",
        "required_objects": ["title", "quadrants", "axis_labels"],
        "tokens": {"quadrant", "2x2", "four_quadrant"},
    },
    "kpi_dashboard": {
        "label": "指标看板",
        "required_objects": ["title", "metric_cards", "metric_values"],
        "tokens": {"kpi", "dashboard", "metric", "indicator"},
    },
    "organization_architecture": {
        "label": "组织架构 / 技术架构",
        "required_objects": ["title", "hierarchy_nodes", "relationship_connectors"],
        "tokens": {"organization", "architecture", "hierarchy", "platform", "tree"},
    },
    "table_with_callouts": {
        "label": "表格重点标注",
        "required_objects": ["table", "callouts", "highlighted_cells"],
        "tokens": {"callout", "table", "highlight"},
    },
}


def canonical_family(*candidates: str) -> str:
    for raw in candidates:
        value = str(raw or "").strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in CANONICAL_FAMILIES:
            return lowered
        if lowered in FAMILY_ALIASES:
            return FAMILY_ALIASES[lowered]
        for alias, family in FAMILY_ALIASES.items():
            if alias in lowered or lowered in alias:
                return family
    return "custom"


def _zone_roles(zones: list[dict[str, Any]]) -> set[str]:
    roles: set[str] = set()
    for zone in zones:
        if not isinstance(zone, dict):
            continue
        role = str(zone.get("role", "")).strip().lower()
        if role:
            roles.add(role)
        component = str(zone.get("component", "")).strip().lower()
        if component:
            roles.add(component)
    return roles


def _count_column_zones(zones: list[dict[str, Any]], template: dict[str, Any]) -> int:
    column_roles = template.get("column_zone_roles", set())
    count = 0
    for zone in zones:
        if not isinstance(zone, dict):
            continue
        zone_id = str(zone.get("id", "")).lower()
        role = str(zone.get("role", "")).lower()
        component = str(zone.get("component", "")).lower()
        if any(token in zone_id for token in ("col", "stage", "column")):
            count += 1
            continue
        if column_roles and (role in column_roles or component in column_roles):
            count += 1
    return count


def _has_footer_band(zones: list[dict[str, Any]], roles: set[str]) -> bool:
    if roles.intersection({"footer", "footer_chain", "principle_band", "footer_bar"}):
        return True
    return any("footer" in str(zone.get("id", "")).lower() for zone in zones if isinstance(zone, dict))


def _has_central_node(zones: list[dict[str, Any]], roles: set[str]) -> bool:
    if "central_node" in roles:
        return True
    return any(
        "hub" in str(zone.get("id", "")).lower() or "center" in str(zone.get("role", "")).lower()
        for zone in zones
        if isinstance(zone, dict)
    )


def _all_text_tokens(*values: Any) -> set[str]:
    text = " ".join(str(value or "") for value in values).lower()
    return {token for token in re.split(r"[^a-z0-9]+", text) if token}


def _zone_count_with_tokens(zones: list[dict[str, Any]], tokens: set[str]) -> int:
    count = 0
    for zone in zones:
        if not isinstance(zone, dict):
            continue
        haystack = " ".join(str(zone.get(key, "")) for key in ("id", "role", "component", "position_hint")).lower()
        if any(token in haystack for token in tokens):
            count += 1
    return count


def classify_layout_archetype(
    *,
    layout_type: str = "",
    layout_family_legacy: str = "",
    family: str = "custom",
    signals: dict[str, Any] | None = None,
    zones: list[dict[str, Any]] | None = None,
    main_chain: dict[str, Any] | None = None,
    icon_slots: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    signals = signals if isinstance(signals, dict) else {}
    zones = zones if isinstance(zones, list) else []
    main_chain = main_chain if isinstance(main_chain, dict) else {}
    icon_slots = icon_slots if isinstance(icon_slots, list) else []
    connectors = main_chain.get("connectors", [])
    connector_count = len(connectors) if isinstance(connectors, list) else 0
    roles = _zone_roles(zones)
    text_tokens = _all_text_tokens(layout_type, layout_family_legacy, family, " ".join(roles))
    columns = int(signals.get("estimated_column_count") or 0)
    stage_count = _zone_count_with_tokens(zones, {"stage", "goal", "card", "step"})
    table_count = _zone_count_with_tokens(zones, {"table", "matrix", "cell", "row", "column"})
    metric_count = _zone_count_with_tokens(zones, {"kpi", "metric", "indicator", "value"})

    candidates: list[tuple[str, float, list[str]]] = []

    if stage_count == 3 or {"short", "mid", "long"}.issubset(text_tokens):
        candidates.append(("three_stage_goal_timeline", 0.82, ["three stage/card signals"]))
    if connector_count >= 2 and (columns >= 4 or family in {"five_column_closed_loop", "dense_cards_with_icons"}):
        candidates.append(("policy_pathway", 0.76, ["process chain connectors"]))
    if table_count >= 3 or {"matrix", "capability"}.intersection(text_tokens):
        candidates.append(("capability_matrix", 0.78, ["matrix/table signals"]))
    if columns == 2 or {"comparison", "before", "after", "versus"}.intersection(text_tokens):
        candidates.append(("left_right_comparison", 0.70, ["two-column contrast signals"]))
    if {"quadrant", "2x2"}.intersection(text_tokens) or _zone_count_with_tokens(zones, {"quadrant"}) >= 4:
        candidates.append(("four_quadrant_framework", 0.80, ["quadrant signals"]))
    if metric_count >= 2 or {"kpi", "dashboard", "metric"}.intersection(text_tokens):
        candidates.append(("kpi_dashboard", 0.74, ["metric card signals"]))
    if family in {"central_platform_with_side_columns", "hub_and_spoke"} or {"architecture", "hierarchy", "platform"}.intersection(text_tokens):
        candidates.append(("organization_architecture", 0.70, ["central/platform hierarchy signals"]))
    if table_count >= 1 and _zone_count_with_tokens(zones, {"callout", "highlight"}) >= 1:
        candidates.append(("table_with_callouts", 0.76, ["table with callout signals"]))

    if not candidates:
        archetype = "custom"
        confidence = 0.45
        reasons = ["no strong archetype signal"]
        required: list[str] = []
        label = "未分类 / 自定义"
    else:
        archetype, confidence, reasons = sorted(candidates, key=lambda item: item[1], reverse=True)[0]
        meta = ARCHETYPES[archetype]
        required = list(meta["required_objects"])
        label = str(meta["label"])
        if icon_slots and archetype in {"policy_pathway", "kpi_dashboard", "organization_architecture"}:
            confidence = min(0.92, confidence + 0.05)

    return {
        "name": archetype,
        "label": label,
        "confidence": round(confidence, 2),
        "version": ARCHETYPE_VERSION,
        "required_objects": required,
        "signals": reasons,
    }


def classify_detected_layout_family(
    *,
    layout_type: str = "",
    layout_family_legacy: str = "",
    signals: dict[str, Any] | None = None,
    zones: list[dict[str, Any]] | None = None,
    main_chain: dict[str, Any] | None = None,
    icon_slots: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    signals = signals if isinstance(signals, dict) else {}
    zones = zones if isinstance(zones, list) else []
    main_chain = main_chain if isinstance(main_chain, dict) else {}
    icon_slots = icon_slots if isinstance(icon_slots, list) else []

    family = canonical_family(layout_family_legacy, layout_type)
    columns = int(signals.get("estimated_column_count") or 0)
    if family == "custom":
        if signals.get("looks_like_four_stage_cards"):
            family = "dense_cards_with_icons"
        elif columns >= 5:
            family = "five_column_closed_loop"
        elif columns >= 3 and signals.get("has_bottom_principle_band"):
            family = "bottom_chain_with_feedback"
        elif columns >= 3:
            family = "central_platform_with_side_columns"
        elif _has_central_node(zones, _zone_roles(zones)):
            family = "hub_and_spoke"

    template = FAMILY_TEMPLATES.get(family, FAMILY_TEMPLATES["custom"])
    archetype = classify_layout_archetype(
        layout_type=layout_type,
        layout_family_legacy=layout_family_legacy,
        family=family,
        signals=signals,
        zones=zones,
        main_chain=main_chain,
        icon_slots=icon_slots,
    )
    confidence = 0.55
    if family != "custom":
        confidence = 0.72
    if layout_family_legacy or layout_type not in {"", "to_be_completed_by_agent"}:
        confidence = min(0.95, confidence + 0.12)
    if signals.get("looks_like_four_stage_cards"):
        confidence = max(confidence, 0.82)
    classifier_conf = signals.get("classifier_confidence")
    if isinstance(classifier_conf, (int, float)):
        confidence = round((confidence + float(classifier_conf)) / 2, 2)
    else:
        confidence = round(confidence, 2)

    column_ids = [
        str(zone.get("id", ""))
        for zone in zones
        if isinstance(zone, dict) and (
            "col" in str(zone.get("id", "")).lower()
            or "stage" in str(zone.get("id", "")).lower()
            or str(zone.get("role", "")).lower() in template.get("column_zone_roles", set())
        )
    ]
    card_ids = [
        str(zone.get("id", ""))
        for zone in zones
        if isinstance(zone, dict)
        and any(token in str(zone.get("role", "")).lower() for token in ("card", "panel", "step"))
    ]
    connectors = main_chain.get("connectors", [])
    flow_arrows = [
        f"{item.get('from', '')}->{item.get('to', '')}"
        for item in connectors
        if isinstance(item, dict) and item.get("from") and item.get("to")
    ]
    footer_chains = [
        str(zone.get("id", ""))
        for zone in zones
        if isinstance(zone, dict) and "footer" in str(zone.get("id", "")).lower()
    ]
    bottom_bars = [
        str(zone.get("id", ""))
        for zone in zones
        if isinstance(zone, dict)
        and str(zone.get("role", "")).lower() in {"footer", "footer_bar", "principle_band"}
    ]

    return {
        "family": family,
        "label": template.get("label", family),
        "confidence": confidence,
        "template_version": TEMPLATE_VERSION,
        "layout_type": layout_type,
        "layout_family_legacy": layout_family_legacy or layout_type,
        "signals": {
            "estimated_column_count": columns,
            "has_top_guidance_band": bool(signals.get("has_top_guidance_band")),
            "has_bottom_principle_band": bool(signals.get("has_bottom_principle_band")),
            "looks_like_four_stage_cards": bool(signals.get("looks_like_four_stage_cards")),
        },
        "components": {
            "columns": column_ids,
            "cards": card_ids,
            "icon_slots": [str(item.get("id", "")) for item in icon_slots if isinstance(item, dict) and item.get("id")],
            "flow_arrows": flow_arrows,
            "footer_chains": footer_chains,
            "bottom_bars": bottom_bars,
        },
        "archetype": archetype,
    }


def build_detected_layout_family(
    layout: dict[str, Any],
    *,
    measured: dict[str, Any] | None = None,
) -> dict[str, Any]:
    measured = measured if isinstance(measured, dict) else {}
    signals = measured.get("detected_layout_signals", {})
    if not isinstance(signals, dict):
        signals = {}
    classifier = layout.get("page_type_classifier", {})
    if isinstance(classifier, dict) and isinstance(classifier.get("confidence"), (int, float)):
        signals = {**signals, "classifier_confidence": classifier["confidence"]}
    contract = layout.get("structure_contract", {})
    if isinstance(contract, dict):
        detected = contract.get("detected_signals", {})
        if isinstance(detected, dict):
            signals = {**detected, **signals}
    icons = []
    icon_ref = layout.get("icon_reconstruction", {})
    if isinstance(icon_ref, dict) and isinstance(icon_ref.get("icons"), list):
        icons = icon_ref["icons"]
    elif measured.get("icon_slots"):
        icons = measured.get("icon_slots", [])
    return classify_detected_layout_family(
        layout_type=str(layout.get("layout_type", "")),
        layout_family_legacy=str(measured.get("layout_family") or layout.get("layout_type", "")),
        signals=signals,
        zones=layout.get("zones", []) if isinstance(layout.get("zones"), list) else [],
        main_chain=layout.get("main_chain", {}) if isinstance(layout.get("main_chain"), dict) else {},
        icon_slots=icons,
    )


def verify_layout_against_family(layout: dict[str, Any], *, strict: bool = False) -> dict[str, Any]:
    block = layout.get("detected_layout_family")
    if not isinstance(block, dict):
        block = build_detected_layout_family(layout)
    family = str(block.get("family", "custom"))
    template = FAMILY_TEMPLATES.get(family, FAMILY_TEMPLATES["custom"])
    zones = layout.get("zones", []) if isinstance(layout.get("zones"), list) else []
    roles = _zone_roles(zones)
    main_chain = layout.get("main_chain", {}) if isinstance(layout.get("main_chain"), dict) else {}
    connectors = main_chain.get("connectors", []) if isinstance(main_chain.get("connectors"), list) else []
    icons = []
    icon_ref = layout.get("icon_reconstruction", {})
    if isinstance(icon_ref, dict) and isinstance(icon_ref.get("icons"), list):
        icons = icon_ref["icons"]

    errors: list[str] = []
    warnings: list[str] = []

    if family == "custom" and strict:
        warnings.append("Page family is `custom`; template contract checks are advisory only.")

    min_zones = int(template.get("min_zones", 0))
    if min_zones and len(zones) < min_zones:
        errors.append(f"Family `{family}` expects at least {min_zones} zones, found {len(zones)}.")

    min_columns = int(template.get("min_column_zones", 0))
    column_count = _count_column_zones(zones, template)
    if min_columns and column_count < min_columns:
        errors.append(f"Family `{family}` expects at least {min_columns} column/stage zones, found {column_count}.")

    if template.get("requires_main_chain") and not main_chain.get("nodes"):
        errors.append(f"Family `{family}` requires main_chain.nodes.")

    min_connectors = int(template.get("min_connectors", 0))
    if min_connectors and len(connectors) < min_connectors:
        errors.append(f"Family `{family}` expects at least {min_connectors} connector(s), found {len(connectors)}.")

    if template.get("requires_footer_band") and not _has_footer_band(zones, roles):
        errors.append(f"Family `{family}` requires a footer/principle band zone.")

    if template.get("requires_central_node") and not _has_central_node(zones, roles):
        errors.append(f"Family `{family}` requires a central node zone.")

    if template.get("requires_icon_slots") and not icons:
        errors.append(f"Family `{family}` requires icon_reconstruction.icons entries.")

    return {
        "valid": not errors,
        "family": family,
        "template_version": TEMPLATE_VERSION,
        "zones_found": len(zones),
        "column_zones_found": column_count,
        "connectors_found": len(connectors),
        "icons_found": len(icons),
        "errors": errors,
        "warnings": warnings,
        "detected_layout_family": block,
    }
