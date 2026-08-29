from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, got {count}")
    return text.replace(old, new, 1)


def sub_once(text: str, pattern: str, repl: str, *, label: str, flags: int = 0) -> str:
    updated, count = re.subn(pattern, repl, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected one regex match, got {count}")
    return updated


# --- Stage2 script intake: make the file the only cross-stage authority. ---
path = "cyberppt/stage02_handoff.py"
text = read(path)
text = replace_once(
    text,
    '"""Compile and audit the governed Stage 01 -> Stage 02 semantic handoff."""',
    '"""Compile and audit Stage 02-owned input derived only from a script file.\n\nThis module must not read or invoke Stage 01 workflow state. The file passed to\nStage 02 is the complete cross-stage boundary. Legacy handoff names remain as\ncompatibility aliases only.\n"""',
    label="stage02 docstring",
)
text = replace_once(
    text,
    "from cyberppt.script_quality_contract import ScriptPage, parse_script_path\nfrom cyberppt.script_quality.models import ScriptDocument\n",
    "from cyberppt.script_quality_contract import ScriptPage, parse_script_markdown\n",
    label="stage02 parser imports",
)
text = replace_once(
    text,
    'HANDOFF_DIR = Path("workbench/stages/02-handoff")\nHANDOFF_JSON = HANDOFF_DIR / "stage02-handoff.json"\nHANDOFF_MD = HANDOFF_DIR / "stage02-handoff-review.md"\nHANDOFF_AUDIT = HANDOFF_DIR / "stage02-handoff-audit.json"\nSCRIPT_PATH = Path("workbench/scripts/final/script-final.md")\n',
    'INPUT_DIR = Path("workbench/stages/02-input")\nINPUT_JSON = INPUT_DIR / "script-intake.json"\nINPUT_REVIEW = INPUT_DIR / "script-intake-review.md"\nINPUT_AUDIT = INPUT_DIR / "script-intake-audit.json"\nINPUT_SCRIPT_PATH = Path("workbench/inputs/final-script.md")\n# Compatibility aliases. Formal Stage 02 code imports stage02_input.py.\nHANDOFF_DIR = INPUT_DIR\nHANDOFF_JSON = INPUT_JSON\nHANDOFF_MD = INPUT_REVIEW\nHANDOFF_AUDIT = INPUT_AUDIT\nSCRIPT_PATH = INPUT_SCRIPT_PATH\nLEGACY_HANDOFF_JSON = Path("workbench/stages/02-handoff/stage02-handoff.json")\n',
    label="stage02 paths",
)

new_snapshot = '''def snapshot_input_script(project: Path, script: Path) -> Path:\n    """Snapshot the supplied script file into the Stage 02 workspace.\n\n    The caller may supply a file produced by Stage 01, another repository, or a\n    human. Stage 02 treats all of them identically. No Stage 01 project layout\n    is inspected.\n    """\n\n    project = project.expanduser().resolve()\n    requested = script.expanduser().resolve()\n    target = (project / INPUT_SCRIPT_PATH).resolve()\n    if requested == target:\n        if not target.is_file():\n            raise FileNotFoundError(f"Stage 02 script input is missing: {target}")\n        return target\n    if requested.is_file():\n        target.parent.mkdir(parents=True, exist_ok=True)\n        shutil.copyfile(requested, target)\n        return target\n\n    # Resume is allowed from the Stage 02-owned snapshot only when the current\n    # intake binding proves it came from the same requested path and bytes.\n    if target.is_file():\n        intake_path = project / INPUT_JSON\n        if not intake_path.is_file() and (project / LEGACY_HANDOFF_JSON).is_file():\n            intake_path = project / LEGACY_HANDOFF_JSON\n        if intake_path.is_file():\n            try:\n                payload = _read_json(intake_path)\n            except (OSError, json.JSONDecodeError, ValueError):\n                payload = None\n            binding = (payload or {}).get("source_bindings", {}).get("script", {})\n            source_path = str(binding.get("source_path") or binding.get("external_path") or "").strip()\n            if source_path and Path(source_path).expanduser().resolve() == requested:\n                if binding.get("sha256") == hashlib.sha256(target.read_bytes()).hexdigest():\n                    return target\n    raise FileNotFoundError(f"Stage 02 script input is missing: {requested}")\n\n\n# Legacy API alias.\nensure_project_script = snapshot_input_script\n'''
text = sub_once(
    text,
    r"def ensure_project_script\(project: Path, script: Path\) -> Path:\n.*?\n\ndef _handoff_authority",
    new_snapshot + "\n\ndef _handoff_authority",
    label="snapshot input function",
    flags=re.S,
)
text = replace_once(
    text,
    '        "planning_policy": payload.get("planning_policy"),\n',
    "",
    label="remove planning policy authority",
)
# Neutral relationship naming and authority.
text = text.replace("_stage01_relationship_features", "_input_relationship_features")
text = text.replace('authority="stage01_semantic_handoff"', 'authority="input_script"')
text = text.replace('"stage01_authoritative"', '"input_file_authoritative"')
text = text.replace('origin="stage01"', 'origin="input_file"')
text = text.replace("Stage01", "input file")
text = text.replace("Stage 01", "input file")
text = text.replace("stage01", "input")

# The intake record must be derived only from fields embedded in the script.
text = sub_once(
    text,
    r"def _page_record\(page: ScriptPage, outline: dict\[str, Any\] \| None\) -> dict\[str, Any\]:\n.*?    render_role = _render_role\(page.page_type\)\n",
    '''def _page_record(page: ScriptPage, outline: dict[str, Any] | None = None) -> dict[str, Any]:\n    _ = outline\n    page_mission = str(page.page_mission or page.main_message)\n    must_not_include: list[str] = []\n    consumed_content_unit_ids: list[str] = []\n    source_refs = tuple(page.source_refs)\n    render_role = _render_role(page.page_type)\n''',
    label="page record file-only preamble",
    flags=re.S,
)
text = sub_once(
    text,
    r"    explicit_prompt_mode = str\(\n.*?\n    directed_topologies = \{",
    '    explicit_prompt_mode = ""\n    directed_topologies = {',
    label="remove embedded stage2 mode from input",
    flags=re.S,
)
text = text.replace('topic_category=str(outline.get("topic_category") or "")', 'topic_category=""')
text = text.replace('page.argument_chain or str(outline.get("argument_chain") or "")', 'page.argument_chain')
text = text.replace('"argument_role": str(outline.get("argument_role") or outline.get("page_role") or ""),', '"argument_role": "",')
text = sub_once(
    text,
    r"        \"field_provenance\": \{\n.*?        \},\n    \}\n    for field in \(\"source_heading_ids\", \"primary_source_heading_id\", \"subtitle_policy\"\):\n.*?\n\n    if render_role != \"content\":",
    '''        "field_provenance": {\n            "content": "input_script",\n            "page_mission": "input_script",\n            "argument_chain": "input_script",\n            "provenance_refs": "input_script",\n            "business_relationships": "input_script",\n            "verified_business_relationships": "stage02_semantic_verifier",\n            "semantic_topology": "stage02_topology_resolver_compatibility_alias",\n            "render_topology": "stage02_topology_resolver",\n            "content_load": "input_script_or_standard_default",\n            "onscreen_expression_ir": "input_script_if_declared",\n            "visual_structure": "stage02_generated",\n            "style": "stage02_style_lock",\n        },\n    }\n\n    if render_role != "content":''',
    label="neutral field provenance",
    flags=re.S,
)
# Remove all remaining outline fallbacks from the visual input.
text = text.replace('page.argument_chain or str(outline.get("argument_chain") or "")', 'page.argument_chain')

# Remove the only runtime access to deck-plan.json.
text = sub_once(
    text,
    r"\ndef _deck_plan_page_map\(.*?\n\ndef build_stage02_handoff\(",
    "\n\ndef build_stage02_handoff(",
    label="remove deck plan reader",
    flags=re.S,
)

# Replace builder with file-only intake builder; keep legacy function name as alias.
new_builder = '''def build_stage02_input(\n    project: Path,\n    *,\n    script: Path | None = None,\n    lightweight_input_confirmed: bool = False,\n    allow_script_edit: bool = False,\n) -> dict[str, Any]:\n    _ = lightweight_input_confirmed, allow_script_edit\n    project = project.expanduser().resolve()\n    requested_script = script.expanduser().resolve() if script else (project / INPUT_SCRIPT_PATH).resolve()\n    snapshot = snapshot_input_script(project, requested_script)\n    binding = _file_binding(snapshot, script_semantic_digest, project=project)\n    binding["source_path"] = str(requested_script)\n    if requested_script.is_file():\n        binding["source_sha256"] = hashlib.sha256(requested_script.read_bytes()).hexdigest()\n        binding["source_semantic_sha256"] = script_semantic_digest(requested_script)\n    document = parse_script_markdown(snapshot.read_text(encoding="utf-8-sig"), page_contracts={})\n    records = [_page_record(page) for page in document.pages]\n    return {\n        "schema": "cyberppt.stage02_script_input.v1",\n        "project": str(project),\n        "created_at": _utc_now(),\n        "source_bindings": {"script": binding},\n        "page_order": [record["page_id"] for record in records],\n        "pages": records,\n    }\n\n\n# Legacy API alias.\ndef build_stage02_handoff(\n    project: Path,\n    *,\n    script: Path | None = None,\n    lightweight_stage01_confirmed: bool = False,\n    allow_script_edit: bool = False,\n) -> dict[str, Any]:\n    return build_stage02_input(\n        project, script=script, lightweight_input_confirmed=lightweight_stage01_confirmed,\n        allow_script_edit=allow_script_edit,\n    )\n'''
text = sub_once(
    text,
    r"def build_stage02_handoff\(\n.*?\n\ndef render_handoff_markdown",
    new_builder + "\n\ndef render_handoff_markdown",
    label="file-only intake builder",
    flags=re.S,
)
text = text.replace("# Stage 01 → Stage 02 字段交接审阅", "# Stage 02 脚本输入审阅")
text = text.replace("上游关系", "输入关系")
text = text.replace("Stage 02 视觉输入", "视觉设计输入")
text = text.replace("Stage 02 handoff schema is invalid.", "Stage 02 script input schema is invalid.")
text = text.replace("Binding {name} is absent or incomplete for the current input file authority.", "Binding {name} is absent or incomplete for the current input file.")
# Accept current input schema; legacy is accepted only for migration reads.
text = replace_once(
    text,
    '    if payload.get("schema") != "cyberppt.stage02_handoff.v1":\n        issue("HANDOFF_SCHEMA_INVALID", "Stage 02 script input schema is invalid.")\n',
    '    if payload.get("schema") not in {"cyberppt.stage02_script_input.v1", "cyberppt.stage02_handoff.v1"}:\n        issue("HANDOFF_SCHEMA_INVALID", "Stage 02 script input schema is invalid.")\n',
    label="input schema audit",
)
# Audit the input source path without requiring an upstream process snapshot.
text = sub_once(
    text,
    r"        if name == \"script\" and binding.get\(\"source_mode\"\) == \"external_script\":\n.*?\n\n    pages = payload.get\(\"pages\"\)",
    '''        source_path = str(binding.get("source_path") or "").strip()\n        if source_path:\n            source = Path(source_path).expanduser()\n            if source.is_file():\n                source = source.resolve()\n                source_sha = hashlib.sha256(source.read_bytes()).hexdigest()\n                source_semantic = semantic_digest(source)\n                if binding.get("source_sha256") and binding.get("source_sha256") != source_sha:\n                    issue("INPUT_SOURCE_CHANGED", f"The supplied script file changed after Stage 02 snapshotted it: {source}")\n                if binding.get("source_semantic_sha256") and binding.get("source_semantic_sha256") != source_semantic:\n                    issue("INPUT_SOURCE_CHANGED", f"The supplied script semantics changed after Stage 02 snapshotted it: {source}")\n\n    pages = payload.get("pages")''',
    label="source-file audit",
    flags=re.S,
)
text = text.replace('features = visual.get("input_relationship_features")', 'features = visual.get("input_relationship_features")')
text = text.replace("STAGE01_RELATIONSHIP_FEATURES_MISSING", "INPUT_RELATIONSHIP_FEATURES_MISSING")
text = text.replace("STAGE01_RELATIONSHIP_FEATURES_AUTHORITY_INVALID", "INPUT_RELATIONSHIP_FEATURES_AUTHORITY_INVALID")
text = text.replace("STAGE01_RELATIONSHIP_ACTIONS_MISSING", "INPUT_RELATIONSHIP_ACTIONS_MISSING")
text = text.replace('features.get("authority") != "input_semantic_handoff"', 'features.get("authority") != "input_script"')
text = text.replace('"schema": "cyberppt.stage02_handoff_audit.v1"', '"schema": "cyberppt.stage02_script_input_audit.v1"')
text = text.replace('"handoff": str(handoff_path.resolve())', '"input": str(handoff_path.resolve())')

# Canonical prepare/load names plus compatibility aliases.
text = text.replace("def prepare_stage02_handoff(\n", "def prepare_stage02_input(\n", 1)
text = text.replace("lightweight_stage01_confirmed: bool = False", "lightweight_input_confirmed: bool = False", 1)
text = text.replace("reuse_current_handoff: bool = False", "reuse_current_input: bool = False", 1)
text = text.replace("_ = lightweight_stage01_confirmed", "_ = lightweight_input_confirmed", 1)
text = text.replace("payload = build_stage02_handoff(project, script=script, allow_script_edit=allow_script_edit)", "payload = build_stage02_input(project, script=script, allow_script_edit=allow_script_edit)", 1)
text = text.replace("if reuse_current_handoff and handoff_path.is_file():", "if reuse_current_input and handoff_path.is_file():", 1)
text = text.replace("report = audit_stage02_handoff(project, current)", "report = audit_stage02_handoff(project, current)", 1)
text = text.replace("def load_stage02_handoff(project: Path, *, required: bool = False)", "def load_stage02_input(project: Path, *, required: bool = False)", 1)
text = text.replace("Stage 02 handoff is missing", "Stage 02 script input is missing")
text = text.replace("Stage 02 handoff is invalid or stale", "Stage 02 script input is invalid or stale")
text = text.replace("def handoff_page_map(payload: dict[str, Any])", "def input_page_map(payload: dict[str, Any])", 1)

# Append explicit compatibility wrappers before __all__.
compat = '''\n\ndef prepare_stage02_handoff(\n    project: Path, *, script: Path | None = None, lightweight_stage01_confirmed: bool = False,\n    reuse_current_handoff: bool = False, allow_script_edit: bool = False,\n) -> dict[str, Any]:\n    return prepare_stage02_input(\n        project, script=script, lightweight_input_confirmed=lightweight_stage01_confirmed,\n        reuse_current_input=reuse_current_handoff, allow_script_edit=allow_script_edit,\n    )\n\n\ndef load_stage02_handoff(project: Path, *, required: bool = False) -> dict[str, Any] | None:\n    return load_stage02_input(project, required=required)\n\n\ndef handoff_page_map(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:\n    return input_page_map(payload)\n'''
text = replace_once(text, "\n\n__all__ = [", compat + "\n\n__all__ = [", label="compat wrappers")
# Replace exported list completely.
text = sub_once(
    text,
    r"__all__ = \[\n.*?\n\]",
    '''__all__ = [\n    "INPUT_AUDIT", "INPUT_DIR", "INPUT_JSON", "INPUT_REVIEW", "INPUT_SCRIPT_PATH",\n    "audit_stage02_handoff", "build_stage02_input", "input_page_map", "load_stage02_input",\n    "normalize_page_id", "prepare_stage02_input", "snapshot_input_script",\n    # compatibility\n    "HANDOFF_AUDIT", "HANDOFF_JSON", "HANDOFF_MD", "SCRIPT_PATH",\n    "build_stage02_handoff", "handoff_page_map", "load_stage02_handoff",\n    "prepare_stage02_handoff", "render_handoff_markdown",\n]''',
    label="exports",
    flags=re.S,
)
write(path, text)

# Thin canonical import surface for Stage 02 runtime.
write(
    "cyberppt/stage02_input.py",
    '''"""Canonical Stage 02 file-input boundary.\n\nStage 02 consumes a script file and owns every artifact created after the file\nboundary. It has no dependency on Stage 01 workflow state.\n"""\nfrom cyberppt.stage02_handoff import (\n    INPUT_AUDIT, INPUT_DIR, INPUT_JSON, INPUT_REVIEW, INPUT_SCRIPT_PATH,\n    BODY_CANVAS, audit_stage02_handoff as audit_stage02_input, build_stage02_input,\n    input_page_map, load_stage02_input, normalize_page_id, prepare_stage02_input,\n    snapshot_input_script,\n)\n\n__all__ = [\n    "INPUT_AUDIT", "INPUT_DIR", "INPUT_JSON", "INPUT_REVIEW", "INPUT_SCRIPT_PATH",\n    "BODY_CANVAS", "audit_stage02_input", "build_stage02_input", "input_page_map",\n    "load_stage02_input", "normalize_page_id", "prepare_stage02_input",\n    "snapshot_input_script",\n]\n''',
)

# Visual structure: consume Stage 02 input, never orchestrate a cross-stage handoff.
path = "cyberppt/visual_stage/execution.py"
text = read(path)
text = text.replace("handoff", "script_input")
text = text.replace("Handoff", "ScriptInput")
text = text.replace("HANDOFF", "INPUT")
# Repair imported API names after mechanical neutralization.
text = text.replace("from cyberppt.stage02_input import INPUT_JSON, ensure_project_script, prepare_stage02_input", "from cyberppt.stage02_input import INPUT_JSON, audit_stage02_input, prepare_stage02_input, snapshot_input_script")
text = text.replace("script = ensure_project_script(project, script)", "source_script = script\n    script = snapshot_input_script(project, source_script)")
text = text.replace("from cyberppt.stage02_input import audit_stage02_input\n\n", "")
# Always prepare/refresh the Stage2-owned intake from the supplied file; reuse is internal.
text = sub_once(
    text,
    r"    script_input = project / INPUT_JSON\n    from cyberppt.stage02_input import audit_stage02_input\n\n    if reuse_current_script_input:.*?    design_input = _write_visual_design_input\(project, script_input\)",
    '''    script_input = project / INPUT_JSON\n    report = prepare_stage02_input(project, script=source_script, reuse_current_input=True)\n    if report.get("status") != "passed":\n        codes = ", ".join(item.get("code", "INPUT_INVALID") for item in report.get("blocking_issues", []))\n        raise ValueError(f"Stage 02 script input is invalid: {codes}")\n    design_input = _write_visual_design_input(project, script_input)''',
    label="visual stage input preparation",
    flags=re.S,
)
# Compatibility argument names can remain at facade; internal execution ignores it.
text = text.replace("reuse_current_script_input: bool = False", "reuse_current_handoff: bool = False")
text = text.replace("_ = lightweight_stage01_confirmed", "_ = lightweight_stage01_confirmed, reuse_current_handoff")
# Neutral fields consumed by the designer.
text = text.replace('visual.get("input_relationship_features") or {}', 'visual.get("input_relationship_features") or {}')
text = text.replace('"input_relationship_features": visual.get("input_relationship_features") or {},', '"input_relationship_features": visual.get("input_relationship_features") or {},')
text = text.replace("input_semantic_handoff", "input_script")
write(path, text)

# Product facade keeps old argument names but delegates to the file-boundary implementation.
path = "cyberppt/commands/visual_structure_stage.py"
text = read(path)
# No runtime imports of the compatibility handoff module are introduced here; execution owns input preparation.
write(path, text)

# Stage02 preflight: every script path is just a file input; no separate handoff prerequisite.
path = "cyberppt/stage02_production/preflight.py"
text = read(path)
text = replace_once(
    text,
    "from cyberppt.stage02_handoff import HANDOFF_JSON, ensure_project_script\n",
    "from cyberppt.stage02_input import INPUT_JSON, prepare_stage02_input, snapshot_input_script\n",
    label="preflight input import",
)
text = sub_once(
    text,
    r"    if not script.is_file\(\) and not options.external_script:\n.*?\n\n    autonomous_contract_path",
    '''    source_script = script\n    if not source_script.is_file():\n        # Resume may use the Stage2-owned snapshot only when its input binding is still valid.\n        snapshot = project / "workbench/inputs/final-script.md"\n        if not snapshot.is_file():\n            raise FileNotFoundError(f"script input not found: {source_script}")\n    script = snapshot_input_script(project, source_script)\n\n    autonomous_contract_path''',
    label="preflight uniform script input",
    flags=re.S,
)
text = text.replace('source_mode = "autonomous_contract" if autonomous_authority is not None else "external_script" if options.external_script else "formal_project_script"', 'source_mode = "autonomous_contract" if autonomous_authority is not None else "script_file"')
text = replace_once(
    text,
    "    from cyberppt.commands.visual_structure_stage import assert_visual_structure_ready\n    from cyberppt.stage02_handoff import load_stage02_handoff\n\n    load_stage02_handoff(project, required=True)\n    assert_visual_structure_ready(project, script)\n",
    "    from cyberppt.commands.visual_structure_stage import assert_visual_structure_ready\n\n    input_report = prepare_stage02_input(project, script=source_script, reuse_current_input=True)\n    if input_report.get(\"status\") != \"passed\":\n        codes = \", \".join(item.get(\"code\", \"INPUT_INVALID\") for item in input_report.get(\"blocking_issues\", []))\n        raise ValueError(f\"Stage 02 script input is invalid: {codes}\")\n    assert_visual_structure_ready(project, script)\n",
    label="preflight prepare input",
)
text = text.replace("handoff_path = project / HANDOFF_JSON", "input_path = project / INPUT_JSON")
text = text.replace("handoff_sha256=sha256_file(handoff_path) or \"\"", "handoff_sha256=sha256_file(input_path) or \"\"")
write(path, text)

# Build context gets a neutral input hash while preserving the deprecated field.
path = "cyberppt/stage02_production/models.py"
text = read(path)
text = replace_once(
    text,
    "    source_script_sha256: str\n    handoff_sha256: str\n",
    "    source_script_sha256: str\n    script_input_sha256: str\n    handoff_sha256: str  # deprecated compatibility alias\n",
    label="build context input hash",
)
write(path, text)
path = "cyberppt/stage02_production/preflight.py"
text = read(path)
text = replace_once(
    text,
    '        source_script_sha256=sha256_file(script) or "",\n        handoff_sha256=sha256_file(input_path) or "",\n',
    '        source_script_sha256=sha256_file(script) or "",\n        script_input_sha256=sha256_file(input_path) or "",\n        handoff_sha256=sha256_file(input_path) or "",\n',
    label="populate input hash",
)
write(path, text)

# Add an architecture regression test that defines loose coupling in executable terms.
write(
    "tests/test_stage_file_boundary.py",
    '''from __future__ import annotations\n\nfrom pathlib import Path\nfrom tempfile import TemporaryDirectory\n\nfrom cyberppt.stage02_input import INPUT_JSON, build_stage02_input, prepare_stage02_input\n\n\nSCRIPT = """# Demo\n\n## P01 文件边界\n\n- 页面类型：内容页\n- 页面标题：文件边界\n- 内容负载：standard\n- 页面使命：说明两个阶段通过文件对接\n- 核心结论：Stage2 只消费脚本文件\n\n### 完整文字稿\n\nStage2 只读取当前输入文件，不读取 Foundation、Deck Plan、Source Truth 或 Outline。\n\n### 上屏文字\n\n- 输入文件：Final Script 是唯一跨阶段输入\n  - Stage2 自行派生视觉结构和生产产物\n\n### 视觉结构\n\n输入文件 → Stage2：file boundary\n"""\n\n\ndef test_stage2_input_is_portable_and_ignores_stage1_project_state() -> None:\n    with TemporaryDirectory() as directory:\n        root = Path(directory)\n        stage1 = root / "unrelated-stage1-project"\n        stage1.mkdir()\n        script = stage1 / "final-script.md"\n        script.write_text(SCRIPT, encoding="utf-8")\n        # Deliberately conflicting Stage1 internals must be invisible to Stage2.\n        (stage1 / "deck-plan.json").write_text('{"pages":[]}', encoding="utf-8")\n        (stage1 / "foundation.json").write_text('{"facts":[]}', encoding="utf-8")\n\n        stage2 = root / "stage2-workspace"\n        payload = build_stage02_input(stage2, script=script)\n\n        assert payload["schema"] == "cyberppt.stage02_script_input.v1"\n        assert payload["pages"][0]["title"] == "文件边界"\n        assert payload["pages"][0]["content_load"] == "standard"\n        assert payload["source_bindings"]["script"]["source_path"] == str(script.resolve())\n        assert (stage2 / "workbench/inputs/final-script.md").is_file()\n\n        report = prepare_stage02_input(stage2, script=script, reuse_current_input=True)\n        assert report["status"] == "passed"\n        assert (stage2 / INPUT_JSON).is_file()\n\n\ndef test_stage2_runtime_does_not_import_stage1_workflow_artifacts() -> None:\n    repo = Path(__file__).resolve().parents[1]\n    runtime_files = [\n        repo / "cyberppt/stage02_handoff.py",\n        repo / "cyberppt/stage02_input.py",\n        repo / "cyberppt/visual_stage/execution.py",\n        repo / "cyberppt/stage02_production/preflight.py",\n    ]\n    forbidden = ("deck-plan.json", "foundation.json", "source-truth.json", "outline.json")\n    text = "\\n".join(path.read_text(encoding="utf-8") for path in runtime_files)\n    for token in forbidden:\n        assert token not in text\n''',
)

# Documentation: define a file boundary, remove the separate handoff prerequisite from formal flow.
for path in ("README.md", "docs/CYBERPPT_WORKFLOW.md", ".agents/skills/cyberppt-stage02-editable-pptx/SKILL.md"):
    text = read(path)
    text = text.replace("Stage 01 → Stage 02", "Final Script 文件 → Stage 02")
    text = text.replace("Stage 01 to Stage 02", "Final Script file to Stage 02")
    text = text.replace("Stage 02 handoff", "Stage 02 script input")
    text = text.replace("stage02_handoff.json", "script-intake.json")
    text = text.replace("prepare-stage02-handoff", "Stage2 自动脚本输入快照")
    text = text.replace("handoff", "script input")
    write(path, text)

print("stage-file-boundary patch applied")
