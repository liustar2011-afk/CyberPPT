#!/usr/bin/env python3
"""
PPT Master - Reference Layout Similarity Gate

Compare a rendered slide preview against images/reference_layout.png (or the path
declared in layout_reference.json). Used by 复刻流程2 pre-export to block
contract-only SVG that does not resemble the reference image.

Usage:
    python3 scripts/verify_reference_similarity.py <project_path>
    python3 scripts/verify_reference_similarity.py <project_path> --render
    python3 scripts/verify_reference_similarity.py <project_path> --threshold 58

Dependencies:
    Pillow; cairosvg when --render and preview PNG must be generated.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageChops, ImageStat
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required. Install project requirements first.") from exc

try:
    from render_preview_backend import RenderResult, ensure_preview_for_svg
except ImportError:  # pragma: no cover
    from scripts.render_preview_backend import RenderResult, ensure_preview_for_svg  # type: ignore

try:
    from svg_page_discovery import list_page_svg_candidates
except ImportError:  # pragma: no cover
    from scripts.svg_page_discovery import list_page_svg_candidates  # type: ignore

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_MEAN_THRESHOLD = 58.0
DEFAULT_ANCHOR_THRESHOLD = 4.0
ZONE_BANDS = (
    ("top", 0, 128),
    ("guidance", 128, 172),
    ("header", 172, 222),
    ("main", 222, 652),
    ("footer", 652, 720),
)
ZONE_THRESHOLDS = {
    "top": 70.0,
    "guidance": 82.0,
    "header": 88.0,
    "main": 62.0,
    "footer": 88.0,
}


def _is_navy(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel
    return r < 80 and g < 110 and b > 95 and b > r + 20


def _is_red(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel
    return r > 170 and g < 100 and b < 100


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _find_reference_image(project: Path) -> Path | None:
    layout = _load_json(project / "layout_reference.json")
    source = layout.get("source_reference", {}) if isinstance(layout, dict) else {}
    if isinstance(source, dict):
        raw = source.get("path", "")
        if raw:
            candidate = project / str(raw)
            if candidate.is_file():
                return candidate
    images = project / "images"
    if images.is_dir():
        for pattern in ("reference_layout.*", "reference.*", "*reference*layout*"):
            matches = sorted(images.glob(pattern))
            for path in matches:
                if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    return path
    return None


def _svg_candidates(project: Path) -> list[Path]:
    final_svgs = sorted((project / "svg_final").glob("*.svg"))
    if final_svgs:
        return final_svgs
    return sorted((project / "svg_output").glob("*.svg"))


def _resolve_path(base: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _page_dir(project: Path, page: dict[str, Any]) -> Path:
    for key in ["project_path", "page_project", "page_dir"]:
        resolved = _resolve_path(project, page.get(key))
        if resolved is not None:
            return resolved
    page_id = str(page.get("page_id", ""))
    candidate = project / "pages" / page_id
    return candidate if candidate.is_dir() else project


def _preview_path(project: Path, svg: Path) -> Path:
    return project / "exports" / "preview_qa" / f"{svg.stem}.preview.png"


def _post_render_preview_checks(
    svg: Path,
    preview: Path,
    render_backend: str,
    *,
    errors: list[str],
    warnings: list[str],
) -> None:
    try:
        from preview_cjk_lib import detect_preview_cjk_tofu, preview_is_nonblank, svg_text_has_cjk
    except ImportError:  # pragma: no cover
        from scripts.preview_cjk_lib import (  # type: ignore
            detect_preview_cjk_tofu,
            preview_is_nonblank,
            svg_text_has_cjk,
        )
    if not svg_text_has_cjk(svg):
        return
    if not preview_is_nonblank(preview):
        errors.append("preview_cjk_blank")
    if detect_preview_cjk_tofu(preview, svg):
        errors.append("preview_cjk_tofu_detected")
        if render_backend == "cairo":
            warnings.append(
                "CJK tofu detected in Cairo preview — ensure CJK fonts are installed "
                "(macOS: system fonts; Linux: apt install fonts-noto-cjk)."
            )


def _apply_render_result(payload: dict[str, Any], render_result: RenderResult | None) -> None:
    if render_result is None:
        return
    payload["render_backend"] = render_result.backend
    payload["render_meta"] = str(render_result.meta_path)
    if render_result.warnings:
        payload.setdefault("warnings", []).extend(list(render_result.warnings))
    if not render_result.ok:
        payload["valid"] = False
        payload.setdefault("errors", []).extend(list(render_result.errors))


def _ensure_preview(
    project: Path,
    svg: Path,
    preview: Path,
    *,
    render: bool,
    render_backend: str,
    hard_gate: bool,
    force_render: bool,
    server_url: str | None,
) -> RenderResult:
    return ensure_preview_for_svg(
        project,
        svg,
        preview,
        render=render,
        render_backend=render_backend,
        hard_gate=hard_gate,
        force_render=force_render,
        server_url=server_url,
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
    )


try:  # shared helper; see scripts/image_io.py
    from image_io import resize_rgb as _resize_rgb
except ImportError:  # pragma: no cover - package-context import
    from scripts.image_io import resize_rgb as _resize_rgb  # type: ignore


def _zone_means(ref: Image.Image, out: Image.Image) -> dict[str, float]:
    zones: dict[str, float] = {}
    width = ref.width
    for name, y0, y1 in ZONE_BANDS:
        band_ref = ref.crop((0, y0, width, y1))
        band_out = out.crop((0, y0, width, y1))
        zones[name] = float(ImageStat.Stat(ImageChops.difference(band_ref, band_out)).mean[0])
    return zones


def _runs_from_rows(rows: list[int]) -> list[list[int]]:
    if not rows:
        return []
    runs: list[list[int]] = []
    start = rows[0]
    previous = rows[0]
    for row in rows[1:]:
        if row == previous + 1:
            previous = row
            continue
        runs.append([start, previous])
        start = row
        previous = row
    runs.append([start, previous])
    return runs


def _color_row_runs(
    image: Image.Image,
    *,
    y0: int,
    y1: int,
    predicate: Any,
    min_row_ratio: float = 0.12,
) -> list[list[int]]:
    rows: list[int] = []
    width = image.width
    threshold = max(1, int(width * min_row_ratio))
    for y in range(max(0, y0), min(image.height, y1)):
        count = 0
        for x in range(width):
            if predicate(image.getpixel((x, y))):
                count += 1
        if count >= threshold:
            rows.append(y)
    return _runs_from_rows(rows)


def _structure_diagnostics(ref: Image.Image, out: Image.Image) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}
    for name, y0, y1 in ZONE_BANDS:
        diagnostics[name] = {
            "reference_navy_rows": _color_row_runs(ref, y0=y0, y1=y1, predicate=_is_navy),
            "candidate_navy_rows": _color_row_runs(out, y0=y0, y1=y1, predicate=_is_navy),
            "reference_red_rows": _color_row_runs(ref, y0=y0, y1=y1, predicate=_is_red),
            "candidate_red_rows": _color_row_runs(out, y0=y0, y1=y1, predicate=_is_red),
        }
    return diagnostics


def _structure_hints(
    zones: dict[str, float],
    limits: dict[str, float],
    diagnostics: dict[str, Any],
) -> list[str]:
    hints: list[str] = []
    for name, value in zones.items():
        limit = limits.get(name, DEFAULT_MEAN_THRESHOLD + 20)
        if value <= limit:
            continue
        diag = diagnostics.get(name, {})
        ref_navy = diag.get("reference_navy_rows", [])
        out_navy = diag.get("candidate_navy_rows", [])
        ref_red = diag.get("reference_red_rows", [])
        out_red = diag.get("candidate_red_rows", [])
        if ref_navy or out_navy:
            hints.append(
                f"zone `{name}` navy rows differ: reference={ref_navy or 'none'}, "
                f"candidate={out_navy or 'none'}"
            )
        if ref_red or out_red:
            hints.append(
                f"zone `{name}` red rows differ: reference={ref_red or 'none'}, "
                f"candidate={out_red or 'none'}"
            )
    return hints


def _edge_strength_at_row(image: Image.Image, y: int) -> float:
    if y <= 0 or y >= image.height:
        return 0.0
    upper = image.crop((0, y - 1, image.width, y))
    lower = image.crop((0, y, image.width, y + 1))
    diff = ImageChops.difference(upper, lower)
    return float(sum(ImageStat.Stat(diff).mean) / 3)


def _nearest_edge_y(image: Image.Image, expected_y: float, *, window: int = 14) -> tuple[int, float]:
    expected = int(round(expected_y))
    y0 = max(1, expected - window)
    y1 = min(image.height - 1, expected + window)
    best_y = expected
    best_strength = 0.0
    for y in range(y0, y1 + 1):
        strength = _edge_strength_at_row(image, y)
        if strength > best_strength:
            best_y = y
            best_strength = strength
    return best_y, best_strength


def _anchor_edges(layout: dict[str, Any], *, height: int) -> list[dict[str, Any]]:
    anchors = layout.get("visual_anchors", [])
    if not isinstance(anchors, list):
        return []
    canvas = layout.get("canvas", {})
    canvas_h = float(canvas.get("height_px") or height) if isinstance(canvas, dict) else float(height)
    y_scale = height / canvas_h if canvas_h else 1.0
    edges: list[dict[str, Any]] = []
    for anchor in anchors:
        if not isinstance(anchor, dict):
            continue
        anchor_id = str(anchor.get("id") or f"anchor_{len(edges) + 1}")
        anchor_type = anchor.get("type")
        if anchor_type == "horizontal_edge" and isinstance(anchor.get("y"), (int, float)):
            edges.append({
                "id": anchor_id,
                "type": "horizontal_edge",
                "expected_y": float(anchor["y"]) * y_scale,
            })
        elif anchor_type == "band" and isinstance(anchor.get("bbox_px"), list) and len(anchor["bbox_px"]) == 4:
            bbox = anchor["bbox_px"]
            if all(isinstance(item, (int, float)) for item in bbox):
                top = float(bbox[1]) * y_scale
                bottom = float(bbox[1] + bbox[3]) * y_scale
                edges.append({"id": f"{anchor_id}.top", "type": "band_top", "expected_y": top})
                edges.append({"id": f"{anchor_id}.bottom", "type": "band_bottom", "expected_y": bottom})
    return edges


def _anchor_drift_report(
    layout: dict[str, Any],
    ref: Image.Image,
    out: Image.Image,
    *,
    threshold: float = DEFAULT_ANCHOR_THRESHOLD,
) -> dict[str, Any]:
    checked: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    for edge in _anchor_edges(layout, height=ref.height):
        expected_y = float(edge["expected_y"])
        ref_y, ref_strength = _nearest_edge_y(ref, expected_y)
        out_y, out_strength = _nearest_edge_y(out, expected_y)
        if ref_strength < 2.0 and out_strength < 2.0:
            warnings.append(f"anchor `{edge['id']}` has no strong local edge near y={expected_y:.1f}; skipped drift gate")
            continue
        delta = out_y - ref_y
        item = {
            "id": edge["id"],
            "type": edge["type"],
            "expected_y": round(expected_y, 1),
            "reference_y": ref_y,
            "candidate_y": out_y,
            "delta_px": delta,
            "reference_strength": round(ref_strength, 2),
            "candidate_strength": round(out_strength, 2),
        }
        checked.append(item)
        if abs(delta) > threshold:
            errors.append(f"anchor `{edge['id']}` drift {delta}px exceeds {threshold:.1f}px")
    return {
        "threshold_px": threshold,
        "checked": checked,
        "errors": errors,
        "warnings": warnings,
    }


def compare_images(
    reference: Path,
    candidate: Path,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    mean_threshold: float = DEFAULT_MEAN_THRESHOLD,
    zone_thresholds: dict[str, float] | None = None,
    layout_reference: dict[str, Any] | None = None,
    anchor_threshold: float = DEFAULT_ANCHOR_THRESHOLD,
) -> dict[str, Any]:
    size = (width, height)
    ref_img = _resize_rgb(reference, size)
    out_img = _resize_rgb(candidate, size)
    diff = ImageChops.difference(ref_img, out_img)
    mean_diff = float(ImageStat.Stat(diff).mean[0])
    zones = _zone_means(ref_img, out_img)
    limits = zone_thresholds or ZONE_THRESHOLDS
    diagnostics = _structure_diagnostics(ref_img, out_img)
    anchor_report = (
        _anchor_drift_report(layout_reference, ref_img, out_img, threshold=anchor_threshold)
        if layout_reference
        else {"threshold_px": anchor_threshold, "checked": [], "errors": [], "warnings": []}
    )

    errors: list[str] = []
    warnings: list[str] = []
    if mean_diff > mean_threshold:
        errors.append(
            f"mean pixel difference {mean_diff:.1f} exceeds threshold {mean_threshold:.1f} "
            f"(reference {reference.name} vs {candidate.name})"
        )
    for name, value in zones.items():
        limit = limits.get(name, mean_threshold + 20)
        if value > limit:
            errors.append(f"zone `{name}` mean diff {value:.1f} exceeds {limit:.1f}")
    errors.extend(anchor_report["errors"])
    warnings.extend(anchor_report["warnings"])
    hints = _structure_hints(zones, limits, diagnostics)

    payload = {
        "valid": not errors,
        "reference": str(reference),
        "candidate": str(candidate),
        "size": list(size),
        "mean_diff": round(mean_diff, 2),
        "mean_threshold": mean_threshold,
        "zones": {key: round(value, 2) for key, value in zones.items()},
        "zone_thresholds": limits,
        "anchor_drift": anchor_report,
        "errors": errors,
        "warnings": warnings,
    }
    if errors:
        payload["structure_diagnostics"] = diagnostics
        payload["structure_hints"] = hints
    return payload


def verify_project(
    project: Path,
    *,
    render: bool = False,
    mean_threshold: float = DEFAULT_MEAN_THRESHOLD,
    anchor_threshold: float = DEFAULT_ANCHOR_THRESHOLD,
    svg_path: Path | None = None,
    object_level: bool = False,
    fail_on_local_diff: bool = False,
    write_object_report: bool = False,
    render_backend: str = "cairo",
    hard_gate: bool = False,
    force_render: bool = False,
    server_url: str | None = None,
) -> dict[str, Any]:
    manifest = _load_json(project / "slide_image_rebuild_manifest.json")
    pages = manifest.get("pages", []) if isinstance(manifest, dict) else []
    if svg_path is None and isinstance(pages, list) and pages:
        return verify_manifest_pages(
            project,
            pages=pages,
            render=render,
            mean_threshold=mean_threshold,
            anchor_threshold=anchor_threshold,
            object_level=object_level,
            fail_on_local_diff=fail_on_local_diff,
            write_object_report=write_object_report,
            render_backend=render_backend,
            hard_gate=hard_gate,
            force_render=force_render,
            server_url=server_url,
        )

    layout = _load_json(project / "layout_reference.json")
    reference = _find_reference_image(project)
    if not reference:
        return {
            "valid": False,
            "errors": ["No reference image found (images/reference_layout.* or layout_reference.json source_reference.path)"],
            "warnings": [],
        }

    svgs = [svg_path] if svg_path else _svg_candidates(project)
    if not svgs:
        return {"valid": False, "errors": ["No SVG pages in svg_final/ or svg_output/"], "warnings": []}

    svg = svgs[0]
    preview = _preview_path(project, svg)
    render_result = _ensure_preview(
        project,
        svg,
        preview,
        render=render,
        render_backend=render_backend,
        hard_gate=hard_gate,
        force_render=force_render,
        server_url=server_url,
    )
    if not render_result.ok:
        payload = {
            "valid": False,
            "errors": list(render_result.errors),
            "warnings": list(render_result.warnings),
            "reference": str(reference),
            "svg": str(svg),
            "preview": str(preview),
            "render_backend": render_result.backend,
            "render_meta": str(render_result.meta_path),
        }
        return payload

    quality_errors: list[str] = []
    quality_warnings: list[str] = list(render_result.warnings)
    if render:
        _post_render_preview_checks(
            svg,
            preview,
            render_result.backend,
            errors=quality_errors,
            warnings=quality_warnings,
        )
    if quality_errors:
        return {
            "valid": False,
            "errors": quality_errors,
            "warnings": quality_warnings,
            "reference": str(reference),
            "svg": str(svg),
            "preview": str(preview),
            "render_backend": render_result.backend,
            "render_meta": str(render_result.meta_path),
        }

    result = compare_images(
        reference,
        preview,
        mean_threshold=mean_threshold,
        layout_reference=layout,
        anchor_threshold=anchor_threshold,
    )
    result["project"] = str(project)
    result["svg"] = str(svg)
    result["preview"] = str(preview)
    _apply_render_result(result, render_result)
    return _attach_object_similarity(
        project,
        result,
        render=render,
        anchor_threshold=anchor_threshold,
        object_level=object_level,
        fail_on_local_diff=fail_on_local_diff,
        write_object_report=write_object_report,
    )


def _attach_object_similarity(
    project: Path,
    payload: dict[str, Any],
    *,
    render: bool,
    anchor_threshold: float,
    object_level: bool,
    fail_on_local_diff: bool,
    write_object_report: bool,
) -> dict[str, Any]:
    if not object_level:
        return payload
    try:
        from reference_object_similarity_lib import Thresholds, summarize_for_similarity, verify_project as verify_objects
    except ImportError:
        from scripts.reference_object_similarity_lib import (  # type: ignore
            Thresholds,
            summarize_for_similarity,
            verify_project as verify_objects,
        )
    object_payload = verify_objects(
        project,
        render=render,
        thresholds=Thresholds(anchor_drift_px=anchor_threshold),
        write_report=write_object_report,
    )
    payload["object_similarity"] = summarize_for_similarity(object_payload)
    if fail_on_local_diff and not object_payload.get("valid"):
        payload["valid"] = False
        for item in object_payload.get("errors", []):
            if isinstance(item, str):
                payload.setdefault("errors", []).append(item)
    return payload


def _verify_one(
    project: Path,
    *,
    layout_path: Path,
    reference: Path,
    svg: Path,
    render: bool,
    mean_threshold: float,
    anchor_threshold: float,
    render_backend: str = "cairo",
    hard_gate: bool = False,
    force_render: bool = False,
    server_url: str | None = None,
) -> dict[str, Any]:
    layout = _load_json(layout_path)
    preview = _preview_path(project, svg)
    render_result = _ensure_preview(
        project,
        svg,
        preview,
        render=render,
        render_backend=render_backend,
        hard_gate=hard_gate,
        force_render=force_render,
        server_url=server_url,
    )
    if not render_result.ok:
        return {
            "valid": False,
            "errors": list(render_result.errors),
            "warnings": list(render_result.warnings),
            "reference": str(reference),
            "svg": str(svg),
            "preview": str(preview),
            "render_backend": render_result.backend,
            "render_meta": str(render_result.meta_path),
        }
    quality_errors: list[str] = []
    quality_warnings: list[str] = list(render_result.warnings)
    _post_render_preview_checks(
        svg,
        preview,
        render_result.backend,
        errors=quality_errors,
        warnings=quality_warnings,
    )
    if quality_errors:
        return {
            "valid": False,
            "errors": quality_errors,
            "warnings": quality_warnings,
            "reference": str(reference),
            "svg": str(svg),
            "preview": str(preview),
            "render_backend": render_result.backend,
            "render_meta": str(render_result.meta_path),
        }
    result = compare_images(
        reference,
        preview,
        mean_threshold=mean_threshold,
        layout_reference=layout,
        anchor_threshold=anchor_threshold,
    )
    result["project"] = str(project)
    result["svg"] = str(svg)
    result["preview"] = str(preview)
    if quality_warnings:
        result.setdefault("warnings", []).extend(quality_warnings)
    _apply_render_result(result, render_result)
    return result


def verify_manifest_pages(
    project: Path,
    *,
    pages: list[Any],
    render: bool = False,
    mean_threshold: float = DEFAULT_MEAN_THRESHOLD,
    anchor_threshold: float = DEFAULT_ANCHOR_THRESHOLD,
    object_level: bool = False,
    fail_on_local_diff: bool = False,
    write_object_report: bool = False,
    render_backend: str = "cairo",
    hard_gate: bool = False,
    force_render: bool = False,
    server_url: str | None = None,
) -> dict[str, Any]:
    page_results: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    for page in pages:
        if not isinstance(page, dict):
            errors.append("Manifest page entry is not an object.")
            continue
        page_id = str(page.get("page_id", "")).strip()
        page_dir = _page_dir(project, page)
        reference = _resolve_path(project, page.get("reference_image")) or _find_reference_image(page_dir)
        if reference is None or not reference.is_file():
            page_result = {
                "valid": False,
                "page_id": page_id,
                "errors": [f"Reference image missing for page `{page_id}`."],
                "warnings": [],
            }
            page_results.append(page_result)
            errors.extend(page_result["errors"])
            continue
        layout_path = page_dir / "layout_reference.json"
        if not layout_path.is_file():
            layout_path = project / "layout_reference.json"
        svgs = list_page_svg_candidates(project, page_id, page_dir=page_dir)
        if not svgs:
            page_result = {
                "valid": False,
                "page_id": page_id,
                "reference": str(reference),
                "errors": [f"No SVG matching page `{page_id}` in svg_final/ or svg_output/."],
                "warnings": [],
            }
            page_results.append(page_result)
            errors.extend(page_result["errors"])
            continue
        page_result = _verify_one(
            page_dir if page_dir.is_dir() else project,
            layout_path=layout_path,
            reference=reference,
            svg=svgs[0],
            render=render,
            mean_threshold=mean_threshold,
            anchor_threshold=anchor_threshold,
            render_backend=render_backend,
            hard_gate=hard_gate,
            force_render=force_render,
            server_url=server_url,
        )
        page_result["page_id"] = page_id
        page_results.append(page_result)
        if not page_result.get("valid"):
            errors.extend(str(item) for item in page_result.get("errors", []))
        warnings.extend(str(item) for item in page_result.get("warnings", []))
    payload = {
        "valid": not errors,
        "project": str(project),
        "mode": "manifest_pages",
        "page_count": len(page_results),
        "errors": errors,
        "warnings": warnings,
        "pages": page_results,
    }
    return _attach_object_similarity(
        project,
        payload,
        render=render,
        anchor_threshold=anchor_threshold,
        object_level=object_level,
        fail_on_local_diff=fail_on_local_diff,
        write_object_report=write_object_report,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare slide preview PNG to layout reference image (复刻流程2 visual gate).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument(
        "--render",
        action="store_true",
        help="Render or validate preview PNG (required for --render-backend none)",
    )
    parser.add_argument(
        "--render-backend",
        choices=["auto", "cairo", "none"],
        default="cairo",
        help="Preview render backend (default: cairo; hard gates must not use auto)",
    )
    parser.add_argument(
        "--hard-gate",
        action="store_true",
        help="Reject --render-backend auto (for CI / pre-export)",
    )
    parser.add_argument("--force-render", action="store_true", help="Force preview re-render")
    parser.add_argument(
        "--server-url",
        help="(unused, kept for CLI compatibility)",
    )
    parser.add_argument("--svg", type=Path, help="Optional SVG path (default: first page in svg_final/svg_output)")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_MEAN_THRESHOLD,
        help=f"Max allowed mean |ref-preview| RGB diff (0-255, default {DEFAULT_MEAN_THRESHOLD})",
    )
    parser.add_argument(
        "--anchor-threshold",
        type=float,
        default=DEFAULT_ANCHOR_THRESHOLD,
        help=f"Max allowed visual anchor drift in pixels (default {DEFAULT_ANCHOR_THRESHOLD})",
    )
    parser.add_argument(
        "--object-level",
        action="store_true",
        help="Also run object-level similarity and attach object_similarity summary",
    )
    parser.add_argument(
        "--fail-on-local-diff",
        action="store_true",
        help="When used with --object-level, fail if any blocking object-level diff is found",
    )
    parser.add_argument(
        "--write-object-report",
        action="store_true",
        help="When used with --object-level, write exports/qa/object_similarity_report.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = verify_project(
        args.project_path.resolve(),
        render=args.render,
        mean_threshold=args.threshold,
        anchor_threshold=args.anchor_threshold,
        svg_path=args.svg,
        object_level=args.object_level,
        fail_on_local_diff=args.fail_on_local_diff,
        write_object_report=args.write_object_report,
        render_backend=args.render_backend,
        hard_gate=args.hard_gate,
        force_render=args.force_render,
        server_url=args.server_url,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
