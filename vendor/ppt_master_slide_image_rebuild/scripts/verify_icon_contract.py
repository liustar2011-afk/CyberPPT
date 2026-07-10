#!/usr/bin/env python3
"""
PPT Master - Icon Contract Verifier

Verify icon integrity for ChatGPT precise slide-image rebuild projects. The
script checks icon_manifest.json against rebuilt SVG pages so every functional
icon has a stable data-icon-id and a known reference bbox. With --style-check,
also validates stroke width, cross-icon consistency, and optional preview-based
fill/padding metrics.

Usage:
    python3 scripts/verify_icon_contract.py <project_path>
    python3 scripts/verify_icon_contract.py <project_path> --render --style-check --enforce
    python3 scripts/verify_icon_contract.py <project_path> --style-check --write-report

Examples:
    python3 scripts/verify_icon_contract.py projects/rebuild_demo --enforce

Dependencies:
    Pillow (only when --render visibility checks are enabled)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

try:
    from icon_style_lib import StyleFinding, StylePolicy, check_page_icon_styles
except ImportError:  # pragma: no cover
    from scripts.icon_style_lib import StyleFinding, StylePolicy, check_page_icon_styles  # type: ignore

try:
    from svg_page_discovery import find_page_svg
except ImportError:  # pragma: no cover
    from scripts.svg_page_discovery import find_page_svg  # type: ignore

SVG_NS = "{http://www.w3.org/2000/svg}"
DEFAULT_POSITION_TOLERANCE_PX = 3.0
DEFAULT_SIZE_TOLERANCE_PX = 4.0
DEFAULT_MIN_VISIBLE_PIXEL_RATIO = 0.015
AUTO_ENFORCE_PROFILES = {
    "chatgpt_precise_rebuild",
    "chatgpt_precise_rebuild_icon_contract",
}
REPORT_VERSION = "1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class Finding:
    level: str
    code: str
    message: str
    path: str = ""

    def as_dict(self) -> dict[str, str]:
        data = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.path:
            data["path"] = self.path
        return data


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _number(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    cleaned = []
    for char in text:
        if char.isdigit() or char in ".-":
            cleaned.append(char)
        elif cleaned:
            break
    try:
        return float("".join(cleaned)) if cleaned else None
    except ValueError:
        return None


def _numbers(value: Any) -> list[float]:
    if isinstance(value, list):
        out = []
        for item in value:
            try:
                out.append(float(item))
            except (TypeError, ValueError):
                pass
        return out
    if not isinstance(value, str):
        return []
    normalized = value.replace(",", " ").replace(";", " ")
    out = []
    for item in normalized.split():
        try:
            out.append(float(item))
        except ValueError:
            pass
    return out


def _merge_bbox(boxes: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float] | None:
    if not boxes:
        return None
    x1 = min(box[0] for box in boxes)
    y1 = min(box[1] for box in boxes)
    x2 = max(box[0] + box[2] for box in boxes)
    y2 = max(box[1] + box[3] for box in boxes)
    return x1, y1, x2 - x1, y2 - y1


def _translate(elem: ET.Element) -> tuple[float, float]:
    raw = (elem.get("transform") or "").strip()
    if not raw.startswith("translate"):
        return 0.0, 0.0
    start = raw.find("(")
    end = raw.find(")", start + 1)
    if start < 0 or end < 0:
        return 0.0, 0.0
    nums = _numbers(raw[start + 1:end])
    if len(nums) == 1:
        return nums[0], 0.0
    if len(nums) >= 2:
        return nums[0], nums[1]
    return 0.0, 0.0


def _direct_bbox(elem: ET.Element) -> tuple[float, float, float, float] | None:
    for key in ["data-icon-bbox", "data-bbox", "data-bbox-px"]:
        nums = _numbers(elem.get(key))
        if len(nums) >= 4:
            return nums[0], nums[1], nums[2], nums[3]

    tag = _strip_ns(elem.tag)
    if tag in {"rect", "image", "svg", "foreignObject"}:
        x = _number(elem.get("x")) or 0.0
        y = _number(elem.get("y")) or 0.0
        width = _number(elem.get("width"))
        height = _number(elem.get("height"))
        if width is not None and height is not None:
            return x, y, width, height
    if tag == "circle":
        cx = _number(elem.get("cx"))
        cy = _number(elem.get("cy"))
        radius = _number(elem.get("r"))
        if cx is not None and cy is not None and radius is not None:
            return cx - radius, cy - radius, 2.0 * radius, 2.0 * radius
    if tag == "ellipse":
        cx = _number(elem.get("cx"))
        cy = _number(elem.get("cy"))
        rx = _number(elem.get("rx"))
        ry = _number(elem.get("ry"))
        if cx is not None and cy is not None and rx is not None and ry is not None:
            return cx - rx, cy - ry, 2.0 * rx, 2.0 * ry
    if tag == "line":
        x1 = _number(elem.get("x1"))
        y1 = _number(elem.get("y1"))
        x2 = _number(elem.get("x2"))
        y2 = _number(elem.get("y2"))
        if None not in {x1, y1, x2, y2}:
            left = min(x1, x2)
            top = min(y1, y2)
            return left, top, abs(x2 - x1), abs(y2 - y1)
    if tag in {"polygon", "polyline"}:
        nums = _numbers(elem.get("points"))
        if len(nums) >= 4:
            xs = nums[0::2]
            ys = nums[1::2]
            return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    return None


def _bbox(elem: ET.Element) -> tuple[float, float, float, float] | None:
    direct = _direct_bbox(elem)
    if direct is not None:
        tx, ty = _translate(elem)
        return direct[0] + tx, direct[1] + ty, direct[2], direct[3]
    boxes = []
    for child in list(elem):
        child_box = _bbox(child)
        if child_box is not None:
            boxes.append(child_box)
    merged = _merge_bbox(boxes)
    if merged is None:
        return None
    tx, ty = _translate(elem)
    return merged[0] + tx, merged[1] + ty, merged[2], merged[3]


def _project_relative(project: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = project / path
    return path


def _find_svg_for_page(project: Path, page: dict[str, Any]) -> Path | None:
    explicit = _project_relative(project, page.get("svg"))
    if explicit and explicit.is_file():
        return explicit
    page_id = str(page.get("page_id", "")).strip() or "01"
    page_dir_rel = str(page.get("page_dir", "")).strip()
    page_dir = project / page_dir_rel if page_dir_rel and page_dir_rel != "." else None
    return find_page_svg(project, page_id, page_dir=page_dir)


def _collect_svg_icons(svg: Path) -> dict[str, tuple[ET.Element, tuple[float, float, float, float] | None]]:
    root = ET.parse(svg).getroot()
    icons: dict[str, tuple[ET.Element, tuple[float, float, float, float] | None]] = {}
    for elem in root.iter():
        icon_id = elem.get("data-icon-id")
        if icon_id:
            icons[icon_id] = (elem, _bbox(elem))
    return icons


def _preview_candidates(project: Path, page: dict[str, Any]) -> list[Path]:
    out: list[Path] = []
    explicit = _project_relative(project, page.get("preview_image"))
    if explicit and explicit.is_file():
        out.append(explicit)
    page_id = str(page.get("page_id", "")).strip()
    roots = [
        project / "preview",
        project / "previews",
        project / "render",
        project / "rendered",
        project / "render_v5",
        project / "exports" / "preview_qa",
    ]
    for root in roots:
        if not root.is_dir():
            continue
        stack = [root]
        while stack:
            current = stack.pop()
            for child in current.iterdir():
                if child.is_dir():
                    stack.append(child)
                    continue
                if child.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                    continue
                stems = {child.stem, child.name.removesuffix(".preview.png")}
                if (
                    page_id in stems
                    or any(stem.startswith(page_id + "_") for stem in stems)
                    or child.name in {"page.png", "page-1.png"}
                ):
                    out.append(child)
    return out


def _ensure_preview(project: Path, *, render_backend: str | None = None, hard_gate: bool = False) -> None:
    script = Path(__file__).resolve().parent / "verify_svg_preview.py"
    if not script.is_file():
        return
    if not render_backend:
        try:
            from render_backend_resolve_lib import resolve_project_render_backend
        except ImportError:  # pragma: no cover
            from scripts.render_backend_resolve_lib import resolve_project_render_backend  # type: ignore
        render_backend, _warnings = resolve_project_render_backend(project, hard_gate=hard_gate or True)
    argv = [
        sys.executable,
        str(script),
        str(project),
        "--render",
        "--render-backend",
        render_backend,
    ]
    if hard_gate:
        argv.append("--hard-gate")
    subprocess.run(argv, check=False, capture_output=True, text=True)


def _visible_ratio(image_path: Path, bbox: tuple[float, float, float, float]) -> float | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        image = Image.open(image_path).convert("RGBA")
    except OSError:
        return None
    x, y, width, height = bbox
    left = max(0, int(round(x)))
    top = max(0, int(round(y)))
    right = min(image.width, int(round(x + width)))
    bottom = min(image.height, int(round(y + height)))
    if right <= left or bottom <= top:
        return 0.0
    crop = image.crop((left, top, right, bottom))
    total = crop.width * crop.height
    if total <= 0:
        return 0.0
    ink = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        pixels = list(crop.getdata())
    for red, green, blue, alpha in pixels:
        if alpha <= 20:
            continue
        if red > 245 and green > 245 and blue > 245:
            continue
        if max(red, green, blue) - min(red, green, blue) > 12 or (red + green + blue) / 3 < 238:
            ink += 1
    return ink / total


def _manifest_pages(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    pages = manifest.get("pages")
    if isinstance(pages, list):
        return [page for page in pages if isinstance(page, dict)]
    if isinstance(manifest.get("icons"), list):
        return [{"page_id": manifest.get("page_id", "01"), "icons": manifest.get("icons", [])}]
    return []


def _has_icon_slots(project: Path) -> bool:
    try:
        from slide_image_rebuild_strict_lib import has_icon_slots

        return has_icon_slots(project)
    except ImportError:
        return False


def should_auto_enforce(project: Path) -> bool:
    slide_manifest = _read_json(project / "slide_image_rebuild_manifest.json")
    profile = str(slide_manifest.get("execution_profile", "")).strip().lower()
    if profile in AUTO_ENFORCE_PROFILES:
        return True
    return (project / "icon_manifest.json").is_file()


def verify(
    project: Path,
    *,
    manifest_path: Path | None = None,
    render: bool = False,
    render_backend: str | None = None,
    hard_gate: bool = False,
    style_check: bool = False,
    write_report: bool = False,
    report_path: Path | None = None,
    enforce: bool = False,
) -> dict[str, Any]:
    findings: list[Finding] = []
    style_findings: list[StyleFinding] = []
    manifest_file = manifest_path or project / "icon_manifest.json"
    if not manifest_file.is_absolute():
        manifest_file = project / manifest_file
    if enforce and _has_icon_slots(project) and not manifest_file.is_file():
        findings: list[Finding] = [Finding(
            "error",
            "icon_slots_without_manifest",
            "layout_reference declares icon slots but icon_manifest.json is missing. "
            "Run build_icon_manifest_from_layout.py --write or author icon_manifest.json manually.",
            str(project / "icon_manifest.json"),
        )]
        return _payload(project, manifest_file, [], findings)

    manifest = _read_json(manifest_file)
    if not manifest:
        level = "error" if enforce else "warning"
        findings.append(Finding(
            level,
            "missing_icon_manifest",
            "icon_manifest.json was not found or could not be parsed.",
            str(manifest_file),
        ))
        return _payload(project, manifest_file, [], findings)

    policy = manifest.get("policy", {}) if isinstance(manifest.get("policy"), dict) else {}
    position_tol = float(policy.get("bbox_position_tolerance_px", DEFAULT_POSITION_TOLERANCE_PX))
    size_tol = float(policy.get("bbox_size_tolerance_px", DEFAULT_SIZE_TOLERANCE_PX))
    min_visible_ratio = float(policy.get("min_visible_pixel_ratio", DEFAULT_MIN_VISIBLE_PIXEL_RATIO))
    require_bbox = bool(policy.get("require_bbox", True))
    style_policy = StylePolicy.from_manifest_policy(policy, style_check=style_check)

    if render:
        _ensure_preview(project, render_backend=render_backend, hard_gate=hard_gate)

    page_results = []
    for page in _manifest_pages(manifest):
        page_id = str(page.get("page_id", "")).strip() or "01"
        svg = _find_svg_for_page(project, page)
        page_summary: dict[str, Any] = {"page_id": page_id, "svg": str(svg) if svg else "", "icons": []}
        page_results.append(page_summary)
        if svg is None:
            findings.append(Finding("error", "missing_page_svg", f"No SVG found for page {page_id}.", str(project)))
            continue
        try:
            svg_icons = _collect_svg_icons(svg)
        except ET.ParseError as exc:
            findings.append(Finding("error", "invalid_svg", f"SVG parse failed for page {page_id}: {exc}", str(svg)))
            continue
        manifest_icons = page.get("icons", []) if isinstance(page.get("icons"), list) else []
        expected_ids = set()
        for item in manifest_icons:
            if not isinstance(item, dict):
                continue
            icon_id = str(item.get("id", "")).strip()
            if not icon_id:
                findings.append(Finding("error", "missing_icon_id", f"Page {page_id} has an icon entry without id.", str(manifest_file)))
                continue
            expected_ids.add(icon_id)
            required = item.get("required", True) is not False
            expected_bbox_values = _numbers(item.get("bbox_px"))
            expected_bbox = tuple(expected_bbox_values[:4]) if len(expected_bbox_values) >= 4 else None
            actual = svg_icons.get(icon_id)
            summary = {"id": icon_id, "required": required, "present": actual is not None}
            page_summary["icons"].append(summary)
            if actual is None:
                if required:
                    findings.append(Finding("error", "missing_required_icon", f"Page {page_id} missing required icon {icon_id}.", str(svg)))
                continue
            actual_bbox = actual[1]
            if expected_bbox is None:
                findings.append(Finding("warning", "missing_manifest_bbox", f"Page {page_id} icon {icon_id} has no bbox_px in manifest.", str(manifest_file)))
                continue
            if actual_bbox is None:
                level = "error" if require_bbox else "warning"
                findings.append(Finding(level, "missing_svg_icon_bbox", f"Page {page_id} icon {icon_id} has no verifiable SVG bbox. Add data-icon-bbox.", str(svg)))
                continue
            dx = abs(actual_bbox[0] - expected_bbox[0])
            dy = abs(actual_bbox[1] - expected_bbox[1])
            dw = abs(actual_bbox[2] - expected_bbox[2])
            dh = abs(actual_bbox[3] - expected_bbox[3])
            summary["actual_bbox"] = [round(value, 2) for value in actual_bbox]
            summary["expected_bbox"] = [round(value, 2) for value in expected_bbox]
            # Icon position/size drift is reference-fidelity, not a broken-icon
            # contract violation: advisory only, never a repair-loop trigger.
            if dx > position_tol or dy > position_tol:
                findings.append(Finding("warning", "icon_position_drift", f"Page {page_id} icon {icon_id} position drift is dx={dx:.1f}, dy={dy:.1f}.", str(svg)))
            if dw > size_tol or dh > size_tol:
                findings.append(Finding("warning", "icon_size_drift", f"Page {page_id} icon {icon_id} size drift is dw={dw:.1f}, dh={dh:.1f}.", str(svg)))
            if render:
                preview_paths = _preview_candidates(project, page)
                if not preview_paths:
                    findings.append(Finding("warning", "missing_preview_for_visibility", f"No preview image found for page {page_id}; icon visibility was not checked.", str(project)))
                    continue
                ratio = _visible_ratio(preview_paths[0], expected_bbox)
                if ratio is None:
                    findings.append(Finding("warning", "visibility_check_unavailable", f"Could not inspect preview pixels for page {page_id} icon {icon_id}.", str(preview_paths[0])))
                else:
                    summary["visible_pixel_ratio"] = round(ratio, 5)
                    if ratio < min_visible_ratio:
                        findings.append(Finding("error", "icon_not_visible", f"Page {page_id} icon {icon_id} visible pixel ratio {ratio:.4f} is below {min_visible_ratio:.4f}.", str(preview_paths[0])))
        extra_ids = set(svg_icons) - expected_ids
        for icon_id in sorted(extra_ids):
            findings.append(Finding("warning", "svg_icon_not_in_manifest", f"Page {page_id} SVG icon {icon_id} is not listed in icon_manifest.json.", str(svg)))

        if style_policy.enabled:
            preview_path = _preview_candidates(project, page)[0] if _preview_candidates(project, page) else None
            page_style_findings, style_summaries = check_page_icon_styles(
                page_id=page_id,
                svg_path=svg,
                svg_icons=svg_icons,
                manifest_icons=manifest_icons,
                preview_path=preview_path,
                policy=style_policy,
            )
            style_findings.extend(page_style_findings)
            if style_summaries:
                page_summary["style"] = style_summaries
            for item in page_style_findings:
                findings.append(Finding(
                    item.level,
                    item.code,
                    item.message,
                    item.path or str(svg),
                ))

    return _payload(
        project,
        manifest_file,
        page_results,
        findings,
        style_findings=style_findings,
        style_check=style_policy.enabled,
        write_report=write_report,
        report_path=report_path,
    )


def _payload(
    project: Path,
    manifest: Path,
    pages: list[dict[str, Any]],
    findings: list[Finding],
    *,
    style_findings: list[StyleFinding] | None = None,
    style_check: bool = False,
    write_report: bool = False,
    report_path: Path | None = None,
) -> dict[str, Any]:
    errors = [item.as_dict() for item in findings if item.level == "error"]
    warnings = [item.as_dict() for item in findings if item.level == "warning"]
    style_errors = [item.as_dict() for item in (style_findings or []) if item.level == "error"]
    style_warnings = [item.as_dict() for item in (style_findings or []) if item.level == "warning"]
    payload = {
        "workflow": "slide-image-rebuild",
        "check": "icon_contract",
        "version": REPORT_VERSION,
        "generated_at": utc_now(),
        "project": str(project),
        "manifest": str(manifest),
        "valid": not errors,
        "style_check": style_check,
        "pages": pages,
        "summary": {
            "page_count": len(pages),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "style_error_count": len(style_errors),
            "style_warning_count": len(style_warnings),
        },
        "errors": errors,
        "warnings": warnings,
        "style_errors": style_errors,
        "style_warnings": style_warnings,
    }
    if write_report:
        out = report_path or project / "exports" / "qa" / "icon_contract_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        payload["report_path"] = str(out.relative_to(project))
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify icon contract for precise image rebuild projects.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--manifest", type=Path, default=None, help="Manifest path. Defaults to <project_path>/icon_manifest.json")
    parser.add_argument("--render", action="store_true", help="Also check rendered preview icon visibility when preview images are available")
    parser.add_argument(
        "--render-backend",
        choices=["cairo", "auto"],
        default=None,
        help="Preview render backend when --render is set (defaults to cairo)",
    )
    parser.add_argument(
        "--hard-gate",
        action="store_true",
        help="Fail preview bootstrap when the chosen render backend is unavailable",
    )
    parser.add_argument(
        "--style-check",
        action="store_true",
        help="Check icon stroke width consistency and optional preview fill/padding metrics",
    )
    parser.add_argument("--write-report", action="store_true", help="Write exports/qa/icon_contract_report.json")
    parser.add_argument("--report", type=Path, help="Custom report output path")
    parser.add_argument("--enforce", action="store_true", help="Treat missing icon_manifest.json as an error")
    parser.add_argument(
        "--no-auto-enforce",
        action="store_true",
        help="Do not auto-enable enforce for chatgpt_precise_rebuild or existing icon_manifest.json",
    )
    return parser


def should_auto_style_check(project: Path) -> bool:
    slide_manifest = _read_json(project / "slide_image_rebuild_manifest.json")
    profile = str(slide_manifest.get("execution_profile", "")).strip().lower()
    if profile in AUTO_ENFORCE_PROFILES:
        return True
    manifest = _read_json(project / "icon_manifest.json")
    policy = manifest.get("policy", {}) if isinstance(manifest.get("policy"), dict) else {}
    return policy.get("style_check", False) is True


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = args.project_path.resolve()
    enforce = args.enforce or (not args.no_auto_enforce and should_auto_enforce(project))
    style_check = args.style_check or should_auto_style_check(project)
    payload = verify(
        project,
        manifest_path=args.manifest,
        render=args.render,
        render_backend=args.render_backend,
        hard_gate=args.hard_gate,
        style_check=style_check,
        write_report=args.write_report,
        report_path=args.report,
        enforce=enforce,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
