from pathlib import Path

path = Path(__file__).with_name("_apply_stage_file_boundary.py")
text = path.read_text(encoding="utf-8")
start = text.index("# Visual structure: consume Stage 02 input")
end = text.index("# Product facade keeps old argument names", start)
replacement = r'''# Visual structure: consume Stage 02 input, never orchestrate a cross-stage handoff.
path = "cyberppt/visual_stage/execution.py"
text = read(path)
old_prepare = ''' + "'''" + r'''def prepare_visual_structure_stage(
    project: Path,
    script: Path,
    *,
    lightweight_stage01_confirmed: bool = False,
    reuse_current_handoff: bool = False,
) -> Path:
    _ = lightweight_stage01_confirmed
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    from cyberppt.stage02_handoff import HANDOFF_JSON, ensure_project_script, prepare_stage02_handoff

    script = ensure_project_script(project, script)
    handoff = project / HANDOFF_JSON
    from cyberppt.stage02_handoff import audit_stage02_handoff

    if reuse_current_handoff:
        if not handoff.is_file():
            raise FileNotFoundError("reuse_current_handoff requires an existing Stage 02 handoff")
        report = audit_stage02_handoff(project)
        if report.get("status") != "passed":
            codes = ", ".join(
                item.get("code", "HANDOFF_INVALID")
                for item in report.get("blocking_issues", [])
            )
            raise ValueError(f"reuse_current_handoff requires a current Stage 02 handoff: {codes}")
    else:
        report = audit_stage02_handoff(project) if handoff.is_file() else {"status": "missing"}
        if report.get("status") != "passed":
            report = prepare_stage02_handoff(project, script=script)
            if report.get("status") != "passed":
                raise ValueError("Stage 01 to Stage 02 handoff is not passed")
    design_input = _write_visual_design_input(project, handoff)
''' + "'''" + r'''
new_prepare = ''' + "'''" + r'''def prepare_visual_structure_stage(
    project: Path,
    script: Path,
    *,
    lightweight_stage01_confirmed: bool = False,
    reuse_current_handoff: bool = False,
) -> Path:
    _ = lightweight_stage01_confirmed, reuse_current_handoff
    project = project.expanduser().resolve()
    source_script = script.expanduser().resolve()
    from cyberppt.stage02_input import INPUT_JSON, prepare_stage02_input, snapshot_input_script

    script = snapshot_input_script(project, source_script)
    report = prepare_stage02_input(project, script=source_script, reuse_current_input=True)
    if report.get("status") != "passed":
        codes = ", ".join(
            item.get("code", "INPUT_INVALID")
            for item in report.get("blocking_issues", [])
        )
        raise ValueError(f"Stage 02 script input is invalid: {codes}")
    script_input = project / INPUT_JSON
    design_input = _write_visual_design_input(project, script_input)
''' + "'''" + r'''
text = replace_once(text, old_prepare, new_prepare, label="visual structure file-boundary prepare")
text = text.replace('f"- stage02_handoff: {handoff}"', 'f"- stage02_script_input: {script_input}"')
text = text.replace('derived only from stage02_handoff.json', 'derived only from the Stage 02 script input snapshot')
text = text.replace('use stage01_relationship_features', 'use input_relationship_features')
text = text.replace('stage01_visual_note_disposition', 'input_visual_note_disposition')
text = text.replace('audited Stage 02 handoff', 'audited Stage 02 script input')
write(path, text)

'''
path.write_text(text[:start] + replacement + text[end:], encoding="utf-8", newline="\n")
print("helper corrected")
