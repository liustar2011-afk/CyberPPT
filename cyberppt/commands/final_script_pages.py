"""Project-level wrapper for running selected pages from a final script."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from scripts.dual_image_overlay.cyberppt_pair_manifest import build_manifest, require_generated
from scripts.dual_image_overlay.deliverable_prompt import parse_page_blocks, parse_pages, template_title


STAGE_DIR = "workbench/stages/02-blueprint-dual-image"
TEMPLATE_LOCK_DIR = "workbench/locks/template_text"
LEDGER_PATH = "workbench/artifact-ledger.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _page_range_slug(pages: list[int]) -> str:
    if not pages:
        raise ValueError("at least one page is required")
    if pages == list(range(pages[0], pages[-1] + 1)):
        return f"pages_{pages[0]:03d}_{pages[-1]:03d}"
    return "pages_" + "_".join(f"{page:03d}" for page in pages)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema": "cyberppt.artifact_ledger.v1", "artifacts": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_project_dirs(project: Path) -> None:
    for relative in (
        STAGE_DIR,
        TEMPLATE_LOCK_DIR,
        "workbench/stages/03-overlay",
        "workbench/stages/04-template-rebuild",
        "workbench/stages/05-qa-delivery",
        "outputs/pages",
        "outputs/renders",
        "delivery",
    ):
        (project / relative).mkdir(parents=True, exist_ok=True)


def _template_text_lock(
    *,
    project: Path,
    script: Path,
    pages: list[int],
    pages_raw: str,
    style_lock: Path | None,
    manifest_path: Path,
) -> Path:
    blocks = parse_page_blocks(script)
    records: list[dict[str, Any]] = []
    for page_number in pages:
        page = blocks[page_number]
        records.append(
            {
                "page": page_number,
                "title": template_title(page),
                "subtitle": "",
                "section": "",
                "template_variant": "default",
                "page_badge_enabled": False,
                "footer_enabled": False,
                "source": str(script),
                "approved": True,
                "depends_on": [str(script), str(manifest_path)],
                "resume_command": (
                    "python3 -m cyberppt final-script-pages "
                    f"{project} --script {script} --pages {pages_raw}"
                ),
            }
        )
    payload = {
        "schema": "cyberppt.template_text_lock.v1",
        "created_at": _utc_now(),
        "project": str(project),
        "source_script": str(script),
        "style_lock": str(style_lock) if style_lock else None,
        "pages": pages,
        "records": records,
    }
    slug = _page_range_slug(pages)
    path = project / TEMPLATE_LOCK_DIR / f"{slug}_template_text_lock.json"
    _write_json(path, payload)
    return path


def _artifact_record(
    *,
    stage: str,
    page: str,
    path: Path,
    status: str,
    depends_on: list[Path],
    resume_command: str,
    supersedes: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "stage": stage,
        "page": page,
        "path": str(path),
        "status": status,
        "depends_on": [str(item) for item in depends_on],
        "supersedes": supersedes or [],
        "resume_command": resume_command,
        "sha256": _sha256(path),
        "updated_at": _utc_now(),
    }
    return payload


def _append_ledger(project: Path, records: list[dict[str, Any]]) -> Path:
    ledger_path = project / LEDGER_PATH
    ledger = _read_json(ledger_path)
    ledger.setdefault("schema", "cyberppt.artifact_ledger.v1")
    artifacts = ledger.setdefault("artifacts", [])
    existing_paths = {str(item.get("path")): item for item in artifacts if isinstance(item, dict)}
    for record in records:
        existing_paths[record["path"]] = record
    ledger["artifacts"] = list(existing_paths.values())
    _write_json(ledger_path, ledger)
    return ledger_path


def run_final_script_pages(
    *,
    project: Path,
    script: Path,
    pages_raw: str,
    style_lock: Path | None = None,
    output_dir: Path | None = None,
    require_images: bool = False,
    run_rebuild: bool = False,
    rebuild_args: list[str] | None = None,
) -> dict[str, Any]:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    style_lock = style_lock.expanduser().resolve() if style_lock else None
    if not script.is_file():
        raise FileNotFoundError(f"final script not found: {script}")
    _ensure_project_dirs(project)

    blocks = parse_page_blocks(script)
    pages = parse_pages(pages_raw, set(blocks))
    slug = _page_range_slug(pages)
    target_dir = output_dir.expanduser().resolve() if output_dir else project / STAGE_DIR / slug

    manifest, manifest_path, compiled_script, page_numbers = build_manifest(
        script=script,
        pages_raw=pages_raw,
        output_dir=target_dir,
        project_path=project,
        style_lock=style_lock,
    )
    lock_path = _template_text_lock(
        project=project,
        script=script,
        pages=page_numbers,
        pages_raw=pages_raw,
        style_lock=style_lock,
        manifest_path=manifest_path,
    )
    if require_images:
        require_generated(manifest)

    rebuild_status: dict[str, Any] | None = None
    if run_rebuild:
        command = [
            sys.executable,
            "-m",
            "cyberppt",
            "template-rebuild",
            str(manifest_path),
            *(rebuild_args or []),
        ]
        completed = subprocess.run(command, check=False)
        rebuild_status = {
            "command": command,
            "returncode": completed.returncode,
            "status": "completed" if completed.returncode == 0 else "failed",
        }
        if completed.returncode != 0:
            raise RuntimeError(f"template rebuild failed with exit code {completed.returncode}")

    resume_command = f"python3 -m cyberppt final-script-pages {project} --script {script} --pages {pages_raw}"
    run_summary = {
        "schema": "cyberppt.final_script_pages_run.v1",
        "created_at": _utc_now(),
        "project": str(project),
        "source_script": str(script),
        "pages": page_numbers,
        "stage": "02-blueprint-dual-image",
        "status": "ready_for_image_generation" if not require_images else "image_assets_verified",
        "artifacts": {
            "compiled_deliverable_prompt": str(compiled_script),
            "page_image_pairs": str(manifest_path),
            "template_text_lock": str(lock_path),
            "output_dir": str(target_dir),
        },
        "next_steps": [
            "Generate each full image from the pair manifest full.prompt.",
            "Generate each no-text background from the corresponding background.prompt.",
            "Rerun this command with --require-images --run-rebuild after image files exist.",
        ],
        "resume_command": resume_command,
        "rebuild": rebuild_status,
    }
    summary_path = target_dir / f"{slug}_final_script_pages_run.json"
    _write_json(summary_path, run_summary)

    page_label = f"{page_numbers[0]}-{page_numbers[-1]}" if len(page_numbers) > 1 else str(page_numbers[0])
    _append_ledger(
        project,
        [
            _artifact_record(
                stage="02-blueprint-dual-image",
                page=page_label,
                path=compiled_script,
                status="ready_for_image_generation",
                depends_on=[script],
                resume_command=resume_command,
            ),
            _artifact_record(
                stage="02-blueprint-dual-image",
                page=page_label,
                path=manifest_path,
                status="ready_for_image_generation",
                depends_on=[compiled_script],
                resume_command=resume_command,
            ),
            _artifact_record(
                stage="02-blueprint-dual-image",
                page=page_label,
                path=lock_path,
                status="approved",
                depends_on=[script, manifest_path],
                resume_command=resume_command,
            ),
            _artifact_record(
                stage="02-blueprint-dual-image",
                page=page_label,
                path=summary_path,
                status="ready_for_image_generation",
                depends_on=[compiled_script, manifest_path, lock_path],
                resume_command=resume_command,
            ),
        ],
    )
    return run_summary
