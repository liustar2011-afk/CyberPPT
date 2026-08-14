from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_FILES = ("normalized-facts.json","concept-base.json","relation-graph.json","argument-chain.json","semantic-report.json")

def _json_sha256(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _compact_fact(item: dict[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(item.get(key)) for key in ("normalized_fact_id","statement","fact_type","verification_status","confidence") if key in item}

def _compact_concept(item: dict[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(item.get(key)) for key in ("concept_id","canonical_name","aliases","concept_type","definition","normalized_fact_ids","confidence") if key in item}

def _compact_relation(item: dict[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(item.get(key)) for key in ("relation_id","from_concept_id","relation_type","to_concept_id","basis","normalized_fact_ids","confidence","inference_rationale") if key in item}

def _validate_artifacts(payloads: dict[str, dict[str, Any]]) -> None:
    expected_types={"normalized-facts.json":"normalized_facts","concept-base.json":"concept_base","relation-graph.json":"relation_graph","argument-chain.json":"argument_chain","semantic-report.json":"semantic_validation_report"}
    for name, artifact_type in expected_types.items():
        payload=payloads.get(name)
        if payload is None: raise FileNotFoundError(f"Missing layer-three artifact: {name}")
        if payload.get("artifact_type") != artifact_type: raise ValueError(f"{name} is not a {artifact_type} artifact")
    if payloads["semantic-report.json"].get("status") != "ok": raise ValueError("semantic-report.json must report status: ok before PPT outline planning")

def build_outline_workpack(payloads: dict[str, dict[str, Any]], *, request: dict[str, Any] | None=None, request_text: str | None=None) -> dict[str, Any]:
    if request is not None and request_text is not None: raise ValueError("request and request_text are mutually exclusive")
    _validate_artifacts(payloads)
    normalized=payloads["normalized-facts.json"]; concepts=payloads["concept-base.json"]; relations=payloads["relation-graph.json"]; argument=payloads["argument-chain.json"]; report=payloads["semantic-report.json"]
    if request is not None: request_payload={"mode":"structured","data":deepcopy(request)}
    elif request_text is not None: request_payload={"mode":"text","text":request_text}
    else: request_payload={"mode":"conversation","note":"Use the current user task and conversation constraints; record unresolved assumptions in deck-brief.json."}
    return {"schema_version":"1.0","artifact_type":"ppt_outline_workpack","source":deepcopy(normalized.get("source",{})),"semantic":{"validated":True,"report_status":report.get("status"),"counts":deepcopy(report.get("counts",{})),"warnings":deepcopy(report.get("warnings",[])),"artifact_sha256":{name:_json_sha256(payloads[name]) for name in REQUIRED_FILES}},"request":request_payload,"planning_index":{"normalized_facts":[_compact_fact(item) for item in normalized.get("facts",[])],"conflicts":deepcopy(normalized.get("conflicts",[])),"ambiguities":deepcopy(normalized.get("ambiguities",[])),"concepts":[_compact_concept(item) for item in concepts.get("concepts",[])],"relations":[_compact_relation(item) for item in relations.get("relations",[])],"source_chain":deepcopy(argument.get("source_chain",[])),"reconstructed_chain":deepcopy(argument.get("reconstructed_chain",[])),"diagnostics":deepcopy(argument.get("diagnostics",[]))},"planning_policy":{"one_page_one_core_point":True,"cyberppt_ready_page_boundary_contract":True,"audience_question_distinct_from_page_mission":True,"evidence_roles_required":["claim","reason","instance","boundary","trace_only"],"cross_page_leakage_guards_required":True,"source_headings_are_not_mandatory_slide_structure":True,"may_reorder_and_deduplicate_supported_material":True,"may_bridge_logic_gaps_only_when_inference_is_labeled":True,"new_source_facts_forbidden":True,"template_pages_have_no_business_body_content":True,"final_on_screen_copy_forbidden":True,"detailed_visual_design_forbidden":True}}

def _read_json(path: Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def _write_json(path: Path,payload:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def prepare_outline_workpack(semantic_dir:Path|str,output_dir:Path|str,*,request:dict[str,Any]|None=None,request_text:str|None=None,force:bool=False)->dict[str,Any]:
    if request is not None and request_text is not None: raise ValueError("request and request_text are mutually exclusive")
    semantic=Path(semantic_dir); output=Path(output_dir); payloads={}
    for name in REQUIRED_FILES:
        path=semantic/name
        if not path.is_file(): raise FileNotFoundError(f"Missing layer-three artifact: {path}")
        payloads[name]=_read_json(path)
    workpack_path=output/"outline-workpack.json"
    if workpack_path.exists() and not force: raise FileExistsError(f"Outline workpack already exists: {workpack_path}")
    workpack=build_outline_workpack(payloads,request=request,request_text=request_text); output.mkdir(parents=True,exist_ok=True); _write_json(workpack_path,workpack)
    return {"status":"prepared","semantic":str(semantic),"output":str(output),"workpack":str(workpack_path),"semantic_counts":workpack["semantic"]["counts"]}
