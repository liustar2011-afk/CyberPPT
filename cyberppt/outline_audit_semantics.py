"""Semantic and source-truth Outline audit rules."""

from __future__ import annotations

from cyberppt.outline_audit_shared import AuditIssue, _core_message, _onscreen_conclusion, _page_id
from cyberppt.semantic_fidelity import (
    STRONG_RELATIONS,
    audit_relation_shape,
    audit_semantic_strength,
    source_text,
    strong_relation_supported,
)


def _semantic_derivation_issues(
    outline: dict[str, object],
    pages: list[dict[str, object]],
    source_truth: dict[str, object] | None,
) -> list[AuditIssue]:
    """Audit the required semantic center and optional visible compression."""

    issues: list[AuditIssue] = []
    records = {
        str(record.get("id") or ""): record
        for record in (source_truth or {}).get("records", [])
        if isinstance(record, dict) and record.get("id")
    }
    require_receipt = (
        outline.get("core_message_derivation_mode") == "required"
        or outline.get("schema") == "cyberppt.outline.v2"
    )
    for page in pages:
        if page.get("page_type") != "content":
            continue
        page_id = _page_id(page)
        main = _core_message(page)
        onscreen = _onscreen_conclusion(page)
        if onscreen and not main:
            issues.append(
                AuditIssue(
                    "ONSCREEN_CONCLUSION_WITHOUT_JUDGMENT",
                    "An on-screen conclusion requires an existing source-derived core message.",
                    (page_id,),
                    "remove_or_derive_judgment",
                )
            )
        if not main:
            continue
        derivation = page.get("core_message_derivation") or page.get("judgment_derivation")
        if require_receipt and not isinstance(derivation, dict):
            issues.append(
                AuditIssue(
                    "CORE_MESSAGE_DERIVATION_MISSING",
                    "Every content page core_message requires a source derivation receipt.",
                    (page_id,),
                    "document_judgment_derivation",
                )
            )
            derivation = {}
        source_refs = [str(ref) for ref in page.get("source_refs", [])]
        receipt_refs = (
            [str(ref) for ref in derivation.get("source_refs", [])]
            if isinstance(derivation, dict)
            else []
        )
        if isinstance(derivation, dict) and require_receipt:
            if not receipt_refs or not set(receipt_refs).issubset(source_refs):
                issues.append(
                    AuditIssue(
                        "JUDGMENT_DERIVATION_INVALID",
                        "Core-message derivation source_refs must be a non-empty subset of page source_refs.",
                        (page_id,),
                        "document_judgment_derivation",
                    )
                )
            if not derivation.get("supporting_statements") or not derivation.get("derivation"):
                issues.append(
                    AuditIssue(
                        "JUDGMENT_DERIVATION_INVALID",
                        "Core-message derivation must state the supporting source text and equal-strength derivation.",
                        (page_id,),
                        "document_judgment_derivation",
                    )
                )
            if derivation.get("introduced_relations") or derivation.get("introduced_modalities"):
                issues.append(
                    AuditIssue(
                        "JUDGMENT_DERIVATION_INTRODUCES_MEANING",
                        "A core message may not introduce relations or modalities absent from the cited material.",
                        (page_id,),
                        "remove_semantic_promotion",
                    )
                )
        evidence_text = source_text(receipt_refs or source_refs, records)
        output_text = "\n".join(part for part in (main, onscreen) if part)
        for fidelity_issue in audit_semantic_strength(output_text, evidence_text):
            issues.append(AuditIssue(fidelity_issue.code, fidelity_issue.message, (page_id,), "remove_semantic_promotion"))
        relations = page.get("content_relations")
        if outline.get("schema") == "cyberppt.outline.v2":
            for relation_issue in audit_relation_shape(relations):
                issues.append(AuditIssue(relation_issue.code, relation_issue.message, (page_id,), "complete_content_relations"))
        if isinstance(relations, list):
            for relation in relations:
                if not isinstance(relation, dict):
                    continue
                relation_name = str(relation.get("relation") or "")
                relation_refs = [str(ref) for ref in relation.get("source_refs", [])]
                relation_evidence = source_text(relation_refs, records)
                if relation_name in STRONG_RELATIONS and not strong_relation_supported(relation_name, relation_evidence):
                    issues.append(AuditIssue("RELATION_STRENGTH_UPGRADED", f"Strong relation {relation_name} is not explicitly supported by its cited sources.", (page_id,), "remove_semantic_promotion"))
    return issues
def _document_semantic_issues(
    outline: dict[str, object], source_truth: dict[str, object] | None
) -> list[AuditIssue]:
    """Keep the deck thesis anchored to the source's document identity."""

    if not source_truth or source_truth.get("document_semantics_mode") != "required":
        return []
    expected = source_truth.get("document_semantics")
    actual = outline.get("document_semantics")
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return [
            AuditIssue(
                "OUTLINE_DOCUMENT_SEMANTICS_MISSING",
                "The outline must inherit the Source Truth document role, report subject, primary thesis, and decision boundary.",
                retry_strategy="anchor_outline_to_document_semantics",
            )
        ]
    fields = ("document_role", "subject_of_report", "primary_thesis", "decision_boundary")
    fields += tuple(
        field
        for field in ("author_purpose", "argument_method", "supporting_basis")
        if field in expected
    )
    if any(str(actual.get(field) or "").strip() != str(expected.get(field) or "").strip() for field in fields):
        return [
            AuditIssue(
                "OUTLINE_DOCUMENT_SEMANTICS_DRIFTED",
                "The outline changes the document role, report subject, primary thesis, or decision boundary established by Source Truth.",
                retry_strategy="anchor_outline_to_document_semantics",
            )
        ]
    if str(outline.get("narrative_thesis") or "").strip() != str(expected.get("primary_thesis") or "").strip():
        return [
            AuditIssue(
                "NARRATIVE_THESIS_DRIFTED",
                "The deck-level narrative thesis must equal the source-grounded primary thesis; document stage or research activity may not replace the subject of report.",
                retry_strategy="anchor_outline_to_document_semantics",
            )
        ]
    return []


def _page_content_unit_contract_issues(
    outline: dict[str, object],
    pages: list[dict[str, object]],
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    # Boundary evidence is mandatory in prose/traceability, but it is opt-in
    # on screen unless the approved page proposition is itself boundary-led.
    structural_duties = {"driver", "consequence", "gap", "response"}
    required = (
        outline.get("semantic_argument_model_mode") == "required"
        or outline.get("page_content_unit_coverage_mode") == "required"
    )
    if not required:
        return issues
    if outline.get("page_content_unit_coverage_mode") != "required":
        issues.append(AuditIssue(
            "PAGE_CONTENT_UNIT_COVERAGE_MODE_REQUIRED",
            "正式语义提纲默认必须启用 page_content_unit_coverage_mode=required，防止页面在完整稿和上屏压缩中静默丢失重要内容。",
            retry_strategy="rebuild_page_content_units",
        ))
    for page in pages:
        if page.get("page_type") != "content":
            continue
        page_id = str(page.get("page_id") or "")
        units = [
            item for item in (page.get("content_units") or [])
            if isinstance(item, dict)
        ]
        if not units:
            issues.append(AuditIssue(
                "PAGE_CONTENT_UNITS_MISSING",
                "内容页必须把拟保留信息拆成可审计的原子内容单元。",
                (page_id,),
                "rebuild_page_content_units",
            ))
            continue
        onscreen_count = 0
        for unit in units:
            unit_id = str(unit.get("unit_id") or "")
            statement = str(unit.get("statement") or "").strip()
            source_refs = [str(item) for item in unit.get("source_refs") or [] if str(item)]
            importance = str(unit.get("importance") or "")
            full_required = unit.get("full_prose_required")
            onscreen_required = unit.get("onscreen_required")
            coverage_anchors = [str(item).strip() for item in unit.get("coverage_anchors") or [] if str(item).strip()]
            onscreen_anchors = [str(item).strip() for item in unit.get("onscreen_anchors") or [] if str(item).strip()]
            argument_duties = [str(item).strip() for item in unit.get("argument_duties") or [] if str(item).strip()]
            if not unit_id or not statement or not source_refs:
                issues.append(AuditIssue(
                    "PAGE_CONTENT_UNIT_IDENTITY_MISSING",
                    "每个内容单元必须声明 unit_id、statement 和 source_refs。",
                    (page_id,),
                    "rebuild_page_content_units",
                ))
            if importance not in {"primary", "supporting", "detail", "boundary"}:
                issues.append(AuditIssue(
                    "PAGE_CONTENT_UNIT_IMPORTANCE_MISSING",
                    "每个内容单元必须声明 primary、supporting、detail 或 boundary 重要等级。",
                    (page_id,),
                    "classify_page_content_units",
                ))
            if not isinstance(full_required, bool):
                issues.append(AuditIssue(
                    "PAGE_CONTENT_UNIT_PROSE_DUTY_MISSING",
                    "每个内容单元必须明确 full_prose_required。",
                    (page_id,),
                    "assign_page_content_duties",
                ))
            elif full_required and len(coverage_anchors) < 2:
                issues.append(AuditIssue(
                    "PAGE_CONTENT_UNIT_ANCHORS_INSUFFICIENT",
                    "必须进入完整文字稿的内容单元至少需要两个来源特征锚点，不能只靠泛化关键词证明覆盖。",
                    (page_id,),
                    "restore_source_specific_anchors",
                ))
            if not isinstance(onscreen_required, bool):
                issues.append(AuditIssue(
                    "PAGE_CONTENT_UNIT_ONSCREEN_DUTY_MISSING",
                    "每个内容单元必须明确 onscreen_required。",
                    (page_id,),
                    "assign_page_content_duties",
                ))
            elif onscreen_required:
                onscreen_count += 1
                if not onscreen_anchors:
                    issues.append(AuditIssue(
                        "PAGE_CONTENT_UNIT_ONSCREEN_ANCHORS_MISSING",
                        "必须上屏的内容单元至少需要一个业务特征锚点。",
                        (page_id,),
                        "restore_onscreen_business_anchor",
                    ))
            if structural_duties.intersection(argument_duties) and onscreen_required is not True:
                issues.append(AuditIssue(
                    "STRUCTURAL_ARGUMENT_DUTY_HIDDEN",
                    "承担前提、驱动、结果、缺口或回应职责的内容单元不得只留在讲稿或追溯层；否则页面论证链会从中间开始。",
                    (page_id,),
                    "restore_structural_argument_chain",
                ))
        if onscreen_count == 0:
            issues.append(AuditIssue(
                "PAGE_ONSCREEN_CONTENT_DUTY_MISSING",
                "每个内容页至少有一个 primary 或关键 supporting 内容单元承担上屏责任。",
                (page_id,),
                "assign_onscreen_content_duty",
            ))
    return issues
def _structural_argument_duty_issues(
    pages: list[dict[str, object]],
    source_truth: dict[str, object] | None,
) -> list[AuditIssue]:
    """Keep indispensable argument-chain records out of trace-only storage."""
    if source_truth is None:
        return []
    structural_duties = {"driver", "consequence", "gap", "response"}
    records = {
        str(item.get("id") or ""): item
        for item in source_truth.get("records") or []
        if isinstance(item, dict) and item.get("id")
    }
    issues: list[AuditIssue] = []
    for page in pages:
        if page.get("page_type") != "content":
            continue
        page_id = str(page.get("page_id") or "")
        detail_refs = {str(item) for item in page.get("detail_refs") or []}
        units = [item for item in page.get("content_units") or [] if isinstance(item, dict)]
        for source_id in page.get("source_refs") or []:
            source_id = str(source_id)
            duty = str(records.get(source_id, {}).get("argument_duty") or "")
            if duty not in structural_duties:
                continue
            carriers = [
                unit for unit in units
                if source_id in {str(item) for item in unit.get("source_refs") or []}
            ]
            visible = any(unit.get("onscreen_required") is True for unit in carriers)
            if source_id in detail_refs or not visible:
                issues.append(AuditIssue(
                    "STRUCTURAL_ARGUMENT_RECORD_HIDDEN",
                    f"Source Truth 记录 {source_id} 承担 {duty} 论证职责，不得只放入 detail_refs、讲稿或追溯层。",
                    (page_id,),
                    "restore_structural_argument_chain",
                ))
    return issues
