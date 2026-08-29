from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from cyberppt.onscreen_expression import expression_constraints
from cyberppt.visual_structure_contract import prompt_contract_hashes, skill_bundle_sha256

from .compiler import compile_visual_spec, _render_visual_structure_markdown
from .persistence import (
    SKILL_RELATIVE,
    VISUAL_FILES,
    _read_json,
    _sha256,
    _spec_content_sha256,
    _utc_now,
    write_json,
)


def _skill_root() -> Path:
    return (Path(__file__).resolve().parents[2] / SKILL_RELATIVE).resolve()


def _write_visual_design_input(project: Path, script_input: Path) -> Path:
    payload = _read_json(script_input)
    source_pages = payload.get("pages") or []
    content_pages = [page for page in source_pages if page.get("render_role") == "content"]
    pages: list[dict[str, Any]] = []
    for index, page in enumerate(content_pages):
        visual = page.get("stage02_visual_input") or {}
        expression = visual.get("onscreen_expression") or page.get("onscreen_expression") or {}
        constraints = visual.get("expression_constraints") or page.get("expression_constraints")
        if constraints is None:
            constraints = expression_constraints(str(expression.get("form") or ""))
        previous_page = content_pages[index - 1] if index else None
        next_page = content_pages[index + 1] if index + 1 < len(content_pages) else None
        business_relationships = [
            {
                key: deepcopy(item[key])
                for key in (
                    "subject", "relation", "objects", "direction", "condition", "modality",
                    "basis", "confidence", "source_refs", "authority_ref",
                )
                if key in item
            }
            for item in visual.get("business_relationships") or []
            if isinstance(item, dict)
        ]
        for relationship in business_relationships:
            if "confidence" in relationship:
                relationship["confidence"] = str(relationship["confidence"])
        pages.append(
            {
                "page_id": page.get("page_id"),
                "page_number": page.get("page_number"),
                "page_title": page.get("title"),
                "argument_role": page.get("argument_role"),
                "page_mission": page.get("page_mission"),
                "core_judgment": page.get("core_message"),
                "semantic_context": page.get("full_prose"),
                "content_load": visual.get("content_load") or page.get("content_load") or "standard",
                "argument_chain": page.get("argument_chain"),
                "prompt_mode": page.get("prompt_mode") or "semantic_brief",
                "locked_on_screen_text": page.get("onscreen_text"),
                "locked_on_screen_items": page.get("onscreen_items") or [],
                "locked_text_items": visual.get("locked_text_items") or [],
                "content_integrity": visual.get("content_integrity") or {},
                "trace_refs": list(dict.fromkeys([
                    *[str(value) for value in page.get("source_refs") or [] if str(value)],
                    *[str(value) for value in page.get("provenance_refs") or [] if str(value)],
                    *[str(value) for value in page.get("boundary_source_refs") or [] if str(value)],
                ])),
                "onscreen_expression": expression,
                "expression_constraints": constraints,
                "business_relationships": business_relationships,
                "input_relationship_features": visual.get("input_relationship_features") or visual.get("stage01_relationship_features") or {},
                "render_topology": visual.get("render_topology") or visual.get("semantic_topology") or {},
                "semantic_verification": visual.get("semantic_verification") or {},
                "relationship_authority": "business_relationships",
                "author_visual_notes": visual.get("author_visual_notes") or "",
                "author_visual_notes_authority": "advisory_only",
                "must_not_include": page.get("must_not_include") or [],
                "body_image_canvas": visual.get("body_image_canvas"),
                "title_render_mode": visual.get("title_render_mode"),
                "subtitle_render_mode": visual.get("subtitle_render_mode"),
                "previous_content_page": (
                    {"page_id": previous_page.get("page_id"), "title": previous_page.get("title")}
                    if previous_page else None
                ),
                "next_content_page": (
                    {"page_id": next_page.get("page_id"), "title": next_page.get("title")}
                    if next_page else None
                ),
            }
        )
    output = project / VISUAL_FILES["design_input"]
    write_json(
        output,
        {
            "schema": "cyberppt.visual_design_input.v2",
            "source": str(script_input),
            "source_sha256": _sha256(script_input),
            "content_lock": "strict",
            "style_policy": "visual structure must not select or embed a visual style",
            "relationship_policy": (
                "business_relationships comes from the input script file; render_topology is Stage 02-derived "
                "layout guidance only and must not rewrite business nodes or edges; author_visual_notes is "
                "advisory only and must never be copied into decision_relationship"
            ),
            "decision_policy": (
                "ppt-visual-structure-designer writes one candidate when the page's business "
                "relationship type is unambiguous from expression_constraints.reading_requirement "
                "and content alone; when the relationship type is genuinely contested (for example "
                "parallel vs. hierarchical), it must compare 2-3 materially different candidates "
                "and justify the selection; deterministic keyword routing is never authoritative"
            ),
            "pages": pages,
        },
    )
    return output


def visual_structure_required(project: Path) -> bool:
    manifest = project / "manifest.yml"
    if manifest.is_file():
        text = manifest.read_text(encoding="utf-8-sig")
        if "visual_structure_designer: required" in text:
            return True
    visual = project / "visual"
    return any((visual / name).is_file() for name in (
        "skill-request.json", "visual-design-input.json", "deck-visual-spec.json",
        "visual-design-decisions.json", "validation-report.json",
    ))


def _write_skill_request(project: Path, script: Path, design_input: Path) -> Path:
    skill_root = _skill_root()
    contracts = prompt_contract_hashes(skill_root)
    output = project / VISUAL_FILES["skill_request"]
    write_json(
        output,
        {
            "schema": "cyberppt.visual_structure_skill_request.v1",
            "skill": "ppt-visual-structure-designer",
            "skill_root": str(skill_root),
            "skill_bundle_sha256": contracts["skill_bundle"],
            "skill_contract_sha256": contracts,
            "approved_script": str(script),
            "approved_script_sha256": _sha256(script),
            "visual_design_input": str(design_input),
            "visual_design_input_sha256": _sha256(design_input),
            "content_lock": "strict",
            "relationship_authority": "business_relationships",
            "author_visual_notes_authority": "advisory_only",
            "prompt_modes": {
                "default": "semantic_brief",
                "directed": "directed_composition",
                "authority": "visual_design_input.pages[].prompt_mode",
            },
            "required_outputs": [VISUAL_FILES["decisions"].as_posix()],
            "compiler_outputs": [
                VISUAL_FILES["spec_json"].as_posix(),
                VISUAL_FILES["spec_markdown"].as_posix(),
            ],
            "forbidden_outputs": ["image", "svg", "html", "pptx"],
            "prepared_at": _utc_now(),
        },
    )
    return output


def prepare_visual_structure_stage(
    project: Path,
    script: Path,
    *,
    lightweight_stage01_confirmed: bool = False,
    reuse_current_handoff: bool = False,
) -> Path:
    _ = lightweight_stage01_confirmed, reuse_current_handoff
    project = project.expanduser().resolve()
    source_script = script.expanduser().resolve()
    from cyberppt.stage02_input import INPUT_JSON, prepare_stage02_input, resolve_input_script

    report = prepare_stage02_input(project, script=source_script, reuse_current=True)
    if report.get("status") != "passed":
        codes = ", ".join(item.get("code", "INPUT_INVALID") for item in report.get("blocking_issues", []))
        raise ValueError(f"Stage 02 script input is invalid: {codes}")
    script = resolve_input_script(project, source_script)
    script_input = project / INPUT_JSON
    design_input = _write_visual_design_input(project, script_input)
    skill_root = _skill_root()
    skill = skill_root / "SKILL.md"
    if not skill.is_file():
        raise FileNotFoundError(f"registered visual structure skill is missing: {skill}")
    skill_request = _write_skill_request(project, script, design_input)
    output = project / VISUAL_FILES["skill_invocation"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join([
            "# PPT Visual Structure Designer Invocation", "", "- skill: ppt-visual-structure-designer",
            f"- skill_path: {skill}", f"- skill_sha256: {_sha256(skill)}",
            f"- skill_bundle_sha256: {skill_bundle_sha256(skill_root)}",
            f"- approved_script: {script}", f"- approved_script_sha256: {_sha256(script)}",
            f"- stage02_script_input: {script_input}", f"- visual_design_input: {design_input}",
            f"- skill_request: {skill_request}", "- mode: stage02-file-input", "- content_lock: strict", "",
            "## Required action", "",
            "Invoke the registered skill in the current execution surface. Use visual-design-input.json, derived only from the Stage 02 script input snapshot, as the visual-design interface. Write cyberppt.visual_design_decisions.v3. Treat business_relationships as authoritative, use input_relationship_features to preserve actors, actions, directions, conditions, branches and feedback, and treat author_visual_notes as advisory only. trace_refs are audit-only provenance: use them to justify decisions but never copy them into visual copy or ImageGen prompt material. Treat expression_constraints as the required reading-relation and balance profile: it governs peer hierarchy, progression, correspondence, feedback or causal direction; it must never be converted directly into a fixed card, column, arrow, loop, pyramid or matrix template. Every candidate must provide its own visual_thesis and expression_fit with the received form, satisfied constraints, reading relation, balance strategy, and either an empty default-profile deviation or an adapted-profile changed-constraint list plus business reason that preserves the expression core. Respect each page's prompt_mode. For semantic_brief, decide only the semantic focus, source-supported relationship boundary, evidence grouping and exact-text binding; omit execution_design or treat it as non-authoritative advice, leaving scene, carrier, spatial organization and supporting detail to ImageGen. For directed_composition, provide the full authoritative execution_design with business_object, visual_focus, semantic_role, use_scene, scene_type, text_integration_method, spatial_organization and relationship_encoding. For every page, record input_visual_note_disposition with the received form, chosen reading relation and balance strategy, plus inherited, adjusted and rejected upstream visual features and reasons. Do not read or reuse any existing Stage 02 visual/ or workbench/prompts/imagegen outputs as authority. Write one candidate when the page's business relationship type is unambiguous from expression_constraints.reading_requirement and content alone; when it is genuinely contested (for example parallel vs. hierarchical), generate and compare 2-3 materially different candidates and justify the selection. Deterministic keyword matching must not choose the final visual intent or carrier. Preserve the approved page set, locked text ids and locked text, and write only:",
            "", "- `visual/visual-design-decisions.json`", "",
            "After the Skill has actually produced that decision receipt, run `python -m cyberppt execute-visual-structure <project> --script <script>` to compile `deck-visual-spec.json` and `script-visual-structure.md`; then record the execution with `python -m cyberppt record-visual-structure-execution <project> --script <script> --executor <surface> --model <model>`, and run `visual-structure-audit`. The audit, not the Skill, rebuilds generation-prompts.md as a legacy structural preview. Formal ImageGen handoff uses the repository artifact-spec-v2 compiler over the audited Stage 02 script input, deck visual spec and style lock.",
            "", "Do not select a visual style, generate images, SVG, HTML, or PPTX in this stage.", "",
        ]),
        encoding="utf-8",
        newline="\n",
    )
    return output


def execute_visual_structure_stage(project: Path, script: Path) -> dict[str, Path]:
    project, script = project.expanduser().resolve(), script.expanduser().resolve()
    from cyberppt.stage02_input import resolve_input_script
    script = resolve_input_script(project, script)
    design_input_path = project / VISUAL_FILES["design_input"]
    decisions_path = project / VISUAL_FILES["decisions"]
    if not script.is_file() or not design_input_path.is_file() or not decisions_path.is_file():
        raise FileNotFoundError("visual structure execution requires script, visual-design-input.json and visual-design-decisions.json")
    spec = compile_visual_spec(project, design_input_path, decisions_path)
    json_path = project / VISUAL_FILES["spec_json"]
    markdown_path = project / VISUAL_FILES["spec_markdown"]
    write_json(json_path, spec)
    markdown_path.write_text(_render_visual_structure_markdown(spec) + "\n", encoding="utf-8", newline="\n")
    return {"spec_json": json_path, "spec_markdown": markdown_path}


def record_visual_structure_execution(
    project: Path,
    script: Path,
    *,
    executor: str,
    model: str,
    note: str = "",
) -> Path:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    from cyberppt.stage02_input import resolve_input_script
    script = resolve_input_script(project, script)
    if not executor.strip() or not model.strip():
        raise ValueError("executor and model are required for the visual structure execution receipt")
    skill_root = _skill_root()
    design_input = project / VISUAL_FILES["design_input"]
    request_path = project / VISUAL_FILES["skill_request"]
    artifact_paths = {key: project / VISUAL_FILES[key] for key in ("decisions", "spec_json", "spec_markdown")}
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
    write_json(
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
            "visual_design_input": str(design_input),
            "visual_design_input_sha256": _sha256(design_input),
            "page_ids": page_ids,
            "skill_outputs": ["decisions"],
            "compiler_outputs": ["spec_json", "spec_markdown"],
            "artifact_sha256": {
                key: (_spec_content_sha256(path) if key == "spec_json" else _sha256(path))
                for key, path in artifact_paths.items()
            },
            "executed_at": _utc_now(),
            "note": note.strip(),
        },
    )
    return output


def _audit_execution_receipt(project: Path, script: Path, skill_root: Path) -> dict[str, Any]:
    from cyberppt.stage02_input import resolve_input_script
    script = resolve_input_script(project, script)
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
        "approved_script_sha256": _sha256(script),
        "visual_design_input_sha256": _sha256(design_input),
    }
    expected_hash_source = {
        "skill_request_sha256": str(request_path),
        "skill_bundle_sha256": f"{skill_root} (vendor Skill bundle)",
        "approved_script_sha256": str(script),
        "visual_design_input_sha256": str(design_input),
    }
    rerun_command = (
        f"python -m cyberppt record-visual-structure-execution {project} --script {script} "
        "--executor <executor> --model <model>"
    )
    if receipt.get("schema") != "cyberppt.visual_structure_execution_receipt.v1":
        issue("EXECUTION_RECEIPT_SCHEMA_INVALID", "Visual structure execution receipt schema is invalid.")
    for field in ("executor", "model", "executed_at"):
        if not str(receipt.get(field) or "").strip():
            issue("EXECUTION_RECEIPT_FIELD_MISSING", f"Execution receipt is missing {field}.")
    for field, value in expected.items():
        if receipt.get(field) != value:
            issue(
                "EXECUTION_RECEIPT_STALE",
                f"Execution receipt field {field!r} is stale; current expected hash comes from "
                f"{expected_hash_source[field]!r}. Re-run: {rerun_command}",
            )
    if receipt.get("skill_outputs") != ["decisions"]:
        issue("EXECUTION_RECEIPT_OUTPUT_OWNERSHIP_INVALID", "Execution receipt must record visual-design-decisions.json as the only Skill output.")
    if receipt.get("compiler_outputs") != ["spec_json", "spec_markdown"]:
        issue("EXECUTION_RECEIPT_OUTPUT_OWNERSHIP_INVALID", "Execution receipt must record the visual spec JSON and Markdown as compiler outputs.")
    receipt_contracts = receipt.get("skill_contract_sha256")
    if receipt_contracts != contracts:
        stale_contract_fields = sorted(
            key for key, value in contracts.items()
            if receipt_contracts is None or receipt_contracts.get(key) != value
        )
        issue(
            "EXECUTION_RECEIPT_CONTRACT_STALE",
            f"Execution receipt is not bound to the current Skill contract files: {stale_contract_fields}; "
            f"current expected hashes come from {skill_root} (SKILL.md, prompt builder, validator, schemas). "
            f"Re-run: {rerun_command}",
        )
    receipt_artifacts = receipt.get("artifact_sha256") if isinstance(receipt.get("artifact_sha256"), dict) else {}
    for key in ("decisions", "spec_json", "spec_markdown"):
        path = project / VISUAL_FILES[key]
        current = _spec_content_sha256(path) if key == "spec_json" else _sha256(path)
        if not path.is_file() or receipt_artifacts.get(key) != current:
            issue(
                "EXECUTION_ARTIFACT_STALE",
                f"Execution receipt does not match {path}; current expected hash comes from that file's "
                f"present content. Re-run: {rerun_command}",
            )
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
