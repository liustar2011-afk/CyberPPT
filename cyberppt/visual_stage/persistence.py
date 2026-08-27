from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.artifact_ledger import append_artifacts, write_json_atomic
from cyberppt.visual_structure_contract import read_json as _read_json, sha256 as _sha256


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
    "review_summary": Path("visual/visual-review-summary.md"),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _spec_content_sha256(path: Path) -> str:
    """Hash compiler-owned visual spec content, excluding audit status stamps."""
    payload = _read_json(path)
    payload.pop("qa_summary", None)
    for page in payload.get("pages") or []:
        if not isinstance(page, dict):
            continue
        page.pop("qa", None)
        contract = page.get("quality_contract")
        if isinstance(contract, dict):
            contract["status"] = None
            focus = contract.get("focus_competition")
            if isinstance(focus, dict):
                focus["status"] = None
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_json_atomic(path, payload)


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
        VISUAL_FILES["review_summary"],
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
        if not path.is_file():
            continue
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
