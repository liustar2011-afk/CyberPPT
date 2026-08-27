from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from cyberppt.semantic_digest import script_semantic_digest
from cyberppt.visual_structure_contract import (
    audit_visual_design_package,
    audit_visual_deck_rhythm,
    prompt_contract_hashes,
)

from .compiler import _page_id
from .execution import _audit_execution_receipt, _skill_root
from .persistence import VISUAL_FILES, _read_json, _register_visual_artifacts, _sha256, _utc_now, write_json
from .prompt_gate import _prompt_inputs_sha256


def _render_visual_review_summary(
    spec: dict[str, Any], decisions: dict[str, Any], validation: dict[str, Any]
) -> str:
    by_id = {
        _page_id(item.get("page_id")): item
        for item in decisions.get("pages") or []
        if isinstance(item, dict)
    }
    lines = [f"# {spec.get('deck_title', '')}视觉质量人工复核摘要", ""]
    for page in spec.get("pages") or []:
        if not isinstance(page, dict):
            continue
        decision = by_id.get(_page_id(page.get("page_id")), {})
        selected = str(decision.get("selected_candidate") or "")
        candidates = [item for item in decision.get("candidates") or [] if isinstance(item, dict)]
        contract = page.get("quality_contract") if isinstance(page.get("quality_contract"), dict) else {}
        graph = page.get("semantic_graph") if isinstance(page.get("semantic_graph"), dict) else {}
        structural = page.get("structural_decision") if isinstance(page.get("structural_decision"), dict) else {}
        lines += [
            f"## 第{page.get('page_number', '')}页｜{page.get('page_title', '')}", "",
            f"- 页面使命：{page.get('page_mission', '')}", f"- 选中候选：{selected}", "- 候选取舍：",
        ]
        for candidate in candidates:
            if str(candidate.get("id") or "") != selected:
                lines.append(f"  - {candidate.get('id', '')}：{candidate.get('rejection_rationale', '')}")
        lines += ["- 关系草图："]
        for edge in graph.get("edges") or []:
            if isinstance(edge, dict):
                lines.append(f"  - {edge.get('from', '')} → {edge.get('to', '')}（{edge.get('relation', '')}）")
        capacity = contract.get("text_capacity") if isinstance(contract.get("text_capacity"), dict) else {}
        feasibility = contract.get("generation_feasibility") if isinstance(contract.get("generation_feasibility"), dict) else {}
        coverage = contract.get("relationship_coverage") if isinstance(contract.get("relationship_coverage"), dict) else {}
        focus = contract.get("focus_competition") if isinstance(contract.get("focus_competition"), dict) else {}
        lines += [
            f"- 锁定文字容量：{capacity.get('locked_text_count')}项；风险={capacity.get('risk_level')}；{', '.join(str(item) for item in capacity.get('risks') or []) or '无'}",
            f"- 可生成性：{feasibility.get('score')}；风险={', '.join(str(item) for item in feasibility.get('risks') or []) or '无'}",
            f"- 关系/焦点风险：覆盖={coverage}；焦点={focus}；主焦点={structural.get('semantic_focus', {})}",
            "",
        ]
    rhythm = validation.get("deck_rhythm") if isinstance(validation.get("deck_rhythm"), dict) else {}
    lines += ["## 整套节奏结论", "", f"- 状态：{rhythm.get('status', 'pending_audit')}"]
    for issue in rhythm.get("blocking_issues") or []:
        lines.append(f"- 阻断：{issue.get('code', '')}｜{issue.get('message', '')}")
    for warning in rhythm.get("warnings") or []:
        lines.append(f"- 警告：{warning.get('code', '')}｜{warning.get('message', '')}")
    return "\n".join(lines) + "\n"


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
        results[label]["status"] = "passed" if results[label].get("valid") is True else "failed"

    results["decision_package"] = audit_visual_design_package(design_input, decisions, spec_json)
    results["execution_receipt"] = _audit_execution_receipt(project, script, skill_root)
    results["deck_rhythm"] = audit_visual_deck_rhythm(_read_json(spec_json), _read_json(decisions))
    pre_prompt_passed = all(result.get("status") == "passed" for result in results.values())
    audited_spec = _read_json(spec_json)
    page_score = 100 if pre_prompt_passed else None
    qa_status = "passed" if pre_prompt_passed else "failed"
    page_issues = (
        []
        if pre_prompt_passed
        else [
            str(issue.get("code") or "")
            for result in results.values()
            for issue in result.get("blocking_issues", [])
            if isinstance(issue, dict)
        ]
    )
    rhythm_warnings = [
        str(issue.get("code") or "")
        for issue in results["deck_rhythm"].get("warnings", [])
        if isinstance(issue, dict)
    ]
    for page in audited_spec.get("pages") or []:
        if isinstance(page, dict):
            page["qa"] = {
                "status": qa_status,
                "score": page_score,
                "blocking_issues": page_issues,
                "warnings": rhythm_warnings,
            }
            contract = page.get("quality_contract")
            if isinstance(contract, dict):
                contract["status"] = qa_status
                contract["focus_competition"]["status"] = qa_status
    audited_spec["qa_summary"] = {
        "status": qa_status,
        "average_score": page_score,
        "blocking_issues": page_issues,
        "warnings": rhythm_warnings,
    }
    write_json(spec_json, audited_spec)
    review_summary = project / VISUAL_FILES["review_summary"]
    review_summary.write_text(
        _render_visual_review_summary(
            audited_spec,
            _read_json(decisions),
            {"deck_rhythm": results["deck_rhythm"]},
        ),
        encoding="utf-8",
        newline="\n",
    )
    prompt_inputs = _prompt_inputs_sha256(project, script, skill_root)
    previous_inputs = previous_report.get("prompt_inputs_sha256")
    previous_inputs = previous_inputs if isinstance(previous_inputs, dict) else {}
    rebuild_reasons = [key for key, value in prompt_inputs.items() if previous_inputs.get(key) != value]
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
    write_json(report_path, report)
    _register_visual_artifacts(project, script, report_path, build_id=str(report["build_id"]))
    return (0 if passed else 1), report
