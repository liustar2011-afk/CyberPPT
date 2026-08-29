from __future__ import annotations

from pathlib import Path

from cyberppt.visual_structure_contract import prompt_contract_hashes

from .execution import _skill_root, visual_structure_required
from .persistence import VISUAL_FILES, _read_json, _sha256


def _prompt_inputs_sha256(project: Path, script: Path, skill_root: Path) -> dict[str, str]:
    contracts = prompt_contract_hashes(skill_root)
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


def assert_visual_structure_ready(project: Path, script: Path) -> Path | None:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    from cyberppt.stage02_input import input_path, load_stage02_input, resolve_input_script
    script = resolve_input_script(project, script)
    if not visual_structure_required(project):
        return None
    report_path = project / VISUAL_FILES["validation"]
    if not report_path.is_file():
        raise FileNotFoundError(
            "required visual structure stage is missing; prepare the Skill request, execute "
            "ppt-visual-structure-designer, record its execution, and run visual-structure-audit before Stage 02"
        )
    report = _read_json(report_path)
    script_input = load_stage02_input(project, required=True)
    input_file = input_path(project)
    design_input = _read_json(project / VISUAL_FILES["design_input"])
    if design_input.get("source_sha256") != _sha256(input_file):
        raise ValueError("visual structure design input is stale for the current Stage 02 script input")
    for key in (
        "design_input",
        "skill_request",
        "decisions",
        "execution_receipt",
        "spec_json",
        "spec_markdown",
        "review_summary",
        "generation_prompts",
    ):
        path = project / VISUAL_FILES[key]
        if not path.is_file() or report.get("artifact_sha256", {}).get(key) != _sha256(path):
            raise ValueError(f"visual structure artifact is missing or changed: {path}")

    input_pages = {
        str(page.get("page_id")): page
        for page in script_input.get("pages") or []
        if isinstance(page, dict) and page.get("page_id")
    }
    spec = _read_json(project / VISUAL_FILES["spec_json"])
    for page in spec.get("pages") or []:
        if not isinstance(page, dict):
            continue
        page_id = str(page.get("page_id") or "")
        source_page = input_pages.get(page_id.lower()) or input_pages.get(page_id.upper())
        if source_page is None or source_page.get("render_role") != "content":
            continue
        generation_handoff = page.get("generation_handoff")
        if not isinstance(generation_handoff, dict):
            raise ValueError(f"visual structure page {page_id} is missing generation_handoff")
        expected_text = [str(value) for value in source_page.get("onscreen_items") or []]
        actual_text = [str(value) for value in generation_handoff.get("required_text") or []]
        if actual_text != expected_text:
            raise ValueError(
                f"visual structure required_text drifted from final-script onscreen_text: {page_id}"
            )
    return report_path
