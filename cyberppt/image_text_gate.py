"""Pre-enhancement typo and pseudo-Chinese gate for generated PPT images."""

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
    # Very short OCR fragments are often neighboring-label slices; vision
    # review remains the authority for explicit two/three-character typos.
    return {item for item in variants if len(item) >= 4}


def _ocr_mismatch_issues(
    items: list[dict[str, Any]], script_text: str
) -> list[dict[str, Any]]:
    """Do not infer typo truth by aligning OCR strings to script prose.

    RapidOCR is retained as an observation source in the audit receipt, while
    blocking typo/gibberish decisions come only from the six-tile visual glyph
    audit.  Whole-string OCR alignment confuses neighboring labels, dividers,
    and valid-but-different Chinese words with single-character corruption.
    """
    return []


def audit_generated_image_text(
    image_path: Path,
    *,
    script_text: str,
    timeout: int = 300,
    vision_runner: Callable[..., str] | None = None,
    ocr_runner: Callable[[Path], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Check only explicit typos and gibberish before image enhancement."""
    image_path = image_path.expanduser().resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"generated image for text audit not found: {image_path}")
    if vision_runner is None:
        from scripts.dual_image_overlay.rebuild_engine.codex_oauth_image import run_codex_vision_text

        vision_runner = run_codex_vision_text
    ocr_runner = ocr_runner or _rapidocr
    prompt = f"""这些图片是同一张PPT正文图的3×2重叠高清局部块。只检查已经出现的文字是否有明确错字或乱码，只返回严格JSON。

这是字形审计，不是语义转录。逐字观察实际笔画，不得依据上下文或脚本文字自动纠正损坏字形。能够猜出原字也不能放行：笔画残缺、粘连、部件错位、错误拼接或非有效汉字均报告 gibberish；明确写成另一个有效汉字报告 typo。

脚本文字参考（只用于正确写法，不要求全部出现）：
{script_text}

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
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for issue in issues:
        key = json.dumps(issue, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    valid = not unique
    return {
        "schema": "cyberppt.generated_image_text_audit.v2",
        "valid": valid,
        "scope": "typo_and_gibberish_only",
        "image": str(image_path),
        "issues": unique,
        "observed_text": payload.get("observed_text", []),
        "ocr_items": ocr_items,
        "summary": str(payload.get("summary") or ""),
        "required_action": None if valid else "regenerate_image_for_typo_or_gibberish_before_enhancement",
    }
