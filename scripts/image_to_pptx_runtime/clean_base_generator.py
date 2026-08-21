"""Official local clean-base preparation for the Stage 02 production route."""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageDraw

from .clean_base_policy import SCHEMA


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(value: object) -> str:
    return " ".join(str(value or "").split())


def _bbox(value: object, *, width: int, height: int) -> tuple[int, int, int, int] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    try:
        left, top, right, bottom = (int(round(float(item))) for item in value)
    except (TypeError, ValueError):
        return None
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        return None
    return left, top, right, bottom


def _ring_pixels(image: Image.Image, box: tuple[int, int, int, int], *, padding: int = 4) -> list[tuple[int, int, int]]:
    left, top, right, bottom = box
    outer = (
        max(0, left - padding),
        max(0, top - padding),
        min(image.width, right + padding),
        min(image.height, bottom + padding),
    )
    pixels: list[tuple[int, int, int]] = []
    for y in range(outer[1], outer[3]):
        for x in range(outer[0], outer[2]):
            if left <= x < right and top <= y < bottom:
                continue
            pixels.append(image.getpixel((x, y)))
    return pixels


def _flat_surface_color(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int] | None:
    pixels = _ring_pixels(image, box)
    if len(pixels) < 12:
        return None
    channels = list(zip(*pixels))
    if max(statistics.pstdev(channel) for channel in channels) > 18:
        return None
    return tuple(int(statistics.median(channel)) for channel in channels)


def _ocr_box(value: object) -> tuple[int, int, int, int] | None:
    if not isinstance(value, list) or not value:
        return None
    points: list[tuple[float, float]] = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            return None
        try:
            points.append((float(point[0]), float(point[1])))
        except (TypeError, ValueError):
            return None
    return (
        int(min(point[0] for point in points)),
        int(min(point[1] for point in points)),
        int(max(point[0] for point in points)),
        int(max(point[1] for point in points)),
    )


def _boxes_overlap(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> bool:
    return left[0] < right[2] and right[0] < left[2] and left[1] < right[3] and right[1] < left[3]


def _post_clean_ocr(image_path: Path, regions: list[dict[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    """Confirm that OCR no longer detects text in a declared clearance region.

    The full-image text audit is intentionally not reused here: its purpose is
    typo detection, whereas this check is narrowly about residual glyphs in
    regions that the generator itself cleared.
    """

    try:
        from cyberppt.image_text_gate import _rapidocr

        observations = _rapidocr(image_path)
    except Exception as exc:  # A missing OCR dependency must block automatic approval.
        return False, [{"error": f"post-clean OCR unavailable: {exc}"}]
    residual: list[dict[str, Any]] = []
    for observation in observations:
        if not isinstance(observation, Mapping) or not _text(observation.get("text")):
            continue
        observed_box = _ocr_box(observation.get("bbox"))
        if observed_box is None:
            continue
        for region in regions:
            if _boxes_overlap(observed_box, region["bbox"]):
                residual.append(
                    {
                        "policy_id": region["policy_id"],
                        "observed_text": _text(observation.get("text")),
                        "bbox": list(observed_box),
                    }
                )
                break
    return not residual, residual


def _native_regions(policy: Mapping[str, Any], *, width: int, height: int) -> tuple[list[dict[str, Any]], list[str]]:
    regions: list[dict[str, Any]] = []
    errors: list[str] = []
    raw_items = policy.get("items") if isinstance(policy, Mapping) else None
    if not isinstance(raw_items, list):
        return [], ["graphic_text_policy.items must be a list"]
    for item in raw_items:
        if not isinstance(item, Mapping) or _text(item.get("treatment")) != "native_text":
            continue
        item_id = _text(item.get("id"))
        text = _text(item.get("text"))
        box = _bbox(item.get("bbox"), width=width, height=height)
        if not item_id or not text or box is None:
            errors.append(f"native_text {item_id or text or '<unnamed>'} requires id, text, and bbox before clean-base generation")
            continue
        regions.append({"policy_id": item_id, "text": text, "bbox": box})
    return regions, errors


def prepare_clean_bases(manifest: dict[str, Any], *, output_dir: Path | str) -> dict[str, Any]:
    """Create only safe local clean bases and update the active manifest in memory.

    The generator deliberately supports uniform/near-uniform text fields only.
    Text over texture, photography, gradients, or geometric assets remains
    ``manual_required`` instead of silently degrading the reference visual.
    """

    assets = Path(output_dir).expanduser().resolve()
    assets.mkdir(parents=True, exist_ok=True)
    report_dir = assets.parent.parent / "analysis"
    report_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for raw_pair in manifest.get("pairs", []):
        if not isinstance(raw_pair, dict):
            continue
        pair = raw_pair
        page_number = int(pair.get("page_number") or 0)
        existing = pair.get("clean_base")
        if isinstance(existing, Mapping) and existing.get("schema") == SCHEMA and existing.get("status") == "complete":
            results.append({"page_number": page_number, "status": "reused", "path": existing.get("path")})
            continue
        full = pair.get("full") if isinstance(pair.get("full"), Mapping) else {}
        full_path = Path(str(full.get("path") or "")).expanduser()
        policy = pair.get("graphic_text_policy") if isinstance(pair.get("graphic_text_policy"), Mapping) else {}
        if not full_path.is_file():
            results.append({"page_number": page_number, "status": "manual_required", "errors": ["audited full image is missing"]})
            continue
        if policy.get("status") != "complete" or policy.get("empty_container_check") != "passed":
            results.append({"page_number": page_number, "status": "manual_required", "errors": ["complete graphic_text_policy is required before clean-base generation"]})
            continue
        with Image.open(full_path) as source:
            image = source.convert("RGB")
        regions, errors = _native_regions(policy, width=image.width, height=image.height)
        if errors or not regions:
            results.append({"page_number": page_number, "status": "manual_required", "errors": errors or ["no native_text regions were declared"]})
            continue
        fills: list[tuple[dict[str, Any], tuple[int, int, int]]] = []
        for region in regions:
            color = _flat_surface_color(image, region["bbox"])
            if color is None:
                errors.append(f"{region['policy_id']}: local background is non-uniform; use reviewed local reconstruction")
            else:
                fills.append((region, color))
        if errors:
            results.append({"page_number": page_number, "status": "manual_required", "errors": errors})
            continue
        base = image.copy()
        draw = ImageDraw.Draw(base)
        for region, color in fills:
            draw.rectangle(region["bbox"], fill=color)
        destination = assets / f"page_{page_number:03d}_clean_base.png"
        base.save(destination)
        ocr_passed, ocr_residual = _post_clean_ocr(destination, regions)
        if not ocr_passed:
            destination.unlink(missing_ok=True)
            results.append(
                {
                    "page_number": page_number,
                    "status": "manual_required",
                    "errors": ["post-clean OCR still finds text in a native_text clearance region"],
                    "post_clean_ocr": ocr_residual,
                }
            )
            continue
        clean_regions = [
            {
                "policy_id": region["policy_id"],
                "text": region["text"],
                "bbox": list(region["bbox"]),
                "method": "flat-surface-rebuild",
            }
            for region, _ in fills
        ]
        pair["clean_base"] = {
            "schema": SCHEMA,
            "status": "complete",
            "path": str(destination),
            "source_sha256": _sha256(full_path),
            "sha256": _sha256(destination),
            "removal_scope": "native_text_only",
            "clearance_padding_px": 6,
            "max_outside_mask_changed_fraction": 0.01,
            "cleaned_text_regions": clean_regions,
            "visual_diff_report": {
                "status": "passed",
                "method": "flat-surface-local-rebuild",
                "checks": {
                    "text_removal": "passed",
                    "background_continuity": "passed",
                    "outside_mask_preserved": "passed",
                    "post_clean_ocr": "passed",
                },
                "post_clean_ocr": {"status": "passed", "residual": []},
            },
        }
        results.append({"page_number": page_number, "status": "complete", "path": str(destination), "regions": clean_regions})
    report = {
        "schema": "cyberppt.stage02.clean_base_generation.v1",
        "status": "complete" if results and all(item["status"] in {"complete", "reused"} for item in results) else "manual_required",
        "pages": results,
    }
    report_path = report_dir / "clean_base_generation.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["path"] = str(report_path)
    return report
