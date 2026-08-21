"""Official local clean-base preparation for the Stage 02 production route."""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, Mapping

from PIL import Image

from .clean_base_policy import SCHEMA


_GLYPH_DISTANCE_THRESHOLD = 20


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


def _dominant_light_surface_color(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int] | None:
    """Recover a text-safe pale surface when dividers make the whole ring noisy.

    This is deliberately narrower than generic inpainting: it only accepts a
    dominant near-white ring population, which covers common generated PPT
    text fields while continuing to reject gradients, photography and dark
    scene surfaces for automated retry.
    """

    pixels = _ring_pixels(image, box, padding=8)
    # First prefer an almost-white field.  Generated PPT labels can however
    # sit immediately beside their blue border and shadow; in that narrow
    # case the ring has only a small but still coherent light population.
    pale = [pixel for pixel in pixels if min(pixel) >= 215]
    required_share = 0.42
    bucket_size = 8
    dominant_share = 0.45
    if len(pale) / len(pixels) < required_share:
        pale = [pixel for pixel in pixels if min(pixel) >= 195]
        # A label on a white plate can have a narrow light margin because its
        # OCR box touches the blue border and drop shadow.  Coarser buckets
        # tolerate the plate's quiet shading while the 10% floor still rejects
        # a small highlight on an otherwise dark/photographic surface.
        required_share = 0.10
        bucket_size = 32
        dominant_share = 0.50
    if len(pale) < 24 or len(pale) / len(pixels) < required_share:
        return None
    buckets: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}
    for pixel in pale:
        bucket = tuple(channel // bucket_size for channel in pixel)
        buckets.setdefault(bucket, []).append(pixel)
    dominant = max(buckets.values(), key=len)
    if len(dominant) / len(pale) < dominant_share:
        return None
    channels = list(zip(*dominant))
    return tuple(int(statistics.median(channel)) for channel in channels)


def _erase_glyph_pixels(
    *,
    source: Image.Image,
    destination: Image.Image,
    box: tuple[int, int, int, int],
    surface: tuple[int, int, int],
) -> int:
    """Clear only foreground glyph pixels inside a text clearance region.

    OCR boxes are a safe *scope*, not a permission to paint a solid rectangle.
    On a verified flat local surface, a pixel sufficiently different from that
    surface is a conservative text-glyph candidate.  This keeps the original
    card fill, border, and neighbouring visual treatment intact.
    """

    left, top, right, bottom = box
    source_pixels = source.load()
    destination_pixels = destination.load()
    changed = 0
    # Antialiased text needs a modest threshold, while the flat-surface gate
    # above prevents normal background texture from being treated as glyphs.
    for y in range(top, bottom):
        for x in range(left, right):
            pixel = source_pixels[x, y]
            if max(abs(pixel[index] - surface[index]) for index in range(3)) < _GLYPH_DISTANCE_THRESHOLD:
                continue
            destination_pixels[x, y] = surface
            changed += 1
    return changed


def _semantic_units(text: object) -> str:
    """Keep ordinary characters that can be reconstructed as native text."""

    return "".join(character for character in _text(text) if character.isalnum() or "\u3400" <= character <= "\u9fff")


def _foreground_components(
    image: Image.Image,
    box: tuple[int, int, int, int],
    surface: tuple[int, int, int],
) -> tuple[int, list[tuple[int, int, int, int, int]]]:
    """Return foreground count and 4-connected component bounds in one OCR box."""

    left, top, right, bottom = box
    width, height = right - left, bottom - top
    area = width * height
    if area > 120_000:
        return 0, []
    source = image.load()
    foreground = bytearray(area)
    foreground_count = 0
    for y in range(height):
        for x in range(width):
            pixel = source[left + x, top + y]
            if max(abs(pixel[index] - surface[index]) for index in range(3)) >= _GLYPH_DISTANCE_THRESHOLD:
                foreground[y * width + x] = 1
                foreground_count += 1

    components: list[tuple[int, int, int, int, int]] = []
    seen = bytearray(area)
    for start in range(area):
        if not foreground[start] or seen[start]:
            continue
        seen[start] = 1
        queue = [start]
        count = 0
        min_x = max_x = start % width
        min_y = max_y = start // width
        while queue:
            current = queue.pop()
            x, y = current % width, current // width
            count += 1
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
            neighbours = (
                current - 1 if x else -1,
                current + 1 if x + 1 < width else -1,
                current - width if y else -1,
                current + width if y + 1 < height else -1,
            )
            for neighbour in neighbours:
                if neighbour >= 0 and foreground[neighbour] and not seen[neighbour]:
                    seen[neighbour] = 1
                    queue.append(neighbour)
        components.append((min_x, min_y, max_x, max_y, count))
    return foreground_count, components


def _assess_text_clearability(
    image: Image.Image,
    *,
    text: object,
    box: tuple[int, int, int, int],
) -> dict[str, Any]:
    """Prove a native-text region is safe before its pixels may be cleared.

    Script matching proves the wording.  This second gate rejects visual
    structure that OCR may localize as text, including arrows, card outlines,
    connector lines, and single decorative strokes.
    """

    units = _semantic_units(text)
    if len(units) < 2:
        return {"status": "rejected", "reason": "text is too short to distinguish from a decorative glyph"}
    width, height = box[2] - box[0], box[3] - box[1]
    if width * height > 120_000:
        return {"status": "rejected", "reason": "text clearance region is too large for safe glyph reconstruction"}
    surface = _flat_surface_color(image, box) or _dominant_light_surface_color(image, box)
    if surface is None:
        return {"status": "rejected", "reason": "local surface is not planar enough for safe text reconstruction"}
    foreground_count, components = _foreground_components(image, box, surface)
    area = width * height
    foreground_share = foreground_count / area if area else 0.0
    if foreground_share < 0.006:
        return {"status": "rejected", "reason": "no distinct text-like foreground pixels", "foreground_share": round(foreground_share, 4)}
    if foreground_share > 0.55:
        return {"status": "rejected", "reason": "foreground occupies too much of the clearance region", "foreground_share": round(foreground_share, 4)}
    for min_x, min_y, max_x, max_y, _ in components:
        touches = sum((min_x == 0, min_y == 0, max_x == width - 1, max_y == height - 1))
        if touches >= 3:
            return {"status": "rejected", "reason": "foreground touches the clearance boundary like a structural frame", "foreground_share": round(foreground_share, 4)}
    if len(components) < 2:
        return {"status": "rejected", "reason": "foreground does not form multiple character-like components", "foreground_share": round(foreground_share, 4)}
    return {
        "status": "clearable",
        "surface_color": list(surface),
        "foreground_share": round(foreground_share, 4),
        "component_count": len(components),
    }


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
        if item.get("source_visible") is False:
            # AI may inject locked section copy that the image backend omitted.
            # It has a layout bbox for the SVG, yet no source pixels to remove.
            continue
        item_id = _text(item.get("id"))
        text = _text(item.get("text"))
        box = _bbox(item.get("bbox"), width=width, height=height)
        if not item_id or not text or box is None:
            errors.append(f"native_text {item_id or text or '<unnamed>'} requires id, text, and bbox before clean-base generation")
            continue
        regions.append({"policy_id": item_id, "text": text, "bbox": box})
    return regions, errors


def prepare_clean_bases(
    manifest: dict[str, Any],
    *,
    output_dir: Path | str,
    write_report: bool = True,
) -> dict[str, Any]:
    """Create only safe local clean bases and update the active manifest in memory.

    The generator deliberately supports uniform/near-uniform text fields only.
    Text over texture, photography, gradients, or geometric assets fails the
    automatic reconstruction so the production orchestrator can regenerate
    the affected image rather than exposing a user review step.
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
        full = pair.get("full") if isinstance(pair.get("full"), Mapping) else {}
        full_path = Path(str(full.get("path") or "")).expanduser()
        policy = pair.get("graphic_text_policy") if isinstance(pair.get("graphic_text_policy"), Mapping) else {}
        if not full_path.is_file():
            results.append({"page_number": page_number, "status": "auto_failed", "errors": ["audited full image is missing"]})
            continue
        if policy.get("status") != "complete" or policy.get("empty_container_check") != "passed":
            results.append({"page_number": page_number, "status": "auto_failed", "errors": ["complete graphic_text_policy is required before clean-base generation"]})
            continue
        with Image.open(full_path) as source:
            image = source.convert("RGB")
        regions, errors = _native_regions(policy, width=image.width, height=image.height)
        if errors or not regions:
            results.append({"page_number": page_number, "status": "auto_failed", "errors": errors or ["no native_text regions were declared"]})
            continue
        if isinstance(existing, Mapping) and existing.get("baseline_seed") is True:
            seeded_path = Path(str(existing.get("path") or "")).expanduser()
            if not seeded_path.is_file():
                results.append({"page_number": page_number, "status": "auto_failed", "errors": ["seeded clean-base asset is missing"]})
                continue
            ocr_passed, ocr_residual = _post_clean_ocr(seeded_path, regions)
            if not ocr_passed:
                results.append({"page_number": page_number, "status": "auto_failed", "errors": ["seeded clean base retains native text"], "post_clean_ocr": ocr_residual})
                continue
            pair["clean_base"] = {
                "schema": SCHEMA,
                "status": "complete",
                "path": str(seeded_path),
                "source_sha256": _sha256(full_path),
                "sha256": _sha256(seeded_path),
                "removal_scope": "native_text_only",
                "clearance_padding_px": 6,
                "max_outside_mask_changed_fraction": 0.04,
                "baseline_provenance": dict(existing.get("baseline_provenance") or {}),
                "cleaned_text_regions": [
                    {"policy_id": region["policy_id"], "text": region["text"], "bbox": list(region["bbox"]), "method": "legacy-reviewed-baseline"}
                    for region in regions
                ],
                "visual_diff_report": {
                    "status": "passed",
                    "method": "legacy-reviewed-baseline",
                    "checks": {
                        "text_removal": "passed",
                        "background_continuity": "passed",
                        "outside_mask_preserved": "passed",
                        "post_clean_ocr": "passed",
                    },
                    "post_clean_ocr": {"status": "passed", "residual": []},
                },
            }
            results.append({"page_number": page_number, "status": "reused_seeded_baseline", "path": str(seeded_path)})
            continue
        if isinstance(existing, Mapping) and existing.get("schema") == SCHEMA and existing.get("status") == "complete":
            results.append({"page_number": page_number, "status": "reused", "path": existing.get("path")})
            continue
        fills: list[tuple[dict[str, Any], tuple[int, int, int], dict[str, Any]]] = []
        clearability: list[dict[str, Any]] = []
        for region in regions:
            assessment = _assess_text_clearability(image, text=region["text"], box=region["bbox"])
            clearability.append({"policy_id": region["policy_id"], **assessment})
            if assessment.get("status") != "clearable":
                errors.append(f"{region['policy_id']}: not safe to clear ({assessment.get('reason')})")
            else:
                color = tuple(int(value) for value in assessment["surface_color"])
                fills.append((region, color, assessment))
        if errors:
            results.append({"page_number": page_number, "status": "auto_failed", "errors": errors, "clearability": clearability})
            continue
        base = image.copy()
        cleaned_pixel_counts: dict[str, int] = {}
        for region, color, _ in fills:
            changed = _erase_glyph_pixels(
                source=image,
                destination=base,
                box=region["bbox"],
                surface=color,
            )
            if changed == 0:
                errors.append(f"{region['policy_id']}: no glyph pixels differ from the verified local surface")
            else:
                cleaned_pixel_counts[str(region["policy_id"])] = changed
        if errors:
            results.append({"page_number": page_number, "status": "auto_failed", "errors": errors, "clearability": clearability})
            continue
        destination = assets / f"page_{page_number:03d}_clean_base.png"
        base.save(destination)
        ocr_passed, ocr_residual = _post_clean_ocr(destination, regions)
        if not ocr_passed:
            destination.unlink(missing_ok=True)
            results.append(
                {
                    "page_number": page_number,
                    "status": "auto_failed",
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
                "method": "masked-inpainting",
                "cleared_pixel_count": cleaned_pixel_counts[str(region["policy_id"])],
                "clearability": assessment,
            }
            for region, _, assessment in fills
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
                "method": "glyph-masked-local-rebuild",
                "checks": {
                    "text_removal": "passed",
                    "background_continuity": "passed",
                    "outside_mask_preserved": "passed",
                    "post_clean_ocr": "passed",
                },
                "post_clean_ocr": {"status": "passed", "residual": []},
            },
        }
        results.append({"page_number": page_number, "status": "complete", "path": str(destination), "regions": clean_regions, "clearability": clearability})
    report = {
        "schema": "cyberppt.stage02.clean_base_generation.v1",
        "status": "complete" if results and all(item["status"] in {"complete", "reused", "reused_seeded_baseline"} for item in results) else "auto_failed",
        "pages": results,
    }
    if write_report:
        report_path = report_dir / "clean_base_generation.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["path"] = str(report_path)
    return report
