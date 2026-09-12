"""Pre-enhancement glyph and fidelity-text gate for generated PPT images."""

from __future__ import annotations

import json
import re
import tempfile
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable

from PIL import Image


def _parse_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
    if fenced:
        raw = fenced.group(1)
    else:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("image text audit must return a JSON object")
    return payload


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _rapidocr(image_path: Path) -> list[dict[str, Any]]:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise RuntimeError(
            "pre-enhancement text audit requires rapidocr-onnxruntime; "
            "install CyberPPT's image-text-audit dependency"
        ) from exc
    result, _elapsed = RapidOCR()(str(image_path))
    return [
        {"text": str(item[1]), "confidence": float(item[2]), "bbox": item[0]}
        for item in (result or [])
    ]


def _normalize(value: str) -> str:
    return re.sub(r"[\s\W_]+", "", value, flags=re.UNICODE)


def _ocr_edge_variants(value: str) -> set[str]:
    """Return variants after removing OCR-only ASCII edge marks.

    RapidOCR can read a thin vertical divider beside a label as ``I`` or ``1``.
    Those marks are layout artifacts, not glyph substitutions in the label.
    """
    divider_glyphs = {"I", "l", "1", "丨"}
    variants = {value}
    if value and value[0] in divider_glyphs:
        variants.add(value[1:])
    if value and value[-1] in divider_glyphs:
        variants.add(value[:-1])
    if (
        len(value) > 2
        and value[0] in divider_glyphs
        and value[-1] in divider_glyphs
    ):
        variants.add(value[1:-1])
    return {item for item in variants if len(item) >= 4}


def _ocr_mismatch_issues(
    items: list[dict[str, Any]], script_text: str
) -> list[dict[str, Any]]:
    """Never infer ordinary-copy truth by aligning OCR to script prose."""
    return []


def _canonical_fidelity_items(
    fidelity_text: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None,
) -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in fidelity_text or ():
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        visibility = str(item.get("visibility") or "").strip()
        if not text or visibility not in {"required", "if_rendered"}:
            continue
        key = (text, visibility)
        if key in seen:
            continue
        seen.add(key)
        values.append({"text": text, "visibility": visibility})
    return values


def _resolve_path(raw: str, *, base: Path) -> Path:
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def _resolve_fidelity_from_stage02_artifacts(
    image_path: Path,
) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    """Resolve fidelity through the persisted manifest -> canonical intake link.

    Stage 02 already persists ``stage02_script_input.path`` in the page manifest.
    Reusing that pointer avoids a second copy of the literal-preservation contract
    while still making production image QA consume the canonical intake.
    """

    manifest_path = image_path.parent / "page_image_pairs.json"
    if not manifest_path.is_file():
        return [], None
    manifest = _read_json_object(manifest_path)
    page_number: int | None = None
    pair_input_path = ""
    for pair in manifest.get("pairs") or []:
        if not isinstance(pair, dict):
            continue
        full = pair.get("full") if isinstance(pair.get("full"), dict) else {}
        raw_path = str(full.get("path") or "").strip()
        if not raw_path:
            continue
        if _resolve_path(raw_path, base=manifest_path.parent) != image_path:
            continue
        try:
            page_number = int(pair.get("page_number"))
        except (TypeError, ValueError):
            page_number = None
        pair_input_path = str(pair.get("stage02_script_input") or "").strip()
        break
    if page_number is None:
        return [], None

    manifest_input = manifest.get("stage02_script_input")
    root_input_path = (
        str(manifest_input.get("path") or "").strip()
        if isinstance(manifest_input, dict)
        else ""
    )
    raw_input_path = root_input_path or pair_input_path
    if not raw_input_path:
        return [], None
    intake_path = _resolve_path(raw_input_path, base=manifest_path.parent)
    if not intake_path.is_file():
        raise FileNotFoundError(
            f"Stage 02 fidelity intake referenced by image manifest is missing: {intake_path}"
        )
    intake = _read_json_object(intake_path)
    page_record = next(
        (
            page
            for page in intake.get("pages") or []
            if isinstance(page, dict)
            and int(page.get("page_number") or 0) == page_number
        ),
        None,
    )
    if page_record is None:
        raise ValueError(
            f"Stage 02 fidelity intake has no page {page_number}: {intake_path}"
        )
    fidelity = _canonical_fidelity_items(page_record.get("fidelity_text") or [])
    return fidelity, {
        "mode": "canonical_stage02_intake",
        "manifest": str(manifest_path.resolve()),
        "intake": str(intake_path),
        "page_number": page_number,
        "intake_semantic_sha256": str(intake.get("semantic_sha256") or ""),
    }


def _ocr_text_values(items: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            values.append(text)
    return values


def _fidelity_exactly_present(literal: str, observed: list[str]) -> bool:
    target = _normalize(literal)
    if not target:
        return False
    normalized = [_normalize(value) for value in observed if _normalize(value)]
    if any(target == value or target in value for value in normalized):
        return True
    joined = "".join(normalized)
    return bool(joined and target in joined)


def _nearest_fidelity_candidate(literal: str, observed: list[str]) -> tuple[str, float] | None:
    """Return a plausible rendered-but-corrupted OCR candidate, if any."""

    target = _normalize(literal)
    if len(target) < 3:
        return None
    best: tuple[str, float] | None = None
    for raw in observed:
        value = _normalize(raw)
        if not value or target in value:
            continue
        if abs(len(value) - len(target)) > max(2, round(len(target) * 0.35)):
            continue
        ratio = SequenceMatcher(a=target, b=value).ratio()
        if ratio < 0.72:
            continue
        if best is None or ratio > best[1]:
            best = (raw, ratio)
    return best


def _fidelity_issues(
    items: list[dict[str, Any]],
    fidelity_text: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None,
) -> list[dict[str, Any]]:
    fidelity_items = _canonical_fidelity_items(fidelity_text)
    if not fidelity_items:
        return []

    observed = _ocr_text_values(items)
    issues: list[dict[str, Any]] = []
    for item in fidelity_items:
        literal = item["text"]
        visibility = item["visibility"]
        if _fidelity_exactly_present(literal, observed):
            continue
        nearest = _nearest_fidelity_candidate(literal, observed)
        if visibility == "required":
            issues.append(
                {
                    "type": "fidelity_required_missing",
                    "expected": literal,
                    "observed": nearest[0] if nearest else "",
                    "similarity": round(nearest[1], 4) if nearest else None,
                    "evidence": "required fidelity literal is not present exactly in OCR output",
                }
            )
            continue
        if nearest is not None:
            issues.append(
                {
                    "type": "fidelity_if_rendered_mismatch",
                    "expected": literal,
                    "observed": nearest[0],
                    "similarity": round(nearest[1], 4),
                    "evidence": "conditional fidelity appears to be rendered but not exactly",
                }
            )
    return issues


def audit_generated_image_text(
    image_path: Path,
    *,
    script_text: str,
    fidelity_text: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    timeout: int = 300,
    vision_runner: Callable[..., str] | None = None,
    ocr_runner: Callable[[Path], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Check rendered glyphs plus explicit fidelity literals before enhancement.

    Ordinary ``script_text`` remains semantic context only and is never used for
    OCR exact-copy alignment. If callers do not pass fidelity explicitly, the
    gate resolves it through the persisted image manifest's canonical Stage 02
    intake pointer. This keeps one literal authority across first generation,
    imported-image revalidation, registered-source recovery and approved-image
    import without duplicating fidelity into a second runtime store.
    """
    image_path = image_path.expanduser().resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"generated image for text audit not found: {image_path}")
    fidelity_source: dict[str, Any] | None = None
    if fidelity_text is None:
        resolved_fidelity, fidelity_source = _resolve_fidelity_from_stage02_artifacts(image_path)
        fidelity_text = resolved_fidelity
    else:
        fidelity_source = {"mode": "explicit_argument"}
    if vision_runner is None:
        from scripts.imagegen_pipeline.providers.codex_oauth_image import run_codex_vision_text

        vision_runner = run_codex_vision_text
    ocr_runner = ocr_runner or _rapidocr
    with Image.open(image_path) as audited_image:
        audit_image_size = list(audited_image.size)
    prompt = f"""这些图片是同一张PPT正文图的3×2重叠高清局部块。只检查已经出现的文字是否有明确错字或乱码，只返回严格JSON。

这是字形审计，不是语义转录。逐字观察实际笔画，不得依据上下文或脚本文字自动纠正损坏字形。能够猜出原字也不能放行：笔画残缺、粘连、部件错位、错误拼接或非有效汉字均报告 gibberish；明确写成另一个有效汉字报告 typo。

不要报告漏字、新增文字、数字、标点、换行、字体、排版或一般可读性问题。
返回：{{"observed_text": ["..."], "issues": [{{"type": "typo|gibberish", "expected": "", "observed": "", "evidence": "", "bbox": [x1,y1,x2,y2]}}], "summary": ""}}
"""
    with tempfile.TemporaryDirectory(prefix="cyberppt-text-gate-") as tmp:
        tile_dir = Path(tmp)
        tile_paths: list[Path] = []
        with Image.open(image_path) as image:
            width, height = image.size
            for row in range(2):
                for column in range(3):
                    cell_width, cell_height, overlap = width / 3, height / 2, 0.08
                    box = (
                        max(0, round(column * cell_width - cell_width * overlap)),
                        max(0, round(row * cell_height - cell_height * overlap)),
                        min(width, round((column + 1) * cell_width + cell_width * overlap)),
                        min(height, round((row + 1) * cell_height + cell_height * overlap)),
                    )
                    tile_path = tile_dir / f"tile-r{row + 1}-c{column + 1}.png"
                    image.crop(box).save(tile_path)
                    tile_paths.append(tile_path)
        payload = _parse_json(vision_runner(prompt=prompt, image_paths=tile_paths, timeout=timeout))

    vision_issues = payload.get("issues")
    if not isinstance(vision_issues, list):
        raise ValueError("image text audit issues must be an array")
    blocking_types = {
        "typo", "misspelling", "wrong_character", "gibberish", "garbled_text", "pseudo_chinese",
    }
    issues = [
        issue for issue in vision_issues
        if isinstance(issue, dict)
        and str(issue.get("type") or "").strip().lower() in blocking_types
    ]
    ocr_items = ocr_runner(image_path)
    issues.extend(_ocr_mismatch_issues(ocr_items, script_text))
    issues.extend(_fidelity_issues(ocr_items, fidelity_text))
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for issue in issues:
        key = json.dumps(issue, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    valid = not unique
    canonical_fidelity = _canonical_fidelity_items(fidelity_text)
    return {
        "schema": "cyberppt.generated_image_text_audit.v3",
        "valid": valid,
        "scope": "fidelity_and_typo_gibberish" if canonical_fidelity else "typo_and_gibberish_only",
        "image": str(image_path),
        "image_size": audit_image_size,
        "issues": unique,
        "observed_text": payload.get("observed_text", []),
        "ocr_items": ocr_items,
        "fidelity_text": canonical_fidelity,
        "fidelity_source": fidelity_source,
        "summary": str(payload.get("summary") or ""),
        "required_action": None if valid else "regenerate_image_for_text_integrity_before_enhancement",
    }
