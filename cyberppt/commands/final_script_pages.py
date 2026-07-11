"""Project-level wrapper for running selected pages from a final script."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from cyberppt.commands.blueprint_gate import (
    assert_blueprint_image_review_ready,
    assert_blueprint_input_ready,
    assert_speaker_notes_review_ready,
)
from scripts.dual_image_overlay.cyberppt_pair_manifest import build_manifest, require_generated
from scripts.dual_image_overlay.deliverable_prompt import parse_page_blocks, parse_pages, template_title
from scripts.dual_image_overlay.style_library import write_project_style_lock
from scripts.speaker_notes import build_manifest as build_speaker_notes_manifest


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
                    + (f" --style-lock {style_lock}" if style_lock else "")
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


def _template_rebuild_failure_message(project: Path, returncode: int) -> str:
    readiness_path = project / "analysis" / "template_rebuild_readiness.json"
    source_gate_path = project / "analysis" / "source_capture_gate.json"
    page_quality_path = project / "analysis" / "page_quality_report.json"
    lines = [
        f"template rebuild quality gate failed with exit code {returncode}.",
        "Stop delivery progression; generated PPTX, if any, is an intermediate artifact only.",
    ]
    if readiness_path.is_file():
        readiness = _read_json(readiness_path)
        lines.append(f"readiness: {readiness_path}")
        lines.append(f"status: {readiness.get('status')}")
        lines.append(f"valid: {readiness.get('valid')}")
        checks = readiness.get("checks")
        if isinstance(checks, dict):
            failed = [key for key, value in checks.items() if value is False]
            if failed:
                lines.append("failed_checks: " + ", ".join(failed))
        artifacts = readiness.get("artifacts")
        if isinstance(artifacts, dict) and artifacts.get("exported_pptx"):
            lines.append(f"intermediate_pptx: {artifacts['exported_pptx']}")
    else:
        lines.append(f"readiness: missing ({readiness_path})")

    if source_gate_path.is_file():
        source_gate = _read_json(source_gate_path)
        gap_counts = source_gate.get("gap_counts")
        if isinstance(gap_counts, dict) and gap_counts:
            lines.append("blocking_gap_counts: " + ", ".join(f"{key}={value}" for key, value in gap_counts.items()))
        blocking = source_gate.get("blocking_gaps")
        if isinstance(blocking, list) and blocking:
            lines.append("blocking_gaps:")
            for gap in blocking[:12]:
                if not isinstance(gap, dict):
                    continue
                page = gap.get("page_number")
                code = gap.get("code")
                message = gap.get("message")
                lines.append(f"- page {page}: {code} - {message}")
            if len(blocking) > 12:
                lines.append(f"- ... {len(blocking) - 12} more")
    else:
        lines.append(f"source_capture_gate: missing ({source_gate_path})")

    if page_quality_path.is_file():
        page_quality = _read_json(page_quality_path)
        lines.append(f"page_quality_report: {page_quality_path}")
        lines.append(f"page_quality_valid: {page_quality.get('valid')}")
        blocking = page_quality.get("blocking_errors")
        if isinstance(blocking, list) and blocking:
            lines.append("page_quality_blocking_errors:")
            for item in blocking[:12]:
                if isinstance(item, dict):
                    lines.append(f"- {item.get('id')}: {item.get('description')}")
            if len(blocking) > 12:
                lines.append(f"- ... {len(blocking) - 12} more")
    else:
        lines.append(f"page_quality_report: missing ({page_quality_path})")
    return "\n".join(lines)


def _template_rebuild_artifacts(project: Path) -> dict[str, str | None]:
    artifacts = {
        "template_rebuild_readiness": project / "analysis" / "template_rebuild_readiness.json",
        "source_capture": project / "analysis" / "source_capture.json",
        "source_capture_gate": project / "analysis" / "source_capture_gate.json",
        "template_gate": project / "analysis" / "template_gate.json",
        "page_quality_report": project / "analysis" / "page_quality_report.json",
    }
    return {key: str(path) if path.exists() else None for key, path in artifacts.items()}


def _artifact_if_file(path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    return str(candidate.resolve()) if candidate.is_file() else None


def _artifact_if_dir_has_files(path: Path | str | None, pattern: str = "*.json") -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    return str(candidate.resolve()) if candidate.is_dir() and any(candidate.glob(pattern)) else None


def _first_artifact_file(*paths: Path | str | None) -> str | None:
    for path in paths:
        artifact = _artifact_if_file(path)
        if artifact:
            return artifact
    return None


def _first_artifact_dir(*paths: Path | str | None, pattern: str = "*.json") -> str | None:
    for path in paths:
        artifact = _artifact_if_dir_has_files(path, pattern)
        if artifact:
            return artifact
    return None


def _first_matching_file(directory: Path, pattern: str) -> str | None:
    matches = sorted(directory.glob(pattern)) if directory.is_dir() else []
    return str(matches[0].resolve()) if matches else None


def _stage02_production_artifacts(project: Path) -> dict[str, str | None]:
    analysis = project / "analysis"
    readiness_path = analysis / "template_rebuild_readiness.json"
    readiness = _read_json(readiness_path) if readiness_path.is_file() else {}
    readiness_artifacts = readiness.get("artifacts")
    if not isinstance(readiness_artifacts, dict):
        readiness_artifacts = {}
    latest_export = None
    exports = sorted((project / "exports").glob("*.pptx"), key=lambda path: path.stat().st_mtime)
    if exports:
        latest_export = str(exports[-1])

    semantic_plan_dir = readiness_artifacts.get("semantic_plan_dir") or analysis / "semantic_plan"
    scene_graph_dir = readiness_artifacts.get("scene_graph_gate_dir") or analysis / "scene_graph_gate"
    visual_registry_dir = (
        readiness_artifacts.get("measured_visual_registry")
        or readiness_artifacts.get("draft_visual_registry")
        or analysis / "visual_registry"
    )
    return {
        "source_capture": _first_artifact_file(
            readiness_artifacts.get("source_capture"),
            analysis / "source_capture.json",
        ),
        "semantic_binding": _first_artifact_file(
            readiness_artifacts.get("semantic_binding"),
            analysis / "semantic_binding" / "semantic_binding_index.json",
        ),
        "semantic_plan": _first_artifact_dir(semantic_plan_dir, pattern="*.json"),
        "scene_graph": _first_artifact_dir(scene_graph_dir, pattern="*.json"),
        "visual_registry": _first_artifact_dir(visual_registry_dir, pattern="*.json"),
        "container_workspace": _first_artifact_file(
            readiness_artifacts.get("container_workspace"),
            analysis / "container_workspace" / "container_workspace_index.json",
        ),
        "workspace_assignment": _first_artifact_file(
            readiness_artifacts.get("workspace_assignment"),
            analysis / "workspace_assignment" / "workspace_assignment_index.json",
        ),
        "office_textbox_fit": _first_artifact_file(analysis / "office_textbox_fit.json"),
        "editable_pptx": _first_artifact_file(readiness_artifacts.get("exported_pptx"), latest_export),
        "render_compare": _first_artifact_file(
            readiness_artifacts.get("render_compare"),
            _first_matching_file(analysis, "page_*_render_compare.json"),
        ),
        "qa_registry": _first_artifact_file(
            readiness_artifacts.get("page_quality_report"),
            analysis / "page_quality_report.json",
        ),
    }


def _stage02_production_reports(artifacts: dict[str, str | None]) -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        if not artifact or not artifact.endswith(".json"):
            continue
        try:
            reports[name] = _read_json(Path(artifact))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return reports


def _latest_pptx(directory: Path) -> str | None:
    matches = sorted(directory.glob("*.pptx"), key=lambda path: path.stat().st_mtime) if directory.is_dir() else []
    return str(matches[-1]) if matches else None


def _image_ppt_artifacts(output_dir: Path, name: str) -> dict[str, str | None]:
    project_dir = output_dir / f"{name}_template_image_project"
    return {
        "template_image_manifest": str(output_dir / "template_image_manifest.json"),
        "template_image_prompts": str(output_dir / "template_image_prompts.md"),
        "template_image_project": str(project_dir),
        "exported_pptx": _latest_pptx(project_dir / "exports"),
    }


def _business_script_source(project: Path) -> Path | None:
    candidates = (
        project / "workbench" / "analysis_expression" / "business_script.md",
        project / "workbench" / "stages" / "01-analysis" / "page_content_design_internal_reporting.md",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _run_speaker_notes_build(*, project: Path, pages_raw: str, output_dir: Path) -> dict[str, Any] | None:
    business_script = _business_script_source(project)
    if business_script is None:
        return None
    notes_dir = output_dir / "speaker_notes"
    try:
        llm_error = ""
        try:
            manifest = build_speaker_notes_manifest(
                business_script=business_script,
                pages_raw=pages_raw,
                output_dir=notes_dir,
                use_llm=True,
            )
        except Exception as exc:
            llm_error = str(exc)
            manifest = build_speaker_notes_manifest(
                business_script=business_script,
                pages_raw=pages_raw,
                output_dir=notes_dir,
            )
    except ValueError as exc:
        if "Pages not found" in str(exc):
            return None
        raise
    manifest_path = notes_dir / "speaker_notes_manifest.json"
    _write_json(manifest_path, manifest)
    return {
        "business_script": str(business_script),
        "speaker_notes_manifest": str(manifest_path),
        "llm_prompt": manifest.get("llm_prompt"),
        "llm_output": manifest.get("llm_output"),
        "llm_error": llm_error,
        "status": "ready_for_review",
    }


def _run_image_ppt_build(
    *,
    script: Path,
    pages_raw: str,
    output_dir: Path,
    name: str,
    speaker_notes_manifest: Path | None = None,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "cyberppt",
        "image-ppt",
        "run",
        "--script",
        str(script),
        "--pages",
        pages_raw,
        "--output-dir",
        str(output_dir),
        "--name",
        name,
    ]
    if speaker_notes_manifest is not None:
        command.extend(["--speaker-notes-manifest", str(speaker_notes_manifest)])
    completed = subprocess.run(command, check=False)
    status = "completed" if completed.returncode == 0 else "failed"
    artifacts = _image_ppt_artifacts(output_dir, name)
    result = {
        "command": command,
        "returncode": completed.returncode,
        "status": status,
        "artifacts": artifacts,
    }
    if completed.returncode != 0:
        raise RuntimeError(
            f"image-ppt production build failed with exit code {completed.returncode}.\n"
            f"command: {' '.join(command)}"
        )
    return result


def run_final_script_pages(
    *,
    project: Path,
    script: Path,
    pages_raw: str,
    style_lock: Path | None = None,
    style_id: int | None = None,
    style_name: str | None = None,
    output_dir: Path | None = None,
    require_images: bool = False,
    production_build: bool = False,
) -> dict[str, Any]:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    style_lock = style_lock.expanduser().resolve() if style_lock else None
    if not script.is_file():
        raise FileNotFoundError(f"final script not found: {script}")
    if production_build:
        raise ValueError(
            "--production-build is no longer supported by final-script-pages; "
            "use python3 -m cyberppt produce assemble <project> --pages <range>."
        )
    _ensure_project_dirs(project)
    if style_lock is not None and (style_id is not None or style_name):
        raise ValueError("--style-lock cannot be combined with --style-id or --style-name")
    adopted_contract = (project / "workbench" / "analysis_expression" / "contract.json").is_file()
    if adopted_contract:
        approved_style_lock = assert_blueprint_input_ready(project, script, style_lock)
        if style_id is not None or style_name:
            raise ValueError("select and approve visual style before compiling blueprint input")
        style_lock = approved_style_lock
    elif style_lock is None:
        style_lock = write_project_style_lock(
            project=project,
            style_id=style_id,
            style_name=style_name,
            source_script=script,
        )

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

    resume_command = (
        f"python3 -m cyberppt final-script-pages {project} --script {script} "
        f"--pages {pages_raw} --style-lock {style_lock}"
    )
    production_readiness = None
    tool_consumption: dict[str, Any] = {}
    stage_name = "02-blueprint-dual-image"
    status = "ready_for_image_generation" if not require_images else "image_assets_verified"
    image_ppt_build: dict[str, Any] | None = None
    speaker_notes_build: dict[str, Any] | None = None
    image_ppt_output_dir = target_dir / "image_ppt"
    image_ppt_name = slug
    speaker_notes_build = _run_speaker_notes_build(project=project, pages_raw=pages_raw, output_dir=target_dir)
    generated_pages = [int(pair["page_number"]) for pair in manifest["pairs"]]
    skipped_pages = [int(item["page_number"]) for item in manifest.get("skipped_pages", [])]
    run_summary = {
        "schema": "cyberppt.final_script_pages_run.v1",
        "created_at": _utc_now(),
        "project": str(project),
        "source_script": str(script),
        "pages": page_numbers,
        "image_generation_pages": generated_pages,
        "template_only_pages": skipped_pages,
        "stage": stage_name,
        "status": status,
        "artifacts": {
            "compiled_deliverable_prompt": str(compiled_script),
            "imagegen_script": str(compiled_script),
            "prompt_policy_report": str(manifest["prompt_policy_report"]["path"]),
            "page_image_pairs": str(manifest_path),
            "template_text_lock": str(lock_path),
            "visual_style_lock": str(style_lock),
            "output_dir": str(target_dir),
            "image_ppt_output_dir": str(image_ppt_output_dir),
            "template_image_manifest": (
                image_ppt_build["artifacts"]["template_image_manifest"] if image_ppt_build else None
            ),
            "template_image_project": (
                image_ppt_build["artifacts"]["template_image_project"] if image_ppt_build else None
            ),
            "exported_pptx": image_ppt_build["artifacts"]["exported_pptx"] if image_ppt_build else None,
            "speaker_notes_manifest": (
                speaker_notes_build["speaker_notes_manifest"] if speaker_notes_build else None
            ),
            "speaker_notes_llm_prompt": speaker_notes_build["llm_prompt"] if speaker_notes_build else None,
        },
        "next_steps": [
            "Review or edit imagegen_script.md, then generate each full image from the compiled pair manifest full.prompt.",
            "Run python3 -m cyberppt image-ppt run to assemble the full images into a template PPTX.",
        ],
        "resume_command": resume_command,
        "rebuild": None,
        "speaker_notes_build": speaker_notes_build,
        "image_ppt_build": image_ppt_build,
        "tool_consumption": tool_consumption,
        "production_readiness": production_readiness,
    }
    summary_path = target_dir / f"{slug}_final_script_pages_run.json"
    _write_json(summary_path, run_summary)

    page_label = f"{page_numbers[0]}-{page_numbers[-1]}" if len(page_numbers) > 1 else str(page_numbers[0])
    ledger_records = [
            _artifact_record(
                stage="02-blueprint-dual-image",
                page=page_label,
                path=compiled_script,
                status="ready_for_image_generation",
                depends_on=[script, style_lock],
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
                path=Path(str(manifest["prompt_policy_report"]["path"])),
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
                path=style_lock,
                status="approved",
                depends_on=[script],
                resume_command=resume_command,
            ),
            _artifact_record(
                stage="02-blueprint-dual-image",
                page=page_label,
                path=summary_path,
                status="ready_for_image_generation",
                depends_on=[compiled_script, manifest_path, lock_path, style_lock],
                resume_command=resume_command,
            ),
        ]
    if speaker_notes_build and speaker_notes_build.get("speaker_notes_manifest"):
        ledger_records.append(
            _artifact_record(
                stage="02-blueprint-dual-image",
                page=page_label,
                path=Path(str(speaker_notes_build["speaker_notes_manifest"])),
                status="ready_for_review",
                depends_on=[Path(str(speaker_notes_build["business_script"]))],
                resume_command=resume_command,
            )
        )
    _append_ledger(project, ledger_records)
    return run_summary
