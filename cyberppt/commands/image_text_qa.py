"""Project-scoped generated-image text QA orchestration."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.dual_image_overlay.deliverable_prompt import (
    parse_page_blocks,
    parse_pages,
    visible_deliverable_lines,
)
from scripts.dual_image_overlay.image_text_qa import (
    inspect_image_text,
    run_image_text_qa,
    write_image_text_qa,
)


STAGE_ROOT = Path("workbench/stages/02-blueprint-dual-image")


def _pages_slug_from_raw(pages_raw: str) -> str:
    pages: list[int] = []
    for part in pages_raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(value.strip()) for value in part.split("-", 1)]
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    pages = sorted(set(pages))
    if not pages:
        raise ValueError("at least one page is required")
    if pages == list(range(pages[0], pages[-1] + 1)):
        return f"pages_{pages[0]:03d}_{pages[-1]:03d}"
    return "pages_" + "_".join(f"{page:03d}" for page in pages)


def _stage_dir_for_project(root: Path, pages_raw: str) -> Path:
    for prepare_path in sorted((root / STAGE_ROOT).glob("*/production_prepare.json")):
        try:
            payload = _read_json(prepare_path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if payload.get("pages_raw") == pages_raw:
            return prepare_path.parent
    return root / STAGE_ROOT / _pages_slug_from_raw(pages_raw)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _fixture_texts(path: Path | None) -> dict[str, str] | None:
    if path is None:
        return None
    payload = _read_json(path)
    pages = payload.get("pages") if isinstance(payload.get("pages"), dict) else payload
    result: dict[str, str] = {}
    for key, value in pages.items():
        if isinstance(value, dict):
            value = value.get("text")
        if isinstance(value, list):
            value = "\n".join(str(item) for item in value)
        result[str(key)] = str(value or "")
    return result


def _update_imagegen_run_qa_status(
    root: Path,
    manifest_path: Path,
    page: int,
    full: dict[str, Any],
    image_path: Path,
    report_path: Path,
    status: str,
) -> None:
    """Attach the QA result only to the matching sealed generation record."""

    run_path = root / "imagegen_runs" / f"page_{page}.json"
    if not run_path.is_file():
        return
    run = _read_json(run_path)
    prompt = full.get("prompt")
    if not isinstance(prompt, str):
        return
    if (
        run.get("manifest_sha256") != _sha256(manifest_path)
        or run.get("prompt_sha256") != hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        or run.get("output_sha256") != _sha256(image_path)
        or Path(str(run.get("output_path", ""))).expanduser().resolve() != image_path
    ):
        return
    run["status"] = status
    run["image_text_qa"] = str(report_path.resolve())
    run["image_text_qa_sha256"] = _sha256(report_path)
    run_path.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_project_image_text_qa(
    project: Path,
    pages_raw: str,
    *,
    ocr_json: Path | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    root = project.expanduser().resolve()
    stage_dir = _stage_dir_for_project(root, pages_raw)
    manifest_path = stage_dir / "page_image_pairs.json"
    if not manifest_path.is_file():
        raise ValueError(f"page image manifest is required: {manifest_path}")
    manifest = _read_json(manifest_path)
    script_path = Path(str(manifest.get("imagegen_script") or manifest.get("source_script") or "")).expanduser()
    if not script_path.is_absolute():
        script_path = manifest_path.parent / script_path
    script_path = script_path.resolve()
    if not script_path.is_file():
        raise ValueError(f"imagegen_script.md is required: {script_path}")

    blocks = parse_page_blocks(script_path)
    pages = parse_pages(pages_raw, set(blocks))
    pairs = {
        int(pair["page_number"]): pair
        for pair in manifest.get("pairs", [])
        if isinstance(pair, dict) and "page_number" in pair
    }
    fixture_texts = _fixture_texts(ocr_json)
    qa_dir = stage_dir / "image_text_qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, Any]] = []
    for page in pages:
        pair = pairs.get(page)
        if pair is None or not isinstance(pair.get("full"), dict):
            raise ValueError(f"page {page} full image is missing from manifest")
        image_path = Path(str(pair["full"].get("path") or "")).expanduser().resolve()
        if not image_path.is_file():
            raise ValueError(f"page {page} generated full image is missing: {image_path}")
        allowed_lines = visible_deliverable_lines(blocks[page])
        if fixture_texts is not None:
            if str(page) not in fixture_texts:
                raise ValueError(f"fixture OCR text is missing page {page}")
            report = inspect_image_text(
                page=page,
                image_path=image_path,
                allowed_lines=allowed_lines,
                ocr_text=fixture_texts[str(page)],
            )
            report["ocr_source"] = "fixture"
            report["ocr_fixture"] = str(ocr_json.expanduser().resolve()) if ocr_json else None
        else:
            report = run_image_text_qa(
                page=page,
                image_path=image_path,
                allowed_lines=allowed_lines,
                model=model,
            )
        report["image_sha256"] = _sha256(image_path)
        report["imagegen_script_sha256"] = str(manifest.get("imagegen_script_sha256") or _sha256(script_path))
        report_path = write_image_text_qa(report, qa_dir / f"page_{page:03d}.json")
        _update_imagegen_run_qa_status(
            root,
            manifest_path,
            page,
            pair["full"],
            image_path,
            report_path,
            str(report["status"]),
        )
        reports.append({"page": page, "path": str(report_path), "status": report["status"]})

    statuses = [str(item["status"]) for item in reports]
    status = "passed" if all(item == "passed" for item in statuses) else (
        "failed" if "failed" in statuses else "review_required"
    )
    summary = {
        "schema": "cyberppt.image_text_qa_summary.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project": str(root),
        "pages_raw": pages_raw,
        "pages": pages,
        "status": status,
        "deliverable_allowed": status == "passed",
        "imagegen_script": str(script_path),
        "imagegen_script_sha256": _sha256(script_path),
        "page_image_manifest": str(manifest_path),
        "page_image_manifest_sha256": _sha256(manifest_path),
        "prompt_policy_report": manifest.get("prompt_policy_report"),
        "reports": reports,
        "resume_command": f"python3 -m cyberppt image-text-qa {root} --pages {pages_raw}",
    }
    summary_path = qa_dir / "image_text_qa_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary
