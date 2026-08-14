from __future__ import annotations

from typing import Any

def _semantic_review_markdown(model: dict[str, Any]) -> str:
    lines = ["# CyberPPT semantic compatibility projection", "", "> Projection only. The authoritative semantic artifacts are the Source Material Foundation layer-three files.", "", f"- primary_thesis: {model.get('document_semantics', {}).get('primary_thesis', '')}", "", "## Projected argument nodes", ""]
    for node in model.get("subsection_nodes") or []:
        if isinstance(node, dict):
            lines.append(f"- `{node.get('id')}` {node.get('thesis') or node.get('section_thesis')} [{node.get('claim_origin')}] ")
    return "\n".join(lines).rstrip() + "\n"

def _outline_review_markdown(outline: dict[str, Any]) -> str:
    lines = ["# CyberPPT Outline compatibility review", "", "> Projection only. Page architecture authority remains deck-brief.json + page-plan.json.", "", f"- 叙事主张：{outline.get('narrative_thesis', '')}", ""]
    for page in outline.get("pages") or []:
        if not isinstance(page, dict):
            continue
        lines.append(f"## {page.get('page_id')}｜{page.get('title')}")
        if page.get("page_type") == "content":
            lines += [f"- 受众问题：{page.get('audience_question', '')}", f"- 页面使命：{page.get('page_mission', '')}", f"- 核心判断：{page.get('core_message', '')}", f"- 不可替代价值：{page.get('non_substitutable_value', '')}", f"- 来源：{'、'.join(page.get('source_refs') or [])}"]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
