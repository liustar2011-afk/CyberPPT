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
EVIDENCE_TYPE_TO_CLAIM_ROLE = {
    "F": "fact",
    "J": "judgment",
    "R": "recommendation",
    "B": "boundary",
    "U": "unresolved",
}


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
        if isinstance(proof_points, list):
            invalid = False
            for point in proof_points:
                if not isinstance(point, dict) or not str(point.get("claim") or "").strip():
                    invalid = True
                    break
                refs = _string_list(point, "source_refs")
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
            if claim_role not in allowed or claim_role in forbidden:
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
        for point in page.get("proof_points", []):
            if isinstance(point, dict) and point.get("consumption") == "primary":
                for source_id in _string_list(point, "source_refs"):
                    primary_pages_by_source.setdefault(source_id, set()).add(page_id)
    for source_id, owners in primary_pages_by_source.items():
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
                previous.get("page_job"), current.get("page_job")
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
            }
            for page in pages
            if page.get("page_type") == "content"
        ],
        "edges": edges,
        "source_record_count": len(_dict_items(source_truth or {}, "records")),
    }
