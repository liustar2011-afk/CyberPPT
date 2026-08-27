"""Page semantics and visual-intent rules for ImageGen handoff."""

from __future__ import annotations

import re

from cyberppt.composition_resolver import resolve_composition, validate_composition
from cyberppt.script_quality_contract import ScriptPage
from cyberppt.semantic_intent import (
    SemanticIntentDecision,
    canonicalize_intent,
    resolve_semantic_intent,
    validate_semantic_structure,
)
from cyberppt.visual_carrier_resolver import (
    select_visual_carrier,
    validate_visual_carrier,
)
from scripts.imagegen_pipeline.creative_brief import (
    CreativeBrief,
    build_creative_brief,
)
from scripts.imagegen_pipeline.handoff.common import (
    _clean_onscreen_for_imagegen,
    _module_label,
)
from scripts.imagegen_pipeline.handoff.contracts import (
    BUSINESS_RELATION_MARKERS,
    DETACHED_TEXT_RAIL_AVOID,
    PAGE_SEMANTIC_LABEL_MARKERS,
    PAGE_SEMANTIC_LEAD_PHRASE_MARKERS,
    PAGE_SEMANTIC_PHRASE_MARKERS,
    PAGE_SEMANTIC_STRUCTURE_LABEL_MARKERS,
    TEXT_IN_COMPOSITION_RULE,
    VISUAL_INTENT_PRIORITY,
    VISUAL_INTENT_SIGNALS,
    VISUAL_INTENT_TEMPLATES,
    VISUAL_STRUCTURE_HARD_HINTS,
    _AUTHORING_STRUCTURE_TAIL_RE,
    _CROSSCUT_HARD_HINT_MARKERS,
    _CROSSCUT_HARD_HINT_PREFIXES,
    _LABEL_SEMANTIC_RE,
    _STRUCTURE_LABEL_LEAD_RE,
)


def _has_semantic_marker(text: str) -> bool:
    if any(marker in text for marker in PAGE_SEMANTIC_PHRASE_MARKERS):
        return True
    return bool(_LABEL_SEMANTIC_RE.search(text)) or any(
        text.startswith(f"{label}：") or text.startswith(f"{label}:")
        for label in PAGE_SEMANTIC_LABEL_MARKERS
    )


def _has_business_relation_marker(text: str) -> bool:
    if "从业务关系看" in text:
        return True
    return any(
        re.search(rf"(?:^|[\s\-•*]){re.escape(marker)}\s*[：:]", text)
        or text.startswith(f"{marker}：")
        or text.startswith(f"{marker}:")
        for marker in BUSINESS_RELATION_MARKERS
        if marker != "从业务关系看"
    )

MODULE_CHAIN_MARKERS = (
    "贯穿主链",
    "四层主链",
    "转化主链",
    "业务主链",
)


def _is_module_enumeration_chain(sentence: str, module_titles: tuple[str, ...]) -> bool:
    """True when a chain sentence mostly restates on-screen module titles."""

    if "→" not in sentence:
        return False
    if not any(marker in sentence for marker in MODULE_CHAIN_MARKERS):
        return False
    labels = [_module_label(title) for title in module_titles if _module_label(title)]
    if len(labels) < 2:
        return False
    hits = sum(1 for label in labels if label in sentence)
    return hits >= max(2, (len(labels) + 1) // 2)


def _normalize_semantic_sentence(value: str) -> str:
    """Collapse whitespace and strip leftover bullets after sentence splits."""

    text = re.sub(r"\s+", " ", value).strip()
    text = re.sub(r"^[\s\-*•·]+", "", text)
    text = re.sub(r"[\s\-*•·]+$", "", text)
    text = text.strip()
    if not text:
        return ""
    text = _AUTHORING_STRUCTURE_TAIL_RE.sub("。", text)
    text = re.sub(r"[；;]。", "。", text)
    text = re.sub(r"。{2,}", "。", text)

    # Whole-source scans can leave module titles before the relation marker.
    # Trim only to true lead anchors — never to mid-sentence structure verbs.
    earliest: int | None = None
    for marker in PAGE_SEMANTIC_LEAD_PHRASE_MARKERS:
        idx = text.find(marker)
        if idx >= 0 and (earliest is None or idx < earliest):
            earliest = idx
    for match in _STRUCTURE_LABEL_LEAD_RE.finditer(text):
        idx = match.start("label")
        if earliest is None or idx < earliest:
            earliest = idx
    for match in re.finditer(
        r"(?:^|[\s\-•*])(?P<label>"
        + "|".join(re.escape(label) for label in PAGE_SEMANTIC_LABEL_MARKERS)
        + r")\s*[：:]",
        text,
    ):
        idx = match.start("label")
        if earliest is None or idx < earliest:
            earliest = idx
    if earliest is not None and earliest > 0:
        text = text[earliest:].strip()
        text = re.sub(r"^[\s\-*•·]+", "", text)
    # Prefer a terminal period over a dangling Chinese semicolon fragment.
    if text.endswith(("；", ";")):
        text = text[:-1].rstrip() + "。"
    return text.strip()


def _is_degenerate_semantic_sentence(sentence: str) -> bool:
    """True when a candidate is only a bare marker / empty after punctuation."""

    stripped = sentence.strip()
    core = re.sub(r"[\s。！？；;：:\-—―–•*·]+", "", stripped)
    if not core:
        return True
    if core in PAGE_SEMANTIC_PHRASE_MARKERS or core in MODULE_CHAIN_MARKERS:
        return True
    bare = re.sub(r"[。！？；;]+$", "", stripped)
    for marker in PAGE_SEMANTIC_STRUCTURE_LABEL_MARKERS:
        if re.fullmatch(re.escape(marker) + r"[——―–\-]*", bare):
            return True
    return False


def _page_semantic_relations(page: ScriptPage) -> str:
    """Extract compact business relations without forwarding source prose.

    The final script keeps the drawable bullets in ``上屏文字`` while the
    connective meaning may remain in ``视觉结构``, full prose, or speaker
    notes.  Preserve only marked relationship sentences so the handoff keeps
    the page's governing logic without leaking the source manuscript.
    Prefer explicit business-relation sentences over module-title chains that
    merely restate the on-screen module order.

    Chinese semicolons often separate clauses inside one labeled relation
    (``责任关系：A；B；C。``) and must not be treated as sentence boundaries;
    only ``。！？`` split candidates.
    """

    candidates: list[str] = []

    def add_sentence(value: str) -> None:
        text = _normalize_semantic_sentence(value)
        if not text or not _has_semantic_marker(text):
            return
        # Keep one compact sentence at a time; source paragraphs can contain
        # detailed evidence that is intentionally not part of the handoff.
        # Do not split on「；」— it is clause punctuation inside labeled relations.
        for sentence in re.split(r"(?<=[。！？])\s*", text):
            sentence = _normalize_semantic_sentence(sentence)
            if (
                sentence
                and _has_semantic_marker(sentence)
                and not _is_degenerate_semantic_sentence(sentence)
                and sentence not in candidates
            ):
                candidates.append(sentence)

    add_sentence(page.visual_structure)
    for source in (page.onscreen_text, page.full_prose, page.speaker_notes):
        for raw in source.splitlines():
            add_sentence(raw)
        # Also inspect prose that is not line-broken at sentence boundaries.
        add_sentence(source)

    if not candidates:
        return ""

    business = [
        sentence
        for sentence in candidates
        if _has_business_relation_marker(sentence)
    ]
    if business:
        structural = [
            sentence
            for sentence in candidates
            if sentence not in business
            and not _is_module_enumeration_chain(sentence, page.module_titles)
        ]
        ordered = business + structural
    else:
        ordered = candidates
    return "\n".join(f"- {sentence}" for sentence in ordered[:4])


def _explicit_visual_intent_type(
    page: ScriptPage,
    context: dict[str, str] | None,
    override: dict[str, str] | None,
) -> str:
    """Resolve an author-declared intent from override, outline, script, or contract."""

    for source in (
        (override or {}).get("visual_intent_type"),
        (context or {}).get("visual_intent_type"),
        page.visual_intent_type,
    ):
        value = str(source or "").strip()
        if value in VISUAL_INTENT_TEMPLATES:
            return value
    receipt = page.contract_receipt
    if isinstance(receipt, dict):
        value = str(receipt.get("visual_intent_type") or "").strip()
        if value in VISUAL_INTENT_TEMPLATES:
            return value
    return ""


def _visual_structure_hard_hint(page: ScriptPage) -> str:
    structure = page.visual_structure.strip()
    if not structure:
        return ""
    corpus = "\n".join(
        (
            structure,
            page.main_message,
            page.full_prose,
            page.speaker_notes,
        )
    )
    # Path/layer primitives with an explicit transverse force are cross-cutting,
    # not a pure path_chain / hierarchy_support stack.
    if structure.startswith(_CROSSCUT_HARD_HINT_PREFIXES) and (
        any(marker in corpus for marker in _CROSSCUT_HARD_HINT_MARKERS)
        or re.search(r"[；;][^；;\n]{0,40}贯穿主链", structure)
        or re.search(r"[；;][^；;\n]{0,20}横切", structure)
        or (
            "横向治理" in structure
            and any(token in corpus for token in ("贯穿", "横向"))
        )
    ):
        return "crosscutting_chain"
    for prefix, intent in VISUAL_STRUCTURE_HARD_HINTS:
        if structure.startswith(prefix):
            return intent
    return ""


def resolve_page_visual_intent(
    page: ScriptPage,
    page_mission: str,
    context: dict[str, str] | None = None,
    override: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Select a page relationship and report how confidently it was chosen.

    Returns ``(intent_type, source)`` where source is one of:
    ``explicit``, ``hint``, ``scored``, or ``fallback``.
    """

    if page.page_type != "content":
        raise ValueError(f"page {page.page_id} is {page.page_type}; no visual intent")
    context = context if isinstance(context, dict) else {}

    explicit = _explicit_visual_intent_type(page, context, override)
    if explicit:
        return explicit, "explicit"

    # V2 page contracts carry the authoritative source relation. Route from it
    # before consulting page-type or rhetoric heuristics.
    relation_names = {
        str(item.get("relation") or "") for item in page.content_relations
    }
    if relation_names & {"composed_of", "contains", "part_of", "classified_as", "layered_as"}:
        return "hierarchy_support", "contract_relation"
    if relation_names & {"sequence_before", "sequence_after"}:
        return "phase", "contract_relation"
    if relation_names & {"bounded_by"}:
        return "boundary_guardrail", "contract_relation"
    if relation_names & {"corresponds_to", "applies_to", "covers", "provides_to", "supports"}:
        return "capability_relationship", "contract_relation"
    if relation_names & {"causes"}:
        return "causal", "contract_relation"

    hinted = _visual_structure_hard_hint(page)
    if hinted:
        return hinted, "hint"

    relationship_corpus = "\n".join(
        (
            page.onscreen_text,
            page.full_prose,
            page.speaker_notes,
            page.visual_structure,
        )
    )
    relationship_lines = "\n".join(
        line.strip()
        for line in relationship_corpus.splitlines()
        if any(
            marker in line
            for marker in (
                "关系：",
                "工作流：",
                "贯通：",
                "闭环：",
                "回流",
                "反馈",
                "持续迭代",
            )
        )
    )
    signal_text = "\n".join(
        (
            page_mission,
            context.get("business_question", ""),
            context.get("page_job", ""),
            context.get("visual_center", ""),
            page.main_message,
            "\n".join(page.module_titles),
            page.visual_structure,
            relationship_lines,
        )
    )
    # These are field or object names, not page relationships.
    score_text = (
        signal_text.replace("业务应用层", "")
        .replace("平台应用层", "")
        .replace("需求预测", "")
        .replace("负荷需求", "")
    )
    scores = {
        intent_type: sum(
            weight for phrase, weight in signals if phrase in score_text
        )
        for intent_type, signals in VISUAL_INTENT_SIGNALS.items()
    }
    has_primary_chain = any(
        phrase in score_text for phrase in ("纵向关系", "纵向主链")
    )
    has_transverse_force = any(
        phrase in score_text
        for phrase in ("横向治理贯穿", "横向贯穿", "贯穿每层")
    )
    if not (has_primary_chain and has_transverse_force):
        scores["crosscutting_chain"] = 0
    role = context.get("argument_role", "").strip()
    if role == "foundation":
        scores["multi_semantic_foundation"] += 8
    elif role in {"change", "gap", "necessity"}:
        scores["causal"] += 3
    elif role == "implementation" and any(
        phrase in score_text for phrase in ("近期", "阶段", "节奏", "先开展", "再拓展")
    ):
        scores["phase"] += 4

    best_score = max(scores.values(), default=0)
    if best_score < 5:
        return "judgment_evidence", "fallback"
    for intent_type in VISUAL_INTENT_PRIORITY:
        if scores.get(intent_type) == best_score:
            return intent_type, "scored"
    return "judgment_evidence", "fallback"


def select_page_visual_intent_type(
    page: ScriptPage,
    page_mission: str,
    context: dict[str, str] | None = None,
    override: dict[str, str] | None = None,
) -> str:
    script_visual_structure = str(getattr(page, "visual_structure", "") or "")
    if any(token in script_visual_structure for token in ("闭环", "回流", "返回前序")):
        return "closed_loop"
    if any(token in script_visual_structure for token in ("双侧协同", "跨系统协同", "接口")):
        return "capability_relationship"
    if any(token in script_visual_structure for token in ("主体泳道", "统一托底", "底部支撑")):
        return "hierarchy_support"
    """Select a page relationship without allowing one generic noun to hijack it."""

    return resolve_page_visual_intent(
        page,
        page_mission,
        context=context,
        override=override,
    )[0]


def resolve_page_semantic_intent(
    page: ScriptPage,
    page_mission: str,
    context: dict[str, str] | None = None,
    override: dict[str, str] | None = None,
) -> SemanticIntentDecision:
    """Return the canonical semantic decision for shadow migration."""

    context = context if isinstance(context, dict) else {}
    override = override if isinstance(override, dict) else {}
    explicit = str(
        override.get("semantic_intent_type")
        or context.get("semantic_intent_type")
        or ""
    ).strip()
    legacy, _legacy_source = resolve_page_visual_intent(
        page, page_mission, context=context, override=override
    )
    corpus = "\n".join(
        part
        for part in (
            page_mission,
            context.get("business_question", ""),
            context.get("page_job", ""),
            page.core_message,
            page.onscreen_text,
            page.full_prose,
            page.visual_structure,
            page.speaker_notes,
            "\n".join(page.module_titles),
        )
        if part
    )
    return resolve_semantic_intent(
        explicit_intent=explicit,
        legacy_intent=legacy,
        content_relations=page.content_relations,
        corpus=corpus,
    )


def audit_page_semantic_intent(
    page: ScriptPage,
    page_mission: str = "",
    context: dict[str, str] | None = None,
    override: dict[str, str] | None = None,
    prior_carriers: tuple[str, ...] = (),
) -> dict[str, object]:
    """Build one serializable shadow-audit record for a content page."""

    legacy, legacy_source = resolve_page_visual_intent(
        page, page_mission, context=context, override=override
    )
    decision = resolve_page_semantic_intent(
        page, page_mission, context=context, override=override
    )
    composition = resolve_composition(decision)
    carrier = select_visual_carrier(decision, composition, prior_carriers)
    corpus = "\n".join(
        (page.core_message, page.onscreen_text, page.full_prose, page.visual_structure)
    )
    record = decision.to_dict()
    legacy_canonical_intent = canonicalize_intent(legacy)
    structure_issues = (
        *validate_composition(composition),
        *validate_visual_carrier(carrier),
    )
    record.update(
        {
            "page_id": page.page_id,
            "page_title": page.title,
            "legacy_intent": legacy,
            "legacy_source": legacy_source,
            "legacy_compatible_intent": decision.legacy_intent,
            "legacy_matches": legacy == decision.legacy_intent,
            "legacy_canonical_intent": legacy_canonical_intent,
            "semantic_refinement": (
                bool(legacy_canonical_intent)
                and legacy_canonical_intent != decision.primary_intent
            ),
            "composition": composition.to_dict(),
            "visual_carrier": carrier.to_dict(),
            "composition_guidance": (
                f"Use {carrier.selected} as the single dominant carrier occupying about "
                f"{round(composition.dominant_ratio * 100)}% of the body area. "
                f"Organize it as: {composition.spatial_organization}. "
                f"Reading path: {' -> '.join(composition.reading_path)}. "
                f"Encode relations with {', '.join(composition.relationship_encoding)}."
            ),
            "blocking_issues": list(
                (*structure_issues, *validate_semantic_structure(
                    decision,
                    corpus=corpus,
                    content_relations=page.content_relations,
                ))
                if decision.source not in {"fallback", "legacy_hint"}
                else structure_issues
            ),
        }
    )
    return record


def build_page_visual_intent(
    page: ScriptPage,
    page_mission: str,
    override: dict[str, str] | None = None,
    context: dict[str, str] | None = None,
) -> str:
    """Compile deterministic, non-rendering page-specific composition guidance."""

    relation = select_page_visual_intent_type(
        page,
        page_mission,
        context=context,
        override=override,
    )
    values = dict(VISUAL_INTENT_TEMPLATES[relation])
    if isinstance(override, dict):
        for key in values:
            value = override.get(key)
            if isinstance(value, str) and value.strip():
                values[key] = value.strip()
    values["recommended_composition"] = (
        f"{values['recommended_composition']} {TEXT_IN_COMPOSITION_RULE}"
    )
    values["avoid_on_this_page"] = (
        f"{values['avoid_on_this_page']} 避免{DETACHED_TEXT_RAIL_AVOID}。"
    )
    return "\n".join(
        (
            "[Prompt context] Page-specific visual intent "
            "(composition guidance only; do not render field names or instruction text)",
            f"- Selected visual intent type: {relation}",
            f"- Visual thesis: {values['visual_thesis']}",
            f"- Decision relationship: {values['decision_relationship']}",
            f"- Recommended composition: {values['recommended_composition']}",
            f"- Avoid on this page: {values['avoid_on_this_page']}",
        )
    )


def build_page_creative_brief(
    page: ScriptPage,
    page_mission: str,
    override: dict[str, str] | None = None,
    context: dict[str, str] | None = None,
) -> CreativeBrief:
    """Build semantic invariants and creative freedom using the existing router."""

    relation = select_page_visual_intent_type(
        page,
        page_mission,
        context=context,
        override=override,
    )
    return build_creative_brief(
        relation=relation,
        page_purpose=page_mission or page.core_message,
        core_meaning=page.core_message,
        required_meanings=page.module_titles,
        onscreen_text=_clean_onscreen_for_imagegen(page.onscreen_text),
        override=override,
    )
