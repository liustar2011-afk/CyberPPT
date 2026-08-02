"""Semantic roles and deterministic argument-flow audits."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re


CLAIM_ROLES = frozenset(
    {
        "fact",
        "change",
        "problem",
        "judgment",
        "recommendation",
        "boundary",
        "unresolved",
    }
)
PAGE_ARGUMENT_ROLES = frozenset(
    {
        "foundation",
        "change",
        "gap",
        "necessity",
        "positioning",
        "solution",
        "scope",
        "implementation",
        "assurance",
        "decision",
    }
)
DEFAULT_ALLOWED_CLAIMS = {
    "foundation": frozenset({"fact"}),
    "change": frozenset({"fact", "change", "judgment"}),
    "gap": frozenset({"fact", "change", "problem", "judgment"}),
    "necessity": frozenset({"fact", "change", "problem", "judgment", "boundary"}),
    "positioning": frozenset({"fact", "judgment", "recommendation", "boundary"}),
    "solution": frozenset({"fact", "judgment", "recommendation", "boundary"}),
    "scope": frozenset(
        {"fact", "judgment", "recommendation", "boundary", "unresolved"}
    ),
    "implementation": frozenset({"fact", "recommendation", "boundary"}),
    "assurance": frozenset({"fact", "judgment", "recommendation", "boundary"}),
    "decision": frozenset({"fact", "judgment", "boundary", "unresolved"}),
}
PAGE_CONTRIBUTION_FIELDS = (
    "page_job",
    "proof_points",
    "new_value_vs_previous",
    "reserved_for_later",
)
SEMANTIC_CONTRIBUTION_FIELDS = (
    "page_mission",
    "core_message",
    "content_units",
    "content_relations",
    "new_value_vs_previous",
    "reserved_for_later",
)
EVIDENCE_TYPE_TO_CLAIM_ROLE = {
    "F": "fact",
    "J": "judgment",
    "R": "recommendation",
    "B": "boundary",
    "U": "unresolved",
}
PRIMARY_PROOF_DIRECTION_LIMIT = 3
BOUNDARY_PRIMARY_ARGUMENT_ROLES = frozenset(
    {"positioning", "scope", "assurance", "decision"}
)


@dataclass(frozen=True)
class ArgumentFlowIssue:
    code: str
    message: str
    pages: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    failed_edges: tuple[tuple[str, str], ...] = ()
    retry_strategy: str = "rebuild_argument_sequence"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_page_role_fields(
    outline: dict[str, object],
) -> list[ArgumentFlowIssue]:
    if outline.get("argument_contract_mode", "legacy") != "strict":
        return []
    if outline.get("schema") == "cyberppt.outline.v2":
        return validate_source_relation_fields(outline)
    raw_pages = outline.get("pages")
    pages = raw_pages if isinstance(raw_pages, list) else []
    issues: list[ArgumentFlowIssue] = []
    required = (
        "argument_role",
        "allowed_claim_roles",
        "prerequisite_pages",
        "forbidden_claim_roles",
    )
    for raw_page in pages:
        if not isinstance(raw_page, dict) or raw_page.get("page_type") != "content":
            continue
        page_id = str(raw_page.get("page_id") or "")
        if any(field not in raw_page for field in required):
            issues.append(
                ArgumentFlowIssue(
                    "ARGUMENT_FIELDS_MISSING",
                    "Strict content pages must declare their argument role and claim constraints.",
                    (page_id,) if page_id else (),
                    retry_strategy="complete_argument_contract",
                )
            )
        missing_contribution = [
            field
            for field in PAGE_CONTRIBUTION_FIELDS
            if field not in raw_page
            or raw_page.get(field) is None
            or raw_page.get(field) == ""
            or raw_page.get(field) == []
        ]
        if missing_contribution:
            issues.append(
                ArgumentFlowIssue(
                    "PAGE_CONTRIBUTION_FIELDS_MISSING",
                    "Strict content pages must declare page_job, proof_points, "
                    "new_value_vs_previous, and reserved_for_later.",
                    (page_id,) if page_id else (),
                    retry_strategy="complete_page_contribution_contract",
                )
            )
        proof_points = raw_page.get("proof_points")
        page_sources = set(_string_list(raw_page, "source_refs"))
        boundary_sources = set(_string_list(raw_page, "boundary_refs"))
        proof_sources: set[str] = set()
        if isinstance(proof_points, list):
            invalid = False
            for point in proof_points:
                if not isinstance(point, dict) or not str(point.get("claim") or "").strip():
                    invalid = True
                    break
                refs = _string_list(point, "source_refs")
                proof_sources.update(refs)
                consumption = str(point.get("consumption") or "")
                if (
                    not refs
                    or not set(refs).issubset(page_sources)
                    or consumption not in {"overview", "primary", "supporting"}
                ):
                    invalid = True
                    break
            if invalid:
                issues.append(
                    ArgumentFlowIssue(
                        "PROOF_POINT_INVALID",
                        "Each proof point must contain a claim and cite only Source IDs "
                        "assigned to the page.",
                        (page_id,) if page_id else (),
                        retry_strategy="reconcile_page_proof_points",
                    )
                )
        if (
            not boundary_sources.issubset(page_sources)
            or boundary_sources & proof_sources
        ):
            issues.append(
                ArgumentFlowIssue(
                    "BOUNDARY_REFS_INVALID",
                    "boundary_refs must cite page sources and must not overlap proof_points.",
                    (page_id,) if page_id else (),
                    tuple(sorted(boundary_sources & proof_sources)),
                    retry_strategy="separate_page_proof_and_boundary",
                )
            )
        role = raw_page.get("argument_role")
        if role is not None and role not in PAGE_ARGUMENT_ROLES:
            issues.append(
                ArgumentFlowIssue(
                    "ARGUMENT_ROLE_INVALID",
                    "Content page argument_role must use the repository vocabulary.",
                    (page_id,) if page_id else (),
                    retry_strategy="complete_argument_contract",
                )
            )
    return issues


def validate_source_relation_fields(
    outline: dict[str, object],
) -> list[ArgumentFlowIssue]:
    """Validate v2 content contracts without imposing page or claim taxonomies."""

    issues: list[ArgumentFlowIssue] = []
    for page in _dict_items(outline, "pages"):
        if page.get("page_type") != "content":
            continue
        page_id = str(page.get("page_id") or "")
        missing = [field for field in SEMANTIC_CONTRIBUTION_FIELDS if not page.get(field)]
        if missing:
            issues.append(
                ArgumentFlowIssue(
                    "SEMANTIC_CONTRIBUTION_FIELDS_MISSING",
                    "V2 content pages must declare page_mission, core_message, content_units, content_relations, new_value_vs_previous, and reserved_for_later.",
                    (page_id,) if page_id else (),
                    retry_strategy="complete_source_relation_contract",
                )
            )
        page_sources = set(_string_list(page, "source_refs"))
        units = page.get("content_units")
        unit_sources: set[str] = set()
        if isinstance(units, list):
            for unit in units:
                refs = _string_list(unit, "source_refs") if isinstance(unit, dict) else []
                unit_sources.update(refs)
                if (
                    not isinstance(unit, dict)
                    or not str(unit.get("statement") or "").strip()
                    or not refs
                    or not set(refs).issubset(page_sources)
                    or str(unit.get("role") or "") not in {"primary", "supporting", "boundary"}
                ):
                    issues.append(
                        ArgumentFlowIssue(
                            "CONTENT_UNIT_INVALID",
                            "Each content unit must state source-supported content, cite only page source_refs, and use primary, supporting, or boundary role.",
                            (page_id,) if page_id else (),
                            retry_strategy="reconcile_content_units",
                        )
                    )
                    break
        detail_sources = set(_string_list(page, "detail_refs"))
        if (
            not detail_sources.issubset(page_sources)
            or bool(detail_sources & unit_sources)
        ):
            issues.append(
                ArgumentFlowIssue(
                    "DETAIL_REFS_INVALID",
                    "detail_refs must be a subset of page source_refs and must not "
                    "also appear as standalone content-unit evidence.",
                    (page_id,) if page_id else (),
                    tuple(sorted((detail_sources - page_sources) | (detail_sources & unit_sources))),
                    retry_strategy="separate_retained_detail_from_page_structure",
                )
            )
        unclassified = page_sources - unit_sources - detail_sources
        if unclassified:
            issues.append(
                ArgumentFlowIssue(
                    "PAGE_EVIDENCE_CLASSIFICATION_INCOMPLETE",
                    "Every page source must be classified as content-unit evidence or "
                    "retained detail; full traceability does not require equal visual weight.",
                    (page_id,) if page_id else (),
                    tuple(sorted(unclassified)),
                    retry_strategy="classify_page_evidence_weight",
                )
            )
        relations = page.get("content_relations")
        if isinstance(relations, list):
            for relation in relations:
                refs = _string_list(relation, "source_refs") if isinstance(relation, dict) else []
                if not isinstance(relation, dict) or not refs or not set(refs).issubset(page_sources):
                    issues.append(
                        ArgumentFlowIssue(
                            "CONTENT_RELATION_REFS_INVALID",
                            "Each content relation must cite a non-empty subset of the page source_refs.",
                            (page_id,) if page_id else (),
                            tuple(sorted(set(refs) - page_sources)),
                            retry_strategy="reconcile_content_relations",
                        )
                    )
                    break
        boundary_sources = set(_string_list(page, "boundary_refs"))
        if not boundary_sources.issubset(page_sources):
            issues.append(
                ArgumentFlowIssue(
                    "BOUNDARY_REFS_INVALID",
                    "boundary_refs must be a subset of page source_refs.",
                    (page_id,) if page_id else (),
                    tuple(sorted(boundary_sources - page_sources)),
                    retry_strategy="reconcile_content_units",
                )
            )
    return issues


def _normalized_similarity(left: object, right: object) -> float:
    def tokens(value: object) -> set[str]:
        compact = re.sub(r"[^\w\u4e00-\u9fff]+", "", str(value or "")).lower()
        if len(compact) < 3:
            return {compact} if compact else set()
        return {compact[index : index + 3] for index in range(len(compact) - 2)}

    left_tokens = tokens(left)
    right_tokens = tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _theme_similarity(page: dict[str, object], claim: object) -> float:
    theme_fields = (
        page.get("page_job"),
        page.get("business_question"),
        page.get("main_message"),
    )
    return max(
        (
            _topic_similarity(claim, field)
            for field in theme_fields
            if _text_value(field)
        ),
        default=0.0,
    )


def _text_value(value: object) -> str:
    return str(value or "").strip()


def _topic_similarity(left: object, right: object) -> float:
    def bigrams(value: object) -> set[str]:
        compact = re.sub(r"[^\w\u4e00-\u9fff]+", "", str(value or "")).lower()
        if len(compact) < 2:
            return {compact} if compact else set()
        return {compact[index : index + 2] for index in range(len(compact) - 1)}

    left_tokens = bigrams(left)
    right_tokens = bigrams(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _dict_items(payload: dict[str, object], field: str) -> list[dict[str, object]]:
    raw = payload.get(field)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _string_list(item: dict[str, object], field: str) -> list[str]:
    raw = item.get(field)
    if not isinstance(raw, list):
        return []
    return [str(value) for value in raw if str(value)]


def _dependency_cycle(
    dependencies: dict[str, list[str]],
) -> tuple[tuple[str, str], ...]:
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def visit(page_id: str) -> tuple[tuple[str, str], ...]:
        if page_id in visited:
            return ()
        if page_id in visiting:
            start = path.index(page_id)
            cycle = path[start:] + [page_id]
            return tuple(zip(cycle, cycle[1:]))
        visiting.add(page_id)
        path.append(page_id)
        for prerequisite in dependencies.get(page_id, []):
            cycle = visit(prerequisite)
            if cycle:
                return cycle
        path.pop()
        visiting.remove(page_id)
        visited.add(page_id)
        return ()

    for candidate in sorted(dependencies):
        cycle = visit(candidate)
        if cycle:
            return cycle
    return ()


def audit_argument_flow(
    outline: dict[str, object],
    source_truth: dict[str, object] | None,
) -> list[ArgumentFlowIssue]:
    if outline.get("argument_contract_mode", "legacy") != "strict":
        return []
    pages = _dict_items(outline, "pages")
    content_pages = [page for page in pages if page.get("page_type") == "content"]
    page_index = {
        str(page.get("page_id") or ""): page
        for page in content_pages
        if str(page.get("page_id") or "")
    }
    records = _dict_items(source_truth or {}, "records")
    record_index = {
        str(record.get("id") or ""): record
        for record in records
        if str(record.get("id") or "")
    }
    issues = validate_page_role_fields(outline)
    dependencies: dict[str, list[str]] = {}
    source_relation_mode = outline.get("schema") == "cyberppt.outline.v2"

    for page_id, page in page_index.items():
        prerequisites = _string_list(page, "prerequisite_pages")
        dependencies[page_id] = prerequisites
        sequence = int(page.get("sequence") or 0)
        for prerequisite in prerequisites:
            prior = page_index.get(prerequisite)
            if prior is None:
                issues.append(
                    ArgumentFlowIssue(
                        "PREREQUISITE_PAGE_MISSING",
                        "Page prerequisites must resolve to another content page.",
                        (page_id,),
                        failed_edges=((prerequisite, page_id),),
                    )
                )
                continue
            if int(prior.get("sequence") or 0) >= sequence:
                issues.append(
                    ArgumentFlowIssue(
                        "PREREQUISITE_PAGE_NOT_EARLIER",
                        "A prerequisite page must appear before its dependent page.",
                        (prerequisite, page_id),
                        failed_edges=((prerequisite, page_id),),
                    )
                )

        argument_role = str(page.get("argument_role") or "")
        explicit_allowed = set(_string_list(page, "allowed_claim_roles"))
        allowed = explicit_allowed or set(DEFAULT_ALLOWED_CLAIMS.get(argument_role, ()))
        forbidden = set(_string_list(page, "forbidden_claim_roles"))
        source_refs = _string_list(page, "source_refs")
        proof_points = [
            point
            for point in page.get("proof_points", [])
            if isinstance(point, dict)
        ]
        primary_points = [
            point for point in proof_points if point.get("consumption") == "primary"
        ]
        if source_relation_mode:
            boundary_focus = page.get("boundary_focus") is True
            boundary_focus_reason = str(page.get("boundary_focus_reason") or "").strip()
            if boundary_focus and not boundary_focus_reason:
                issues.append(
                    ArgumentFlowIssue(
                        "BOUNDARY_FOCUS_JUSTIFICATION_MISSING",
                        "A v2 page may make a boundary its semantic center only when "
                        "boundary_focus_reason explains why scope, admission, assurance, "
                        "or a pending decision is the page's actual business subject.",
                        (page_id,),
                        retry_strategy="justify_or_demote_boundary_focus",
                    )
                )

            boundary_sources = {
                source_id
                for source_id in source_refs
                if str(
                    record_index.get(source_id, {}).get("claim_role")
                    or EVIDENCE_TYPE_TO_CLAIM_ROLE.get(
                        str(record_index.get(source_id, {}).get("type") or ""),
                        "",
                    )
                )
                in {"boundary", "unresolved"}
            }
            raw_units = page.get("content_units")
            units = [unit for unit in raw_units if isinstance(unit, dict)] if isinstance(raw_units, list) else []
            primary_units = [unit for unit in units if unit.get("role") == "primary"]
            supporting_units = [unit for unit in units if unit.get("role") == "supporting"]
            boundary_units = [unit for unit in units if unit.get("role") == "boundary"]
            if (
                (not boundary_focus and len(primary_units) != 1)
                or len(supporting_units) > 3
                or len(boundary_units) > 1
                or len(units) > 5
            ):
                issues.append(
                    ArgumentFlowIssue(
                        "CONTENT_UNIT_HIERARCHY_FLAT",
                        "An ordinary page needs exactly one primary unit, at most three "
                        "supporting modules, and at most one grouped boundary unit. "
                        "Retain lower-weight evidence in detail_refs instead of equal modules.",
                        (page_id,),
                        retry_strategy="compress_page_semantic_hierarchy",
                    )
                )
            if len(source_refs) >= 6 and len(units) >= 6 and len(units) / len(source_refs) >= 0.75:
                issues.append(
                    ArgumentFlowIssue(
                        "SOURCE_RECORDS_MIRRORED_AS_CONTENT_UNITS",
                        "Source records are traceability atoms, not slide modules. Group "
                        "related P0/P1 evidence and retain P2 details without creating one "
                        "content unit per record.",
                        (page_id,),
                        tuple(source_refs),
                        retry_strategy="group_evidence_into_page_modules",
                    )
                )

            detail_sources = set(_string_list(page, "detail_refs"))
            p0_details = {
                source_id for source_id in detail_sources
                if record_index.get(source_id, {}).get("priority") == "P0"
            }
            p2_structural = {
                source_id
                for unit in units
                for source_id in _string_list(unit, "source_refs")
                if record_index.get(source_id, {}).get("priority") == "P2"
            }
            if p0_details:
                issues.append(
                    ArgumentFlowIssue(
                        "P0_DEMOTED_TO_DETAIL",
                        "Page-forming P0 evidence cannot be retained only as background detail.",
                        (page_id,),
                        tuple(sorted(p0_details)),
                        retry_strategy="restore_p0_page_structure",
                    )
                )
            if p2_structural:
                issues.append(
                    ArgumentFlowIssue(
                        "P2_USED_AS_PAGE_STRUCTURE",
                        "P2 evidence is retained detail and may inform prose, notes, or "
                        "appendices, but it must not create a peer content module.",
                        (page_id,),
                        tuple(sorted(p2_structural)),
                        retry_strategy="demote_p2_to_detail_refs",
                    )
                )
            for unit in page.get("content_units", []):
                if not isinstance(unit, dict):
                    continue
                unit_boundary_sources = boundary_sources.intersection(
                    _string_list(unit, "source_refs")
                )
                unit_role = str(unit.get("role") or "")
                if unit_boundary_sources and unit_role == "primary":
                    issues.append(
                        ArgumentFlowIssue(
                            "BOUNDARY_USED_AS_PRIMARY_PROOF",
                            "Boundary or unresolved evidence cannot be a primary content "
                            "unit in outline.v2. Keep it as a boundary unit; when the whole "
                            "page is genuinely about scope, admission, assurance, or a "
                            "pending decision, explicitly declare boundary_focus.",
                            (page_id,),
                            tuple(sorted(unit_boundary_sources)),
                            retry_strategy="refocus_page_evidence",
                        )
                    )
                elif unit_boundary_sources and unit_role != "boundary":
                    issues.append(
                        ArgumentFlowIssue(
                            "BOUNDARY_CONTENT_UNIT_ROLE_INVALID",
                            "Boundary or unresolved Source Truth records must use the "
                            "boundary content-unit role, not a substantive supporting role.",
                            (page_id,),
                            tuple(sorted(unit_boundary_sources)),
                            retry_strategy="demote_boundary_content_unit",
                        )
                    )

            derivation = page.get("core_message_derivation") or page.get(
                "judgment_derivation"
            )
            derivation_refs = (
                set(_string_list(derivation, "source_refs"))
                if isinstance(derivation, dict)
                else set()
            )
            p2_core_sources = {
                source_id for source_id in derivation_refs
                if record_index.get(source_id, {}).get("priority") == "P2"
            }
            if p2_core_sources:
                issues.append(
                    ArgumentFlowIssue(
                        "P2_USED_AS_CORE_MESSAGE",
                        "Retained-detail P2 evidence cannot derive the page core_message.",
                        (page_id,),
                        tuple(sorted(p2_core_sources)),
                        retry_strategy="derive_core_from_p0_p1",
                    )
                )
            core_boundary_sources = boundary_sources.intersection(derivation_refs)
            if core_boundary_sources and not boundary_focus:
                issues.append(
                    ArgumentFlowIssue(
                        "BOUNDARY_USED_AS_CORE_MESSAGE",
                        "Boundary or unresolved evidence may constrain a normal page but "
                        "may not derive its core_message. Move it to boundary_refs and a "
                        "boundary content unit, or explicitly declare a justified "
                        "boundary_focus page.",
                        (page_id,),
                        tuple(sorted(core_boundary_sources)),
                        retry_strategy="demote_boundary_from_core_message",
                    )
                )
        if not source_relation_mode and len(primary_points) > PRIMARY_PROOF_DIRECTION_LIMIT:
            issues.append(
                ArgumentFlowIssue(
                    "PRIMARY_PROOF_DIRECTIONS_EXCESSIVE",
                    "A single-theme page may contain at most three independent primary "
                    "proof directions; consolidate records that establish one implication.",
                    (page_id,),
                    tuple(
                        dict.fromkeys(
                            source_id
                            for point in primary_points
                            for source_id in _string_list(point, "source_refs")
                        )
                    ),
                    retry_strategy="refocus_page_evidence",
                )
            )
        for point in ([] if source_relation_mode else primary_points):
            point_sources = _string_list(point, "source_refs")
            boundary_primary_sources = [
                source_id
                for source_id in point_sources
                if str(
                    record_index.get(source_id, {}).get("claim_role")
                    or EVIDENCE_TYPE_TO_CLAIM_ROLE.get(
                        str(record_index.get(source_id, {}).get("type") or ""),
                        "",
                    )
                )
                in {"boundary", "unresolved"}
            ]
            if (
                boundary_primary_sources
                and argument_role not in BOUNDARY_PRIMARY_ARGUMENT_ROLES
            ):
                issues.append(
                    ArgumentFlowIssue(
                        "BOUNDARY_USED_AS_PRIMARY_PROOF",
                        "Boundary or unresolved evidence cannot be primary proof unless "
                        "the page itself defines positioning, scope, assurance conditions, "
                        "or a decision.",
                        (page_id,),
                        tuple(boundary_primary_sources),
                        retry_strategy="refocus_page_evidence",
                    )
                )
            claim = point.get("claim")
            if claim and _theme_similarity(page, claim) == 0.0:
                issues.append(
                    ArgumentFlowIssue(
                        "PROOF_POINT_OFF_TOPIC",
                        "A primary proof claim must share a concrete topic with page_job, "
                        "business_question, or main_message.",
                        (page_id,),
                        tuple(point_sources),
                        retry_strategy="refocus_page_evidence",
                    )
                )
        if not source_refs:
            issues.append(
                ArgumentFlowIssue(
                    "PAGE_EVIDENCE_MISSING",
                    "Strict content pages must cite at least one Source Truth record.",
                    (page_id,),
                    retry_strategy="reconcile_page_evidence_mapping",
                )
            )
        for source_id in source_refs:
            record = record_index.get(source_id)
            if record is None:
                issues.append(
                    ArgumentFlowIssue(
                        "PAGE_SOURCE_MISSING",
                        "Every outline source reference must resolve in Source Truth.",
                        (page_id,),
                        (source_id,),
                        retry_strategy="reconcile_page_evidence_mapping",
                    )
                )
                continue
            claim_role = str(
                record.get("claim_role")
                or EVIDENCE_TYPE_TO_CLAIM_ROLE.get(str(record.get("type") or ""), "")
            )
            if not source_relation_mode and (claim_role not in allowed or claim_role in forbidden):
                issues.append(
                    ArgumentFlowIssue(
                        "CLAIM_ROLE_EXCEEDS_PAGE_ROLE",
                        "A cited claim exceeds the page argument role.",
                        (page_id,),
                        (source_id,),
                        retry_strategy="reassign_claim_to_later_page",
                    )
                )
                if (
                    claim_role == "recommendation"
                    and argument_role in {"foundation", "change", "gap"}
                ):
                    issues.append(
                        ArgumentFlowIssue(
                            "PREMATURE_SOLUTION_CLAIM",
                            "A recommendation appears before the argument establishes its need.",
                            (page_id,),
                            (source_id,),
                            retry_strategy="reassign_claim_to_later_page",
                        )
                    )

            if (
                not source_relation_mode
                and
                str(page.get("main_claim_status") or "") == "confirmed"
                and claim_role in {"boundary", "unresolved"}
            ):
                issues.append(
                    ArgumentFlowIssue(
                        "SOURCE_STATUS_UPGRADED",
                        "Conditional or unresolved evidence cannot support a confirmed claim.",
                        (page_id,),
                        (source_id,),
                        retry_strategy="restore_source_status_and_boundary",
                    )
                )

    actual_pages_by_source: dict[str, set[str]] = {}
    primary_pages_by_source: dict[str, set[str]] = {}
    for page_id, page in page_index.items():
        for source_id in _string_list(page, "source_refs"):
            actual_pages_by_source.setdefault(source_id, set()).add(page_id)
        point_field = "content_units" if source_relation_mode else "proof_points"
        for point in page.get(point_field, []):
            if isinstance(point, dict) and (
                point.get("role") == "primary" or point.get("consumption") == "primary"
            ):
                for source_id in _string_list(point, "source_refs"):
                    primary_pages_by_source.setdefault(source_id, set()).add(page_id)
    for source_id, owners in primary_pages_by_source.items():
        if source_relation_mode:
            continue
        if len(owners) > 1:
            issues.append(
                ArgumentFlowIssue(
                    "EVIDENCE_PRIMARY_CONSUMPTION_CONFLICT",
                    "One Source record may have only one primary consumption page.",
                    tuple(sorted(owners)),
                    (source_id,),
                    retry_strategy="assign_single_primary_evidence_owner",
                )
            )
    for source_id, record in record_index.items():
        declared = set(_string_list(record, "page_refs"))
        actual = actual_pages_by_source.get(source_id, set())
        if declared != actual:
            issues.append(
                ArgumentFlowIssue(
                    "PAGE_EVIDENCE_MAPPING_MISMATCH",
                    "Source Truth page mappings must match Outline citations in both directions.",
                    tuple(sorted(declared | actual)),
                    (source_id,),
                    retry_strategy="reconcile_page_evidence_mapping",
                )
            )

    def prerequisite_closure(page_id: str) -> set[str]:
        closure: set[str] = set()
        pending = list(dependencies.get(page_id, []))
        while pending:
            candidate = pending.pop()
            if candidate in closure:
                continue
            closure.add(candidate)
            pending.extend(dependencies.get(candidate, []))
        return closure

    for page_id, page in page_index.items():
        covered_pages = prerequisite_closure(page_id) | {page_id}
        covered_sources = {
            source_id
            for covered_page in covered_pages
            for source_id in _string_list(page_index.get(covered_page, {}), "source_refs")
        }
        for source_id in _string_list(page, "source_refs"):
            record = record_index.get(source_id)
            if record is None:
                continue
            missing = [
                dependency
                for dependency in _string_list(record, "depends_on")
                if dependency not in covered_sources
            ]
            if missing:
                issues.append(
                    ArgumentFlowIssue(
                        "EVIDENCE_PREREQUISITE_UNCOVERED",
                        "Claim dependencies must be covered by the page or its prerequisites.",
                        (page_id,),
                        tuple([source_id, *missing]),
                        retry_strategy="rebuild_argument_sequence",
                    )
                )

    cycle = _dependency_cycle(dependencies)
    if cycle:
        cycle_pages = tuple(dict.fromkeys(node for edge in cycle for node in edge))
        issues.append(
            ArgumentFlowIssue(
                "ARGUMENT_DEPENDENCY_CYCLE",
                "Page argument prerequisites must form an acyclic graph.",
                cycle_pages,
                failed_edges=cycle,
            )
        )
    ordered_pages = sorted(
        page_index.values(),
        key=lambda item: int(item.get("sequence") or 0),
    )
    for previous_index, previous in enumerate(ordered_pages):
        for current in ordered_pages[previous_index + 1 :]:
            previous_sources = set(_string_list(previous, "source_refs"))
            current_sources = set(_string_list(current, "source_refs"))
            shared_sources = previous_sources & current_sources
            source_overlap = (
                len(shared_sources) / min(len(previous_sources), len(current_sources))
                if previous_sources and current_sources
                else 0.0
            )
            job_similarity = _normalized_similarity(
                previous.get("page_mission") or previous.get("page_job"),
                current.get("page_mission") or current.get("page_job"),
            )
            value_similarity = _normalized_similarity(
                previous.get("new_value_vs_previous"),
                current.get("new_value_vs_previous"),
            )
            if source_overlap < 0.6 or max(job_similarity, value_similarity) < 0.75:
                continue
            issues.append(
                ArgumentFlowIssue(
                    "PAGE_CONTRIBUTION_OVERLAP",
                    "Pages reuse substantially the same evidence for the same page job or new value; "
                    "merge them or redefine their unique contribution.",
                    (
                        str(previous.get("page_id") or ""),
                        str(current.get("page_id") or ""),
                    ),
                    tuple(sorted(shared_sources)),
                    retry_strategy="separate_page_contributions",
                )
            )
    return sorted(issues, key=lambda issue: ((issue.pages or ("",))[0], issue.code))


def argument_graph_summary(
    outline: dict[str, object],
    source_truth: dict[str, object] | None = None,
) -> dict[str, object]:
    pages = _dict_items(outline, "pages")
    edges = sorted(
        [
            {"from": prerequisite, "to": str(page.get("page_id") or "")}
            for page in pages
            if page.get("page_type") == "content"
            for prerequisite in _string_list(page, "prerequisite_pages")
        ],
        key=lambda edge: (edge["from"], edge["to"]),
    )
    return {
        "nodes": [
            {
                "page_id": str(page.get("page_id") or ""),
                "argument_role": str(page.get("argument_role") or ""),
                "core_message": str(page.get("core_message") or page.get("main_message") or ""),
                "content_relation_count": len(page.get("content_relations") or []),
            }
            for page in pages
            if page.get("page_type") == "content"
        ],
        "edges": edges,
        "source_record_count": len(_dict_items(source_truth or {}, "records")),
    }
