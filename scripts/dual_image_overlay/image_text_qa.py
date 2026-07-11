"""Deterministic QA for text observed in generated full-page images."""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

from scripts.dual_image_overlay.prompt_policy import classify_forbidden_text


_PUNCTUATION_RE = re.compile(r"[\s，。,.、:：;；！？!?（）()【】\[\]“”\"'‘’‘’·—_\-]+")


def _normalize_text(text: str) -> str:
    return _PUNCTUATION_RE.sub("", text).lower()


def _matches_allowed(observed: str, allowed_lines: Iterable[str]) -> bool:
    observed_key = _normalize_text(observed)
    if not observed_key:
        return True
    for allowed in allowed_lines:
        allowed_key = _normalize_text(allowed)
        if not allowed_key:
            continue
        if observed_key == allowed_key or observed_key in allowed_key or allowed_key in observed_key:
            return True
        if min(len(observed_key), len(allowed_key)) >= 4 and SequenceMatcher(
            None, observed_key, allowed_key
        ).ratio() >= 0.86:
            return True
    return False


def inspect_image_text(
    *,
    page: int,
    image_path: Path,
    allowed_lines: Iterable[str],
    ocr_text: str,
) -> dict[str, object]:
    """Classify OCR text without allowing the OCR model to decide pass/fail."""

    allowed = tuple(str(line).strip() for line in allowed_lines if str(line).strip())
    observed = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    forbidden_matches: list[dict[str, str]] = []
    unexpected_text: list[str] = []
    for line in observed:
        classes = classify_forbidden_text(line)
        if classes:
            forbidden_matches.append(
                {
                    "class": classes[0],
                    "classes": ",".join(classes),
                    "text": line,
                }
            )
        elif not _matches_allowed(line, allowed):
            unexpected_text.append(line)

    if forbidden_matches:
        status = "failed"
    elif unexpected_text:
        status = "review_required"
    else:
        status = "passed"
    return {
        "schema": "cyberppt.image_text_qa.v1",
        "page": page,
        "image_path": str(image_path.expanduser().resolve()),
        "allowed_text": list(allowed),
        "observed_text": observed,
        "forbidden_matches": forbidden_matches,
        "unexpected_text": unexpected_text,
        "status": status,
        "deliverable_allowed": status == "passed",
    }


def run_image_text_qa(
    *,
    page: int,
    image_path: Path,
    allowed_lines: Iterable[str],
    model: str | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    """Obtain OCR text through the existing vision transport, then classify it."""

    from scripts.dual_image_overlay.rebuild_engine.codex_oauth_image import run_codex_vision_text

    ocr_text = run_codex_vision_text(
        prompt=(
            "Extract every visible text line from this generated PPT content-region image. "
            "Return plain text only, one visible line per output line. Do not infer or rewrite text."
        ),
        image_paths=[image_path],
        model=model,
        dry_run=dry_run,
    )
    report = inspect_image_text(
        page=page,
        image_path=image_path,
        allowed_lines=allowed_lines,
        ocr_text=ocr_text,
    )
    report["ocr_source"] = "codex_vision_text"
    report["model"] = model
    return report


def write_image_text_qa(report: dict[str, object], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
