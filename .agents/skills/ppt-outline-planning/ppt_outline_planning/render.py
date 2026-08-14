from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CN={1:"一",2:"二",3:"三",4:"四",5:"五",6:"六",7:"七",8:"八",9:"九",10:"十",11:"十一",12:"十二",13:"十三",14:"十四",15:"十五",16:"十六",17:"十七",18:"十八",19:"十九",20:"二十"}
def _cn_number(value:int)->str: return _CN.get(value,str(value))
def _evidence_text(evidence:dict[str,Any])->str:
    parts=[]; nf=evidence.get("normalized_fact_ids") or []; rel=evidence.get("relation_ids") or []; arg=evidence.get("argument_node_ids") or []
    if nf: parts.append(f"NF[{', '.join(nf)}]")
    if rel: parts.append(f"REL[{', '.join(rel)}]")
    if arg: parts.append(f"ARG[{', '.join(arg)}]")
    return "；".join(parts) if parts else "无"
def _argument_chain_lines(chain:object)->list[str]:
    if not isinstance(chain,list): return []
    out=[]
    for node in chain:
        if isinstance(node,dict): out.append(f"  - {node.get('role','')}｜{node.get('statement','')}｜{_evidence_text(node.get('evidence') if isinstance(node.get('evidence'),dict) else {})}")
    return out
def _evidence_role_text(roles:object)->str:
    if not isinstance(roles,dict): return "无"
    parts=[]
    for role in ("claim","reason","instance","boundary","trace_only"):
        refs=roles.get(role)
        if isinstance(refs,list) and refs: parts.append(f"{role}={'、'.join(str(ref) for ref in refs)}")
    return "；".join(parts) if parts else "无"
def _reserved_text(items:object)->str:
    if not isinstance(items,list) or not items: return "无"
    parts=[f"{item.get('topic','')} → {item.get('target_page','')}" for item in items if isinstance(item,dict)]
    return "；".join(parts) if parts else "无"
def _page_lines(page:dict[str,Any])->list[str]:
    lines=[f"### {page.get('page_id','')} {page.get('title_intent','')}".rstrip()]
    if page.get("page_type")=="template": return lines+[f"- 页面类型：模板页 / {page.get('template_kind','')}",f"- 页面使命：{page.get('page_mission','')}"]
    evidence=page.get("evidence") or {}
    lines += ["- 页面类型：内容页",f"- 页面使命：{page.get('page_mission','')}",f"- 受众问题：{page.get('audience_question','')}",f"- 核心判断：{page.get('key_judgment','')}",f"- 不可替代价值：{page.get('non_substitutable_value','')}",f"- 判断依据：{page.get('judgment_basis','')}",f"- 论证角色：{page.get('argument_role','')}",f"- 证据：{_evidence_text(evidence)}",f"- 内容策略：{page.get('content_strategy','')}",f"- 建议视觉逻辑：{page.get('suggested_visual_logic','')}",f"- 重要性：{page.get('importance','')}","- 主论证链："]
    lines.extend(_argument_chain_lines(page.get("argument_chain")) or ["  - 无"])
    lines += [f"- 证据职责：{_evidence_role_text(page.get('evidence_roles'))}",f"- 本页禁止：{'；'.join(str(x) for x in (page.get('must_not_include') or [])) or '无'}",f"- 后页保留：{_reserved_text(page.get('reserved_for_later'))}",f"- 拆页风险：{page.get('split_risk','')}"]
    if page.get("split_risk_reason"): lines.append(f"- 拆页风险说明：{page['split_risk_reason']}")
    if page.get("transition_from_previous"): lines.append(f"- 与前页衔接：{page['transition_from_previous']}")
    if page.get("transition_to_next"): lines.append(f"- 向后页交接：{page['transition_to_next']}")
    if page.get("inference_rationale"): lines.append(f"- 推断依据：{page['inference_rationale']}")
    if evidence.get("inference_note"): lines.append(f"- 推断关系说明：{evidence['inference_note']}")
    return lines
def render_outline_markdown(deck_brief:dict[str,Any],page_plan:dict[str,Any])->str:
    task=deck_brief.get("task_understanding") or {}; strategy=deck_brief.get("deck_strategy") or {}; budget=strategy.get("page_budget") or {}; decision_path=strategy.get("decision_path") or []
    lines=["# PPT提纲","","## 整体设计",f"- 工作标题：{strategy.get('working_title','')}",f"- 汇报类型：{strategy.get('deck_type','')}",f"- 受众：{task.get('audience','')}",f"- 汇报目的：{task.get('purpose','')}",f"- 核心问题：{strategy.get('core_question','')}",f"- 核心判断：{strategy.get('deck_thesis','')}",f"- 叙事模式：{strategy.get('narrative_mode','')}",f"- 决策路径：{' → '.join(str(x) for x in decision_path)}",f"- 页数预算：{budget.get('target','')}页（{budget.get('min','')}—{budget.get('max','')}页，含模板页）"]
    if task.get("constraints"): lines.append(f"- 约束：{'；'.join(str(x) for x in task['constraints'])}")
    if task.get("assumptions"): lines.append(f"- 假设：{'；'.join(str(x) for x in task['assumptions'])}")
    lines.append("")
    sections=sorted(deck_brief.get("sections") or [],key=lambda x:x.get("order",0)); section_by_id={s.get("section_id"):s for s in sections}; emitted=set()
    for page in page_plan.get("pages") or []:
        section_id=page.get("section_id")
        if section_id and section_id not in emitted:
            section=section_by_id.get(section_id,{}); order=section.get("order",len(emitted)+1)
            lines += [f"## 第{_cn_number(int(order))}部分 {section.get('title_intent','')}".rstrip(),f"- 章节使命：{section.get('section_mission','')}",f"- 章节判断：{section.get('section_thesis','')}",f"- 论证角色：{', '.join(section.get('argument_roles') or [])}",""]; emitted.add(section_id)
        lines.extend(_page_lines(page)); lines.append("")
    return "\n".join(lines).rstrip()+"\n"
def render_outline_directory(outline_dir:Path|str,*,output_path:Path|str|None=None,force:bool=False)->Path:
    outline=Path(outline_dir); report_path=outline/"outline-report.json"
    if not report_path.is_file(): raise ValueError("outline-report.json with status: ok is required before rendering ppt-outline.md")
    report=json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("artifact_type")!="ppt_outline_validation_report" or report.get("status")!="ok": raise ValueError("outline-report.json with status: ok is required before rendering ppt-outline.md")
    deck_path=outline/"deck-brief.json"; page_path=outline/"page-plan.json"
    if not deck_path.is_file() or not page_path.is_file(): raise FileNotFoundError("deck-brief.json and page-plan.json are required before rendering")
    deck=json.loads(deck_path.read_text(encoding="utf-8")); pages=json.loads(page_path.read_text(encoding="utf-8")); target=Path(output_path) if output_path is not None else outline/"ppt-outline.md"
    if target.exists() and not force: raise FileExistsError(f"PPT outline already exists: {target}")
    target.parent.mkdir(parents=True,exist_ok=True); target.write_text(render_outline_markdown(deck,pages),encoding="utf-8"); return target
