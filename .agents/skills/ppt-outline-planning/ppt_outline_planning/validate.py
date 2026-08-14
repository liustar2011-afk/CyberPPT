from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPORT_SCHEMA_VERSION="1.0"
EVIDENCE_ROLE_KEYS=("claim","reason","instance","boundary","trace_only")
FORBIDDEN_DOWNSTREAM_FIELDS={"body_text","final_copy","screen_text","bullets","speaker_notes","image_prompt","layout","colors","fonts"}
ARGUMENT_CHAIN_ROLES={"premise","driver","background","problem","cause","constraint","gap","response","claim","reason","instance","mechanism","condition","consequence","judgment","conclusion","recommendation","implementation","support","detail","boundary","evidence","other"}

def _read(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def _write(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def _err(items:list[dict[str,Any]],code:str,message:str,**ctx:Any)->None: items.append({"code":code,"message":message,"context":ctx})
def _warn(items:list[dict[str,Any]],code:str,message:str,**ctx:Any)->None: items.append({"code":code,"message":message,"context":ctx})
def _scan(value:Any,errors:list[dict[str,Any]],path:str="")->None:
    if isinstance(value,dict):
        for key,child in value.items():
            p=f"{path}.{key}" if path else key
            if key in FORBIDDEN_DOWNSTREAM_FIELDS: _err(errors,"forbidden_downstream_field","Outline planning must stop before script copy or detailed visual design.",field=key,path=p)
            _scan(child,errors,p)
    elif isinstance(value,list):
        for i,child in enumerate(value): _scan(child,errors,f"{path}[{i}]")
def _semantic(semantic:Path)->tuple[dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any]]:
    files=["normalized-facts.json","concept-base.json","relation-graph.json","argument-chain.json","semantic-report.json"]
    values=[]
    for name in files:
        path=semantic/name
        if not path.is_file(): raise FileNotFoundError(f"Missing layer-three artifact: {path}")
        values.append(_read(path))
    return tuple(values)  # type: ignore[return-value]
def validate_outline_outputs(semantic_dir:Path|str,outline_dir:Path|str,*,write_report:bool=False)->dict[str,Any]:
    semantic=Path(semantic_dir); outline=Path(outline_dir)
    normalized,concepts,relations,argument,semantic_report=_semantic(semantic)
    deck_path=outline/"deck-brief.json"; page_path=outline/"page-plan.json"
    if not deck_path.is_file() or not page_path.is_file(): raise FileNotFoundError("deck-brief.json and page-plan.json are required")
    deck=_read(deck_path); plan=_read(page_path); errors=[]; warnings=[]
    if semantic_report.get("status")!="ok": _err(errors,"semantic_not_validated","semantic-report.json must report status: ok")
    if deck.get("artifact_type")!="ppt_deck_brief": _err(errors,"wrong_artifact_type","deck-brief.json must be ppt_deck_brief")
    if plan.get("artifact_type")!="ppt_page_plan": _err(errors,"wrong_artifact_type","page-plan.json must be ppt_page_plan")
    if deck.get("deck_id")!=plan.get("deck_id") or not deck.get("deck_id"): _err(errors,"deck_id_mismatch","deck IDs must match and be non-empty")
    _scan(deck,errors,"deck"); _scan(plan,errors,"page-plan")
    task=deck.get("task_understanding") or {}; strategy=deck.get("deck_strategy") or {}
    for field in ("audience","purpose"):
        if not str(task.get(field) or "").strip(): _err(errors,"missing_task_context",f"task_understanding.{field} is required")
    for field in ("working_title","core_question","deck_thesis"):
        if not str(strategy.get(field) or "").strip(): _err(errors,"missing_deck_strategy",f"deck_strategy.{field} is required")
    sections=deck.get("sections") if isinstance(deck.get("sections"),list) else []; section_by_id={str(s.get("section_id")):s for s in sections if isinstance(s,dict) and s.get("section_id")}
    pages=plan.get("pages") if isinstance(plan.get("pages"),list) else []
    orders=[p.get("order") for p in pages if isinstance(p,dict)]
    if orders!=list(range(1,len(pages)+1)): _err(errors,"non_contiguous_page_order","Page order must be contiguous and match array order",orders=orders)
    page_ids=[str(p.get("page_id")) for p in pages if isinstance(p,dict) and p.get("page_id")]
    if len(page_ids)!=len(set(page_ids)): _err(errors,"duplicate_page_id","page_id values must be unique")
    nf_ids={str(x.get("normalized_fact_id")) for x in normalized.get("facts") or [] if isinstance(x,dict)}
    relation_by_id={str(x.get("relation_id")):x for x in relations.get("relations") or [] if isinstance(x,dict)}
    arg_ids={str(x.get("node_id")) for group in (argument.get("source_chain") or [],argument.get("reconstructed_chain") or []) for x in group if isinstance(x,dict)}
    page_order={str(p.get("page_id")):int(p.get("order")) for p in pages if isinstance(p,dict) and p.get("page_id") and isinstance(p.get("order"),int)}
    content_count=0; template_count=0; evidence_count=0
    for page in pages:
        if not isinstance(page,dict): _err(errors,"invalid_page","Page entries must be objects"); continue
        pid=str(page.get("page_id") or "")
        if page.get("page_type")=="template":
            template_count+=1
            forbidden=[k for k in ("key_judgment","argument_chain","evidence_roles","evidence") if page.get(k) not in (None,"",[],{})]
            if forbidden: _err(errors,"template_page_has_business_content","Template page may not carry business reasoning",page_id=pid,fields=forbidden)
            continue
        if page.get("page_type")!="content": _err(errors,"invalid_page_type","page_type must be template or content",page_id=pid); continue
        content_count+=1
        for field in ("audience_question","page_mission","key_judgment","non_substitutable_value","argument_role","must_not_include","reserved_for_later","split_risk","transition_from_previous","transition_to_next"):
            value=page.get(field)
            if value is None or value=="" or (field=="must_not_include" and value==[]): _err(errors,"missing_page_boundary_field",f"Content page requires {field}",page_id=pid,field=field)
        if page.get("split_risk") in {"medium","high"} and not str(page.get("split_risk_reason") or "").strip(): _err(errors,"missing_split_risk_reason","Medium/high split risk requires split_risk_reason",page_id=pid)
        evidence=page.get("evidence") if isinstance(page.get("evidence"),dict) else {}; nfs=[str(x) for x in evidence.get("normalized_fact_ids") or []]; rels=[str(x) for x in evidence.get("relation_ids") or []]; args=[str(x) for x in evidence.get("argument_node_ids") or []]
        if not nfs: _err(errors,"missing_direct_fact_grounding","Every content page requires at least one direct normalized_fact_id",page_id=pid)
        for ref in nfs:
            if ref not in nf_ids: _err(errors,"unknown_normalized_fact","Unknown normalized fact",page_id=pid,id=ref)
        inferred=[]
        for ref in rels:
            relation=relation_by_id.get(ref)
            if relation is None: _err(errors,"unknown_relation","Unknown relation",page_id=pid,id=ref)
            elif relation.get("basis")=="inferred": inferred.append(ref)
        if inferred and not str(evidence.get("inference_note") or "").strip(): _err(errors,"undisclosed_inferred_relation","Inferred relations require evidence.inference_note",page_id=pid,relation_ids=inferred)
        for ref in args:
            if ref not in arg_ids: _err(errors,"unknown_argument_node","Unknown argument node",page_id=pid,id=ref)
        page_evidence=set(nfs)|set(rels)|set(args); evidence_count+=len(page_evidence)
        chain=page.get("argument_chain")
        if not isinstance(chain,list) or not chain: _err(errors,"invalid_argument_chain","argument_chain must be non-empty",page_id=pid)
        else:
            for idx,node in enumerate(chain,1):
                if not isinstance(node,dict): _err(errors,"invalid_argument_chain","argument_chain entries must be objects",page_id=pid,index=idx); continue
                if node.get("role") not in ARGUMENT_CHAIN_ROLES: _err(errors,"invalid_argument_chain_role","Unknown argument role",page_id=pid,index=idx)
                if not str(node.get("statement") or "").strip(): _err(errors,"invalid_argument_chain","argument_chain statement required",page_id=pid,index=idx)
                ev=node.get("evidence") if isinstance(node.get("evidence"),dict) else {}; refs=set(str(x) for key in ("normalized_fact_ids","relation_ids","argument_node_ids") for x in ev.get(key) or [])
                if not refs: _err(errors,"invalid_argument_chain","argument_chain evidence required",page_id=pid,index=idx)
                outside=sorted(refs-page_evidence)
                if outside: _err(errors,"argument_chain_evidence_outside_page","Chain evidence must already be declared by page",page_id=pid,index=idx,ids=outside)
        roles=page.get("evidence_roles")
        if not isinstance(roles,dict): _err(errors,"invalid_evidence_roles","evidence_roles must be object",page_id=pid)
        else:
            assigned={}
            for role in EVIDENCE_ROLE_KEYS:
                refs=roles.get(role)
                if not isinstance(refs,list): _err(errors,"invalid_evidence_roles",f"evidence_roles.{role} must be array",page_id=pid); continue
                for ref in refs: assigned.setdefault(str(ref),[]).append(role)
            for ref,names in assigned.items():
                if ref not in page_evidence: _err(errors,"evidence_role_outside_page","Role can classify only page evidence",page_id=pid,id=ref)
                if len(names)>1: _err(errors,"evidence_role_overlap","One evidence ID may have one role only",page_id=pid,id=ref,roles=names)
            missing=sorted(page_evidence-set(assigned))
            if missing: _err(errors,"unassigned_page_evidence","Every page evidence ID must have exactly one role",page_id=pid,ids=missing)
        if page.get("judgment_basis")=="planning_inference" and not str(page.get("inference_rationale") or "").strip(): _err(errors,"missing_inference_rationale","planning_inference requires inference_rationale",page_id=pid)
        reserved=page.get("reserved_for_later")
        if isinstance(reserved,list):
            for item in reserved:
                if not isinstance(item,dict) or not item.get("topic") or not item.get("target_page"): _err(errors,"invalid_reserved_for_later","Reserved item requires topic and target_page",page_id=pid); continue
                target=str(item.get("target_page"))
                if target not in page_order: _err(errors,"invalid_reserved_target","reserved target must exist",page_id=pid,target_page=target)
                elif page_order[target]<=page_order.get(pid,0): _err(errors,"reserved_target_not_later","reserved target must be later page",page_id=pid,target_page=target)
    for section_id,section in section_by_id.items():
        planned=[str(x) for x in section.get("page_ids") or []]; actual=[str(p.get("page_id")) for p in pages if isinstance(p,dict) and str(p.get("section_id") or "")==section_id]
        if planned!=actual: _err(errors,"section_page_mismatch","Section page_ids must match page plan",section_id=section_id,planned=planned,actual=actual)
    budget=strategy.get("page_budget") if isinstance(strategy.get("page_budget"),dict) else {}
    target=budget.get("target"); minimum=budget.get("min"); maximum=budget.get("max")
    if not all(isinstance(v,int) and v>0 for v in (target,minimum,maximum)): _err(errors,"invalid_page_budget","page_budget target/min/max must be positive integers")
    elif not minimum<=len(pages)<=maximum: _err(errors,"page_count_out_of_range","Page count outside budget",actual=len(pages),min=minimum,max=maximum)
    result={"schema_version":REPORT_SCHEMA_VERSION,"artifact_type":"ppt_outline_validation_report","status":"ok" if not errors else "error","errors":errors,"warnings":warnings,"counts":{"sections":len(sections),"pages":len(pages),"content_pages":content_count,"template_pages":template_count,"evidence_references":evidence_count}}
    if write_report: _write(outline/"outline-report.json",result)
    return result
