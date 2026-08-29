from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


# Canonical Stage 02 boundary: one script file, snapshotted into Stage 02.
write(
    "cyberppt/stage02_input.py",
    r'''"""Stage 02 file-input boundary.

Stage 02 accepts one script file, snapshots it into its own workspace, and
builds all downstream visual/production state from that snapshot. The producer
of the file is intentionally unknown to this module.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any

from cyberppt.artifact_ledger import write_json_atomic
from cyberppt.content_integrity_contract import build_content_integrity_contract, extract_onscreen_line_items
from cyberppt.onscreen_expression import expression_constraints, resolve_onscreen_expression
from cyberppt.script_quality_contract import ScriptPage, parse_script_markdown
from cyberppt.semantic_digest import script_semantic_digest
from cyberppt.semantic_verifier import verify_semantic_proposals
from cyberppt.stage02_semantic_intake import normalize_semantic_proposals
from cyberppt.topology_resolver import resolve_semantic_topology
from cyberppt.visual_structure_contract import normalize_page_id

INPUT_DIR = Path("workbench/stages/02-input")
INPUT_JSON = INPUT_DIR / "script-intake.json"
INPUT_AUDIT = INPUT_DIR / "script-intake-audit.json"
INPUT_REVIEW = INPUT_DIR / "script-intake-review.md"
INPUT_SCRIPT_PATH = Path("workbench/inputs/final-script.md")
LEGACY_INPUT_JSON = Path("workbench/stages/02-handoff/stage02-handoff.json")
BODY_CANVAS = {"width": 2048, "height": 1024, "ratio": "2:1"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_role(page_type: str) -> str:
    return {"cover":"cover","contents":"agenda","agenda":"agenda","chapter":"section","section":"section","closing":"ending","ending":"ending","content":"content"}.get(page_type,"content")


def _onscreen_items(page: ScriptPage) -> list[str]:
    return [text for text, _indent in extract_onscreen_line_items(page.onscreen_text)]


def _locked_text_items(page: ScriptPage) -> list[dict[str, Any]]:
    page_id = normalize_page_id(page.page_id, page.sequence).upper()
    return [{"text_id": f"{page_id}-T{index:02d}", "text": text, "ordinal": index} for index, text in enumerate(_onscreen_items(page), start=1)]


def _relationship_features(relationships: list[dict[str, Any]], visual_notes: str, *, authority: str) -> dict[str, Any]:
    actors = list(dict.fromkeys(str(item.get("subject") or "").strip() for item in relationships if isinstance(item, dict) and str(item.get("subject") or "").strip()))
    actions: list[dict[str, Any]] = []
    for item in relationships:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject") or "").strip(); relation = str(item.get("relation") or "").strip()
        for raw in item.get("objects") or []:
            obj = str(raw or "").strip()
            if obj: actions.append({"subject": subject, "relation": relation, "object": obj})
    notes = re.split(r"\n\s*-\s*【(?:视觉结构，不上屏|演讲者备注)】", str(visual_notes or ""), maxsplit=1)[0]
    clauses = [value.strip(" ；。\n") for value in notes.replace("\n", "；").split("；") if value.strip(" ；。\n")]
    select = lambda tokens: [value for value in clauses if any(token in value for token in tokens)]
    return {"authority": authority, "actors": actors, "actions": actions, "directions": select(("进入","形成","转化","承接","汇聚","贯通","连接","回到")), "conditions": select(("条件","只有","仅","若","如果","通过后","满足")), "branches": select(("分支","互斥","分别","三类","两类","暂停","终止","再验证")), "feedback": select(("反馈","回流","复盘","迭代","持续更新","回到")), "source_visual_notes": notes.strip()}


def _reject_invalid_authoritative_relations(page_id: str, verification: dict[str, Any]) -> None:
    blockers = [item for item in verification.get("verdicts") or [] if isinstance(item, dict) and str(item.get("verdict") or "") in {"rejected","unresolved"} and str(item.get("constraint_authority") or "soft") in {"hard","strong"}]
    if blockers:
        details = "; ".join(f"{item.get('proposal_id') or '?'}:{item.get('verdict')}:{','.join(item.get('conflict_codes') or [])}" for item in blockers)
        raise ValueError(f"input script relationship contract is invalid for {page_id}: {details}")


def _page_record(page: ScriptPage) -> dict[str, Any]:
    page_mission = str(page.page_mission or page.main_message); source_refs = tuple(page.source_refs); render_role = _render_role(page.page_type); content_load = page.content_load or "standard"
    business_relationships = [dict(item) for item in page.content_relations if isinstance(item, dict)]
    input_features = _relationship_features(business_relationships, page.visual_structure, authority="input_script")
    proposals = list(normalize_semantic_proposals(business_relationships, default_source_refs=source_refs, origin="input_file"))
    verification = verify_semantic_proposals(proposals, page_text="\n".join((page_mission,page.main_message,page.full_prose,page.onscreen_text)), visual_notes=page.visual_structure)
    verified_relationships = [dict(item) for item in verification.get("verified_relationships") or [] if isinstance(item, dict)]
    _reject_invalid_authoritative_relations(page.page_id, verification)
    verified_features = _relationship_features(verified_relationships, page.visual_structure, authority="stage02_semantic_verifier")
    render_topology = resolve_semantic_topology(verified_relationships, module_count=len(page.top_level_module_titles), page_text="\n".join((page_mission,page.main_message,page.full_prose,page.onscreen_text)))
    directed = {"sequence","dependency_chain","causal_chain","feedback_loop","layered_structure","support_convergence"}
    has_direction = any(bool(str(item.get("direction") or "").strip() or str(item.get("condition") or "").strip()) for item in business_relationships)
    prompt_mode = "directed_composition" if str(render_topology.get("primary_topology") or "") in directed and has_direction else "semantic_brief"
    action_text = tuple(" ".join(str(item.get(field) or "") for field in ("subject","relation","object")).strip() for item in input_features["actions"] if isinstance(item, dict))
    expression = resolve_onscreen_expression(page, page_mission=page_mission, business_relationships=business_relationships, actions=action_text, topic_category="", semantic_topology=render_topology).to_dict()
    expression["constraint_authority"] = str(render_topology.get("constraint_authority") or "soft")
    constraints = expression_constraints(str(expression["form"])); locked = _locked_text_items(page); integrity = build_content_integrity_contract(page).to_dict()
    receipt = page.contract_receipt if isinstance(page.contract_receipt, dict) else {}; expression_ir = receipt.get("onscreen_expression_ir") if isinstance(receipt.get("onscreen_expression_ir"), dict) else None
    record: dict[str, Any] = {"page_id": normalize_page_id(page.page_id,page.sequence), "page_number": page.sequence, "render_role": render_role, "argument_role":"", "title":page.title, "subtitle":page.subtitle, "content_load":content_load, "page_mission":page_mission, "core_message":page.main_message, "full_prose":page.full_prose, "onscreen_text":page.onscreen_text, "onscreen_items":_onscreen_items(page), "locked_text_items":locked, "content_integrity":integrity, "image_locked_text":page.image_locked_text, "editable_body_text":page.onscreen_text, "speaker_notes":page.speaker_notes, "source_refs":list(source_refs), "provenance_refs":list(page.provenance_refs), "argument_chain":page.argument_chain, "prompt_mode":prompt_mode, "business_relationships":business_relationships, "semantic_proposals":proposals, "semantic_verification":verification, "verified_business_relationships":verified_relationships, "render_topology":render_topology, "onscreen_expression":expression, "onscreen_expression_ir":expression_ir, "expression_constraints":constraints, "field_provenance":{"content":"input_script","business_relationships":"input_script","render_topology":"stage02_derived","visual_structure":"stage02_derived","style":"stage02_owned"}}
    if render_role != "content": record["stage02_visual_input"] = None; return record
    record["stage02_visual_input"] = {"page_mission":page_mission,"core_message":page.main_message,"full_prose":page.full_prose,"content_load":content_load,"argument_chain":page.argument_chain,"prompt_mode":prompt_mode,"onscreen_text":page.onscreen_text,"locked_text_items":locked,"content_integrity":integrity,"module_titles":list(page.module_titles),"top_level_module_titles":list(page.top_level_module_titles),"business_relationships":business_relationships,"input_relationship_features":input_features,"semantic_proposals":proposals,"semantic_verification":verification,"verified_business_relationships":verified_relationships,"verified_relationship_features":verified_features,"render_topology":render_topology,"relationship_authority":"input_file_authoritative","onscreen_expression":expression,"onscreen_expression_ir":expression_ir,"expression_constraints":constraints,"constraint_authority":expression["constraint_authority"],"author_visual_notes":page.visual_structure,"author_visual_notes_authority":"advisory_only","must_not_include":[],"body_image_canvas":dict(BODY_CANVAS),"title_render_mode":"external_text_layer","subtitle_render_mode":"external_text_layer"}
    return record


def input_path(project: Path) -> Path:
    project = project.expanduser().resolve(); current = project / INPUT_JSON
    if current.is_file(): return current
    legacy = project / LEGACY_INPUT_JSON
    return legacy if legacy.is_file() else current


def snapshot_input_script(project: Path, source_script: Path) -> Path:
    project = project.expanduser().resolve(); source = source_script.expanduser().resolve(); target = (project / INPUT_SCRIPT_PATH).resolve()
    if source == target:
        if not target.is_file(): raise FileNotFoundError(f"Stage 02 script snapshot is missing: {target}")
        return target
    if source.is_file(): target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source,target); return target
    if target.is_file():
        path = input_path(project)
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8")); binding = (payload.get("source_bindings") or {}).get("script") or {}; recorded = str(binding.get("source_path") or binding.get("external_path") or "").strip()
            if recorded and Path(recorded).expanduser().resolve() == source and binding.get("sha256") == _sha256(target): return target
    raise FileNotFoundError(f"Stage 02 script input is missing: {source}")


def resolve_input_script(project: Path, source_script: Path) -> Path:
    project = project.expanduser().resolve(); source = source_script.expanduser().resolve(); target = (project / INPUT_SCRIPT_PATH).resolve(); path = input_path(project)
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8")); binding = (payload.get("source_bindings") or {}).get("script") or {}
        if payload.get("schema") == "cyberppt.stage02_script_input.v1":
            recorded = str(binding.get("source_path") or "").strip()
            if recorded and Path(recorded).expanduser().resolve() == source:
                if source.is_file() and binding.get("source_sha256") and binding.get("source_sha256") != _sha256(source): raise ValueError("Stage 02 script input changed; rebuild Stage 02 visual artifacts from the updated file")
                if target.is_file() and binding.get("sha256") == _sha256(target): return target
        else:
            raw = str(binding.get("path") or "").strip(); legacy_script = (project / raw).resolve() if binding.get("scope") == "project" else Path(raw).expanduser().resolve()
            if legacy_script.is_file() and (source == legacy_script or source == target): return legacy_script
    if source == target and source.is_file(): return source
    raise ValueError("Stage 02 script input is not prepared for this file; prepare the Stage 02 visual stage again")


def build_stage02_input(project: Path, *, script: Path) -> dict[str, Any]:
    project = project.expanduser().resolve(); source = script.expanduser().resolve(); snapshot = snapshot_input_script(project,source)
    document = parse_script_markdown(snapshot.read_text(encoding="utf-8-sig"), page_contracts={}); records = [_page_record(page) for page in document.pages]
    binding: dict[str, Any] = {"scope":"project","path":INPUT_SCRIPT_PATH.as_posix(),"sha256":_sha256(snapshot),"semantic_sha256":script_semantic_digest(snapshot),"source_path":str(source)}
    if source.is_file(): binding["source_sha256"]=_sha256(source); binding["source_semantic_sha256"]=script_semantic_digest(source)
    return {"schema":"cyberppt.stage02_script_input.v1","project":str(project),"created_at":_utc_now(),"source_bindings":{"script":binding},"page_order":[record["page_id"] for record in records],"pages":records}


def input_page_map(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(page.get("page_number") or 0):page for page in payload.get("pages") or [] if isinstance(page,dict) and int(page.get("page_number") or 0)>0}


def audit_stage02_input(project: Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    project=project.expanduser().resolve(); path=input_path(project)
    if payload is None:
        if not path.is_file(): return {"schema":"cyberppt.stage02_script_input_audit.v1","status":"failed","blocking_issues":[{"code":"INPUT_MISSING","message":f"Stage 02 script input is missing: {path}"}]}
        payload=json.loads(path.read_text(encoding="utf-8"))
    issues:list[dict[str,str]]=[]
    if payload.get("schema")=="cyberppt.stage02_script_input.v1":
        binding=(payload.get("source_bindings") or {}).get("script") or {}; snapshot=(project/str(binding.get("path") or INPUT_SCRIPT_PATH)).resolve()
        if not snapshot.is_file() or binding.get("sha256")!=_sha256(snapshot): issues.append({"code":"INPUT_SNAPSHOT_STALE","message":"Stage 02-owned script snapshot is missing or changed."})
        source_path=str(binding.get("source_path") or "").strip()
        if source_path:
            source=Path(source_path).expanduser()
            if source.is_file() and binding.get("source_sha256") and binding.get("source_sha256")!=_sha256(source.resolve()): issues.append({"code":"INPUT_SOURCE_CHANGED","message":"The supplied script file changed after Stage 02 prepared its input snapshot."})
        if not isinstance(payload.get("pages"),list) or not payload.get("pages"): issues.append({"code":"INPUT_PAGES_MISSING","message":"Stage 02 script input contains no pages."})
    elif payload.get("schema")!="cyberppt.stage02_handoff.v1": issues.append({"code":"INPUT_SCHEMA_INVALID","message":"Unsupported Stage 02 input schema."})
    return {"schema":"cyberppt.stage02_script_input_audit.v1","status":"passed" if not issues else "failed","blocking_issues":issues}


def prepare_stage02_input(project: Path, *, script: Path, reuse_current: bool=True) -> dict[str, Any]:
    project=project.expanduser().resolve(); source=script.expanduser().resolve(); current=project/INPUT_JSON
    if reuse_current and current.is_file():
        existing=json.loads(current.read_text(encoding="utf-8")); binding=(existing.get("source_bindings") or {}).get("script") or {}; recorded=str(binding.get("source_path") or "").strip(); same=bool(recorded) and Path(recorded).expanduser().resolve()==source; fresh=not source.is_file() or not binding.get("source_sha256") or binding.get("source_sha256")==_sha256(source); report=audit_stage02_input(project,existing)
        if same and fresh and report.get("status")=="passed": report["reused"]=True; return report
    payload=build_stage02_input(project,script=source); current.parent.mkdir(parents=True,exist_ok=True); write_json_atomic(current,payload); report=audit_stage02_input(project,payload); write_json_atomic(project/INPUT_AUDIT,report); (project/INPUT_REVIEW).write_text("# Stage 02 script input\n\n"+"\n".join(f"- P{page['page_number']:02d} {page.get('title','')}" for page in payload.get("pages") or [])+"\n",encoding="utf-8",newline="\n"); report["reused"]=False; return report


def load_stage02_input(project: Path, *, required: bool=False) -> dict[str, Any] | None:
    path=input_path(project)
    if not path.is_file():
        if required: raise FileNotFoundError(f"Stage 02 script input is missing: {path}")
        return None
    payload=json.loads(path.read_text(encoding="utf-8")); report=audit_stage02_input(project,payload)
    if required and report.get("status")!="passed": raise ValueError("Stage 02 script input is invalid or stale")
    return payload

__all__=["BODY_CANVAS","INPUT_AUDIT","INPUT_DIR","INPUT_JSON","INPUT_REVIEW","INPUT_SCRIPT_PATH","audit_stage02_input","build_stage02_input","input_page_map","input_path","load_stage02_input","prepare_stage02_input","resolve_input_script","snapshot_input_script"]
''')

# Visual structure reads Stage2 input snapshot.
path="cyberppt/visual_stage/execution.py"; text=read(path)
text=text.replace('def _write_visual_design_input(project: Path, handoff: Path) -> Path:\n    payload = _read_json(handoff)','def _write_visual_design_input(project: Path, script_input: Path) -> Path:\n    payload = _read_json(script_input)')
text=text.replace('"source": str(handoff),','"source": str(script_input),').replace('"source_sha256": _sha256(handoff),','"source_sha256": _sha256(script_input),')
text=text.replace('"stage01_relationship_features": visual.get("stage01_relationship_features") or {},','"input_relationship_features": visual.get("input_relationship_features") or visual.get("stage01_relationship_features") or {},')
text=text.replace('"business_relationships is Stage 01 semantic authority; render_topology is Stage 02-derived "','"business_relationships comes from the input script file; render_topology is Stage 02-derived "')
old='''    _ = lightweight_stage01_confirmed
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
'''
new='''    _ = lightweight_stage01_confirmed, reuse_current_handoff
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
'''
if old not in text: raise RuntimeError("visual prepare block missing")
text=text.replace(old,new,1).replace('f"- stage02_handoff: {handoff}"','f"- stage02_script_input: {script_input}"').replace('derived only from stage02_handoff.json','derived only from the Stage 02 script input snapshot').replace('use stage01_relationship_features','use input_relationship_features').replace('stage01_visual_note_disposition','input_visual_note_disposition').replace('audited Stage 02 handoff','audited Stage 02 script input').replace('"- mode: workbench-handoff"','"- mode: stage02-file-input"')
text=text.replace('def execute_visual_structure_stage(project: Path, script: Path) -> dict[str, Path]:\n    project, script = project.expanduser().resolve(), script.expanduser().resolve()','def execute_visual_structure_stage(project: Path, script: Path) -> dict[str, Path]:\n    project, script = project.expanduser().resolve(), script.expanduser().resolve()\n    from cyberppt.stage02_input import resolve_input_script\n    script = resolve_input_script(project, script)')
text=text.replace('    project = project.expanduser().resolve()\n    script = script.expanduser().resolve()\n    if not executor.strip() or not model.strip():','    project = project.expanduser().resolve()\n    script = script.expanduser().resolve()\n    from cyberppt.stage02_input import resolve_input_script\n    script = resolve_input_script(project, script)\n    if not executor.strip() or not model.strip():',1)
text=text.replace('def _audit_execution_receipt(project: Path, script: Path, skill_root: Path) -> dict[str, Any]:\n    issues: list[dict[str, str]] = []','def _audit_execution_receipt(project: Path, script: Path, skill_root: Path) -> dict[str, Any]:\n    from cyberppt.stage02_input import resolve_input_script\n    script = resolve_input_script(project, script)\n    issues: list[dict[str, str]] = []')
write(path,text)

# Visual audit binds to Stage2 input.
path="cyberppt/visual_stage/audit.py"; text=read(path)
text=text.replace('    project = project.expanduser().resolve()\n    script = script.expanduser().resolve()\n    skill_root = _skill_root()','    project = project.expanduser().resolve()\n    script = script.expanduser().resolve()\n    from cyberppt.stage02_input import input_path, load_stage02_input, resolve_input_script\n    script = resolve_input_script(project, script)\n    skill_root = _skill_root()',1)
text=text.replace('    from cyberppt.stage02_handoff import HANDOFF_JSON, load_stage02_handoff\n\n    handoff = load_stage02_handoff(project, required=True)\n    handoff_path = project / HANDOFF_JSON','    script_input = load_stage02_input(project, required=True)\n    script_input_path = input_path(project)')
text=text.replace('if design_payload.get("source_sha256") != _sha256(handoff_path):','if design_payload.get("source_sha256") != _sha256(script_input_path):').replace('visual-design-input.json is stale for the current Stage 02 handoff','visual-design-input.json is stale for the current Stage 02 script input')
text=text.replace('"stage02_handoff": str(handoff_path) if handoff is not None else None,\n        "stage02_handoff_sha256": _sha256(handoff_path),','"stage02_script_input": str(script_input_path) if script_input is not None else None,\n        "stage02_script_input_sha256": _sha256(script_input_path),')
write(path,text)

# Readiness gate uses Stage2 input.
path="cyberppt/visual_stage/prompt_gate.py"; text=read(path)
text=text.replace('    project = project.expanduser().resolve()\n    script = script.expanduser().resolve()\n    if not visual_structure_required(project):','    project = project.expanduser().resolve()\n    script = script.expanduser().resolve()\n    from cyberppt.stage02_input import input_path, load_stage02_input, resolve_input_script\n    script = resolve_input_script(project, script)\n    if not visual_structure_required(project):')
start=text.index('    from cyberppt.stage02_handoff import load_stage02_handoff\n'); end=text.index('    for key in (\n',start)
text=text[:start]+'''    script_input = load_stage02_input(project, required=True)
    input_file = input_path(project)
    design_input = _read_json(project / VISUAL_FILES["design_input"])
    if design_input.get("source_sha256") != _sha256(input_file):
        raise ValueError("visual structure design input is stale for the current Stage 02 script input")
'''+text[end:]
old='''    handoff_path = project / Path("workbench/stages/02-handoff/stage02-handoff.json")
    design_input = _read_json(project / VISUAL_FILES["design_input"])
    if design_input.get("source_sha256") != _sha256(handoff_path):
        raise ValueError(
            "visual structure design input is stale: it was compiled from a different Stage 02 handoff"
        )
    handoff_pages = {
        str(page.get("page_id")): page
        for page in handoff.get("pages") or []
        if isinstance(page, dict) and page.get("page_id")
    }
'''
new='''    input_pages = {
        str(page.get("page_id")): page
        for page in script_input.get("pages") or []
        if isinstance(page, dict) and page.get("page_id")
    }
'''
if old not in text: raise RuntimeError("prompt gate source block missing")
text=text.replace(old,new,1).replace('source_page = handoff_pages.get(page_id.lower()) or handoff_pages.get(page_id.upper())','source_page = input_pages.get(page_id.lower()) or input_pages.get(page_id.upper())')
write(path,text)

# Production preflight treats every script as a generic file.
path="cyberppt/stage02_production/preflight.py"; text=read(path)
text=text.replace('from cyberppt.stage02_handoff import HANDOFF_JSON, ensure_project_script\n','from cyberppt.stage02_input import INPUT_JSON, prepare_stage02_input, resolve_input_script\n')
old='''    if not script.is_file() and not options.external_script:
        raise FileNotFoundError(f"final script not found: {script}")
    if options.external_script:
        script = ensure_project_script(project, script)

'''
new='''    source_script = script
    input_report = prepare_stage02_input(project, script=source_script, reuse_current=True)
    if input_report.get("status") != "passed":
        codes = ", ".join(item.get("code", "INPUT_INVALID") for item in input_report.get("blocking_issues", []))
        raise ValueError(f"Stage 02 script input is invalid: {codes}")
    script = resolve_input_script(project, source_script)

'''
if old not in text: raise RuntimeError("preflight script block missing")
text=text.replace(old,new,1).replace('source_mode = "autonomous_contract" if autonomous_authority is not None else "external_script" if options.external_script else "formal_project_script"','source_mode = "autonomous_contract" if autonomous_authority is not None else "script_file"')
text=text.replace('    from cyberppt.stage02_handoff import load_stage02_handoff\n\n    load_stage02_handoff(project, required=True)\n    assert_visual_structure_ready(project, script)','    assert_visual_structure_ready(project, script)')
text=text.replace('    handoff_path = project / HANDOFF_JSON','    script_input_path = project / INPUT_JSON').replace('handoff_sha256=sha256_file(handoff_path) or ""','handoff_sha256=sha256_file(script_input_path) or ""')
write(path,text)

# Artifact-spec compiler consumes Stage2 input. Historical local variable names remain compatibility-only.
path="cyberppt/page_artifact_spec.py"; text=read(path)
old='''    from cyberppt.stage02_handoff import HANDOFF_JSON, handoff_page_map, load_stage02_handoff

    project = project.expanduser().resolve()
    handoff_path = project / HANDOFF_JSON
    visual_path = project / "visual" / "deck-visual-spec.json"
    handoff = load_stage02_handoff(project, required=True)
    if handoff is None:  # pragma: no cover - required=True is the contract
        raise FileNotFoundError(f"Stage 02 handoff is missing: {handoff_path}")
'''
new='''    from cyberppt.stage02_input import input_page_map, input_path, load_stage02_input

    project = project.expanduser().resolve()
    script_input_path = input_path(project)
    visual_path = project / "visual" / "deck-visual-spec.json"
    handoff = load_stage02_input(project, required=True)
    if handoff is None:  # pragma: no cover - required=True is the contract
        raise FileNotFoundError(f"Stage 02 script input is missing: {script_input_path}")
'''
if old not in text: raise RuntimeError("artifact input loader block missing")
text=text.replace(old,new,1).replace('handoff_map = handoff_page_map(handoff)','handoff_map = input_page_map(handoff)').replace('handoff_sha = hashlib.sha256(handoff_path.read_bytes()).hexdigest()','handoff_sha = hashlib.sha256(script_input_path.read_bytes()).hexdigest()')
text=text.replace('planning_policy=handoff.get("planning_policy")\n            if isinstance(handoff.get("planning_policy"), dict)\n            else None,','planning_policy=None,')
write(path,text)

# Executable architecture contract.
write("tests/test_stage_file_boundary.py",r'''from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from cyberppt.stage02_input import INPUT_JSON, build_stage02_input, prepare_stage02_input

SCRIPT="""## P01 文件边界
- 页面类型：内容页
- 页面标题：文件边界
- 内容负载：standard
- 页面使命：说明两个阶段通过文件对接
- 核心结论：Stage2 只消费脚本文件

### 完整文字稿
Stage2 只读取当前输入文件，并从该文件建立自己的视觉生产状态。

### 上屏文字
输入文件：Final Script 是唯一跨阶段输入
  Stage2 自行派生视觉结构和生产产物

### 视觉结构
输入文件进入视觉生产链，形成完整页面视觉稿。
"""

def test_stage2_input_is_portable_and_ignores_adjacent_producer_state():
    with TemporaryDirectory() as directory:
        root=Path(directory); producer=root/"producer"; producer.mkdir(); script=producer/"final-script.md"; script.write_text(SCRIPT,encoding="utf-8")
        (producer/"deck-plan.json").write_text('{"pages":[]}',encoding="utf-8"); (producer/"foundation.json").write_text('{"facts":[]}',encoding="utf-8")
        stage2=root/"stage2"; payload=build_stage02_input(stage2,script=script)
        assert payload["schema"]=="cyberppt.stage02_script_input.v1"; assert payload["pages"][0]["title"]=="文件边界"; assert payload["pages"][0]["content_load"]=="standard"; assert payload["source_bindings"]["script"]["source_path"]==str(script.resolve())
        assert (stage2/"workbench/inputs/final-script.md").is_file(); assert prepare_stage02_input(stage2,script=script,reuse_current=True)["status"]=="passed"; assert (stage2/INPUT_JSON).is_file()

def test_formal_stage2_runtime_has_no_stage1_artifact_dependency():
    repo=Path(__file__).resolve().parents[1]; files=[repo/"cyberppt/stage02_input.py",repo/"cyberppt/visual_stage/execution.py",repo/"cyberppt/visual_stage/audit.py",repo/"cyberppt/visual_stage/prompt_gate.py",repo/"cyberppt/stage02_production/preflight.py",repo/"cyberppt/page_artifact_spec.py"]
    text="\n".join(path.read_text(encoding="utf-8") for path in files)
    assert "from cyberppt.stage02_handoff" not in text; assert "parse_script_path" not in (repo/"cyberppt/stage02_input.py").read_text(encoding="utf-8")
    for token in ("deck-plan.json","foundation.json","source-truth.json","outline.json"): assert token not in text
''')

# Documentation: the stage boundary is the Final Script file.
for path in ("README.md","docs/CYBERPPT_WORKFLOW.md",".agents/skills/cyberppt-stage02-editable-pptx/SKILL.md"):
    text=read(path)
    text=text.replace("先运行 `prepare-stage02-handoff --script <path>`，再进入视觉结构与 `final-script-pages`。页面生产前必须具备当前脚本绑定的 Stage 02 handoff 和视觉结构审计。","Stage 02 直接接收 `--script <path>` 指向的最终脚本文件，并在自身工作区建立输入快照。Stage 02 不读取 Stage 01 的 Foundation、Deck Plan、Source Truth、Outline 或流程状态。")
    text=text.replace("运行 `prepare-stage02-handoff`，核对当前最终脚本、项目绑定、脚本版本和页面范围。脚本发生变化后，必须重新生成 handoff，不得沿用旧绑定。","Stage 02 以传入脚本文件为唯一跨阶段输入，并在自身工作区记录脚本快照与哈希。脚本文件发生变化后，Stage 02 自行判定已有视觉产物失效。")
    text=text.replace("Stage 02 handoff","Stage 02 script input").replace("stage02_handoff.json","script-intake.json").replace("Stage 01 → Stage 02","Final Script 文件 → Stage 02").replace("Stage 01 to Stage 02","Final Script file to Stage 02")
    write(path,text)

print("stage-file-boundary v2 applied")
