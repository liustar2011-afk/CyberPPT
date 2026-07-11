"""Reviewable prompt builders for Stage 1 model generation."""

from __future__ import annotations

from cyberppt.phase1.source_bundle import SourceBundle


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
