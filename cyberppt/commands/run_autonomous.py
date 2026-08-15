"""Fail-closed orchestration for an explicitly authorized lightweight run."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from cyberppt.artifact_ledger import write_json_atomic
from cyberppt.autonomous_contract import AutonomousContract, load_contract, validate_source_boundary
from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.commands.outline_audit import run_outline_audit
from cyberppt.commands.script_audit import run_script_audit
from cyberppt.commands.source_truth_audit import run_source_truth_audit
from cyberppt.commands.visual_structure_stage import (
    VISUAL_FILES,
    execute_visual_structure_stage,
    prepare_visual_structure_stage,
    record_visual_structure_execution,
    run_visual_structure_audit,
)
from cyberppt.semantic_understanding import run_semantic_understanding_audit
from cyberppt.source_document_map import prepare_source_map, run_source_map_audit
from cyberppt.stage02_handoff import audit_stage02_handoff, prepare_stage02_handoff
from cyberppt.script_quality_contract import parse_script_path
from cyberppt.stage01_compiler import compile_source_truth
from scripts.imagegen_pipeline.page_manifest import output_variants_for_mode


REPORT_PATH = "workbench/stages/00-autonomous/run-report.json"
OUTLINE_PATH = "workbench/stages/01-analysis/outline.json"
SOURCE_TRUTH_PATH = "workbench/stages/01-analysis/source-truth.json"
DRAFTS_DIR = "workbench/scripts/drafts"
FINAL_SCRIPT_PATH = "workbench/scripts/final/script-final.md"


class GateBlocked(RuntimeError):
    def __init__(self, gate: str, message: str, artifact: Path | None = None):
        super().__init__(message)
        self.gate = gate
        self.artifact = artifact


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateBlocked("authoring-coverage", f"invalid JSON: {path}: {exc.msg}", path) from exc
    if not isinstance(payload, dict):
        raise GateBlocked("authoring-coverage", f"JSON root must be object: {path}", path)
    return payload


def _require_passed(
    gates: list[dict[str, Any]],
    name: str,
    result: tuple[int, dict[str, Any]] | dict[str, Any],
    artifact: Path,
) -> None:
    if isinstance(result, tuple):
        code, report = result
    else:
        code, report = 0, result
    status = report.get("status") if isinstance(report, dict) else None
    if code != 0 or status != "passed":
        raise GateBlocked(name, f"{name} did not pass (status={status!r}, exit_code={code})", artifact)
    gates.append({"name": name, "status": "passed", "artifact": str(artifact)})


def _assert_page_authoring(project: Path) -> Path:
    outline_path = project / OUTLINE_PATH
    drafts_dir = project / DRAFTS_DIR
    if not outline_path.is_file() or not drafts_dir.is_dir():
        raise GateBlocked(
            "page-authoring",
            "authored Outline or Markdown page drafts are missing",
            drafts_dir,
        )
    outline = _read_json(outline_path)
    if outline.get("editorial_authoring_mode") != "author_driven" or outline.get("editorial_authoring_status") != "author_edited":
        raise GateBlocked("outline-authoring", "candidate Outline cannot enter autonomous production; author editing is required", outline_path)
    pages = outline.get("pages")
    if not isinstance(pages, list):
        raise GateBlocked("page-authoring", "Outline pages have invalid shape", outline_path)
    expected = {
        str(page.get("page_id"))
        for page in pages
        if isinstance(page, dict) and page.get("page_type") == "content"
    }
    authored: dict[str, object] = {}
    for draft in sorted(drafts_dir.glob("*.md")):
        document = parse_script_path(draft)
        for page in document.pages:
            if page.page_id in authored:
                raise GateBlocked(
                    "page-authoring",
                    f"duplicate authored Markdown page: {page.page_id}",
                    draft,
                )
            authored[page.page_id] = page
    missing = sorted(page_id for page_id in expected if page_id not in authored)
    if missing:
        raise GateBlocked(
            "page-authoring",
            f"content pages lack professional Markdown drafts: {', '.join(missing)}",
            drafts_dir,
        )
    for page_id in expected:
        page = authored.get(page_id)
        required = (
            "full_prose",
            "onscreen_text",
            "visual_structure",
            "speaker_notes",
            "selection_notes",
            "evidence_map",
        )
        if page is None or any(not str(getattr(page, field, "")).strip() for field in required):
            raise GateBlocked(
                "page-authoring",
                f"{page_id} lacks a complete professional Markdown page script",
                drafts_dir,
            )
    return drafts_dir


def _expected_content_page_numbers(script: Path) -> set[int]:
    return {
        page.sequence
        for page in parse_script_path(script).pages
        if page.page_type == "content"
    }


def _assert_actual_send(
    *,
    manifest_path: Path,
    pair: dict[str, Any],
    variant: str,
) -> None:
    page_number = int(pair.get("page_number") or 0)
    item = pair.get(variant)
    if not isinstance(item, dict):
        raise GateBlocked("prompt-proof", f"page {page_number} {variant} manifest entry is missing", manifest_path)
    expected_base_hash = str(item.get("prompt_sha256") or "")
    if not expected_base_hash:
        raise GateBlocked("prompt-proof", f"page {page_number} {variant} lacks a prompt hash", manifest_path)
    attempts = manifest_path.parent / "prompts" / "attempts"
    request_paths = sorted(attempts.glob(f"page-{page_number:03d}-{variant}-attempt-*-request.json"))
    matched = False
    for request_path in request_paths:
        request = _read_json(request_path)
        sent = Path(str(request.get("prompt_path") or ""))
        if not sent.is_file():
            continue
        actual_hash = sha256(sent.read_bytes()).hexdigest()
        if str(request.get("prompt_sha256") or "") != actual_hash:
            continue
        if str(request.get("base_prompt_sha256") or "") != expected_base_hash:
            continue
        if str(request.get("model") or "") != "gpt-image-2" or not str(request.get("quality") or "").strip():
            continue
        if variant != "full":
            full_path = Path(str((pair.get("full") or {}).get("path") or "")).resolve()
            inputs = {Path(str(value)).resolve() for value in request.get("input_images") or []}
            if full_path not in inputs:
                continue
        matched = True
        break
    if not matched:
        raise GateBlocked(
            "prompt-proof",
            f"page {page_number} {variant} lacks a hash-bound actual ImageGen send record",
            manifest_path,
        )


def _assert_production_proof(contract: AutonomousContract, result: dict[str, Any]) -> Path:
    artifacts = result.get("artifacts") if isinstance(result.get("artifacts"), dict) else {}
    manifest_path = Path(str(artifacts.get("page_image_pairs") or "")).expanduser()
    if not manifest_path.is_file():
        raise GateBlocked("image-production", "page image manifest is missing", manifest_path)
    manifest = _read_json(manifest_path)
    if manifest.get("production_mode") != contract.production_mode:
        raise GateBlocked("image-production", "image manifest production mode differs from contract", manifest_path)
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise GateBlocked("image-production", "page image manifest has no page pairs", manifest_path)
    expected_pages = _expected_content_page_numbers(contract.project / FINAL_SCRIPT_PATH)
    actual_pages = {
        int(pair.get("page_number"))
        for pair in pairs
        if isinstance(pair, dict) and isinstance(pair.get("page_number"), int)
    }
    if actual_pages != expected_pages:
        raise GateBlocked(
            "image-production",
            f"image manifest pages {sorted(actual_pages)} do not match content pages {sorted(expected_pages)}",
            manifest_path,
        )
    variants = output_variants_for_mode(contract.production_mode)
    for pair in pairs:
        if not isinstance(pair, dict):
            raise GateBlocked("image-production", "page image manifest contains invalid pair", manifest_path)
        for variant in variants:
            item = pair.get(variant)
            path = Path(str(item.get("path") or "")) if isinstance(item, dict) else Path()
            if not isinstance(item, dict) or item.get("status") != "Generated" or not path.is_file():
                raise GateBlocked("image-production", f"page {pair.get('page_number')} {variant} image is not generated", manifest_path)
        if contract.require_image_qa:
            full = pair.get("full")
            if not isinstance(full, dict) or (full.get("text_audit") or {}).get("valid") is not True:
                raise GateBlocked("image-qa", f"page {pair.get('page_number')} full image lacks passed text QA", manifest_path)
    if contract.require_prompt_files:
        visual_prompts = contract.project / "visual" / "generation-prompts.md"
        if not visual_prompts.is_file():
            raise GateBlocked("prompt-proof", "generated visual prompts or actual sent prompts are missing", manifest_path)
        for pair in pairs:
            if isinstance(pair, dict):
                for variant in variants:
                    _assert_actual_send(manifest_path=manifest_path, pair=pair, variant=variant)
    readiness = result.get("production_readiness")
    readiness_path = Path(str(artifacts.get("delivery_readiness") or "")).expanduser()
    if (
        not isinstance(readiness, dict)
        or readiness.get("status") != "production_ready"
        or readiness.get("valid") is not True
    ):
        raise GateBlocked(
            "image-to-editable-svg",
            "image-to-editable-svg production did not reach production_ready",
            readiness_path,
        )
    if not readiness_path.is_file():
        raise GateBlocked(
            "image-to-editable-svg",
            "image-to-editable-svg delivery readiness report is missing",
            readiness_path,
        )
    delivery_readiness = _read_json(readiness_path)
    if (
        delivery_readiness.get("status") != "production_ready"
        or (delivery_readiness.get("delivery_readiness") or {}).get("valid") is not True
    ):
        raise GateBlocked(
            "image-to-editable-svg",
            "image-to-editable-svg delivery readiness did not pass QA",
            readiness_path,
        )
    exported_pptx = artifacts.get("exported_pptx")
    if not exported_pptx or not Path(str(exported_pptx)).is_file():
        raise GateBlocked(
            "image-to-editable-svg",
            "image-to-editable-svg production has no verified exported PPTX",
            readiness_path,
        )
    return manifest_path


def _pages_raw(script: Path) -> str:
    document = parse_script_path(script)
    numbers = [page.sequence for page in document.pages]
    if not numbers:
        raise GateBlocked("script-audit", "final script has no pages", script)
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        raise GateBlocked("script-audit", f"final script pages are not continuous from p01: {numbers}", script)
    return f"1-{numbers[-1]}"


def _report_path(contract: AutonomousContract) -> Path:
    return contract.project / REPORT_PATH


def _write_report(path: Path, report: dict[str, Any]) -> dict[str, Any]:
    report["report_path"] = str(path)
    write_json_atomic(path, report)
    return report


def run_autonomous(
    contract_path: Path,
    *,
    generate_images: bool = True,
    image_timeout: int = 600,
    resume: bool = False,
) -> tuple[int, dict[str, Any]]:
    """Run existing deterministic gates in order and never skip a failed gate.

    Content authoring remains an explicit input to the runner: the command
    deliberately refuses candidate Outline, absent page authoring, unexecuted
    visual decisions, and missing ImageGen proof instead of fabricating them.
    An autonomous contract authorizes deterministic verification while keeping
    the current full-script audit as the sole content precondition for Stage 02.
    """

    contract = load_contract(contract_path)
    report_path = _report_path(contract)
    gates: list[dict[str, Any]] = []
    script = contract.project / FINAL_SCRIPT_PATH
    try:
        validate_source_boundary(contract)
        gates.append({"name": "source-boundary", "status": "passed", "artifact": str(contract.project / "source")})
        prepare_source_map(contract.project)
        _require_passed(gates, "source-map-check", run_source_map_audit(contract.project), contract.project / "workbench/stages/00-source-map/source-map-audit.json")
        _require_passed(gates, "semantic-check", run_semantic_understanding_audit(contract.project), contract.project / "workbench/stages/00-semantic-understanding/semantic-understanding.md")
        compile_source_truth(contract.project)
        _require_passed(gates, "source-truth-audit", run_source_truth_audit(contract.project, contract.project / SOURCE_TRUTH_PATH), contract.project / SOURCE_TRUTH_PATH)
        _require_passed(gates, "outline-audit", run_outline_audit(contract.project, contract.project / OUTLINE_PATH, source_truth_path=contract.project / SOURCE_TRUTH_PATH), contract.project / OUTLINE_PATH)
        authoring = _assert_page_authoring(contract.project)
        gates.append({"name": "page-authoring", "status": "passed", "artifact": str(authoring)})
        _require_passed(gates, "script-audit", run_script_audit(contract.project, script), script)
        validate_source_boundary(contract)
        _require_passed(
            gates,
            "stage02-handoff",
            prepare_stage02_handoff(
                contract.project,
                script=script,
                reuse_current_handoff=True,
            ),
            contract.project / "workbench/stages/02-handoff/stage02-handoff.json",
        )
        _require_passed(gates, "stage02-handoff-check", audit_stage02_handoff(contract.project), contract.project / "workbench/stages/02-handoff/stage02-handoff-audit.json")
        invocation = prepare_visual_structure_stage(
            contract.project,
            script,
            reuse_current_handoff=True,
        )
        gates.append({"name": "visual-structure-prepare", "status": "passed", "artifact": str(invocation)})
        decisions = contract.project / VISUAL_FILES["decisions"]
        if not decisions.is_file():
            raise GateBlocked(
                "visual-structure-authoring",
                "visual-design-decisions.json is missing; execute the registered visual structure Skill before resuming",
                decisions,
            )
        executed = execute_visual_structure_stage(contract.project, script)
        receipt = record_visual_structure_execution(
            contract.project,
            script,
            executor="codex-desktop",
            model="gpt-5.6",
            note="Executed under the explicit autonomous contract after authoring the visual decision package.",
        )
        gates.append({"name": "visual-structure-execution", "status": "passed", "artifact": str(receipt)})
        _require_passed(
            gates,
            "visual-structure-audit",
            run_visual_structure_audit(contract.project, script),
            contract.project / VISUAL_FILES["validation"],
        )
        if contract.require_images and not generate_images:
            raise GateBlocked("image-production", "contract requires image generation; rerun without --skip-image-generation", script)
        if contract.require_images:
            try:
                production = run_final_script_pages(
                    project=contract.project,
                    script=script,
                    pages_raw=_pages_raw(script),
                    style_id=contract.style_id,
                    production_mode=contract.production_mode,
                    generate_images=True,
                    require_images=True,
                    image_timeout=image_timeout,
                    autonomous_contract=contract.path,
                    production_build=True,
                )
            except (FileNotFoundError, PermissionError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
                raise GateBlocked(
                    "image-production",
                    str(exc),
                    contract.project / "workbench/stages/02-imagegen",
                ) from exc
            manifest = _assert_production_proof(contract, production)
            gates.append({"name": "image-production", "status": "passed", "artifact": str(manifest)})
        report = {
            "schema": "cyberppt.run_autonomous.v1",
            "status": "completed",
            "project": str(contract.project),
            "contract": str(contract.path),
            "resume": resume,
            "gates": gates,
            "artifacts": {"final_script": str(script), "production_manifest": str(manifest) if contract.require_images else None},
        }
        return 0, _write_report(report_path, report)
    except GateBlocked as exc:
        report = {
            "schema": "cyberppt.run_autonomous.v1",
            "status": "failed",
            "project": str(contract.project),
            "contract": str(contract.path),
            "resume": resume,
            "gates": gates,
            "failed_gate": exc.gate,
            "blocking_artifact": str(exc.artifact) if exc.artifact else None,
            "message": str(exc),
        }
        return 1, _write_report(report_path, report)
    except (FileNotFoundError, PermissionError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        report = {
            "schema": "cyberppt.run_autonomous.v1",
            "status": "failed",
            "project": str(contract.project),
            "contract": str(contract.path),
            "resume": resume,
            "gates": gates,
            "failed_gate": gates[-1]["name"] if gates else "contract",
            "blocking_artifact": None,
            "message": str(exc),
        }
        return 1, _write_report(report_path, report)
