"""Source-bounded subtitle candidates for lightweight Stage 01 pages.

The policy deliberately returns ``author_required`` when it cannot preserve a
page's subjects, relation and state without inventing connecting language.
"""

from __future__ import annotations

import re


STRUCTURAL_FORMS = frozenset(
    {
        "flow_3_5",
        "operation_loop",
        "architecture_layers",
        "comparison_2col",
        "matrix_2x2",
        "pyramid_argument",
        "grouped_2",
    }
)
STRUCTURAL_INTENTS = frozenset(
    {
        "architecture",
        "capability_map",
        "closed_loop_operation",
        "phase",
        "actor_relation",
    }
)
STATE_MARKERS = ("拟", "计划", "条件", "待确认", "风险", "尚未", "可能")
LONG_CORE_MESSAGE = 32


def _strings(value: object) -> list[str]:
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def _module_refs(modules: list[dict[str, object]], units: list[dict[str, object]]) -> list[str]:
    refs: list[str] = []
    for item in [*modules, *units]:
        refs.extend(_strings(item.get("source_refs")))
    return list(dict.fromkeys(refs))


def _pair_before_gate(core_message: str) -> str:
    match = re.search(r"对([\u4e00-\u9fff]{1,12})(?:和|与)([\u4e00-\u9fff]{1,12})实行", core_message)
    if not match:
        return ""
    return f"{match.group(1)}与{match.group(2)}"


def _stage_gate_subtitle(core_message: str) -> str:
    subjects = _pair_before_gate(core_message)
    if not subjects or "阶段门控" not in core_message:
        return ""
    tail = re.search(r"(?:进入|转入|走向)([\u4e00-\u9fff、，]+?)(?:。|；|$)", core_message)
    if not tail:
        return f"{subjects}分别在阶段门控下推进"
    outcome = tail.group(1).replace("和", "与")
    return f"{subjects}分别在阶段门控下进入{outcome}"


def _policy(
    mode: str,
    subtitle: str = "",
    rationale: str = "",
    source_refs: list[str] | None = None,
    derived_from: list[str] | None = None,
) -> dict[str, object]:
    return {
        "mode": mode,
        "subtitle": subtitle,
        "rationale": rationale,
        "source_refs": source_refs or [],
        "derived_from": derived_from or [],
    }


def resolve_subtitle_policy(
    *,
    core_message: str,
    visual_intent_type: str,
    onscreen_expression_form: str,
    onscreen_modules: list[dict[str, object]],
    content_units: list[dict[str, object]],
) -> dict[str, object]:
    """Return a source-bounded subtitle candidate; never invent a claim."""

    core = str(core_message).strip()
    form = str(onscreen_expression_form).strip()
    intent = str(visual_intent_type).strip()
    modules = [item for item in onscreen_modules if isinstance(item, dict)]
    units = [item for item in content_units if isinstance(item, dict)]
    is_structural = form in STRUCTURAL_FORMS or intent in STRUCTURAL_INTENTS
    refs = _module_refs(modules, units)

    if not is_structural or not modules:
        return _policy("not_needed", rationale="页面无需由副标题承载结构外的长主判断。")
    if any(marker in core for marker in STATE_MARKERS):
        return _policy(
            "author_required",
            rationale="主判断含条件或不确定状态，自动压缩可能改变来源语气。",
            source_refs=refs,
            derived_from=["core_message", "onscreen_modules"],
        )
    if len(core) < LONG_CORE_MESSAGE:
        return _policy("not_needed", rationale="页面主判断足够短，无需由副标题再行压缩。")

    subtitle = _stage_gate_subtitle(core)
    if subtitle:
        return _policy(
            "generated",
            subtitle=subtitle,
            rationale="长主判断中的共同阶段门控关系由副标题承载，生命周期明细交由上屏结构表达。",
            source_refs=refs,
            derived_from=["core_message", "onscreen_modules"],
        )
    return _policy(
        "author_required",
        rationale="页面具备结构型表达，但无法在不新增关系的前提下安全压缩主判断。",
        source_refs=refs,
        derived_from=["core_message", "onscreen_modules"],
    )
