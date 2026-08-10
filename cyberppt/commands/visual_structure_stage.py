"""Register and gate the visual-structure-designer stage."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.artifact_ledger import append_artifacts, write_json_atomic
from cyberppt.semantic_digest import script_semantic_digest
from cyberppt.visual_structure_contract import (
    audit_visual_design_package,
    prompt_contract_hashes,
    skill_bundle_sha256,
)


SKILL_RELATIVE = Path("vendor/skills/ppt-visual-structure-designer")
VISUAL_FILES = {
    "design_input": Path("visual/visual-design-input.json"),
    "skill_request": Path("visual/skill-request.json"),
    "skill_invocation": Path("visual/skill-invocation.md"),
    "decisions": Path("visual/visual-design-decisions.json"),
    "execution_receipt": Path("visual/execution-receipt.json"),
    "spec_json": Path("visual/deck-visual-spec.json"),
    "spec_markdown": Path("visual/script-visual-structure.md"),
    "generation_prompts": Path("visual/generation-prompts.md"),
    "validation": Path("visual/validation-report.json"),
}


def _write_visual_design_input(project: Path, handoff: Path) -> Path:
    payload = _read_json(handoff)
    source_pages = payload.get("pages") or []
    content_pages = [page for page in source_pages if page.get("render_role") == "content"]
    pages: list[dict[str, Any]] = []
    for index, page in enumerate(content_pages):
        visual = page.get("stage02_visual_input") or {}
        previous_page = content_pages[index - 1] if index else None
        next_page = content_pages[index + 1] if index + 1 < len(content_pages) else None
        pages.append(
            {
                "page_id": page.get("page_id"),
                "page_number": page.get("page_number"),
                "page_title": page.get("title"),
                "argument_role": page.get("argument_role"),
                "page_mission": page.get("page_mission"),
                "core_judgment": page.get("core_message"),
                "semantic_context": page.get("full_prose"),
                "locked_on_screen_text": page.get("onscreen_text"),
                "locked_on_screen_items": page.get("onscreen_items") or [],
                "locked_text_items": visual.get("locked_text_items") or [],
                "business_relationships": visual.get("business_relationships") or [],
                "relationship_authority": "business_relationships",
                "author_visual_notes": visual.get("author_visual_notes") or "",
                "author_visual_notes_authority": "advisory_only",
                "source_refs": page.get("source_refs") or [],
                "must_not_include": page.get("must_not_include") or [],
                "body_image_canvas": visual.get("body_image_canvas"),
                "title_render_mode": visual.get("title_render_mode"),
                "subtitle_render_mode": visual.get("subtitle_render_mode"),
                "previous_content_page": (
                    {"page_id": previous_page.get("page_id"), "title": previous_page.get("title")}
                    if previous_page
                    else None
                ),
                "next_content_page": (
                    {"page_id": next_page.get("page_id"), "title": next_page.get("title")}
                    if next_page
                    else None
                ),
            }
        )
    output = project / VISUAL_FILES["design_input"]
    write_json_atomic(
        output,
        {
            "schema": "cyberppt.visual_design_input.v2",
            "source": str(handoff),
            "source_sha256": _sha256(handoff),
            "content_lock": "strict",
            "style_policy": "visual structure must not select or embed a visual style",
            "relationship_policy": (
                "business_relationships is authoritative; author_visual_notes is advisory only "
                "and must never be copied into decision_relationship"
            ),
            "decision_policy": (
                "ppt-visual-structure-designer must compare at least three materially different "
                "candidates per page; deterministic keyword routing is not authoritative"
            ),
            "pages": pages,
        },
    )
    return output


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def visual_structure_required(project: Path) -> bool:
    manifest = project / "manifest.yml"
    if not manifest.is_file():
        return False
    text = manifest.read_text(encoding="utf-8-sig")
    return "visual_structure_designer: required" in text


def _skill_root() -> Path:
    return (Path(__file__).resolve().parents[2] / SKILL_RELATIVE).resolve()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_skill_request(project: Path, script: Path, design_input: Path) -> Path:
    skill_root = _skill_root()
    contracts = prompt_contract_hashes(skill_root)
    output = project / VISUAL_FILES["skill_request"]
    write_json_atomic(
        output,
        {
            "schema": "cyberppt.visual_structure_skill_request.v1",
            "skill": "ppt-visual-structure-designer",
            "skill_root": str(skill_root),
            "skill_bundle_sha256": contracts["skill_bundle"],
            "skill_contract_sha256": contracts,
            "approved_script": str(script),
            "approved_script_sha256": _sha256(script),
            "approved_script_semantic_sha256": script_semantic_digest(script),
            "visual_design_input": str(design_input),
            "visual_design_input_sha256": _sha256(design_input),
            "content_lock": "strict",
            "relationship_authority": "business_relationships",
            "author_visual_notes_authority": "advisory_only",
            "required_outputs": [
                VISUAL_FILES["decisions"].as_posix(),
                VISUAL_FILES["spec_json"].as_posix(),
                VISUAL_FILES["spec_markdown"].as_posix(),
            ],
            "forbidden_outputs": ["image", "svg", "html", "pptx"],
            "prepared_at": _utc_now(),
        },
    )
    return output


def prepare_visual_structure_stage(project: Path, script: Path) -> Path:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    from cyberppt.stage02_handoff import HANDOFF_JSON, prepare_stage02_handoff

    report = prepare_stage02_handoff(project, script=script)
    if report.get("status") != "passed":
        raise ValueError("Stage 01 to Stage 02 handoff is not passed")
    handoff = project / HANDOFF_JSON
    design_input = _write_visual_design_input(project, handoff)
    skill_root = _skill_root()
    skill = skill_root / "SKILL.md"
    if not skill.is_file():
        raise FileNotFoundError(f"registered visual structure skill is missing: {skill}")
    skill_request = _write_skill_request(project, script, design_input)
    output = project / VISUAL_FILES["skill_invocation"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(
            [
                "# PPT Visual Structure Designer Invocation",
                "",
                "- skill: ppt-visual-structure-designer",
                f"- skill_path: {skill}",
                f"- skill_sha256: {_sha256(skill)}",
                f"- skill_bundle_sha256: {skill_bundle_sha256(skill_root)}",
                f"- approved_script: {script}",
                f"- approved_script_sha256: {_sha256(script)}",
                f"- approved_script_semantic_sha256: {script_semantic_digest(script)}",
                f"- stage02_handoff: {handoff}",
                f"- visual_design_input: {design_input}",
                f"- skill_request: {skill_request}",
                "- mode: workbench-handoff",
                "- content_lock: strict",
                "",
                "## Required action",
                "",
                "Invoke the registered skill in the current execution surface. Use visual-design-input.json, derived only from stage02_handoff.json, as the visual-design interface. Treat business_relationships as authoritative and author_visual_notes as advisory only. Do not read or reuse any existing Stage 02 visual/ or workbench/prompts/imagegen outputs as authority. Generate and compare at least three materially different candidates per content page; deterministic keyword matching must not choose the final visual intent or carrier. Preserve the approved page set, locked text ids and locked text, and write:",
                "",
                "- `visual/visual-design-decisions.json`",
                "- `visual/deck-visual-spec.json`",
                "- `visual/script-visual-structure.md`",
                "",
                "After the Skill has actually produced these files, record the execution with `python -m cyberppt record-visual-structure-execution <project> --script <script> --executor <surface> --model <model>`, then run `visual-structure-audit`. The audit, not the Skill, rebuilds generation-prompts.md from the current validated package.",
                "",
                "Do not select a visual style, generate images, SVG, HTML, or PPTX in this stage.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return output


def record_visual_structure_execution(
    project: Path,
    script: Path,
    *,
    executor: str,
    model: str,
    note: str = "",
) -> Path:
    """Record a completed, externally executed Skill run with current hashes."""

    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    if not executor.strip() or not model.strip():
        raise ValueError("executor and model are required for the visual structure execution receipt")
    skill_root = _skill_root()
    design_input = project / VISUAL_FILES["design_input"]
    request_path = project / VISUAL_FILES["skill_request"]
    artifact_paths = {
        key: project / VISUAL_FILES[key]
        for key in ("decisions", "spec_json", "spec_markdown")
    }
    for path in (script, design_input, request_path, *artifact_paths.values()):
        if not path.is_file():
            raise FileNotFoundError(f"visual structure execution artifact is missing: {path}")
    request = _read_json(request_path)
    contracts = prompt_contract_hashes(skill_root)
    if request.get("visual_design_input_sha256") != _sha256(design_input):
        raise ValueError("visual structure skill request is stale for visual-design-input.json")
    if request.get("skill_bundle_sha256") != contracts["skill_bundle"]:
        raise ValueError("visual structure skill request is stale for the current registered Skill")
    design_payload = _read_json(design_input)
    page_ids = [str(item.get("page_id") or "") for item in design_payload.get("pages") or [] if isinstance(item, dict)]
    output = project / VISUAL_FILES["execution_receipt"]
    write_json_atomic(
        output,
        {
            "schema": "cyberppt.visual_structure_execution_receipt.v1",
            "skill": "ppt-visual-structure-designer",
            "executor": executor.strip(),
            "model": model.strip(),
            "skill_request": str(request_path),
            "skill_request_sha256": _sha256(request_path),
            "skill_bundle_sha256": contracts["skill_bundle"],
            "skill_contract_sha256": contracts,
            "approved_script": str(script),
            "approved_script_semantic_sha256": script_semantic_digest(script),
            "visual_design_input": str(design_input),
            "visual_design_input_sha256": _sha256(design_input),
            "page_ids": page_ids,
            "artifact_sha256": {key: _sha256(path) for key, path in artifact_paths.items()},
            "executed_at": _utc_now(),
            "note": note.strip(),
        },
    )
    return output


def _audit_execution_receipt(
    project: Path,
    script: Path,
    skill_root: Path,
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []

    def issue(code: str, message: str) -> None:
        issues.append({"code": code, "message": message})

    receipt_path = project / VISUAL_FILES["execution_receipt"]
    if not receipt_path.is_file():
        return {
            "schema": "cyberppt.visual_structure_execution_audit.v1",
            "status": "failed",
            "blocking_issues": [{"code": "EXECUTION_RECEIPT_MISSING", "message": f"Missing execution receipt: {receipt_path}"}],
        }
    receipt = _read_json(receipt_path)
    request_path = project / VISUAL_FILES["skill_request"]
    design_input = project / VISUAL_FILES["design_input"]
    contracts = prompt_contract_hashes(skill_root)
    expected = {
        "skill_request_sha256": _sha256(request_path),
        "skill_bundle_sha256": contracts["skill_bundle"],
        "approved_script_semantic_sha256": script_semantic_digest(script),
        "visual_design_input_sha256": _sha256(design_input),
    }
    if receipt.get("schema") != "cyberppt.visual_structure_execution_receipt.v1":
        issue("EXECUTION_RECEIPT_SCHEMA_INVALID", "Visual structure execution receipt schema is invalid.")
    for field in ("executor", "model", "executed_at"):
        if not str(receipt.get(field) or "").strip():
            issue("EXECUTION_RECEIPT_FIELD_MISSING", f"Execution receipt is missing {field}.")
    for field, value in expected.items():
        if receipt.get(field) != value:
            issue("EXECUTION_RECEIPT_STALE", f"Execution receipt {field} is stale.")
    receipt_contracts = receipt.get("skill_contract_sha256")
    if receipt_contracts != contracts:
        issue("EXECUTION_RECEIPT_CONTRACT_STALE", "Execution receipt is not bound to the current Skill contract files.")
    receipt_artifacts = receipt.get("artifact_sha256") if isinstance(receipt.get("artifact_sha256"), dict) else {}
    for key in ("decisions", "spec_json", "spec_markdown"):
        path = project / VISUAL_FILES[key]
        if not path.is_file() or receipt_artifacts.get(key) != _sha256(path):
            issue("EXECUTION_ARTIFACT_STALE", f"Execution receipt does not match {path}.")
    input_pages = [
        str(item.get("page_id") or "")
        for item in _read_json(design_input).get("pages") or []
        if isinstance(item, dict)
    ]
    if receipt.get("page_ids") != input_pages:
        issue("EXECUTION_PAGE_SET_STALE", "Execution receipt page_ids differ from visual-design-input.json.")
    return {
        "schema": "cyberppt.visual_structure_execution_audit.v1",
        "status": "passed" if not issues else "failed",
        "blocking_issues": issues,
    }


def _prompt_inputs_sha256(project: Path, script: Path, skill_root: Path) -> dict[str, str]:
    contracts = prompt_contract_hashes(skill_root)
    try:
        script_digest = script_semantic_digest(script)
    except ValueError:
        # Legacy external-script fixtures may not expose structured semantic
        # fields.  Bind those byte-for-byte instead of dropping script
        # freshness from the prompt contract.
        script_digest = _sha256(script)
    values = {
        "script_semantic": script_digest,
        "design_input": _sha256(project / VISUAL_FILES["design_input"]),
        "decisions": _sha256(project / VISUAL_FILES["decisions"]),
        "execution_receipt": _sha256(project / VISUAL_FILES["execution_receipt"]),
        "spec_json": _sha256(project / VISUAL_FILES["spec_json"]),
        "spec_markdown": _sha256(project / VISUAL_FILES["spec_markdown"]),
    }
    values.update({f"contract_{key}": value for key, value in contracts.items()})
    return values


def run_visual_structure_audit(project: Path, script: Path) -> tuple[int, dict[str, Any]]:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    skill_root = _skill_root()
    validator = skill_root / "scripts" / "validate_visual_spec.py"
    prompt_builder = skill_root / "scripts" / "build_generation_prompt.py"
    design_input = project / VISUAL_FILES["design_input"]
    request_path = project / VISUAL_FILES["skill_request"]
    decisions = project / VISUAL_FILES["decisions"]
    execution_receipt = project / VISUAL_FILES["execution_receipt"]
    spec_json = project / VISUAL_FILES["spec_json"]
    spec_md = project / VISUAL_FILES["spec_markdown"]
    prompts = project / VISUAL_FILES["generation_prompts"]
    report_path = project / VISUAL_FILES["validation"]
    previous_report = _read_json(report_path) if report_path.is_file() else {}
    from cyberppt.stage02_handoff import HANDOFF_JSON, load_stage02_handoff

    handoff = load_stage02_handoff(project, required=True)
    handoff_path = project / HANDOFF_JSON
    for path in (
        validator,
        prompt_builder,
        script,
        design_input,
        request_path,
        decisions,
        execution_receipt,
        spec_json,
        spec_md,
    ):
        if not path.is_file():
            raise FileNotFoundError(f"visual structure stage artifact is missing: {path}")
    design_payload = _read_json(design_input)
    if design_payload.get("source_sha256") != _sha256(handoff_path):
        raise ValueError("visual-design-input.json is stale for the current Stage 02 handoff")

    results: dict[str, Any] = {}
    for label, path in (("markdown", spec_md), ("json", spec_json)):
        completed = subprocess.run(
            [sys.executable, str(validator), str(path), "--strict", "--json-report"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        results[label] = json.loads(completed.stdout)
        results[label]["status"] = "passed" if completed.returncode == 0 else "failed"

    results["decision_package"] = audit_visual_design_package(
        design_input,
        decisions,
        spec_json,
    )
    results["execution_receipt"] = _audit_execution_receipt(project, script, skill_root)
    pre_prompt_passed = all(result.get("status") == "passed" for result in results.values())
    prompt_inputs = _prompt_inputs_sha256(project, script, skill_root)
    previous_inputs = previous_report.get("prompt_inputs_sha256")
    previous_inputs = previous_inputs if isinstance(previous_inputs, dict) else {}
    rebuild_reasons = [
        key
        for key, value in prompt_inputs.items()
        if previous_inputs.get(key) != value
    ]
    if not prompts.is_file():
        rebuild_reasons.append("generation_prompts_missing")
    elif previous_report.get("artifact_sha256", {}).get("generation_prompts") != _sha256(prompts):
        rebuild_reasons.append("generation_prompts_hash")
    rebuild_reasons = list(dict.fromkeys(rebuild_reasons))
    prompt_rebuilt = False
    if pre_prompt_passed and rebuild_reasons:
        subprocess.run(
            [sys.executable, str(prompt_builder), str(spec_json), "--output", str(prompts)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        prompt_rebuilt = True
    if pre_prompt_passed and prompts.is_file():
        results["prompt_freshness"] = {
            "status": "passed",
            "rebuilt": prompt_rebuilt,
            "rebuild_reasons": rebuild_reasons,
            "generation_prompts_sha256": _sha256(prompts),
        }
    else:
        results["prompt_freshness"] = {
            "status": "failed",
            "rebuilt": False,
            "rebuild_reasons": rebuild_reasons,
            "blocking_issues": [
                {
                    "code": "PROMPT_REBUILD_BLOCKED",
                    "message": "Prompt rebuild is blocked until the visual decision package and execution receipt pass.",
                }
            ],
        }
    passed = all(result.get("status") == "passed" for result in results.values())
    contracts = prompt_contract_hashes(skill_root)
    report = {
        "schema": "cyberppt.visual_structure_stage.v2",
        "build_id": f"visual-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{_sha256(script)[:10]}",
        "status": "passed" if passed else "failed",
        "validated_at": _utc_now(),
        "skill": "ppt-visual-structure-designer",
        "skill_sha256": _sha256(skill_root / "SKILL.md"),
        "skill_bundle_sha256": contracts["skill_bundle"],
        "skill_contract_sha256": contracts,
        "script": str(script),
        "script_sha256": _sha256(script),
        "script_semantic_sha256": script_semantic_digest(script),
        "stage02_handoff": str(handoff_path) if handoff is not None else None,
        "stage02_handoff_sha256": _sha256(handoff_path),
        "artifacts": {key: str(project / value) for key, value in VISUAL_FILES.items() if key != "validation"},
        "artifact_sha256": {
            key: _sha256(project / relative)
            for key, relative in VISUAL_FILES.items()
            if key != "validation" and (project / relative).is_file()
        },
        "prompt_inputs_sha256": prompt_inputs,
        "prompt_rebuilt": prompt_rebuilt,
        "prompt_rebuild_reasons": rebuild_reasons,
        "results": results,
    }
    if isinstance(previous_report.get("semantic_review"), dict):
        report["semantic_review"] = previous_report["semantic_review"]
    write_json_atomic(report_path, report)
    _register_visual_artifacts(project, script, report_path, build_id=str(report["build_id"]))
    return (0 if passed else 1), report


def _register_visual_artifacts(
    project: Path,
    script: Path,
    report_path: Path,
    *,
    build_id: str,
) -> None:
    ledger_path = project / "workbench" / "artifact-ledger.json"
    registered_paths = [
        VISUAL_FILES["design_input"],
        VISUAL_FILES["skill_request"],
        VISUAL_FILES["skill_invocation"],
        VISUAL_FILES["decisions"],
        VISUAL_FILES["execution_receipt"],
        VISUAL_FILES["spec_json"],
        VISUAL_FILES["spec_markdown"],
        VISUAL_FILES["generation_prompts"],
        VISUAL_FILES["validation"],
    ]
    try:
        script_dependency = script.relative_to(project).as_posix()
    except ValueError:
        script_dependency = str(script)
    resume = f"python -m cyberppt visual-structure-audit {project} --script {script}"
    records: list[dict[str, Any]] = []
    status = "passed" if _read_json(report_path).get("status") == "passed" else "failed"
    for relative in registered_paths:
        path = project / relative
        records.append(
            {
                "stage": "02-visual-structure",
                "page": None,
                "path": relative.as_posix(),
                "status": status,
                "depends_on": [script_dependency],
                "resume_command": resume,
                "sha256": _sha256(path),
            }
        )
    append_artifacts(ledger_path, records, build_id=build_id)


def assert_visual_structure_ready(project: Path, script: Path) -> Path | None:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    if not visual_structure_required(project):
        return None
    report_path = project / VISUAL_FILES["validation"]
    if not report_path.is_file():
        raise FileNotFoundError(
            "required visual structure stage is missing; prepare the Skill request, execute "
            "ppt-visual-structure-designer, record its execution, and run visual-structure-audit before Stage 02"
        )
    report = _read_json(report_path)
    from cyberppt.stage02_handoff import load_stage02_handoff

    load_stage02_handoff(project, required=True)
    if report.get("schema") != "cyberppt.visual_structure_stage.v2" or report.get("status") != "passed":
        raise ValueError("visual structure stage is not passed; rerun visual-structure-audit")
    for key in (
        "design_input",
        "skill_request",
        "decisions",
        "execution_receipt",
        "spec_json",
        "spec_markdown",
        "generation_prompts",
    ):
        path = project / VISUAL_FILES[key]
        if not path.is_file() or report.get("artifact_sha256", {}).get(key) != _sha256(path):
            raise ValueError(f"visual structure artifact is missing or changed: {path}")
    current_prompt_inputs = _prompt_inputs_sha256(project, script, _skill_root())
    if report.get("prompt_inputs_sha256") != current_prompt_inputs:
        raise ValueError(
            "visual structure prompt inputs changed (script, Skill, builder, validator, schema, input, decisions, or spec); "
            "rerun visual-structure-audit"
        )
    return report_path
