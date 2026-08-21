"""AI-authored native text inputs for the canonical Stage 02 production path.

The locked final script is the text truth.  OCR observations from the audited
full image are used only to locate that truth, then this module prepares the
``graphic_text_policy`` and an authored SVG that the existing clean-base and
Quick/PPTX gates consume.  It deliberately fails closed for unmatched readable
OCR rather than asking a user to classify it or silently leaving it baked into
the editable deliverable.
"""

from __future__ import annotations

from collections.abc import Mapping
from difflib import SequenceMatcher
from html import escape
import json
import math
import re
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from .graphic_text_policy import SCHEMA as POLICY_SCHEMA
from .native_text_style import DEFAULT_PROFILE, FONT_STACK


POLICY_REPORT_SCHEMA = "cyberppt.stage02.ai_native_text_policy.v1"
SVG_REPORT_SCHEMA = "cyberppt.stage02.ai_authored_svg.v1"
_PUNCTUATION_RE = re.compile(r"[\s，。！？：:、；;（）()【】\[\]‘’“”\"'·…—_-]+")
_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_DECORATIVE_RE = re.compile(r"^[^\w\u3400-\u9fff]+$")


def _text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _compact(value: object) -> str:
    return _PUNCTUATION_RE.sub("", _text(value))


def _ocr_bbox(value: object) -> tuple[float, float, float, float] | None:
    if not isinstance(value, list) or not value:
        return None
    try:
        if len(value) == 4 and all(isinstance(item, (int, float)) for item in value):
            left, top, right, bottom = (float(item) for item in value)
        else:
            points = [item for item in value if isinstance(item, list) and len(item) >= 2]
            if not points:
                return None
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in (left, top, right, bottom)) or left >= right or top >= bottom:
        return None
    return left, top, right, bottom


def _axis_bbox(boxes: list[tuple[float, float, float, float]]) -> list[int]:
    return [
        int(math.floor(min(box[0] for box in boxes))),
        int(math.floor(min(box[1] for box in boxes))),
        int(math.ceil(max(box[2] for box in boxes))),
        int(math.ceil(max(box[3] for box in boxes))),
    ]


def _visible_text(pair: Mapping[str, Any]) -> list[str]:
    full = pair.get("full") if isinstance(pair.get("full"), Mapping) else {}
    receipt = full.get("debug_receipt") if isinstance(full.get("debug_receipt"), Mapping) else {}
    values = receipt.get("visible_text") if isinstance(receipt.get("visible_text"), list) else []
    text = [_text(value) for value in values if _text(value)]
    if text:
        return list(dict.fromkeys(text))
    truth = pair.get("image_text_truth") if isinstance(pair.get("image_text_truth"), Mapping) else {}
    return list(dict.fromkeys(_text(value) for value in str(truth.get("script_text") or "").splitlines() if _text(value)))


def _observations(pair: Mapping[str, Any]) -> list[dict[str, Any]]:
    full = pair.get("full") if isinstance(pair.get("full"), Mapping) else {}
    audit = full.get("text_audit") if isinstance(full.get("text_audit"), Mapping) else {}
    raw_items = audit.get("ocr_items") if isinstance(audit.get("ocr_items"), list) else []
    if not raw_items:
        path = Path(str(full.get("path") or "")).expanduser()
        if path.is_file():
            try:
                from cyberppt.image_text_gate import _rapidocr

                raw_items = _rapidocr(path)
            except Exception:
                raw_items = []
    scale_x, scale_y = _ocr_scale(pair)
    values: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, Mapping):
            continue
        text = _text(item.get("text", item.get("content")))
        bbox = _ocr_bbox(item.get("bbox"))
        confidence = item.get("confidence")
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        if text and bbox is not None:
            bbox = (
                bbox[0] * scale_x,
                bbox[1] * scale_y,
                bbox[2] * scale_x,
                bbox[3] * scale_y,
            )
            values.append({"index": index, "text": text, "compact": _compact(text), "bbox": bbox, "confidence": confidence})
    return values


def _complete_policy_has_native_bboxes(value: Mapping[str, Any]) -> bool:
    if value.get("status") != "complete" or not isinstance(value.get("items"), list):
        return False
    native = [item for item in value["items"] if isinstance(item, Mapping) and item.get("treatment") == "native_text"]
    return bool(native) and all(
        item.get("source_visible") is False or _ocr_bbox(item.get("bbox")) is not None
        for item in native
    )


def _ocr_scale(pair: Mapping[str, Any]) -> tuple[float, float]:
    """Map OCR logical-canvas coordinates to the enhanced image pixel canvas."""

    full = pair.get("full") if isinstance(pair.get("full"), Mapping) else {}
    path = Path(str(full.get("path") or "")).expanduser()
    canvas = str(full.get("canvas") or "")
    match = re.fullmatch(r"\s*(\d+)x(\d+)\s*", canvas)
    if not path.is_file() or match is None:
        return 1.0, 1.0
    logical_width, logical_height = (float(match.group(1)), float(match.group(2)))
    if logical_width <= 0 or logical_height <= 0:
        return 1.0, 1.0
    with Image.open(path) as image:
        return image.width / logical_width, image.height / logical_height


def _fragment_match(expected: str, observed: str) -> tuple[float, int, int] | None:
    """Return a conservative expected-span alignment for one OCR fragment."""

    if not expected or not observed:
        return None
    exact = expected.find(observed)
    if exact >= 0:
        return 1.0, exact, exact + len(observed)
    best_score, best_start, best_end = 0.0, 0, 0
    low = max(1, len(observed) - 3)
    high = min(len(expected), len(observed) + 3)
    for size in range(low, high + 1):
        for start in range(0, len(expected) - size + 1):
            score = SequenceMatcher(None, observed, expected[start : start + size]).ratio()
            if score > best_score:
                best_score, best_start, best_end = score, start, start + size
    minimum = 0.82 if len(observed) >= 4 else 1.0
    return (best_score, best_start, best_end) if best_score >= minimum else None


def _locate_truth(expected_text: str, observations: list[dict[str, Any]], used: set[int]) -> dict[str, Any] | None:
    expected = _compact(expected_text)
    if not expected:
        return None
    fragments: list[tuple[float, int, int, dict[str, Any]]] = []
    for observation in observations:
        if int(observation["index"]) in used:
            continue
        matched = _fragment_match(expected, str(observation["compact"]))
        if matched is not None:
            score, start, end = matched
            fragments.append((score, start, end, observation))
    if not fragments:
        return None
    selected: list[tuple[float, int, int, dict[str, Any]]] = []
    covered: list[tuple[int, int]] = []
    for candidate in sorted(fragments, key=lambda item: (item[0], item[2] - item[1], item[3]["confidence"]), reverse=True):
        _, start, end, observation = candidate
        overlap = any(not (end <= left or start >= right) for left, right in covered)
        if overlap:
            continue
        selected.append(candidate)
        covered.append((start, end))
    selected.sort(key=lambda item: (item[1], item[3]["bbox"][1], item[3]["bbox"][0]))
    coverage = sum(end - start for _, start, end, _ in selected) / len(expected)
    observed_joined = "".join(str(item[3]["compact"]) for item in selected)
    similarity = SequenceMatcher(None, expected, observed_joined).ratio()
    if coverage < 0.68 or similarity < 0.68:
        return None
    for _, _, _, observation in selected:
        used.add(int(observation["index"]))
    lines = [
        {
            "text": item[3]["text"],
            "bbox": list(item[3]["bbox"]),
            "confidence": item[3]["confidence"],
        }
        for item in sorted(selected, key=lambda item: (item[3]["bbox"][1], item[3]["bbox"][0]))
    ]
    boxes = [tuple(line["bbox"]) for line in lines]
    return {"bbox": _axis_bbox(boxes), "lines": lines, "coverage": coverage, "similarity": similarity}


def _decorative_observation(observation: Mapping[str, Any]) -> bool:
    text = _text(observation.get("text"))
    return bool(
        _DECORATIVE_RE.fullmatch(text)
        or (len(text) == 1 and not _CJK_RE.search(text) and float(observation.get("confidence") or 0) < 0.85)
    )


def _injected_locator(text: str, observations: list[dict[str, Any]], *, width: int, height: int) -> dict[str, Any] | None:
    """Place an omitted section title in the unused page-top safe zone.

    This preserves locked source copy without pretending that an absent glyph
    was removed from the generated image.  Other missing body text remains a
    hard automatic failure because it has no safe generic placement.
    """

    if not text.startswith("【") or not text.endswith("】"):
        return None
    first_top = min((float(item["bbox"][1]) for item in observations), default=height * 0.18)
    top = max(12.0, min(height * 0.055, first_top * 0.28))
    text_height = max(22.0, min(height * 0.045, first_top - top - 10.0))
    left = width * 0.04
    right = min(width * 0.45, left + max(text_height * len(_compact(text)) * 1.05, width * 0.16))
    box = [int(round(left)), int(round(top)), int(round(right)), int(round(top + text_height))]
    return {
        "bbox": box,
        "lines": [{"text": text, "bbox": box, "confidence": None}],
        "coverage": 1.0,
        "similarity": 1.0,
        "source_visible": False,
        "locator_source": "ai_injected_safe_zone",
    }


def prepare_ai_graphic_text_policy(
    manifest: dict[str, Any],
    *,
    output_dir: Path | str,
    write_report: bool = True,
) -> dict[str, Any]:
    """Complete missing policies from locked text truth plus audited OCR boxes."""

    report_dir = Path(output_dir).expanduser().resolve() / "analysis"
    report_dir.mkdir(parents=True, exist_ok=True)
    pages: list[dict[str, Any]] = []
    for pair in manifest.get("pairs", []):
        if not isinstance(pair, dict):
            continue
        page_number = int(pair.get("page_number") or 0)
        existing = pair.get("graphic_text_policy")
        if isinstance(existing, Mapping) and _complete_policy_has_native_bboxes(existing):
            pages.append({"page_number": page_number, "status": "reused", "item_count": len(existing.get("items", []))})
            continue
        observations = _observations(pair)
        used: set[int] = set()
        located: list[dict[str, Any]] = []
        missing: list[str] = []
        full = pair.get("full") if isinstance(pair.get("full"), Mapping) else {}
        full_path = Path(str(full.get("path") or "")).expanduser()
        with Image.open(full_path) as image:
            image_size = image.size
        for text in sorted(_visible_text(pair), key=lambda value: len(_compact(value)), reverse=True):
            locator = _locate_truth(text, observations, used)
            if locator is None:
                locator = _injected_locator(text, observations, width=image_size[0], height=image_size[1])
            if locator is None:
                missing.append(text)
                continue
            located.append({"text": text, **locator})
        unknown = [item for item in observations if int(item["index"]) not in used and not _decorative_observation(item)]
        if missing or unknown:
            pair["graphic_text_policy"] = {
                "schema": POLICY_SCHEMA,
                "page_number": page_number,
                "status": "auto_failed",
                "empty_container_check": "failed",
                "items": [],
                "note": "AI native-text authoring could not bind every readable observation to locked text truth.",
            }
            pages.append(
                {
                    "page_number": page_number,
                    "status": "auto_failed",
                    "missing_script_text": missing,
                    "unbound_ocr": [{"text": item["text"], "bbox": list(item["bbox"])} for item in unknown],
                }
            )
            continue
        items: list[dict[str, Any]] = []
        for index, item in enumerate(located, start=1):
            items.append(
                {
                    "id": f"text-{index:03d}",
                    "text": item["text"],
                    "treatment": "native_text",
                    "bbox": item["bbox"],
                    "layout_lines": item["lines"],
                    "source_visible": item.get("source_visible", True),
                    "locator": {
                        "source": item.get("locator_source", "ai_ocr_script_alignment"),
                        "coverage": round(float(item["coverage"]), 4),
                        "similarity": round(float(item["similarity"]), 4),
                    },
                }
            )
        for observation in observations:
            if int(observation["index"]) in used:
                continue
            if _decorative_observation(observation):
                items.append(
                    {
                        "id": f"glyph-{len(items) + 1:03d}",
                        "treatment": "decorative_glyph",
                        "observed_text": observation["text"],
                        "bbox": _axis_bbox([tuple(observation["bbox"])]),
                        "visual_review": {"status": "passed", "classification": "non_semantic_glyph", "source": "ai_low_risk_ocr_classification"},
                    }
                )
        pair["graphic_text_policy"] = {
            "schema": POLICY_SCHEMA,
            "page_number": page_number,
            "status": "complete",
            "empty_container_check": "passed",
            "unresolved_empty_containers": [],
            "author": "stage02_ai_native_text_authoring",
            "items": items,
        }
        pages.append({"page_number": page_number, "status": "complete", "item_count": len(items), "native_text_count": len(located)})
    status = "complete" if all(page.get("status") in {"complete", "reused"} for page in pages) else "auto_failed"
    report = {"schema": POLICY_REPORT_SCHEMA, "status": status, "pages": pages}
    if write_report:
        path = report_dir / "ai_native_text_policy.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["path"] = str(path)
    return report


def _glyph_units(text: str) -> float:
    """Approximate Microsoft YaHei advance units without reflowing the text.

    CJK glyphs are close to one em, while punctuation and ASCII consume less.
    This deliberately gives a conservative width fit; the OCR box describes
    painted glyphs, not a PowerPoint text-frame rectangle.
    """

    units = 0.0
    for character in _text(text):
        if _CJK_RE.fullmatch(character):
            units += 1.0
        elif character.isspace():
            units += 0.30
        elif character in "，。！？：:、；;（）()【】[]“”‘’\"'·…—_-":
            units += 0.50
        else:
            units += 0.58
    return max(1.0, units)


def _line_bbox(line: Mapping[str, Any], fallback_bbox: list[int]) -> tuple[float, float, float, float]:
    raw = line.get("bbox")
    if isinstance(raw, list) and len(raw) == 4:
        try:
            left, top, right, bottom = (float(value) for value in raw)
            if left < right and top < bottom:
                return left, top, right, bottom
        except (TypeError, ValueError):
            pass
    return tuple(float(value) for value in fallback_bbox)  # type: ignore[return-value]


def _font_size(lines: list[Mapping[str, Any]], line_texts: list[str], fallback_bbox: list[int]) -> float:
    """Fit one native font size inside every observed visual line.

    The previous ``bbox_height * 0.9`` rule made compact labels visibly too
    large.  Using both height and width keeps a four-character label inside
    its OCR field and leaves long body lines at their captured line breaks.
    """

    candidates: list[float] = []
    for line, text in zip(lines, line_texts):
        left, top, right, bottom = _line_bbox(line, fallback_bbox)
        vertical_limit = (bottom - top) * 0.72
        horizontal_limit = (right - left) / _glyph_units(text)
        candidates.append(min(vertical_limit, horizontal_limit))
    if not candidates:
        left, top, right, bottom = (float(value) for value in fallback_bbox)
        candidates.append(min((bottom - top) * 0.72, (right - left) / _glyph_units("文")))
    return max(12.0, round(min(candidates), 2))


def _line_texts(text: str, lines: list[Mapping[str, Any]]) -> list[str]:
    if len(lines) <= 1:
        return [text]
    weights = [max(1, len(_compact(line.get("text")))) for line in lines]
    total = sum(weights)
    values: list[str] = []
    cursor = 0
    for index, weight in enumerate(weights):
        if index == len(weights) - 1:
            values.append(text[cursor:])
        else:
            count = max(1, round(len(text) * weight / total))
            values.append(text[cursor : cursor + count])
            cursor += count
    return values


def _line_tspan(*, content: str, x: float, baseline: float, first: bool) -> str:
    """Preserve a label's visual emphasis while anchoring each OCR line."""

    position = f'x="{x:.2f}" y="{baseline:.2f}"'
    label, separator, remainder = content.partition("：")
    if separator and label and len(_compact(label)) <= 12:
        prefix = escape(label + separator)
        suffix = escape(remainder)
        return (
            f'<tspan {position} fill="#12355B" font-weight="700">{prefix}</tspan>'
            f'<tspan fill="#202020" font-weight="400">{suffix}</tspan>'
        )
    if first:
        return f'<tspan {position}>{escape(content)}</tspan>'
    return f'<tspan {position}>{escape(content)}</tspan>'


def prepare_ai_authored_svgs(
    manifest: dict[str, Any],
    *,
    output_dir: Path | str,
    write_report: bool = True,
) -> dict[str, Any]:
    """Write the AI-authored SVGs after clean-base preparation succeeds."""

    authoring = Path(output_dir).expanduser().resolve()
    authoring.mkdir(parents=True, exist_ok=True)
    report_dir = authoring.parent / "analysis"
    report_dir.mkdir(parents=True, exist_ok=True)
    pages: list[dict[str, Any]] = []
    for pair in manifest.get("pairs", []):
        if not isinstance(pair, dict):
            continue
        page_number = int(pair.get("page_number") or 0)
        policy = pair.get("graphic_text_policy") if isinstance(pair.get("graphic_text_policy"), Mapping) else {}
        clean = pair.get("clean_base") if isinstance(pair.get("clean_base"), Mapping) else {}
        full = pair.get("full") if isinstance(pair.get("full"), Mapping) else {}
        full_path = Path(str(full.get("path") or "")).expanduser()
        clean_path = Path(str(clean.get("path") or "")).expanduser()
        items = [item for item in policy.get("items", []) if isinstance(item, Mapping) and item.get("treatment") == "native_text"] if isinstance(policy.get("items"), list) else []
        if policy.get("status") != "complete" or clean.get("status") != "complete" or not full_path.is_file() or not clean_path.is_file() or not items:
            pages.append({"page_number": page_number, "status": "auto_failed", "error": "complete policy, clean base, full image, and native text items are required"})
            continue
        with Image.open(full_path) as image:
            width, height = image.size
        svg_path = authoring / f"page_{page_number:03d}.svg"
        try:
            href = clean_path.resolve().relative_to(svg_path.parent.resolve()).as_posix()
        except ValueError:
            href = clean_path.resolve().as_uri()
        pieces = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" data-reconstruction-schema="v1" data-cyberppt-author="ai" data-cyberppt-native-text-style="{DEFAULT_PROFILE}">',
            f'<image id="clean-base" href="{escape(href, quote=True)}" x="0" y="0" width="{width}" height="{height}" preserveAspectRatio="none"/>',
        ]
        for item in items:
            text = _text(item.get("text"))
            box = item.get("bbox")
            lines = [dict(line) for line in item.get("layout_lines", []) if isinstance(line, Mapping)] if isinstance(item.get("layout_lines"), list) else []
            if not text or not isinstance(box, list) or len(box) != 4:
                raise ValueError(f"invalid AI native text item {item.get('id')}")
            if not lines:
                lines = [{"text": text, "bbox": box}]
            line_texts = _line_texts(text, lines)
            size = _font_size(lines, line_texts, box)
            first_left, first_top, _, _ = _line_bbox(lines[0], box)
            x = first_left
            baseline = first_top + size * 0.78
            heading = len(_compact(text)) <= 12 or text.startswith("【")
            text_parts = [
                f'<text id="native-{escape(str(item.get("id")), quote=True)}" data-cyberppt-text-id="{escape(str(item.get("id")), quote=True)}" data-truth-source="script" x="{x:.2f}" y="{baseline:.2f}" font-family="{FONT_STACK}" font-size="{size:.2f}" font-weight="{"700" if heading else "400"}" fill="{"#12355B" if heading else "#202020"}">'
            ]
            for index, (line, content) in enumerate(zip(lines, line_texts)):
                line_left, line_top, _, _ = _line_bbox(line, box)
                text_parts.append(
                    _line_tspan(
                        content=content,
                        x=line_left,
                        baseline=line_top + size * 0.78,
                        first=index == 0,
                    )
                )
            text_parts.append("</text>")
            pieces.append("".join(text_parts))
        pieces.append("</svg>")
        svg_path.write_text("\n".join(pieces) + "\n", encoding="utf-8")
        pair["authoring_svg"] = str(svg_path)
        pair["authoring_svg_author"] = "ai"
        pair["native_text_style_profile"] = DEFAULT_PROFILE
        pages.append({"page_number": page_number, "status": "complete", "path": str(svg_path), "native_text_count": len(items)})
    status = "complete" if all(page.get("status") == "complete" for page in pages) else "auto_failed"
    report = {"schema": SVG_REPORT_SCHEMA, "status": status, "pages": pages}
    if write_report:
        path = report_dir / "ai_authored_svg.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["path"] = str(path)
    return report


def compile_ai_editable_pages(
    manifest: dict[str, Any],
    *,
    output_dir: Path | str,
    checkpoint: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Compile each page's policy, clean base, and SVG in one resumable pass.

    The public wrappers remain available for focused work and compatibility.
    Production uses this compiler so a page reaches its authored-SVG checkpoint
    before the next page is inspected, rather than making three batch-wide
    passes and emitting three overlapping diagnostic files.
    """

    from .clean_base_generator import prepare_clean_bases

    authoring = Path(output_dir).expanduser().resolve()
    authoring.mkdir(parents=True, exist_ok=True)
    pages: list[dict[str, Any]] = []
    policy_pages: list[dict[str, Any]] = []
    clean_pages: list[dict[str, Any]] = []
    svg_pages: list[dict[str, Any]] = []
    for raw_pair in manifest.get("pairs", []):
        if not isinstance(raw_pair, dict):
            continue
        pair = raw_pair
        page_number = int(pair.get("page_number") or 0)
        page_manifest = {"pairs": [pair]}
        policy = prepare_ai_graphic_text_policy(page_manifest, output_dir=authoring, write_report=False)
        policy_page = dict(policy.get("pages", [{}])[0])
        policy_pages.append(policy_page)
        page_report: dict[str, Any] = {"page_number": page_number, "policy": policy_page}
        if policy_page.get("status") not in {"complete", "reused"}:
            page_report["status"] = "auto_failed"
            pages.append(page_report)
            if checkpoint:
                checkpoint()
            continue
        clean = prepare_clean_bases(page_manifest, output_dir=authoring / "assets", write_report=False)
        clean_page = dict(clean.get("pages", [{}])[0])
        clean_pages.append(clean_page)
        page_report["clean_base"] = clean_page
        if clean_page.get("status") not in {"complete", "reused", "reused_seeded_baseline"}:
            page_report["status"] = "auto_failed"
            pages.append(page_report)
            if checkpoint:
                checkpoint()
            continue
        authored = prepare_ai_authored_svgs(page_manifest, output_dir=authoring, write_report=False)
        svg_page = dict(authored.get("pages", [{}])[0])
        svg_pages.append(svg_page)
        page_report["authored_svg"] = svg_page
        page_report["status"] = "complete" if svg_page.get("status") == "complete" else "auto_failed"
        pages.append(page_report)
        if checkpoint:
            checkpoint()
    status = "complete" if pages and all(page.get("status") == "complete" for page in pages) else "auto_failed"
    report = {
        "schema": "cyberppt.stage02.editable_page_compilation.v1",
        "status": status,
        "pages": pages,
        "policy": {"schema": POLICY_REPORT_SCHEMA, "status": status, "pages": policy_pages},
        "clean_base": {"schema": "cyberppt.stage02.clean_base_generation.v1", "status": status, "pages": clean_pages},
        "authored_svg": {"schema": SVG_REPORT_SCHEMA, "status": status, "pages": svg_pages},
    }
    report_dir = authoring.parent / "analysis"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "editable_page_compilation.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["path"] = str(path)
    for key in ("policy", "clean_base", "authored_svg"):
        report[key]["path"] = str(path)
    return report
