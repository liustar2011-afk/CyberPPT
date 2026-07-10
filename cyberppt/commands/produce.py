"""Project-scoped preparation and state reporting for the production workflow."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.commands.analysis_expression_gate import assert_analysis_expression_ready
from cyberppt.commands.blueprint_gate import (
    assert_blueprint_image_review_ready,
    assert_blueprint_input_ready,
    assert_speaker_notes_review_ready,
    stage_speaker_notes_review,
)
from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.commands.production_qa import render_and_compare, validate_assembly_bundle
from scripts.validate_pptx import validate_pptx


STAGE_ROOT = Path("workbench/stages/02-blueprint-dual-image")
BLUEPRINT_APPROVAL = STAGE_ROOT / "blueprint_input.approved.json"
QA_STAGE_ROOT = Path("workbench/stages/05-qa-delivery")
LEDGER_PATH = Path("workbench/artifact-ledger.json")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _project(project: Path) -> Path:
    return project.expanduser().resolve()


def _pages_slug_from_raw(pages_raw: str) -> str:
    pages: list[int] = []
    for part in pages_raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(item.strip()) for item in part.split("-", 1)]
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    pages = sorted(set(pages))
    if not pages:
        raise ValueError("at least one page is required")
    if pages == list(range(pages[0], pages[-1] + 1)):
        return f"pages_{pages[0]:03d}_{pages[-1]:03d}"
    return "pages_" + "_".join(f"{page:03d}" for page in pages)


def _stage_dir(project: Path, pages_raw: str) -> Path:
    return project / STAGE_ROOT / _pages_slug_from_raw(pages_raw)


def _assembly_report_path(project: Path, pages_raw: str) -> Path:
    prepare_path = _prepare_path(project, pages_raw)
    if prepare_path is not None:
        candidate = prepare_path.parent / "image_ppt" / "assembly_report.json"
        if candidate.is_file():
            return candidate
    candidate = _stage_dir(project, pages_raw) / "image_ppt" / "assembly_report.json"
    if candidate.is_file():
        return candidate
    if pages_raw.strip().isdigit():
        return project / STAGE_ROOT / f"pages_{int(pages_raw):03d}" / "image_ppt" / "assembly_report.json"
    return candidate


def _append_ledger(project: Path, records: list[dict[str, Any]]) -> Path:
    path = project / LEDGER_PATH
    if path.exists():
        ledger = _read_json(path)
    else:
        ledger = {"schema": "cyberppt.artifact_ledger.v1", "artifacts": []}
    artifacts = ledger.setdefault("artifacts", [])
    existing = {str(item.get("path")): item for item in artifacts if isinstance(item, dict)}
    for record in records:
        existing[str(record["path"])] = record
    ledger["artifacts"] = list(existing.values())
    return _write_json(path, ledger)


def _dependency_hashes(paths: list[Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in paths:
        resolved = path.expanduser().resolve()
        if resolved.is_file():
            hashes[str(resolved)] = _sha256(resolved)
    return hashes


def _dependencies_current(hashes: dict[str, Any]) -> bool:
    for raw_path, expected in hashes.items():
        path = Path(str(raw_path)).expanduser().resolve()
        if not path.is_file() or not isinstance(expected, str) or _sha256(path) != expected:
            return False
    return True


def _approved_blueprint_script(project: Path) -> Path:
    approval_path = project / BLUEPRINT_APPROVAL
    if not approval_path.is_file():
        raise ValueError("blueprint input approval is required")
    approval = _read_json(approval_path)
    script = Path(str(approval.get("artifact", ""))).expanduser().resolve()
    if not script.is_file():
        raise ValueError(f"approved blueprint input is missing: {script}")
    if _sha256(script) != approval.get("source_sha256"):
        raise ValueError("approved blueprint input changed; stage and approve blueprint input again")
    return script


def _prepare_path(project: Path, pages_raw: str) -> Path | None:
    for candidate in sorted((project / STAGE_ROOT).glob("*/production_prepare.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            payload = _read_json(candidate)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if payload.get("pages_raw") == pages_raw:
            return candidate
    return None


def _base_status(project: Path, pages_raw: str) -> dict[str, Any]:
    return {
        "schema": "cyberppt.production_status.v1",
        "project": str(project),
        "pages_raw": pages_raw,
        "gates": [],
        "artifacts": {},
        "failures": [],
    }


def prepare_production(project: Path, pages_raw: str) -> dict[str, Any]:
    """Compile approved production inputs and stop for speaker-notes review."""

    root = _project(project)
    assert_analysis_expression_ready(root)
    script = _approved_blueprint_script(root)
    style_lock = assert_blueprint_input_ready(root, script, None)
    prepared = run_final_script_pages(
        project=root,
        script=script,
        pages_raw=pages_raw,
        style_lock=style_lock,
        production_build=False,
    )
    notes_manifest = Path(str(prepared["artifacts"]["speaker_notes_manifest"])).resolve()
    if not notes_manifest.is_file():
        raise RuntimeError("speaker-notes manifest was not produced during preparation")
    pending = stage_speaker_notes_review(root, notes_manifest, pages_raw)
    output_dir = Path(str(prepared["artifacts"]["output_dir"])).resolve()
    prepare_path = _write_json(
        output_dir / "production_prepare.json",
        {
            "schema": "cyberppt.production_prepare.v1",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "project": str(root),
            "pages_raw": pages_raw,
            "script": str(script),
            "script_sha256": _sha256(script),
            "visual_style_lock": str(style_lock),
            "template_text_lock": prepared["artifacts"]["template_text_lock"],
            "page_image_pairs": prepared["artifacts"]["page_image_pairs"],
            "speaker_notes_manifest": str(notes_manifest),
            "speaker_notes_pending_confirmation": str(pending),
            "resume_command": f"python3 -m cyberppt produce assemble {root} --pages {pages_raw}",
        },
    )
    return {
        "schema": "cyberppt.production_prepare_result.v1",
        "status": "production_inputs_prepared",
        "next_gate": "speaker_notes_approval_required",
        "next_command": f"approve-speaker-notes-review {root} --option-id confirm_speaker_notes",
        "pages": prepared["pages"],
        "artifacts": {
            **prepared["artifacts"],
            "speaker_notes_pending_confirmation": str(pending),
            "production_prepare": str(prepare_path),
        },
    }


def get_production_status(project: Path, pages_raw: str) -> dict[str, Any]:
    """Calculate the next legal production transition from current artifacts."""

    root = _project(project)
    result = _base_status(root, pages_raw)
    try:
        assert_analysis_expression_ready(root)
    except ValueError as exc:
        result.update(status="blocked", next_gate="analysis_approval_required", next_command="analysis-expression-status")
        result["failures"].append(str(exc))
        return result
    result["gates"].append("analysis_approved")

    try:
        script = _approved_blueprint_script(root)
        style_lock = assert_blueprint_input_ready(root, script, None)
    except ValueError as exc:
        result.update(status="blocked", next_gate="blueprint_input_approval_required", next_command="stage-blueprint-input")
        result["failures"].append(str(exc))
        return result
    result["gates"].extend(("visual_style_approved", "blueprint_input_approved"))
    result["artifacts"].update({"script": str(script), "visual_style_lock": str(style_lock)})

    prepare_path = _prepare_path(root, pages_raw)
    if prepare_path is None:
        result.update(
            status="blueprint_input_approved",
            next_gate="production_inputs_prepare_required",
            next_command=f"produce prepare {root} --pages {pages_raw}",
        )
        return result
    prepared = _read_json(prepare_path)
    if prepared.get("script_sha256") != _sha256(script):
        result.update(
            status="blueprint_input_approved",
            next_gate="production_inputs_prepare_required",
            next_command=f"produce prepare {root} --pages {pages_raw}",
        )
        result["failures"].append("prepared production inputs are stale")
        return result
    result["gates"].append("production_inputs_prepared")
    result["artifacts"].update(prepared)

    try:
        notes_manifest = assert_speaker_notes_review_ready(root, pages_raw)
    except ValueError as exc:
        result.update(
            status="production_inputs_prepared",
            next_gate="speaker_notes_approval_required",
            next_command=f"approve-speaker-notes-review {root} --option-id confirm_speaker_notes",
        )
        result["failures"].append(str(exc))
        return result
    result["gates"].append("speaker_notes_approved")
    result["artifacts"]["speaker_notes_manifest"] = str(notes_manifest)
    assembly_path = _assembly_report_path(root, pages_raw)
    if assembly_path.is_file():
        assembly = _read_json(assembly_path)
        if assembly.get("valid") is True:
            readiness_path = root / QA_STAGE_ROOT / _pages_slug_from_raw(pages_raw) / "production_readiness.json"
            if readiness_path.is_file():
                readiness = _read_json(readiness_path)
                delivery_pptx = Path(str(readiness.get("delivery_pptx", ""))).expanduser().resolve()
                if (
                    readiness.get("status") == "deliverable_ready"
                    and delivery_pptx.is_file()
                    and readiness.get("delivery_pptx_sha256") == _sha256(delivery_pptx)
                    and _dependencies_current(readiness.get("dependency_hashes", {}))
                ):
                    result["gates"].extend(("blueprint_images_approved", "image_ppt_assembled", "render_qa_passed", "strict_qa_passed"))
                    result["artifacts"].update(readiness.get("artifacts", {}))
                    result.update(status="deliverable_ready", next_gate="none", next_command="")
                    return result
            result["gates"].extend(("blueprint_images_approved", "image_ppt_assembled"))
            result.update(
                status="image_ppt_assembled",
                next_gate="render_qa_required",
                next_command=f"produce verify {root} --pages {pages_raw}",
            )
            return result
    result.update(
        status="speaker_notes_approved",
        next_gate="blueprint_images_approval_required",
        next_command=f"stage-blueprint-image-review {root} --manifest {prepared['page_image_pairs']}",
    )
    return result


def assemble_production(project: Path, pages_raw: str) -> dict[str, Any]:
    """Assemble approved full images without regenerating or silently accepting missing output."""

    root = _project(project)
    status = get_production_status(root, pages_raw)
    if status.get("next_gate") == "speaker_notes_approval_required":
        assert_speaker_notes_review_ready(root, pages_raw)
    prepare_path = _prepare_path(root, pages_raw)
    if prepare_path is None:
        raise ValueError(f"production inputs are not prepared; run produce prepare {root} --pages {pages_raw}")
    prepared = _read_json(prepare_path)
    script = Path(str(prepared["script"])).resolve()
    page_manifest = Path(str(prepared["page_image_pairs"])).resolve()
    template_text_lock = Path(str(prepared["template_text_lock"])).resolve()
    notes_manifest = assert_speaker_notes_review_ready(root, pages_raw)
    pairs = _read_json(page_manifest)
    assert_blueprint_image_review_ready(root, pairs)
    pages = [int(item["page_number"]) for item in pairs.get("pairs", []) if isinstance(item, dict) and "page_number" in item]
    if not pages:
        raise ValueError("prepared page image manifest contains no pages")
    output_dir = prepare_path.parent / "image_ppt"
    name = prepare_path.parent.name
    command = [
        sys.executable,
        "-m",
        "cyberppt",
        "image-ppt",
        "--project",
        str(root),
        "run",
        "--project-production",
        "--script",
        str(script),
        "--pages",
        pages_raw,
        "--template-text-lock",
        str(template_text_lock),
        "--page-image-manifest",
        str(page_manifest),
        "--speaker-notes-manifest",
        str(notes_manifest),
        "--output-dir",
        str(output_dir),
        "--name",
        name,
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"image-ppt assembly failed with exit code {completed.returncode}")
    project_dir = output_dir / f"{name}_template_image_project"
    exports = sorted((project_dir / "exports").glob("*.pptx"))
    exported_pptx = exports[-1] if exports else output_dir / "missing.pptx"
    approved_images = {
        int(pair["page_number"]): str(Path(str(pair["full"]["path"])).resolve())
        for pair in pairs.get("pairs", [])
        if isinstance(pair, dict) and isinstance(pair.get("full"), dict) and "page_number" in pair
    }
    bundle = {
        "project": str(root),
        "exported_pptx": str(exported_pptx),
        "template_image_manifest": str(output_dir / "template_image_manifest.json"),
        "approved_images": approved_images,
    }
    report = validate_assembly_bundle(bundle, pages)
    report["command"] = command
    report_path = _write_json(output_dir / "assembly_report.json", report)
    if not report["valid"]:
        raise RuntimeError("assembly_artifact_missing: " + ", ".join(report["failures"]))
    return {
        "schema": "cyberppt.production_assemble_result.v1",
        "status": "image_ppt_assembled",
        "next_gate": "render_qa_required",
        "next_command": f"produce verify {root} --pages {pages_raw}",
        "artifacts": {**bundle, "assembly_report": str(report_path)},
    }


def _approved_images_from_assembly(assembly: dict[str, Any]) -> dict[int, Path]:
    approved: dict[int, Path] = {}
    for page, path in assembly.get("approved_images", {}).items():
        approved[int(page)] = Path(str(path)).expanduser().resolve()
    return approved


def _assert_current_assembly(assembly: dict[str, Any]) -> tuple[Path, Path]:
    artifacts = assembly.get("artifacts") if isinstance(assembly.get("artifacts"), dict) else {}
    pptx = Path(str(artifacts.get("exported_pptx", ""))).expanduser().resolve()
    manifest = Path(str(artifacts.get("template_image_manifest", ""))).expanduser().resolve()
    if assembly.get("valid") is not True:
        raise RuntimeError("assembly is not valid")
    if not pptx.is_file() or not manifest.is_file():
        raise RuntimeError("assembly artifact missing")
    expected_hashes = assembly.get("artifacts_sha256") if isinstance(assembly.get("artifacts_sha256"), dict) else {}
    for key, path in (("exported_pptx", pptx), ("template_image_manifest", manifest)):
        expected = expected_hashes.get(key)
        if expected and expected != _sha256(path):
            raise RuntimeError(f"stale assembly: {key} changed since assembly_report.json")
    return pptx, manifest


def _assert_current_speaker_notes(project: Path, pages_raw: str, template_manifest: Path) -> Path:
    notes_manifest = assert_speaker_notes_review_ready(project, pages_raw)
    template = _read_json(template_manifest)
    recorded = template.get("speaker_notes_manifest")
    if recorded is not None and Path(str(recorded)).expanduser().resolve() != notes_manifest:
        raise RuntimeError("speaker notes approval does not match the assembled manifest")
    return notes_manifest


def _template_text_lock_record(template_manifest: Path) -> dict[str, Any] | None:
    template = _read_json(template_manifest)
    raw_path = template.get("template_text_lock")
    if not raw_path:
        return None
    path = Path(str(raw_path)).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"template text lock is missing: {path}")
    return {"path": str(path), "sha256": _sha256(path)}


def _template_text_requirements(template_manifest: Path, pages: list[int]) -> dict[int, list[str]]:
    template = _read_json(template_manifest)
    raw_path = template.get("template_text_lock")
    if not raw_path:
        return {}
    lock = _read_json(Path(str(raw_path)).expanduser().resolve())
    requirements: dict[int, list[str]] = {page: [] for page in pages}
    for record in lock.get("records", []):
        if not isinstance(record, dict):
            continue
        page = int(record.get("page", 0) or 0)
        if page not in requirements:
            continue
        for field in ("title", "subtitle"):
            value = str(record.get(field) or "").strip()
            if value:
                requirements[page].append(value)
    return requirements


def _full_image_delivery_manifest(
    *,
    project: Path,
    pages: list[int],
    template_manifest: Path,
    approved_images: dict[int, Path],
    visual_report: dict[str, Any],
    visual_report_path: Path,
) -> dict[str, Any]:
    template = _read_json(template_manifest)
    template_text_lock = _template_text_lock_record(template_manifest)
    native_text_requirements = _template_text_requirements(template_manifest, pages)
    tasks = {
        int(item["page_number"]): item
        for item in template.get("tasks", [])
        if isinstance(item, dict) and isinstance(item.get("page_number"), int)
    }
    return {
        "schema": "cyberppt.full_image_delivery_manifest.v1",
        "delivery_mode": "full_image_ppt",
        "body_content_editable": False,
        "template_text_editable": True,
        "speaker_notes_required": True,
        "project": str(project),
        "template_image_manifest": str(template_manifest),
        "template_text_lock": template_text_lock,
        "production_visual_report": {"path": str(visual_report_path), "passed": visual_report.get("passed") is True},
        "slides": [
            {
                "slide": index,
                "source_page": page,
                "delivery_mode": "full_image_ppt",
                "native_text_requirements": native_text_requirements.get(page, []),
                "image_assets": [{"role": "approved_full_image", "path": str(approved_images[page])}],
                "notes_present": bool(str(tasks.get(page, {}).get("notes_text") or "").strip()),
            }
            for index, page in enumerate(pages, start=1)
        ],
    }


def verify_production(project: Path, pages_raw: str) -> dict[str, Any]:
    """Run render, visual, strict, and delivery promotion gates for an assembled PPTX."""

    root = _project(project)
    assembly_path = _assembly_report_path(root, pages_raw)
    if not assembly_path.is_file():
        raise ValueError(f"image PPT assembly is required; run produce assemble {root} --pages {pages_raw}")
    assembly = _read_json(assembly_path)
    pptx, template_manifest = _assert_current_assembly(assembly)
    notes_manifest = _assert_current_speaker_notes(root, pages_raw, template_manifest)
    approved_images = _approved_images_from_assembly(assembly)
    pages = sorted(approved_images)
    if not pages:
        raise RuntimeError("assembly has no approved images")

    qa_dir = root / QA_STAGE_ROOT / _pages_slug_from_raw(pages_raw)
    visual_report = render_and_compare(pptx, template_manifest, approved_images, pages, qa_dir)
    visual_report_path = qa_dir / "production_visual_report.json"
    if not visual_report_path.is_file():
        _write_json(visual_report_path, visual_report)
    if visual_report.get("passed") is not True:
        raise RuntimeError("render_qa_failed: " + ", ".join(visual_report.get("failures", [])))

    delivery_manifest = _full_image_delivery_manifest(
        project=root,
        pages=pages,
        template_manifest=template_manifest,
        approved_images=approved_images,
        visual_report=visual_report,
        visual_report_path=visual_report_path,
    )
    delivery_manifest_path = _write_json(qa_dir / "full_image_delivery_manifest.json", delivery_manifest)
    strict_report = validate_pptx(pptx, manifest_path=delivery_manifest_path, strict=True)
    strict_report_path = _write_json(qa_dir / "strict_validation_report.json", strict_report)
    if strict_report.get("errors"):
        raise RuntimeError("strict_qa_failed: " + ", ".join(str(item.get("code")) for item in strict_report["errors"]))

    delivery_dir = root / "delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    delivery_pptx = delivery_dir / f"{root.name}_{_pages_slug_from_raw(pages_raw)}.pptx"
    shutil.copy2(pptx, delivery_pptx)
    dependencies = [
        assembly_path,
        pptx,
        template_manifest,
        notes_manifest,
        visual_report_path,
        strict_report_path,
        delivery_manifest_path,
        *approved_images.values(),
    ]
    template_text_lock = _template_text_lock_record(template_manifest)
    if template_text_lock is not None:
        dependencies.append(Path(template_text_lock["path"]))
    readiness = {
        "schema": "cyberppt.production_readiness.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "deliverable_ready",
        "project": str(root),
        "pages_raw": pages_raw,
        "assembly_report": str(assembly_path),
        "delivery_pptx": str(delivery_pptx),
        "delivery_pptx_sha256": _sha256(delivery_pptx),
        "dependency_hashes": _dependency_hashes(dependencies),
        "artifacts": {
            "production_visual_report": str(visual_report_path),
            "strict_validation_report": str(strict_report_path),
            "full_image_delivery_manifest": str(delivery_manifest_path),
            "delivery_pptx": str(delivery_pptx),
        },
    }
    readiness_path = _write_json(qa_dir / "production_readiness.json", readiness)
    _append_ledger(
        root,
        [
            {
                "stage": "05-qa-delivery",
                "page": pages_raw,
                "path": str(delivery_pptx),
                "status": "deliverable_ready",
                "sha256": readiness["delivery_pptx_sha256"],
                "depends_on": [str(assembly_path), str(visual_report_path), str(strict_report_path)],
                "updated_at": readiness["created_at"],
                "resume_command": f"python3 -m cyberppt produce status {root} --pages {pages_raw} --json",
            }
        ],
    )
    return {**readiness, "production_readiness": str(readiness_path), "next_gate": "none", "next_command": ""}
