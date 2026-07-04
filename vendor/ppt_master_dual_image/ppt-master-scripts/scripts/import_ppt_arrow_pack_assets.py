#!/usr/bin/env python3
"""
PPT Master - Import PPT Arrow Pack Assets

Generate reusable arrow templates from repo-local PPT arrow pack SVG sources.

Usage:
    python3 skills/ppt-master/scripts/import_ppt_arrow_pack_assets.py
    python3 skills/ppt-master/scripts/import_ppt_arrow_pack_assets.py --check

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def _tag(elem: ET.Element) -> str:
    return elem.tag.rsplit("}", 1)[-1]


def _parse_viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    value = root.get("viewBox", "0 0 1200 300")
    parts = [float(p) for p in re.split(r"[\s,]+", value.strip()) if p]
    if len(parts) != 4:
        raise ValueError(f"invalid viewBox: {value!r}")
    return parts[0], parts[1], parts[2], parts[3]


def _inner_xml(elem: ET.Element) -> str:
    return ET.tostring(elem, encoding="unicode", short_empty_elements=True)


def _normalize_svg_for_template(root: ET.Element) -> None:
    for elem in root.iter():
        if _tag(elem) == "marker" and elem.get("orient") == "auto-start-reverse":
            elem.set("orient", "auto")
        if _tag(elem) == "path" and re.fullmatch(r"M\s*10\s+0\s+L\s*0\s+5\s+L\s*10\s+10\s*z", elem.get("d", "")):
            elem.set("d", "M0,0 L10,5 L0,10 Z")


def _read_source(arrows_root: Path, local_source: str) -> tuple[str, list[str], tuple[float, float, float, float]]:
    path = arrows_root / local_source
    root = ET.parse(path).getroot()
    _normalize_svg_for_template(root)
    defs = []
    graphics = []
    for child in root:
        tag = _tag(child)
        if tag == "defs":
            defs.append(_inner_xml(child))
        elif tag not in {"title", "metadata"}:
            graphics.append(_inner_xml(child))
    if not graphics:
        raise ValueError(f"no drawable content in {path}")
    return "\n    ".join(defs), graphics, _parse_viewbox(root)


def _layout_transform(viewbox: tuple[float, float, float, float], layout: str, scale_multiplier: float) -> str:
    min_x, min_y, width, height = viewbox
    if layout == "vertical":
        max_w, max_h, center_x, center_y = 980, 430, 640, 350
    elif layout == "low_profile":
        max_w, max_h, center_x, center_y = 880, 250, 640, 350
    else:
        max_w, max_h, center_x, center_y = 980, 430, 640, 350
    scale = min(max_w / width, max_h / height) * scale_multiplier
    tx = center_x - (width * scale) / 2 - min_x * scale
    ty = center_y - (height * scale) / 2 - min_y * scale
    return f"translate({tx:.3f} {ty:.3f}) scale({scale:.6f})"


def _template_svg(
    entry: dict[str, Any],
    defs: str,
    graphics: list[str],
    viewbox: tuple[float, float, float, float],
    license_ref: str,
) -> str:
    key = entry["key"]
    transform = _layout_transform(viewbox, entry.get("layout", "wide"), float(entry.get("scale_multiplier", 1.0)))
    body = "\n    ".join(graphics)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <!--
  PPT Arrow Pack Template
  Source: {entry["local_source"]}
  License: custom pack permission; see {license_ref}
  Regenerate with: python3 skills/ppt-master/scripts/import_ppt_arrow_pack_assets.py
  -->
  {defs}
  <rect width="1280" height="720" fill="#FFFFFF"/>
  <rect x="96" y="106" width="1088" height="488" rx="28" fill="#F8FAFC" stroke="#D9E5F5" stroke-width="2"/>
  <g id="{key}" transform="{transform}">
    {body}
  </g>
  <text x="640" y="650" text-anchor="middle" font-family="Microsoft YaHei, Arial, sans-serif" font-size="17" font-weight="700" fill="#123A73">{key}</text>
</svg>
'''


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_index(arrows_root: Path, entries: list[dict[str, str]], *, check: bool) -> bool:
    index_path = arrows_root / "arrows_index.json"
    index = _load_json(index_path)
    arrows = index.setdefault("arrows", {})
    changed = False
    for entry in entries:
        item = {"summary": entry["summary"]}
        if arrows.get(entry["key"]) != item:
            changed = True
            if not check:
                arrows[entry["key"]] = item
    expected = arrows if not check else {**arrows, **{entry["key"]: {"summary": entry["summary"]} for entry in entries}}
    if index.setdefault("meta", {}).get("total") != len(expected):
        changed = True
        if not check:
            index["meta"]["total"] = len(expected)
    if not check and changed:
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def _connector_tags(key: str, summary: str) -> list[str]:
    text = f"{key.replace('_', ' ')} {summary}".lower()
    tags = []
    for tag in [
        "connector",
        "orthogonal",
        "route",
        "node-link",
        "straight",
        "curve",
        "elbow",
        "fork",
        "merge",
        "split",
        "parallel",
        "dashed",
        "hub",
        "spoke",
        "exchange",
        "cycle",
        "loop",
        "feedback",
        "bus",
        "lane",
        "dependency",
        "architecture",
        "return",
        "bidirectional",
        "vertical",
        "side-rail",
        "data-flow",
    ]:
        needle = tag.replace("-", " ")
        if needle in text or tag in text:
            tags.append(tag)
    if "right angle" in text:
        tags.append("orthogonal")
    if "data flow" in text:
        tags.append("data-flow")
    return sorted(set(tags))


def _source_family(key: str) -> str:
    for number in range(7, 1, -1):
        if key.startswith(f"pptpack{number}_"):
            return f"ppt_arrow_pack_{number:02d}"
    if key.startswith("pptpack_"):
        return "ppt_arrow_pack_01"
    return "built_in"


def _write_connector_index(arrows_root: Path, *, check: bool) -> bool:
    index = _load_json(arrows_root / "arrows_index.json")
    arrows = index["arrows"]
    categories: dict[str, dict[str, Any]] = {
        "core_connector_templates": {
            "title": "Core connector templates",
            "use_for": "Small curated built-in templates for ordinary node links, dependency buses, layer connectors, side rails, and data-flow swimlanes.",
            "selection_hint": "Start here when you need a reliable general-purpose connector before searching the larger pack families.",
            "skip_for": "Large PPT-style block arrows or decorative process chains.",
            "entries": [],
        },
        "orthogonal_route_connectors": {
            "title": "Orthogonal route connectors",
            "use_for": "Right-angle, elbow, branch, route-turn, return, and module-to-module connector paths.",
            "selection_hint": "Best default for architecture pages with cards, modules, layers, and dependency links that need to bend around content.",
            "skip_for": "Central hub-spoke exchange maps or circular feedback loops.",
            "entries": [],
        },
        "node_link_connectors": {
            "title": "Node-link connectors",
            "use_for": "Thin straight, curved, fork, merge, loop-back, and dashed connector lines between existing nodes.",
            "selection_hint": "Use when the slide already has nodes/cards and needs line-level relationships rather than a page-level arrow structure.",
            "skip_for": "Wide structural arrows, chevron phase flows, or hub-spoke maps.",
            "entries": [],
        },
        "hub_exchange_topologies": {
            "title": "Hub exchange topologies",
            "use_for": "Central platform exchange, hub-spoke routing, node-spoke relationships, and multi-direction platform interaction maps.",
            "selection_hint": "Use when one central node coordinates many surrounding systems or stakeholders.",
            "skip_for": "Plain pairwise card-to-card routing.",
            "entries": [],
        },
        "cycle_feedback_routes": {
            "title": "Cycle and feedback routes",
            "use_for": "Closed-loop governance, iterative feedback, return loops, and circular process connector routes.",
            "selection_hint": "Use when the semantic emphasis is feedback, correction, loop-back, or continuous improvement.",
            "skip_for": "Linear dependency lines or simple right-angle routing.",
            "entries": [],
        },
        "bus_lane_dependency_connectors": {
            "title": "Bus, lane, and dependency connectors",
            "use_for": "Architecture support buses, dotted dependency lines, data-flow lanes, vertical taps, side rails, and layer-to-layer connectors.",
            "selection_hint": "Use for enterprise architecture pages where many cards share a common support layer or data lane.",
            "skip_for": "Single isolated node-to-node connectors.",
            "entries": [],
        },
    }
    core_keys = {
        "connector_arrow_set",
        "data_flow_swimlanes",
        "dashed_bus_up_taps",
        "architecture_layer_connectors",
        "dashed_orthogonal_dependency_bus",
        "vertical_feedback_ladder",
        "side_rail_arrow_frame",
        "cycle_feedback_arrows",
    }
    seen: set[str] = set()

    def add(category: str, key: str) -> None:
        if key not in arrows or key in seen:
            return
        summary = arrows[key].get("summary", "")
        categories[category]["entries"].append(
            {
                "key": key,
                "path": f"{key}.svg",
                "summary": summary,
                "tags": _connector_tags(key, summary),
                "source_family": _source_family(key),
            }
        )
        seen.add(key)

    for key in arrows:
        if key in core_keys:
            add("core_connector_templates", key)
    for key in arrows:
        if key.startswith(("pptpack7_orthogonal_connector_", "pptpack6_right_angle_route_connector_", "pptpack4_connector_route_")):
            add("orthogonal_route_connectors", key)
    for key in arrows:
        if key.startswith(("pptpack5_node_link_connector_", "pptpack2_connector_", "pptpack3_connector_")):
            add("node_link_connectors", key)
    for key in arrows:
        if key.startswith("pptpack7_hub_exchange_topology_"):
            add("hub_exchange_topologies", key)
    for key in arrows:
        if key.startswith("pptpack7_cycle_feedback_"):
            add("cycle_feedback_routes", key)
    for key in arrows:
        if key.startswith("pptpack6_multi_lane_data_flow_"):
            add("bus_lane_dependency_connectors", key)

    all_entries = []
    for name, category in categories.items():
        category["entries"].sort(key=lambda item: item["key"])
        category["count"] = len(category["entries"])
        all_entries.extend({"key": item["key"], "category": name} for item in category["entries"])

    connector_index = {
        "meta": {
            "total": len(all_entries),
            "source_index": "arrows_index.json",
            "defaultViewBox": index["meta"].get("defaultViewBox", "0 0 1280 720"),
            "formats": index["meta"].get("formats", ["ppt169"]),
            "filePattern": "{key}.svg",
            "libraryPositioning": "Narrow connector-focused index for selecting relationship arrows from the main arrow template library. Use this before scanning the full arrows_index.json when a page needs node links, orthogonal routes, hub exchange, feedback loops, architecture buses, or dependency lanes.",
            "selection_order": list(categories),
            "updated": index["meta"].get("updated"),
        },
        "usage": {
            "primary_rule": "Use connector_index.json for relationship/link arrows; use arrows_index.json for the full arrow library.",
            "path_rule": "Each entry path is relative to skills/ppt-master/templates/arrows/.",
            "executor_rule": "When a connector template is selected for a generated slide, copy or adapt the SVG geometry into the page SVG while preserving supported marker heads and simple paths for PPTX editability.",
        },
        "categories": categories,
        "all": all_entries,
    }
    path = arrows_root / "connector_index.json"
    content = json.dumps(connector_index, ensure_ascii=False, indent=2) + "\n"
    changed = not path.exists() or path.read_text(encoding="utf-8") != content
    if changed and not check:
        path.write_text(content, encoding="utf-8")
    return changed


def import_assets(repo: Path, *, check: bool = False) -> dict[str, Any]:
    arrows_root = repo / "skills" / "ppt-master" / "templates" / "arrows"
    manifest_paths = [
        arrows_root / "ppt_arrow_pack_sources.json",
        arrows_root / "ppt_arrow_pack2_sources.json",
        arrows_root / "ppt_arrow_pack3_sources.json",
        arrows_root / "ppt_arrow_pack4_sources.json",
        arrows_root / "ppt_arrow_pack5_sources.json",
        arrows_root / "ppt_arrow_pack6_sources.json",
        arrows_root / "ppt_arrow_pack7_sources.json",
    ]
    generated: list[str] = []
    index_entries: list[dict[str, str]] = []
    changed = False
    for manifest_path in manifest_paths:
        if not manifest_path.exists():
            continue
        manifest = _load_json(manifest_path)
        license_ref = manifest.get("meta", {}).get("license_reference", "assets/ppt_arrow_pack_sources/LICENSE_CUSTOM_PPT_ARROWS_USAGE.txt")
        for entry in manifest["sources"]:
            defs, graphics, viewbox = _read_source(arrows_root, entry["local_source"])
            svg = _template_svg(entry, defs, graphics, viewbox, license_ref)
            out = arrows_root / f'{entry["key"]}.svg'
            generated.append(entry["key"])
            index_entries.append({"key": entry["key"], "summary": entry["summary"]})
            if not out.exists() or out.read_text(encoding="utf-8") != svg:
                changed = True
                if not check:
                    out.write_text(svg, encoding="utf-8")
    changed = _write_index(arrows_root, index_entries, check=check) or changed
    changed = _write_connector_index(arrows_root, check=check) or changed
    return {"changed": changed, "generated": generated, "count": len(generated)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate PPT arrow pack templates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3], help="Repository root")
    parser.add_argument("--check", action="store_true", help="Report whether generated files are stale")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = import_assets(args.repo.resolve(), check=args.check)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if args.check and report["changed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
