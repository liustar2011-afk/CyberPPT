"""OCR-backed hard gate for visible text in rendered Quick output."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from PIL import Image

_CHINESE_RUN = re.compile(r"[\u3400-\u9fff]+")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _chinese_runs(value: object) -> list[str]:
    return _CHINESE_RUN.findall(_text(value))


def _allowed_run(observed: str, allowed: Iterable[str]) -> bool:
    return any(observed in candidate for candidate in allowed if candidate)


def audit_final_visible_text(
    image_path: Path | str,
    *,
    expected_texts: Iterable[str],
    authorized_image_texts: Iterable[str] = (),
    ocr_runner: Callable[[Path], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Reject rendered Chinese text that has no declared editable ownership.

    The check is intentionally narrow: it does not infer typo truth from OCR
    or require the OCR result to reproduce every expected line.  It catches
    extra/pseudo-Chinese visible in the final raster while permitting OCR to
    split a declared line into smaller runs.
    """

    image = Path(image_path).expanduser().resolve()
    report: dict[str, Any] = {
        "schema": "cyberppt.stage02.final_visible_text_qa.v1",
        "image": str(image),
        "image_sha256": _sha256(image) if image.is_file() else "",
        "expected_texts": [_text(item) for item in expected_texts if _text(item)],
        "authorized_image_texts": [_text(item) for item in authorized_image_texts if _text(item)],
        "observed_text": [],
        "unexpected_chinese": [],
        "checks": {"ocr_executed": False, "no_unowned_chinese": False},
        "valid": False,
    }
    if not image.is_file():
        report["error"] = f"rendered Quick image is missing: {image}"
        return report
    try:
        with Image.open(image) as rendered:
            report["image_size"] = list(rendered.size)
        if ocr_runner is None:
            from cyberppt.image_text_gate import _rapidocr

            ocr_runner = _rapidocr
        observations = ocr_runner(image)
        if not isinstance(observations, list) or any(
            not isinstance(item, Mapping) for item in observations
        ):
            raise RuntimeError("final visible-text OCR returned an invalid observation list")
        report["checks"]["ocr_executed"] = True
    except Exception as exc:  # An unexecuted hard gate cannot pass.
        report["error"] = f"final visible-text OCR unavailable: {exc}"
        return report

    allowed: list[str] = []
    for item in (*report["expected_texts"], *report["authorized_image_texts"]):
        allowed.extend(_chinese_runs(item))
        # OCR can join Chinese runs by reading an authored em/en dash as 一.
        # Only declared dash positions gain this exact alias; ordinary Chinese
        # is never deleted/replaced and native PPTX text is checked separately.
        if any(marker in item for marker in ("—", "–", "｜", "|")):
            allowed.extend(
                _chinese_runs(item.translate(str.maketrans({"—": "一", "–": "一", "｜": "一", "|": "一"})))
            )
    unexpected: list[dict[str, Any]] = []
    for observation in observations:
        if not isinstance(observation, Mapping):
            continue
        observed = _text(observation.get("text"))
        if not observed:
            continue
        report["observed_text"].append(observed)
        for run in _chinese_runs(observed):
            confidence = observation.get("confidence")
            if len(run) == 1 and isinstance(confidence, (int, float)) and confidence < 0.75:
                continue
            if not _allowed_run(run, allowed):
                unexpected.append(
                    {
                        "observed_text": observed,
                        "chinese_run": run,
                        "bbox": observation.get("bbox"),
                        "confidence": observation.get("confidence"),
                    }
                )
    report["unexpected_chinese"] = unexpected
    report["checks"]["no_unowned_chinese"] = not unexpected
    report["valid"] = bool(report["checks"]["ocr_executed"] and not unexpected)
    report["status"] = "passed" if report["valid"] else "failed"
    return report


def write_final_visible_text_qa(path: Path | str, report: Mapping[str, Any]) -> Path:
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(dict(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return destination


__all__ = ["audit_final_visible_text", "write_final_visible_text_qa"]
