#!/usr/bin/env python3
"""
PPT Master - Slide Image Rebuild Contract Sync

Normalize and preflight slide-image-rebuild project contracts before strict QA.

Usage:
    python3 scripts/sync_rebuild_contract.py <project_path>
    python3 scripts/sync_rebuild_contract.py <project_path> --write

Examples:
    python3 scripts/sync_rebuild_contract.py projects/demo --write

Dependencies:
    None (standard library only; uses sibling project helpers)
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from build_icon_manifest_lib import build_manifest, write_manifest  # noqa: E402
from json_io import load_json  # noqa: E402

PLACEHOLDER_TOKENS = (
    "to_be_completed_by_agent",
    "待完善正文",
    "参考页标题",
)

REPO_ICON_REPLACED_IMPLEMENTATIONS = {
    "",
    "semantic_vector",
    "hand_vector",
    "tight_icon_crop",
}

CANVAS_PRESETS = {
    "ppt169": {"aspect": "16:9", "width_px": 1280, "height_px": 720},
    "ppt43": {"aspect": "4:3", "width_px": 1024, "height_px": 768},
    "story": {"aspect": "9:16", "width_px": 1080, "height_px": 1920},
    "xhs": {"aspect": "3:4", "width_px": 1242, "height_px": 1660},
    "xiaohongshu": {"aspect": "3:4", "width_px": 1242, "height_px": 1660},
}

def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return any(token in value for token in PLACEHOLDER_TOKENS)
    if isinstance(value, list):
        return any(_contains_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_placeholder(item) for item in value.values())
    return False


def _clean_placeholder(value: Any, replacement: str = "") -> tuple[Any, int]:
    if isinstance(value, str):
        cleaned = value
        count = 0
        for token in PLACEHOLDER_TOKENS:
            if token in cleaned:
                cleaned = cleaned.replace(token, replacement)
                count += 1
        return cleaned.strip(), count
    if isinstance(value, list):
        out = []
        count = 0
        for item in value:
            cleaned, item_count = _clean_placeholder(item, replacement)
            out.append(cleaned)
            count += item_count
        return out, count
    if isinstance(value, dict):
        out = {}
        count = 0
        for key, item in value.items():
            cleaned, item_count = _clean_placeholder(item, replacement)
            out[key] = cleaned
            count += item_count
        return out, count
    return value, 0


def _manifest_format(project: Path) -> str:
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    fmt = str(manifest.get("format") or "").strip()
    return fmt or "ppt169"


def _normalize_canvas(layout: dict[str, Any], fmt: str) -> bool:
    preset = CANVAS_PRESETS.get(fmt) or CANVAS_PRESETS.get(fmt.lower())
    if not preset:
        return False
    canvas = layout.get("canvas")
    if not isinstance(canvas, dict):
        layout["canvas"] = {**preset, "safe_margin_px": 12}
        return True
    changed = False
    for key, value in preset.items():
        if canvas.get(key) != value:
            canvas[key] = value
            changed = True
    canvas.setdefault("safe_margin_px", 12)
    return changed


def _normalize_icon_strategy(layout: dict[str, Any]) -> int:
    icon_reconstruction = layout.get("icon_reconstruction")
    if not isinstance(icon_reconstruction, dict):
        return 0
    changed = 0
    if icon_reconstruction.get("policy") != "repo_library_first":
        icon_reconstruction["policy"] = "repo_library_first"
        changed += 1
    icon_reconstruction.setdefault(
        "preferred_libraries",
        ["tabler-outline", "tabler-filled", "chunk-filled", "phosphor-duotone"],
    )
    entries = icon_reconstruction.get("icons")
    if not isinstance(entries, list):
        return changed
    for icon in entries:
        if not isinstance(icon, dict):
            continue
        implementation = str(icon.get("implementation") or "").strip()
        if implementation in REPO_ICON_REPLACED_IMPLEMENTATIONS:
            icon["implementation"] = "asset_svg"
            icon["fallback_allowed"] = False
            changed += 1
    return changed


def _main_chain_labels(layout: dict[str, Any]) -> list[str]:
    main_chain = layout.get("main_chain")
    if not isinstance(main_chain, dict):
        return []
    nodes = main_chain.get("nodes")
    if not isinstance(nodes, list):
        return []
    labels = []
    for node in nodes:
        if isinstance(node, dict):
            label = str(node.get("label") or node.get("id") or "").strip()
            if label:
                labels.append(label)
    return labels


def _sync_content_mapping(content: dict[str, Any], labels: list[str]) -> bool:
    renderable = content.get("renderable_content")
    if not isinstance(renderable, dict) or not labels:
        return False
    current = renderable.get("main_chain_labels")
    if current != labels:
        renderable["main_chain_labels"] = labels
        return True
    return False


def _layout_page_entries(project: Path) -> list[tuple[str, Path]]:
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    pages = manifest.get("pages")
    entries: list[tuple[str, Path]] = []
    if isinstance(pages, list) and pages:
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_id = str(page.get("page_id") or "P01").strip()
            page_dir_raw = page.get("page_dir")
            page_dir = project / str(page_dir_raw) if isinstance(page_dir_raw, str) and page_dir_raw else project
            layout_path = page_dir / "layout_reference.json"
            if not layout_path.exists():
                layout_path = project / "layout_reference.json"
            if layout_path.exists():
                entries.append((page_id, layout_path))
        if entries:
            return entries
    root = project / "layout_reference.json"
    return [("P01", root)] if root.exists() else []


def _svg_path_for_page(project: Path, page_id: str) -> Path | None:
    svg_dir = project / "svg_output"
    if not svg_dir.is_dir():
        return None
    direct = svg_dir / f"{page_id}.svg"
    if direct.exists():
        return direct
    svgs = sorted(svg_dir.glob("*.svg"))
    return svgs[0] if len(svgs) == 1 else None


def _svg_marker_sets(svg_path: Path) -> tuple[set[str], set[str]]:
    try:
        root = ET.parse(svg_path).getroot()
    except ET.ParseError:
        return set(), set()
    zone_ids: set[str] = set()
    icon_ids: set[str] = set()
    for elem in root.iter():
        zone_id = elem.attrib.get("data-zone-id")
        if zone_id:
            zone_ids.add(zone_id)
        icon_id = elem.attrib.get("data-icon-id")
        if icon_id:
            icon_ids.add(icon_id)
    return zone_ids, icon_ids


def _collect_expected_ids(layout: dict[str, Any]) -> tuple[set[str], set[str]]:
    zones = layout.get("zones")
    zone_ids: set[str] = set()
    if isinstance(zones, list):
        for zone in zones:
            if isinstance(zone, dict):
                zone_id = str(zone.get("id", "")).strip()
                if zone_id:
                    zone_ids.add(zone_id)
    icons = layout.get("icon_reconstruction")
    icon_entries = icons.get("icons") if isinstance(icons, dict) else None
    icon_ids: set[str] = set()
    if isinstance(icon_entries, list):
        for icon in icon_entries:
            if isinstance(icon, dict):
                icon_id = str(icon.get("id", "")).strip()
                if icon_id:
                    icon_ids.add(icon_id)
    return zone_ids, icon_ids


def _clean_legacy_icon_crops(project: Path, *, write: bool, actions: list[str]) -> None:
    crop_dir = project / "images" / "icon_crops"
    if not crop_dir.exists():
        return
    if write:
        for path in sorted(crop_dir.glob("*")):
            if path.is_file():
                path.unlink()
        try:
            crop_dir.rmdir()
        except OSError:
            pass
    actions.append("removed legacy images/icon_crops" if write else "would remove legacy images/icon_crops")


def _normalize_icon_manifest(project: Path, *, write: bool, actions: list[str], warnings: list[str]) -> None:
    manifest_path = project / "icon_manifest.json"
    existing = _read_json(manifest_path)
    if isinstance(existing, dict):
        changed = 0
        pages = existing.get("pages")
        if isinstance(pages, list):
            for page in pages:
                if not isinstance(page, dict):
                    continue
                icons = page.get("icons")
                if not isinstance(icons, list):
                    continue
                for icon in icons:
                    if not isinstance(icon, dict):
                        continue
                    implementation = str(icon.get("implementation") or "").strip()
                    if implementation in REPO_ICON_REPLACED_IMPLEMENTATIONS:
                        icon["implementation"] = "asset_svg"
                        icon["fallback_allowed"] = False
                        changed += 1
        if changed:
            actions.append(
                f"{'updated' if write else 'would update'} {changed} existing icon_manifest implementation value(s) to repo-icons"
            )
            if write:
                _write_json(manifest_path, existing)
        else:
            actions.append("kept existing icon_manifest.json entries")
        return

    icon_manifest = build_manifest(project)
    icon_count = int(icon_manifest.get("summary", {}).get("icon_count", 0))
    if icon_count:
        actions.append(f"{'wrote' if write else 'would write'} icon_manifest.json with {icon_count} repo-icon-first entries")
        if write:
            write_manifest(project, icon_manifest, force=False)
    else:
        warnings.append("No icon entries found in layout_reference.")


def sync_project(project: Path, *, write: bool = False) -> dict[str, Any]:
    project = project.resolve()
    fmt = _manifest_format(project)
    actions: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    labels_by_layout: dict[Path, list[str]] = {}
    for page_id, layout_path in _layout_page_entries(project):
        layout = _read_json(layout_path)
        if not isinstance(layout, dict):
            errors.append(f"{layout_path}: missing or invalid layout_reference.json")
            continue

        changed = False
        if _normalize_canvas(layout, fmt):
            changed = True
            actions.append(f"normalized canvas in {layout_path.relative_to(project)} to {fmt}")
        icon_changes = _normalize_icon_strategy(layout)
        if icon_changes:
            changed = True
            actions.append(
                f"normalized {icon_changes} icon strategy value(s) in {layout_path.relative_to(project)} to repo-icons"
            )

        cleaned, count = _clean_placeholder(layout)
        if count:
            layout = cleaned
            changed = True
            actions.append(f"cleaned {count} placeholder value(s) in {layout_path.relative_to(project)}")

        labels_by_layout[layout_path] = _main_chain_labels(layout)
        if changed and write:
            _write_json(layout_path, layout)

        svg_path = _svg_path_for_page(project, page_id)
        if svg_path is not None:
            expected_zones, expected_icons = _collect_expected_ids(layout)
            actual_zones, actual_icons = _svg_marker_sets(svg_path)
            missing_zones = sorted(expected_zones - actual_zones)
            missing_icons = sorted(expected_icons - actual_icons)
            for zone_id in missing_zones:
                errors.append(f"{svg_path.relative_to(project)} missing data-zone-id `{zone_id}`")
            for icon_id in missing_icons:
                errors.append(f"{svg_path.relative_to(project)} missing data-icon-id `{icon_id}`")
        else:
            warnings.append(f"No svg_output file found for page `{page_id}`; marker check skipped.")

    content_path = project / "content_mapping.json"
    content = _read_json(content_path)
    if isinstance(content, dict):
        cleaned, count = _clean_placeholder(content)
        content_changed = count > 0
        if count:
            content = cleaned
            actions.append(f"cleaned {count} placeholder value(s) in content_mapping.json")
        labels = next((item for item in labels_by_layout.values() if item), [])
        if _sync_content_mapping(content, labels):
            content_changed = True
            actions.append("synced content_mapping main_chain_labels from layout_reference")
        if content_changed and write:
            _write_json(content_path, content)
    elif content_path.exists():
        errors.append("content_mapping.json is invalid JSON")

    for path in [project / "text_region_map.json", project / "svg_build_plan.json"]:
        payload = _read_json(path)
        if payload is None:
            continue
        cleaned, count = _clean_placeholder(payload)
        if count:
            actions.append(f"cleaned {count} placeholder value(s) in {path.name}")
            if write:
                _write_json(path, cleaned)

    _normalize_icon_manifest(project, write=write, actions=actions, warnings=warnings)

    _clean_legacy_icon_crops(project, write=write, actions=actions)

    remaining_placeholders = []
    for path in [
        project / "layout_reference.json",
        project / "content_mapping.json",
        project / "text_region_map.json",
        project / "svg_build_plan.json",
    ]:
        payload = _read_json(path)
        if payload is not None and _contains_placeholder(payload):
            remaining_placeholders.append(path.name)
    for name in remaining_placeholders:
        errors.append(f"{name} still contains scaffold placeholder text")

    return {
        "valid": not errors,
        "write": write,
        "project": str(project),
        "actions": actions,
        "warnings": warnings,
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize slide-image-rebuild project contracts before strict QA.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project", help="slide-image-rebuild project directory")
    parser.add_argument("--write", action="store_true", help="write fixes instead of reporting dry-run actions")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project = Path(args.project)
    result = sync_project(project, write=args.write)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
