"""Source coverage rules for authored PPT scripts."""

from __future__ import annotations

import re

from cyberppt.semantic_expression_models import load_expression_models

from .common import _source_statement_overlap
from .models import ScriptPage, ScriptQualityIssue, _issue
from .parsing import _module_title
from .text_rules import NEGATION_TERMS, normalized_tokens, text_similarity


def _dict_items(
    payload: dict[str, object],
    key: str,
) -> list[dict[str, object]]:
    value = payload.get(key)
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _outline_pages(
    outline: dict[str, object],
) -> dict[str, dict[str, object]]:
    return {
        str(page.get("page_id")): page
        for page in _dict_items(outline, "pages")
    }


def _truth_records(
    source_truth: dict[str, object],
) -> dict[str, dict[str, object]]:
    return {
        str(record.get("id")): record
        for record in _dict_items(source_truth, "records")
    }


def _polarity_dropped_terms(statement: str, authored: str) -> tuple[str, ...]:
    """Return source negation markers that vanish from the authored text.

    ``_source_statement_overlap`` scores character-shingle survival and is
    blind to polarity: dropping "不得"/"禁止" from an otherwise long,
    shingle-heavy statement barely moves the overlap ratio, so a rewrite that
    silently inverts a prohibition into its opposite ("不得对外提供" ->
    "对外提供") can still pass as "covered". Flag that gap directly by
    requiring every negation marker present in the source statement to also
    appear in the authored text.
    """

    return tuple(term for term in NEGATION_TERMS if term in statement and term not in authored)


def _source_consumption_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    """Verify that source-grounded content units reach the authored page.

    ``source_refs`` prove traceability only.  Strict Outline v2 pages also
    carry ``source_statements`` in each content unit; this check requires the
    editorial unit or at least one of its factual anchors to survive in the
    full prose/visible layer.  Supporting units may be compressed, while the
    primary unit remains mandatory.
    """

    evidence_contract = contract.get("source_evidence_contract")
    if not isinstance(evidence_contract, dict) or evidence_contract.get("mode") != "required":
        return []
    raw_units = contract.get("content_units")
    if not isinstance(raw_units, list):
        return []
    expected_unit_ids = {
        str(unit.get("unit_id"))
        for unit in raw_units
        if isinstance(unit, dict)
        and str(unit.get("role") or "") != "boundary"
        and unit.get("unit_id")
    }
    receipt = page.contract_receipt or {}
    declared_unit_ids = receipt.get("consumed_content_unit_ids")
    if not isinstance(declared_unit_ids, list):
        return [
            _issue(
                "CONTENT_UNIT_CONSUMPTION_DECLARATION_MISSING",
                page,
                "The page receipt must declare the content units consumed by the authored page.",
                "Copy the explicit consumes list from the page authoring artifact into the page receipt.",
            )
        ]
    if {str(item) for item in declared_unit_ids} != expected_unit_ids:
        return [
            _issue(
                "CONTENT_UNIT_CONSUMPTION_DECLARATION_MISMATCH",
                page,
                "The page receipt consumes a different set of content units than the approved Outline.",
                "Align the page authoring consumes list with every non-boundary content_unit.unit_id.",
                evidence=tuple(sorted(expected_unit_ids)),
            )
        ]
    contract_units_by_id = {
        str(unit.get("unit_id")): unit
        for unit in evidence_contract.get("units", [])
        if isinstance(unit, dict) and unit.get("unit_id")
    }
    contract_units = {
        tuple(str(item) for item in unit.get("source_refs") or []): unit
        for unit in evidence_contract.get("units", [])
        if isinstance(unit, dict)
    }
    authored = "\n".join(
        (page.full_prose, page.onscreen_text, page.speaker_notes, page.visual_structure)
    )
    issues: list[ScriptQualityIssue] = []
    for unit in raw_units:
        if not isinstance(unit, dict) or str(unit.get("role") or "") == "boundary":
            continue
        statement = str(unit.get("statement") or "")
        evidence_unit = contract_units_by_id.get(str(unit.get("unit_id"))) or contract_units.get(
            tuple(str(item) for item in unit.get("source_refs") or []),
            {},
        )
        source_statements = [
            str(item)
            for item in (
                unit.get("source_statements")
                or evidence_unit.get("source_statements")
                or []
            )
            if str(item).strip()
        ]
        unit_overlap = _source_statement_overlap(statement, authored)
        fact_overlaps = [
            _source_statement_overlap(item, authored)
            for item in source_statements
        ]
        dropped_negations = _polarity_dropped_terms(statement, authored)
        if not dropped_negations:
            for item in source_statements:
                dropped_negations = _polarity_dropped_terms(item, authored)
                if dropped_negations:
                    break
        if dropped_negations:
            refs = tuple(str(item) for item in unit.get("source_refs") or [])
            issues.append(
                _issue(
                    "SOURCE_POLARITY_MISMATCH",
                    page,
                    "The authored page drops a source negation marker, risking an inverted claim.",
                    "Restore the source's prohibition/negation wording (or an equivalent negative statement); do not let a shingle-overlap match hide a polarity flip.",
                    source_ids=refs,
                    evidence=(statement, *dropped_negations),
                )
            )
        threshold = 0.10 if str(unit.get("role") or "") == "primary" else 0.04
        if unit_overlap < threshold and max(fact_overlaps or [0.0]) < threshold:
            refs = tuple(str(item) for item in unit.get("source_refs") or [])
            issues.append(
                _issue(
                    "SOURCE_FACT_NOT_CONSUMED",
                    page,
                    "Source IDs are present, but the page does not consume the corresponding factual claim.",
                    "Rewrite 完整文字稿 or 上屏文字 from the content unit and its source statements; keep Source IDs as traceability only.",
                    source_ids=refs,
                    evidence=(statement, f"unit_overlap={unit_overlap:.3f}", f"max_fact_overlap={max(fact_overlaps or [0.0]):.3f}"),
                )
            )
    return issues


def _full_prose_source_coverage_issues(
    page: ScriptPage,
    contract: dict[str, object],
    records_by_id: dict[str, dict[str, object]],
) -> list[ScriptQualityIssue]:
    """Require every page-assigned fact to survive in 完整文字稿.

    Evidence identifiers prove provenance, not consumption.  A page may omit
    an assigned record only when the approved Outline declares a specific
    editorial reason in ``intentional_omissions``.
    """

    # ``source_refs`` is the complete evidence inventory, while
    # ``detail_refs`` explicitly marks retained traceability that does not
    # have to be narrated record by record.  Requiring those details in full
    # prose defeats the evidence hierarchy and turns appendices into page
    # copy.  Boundary evidence remains mandatory unless intentionally omitted.
    detail_refs = {str(ref) for ref in (contract.get("detail_refs") or [])}
    expected_refs = tuple(
        dict.fromkeys(
            str(ref)
            for field in ("source_refs", "boundary_refs")
            for ref in (contract.get(field) or [])
            if str(ref).strip() and str(ref) not in detail_refs
        )
    )
    omissions: set[str] = set()
    issues: list[ScriptQualityIssue] = []
    for item in contract.get("intentional_omissions") or []:
        if not isinstance(item, dict):
            issues.append(
                _issue(
                    "FULL_PROSE_OMISSION_INVALID",
                    page,
                    "Outline intentional_omissions entries must be objects.",
                    "Declare source_refs and a specific editorial reason in the approved Outline.",
                )
            )
            continue
        refs = tuple(str(ref) for ref in item.get("source_refs") or [] if str(ref).strip())
        reason = str(item.get("reason") or "").strip()
        if not refs or len(reason) < 8:
            issues.append(
                _issue(
                    "FULL_PROSE_OMISSION_REASON_MISSING",
                    page,
                    "An intentional omission requires source_refs and a specific editorial reason.",
                    "Explain why the source information is deliberately excluded from this page; generic importance labels are insufficient.",
                    source_ids=refs,
                )
            )
            continue
        omissions.update(refs)
    for ref in expected_refs:
        if ref in omissions:
            continue
        record = records_by_id.get(ref)
        if not record:
            continue
        anchors = [str(record.get("statement") or "")]
        anchors.extend(
            str(unit.get("text") or "")
            for unit in record.get("semantic_units") or []
            if isinstance(unit, dict) and str(unit.get("text") or "").strip()
        )
        overlap = max(
            (_source_statement_overlap(anchor, page.full_prose) for anchor in anchors if anchor.strip()),
            default=0.0,
        )
        if overlap < 0.08:
            issues.append(
                _issue(
                    "FULL_PROSE_SOURCE_COVERAGE_GAP",
                    page,
                    "The approved source record is cited but its factual content is absent from 完整文字稿.",
                    "Restore the source-specific fact in 完整文字稿, or record a specific intentional omission in the approved Outline.",
                    source_ids=(ref,),
                    evidence=(str(record.get("statement") or ""), f"overlap={overlap:.3f}"),
                )
            )
        dropped_negations: tuple[str, ...] = ()
        for anchor in anchors:
            if not anchor.strip():
                continue
            dropped_negations = _polarity_dropped_terms(anchor, page.full_prose)
            if dropped_negations:
                break
        if dropped_negations:
            issues.append(
                _issue(
                    "SOURCE_POLARITY_MISMATCH",
                    page,
                    "完整文字稿 drops a source negation marker, risking an inverted claim.",
                    "Restore the source's prohibition/negation wording (or an equivalent negative statement); do not let a shingle-overlap match hide a polarity flip.",
                    source_ids=(ref,),
                    evidence=(str(record.get("statement") or ""), *dropped_negations),
                )
            )
    return issues


def _full_prose_paragraph_boundary_issues(
    page: ScriptPage,
    contract: dict[str, object],
    records_by_id: dict[str, dict[str, object]],
) -> list[ScriptQualityIssue]:
    """Keep source-paragraph reasoning visible in the full-prose layer.

    The rule activates only when a page consumes at least three distinct
    source paragraphs.  It does not prohibit a deliberate merge, but makes
    that editorial choice explicit and checks that the mapped prose paragraph
    actually carries each assigned source record.
    """

    detail_refs = {str(ref) for ref in (contract.get("detail_refs") or [])}
    expected_refs = tuple(
        dict.fromkeys(
            str(ref)
            for field in ("source_refs", "boundary_refs")
            for ref in (contract.get(field) or [])
            if str(ref).strip() and str(ref) not in detail_refs and ref in records_by_id
        )
    )
    groups: dict[tuple[str, ...], list[str]] = {}
    for ref in expected_refs:
        unit_refs = tuple(str(item) for item in records_by_id[ref].get("source_unit_refs") or [] if str(item))
        if not unit_refs:
            continue
        groups.setdefault(unit_refs, []).append(ref)
    if len(groups) < 3:
        return []

    paragraphs = tuple(
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", page.full_prose)
        if paragraph.strip()
    )
    mapping = page.prose_paragraph_map
    if not mapping:
        return [_issue(
            "FULL_PROSE_PARAGRAPH_MAP_MISSING",
            page,
            "This page consumes several source paragraphs but does not record how they map into 完整文字稿 paragraphs.",
            "Add one ‘完整文字稿段落映射’ entry per prose paragraph. Keep source paragraphs separate by default; a combined entry must state 合并理由.",
            source_ids=expected_refs,
        )]
    issues: list[ScriptQualityIssue] = []
    if len(mapping) != len(paragraphs):
        issues.append(_issue(
            "FULL_PROSE_PARAGRAPH_MAP_COUNT_MISMATCH",
            page,
            "The paragraph map and 完整文字稿 have different paragraph counts.",
            "Use one mapping entry for each prose paragraph, in the same order.",
            evidence=(f"map={len(mapping)}", f"prose={len(paragraphs)}"),
        ))
    mapped_refs = tuple(ref for refs, _ in mapping for ref in refs)
    if set(mapped_refs) != set(expected_refs) or len(mapped_refs) != len(set(mapped_refs)):
        issues.append(_issue(
            "FULL_PROSE_PARAGRAPH_MAP_COVERAGE_INVALID",
            page,
            "The paragraph map must cover every non-detail page source once and only once.",
            "Correct the Source Truth IDs in 完整文字稿段落映射; retain details only when the Outline marks them as detail_refs.",
            source_ids=expected_refs,
            evidence=mapped_refs,
        ))
    group_by_ref = {ref: group for group, refs in groups.items() for ref in refs}
    for index, (refs, reason) in enumerate(mapping):
        source_groups = {group_by_ref.get(ref) for ref in refs}
        source_groups.discard(None)
        if len(source_groups) > 1 and len(reason) < 8:
            issues.append(_issue(
                "FULL_PROSE_PARAGRAPH_MERGE_REASON_MISSING",
                page,
                "A full-prose paragraph merges distinct source paragraphs without an editorial reason.",
                "Keep source paragraphs separate by default, or state a concrete 合并理由 explaining the shared argument duty and retained conclusion.",
                source_ids=refs,
            ))
        if index >= len(paragraphs):
            continue
        for ref in refs:
            record = records_by_id.get(ref)
            if not record:
                continue
            statement = str(record.get("statement") or "")
            if statement and _source_statement_overlap(statement, paragraphs[index]) < 0.05:
                issues.append(_issue(
                    "FULL_PROSE_PARAGRAPH_SOURCE_MISMATCH",
                    page,
                    "A mapped source record is not substantively represented in its assigned prose paragraph.",
                    "Move the source-specific fact into the mapped paragraph or correct the paragraph map.",
                    source_ids=(ref,),
                    evidence=(f"paragraph={index + 1}",),
                ))
    return issues


def _page_content_unit_coverage_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    """Verify atomic page content survives both prose and onscreen compression."""

    issues: list[ScriptQualityIssue] = []
    model_covered_refs, model_issues = _model_slot_coverage_issues(page, contract)
    if contract.get("source_grounding_mode") == "required":
        model_covered_refs = set()
    issues.extend(model_issues)
    units = [
        item for item in (contract.get("content_units") or [])
        if isinstance(item, dict)
    ]
    for unit in units:
        unit_id = str(unit.get("unit_id") or "")
        statement = str(unit.get("statement") or "").strip()
        priority = str(unit.get("priority") or "P2")
        source_refs = tuple(
            str(item) for item in unit.get("source_refs") or [] if str(item)
        )
        coverage_anchors = tuple(
            str(item).strip() for item in unit.get("coverage_anchors") or []
            if str(item).strip()
        )
        onscreen_anchors = tuple(
            str(item).strip() for item in unit.get("onscreen_anchors") or []
            if str(item).strip()
        )
        if unit.get("full_prose_required") is True:
            hits = tuple(anchor for anchor in coverage_anchors if anchor in page.full_prose)
            required_hits = max(2, (len(coverage_anchors) * 2 + 2) // 3)
            statement_overlap = _source_statement_overlap(statement, page.full_prose)
            # Short anchors prove literal retention where the author keeps the
            # source wording.  A natural professional rewrite can preserve the
            # full meaning without repeating two arbitrary clauses verbatim;
            # high statement overlap is an equivalent proof in that case.
            if (
                len(hits) < required_hits
                and statement_overlap < 0.35
            ) or statement_overlap < 0.12:
                issues.append(_issue(
                    "FULL_PROSE_CONTENT_UNIT_GAP",
                    page,
                    (
                        "页面原子内容单元来自P0级来源事实，没有完整进入完整文字稿；"
                        "P0缺口不接受锚点覆盖说明豁免，必须恢复。"
                        if priority == "P0" else
                        "页面原子内容单元没有完整进入完整文字稿，存在对象、动作、条件或业务特征丢失。"
                    ),
                    "恢复该内容单元的来源特征；不要用更抽象的概括句替代。",
                    source_ids=source_refs,
                    evidence=(
                        f"unit_id={unit_id}",
                        f"priority={priority}",
                        f"statement={statement}",
                        f"anchor_hits={len(hits)}/{len(coverage_anchors)}",
                        f"overlap={statement_overlap:.3f}",
                    ),
                ))
        if (
            unit.get("onscreen_required") is True
            and contract.get("source_grounding_mode") != "required"
            and not set(source_refs).issubset(model_covered_refs)
        ):
            # 副标题 renders on the slide alongside 上屏文字, and this project's
            # own convention (page-script-contract.md) deliberately puts a
            # page's core judgment there instead of repeating it in the body
            # (see ONSCREEN_REDUNDANT_RESTATEMENT). An anchor already visible
            # via the subtitle is not missing from the screen; search both
            # surfaces before declaring a gap.
            onscreen_surface = page.onscreen_text + "\n" + page.subtitle
            missing = tuple(
                anchor
                for anchor in onscreen_anchors
                if anchor not in onscreen_surface
                # A PPT slide is not a Word paragraph: a compressed,
                # phrase-based rewrite of the anchor (dropped connector,
                # reordered clause, swapped near-synonym) should not hard-fail
                # as long as the source-specific content clearly survives.
                # This overlap fallback used to only apply to anchors over 30
                # characters; short anchors got zero tolerance, which is
                # backwards -- a short anchor is exactly the case where a
                # natural author edit is most likely to touch a couple of
                # characters. Apply the same overlap bar regardless of length.
                and _source_statement_overlap(anchor, onscreen_surface) < 0.85
            )
            if missing:
                issues.append(_issue(
                    "ONSCREEN_CONTENT_UNIT_GAP",
                    page,
                    (
                        "提纲指定的内容单元来自P0级来源事实，没有进入上屏文字；"
                        "P0缺口不接受锚点覆盖说明豁免，必须以短语化方式恢复。"
                        if priority == "P0" else
                        "提纲指定的重要内容单元没有进入上屏文字，页面视觉表达丢失关键业务特征。"
                    ),
                    "以短语化、条目化方式恢复 onscreen_anchors；可以压缩句式，不能删除业务对象或关键动作。",
                    source_ids=source_refs,
                    evidence=(f"unit_id={unit_id}", f"priority={priority}", *missing),
                ))
    return issues


def _visible_module_groups(text: str) -> dict[str, str]:
    """Map each blank-line-delimited visible group to its top-level title."""

    groups: dict[str, str] = {}
    for group in (item for item in str(text).split("\n\n") if item.strip()):
        lines = [line.strip() for line in group.splitlines() if line.strip()]
        if not lines:
            continue
        title = _module_title(lines[0]) or lines[0]
        groups[title] = "\n".join(lines)
    return groups


def _onscreen_module_provenance_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    """Ensure direct audience modules keep their declared fact boundary."""

    if contract.get("source_grounding_mode") != "required":
        return []
    visible_groups = _visible_module_groups(page.onscreen_text)
    issues: list[ScriptQualityIssue] = []
    for module in _dict_items(contract, "onscreen_modules"):
        title = str(module.get("display_title") or "").strip()
        visible_layer = str(module.get("visible_layer") or "body").strip()
        if visible_layer in {"notes", "semantic"}:
            # Deployment and other retained supporting facts remain in the
            # semantic / full-prose layer; they are not audience modules.
            continue
        if visible_layer == "judgment":
            if title in visible_groups:
                issues.append(_issue(
                    "ONSCREEN_LEAD_DUPLICATES_STRUCTURE",
                    page,
                    "承担页面导语职责的来源事实不得同时作为并列上屏模块重复呈现。",
                    "将该事实保留在上屏结论，并由下方结构模块展开其组成或职责。",
                    source_ids=tuple(str(value) for value in module.get("source_refs") or [] if str(value)),
                    evidence=(f"module={title}",),
                ))
            visible = page.onscreen_judgment
        else:
            visible = visible_groups.get(title, "")
        claim = str(module.get("allowed_visible_claim") or "").strip()
        characteristics = tuple(
            str(value).strip()
            for value in module.get("required_characteristics") or []
            if str(value).strip()
        )
        refs = tuple(str(value) for value in module.get("source_refs") or [] if str(value))
        if not visible:
            issues.append(_issue(
                "ONSCREEN_FACT_PROVENANCE_MISSING",
                page,
                "登记的上屏来源模块没有对应的可见模块。",
                "恢复该模块，或调整正式 Outline 中的来源归属。",
                source_ids=refs,
                evidence=(f"module={title}",),
            ))
            continue
        claim_overlap = _source_statement_overlap(claim, visible, size=3)
        feature_hit = any(
            feature in visible
            or _source_statement_overlap(feature, visible, size=3) >= 0.55
            for feature in characteristics
        )
        # A direct module is allowed to shorten a long source paragraph.  The
        # explicit source-specific characteristic proves its fact boundary;
        # a modest phrase overlap guards against an unrelated label carrying
        # the same characteristic by accident.
        if claim_overlap >= 0.05 and feature_hit:
            continue
        mode = str(module.get("derivation_mode") or "")
        code = (
            "ONSCREEN_CROSS_SLOT_FACT_MIXING"
            if mode == "direct"
            else "ONSCREEN_FACT_PROVENANCE_MISSING"
        )
        issues.append(_issue(
            code,
            page,
            "可见模块未保持登记来源事实的对象、状态或表达模型槽位边界。",
            "拆回直接事实，或在 Outline 中登记 synthesis/relation 并明确关系。",
            source_ids=refs,
            evidence=(
                f"module={title}",
                f"claim_overlap={claim_overlap:.3f}",
                f"mode={mode}",
            ),
        ))
    return issues


def _model_slot_coverage_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> tuple[set[str], list[ScriptQualityIssue]]:
    """Verify visible responsibility for an author-selected expression model.

    The Outline audit has already established that mappings cite only current
    page evidence.  Here we verify that a non-implicit slot is represented in
    the audience layer before exempting its units from literal-anchor checks.
    """

    selection = contract.get("expression_model_selection")
    if not isinstance(selection, dict) or selection.get("fit") != "selected":
        return set(), []
    model = load_expression_models().get(str(selection.get("model_id") or ""))
    if model is None:
        return set(), []
    units = [
        item for item in (contract.get("content_units") or [])
        if isinstance(item, dict)
    ]
    visible = "\n".join(
        part for part in (page.onscreen_judgment, page.onscreen_text) if part.strip()
    )
    visible_groups = _visible_module_groups(page.onscreen_text)
    grounded_modules = _dict_items(contract, "onscreen_modules")

    def _grounded_ref_is_visible(ref: str) -> bool:
        """Use the author-declared body module as model-slot evidence.

        Content units may aggregate several source records.  When explicit
        source-grounded modules exist, the visible body module is the more
        precise evidence that a selected model slot reached the audience.
        """

        for module in grounded_modules:
            refs = {str(value) for value in module.get("source_refs") or [] if str(value)}
            if ref not in refs or str(module.get("visible_layer") or "body") != "body":
                continue
            group = visible_groups.get(str(module.get("display_title") or "").strip(), "")
            if not group:
                continue
            claim = str(module.get("allowed_visible_claim") or "")
            characteristics = [
                str(value) for value in module.get("required_characteristics") or [] if str(value)
            ]
            if (
                _source_statement_overlap(claim, group, size=3) >= 0.05
                and any(
                    feature in group
                    or _source_statement_overlap(feature, group, size=3) >= 0.55
                    for feature in characteristics
                )
            ):
                return True
        return False

    covered_refs: set[str] = set()
    issues: list[ScriptQualityIssue] = []
    slot_names = {slot.name for slot in model.slots}
    for mapping in selection.get("source_mapping") or []:
        if not isinstance(mapping, dict) or mapping.get("implicit") is True:
            continue
        slot = str(mapping.get("slot") or "")
        refs = {str(ref) for ref in mapping.get("source_refs") or [] if str(ref)}
        if not refs or slot not in slot_names:
            continue
        missing: set[str] = set()
        for ref in refs:
            if _grounded_ref_is_visible(ref):
                covered_refs.add(ref)
                continue
            matching_units = [
                unit for unit in units
                if ref in {str(value) for value in unit.get("source_refs") or []}
            ]
            if not matching_units:
                missing.add(ref)
                continue
            if any(
                any(
                    anchor and anchor in visible
                    for anchor in unit.get("onscreen_anchors") or []
                )
                or any(
                    _source_statement_overlap(str(anchor), visible, size=3) >= 0.55
                    for anchor in unit.get("onscreen_anchors") or []
                    if str(anchor).strip()
                )
                or _source_statement_overlap(str(unit.get("statement") or ""), visible) >= 0.22
                for unit in matching_units
            ):
                covered_refs.add(ref)
            else:
                missing.add(ref)
        if missing:
            issues.append(_issue(
                "EXPRESSION_MODEL_SLOT_ONSCREEN_MISSING",
                page,
                "作者选定表达模型的槽位没有在可见文字中承担来源表达职责。",
                "恢复该槽位的来源特征或调整作者确认的槽位映射；不要只补审计锚点。",
                source_ids=tuple(sorted(missing)),
                evidence=(f"model={model.model_id}", f"slot={slot}"),
            ))
    return covered_refs, issues
