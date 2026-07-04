#!/usr/bin/env python3
"""
PPT Master - Page Content Checker

Validates that SVG pages visibly render the semantic units promised by a
project page contract. See references/content-quality-gate.md.

Usage:
    python3 scripts/page_content_checker.py <project_path> [--require-contract]

Examples:
    python3 scripts/page_content_checker.py projects/example_ppt169_20260622
    python3 scripts/page_content_checker.py projects/example --require-contract

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
_NUMBER_RE = re.compile(r"^(\d{1,3})")


def _local_name(tag: str) -> str:
    """Return an XML tag without its namespace."""
    return tag.rsplit("}", 1)[-1]


def _page_key(path: Path) -> str:
    """Return the canonical PNN page key from an SVG filename."""
    match = _NUMBER_RE.match(path.stem)
    return f"P{int(match.group(1)):02d}" if match else path.stem


def _number(value: str | None, default: float = 0.0) -> float:
    """Read a simple SVG numeric attribute."""
    try:
        return float((value or "").replace("px", ""))
    except ValueError:
        return default


def _load_contract(project: Path) -> dict[str, Any] | None:
    """Load and minimally validate the project page contract."""
    path = project / "analysis" / "page_contract.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("pages"), list):
        raise ValueError("page_contract.json must contain a top-level pages array")
    return data


def _visible_refs(svg_path: Path) -> tuple[set[str], Counter[str], float]:
    """Collect semantic references, roles, and approximate element coverage."""
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    refs: set[str] = set()
    roles: Counter[str] = Counter()
    boxes: list[tuple[float, float, float, float]] = []
    chrome_tokens = {"background", "bg", "chrome", "header", "footer", "logo", "decor"}

    def walk(element: ET.Element, ignored: bool = False) -> None:
        nonlocal boxes
        element_id = element.get("id", "").lower().replace("_", "-")
        current_ignored = ignored or any(token in element_id.split("-") for token in chrome_tokens)
        ref = element.get("data-ref")
        role = element.get("data-role")
        if ref:
            refs.add(ref)
        if role:
            roles[role] += 1
        if not current_ignored and _local_name(element.tag) in {"rect", "image", "circle", "ellipse"}:
            x = _number(element.get("x"))
            y = _number(element.get("y"))
            width = _number(element.get("width"))
            height = _number(element.get("height"))
            if _local_name(element.tag) == "circle":
                radius = _number(element.get("r"))
                x, y, width, height = _number(element.get("cx")) - radius, _number(element.get("cy")) - radius, radius * 2, radius * 2
            if width > 0 and height > 0:
                boxes.append((x, y, width, height))
        for child in element:
            walk(child, current_ignored)

    walk(root)
    area = sum(width * height for _x, _y, width, height in boxes)
    return refs, roles, min(area / (1280 * 720), 1.0)


def _contract_pages(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index contract records by canonical page id."""
    pages: dict[str, dict[str, Any]] = {}
    for page in contract["pages"]:
        if not isinstance(page, dict) or not isinstance(page.get("page_id"), str):
            raise ValueError("Each contract page needs a string page_id such as P01")
        pages[page["page_id"]] = page
    return pages


def check_project(project: Path, require_contract: bool) -> int:
    """Validate SVG semantic coverage against the project contract."""
    try:
        contract = _load_contract(project)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    if contract is None:
        severity = "ERROR" if require_contract else "WARN"
        print(f"[{severity}] Missing analysis/page_contract.json; semantic gate skipped.")
        return 1 if require_contract else 0

    pages = _contract_pages(contract)
    svg_files = sorted((project / "svg_output").glob("*.svg"))
    errors = 0
    warnings = 0
    print(f"[SCAN] Semantic content check: {len(svg_files)} SVG page(s)")
    for svg_path in svg_files:
        page_id = _page_key(svg_path)
        page = pages.get(page_id)
        if page is None:
            level = "ERROR" if require_contract else "WARN"
            print(f"[{level}] {page_id}: no contract record")
            errors += level == "ERROR"
            warnings += level == "WARN"
            continue
        try:
            refs, roles, coverage = _visible_refs(svg_path)
        except ET.ParseError as exc:
            print(f"[ERROR] {page_id}: invalid SVG XML: {exc}")
            errors += 1
            continue
        required_refs = set(page.get("required_refs", []))
        required_relations = set(page.get("required_relations", []))
        missing_refs = sorted(required_refs - refs)
        missing_relations = sorted(required_relations - refs)
        if missing_refs:
            print(f"[ERROR] {page_id}: missing required refs: {', '.join(missing_refs)}")
            errors += 1
        if missing_relations:
            print(f"[ERROR] {page_id}: missing required relations: {', '.join(missing_relations)}")
            errors += 1
        density = page.get("density", {})
        if isinstance(density, dict) and density.get("minimum_coverage") is not None:
            minimum = float(density["minimum_coverage"])
            level = "ERROR" if density.get("required") else "WARN"
            if coverage < minimum:
                print(f"[{level}] {page_id}: approximate coverage {coverage:.1%} below {minimum:.1%}")
                errors += level == "ERROR"
                warnings += level == "WARN"
        if not missing_refs and not missing_relations:
            print(f"[OK] {page_id}: refs={len(refs)} roles={dict(roles)} coverage={coverage:.1%}")
    missing_svg = sorted(set(pages) - {_page_key(path) for path in svg_files})
    for page_id in missing_svg:
        print(f"[ERROR] {page_id}: contract page has no SVG output")
        errors += 1
    print(f"[SUMMARY] errors={errors} warnings={warnings}")
    return 1 if errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate SVG semantic page coverage.")
    parser.add_argument("project_path", help="PPT Master project directory")
    parser.add_argument("--require-contract", action="store_true", help="Fail if page_contract.json is absent")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return check_project(Path(args.project_path), args.require_contract)


if __name__ == "__main__":
    raise SystemExit(main())
