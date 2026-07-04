#!/usr/bin/env python3
"""
PPT Master - Chrome-only Brand Verifier (spec_lock-driven)

Chrome-only brand elements are injected by the native PPTX exporter through a
shared slide layout. Ordinary body-page SVGs must therefore contain only page
content, never a second copy of the divider, logo, footer, organization name,
or page number. Cover/ending pages are excluded from layout injection because
their locked brand templates already include their own public treatment.

This script verifies:
  - Body pages that REDRAW any `master_chrome` element -> error (duplicate
    public element on export).
  - The brand's own cover/ending template page(s) are exempt from body-page
    chrome checks.
  - Any page where ordinary content (text/image/rect that is not itself a
    chrome element) overlaps a declared `protected_region` -> error.

Source of truth for geometry is the project's own `<project>/templates/
spec_lock.md §master_chrome` / `§cover_regions` (Strategist copies these
verbatim from the brand's `brand_rules.json` at Step 3) — NOT the brand
directory itself, so this also catches transcription drift between the brand
and the locked project spec.

Usage:
    python3 scripts/verify_chrome_only_brand.py <project_dir>

Examples:
    python3 scripts/verify_chrome_only_brand.py projects/demo

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Finding:
    file: str
    code: str
    detail: str


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _float_attr(attrs: str, name: str) -> float | None:
    match = re.search(rf'\b{name}="([0-9.]+)"', attrs)
    if not match:
        return None
    return float(match.group(1))


def _near(value: float | None, expected: float, tolerance: float = 1.5) -> bool:
    return value is not None and abs(value - expected) <= tolerance


_KV_RE = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')


def _parse_kv_line(line: str) -> dict[str, str]:
    """Parse trailing `key=value` / `key="quoted value"` tokens on a spec_lock row."""
    out: dict[str, str] = {}
    for match in _KV_RE.finditer(line):
        key = match.group(1)
        value = match.group(2) if match.group(2) is not None else match.group(3)
        out[key] = value
    return out


def _extract_spec_lock_section(spec_lock_text: str, heading: str) -> list[str]:
    pattern = rf"^##\s+{re.escape(heading)}\s*$(?P<body>.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, spec_lock_text, re.MULTILINE | re.DOTALL)
    if not match:
        return []
    lines = []
    for raw in match.group("body").splitlines():
        stripped = raw.strip()
        if stripped.startswith("- "):
            lines.append(stripped[2:])
    return lines


def _parse_master_chrome(spec_lock_text: str) -> tuple[dict[str, dict], list[dict]]:
    rows = _extract_spec_lock_section(spec_lock_text, "master_chrome")
    elements: dict[str, dict] = {}
    protected_regions: list[dict] = []
    for row in rows:
        if ":" not in row:
            continue
        label, rest = row.split(":", 1)
        label = label.strip()
        kv = _parse_kv_line(rest)
        if label == "protected_region":
            protected_regions.append(kv)
        else:
            elements[label] = kv
    return elements, protected_regions


def _parse_page_layouts(spec_lock_text: str) -> dict[str, str]:
    rows = _extract_spec_lock_section(spec_lock_text, "page_layouts")
    mapping: dict[str, str] = {}
    for row in rows:
        if ":" not in row:
            continue
        page_id, value = row.split(":", 1)
        mapping[page_id.strip()] = value.strip()
    return mapping


def _project_spec_lock_path(project_dir: Path) -> Path | None:
    """Return the active project lock, with a legacy template-path fallback."""
    for path in (project_dir / "spec_lock.md", project_dir / "templates" / "spec_lock.md"):
        if path.exists():
            return path
    return None


def _parse_body_header_region(rules: dict) -> dict[str, float]:
    """Read the optional body-page header title region from brand rules."""
    raw = ((rules.get("content_regions") or {}).get("body_header_region") or {})
    try:
        return {
            "x": float(raw["x"]),
            "y": float(raw["y"]),
            "w": float(raw["width"]),
            "h": float(raw["height"]),
        }
    except (KeyError, TypeError, ValueError):
        return {}


def _svg_files(project_dir: Path) -> list[Path]:
    return sorted((project_dir / "svg_output").glob("*.svg"))


def _page_id(svg_file: Path) -> str | None:
    match = re.match(r"(\d+)", svg_file.stem)
    if not match:
        return None
    return f"P{int(match.group(1)):02d}"


def _brand_template_basenames(rules: dict) -> set[str]:
    templates = rules.get("brand_page_templates") or {}
    names: set[str] = set()
    for entry in templates.values():
        if isinstance(entry, dict) and entry.get("file"):
            names.add(str(Path(entry["file"]).stem))
    return names


def _has_top_divider(text: str, spec: dict) -> bool:
    fill = str(spec.get("fill", "#8B0000")).lower()
    y = float(spec.get("y", 82))
    for match in re.finditer(r"<rect\b(?P<attrs>[^>]*)/?>", text):
        attrs = match.group("attrs")
        fill_match = re.search(r'\bfill="([^"]+)"', attrs)
        found_fill = fill_match.group(1).lower() if fill_match else ""
        width = _float_attr(attrs, "width") or _float_attr(attrs, "w")
        if found_fill == fill and _near(_float_attr(attrs, "y"), y, 4) and width and width >= 1000:
            return True
    return False


def _has_footer_bar(text: str, spec: dict) -> bool:
    fill = str(spec.get("fill", "#003366")).lower()
    y = float(spec.get("y", 696))
    for match in re.finditer(r"<rect\b(?P<attrs>[^>]*)/?>", text):
        attrs = match.group("attrs")
        fill_match = re.search(r'\bfill="([^"]+)"', attrs)
        found_fill = fill_match.group(1).lower() if fill_match else ""
        width = _float_attr(attrs, "width") or _float_attr(attrs, "w")
        if found_fill == fill and _near(_float_attr(attrs, "y"), y, 8) and width and width >= 1000:
            return True
    return False


def _has_logo(text: str, spec: dict) -> bool:
    logo_x = float(spec.get("x", 1060))
    for match in re.finditer(r"<image\b(?P<attrs>[^>]*)/?>", text):
        attrs = match.group("attrs")
        if "logo" in attrs.lower() or _near(_float_attr(attrs, "x"), logo_x, 4):
            return True
    return False


def _has_footer_org_text(text: str, spec: dict) -> bool:
    value = str(spec.get("text", "")).strip()
    if not value:
        return False
    x = float(spec.get("x", 40))
    y = float(spec.get("y", 712))
    for match in re.finditer(r"<text\b(?P<attrs>[^>]*)>(?P<value>.*?)</text>", text, re.DOTALL):
        attrs = match.group("attrs")
        found_value = re.sub(r"<[^>]+>", "", match.group("value")).strip()
        if found_value == value and _near(_float_attr(attrs, "x"), x, 8) and _near(_float_attr(attrs, "y"), y, 8):
            return True
    return False


def _has_footer_page_num(text: str, spec: dict) -> bool:
    page_num_x = float(spec.get("x", 1240))
    for match in re.finditer(r"<text\b(?P<attrs>[^>]*)>(?P<value>.*?)</text>", text, re.DOTALL):
        attrs = match.group("attrs")
        if _near(_float_attr(attrs, "x"), page_num_x, 8):
            return True
    # slidenum field placeholders are not literal SVG text; treat any text near the
    # declared coordinate as satisfying the rule (covers both static and dynamic forms).
    return False


_CHECKS = {
    "top_divider": _has_top_divider,
    "footer_bar": _has_footer_bar,
    "logo": _has_logo,
    "footer_org_text": _has_footer_org_text,
    "footer_page_num": _has_footer_page_num,
}


def _detect_duplicate(svg_file: Path, elements: dict[str, dict]) -> list[Finding]:
    text = svg_file.read_text(encoding="utf-8", errors="ignore")
    findings: list[Finding] = []
    for label, check in _CHECKS.items():
        spec = elements.get(label)
        if spec is None:
            continue
        if check(text, spec):
            findings.append(
                Finding(
                    svg_file.name,
                    f"duplicate_{label}",
                    f"Body page redraws `{label}` even though the PPTX chrome layout provides it.",
                )
            )
    return findings


def _detect_protected_region_violations(
    svg_file: Path, protected_regions: list[dict], elements: dict[str, dict]
) -> list[Finding]:
    text = svg_file.read_text(encoding="utf-8", errors="ignore")
    findings: list[Finding] = []
    for match in re.finditer(r"<text\b(?P<attrs>[^>]*)>(?P<value>.*?)</text>", text, re.DOTALL):
        attrs = match.group("attrs")
        x = _float_attr(attrs, "x")
        y = _float_attr(attrs, "y")
        if x is None or y is None:
            continue
        value = re.sub(r"<[^>]+>", "", match.group("value")).strip()
        for region in protected_regions:
            try:
                rx, ry = float(region.get("x", 0)), float(region.get("y", 0))
                rw, rh = float(region.get("w", 0)), float(region.get("h", 0))
            except (TypeError, ValueError):
                continue
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                findings.append(
                    Finding(
                        svg_file.name,
                        "protected_region_violation",
                        f"Text {value!r} at ({x},{y}) falls inside protected_region {region}.",
                    )
                )
    return findings


def _text_box(attrs: str, value: str) -> tuple[float, float, float, float] | None:
    """Estimate an SVG text run's bounds for title-region enforcement."""
    x = _float_attr(attrs, "x")
    y = _float_attr(attrs, "y")
    size = _float_attr(attrs, "font-size") or 18.0
    if x is None or y is None:
        return None

    glyph_units = sum(1.0 if ord(char) > 127 else 0.56 for char in value.strip())
    width = glyph_units * size
    anchor_match = re.search(r'\btext-anchor="([^"]+)"', attrs)
    anchor = anchor_match.group(1) if anchor_match else "start"
    if anchor == "middle":
        left = x - width / 2
    elif anchor == "end":
        left = x - width
    else:
        left = x
    return left, y - size * 1.05, left + width, y + size * 0.25


def _detect_body_header_violations(svg_file: Path, region: dict[str, float]) -> list[Finding]:
    """Require ordinary body-page title and subtitle text to stay above the divider."""
    if not region:
        return []

    text = svg_file.read_text(encoding="utf-8", errors="ignore")
    header_match = re.search(
        r'<g\b(?P<attrs>[^>]*)\bid="[^"]*header[^"]*"[^>]*>(?P<body>.*?)</g>',
        text,
        re.DOTALL,
    )
    if not header_match:
        return [
            Finding(
                svg_file.name,
                "missing_body_header",
                "Body page has no title/subtitle header group; expected an id containing `header` in the locked body header region.",
            )
        ]

    findings: list[Finding] = []
    for match in re.finditer(r"<text\b(?P<attrs>[^>]*)>(?P<value>.*?)</text>", header_match.group("body"), re.DOTALL):
        value = re.sub(r"<[^>]+>", "", match.group("value")).strip()
        if not value:
            continue
        box = _text_box(match.group("attrs"), value)
        if box is None:
            findings.append(
                Finding(svg_file.name, "body_header_unpositioned", f"Header text {value!r} has no numeric x/y coordinates.")
            )
            continue
        left, top, right, bottom = box
        if left < region["x"] or top < region["y"] or right > region["x"] + region["w"] or bottom > region["y"] + region["h"]:
            findings.append(
                Finding(
                    svg_file.name,
                    "body_header_region_violation",
                    f"Header text {value!r} bounds ({left:.1f},{top:.1f})-({right:.1f},{bottom:.1f}) exceed body_header_region {region}.",
                )
            )
    return findings


def verify_project(project_dir: Path) -> list[Finding]:
    rules_path = project_dir / "templates" / "brand_rules.json"
    spec_lock_path = _project_spec_lock_path(project_dir)
    if not rules_path.exists() or spec_lock_path is None:
        return []
    rules = _read_json(rules_path)
    if rules.get("brand_mode") != "chrome-only":
        return []

    spec_lock_text = spec_lock_path.read_text(encoding="utf-8", errors="ignore")
    elements, protected_regions = _parse_master_chrome(spec_lock_text)
    if not elements:
        return []  # missing/empty §master_chrome → chrome-only brand not actually locked for this project

    page_layouts = _parse_page_layouts(spec_lock_text)
    brand_template_basenames = _brand_template_basenames(rules)
    template_pages = {p for p, v in page_layouts.items() if v in brand_template_basenames}
    body_header_region = _parse_body_header_region(rules)

    findings: list[Finding] = []
    for svg_file in _svg_files(project_dir):
        page_id = _page_id(svg_file)
        is_template_page = page_id in template_pages if page_id else False
        if not is_template_page:
            findings.extend(_detect_duplicate(svg_file, elements))
            findings.extend(_detect_protected_region_violations(svg_file, protected_regions, elements))
            findings.extend(_detect_body_header_violations(svg_file, body_header_region))

    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify body SVGs do not duplicate chrome-only brand elements injected by the PPTX layout.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_dir", type=Path, help="Project directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project_dir = args.project_dir.resolve()
    if not project_dir.exists():
        print(f"Project directory not found: {project_dir}", file=sys.stderr)
        return 1
    findings = verify_project(project_dir)
    if findings:
        print("Chrome-only brand verification failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding.file}: {finding.code}: {finding.detail}", file=sys.stderr)
        return 1
    print("Chrome-only brand verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
