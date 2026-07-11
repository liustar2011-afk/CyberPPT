"""Sealed execution of one approved ImageGen manifest page."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from scripts.dual_image_overlay.rebuild_engine.codex_oauth_image import run_codex_image


STAGE_ROOT = Path("workbench/stages/02-blueprint-dual-image")
ImageGenerator = Callable[..., Path]


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _single_page(pages_raw: str) -> int:
    value = pages_raw.strip()
    if not value or "," in value or "-" in value:
        raise ValueError("imagegen-run accepts exactly one page")
    try:
        page = int(value)
    except ValueError as exc:
        raise ValueError("imagegen-run accepts exactly one page") from exc
    if page < 1:
        raise ValueError("imagegen-run accepts a positive page number")
    return page


def _matching_manifest_paths(root: Path, page: int) -> list[Path]:
    stage_root = root / STAGE_ROOT
    matches: list[Path] = []
    for path in stage_root.glob("*/page_image_pairs.json"):
        try:
            manifest = _read_manifest(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        pairs = manifest.get("pairs")
        if isinstance(pairs, list) and any(
            isinstance(pair, dict) and pair.get("page_number") == page for pair in pairs
        ):
            matches.append(path)
    return sorted(matches)


def _resolve_manifest(root: Path, page: int) -> tuple[Path, dict[str, Any]]:
    matches = _matching_manifest_paths(root, page)
    if not matches:
        raise ValueError(f"no approved content-page manifest found for page {page}")
    if len(matches) != 1:
        formatted = ", ".join(str(path) for path in matches)
        raise ValueError(f"multiple current manifests contain page {page}: {formatted}")
    path = matches[0]
    return path, _read_manifest(path)


def _content_pair(manifest: dict[str, Any], page: int) -> dict[str, Any]:
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list):
        raise ValueError("manifest pairs must be a list")
    matching = [pair for pair in pairs if isinstance(pair, dict) and pair.get("page_number") == page]
    if len(matching) != 1 or not isinstance(matching[0].get("full"), dict):
        raise ValueError(f"page {page} is not an approved content-page pair")
    return matching[0]


def _expected_dimensions(manifest: dict[str, Any]) -> tuple[int, int]:
    contract = manifest.get("generation_contract")
    size = contract.get("generation_size") if isinstance(contract, dict) else None
    if not isinstance(size, dict):
        raise ValueError("manifest generation_contract.generation_size is required")
    width, height = size.get("width"), size.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or width < 1 or height < 1:
        raise ValueError("manifest generation size must contain positive integer dimensions")
    return width, height


def run_imagegen_page(
    project: Path,
    pages_raw: str,
    model: str | None = None,
    *,
    generator: ImageGenerator | None = None,
) -> dict[str, Any]:
    """Generate exactly one approved full-image manifest entry and record it."""
    root = project.expanduser().resolve()
    page = _single_page(pages_raw)
    manifest_path, manifest = _resolve_manifest(root, page)
    pair = _content_pair(manifest, page)
    full = pair["full"]
    prompt = full.get("prompt")
    path_value = full.get("path")
    if not isinstance(prompt, str) or not prompt:
        raise ValueError(f"page {page} full prompt is required")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError(f"page {page} full output path is required")
    output_path = Path(path_value).expanduser()
    if not output_path.is_absolute():
        output_path = (manifest_path.parent / output_path).resolve()
    expected_dimensions = _expected_dimensions(manifest)
    image_generator = generator or run_codex_image
    kwargs: dict[str, Any] = {"prompt": prompt, "output_path": output_path}
    if model is not None:
        kwargs["model"] = model
    image_generator(**kwargs)
    if not output_path.is_file():
        raise RuntimeError(f"image generator did not create manifest output: {output_path}")
    with Image.open(output_path) as image:
        actual_dimensions = image.size
    if actual_dimensions != expected_dimensions:
        raise ValueError(
            f"generated image dimensions {actual_dimensions[0]}x{actual_dimensions[1]} do not match "
            f"manifest generation size {expected_dimensions[0]}x{expected_dimensions[1]}"
        )

    run_dir = root / "imagegen_runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_path = run_dir / f"page_{page}.json"
    report = {
        "schema": "cyberppt.imagegen_run.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project": str(root),
        "page": page,
        "model": model,
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256_bytes(manifest_path.read_bytes()),
        "prompt_sha256": _sha256_bytes(prompt.encode("utf-8")),
        "output_path": str(output_path),
        "output_sha256": _sha256_bytes(output_path.read_bytes()),
        "expected_dimensions": list(expected_dimensions),
        "actual_dimensions": list(actual_dimensions),
        "status": "awaiting_image_text_qa",
        "image_text_qa": None,
    }
    run_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["run_path"] = str(run_path)
    return report
