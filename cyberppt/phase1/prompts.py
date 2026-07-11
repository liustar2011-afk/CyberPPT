"""Reviewable prompt builders for Stage 1 model generation."""

from __future__ import annotations

from cyberppt.phase1.source_bundle import SourceBundle, SourceChunk, SourceUnit


def _source_prompt_prefix(base_prompt: str) -> str:
    return base_prompt.split("【参考规范】", 1)[0].rstrip()


def build_source_analysis_chunk_prompt(
    base_prompt: str,
    chunk: SourceChunk,
    units: dict[str, SourceUnit],
) -> str:
    source_units = "\n\n".join(
        f"[{units[unit_id].unit_id}]\n{units[unit_id].text}"
        for unit_id in chunk.unit_ids
    )
    return f"""{_source_prompt_prefix(base_prompt)}

【当前阶段】分块证据抽取，仅处理当前材料块，不判断全文故事线。
【输出字段】chunk_id、evidence、material_signals、open_questions。
【evidence 字段】claim、support、source_unit_ids、numbers、caveat。
【来源约束】source_unit_ids 只能使用当前材料块列出的单元 ID；不得使用页码或自造编号。
【格式要求】只返回 JSON 对象，不返回 Markdown，不使用 E01 等最终证据编号。
【chunk_id】{chunk.chunk_id}
【材料块】
{source_units}
"""


def build_source_analysis_aggregate_prompt(base_prompt: str, chunk_outputs: list[str]) -> str:
    joined = "\n\n".join(
        f"【分块结果 {index + 1}】\n{output}" for index, output in enumerate(chunk_outputs)
    )
    return f"""{_source_prompt_prefix(base_prompt)}

【当前阶段】全局证据归并与 source_analysis 候选稿生成。
【任务】只基于下方分块证据结果，完成全文材料类型、汇报任务、受众、故事线、物料池和确认问题判断。
【输出字段】material_type、reporting_task、audience、evidence、storylines、material_pool、confirmation_questions。
【evidence 字段】每条必须提供 claim、verbatim_support、source_unit_ids、numbers、confidence、caveat、meaning、visual。
【事实边界】不得新增事实、数字、来源或外部知识；保留分块证据中的 source_unit_ids，并在跨块重复或冲突时合并说明。
【格式要求】只返回 JSON 对象，不返回 Markdown，不使用 E01 等最终证据编号。
【分块证据结果】
{joined}
"""


def build_source_analysis_prompt(bundle: SourceBundle, references: dict[str, str]) -> str:
    reference_text = "\n\n".join(f"【{name}】\n{value}" for name, value in sorted(references.items()))
    source_units = "\n\n".join(
        f"[{unit.unit_id}] kind={unit.kind} locator={unit.locator} numbers={list(unit.numbers)}\n{unit.text}"
        for unit in bundle.units
    )
    return f"""# CyberPPT Stage 1 source_analysis prompt

【任务】生成 source_analysis 严格 JSON，服务于央企、政府内部汇报。
【事实边界】不得新增事实、数字、来源或外部知识；不确定内容必须写入 caveat 或 confirmation_questions。
【证据要求】每条 evidence 必须提供 claim、verbatim_support、source_unit_ids、numbers、confidence、caveat、meaning、visual。
【来源要求】只允许引用下方 source_unit_ids；不要自行编造页码、表格编号或文件位置。
【输出字段】material_type、reporting_task、audience、evidence、storylines、material_pool、confirmation_questions。
【格式要求】只返回 JSON 对象，不要返回 Markdown，不要使用 E01 等最终证据编号。

【参考规范】
{reference_text}

【源材料哈希】{bundle.source_sha256}
【源材料单元】
{source_units}
"""


def build_gate_prompt(
    gate: str,
    approved: dict[str, str],
    evidence_registry: str,
    references: dict[str, str],
) -> str:
    if gate not in {"reporting_direction", "report_structure", "page_design", "business_script"}:
        raise ValueError(f"unsupported downstream gate: {gate}")
    upstream = "\n\n".join(f"【已批准：{name}】\n{text}" for name, text in approved.items())
    reference_text = "\n\n".join(f"【{name}】\n{value}" for name, value in sorted(references.items()))
    output_rules = {
        "reporting_direction": "输出 audience、purpose、content_focus、evidence、strengths、boundaries、options、recommendation。options 至少两项。",
        "report_structure": "输出 modules 数组；每个模块只描述事项、重点和 evidence_ids，不输出页数、页面标题或视觉形式。模块数量按材料任务自适应。",
        "page_design": "输出 pages 数组；每页必须包含角色、标题、详细说明、证据、caveat、视觉、图表计划、含义、承接、信息密度和组件清单。",
        "business_script": "输出 pages 数组；每页必须分离 visible_content、evidence_ids、source_locations、completeness、density、meaning 和 transition。",
    }[gate]
    return f"""# CyberPPT Stage 1 {gate} prompt

【任务】生成 {gate} 严格 JSON，服务于央企、政府内部汇报。
【事实边界】不得新增事实、数字、来源或外部知识；不确定内容必须保留 caveat 或边界。
【证据约束】只允许使用冻结证据表中的 E 编号，不得编造 E 编号。
【文风】正式、客观、审慎；采用 internal_public_sector 和 source_and_task_adaptive。
【输出要求】{output_rules}
【格式要求】只返回 JSON 对象，不返回 Markdown，不输出分析过程。

【冻结证据表】
{evidence_registry}

【上游已批准工件】
{upstream}

【参考规范】
{reference_text}
"""
