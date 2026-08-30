"""Final Script audit rules."""
from __future__ import annotations

from .common import *
from .composed_trace import hard_finding_messages, trace_composed

_STATUS_PRESERVATION_MARKERS = {
    "规划": ("拟", "将", "应", "计划", "推动", "制定", "形成", "完成", "开展", "目标", "后续", "需"),
    "建议": ("建议", "应", "可", "宜", "鼓励"),
    "待确认": ("亟需", "需要", "仍需", "尚未", "有待", "不足", "差距", "滞后", "要求"),
}


def _status_strength_preserved(status: str, text: str) -> bool:
    """Preserve modality without leaking internal status labels into prose.

    Only statuses with a known modal-marker vocabulary (规划/建议/待确认) impose a
    check; any other status (e.g. a Foundation's neutral "来源陈述"/"现状" label) is a
    compiler-internal category, not a phrase a human would ever write verbatim in
    prose, so it is treated as carrying no modality claim to preserve.
    """

    if not status:
        return True
    markers = _STATUS_PRESERVATION_MARKERS.get(status)
    if markers is None:
        return True
    return any(marker in text for marker in markers)

def _onscreen_module_lines(module: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    text = module.get("text")
    if isinstance(text, str) and text.strip():
        lines.append(text.strip())
    for item in module.get("items") or []:
        if isinstance(item, str) and item.strip():
            lines.append(item.strip())
    return lines

def _is_lead_like_evidence_item(value: str) -> bool:
    """Identify a proposition-shaped item that can shadow a forbidden lead.

    Evidence-first pages may still contain complete factual statements. The
    relevant failure mode is narrower: a broad proposition appears only as the
    first item while lighter sibling facts follow at the same rendered level.
    """
    return (
        len(_VISIBLE_CHAR_RE.findall(value)) >= _COMPLETE_PROPOSITION_MIN_CHARS
        and bool(_LEAD_LIKE_EVIDENCE_ITEM_RE.search(value))
    )

def _evidence_first_item_hierarchy_issues(
    slide_id: str, module: dict[str, Any]
) -> list[str]:
    """Reject a hidden module lead placed in the first flat evidence item."""
    items = [
        item.strip()
        for item in module.get("items") or []
        if isinstance(item, str) and item.strip()
    ]
    if len(items) < 2 or not _is_lead_like_evidence_item(items[0]):
        return []
    if all(_is_lead_like_evidence_item(item) for item in items[1:]):
        return []
    heading = str(module.get("heading") or "?").strip()
    return [
        f"{slide_id}: onscreen_composition='evidence_first' module '{heading}' "
        "uses a lead-like first item above lighter peer evidence; rewrite every item "
        "as same-granularity source facts, or use selective_lead when the judgment "
        "must remain inside the module"
    ]

def _is_readable_proposition(line: str) -> bool:
    """Return whether a visible line carries a compact, sentence-like proposition."""
    value = str(line or "").strip()
    if not value or re.search(r"[：:]", value):
        return False
    chars = len(_VISIBLE_CHAR_RE.findall(value))
    has_predicate = bool(
        _LEAD_LIKE_EVIDENCE_ITEM_RE.search(value)
        or re.search(
            r"(已有|已形成|已明确|缺少|不清|不健全|滞后|并存|负责|承担|"
            r"体现|保障|贯穿|统筹|纳入|建立|扩大|持续|具备|属于|仍需|"
            r"回应|界定|提升|形成|连接|约束|支撑|控制|沉淀|拓展|深化|"
            r"承载|驱动|贯通|复用|转化|推进|决定|提供|用于|服务|规范|覆盖|"
            r"增加|定位|实现|保持|验证|反映|降低|审核|审定|履行|判断|构成|"
            r"明确|统一|改善|完善|强化|提高|促进|推动|满足|适应|识别|管理|保护|"
            r"扩展|依托|展示|评估|补充|保留|采用|固化|表达|分析|"
            r"主导|实行|贯通|支持|需要|需做到)",
            value,
        )
    )
    return (
        has_predicate
        and _COMPLETE_PROPOSITION_MIN_CHARS <= chars <= _COMPLETE_PROPOSITION_MAX_CHARS
    )

def _onscreen_expression_warnings(
    page: dict[str, Any], slide: dict[str, Any],
) -> list[str]:
    """Advisory checks for a declared sentence-led or mixed visible expression mode."""
    contract = page.get("onscreen_contract")
    if not isinstance(contract, dict) or "expression_mode" not in contract:
        return []
    mode = str(contract.get("expression_mode") or "").strip()
    if mode not in {"sentence_led", "mixed"}:
        return []

    modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    if mode == "sentence_led":
        warnings = []
        for module in modules:
            heading = str(module.get("heading") or "?").strip()
            lines = _onscreen_module_lines(module)
            if not any(_is_readable_proposition(line) for line in lines):
                warnings.append(
                    f"module '{heading}': expression_mode='sentence_led' has no readable proposition; "
                    "add one source-grounded sentence with a subject, predicate and terminal punctuation"
                )
        return warnings

    lines = [line for module in modules for line in _onscreen_module_lines(module)]
    if lines and not any(_is_readable_proposition(line) for line in lines):
        return [
            "expression_mode='mixed' contains no readable proposition; "
            "combine compact evidence phrases with at least one source-grounded sentence"
        ]
    return []


_STRUCTURAL_METADATA_PATTERNS = (
    re.compile(r"^目\s*录$"),
    re.compile(r"^工作摘要$"),
    re.compile(r"^[（(]?(?:重构稿\s*)?V\d+(?:\.\d+)*[^。；]*[）)]?$", re.I),
    re.compile(r"^\d{4}年\d{1,2}月(?:\d{1,2}日)?$"),
    re.compile(r"^[一二三四五六七八九十]+、[^。；]{2,40}$"),
    re.compile(r"^附件[一二三四五六七八九十\d]+(?:[：:].*)?$"),
)

def _looks_like_structural_metadata(value: str) -> bool:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" ；;。")
    return bool(text) and any(pattern.fullmatch(text) for pattern in _STRUCTURAL_METADATA_PATTERNS)


def _author_execution_issues(
    delivery_mode: str,
    page: dict[str, Any],
    slide: dict[str, Any],
    items: dict[str, dict[str, Any]],
) -> list[str]:
    """Fail closed on deterministic assembly signatures that cannot count as AUTHOR.

    This gate intentionally verifies authored output rather than accepting a self-
    declared ``author_mode`` flag.  It catches the two bypasses that previously let
    plan headings and source rows be concatenated into a formally valid script.
    """
    if slide.get("page_type") != "content":
        return []

    issues: list[str] = []
    full_copy = str(slide.get("full_copy") or "").strip()
    metadata_hits: list[str] = []
    for ref in page.get("source_refs") or []:
        item = items.get(ref) if isinstance(ref, str) else None
        if not isinstance(item, dict):
            continue
        source_text = _item_text(item).strip()
        if _looks_like_structural_metadata(source_text) and source_text in full_copy:
            metadata_hits.append(ref)
    if metadata_hits:
        issues.append(
            "AUTHOR_STRUCTURAL_METADATA_LEAK: full_copy contains document front matter, "
            f"TOC entries, or section labels as argument prose: {metadata_hits}"
        )

    semicolon_segments = [part.strip() for part in re.split(r"[；;]", full_copy) if part.strip()]
    if len(semicolon_segments) >= 5 and sum(
        1 for part in semicolon_segments if len(_VISIBLE_CHAR_RE.findall(part)) <= 36
    ) >= 4:
        issues.append(
            "AUTHOR_MECHANICAL_SOURCE_CONCATENATION: full_copy is dominated by short "
            "semicolon-joined source fragments; rewrite it as a coherent argument"
        )

    contract = page.get("onscreen_contract")
    expression_mode = str(contract.get("expression_mode") or "") if isinstance(contract, dict) else ""
    if delivery_mode == "self_read" and expression_mode == "phrase_led":
        for module in slide.get("onscreen") or []:
            if not isinstance(module, dict):
                continue
            heading = str(module.get("heading") or "?").strip()
            for line in _onscreen_module_lines(module):
                if "|" in line:
                    issues.append(
                        f"AUTHOR_ONSCREEN_TABLE_FRAGMENT: module '{heading}' contains a raw table row: {line!r}"
                    )
                    continue
                if _is_readable_proposition(line):
                    continue
                if re.search(r"[：:]", line):
                    _, body = re.split(r"[：:]", line, maxsplit=1)
                    if _is_readable_proposition(body) or len(_VISIBLE_CHAR_RE.findall(body)) >= 12:
                        continue
                issues.append(
                    f"AUTHOR_ONSCREEN_INCOMPLETE_DETAIL: module '{heading}' has a visible "
                    f"detail without a complete business action, relation, or result: {line!r}"
                )
    return issues

def _authored_bare_label_detail_issues(
    page: dict[str, Any],
    slide: dict[str, Any],
    items: dict[str, dict[str, Any]],
) -> list[str]:
    """Keep source detail and role-bearing payload attached to visible labels."""

    contract = page.get("onscreen_contract")
    contract = contract if isinstance(contract, dict) else {}
    detail_policy = contract.get("detail_policy")
    detail_policy = detail_policy if isinstance(detail_policy, dict) else {}
    label_only_allowed = detail_policy.get("label_only_allowed") is True
    contract_modules = {
        str(module.get("heading") or "").strip(): module
        for module in contract.get("modules") or []
        if isinstance(module, dict) and str(module.get("heading") or "").strip()
    }
    page_evidence_ids = _page_evidence_ids(page)
    issues: list[str] = []
    for module_index, module in enumerate(slide.get("onscreen") or []):
        if not isinstance(module, dict):
            continue
        heading = str(module.get("heading") or "").strip()
        visible_items = [
            str(value).strip()
            for value in module.get("items") or []
            if isinstance(value, str) and value.strip()
        ]
        if not visible_items:
            continue
        module_contract = contract_modules.get(heading, {})
        evidence_ids = {
            str(value)
            for value in module_contract.get("evidence_refs") or []
            if str(value)
        } or page_evidence_ids
        source_statements = [
            _item_text(items[item_id])
            for item_id in evidence_ids
            if item_id in items
        ]
        collapsed = [
            value
            for value in visible_items
            if (
                is_bare_business_label(value)
                and source_has_richer_item_detail(value, source_statements)
            )
            or label_enumeration_collapses_richer_detail(value, source_statements)
        ]
        role_only = functional_group_needs_item_explanations(
            heading,
            visible_items,
            content_load=page.get("content_load"),
            label_only_allowed=label_only_allowed,
        )
        if collapsed or role_only:
            labels = collapsed or [
                value for value in visible_items if is_bare_business_label(value)
            ]
            issues.append(
                "onscreen module {index} '{heading}' collapses source-backed or role-bearing "
                "details into bare labels {labels}; write '标签：来源支持的对象、作用、任务或边界' "
                "without terminal punctuation. Use detail_policy.label_only_allowed=true only "
                "when the approved source intentionally provides a label-only taxonomy".format(
                    index=module_index,
                    heading=heading or "?",
                    labels=labels,
                )
            )
    return issues

def _audit_authored_content_coverage(page: dict[str, Any], slide: dict[str, Any]) -> list[str]:
    route = page.get("content_route")
    if not isinstance(route, dict):
        return []
    visible = re.sub(r"\s+", "", _slide_text(slide))
    slide_id = str(slide.get("id") or page.get("id") or "?")
    issues: list[str] = []
    for signal in route.get("meaning_signals") or []:
        if isinstance(signal, str) and signal.strip() and re.sub(r"\s+", "", signal) not in visible:
            issues.append(
                f"{slide_id}: content_route meaning signal '{signal}' is absent from final copy"
            )
    return issues

def _authored_relationships_issues(page: dict[str, Any], slide: dict[str, Any]) -> list[str]:
    """Every `relationships[]` edge AUTHOR writes must trace to PLAN's approved topology."""
    primary = page.get("primary_relation")
    if not isinstance(primary, dict):
        return []
    scope = {s for s in primary.get("scope") or [] if isinstance(s, str)}
    rel_type = primary.get("type")
    secondary_pairs = {
        (relation.get("from"), relation.get("to"))
        for relation in (page.get("secondary_relations") or [])
        if isinstance(relation, dict)
    }
    hard_topology_allows_scoped_pairs = rel_type in ("sequence", "hierarchy", "matrix", "mixed")

    issues: list[str] = []
    for r_index, relation in enumerate(slide.get("relationships") or []):
        if not isinstance(relation, dict):
            continue
        from_label, to_label = relation.get("from"), relation.get("to")
        pair = (from_label, to_label)
        if pair in secondary_pairs:
            continue
        if hard_topology_allows_scoped_pairs and from_label in scope and to_label in scope:
            continue
        if not scope and not secondary_pairs:
            continue
        issues.append(
            f"relationships[{r_index}] ({from_label} → {to_label}): not declared in plan's "
            "primary_relation topology or secondary_relations; AUTHOR cannot invent a relation "
            "edge PLAN did not sanction"
        )
    return issues

def _audit_lean_authored_source_consumption(
    page: dict[str, Any],
    slide: dict[str, Any],
    items: dict[str, dict[str, Any]],
    foundation: dict[str, Any],
) -> list[str]:
    """Audit AUTHOR's actual evidence selection directly against the Final Script slide.

    A v2 lean Deck Plan only states the page's source_refs boundary; it must not carry
    an AUTHOR-owned source_consumption contract (forbidden by
    ``_PLAN_FORBIDDEN_PAGE_AUTHOR_FIELDS`` in deck_plan.py). So a strict/legacy
    Foundation's ``source_consumption_policy: required`` cannot be enforced at PLAN
    time — it is checked post-hoc against what AUTHOR actually wrote:
    ``slide.source_refs`` declares which Foundation records were used, and
    ``full_copy`` must carry their source-specific semantics and protected values.
    """
    if not requires_source_consumption(page, foundation):
        return []

    page_refs = {ref for ref in page.get("source_refs") or [] if isinstance(ref, str) and ref}
    slide_refs = [ref for ref in slide.get("source_refs") or [] if isinstance(ref, str) and ref]

    if not slide_refs:
        return [
            "AUTHOR_SOURCE_CONSUMPTION_MISSING: strict sourced content page requires "
            "slide.source_refs to declare the Foundation records AUTHOR actually used"
        ]

    issues: list[str] = []
    unknown = sorted({ref for ref in slide_refs if ref not in items})
    if unknown:
        issues.append(
            f"AUTHOR_SOURCE_REF_UNKNOWN: slide.source_refs cites unknown foundation records {unknown}"
        )
    outside = sorted({ref for ref in slide_refs if ref not in page_refs} - set(unknown))
    if outside:
        issues.append(
            "AUTHOR_SOURCE_REF_OUTSIDE_PLAN_SCOPE: slide.source_refs "
            f"{outside} fall outside the page's PLAN-approved source_refs boundary"
        )

    usable_refs = sorted(ref for ref in set(slide_refs) if ref in page_refs and ref in items)

    substantive_page_refs = {
        ref for ref in page_refs
        if ref in items and not _looks_like_structural_metadata(_item_text(items[ref]))
    }
    substantive_usable_refs = [
        ref for ref in usable_refs
        if not _looks_like_structural_metadata(_item_text(items[ref]))
    ]
    distinct_statements = {
        str(items[ref].get("statement") or _item_text(items[ref])).strip()
        for ref in substantive_usable_refs
        if str(items[ref].get("statement") or _item_text(items[ref])).strip()
    }
    minimum_distinct = min(3, len(substantive_page_refs))
    if minimum_distinct and len(distinct_statements) < minimum_distinct:
        issues.append(
            "AUTHOR_SOURCE_CONSUMPTION_TOO_NARROW: usable evidence covers only "
            f"{len(distinct_statements)} distinct source fact(s), fewer than the required "
            f"{minimum_distinct}; a strict sourced page cannot rest the whole argument on one fact"
        )

    full_copy = str(slide.get("full_copy") or "")
    compact_full_copy = re.sub(r"\s+", "", full_copy)

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", full_copy)
        if paragraph.strip()
    ]
    required_paragraphs = (
        3 if len(substantive_usable_refs) >= 6
        else 2 if len(substantive_usable_refs) >= 3
        else 1
    )
    if len(paragraphs) < required_paragraphs:
        issues.append(
            "AUTHOR_FULL_COPY_TOO_THIN: full_copy uses "
            f"{len(substantive_usable_refs)} substantive source facts but exposes only "
            f"{len(paragraphs)} substantive paragraph(s); at least {required_paragraphs} "
            "argument paragraph(s) are required so the complete copy preserves an "
            "audience-facing reasoning hierarchy before onscreen compression"
        )

    selected_source_statements = [
        statement
        for ref in substantive_usable_refs
        for statement in _source_surface_values(items[ref])
        if statement
    ]
    for paragraph_index, paragraph in enumerate(paragraphs):
        overlap = max(
            (
                _source_statement_overlap(statement, paragraph)
                for statement in selected_source_statements
            ),
            default=0.0,
        )
        if overlap < 0.04:
            issues.append(
                "AUTHOR_FULL_COPY_PARAGRAPH_UNGROUNDED: full_copy paragraph "
                f"{paragraph_index + 1} has no source-specific support from the "
                f"page's declared evidence (overlap={overlap:.3f})"
            )

    for ref in usable_refs:
        item = items[ref]
        primary_statement = str(
            item.get("statement")
            or item.get("claim")
            or item.get("definition")
            or item.get("relation")
            or _item_text(item)
        ).strip()
        overlap = (
            _source_statement_overlap(primary_statement, full_copy)
            if primary_statement else 0.0
        )
        if overlap < 0.08:
            issues.append(
                f"AUTHOR_SOURCE_SEMANTICS_LOST: {ref} is declared as used but its source-specific "
                f"content is absent from full_copy (overlap={overlap:.3f}); "
                f"source statement: {primary_statement or _item_text(item)}"
            )

        source_surface = " ".join(_source_surface_values(item))
        protected_numbers = set(
            re.findall(
                r"\d+(?:\.\d+)?(?:年\d{1,2}月\d{1,2}日|年|月|日|%|％|万|亿|项|级)?",
                source_surface,
            )
        )
        for number_ref in item.get("number_refs") or []:
            number = items.get(number_ref)
            if not isinstance(number, dict):
                continue
            raw_value = number.get("value")
            unit = str(number.get("unit") or "").strip()
            raw_values = raw_value if isinstance(raw_value, list) else [raw_value]
            for raw_entry in raw_values:
                value = "" if raw_entry is None else str(raw_entry).strip()
                if not value:
                    continue
                protected_numbers.add(value)
                if not isinstance(raw_value, list) and unit and unit not in {"时间", "年份", "生效日期"}:
                    protected_numbers.add(f"{value}{unit}")
        missing_numbers = sorted(
            value for value in protected_numbers
            if value and re.sub(r"\s+", "", value) not in compact_full_copy
        )
        if missing_numbers:
            issues.append(f"AUTHOR_NUMBER_OR_DATE_LOST: {ref} lost protected values {missing_numbers}")

        missing_conditions = [
            str(value).strip()
            for value in item.get("conditions") or []
            if str(value).strip() and re.sub(r"\s+", "", str(value)) not in compact_full_copy
        ]
        if missing_conditions:
            issues.append(f"AUTHOR_CONDITION_LOST: {ref} lost source conditions {missing_conditions}")

        missing_entities = []
        for entity_ref in item.get("entity_refs") or []:
            entity = items.get(entity_ref)
            name = str((entity or {}).get("name") or "").strip()
            if name and re.sub(r"\s+", "", name) not in compact_full_copy:
                missing_entities.append(name)
        if missing_entities:
            issues.append(f"AUTHOR_RESPONSIBILITY_LOST: {ref} lost source actors {missing_entities}")

        status = str(item.get("status") or "").strip()
        if not _status_strength_preserved(status, full_copy):
            issues.append(f"AUTHOR_STATUS_STRENGTH_LOST: {ref} lost source status '{status}'")

    return issues


def _onscreen_surface(slide: dict[str, Any]) -> str:
    return " ".join(
        value
        for module in slide.get("onscreen") or []
        if isinstance(module, dict)
        for value in (
            [str(module.get("heading") or "").strip()]
            + _onscreen_module_lines(module)
        )
        if value
    )


def _audit_lean_onscreen_full_copy_alignment(slide: dict[str, Any]) -> list[str]:
    """Require every visible v2-lean proposition to derive from complete copy."""
    if slide.get("page_type") != "content":
        return []

    full_copy = str(slide.get("full_copy") or "").strip()
    core_message = str(slide.get("core_message") or "").strip()
    issues: list[str] = []
    if core_message and _source_statement_overlap(core_message, full_copy, size=3) < 0.08:
        issues.append(
            "AUTHOR_ONSCREEN_FULL_COPY_DISCONNECTED: core_message is not materially "
            "supported by full_copy"
        )

    heading_support = " ".join(value for value in (core_message, full_copy) if value)
    compact_full_copy = re.sub(r"\s+", "", full_copy)
    for module_index, module in enumerate(slide.get("onscreen") or []):
        if not isinstance(module, dict):
            continue
        heading = str(module.get("heading") or "").strip()
        if heading and _source_statement_overlap(heading, heading_support, size=3) < 0.08:
            issues.append(
                "AUTHOR_ONSCREEN_FULL_COPY_DISCONNECTED: onscreen module "
                f"{module_index + 1} heading {heading!r} has no semantic anchor in "
                "core_message or full_copy"
            )
        for line in _onscreen_module_lines(module):
            overlap = _source_statement_overlap(line, full_copy, size=3)
            if overlap < 0.08:
                issues.append(
                    "AUTHOR_ONSCREEN_FULL_COPY_DISCONNECTED: onscreen module "
                    f"{module_index + 1} detail {line!r} is not a supported selection "
                    f"from full_copy (overlap={overlap:.3f})"
                )
            visible_numbers = set(
                re.findall(
                    r"\d+(?:\.\d+)?(?:年\d{1,2}月\d{1,2}日|年|月|日|%|％|万|亿|项|级)?",
                    line,
                )
            )
            missing_numbers = sorted(
                number for number in visible_numbers
                if number and re.sub(r"\s+", "", number) not in compact_full_copy
            )
            if missing_numbers:
                issues.append(
                    "AUTHOR_ONSCREEN_PROTECTED_FACT_DRIFTED: onscreen module "
                    f"{module_index + 1} introduces values absent from full_copy: "
                    f"{missing_numbers}"
                )
    return issues


def _audit_lean_relationship_visibility(slide: dict[str, Any]) -> list[str]:
    """Require relationship claims and edges to be visible in both copy layers."""
    if slide.get("page_type") != "content":
        return []

    full_copy = str(slide.get("full_copy") or "").strip()
    visible = _onscreen_surface(slide)
    relationships = [
        relation
        for relation in slide.get("relationships") or []
        if isinstance(relation, dict)
    ]
    claim_surface = " ".join(
        str(slide.get(key) or "") for key in ("core_message", "visual_thesis")
    )
    issues: list[str] = []
    if _RELATIONSHIP_CLAIM_RE.search(claim_surface) and not relationships:
        issues.append(
            "AUTHOR_RELATIONSHIP_NOT_MATERIALIZED: the page claims a relationship "
            "but declares no edge with two endpoints and a connecting action"
        )

    for relation_index, relation in enumerate(relationships):
        missing = [
            key for key in ("from", "to", "relation")
            if not str(relation.get(key) or "").strip()
        ]
        if missing:
            issues.append(
                "AUTHOR_RELATIONSHIP_NOT_MATERIALIZED: relationships[{}] is missing "
                "{}".format(relation_index, missing)
            )
            continue
        statement = " ".join(
            str(relation.get(key) or "").strip()
            for key in ("from", "relation", "to")
        )
        prose_overlap = _source_statement_overlap(statement, full_copy, size=3)
        visible_overlap = _source_statement_overlap(statement, visible, size=3)
        if prose_overlap < 0.08 or visible_overlap < 0.08:
            issues.append(
                "AUTHOR_RELATIONSHIP_METADATA_ONLY: relationships[{}] is not "
                "materially expressed in both full_copy and onscreen "
                "(full_copy={:.3f}, onscreen={:.3f})".format(
                    relation_index, prose_overlap, visible_overlap
                )
            )
    return issues

def _audit_authored_onscreen_composition(
    page: dict[str, Any], slide: dict[str, Any]
) -> list[str]:
    """Check that module lead text follows the approved page composition policy."""
    composition = page.get("onscreen_composition")
    if not isinstance(composition, dict):
        return []

    issues = _audit_onscreen_composition_definition(page)
    mode = composition.get("mode")
    if mode not in _ONSCREEN_COMPOSITION_MODES:
        return issues

    slide_id = str(slide.get("id") or page.get("id") or "?")
    modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    lead_modules = [
        module for module in modules
        if isinstance(module.get("text"), str) and module["text"].strip()
    ]
    if mode == "evidence_first":
        for module in lead_modules:
            heading = str(module.get("heading") or "?").strip()
            issues.append(
                f"{slide_id}: onscreen_composition='evidence_first' forbids module lead text in "
                f"'{heading}'; move the judgment to core_message and retain source facts as evidence items"
            )
        for module in modules:
            issues.extend(_evidence_first_item_hierarchy_issues(slide_id, module))
    else:
        lead_budget = composition.get("lead_budget")
        if isinstance(lead_budget, int) and not isinstance(lead_budget, bool) and len(lead_modules) > lead_budget:
            issues.append(
                f"{slide_id}: onscreen_composition='selective_lead' permits at most {lead_budget} "
                f"module lead(s), got {len(lead_modules)}"
            )
    return issues


def _semantic_payload_units(module: dict[str, Any]) -> int:
    """Estimate distinct reader-facing information units in one module.

    A line is one unit.  Parallel details separated by Chinese list punctuation
    contribute additional units, so a compact taxonomy can remain dense without
    being expanded into artificial cards or repeated explanatory sentences.
    """

    units = 0
    for line in _onscreen_module_lines(module):
        fragments = [
            fragment.strip()
            for fragment in re.split(r"[、，,；;]", line)
            if fragment.strip()
        ]
        units += max(1, len(fragments))
    return units


def _audit_self_reading_density(
    delivery_mode: str | dict[str, Any], page: dict[str, Any], slide: dict[str, Any]
) -> list[str]:
    """Require content pages in self-read decks to explain themselves on screen.

    The threshold scales with the approved module count and ``content_load``.
    Structural pages are intentionally excluded.  This guards independent
    readability without imposing one universal word, line, or card count.
    """

    mode = str(delivery_mode.get("delivery_mode") if isinstance(delivery_mode, dict) else delivery_mode)
    page_type = str(slide.get("page_type") or page.get("page_role") or "")
    if mode != "self_read" or page_type != "content":
        return []
    load = str(slide.get("content_load") or page.get("content_load") or "standard")
    if load == "light":
        return []
    modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    slide_id = str(slide.get("id") or page.get("id") or "?")
    if not modules:
        return [f"ONSCREEN_SELF_READ_PAYLOAD_MISSING: {slide_id} has no reader-facing modules"]
    issues: list[str] = []
    empty_headings = [
        str(module.get("heading") or "?").strip()
        for module in modules
        if not _onscreen_module_lines(module)
    ]
    if empty_headings:
        issues.append(
            f"ONSCREEN_SELF_READ_MODULE_THIN: {slide_id} modules {empty_headings} have headings "
            "without explanatory payload"
        )
    units = sum(_semantic_payload_units(module) for module in modules)
    module_count = len(modules)
    minimum = 2 * module_count if load == "dense" else (3 * module_count + 1) // 2
    if units < minimum:
        issues.append(
            f"ONSCREEN_SELF_READ_DENSITY_LOW: {slide_id} {load} content provides {units} "
            f"semantic payload units across {module_count} modules; at least {minimum} are "
            "required for independent reading at the approved load. Add distinct source-backed "
            "facts, roles, conditions, boundaries or results; do not repeat the page judgment"
        )
    return issues

def _audit_authored_onscreen_contract(
    page: dict[str, Any], slide: dict[str, Any], items: dict[str, dict[str, Any]]
) -> list[str]:
    """Check that AUTHOR consumed the declared module-level semantic contract.

    This intentionally does not infer a module's meaning from keywords on pages that
    have no contract.  The plan author declares the page's axis, source scope and role
    vocabulary; the final audit then checks the visible module payload against it.
    """
    contract = page.get("onscreen_contract")
    if not isinstance(contract, dict):
        return []

    issues = _onscreen_contract_definition_issues(page, contract, items)
    expected_modules = [module for module in contract.get("modules") or [] if isinstance(module, dict)]
    actual_modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    expected_headings = [str(module.get("heading") or "").strip() for module in expected_modules]
    actual_headings = [str(module.get("heading") or "").strip() for module in actual_modules]
    slide_id = str(slide.get("id") or page.get("id") or "?")

    if actual_headings != expected_headings:
        issues.append(
            f"{slide_id}: onscreen module headings do not match the approved contract; "
            f"expected {expected_headings}, got {actual_headings}"
        )

    modules_by_heading = {
        str(module.get("heading") or "").strip(): module
        for module in actual_modules
        if str(module.get("heading") or "").strip()
    }
    contract_headings = set(expected_headings)
    policy = contract.get("detail_policy") or {}
    if not isinstance(policy, dict):
        policy = {}
    role_markers = policy.get("role_markers") or {}
    if not isinstance(role_markers, dict):
        role_markers = {}
    allowed_roles = {str(role) for role in policy.get("allowed_roles") or []}
    forbidden_roles = {str(role) for role in policy.get("forbidden_roles") or []}
    forbidden_patterns = [pattern for pattern in policy.get("forbidden_patterns") or [] if isinstance(pattern, str)]

    for expected in expected_modules:
        heading = str(expected.get("heading") or "").strip()
        module = modules_by_heading.get(heading)
        if module is None:
            continue
        lines = _onscreen_module_lines(module)
        body = " ".join(lines)
        for signal in expected.get("required_signals") or []:
            if isinstance(signal, str) and signal and signal not in body:
                issues.append(
                    f"ONSCREEN_REQUIRED_SIGNAL_MISSING: {slide_id} module '{heading}': "
                    f"required signal '{signal}' is missing"
                )
        for signal in expected.get("forbidden_signals") or []:
            if isinstance(signal, str) and signal and signal in body:
                issues.append(f"{slide_id} module '{heading}': forbidden cross-scope signal '{signal}' is present")

        if contract.get("scope_mode") == "exclusive":
            for other_heading in contract_headings - {heading}:
                if other_heading and other_heading in body:
                    issues.append(
                        f"{slide_id} module '{heading}': exclusive scope contains peer module heading '{other_heading}'"
                    )

        for line in lines:
            matched_roles: set[str] = set()
            for role, patterns in role_markers.items():
                if not isinstance(role, str) or not isinstance(patterns, list):
                    continue
                for pattern in patterns:
                    if not isinstance(pattern, str) or not pattern:
                        continue
                    try:
                        if re.search(pattern, line):
                            matched_roles.add(role)
                            break
                    except re.error:
                        # The definition audit reports the malformed pattern.  Avoid
                        # duplicating that same error for every authored line.
                        continue
            disallowed = matched_roles.intersection(forbidden_roles)
            if allowed_roles:
                disallowed.update(matched_roles - allowed_roles)
            if disallowed:
                issues.append(
                    f"{slide_id} module '{heading}': detail line '{line}' uses disallowed role(s) "
                    f"{sorted(disallowed)}"
                )
            for pattern in forbidden_patterns:
                try:
                    matched = re.search(pattern, line)
                except re.error:
                    matched = None
                if matched:
                    issues.append(
                        f"{slide_id} module '{heading}': detail line '{line}' matches forbidden pattern '{pattern}'"
                    )
    return issues

def _slide_text(slide: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "subtitle", "mission", "core_message", "full_copy", "visual_thesis", "speaker_notes"):
        value = slide.get(key)
        if isinstance(value, str):
            parts.append(value)
    argument = slide.get("argument") or {}
    if isinstance(argument, dict):
        if isinstance(argument.get("pattern"), str):
            parts.append(argument["pattern"])
        parts.extend(x for x in (argument.get("chain") or []) if isinstance(x, str))
    for module in slide.get("onscreen") or []:
        if not isinstance(module, dict):
            continue
        for key in ("heading", "text"):
            value = module.get(key)
            if isinstance(value, str):
                parts.append(value)
        parts.extend(x for x in (module.get("items") or []) if isinstance(x, str))
    for relation in slide.get("relationships") or []:
        if not isinstance(relation, dict):
            continue
        for key in ("from", "to", "relation"):
            value = relation.get(key)
            if isinstance(value, str):
                parts.append(value)
    return " ".join(parts)

def _source_text_for_refs(source_refs: list[Any], foundation: dict[str, Any]) -> str:
    refs = {x for x in source_refs if isinstance(x, str)}
    parts: list[str] = []
    for key in CITABLE_KEYS:
        for item in foundation.get(key) or []:
            if not isinstance(item, dict):
                continue
            if refs.intersection(x for x in (item.get("source_refs") or []) if isinstance(x, str)):
                parts.append(_item_text(item))
    return " ".join(parts)

def _normalize_source_chapter_title(title: str) -> str:
    return CHAPTER_PREFIX_RE.sub("", title).strip(" 　")


_RELATIONSHIP_CLAIM_RE = re.compile(
    r"(映射|协同|闭环|衔接|转化|贯通|联动|传导|反馈|对应|支撑.+(?:形成|实现|落地))"
)


def _whole_deck_authoring_warnings(final_script: dict[str, Any]) -> list[str]:
    """Flag deck-wide authoring regressions that page-local checks cannot see.

    These are review signals, not fixed layout rules.  A short deck can
    legitimately use the same composition on every page, and a taxonomy deck
    can legitimately carry few explicit relationships.
    """
    content_slides = [
        slide
        for slide in final_script.get("slides") or []
        if isinstance(slide, dict) and slide.get("page_type") == "content"
    ]
    if len(content_slides) < 6:
        return []

    warnings: list[str] = []
    shapes: list[tuple[int, int]] = []
    for slide in content_slides:
        modules = [
            module for module in slide.get("onscreen") or [] if isinstance(module, dict)
        ]
        shapes.append(
            (
                len(modules),
                sum(len(module.get("items") or []) for module in modules),
            )
        )
    if len(set(shapes)) == 1:
        module_count, item_count = shapes[0]
        warnings.append(
            "AUTHOR_STRUCTURE_FLATLINE: all "
            f"{len(content_slides)} content pages use the same {module_count}-module/"
            f"{item_count}-item shape; run whole-deck Critic to verify that page missions, "
            "evidence depth and relationship grammars were authored independently"
        )

    relationship_count = sum(
        len([item for item in slide.get("relationships") or [] if isinstance(item, dict)])
        for slide in content_slides
    )
    relation_claim_pages = [
        str(slide.get("id") or "?")
        for slide in content_slides
        if _RELATIONSHIP_CLAIM_RE.search(
            " ".join(
                str(slide.get(key) or "")
                for key in ("core_message", "visual_thesis")
            )
        )
    ]
    if relationship_count == 0 and len(relation_claim_pages) >= 2:
        warnings.append(
            "AUTHOR_RELATIONSHIP_LAYER_ABSENT: the deck makes relationship claims on "
            f"{relation_claim_pages} but no content page declares relationships; verify "
            "both endpoints and the connecting action in Final Script"
        )
    return warnings

def audit_final_script(final_script: dict[str, Any], plan: dict[str, Any], foundation: dict[str, Any]) -> tuple[list[str], list[str]]:
    issues: list[str] = audit_final_internal_expert_voice(final_script, plan)
    warnings: list[str] = []
    issues.extend(hard_finding_messages(trace_composed(final_script, foundation)))
    items = foundation_items_by_id(foundation)
    pages = {p.get("id"): p for p in (plan.get("pages") or []) if isinstance(p, dict) and isinstance(p.get("id"), str)}
    chapters = {c.get("id"): c for c in (plan.get("chapters") or []) if isinstance(c, dict) and isinstance(c.get("id"), str)}
    structure = {x.get("id"): x for x in (foundation.get("source_structure") or []) if isinstance(x, dict) and isinstance(x.get("id"), str)}
    audience_scope = plan.get("audience_scope", "unspecified")
    preserve_structure = plan.get("source_structure_mode") == "preserve"
    delivery_mode = str((final_script.get("deck") or {}).get("delivery_mode") or plan.get("delivery_mode") or "self_read")

    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        page = pages.get(slide_id)
        if page is None:
            warnings.append(f"slides.{index} ({slide_id}): no matching deck-plan page; semantic inheritance cannot be audited")
            continue
        final_text = _slide_text(slide)
        plan_text = _page_text(page)
        evidence_ids = _page_evidence_ids(page)
        evidence = _support_items(sorted(evidence_ids), items)

        plan_model = str((page.get("analysis_basis") or {}).get("model") or "").lower()
        plan_logic = str(page.get("logic") or "")
        plan_is_classification = any(token in plan_model for token in ("classification", "taxonomy", "typology")) or "分类" in plan_logic
        plan_allows_progression = bool(PROGRESSION_RE.search(plan_text) or any(token in plan_model for token in ("progression", "maturity")))
        if plan_is_classification and not plan_allows_progression and PROGRESSION_RE.search(final_text):
            issues.append(f"slides.{index} ({slide_id}): AUTHOR upgraded a classification/taxonomy plan into a progression chain")

        if _has_optionality(evidence) and not _preserves_optionality(final_text):
            issues.append(f"slides.{index} ({slide_id}): final script lost source optionality; it must preserve independent choice and progressive deepening")

        group_issue = _group_strength_issue(str(slide.get("core_message") or ""), evidence)
        if group_issue:
            issues.append(f"slides.{index} ({slide_id}): {group_issue}")

        internal = [item for item in evidence if effective_visibility(item) == "internal_only"]
        if audience_scope == "external" and internal:
            exposed: list[str] = []
            for item in internal:
                item_text = _item_text(item)
                values = [str(item.get("value") or "")]
                for match in re.findall(r"\d+(?:\.\d+)?%?(?:至|-|—)\d+(?:\.\d+)?%?|\d+(?:\.\d+)?%", item_text):
                    values.append(match)
                normalized_final = final_text.replace("至", "-").replace("—", "-")
                if any(value and value.replace("至", "-").replace("—", "-") in normalized_final for value in values):
                    exposed.append(str(item.get("id") or "?"))
            if exposed:
                issues.append(f"slides.{index} ({slide_id}): external final script exposes internal-only evidence {sorted(set(exposed))}")

        if GAP_RE.search(final_text):
            source_text = _source_text_for_refs(page.get("source_refs") or [], foundation)
            if not GAP_RE.search(plan_text) and not GAP_RE.search(source_text):
                issues.append(f"slides.{index} ({slide_id}): final script introduces a current-vs-target gap judgment without a source or plan baseline")

        for composition_issue in _audit_authored_onscreen_composition(page, slide):
            issues.append(f"slides.{index} ({slide_id}): {composition_issue}")
        for density_issue in _audit_self_reading_density(delivery_mode, page, slide):
            issues.append(f"slides.{index} ({slide_id}): {density_issue}")
        for contract_issue in _audit_authored_onscreen_contract(page, slide, items):
            issues.append(f"slides.{index} ({slide_id}): {contract_issue}")
        # A lean Deck Plan deliberately omits AUTHOR prose and onscreen contracts, so
        # Foundation-owned source-consumption safeguards (source_consumption_policy:
        # required) cannot be checked against PLAN — they are checked here, directly
        # against what AUTHOR actually wrote.
        for consumption_issue in _audit_lean_authored_source_consumption(
            page, slide, items, foundation
        ):
            issues.append(f"slides.{index} ({slide_id}): {consumption_issue}")
        for alignment_issue in _audit_lean_onscreen_full_copy_alignment(slide):
            issues.append(f"slides.{index} ({slide_id}): {alignment_issue}")
        for relationship_issue in _audit_lean_relationship_visibility(slide):
            issues.append(f"slides.{index} ({slide_id}): {relationship_issue}")
        for coverage_issue in _audit_authored_content_coverage(page, slide):
            issues.append(f"slides.{index} ({slide_id}): {coverage_issue}")
        for detail_issue in _authored_bare_label_detail_issues(page, slide, items):
            issues.append(
                f"slides.{index} ({slide_id}): ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL: "
                f"{detail_issue}"
            )
        for author_issue in _author_execution_issues(delivery_mode, page, slide, items):
            issues.append(f"slides.{index} ({slide_id}): {author_issue}")
        warnings.extend(
            f"slides.{index} ({slide_id}): {warning}"
            for warning in _onscreen_expression_warnings(page, slide)
        )

        if preserve_structure and slide.get("page_type") == "chapter":
            chapter_id = slide.get("chapter_id")
            chapter = chapters.get(chapter_id) if isinstance(chapter_id, str) else None
            source_ids = chapter.get("source_chapter_ids") if isinstance(chapter, dict) else None
            if source_ids and len(source_ids) == 1:
                node = structure.get(source_ids[0])
                if isinstance(node, dict) and isinstance(node.get("title"), str):
                    expected = _normalize_source_chapter_title(node["title"])
                    actual = str(slide.get("title") or "").strip()
                    if actual and expected and actual != expected:
                        issues.append(f"slides.{index} ({slide_id}): source_structure_mode='preserve' requires chapter title '{expected}', got '{actual}'")

    warnings.extend(_whole_deck_authoring_warnings(final_script))
    return issues, warnings

__all__ = ['_onscreen_module_lines', '_is_lead_like_evidence_item', '_evidence_first_item_hierarchy_issues', '_is_readable_proposition', '_onscreen_expression_warnings', '_looks_like_structural_metadata', '_author_execution_issues', '_authored_bare_label_detail_issues', '_audit_authored_content_coverage', '_authored_relationships_issues', '_audit_lean_authored_source_consumption', '_audit_lean_onscreen_full_copy_alignment', '_audit_lean_relationship_visibility', '_audit_authored_onscreen_composition', '_semantic_payload_units', '_audit_self_reading_density', '_audit_authored_onscreen_contract', '_slide_text', '_source_text_for_refs', '_normalize_source_chapter_title', '_whole_deck_authoring_warnings', 'audit_final_script']
