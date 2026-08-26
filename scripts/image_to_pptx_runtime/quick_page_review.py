"""Human visual-review receipts for Stage 02 Quick page previews."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


QUICK_VISUAL_REVIEW_CHECKS = frozenset(
    {
        "layout_fidelity",
        "typography_fidelity",
        "color_weight_fidelity",
        "text_wrapping",
        "residual_chinese",
        "readability",
    }
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quick_visual_review_passes(checkpoint: Mapping[str, Any]) -> bool:
    review = checkpoint.get("visual_review")
    if not isinstance(review, Mapping) or review.get("status") != "passed":
        return False
    preview = Path(str(checkpoint.get("preview_png") or ""))
    if not preview.is_file() or review.get("preview_png_sha256") != _sha256(preview):
        return False
    checks = review.get("checks")
    return isinstance(checks, Mapping) and QUICK_VISUAL_REVIEW_CHECKS.issubset(
        {str(key) for key, value in checks.items() if value == "passed"}
    )


def record_quick_page_review(
    manifest_path: Path,
    *,
    page_number: int,
    status: str,
    reviewer: str,
    checks: Mapping[str, str],
    notes: str = "",
) -> dict[str, Any]:
    """Bind a human decision to the exact rendered preview bytes."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list):
        raise ValueError("manifest has no page pairs")
    pair = next(
        (item for item in pairs if isinstance(item, dict) and item.get("page_number") == page_number),
        None,
    )
    if pair is None:
        raise ValueError(f"manifest has no page {page_number}")
    checkpoint = pair.get("quick_page_checkpoint")
    if not isinstance(checkpoint, dict):
        raise ValueError(f"page {page_number} has no rendered Quick checkpoint")
    preview = Path(str(checkpoint.get("preview_png") or ""))
    if not preview.is_file():
        raise ValueError(f"page {page_number} preview PNG is missing")
    if status not in {"passed", "failed"}:
        raise ValueError("visual review status must be passed or failed")
    normalized = {str(key): str(value) for key, value in checks.items()}
    missing = QUICK_VISUAL_REVIEW_CHECKS - normalized.keys()
    invalid = {key for key, value in normalized.items() if value not in {"passed", "failed"}}
    if missing or invalid:
        raise ValueError(
            "visual review requires passed/failed decisions for: "
            + ", ".join(sorted(QUICK_VISUAL_REVIEW_CHECKS))
        )
    if status == "passed" and any(normalized[key] != "passed" for key in QUICK_VISUAL_REVIEW_CHECKS):
        raise ValueError("a passed visual review requires all checks to pass")
    review = {
        "schema": "cyberppt.stage02.quick_visual_review.v1",
        "status": status,
        "reviewer": reviewer.strip() or "human-reviewer",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "preview_png": str(preview),
        "preview_png_sha256": _sha256(preview),
        "checks": {key: normalized[key] for key in sorted(QUICK_VISUAL_REVIEW_CHECKS)},
        "notes": notes,
    }
    checkpoint["visual_review"] = review
    checkpoint["status"] = "passed" if status == "passed" else "visual_review_failed"
    checkpoint["resume"] = "reviewed"
    temporary = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(manifest_path)
    return {"page_number": page_number, "checkpoint_status": checkpoint["status"], **review}
