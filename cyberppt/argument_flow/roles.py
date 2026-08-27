"""Argument/page role vocabulary and legacy page-role contract validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .evidence import string_list

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
    "scope": frozenset({"fact", "judgment", "recommendation", "boundary", "unresolved"}),
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


def validate_page_role_fields(outline: dict[str, object]) -> list[ArgumentFlowIssue]:
    if outline.get("argument_contract_mode", "legacy") != "strict":
        return []
    if outline.get("schema") == "cyberppt.outline.v2":
        from .page_contract import validate_source_relation_fields

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
                    "Strict content pages must declare page_job, proof_points, new_value_vs_previous, and reserved_for_later.",
                    (page_id,) if page_id else (),
                    retry_strategy="complete_page_contribution_contract",
                )
            )
        proof_points = raw_page.get("proof_points")
        page_sources = set(string_list(raw_page, "source_refs"))
        boundary_sources = set(string_list(raw_page, "boundary_refs"))
        proof_sources: set[str] = set()
        if isinstance(proof_points, list):
            invalid = False
            for point in proof_points:
                if not isinstance(point, dict) or not str(point.get("claim") or "").strip():
                    invalid = True
                    break
                refs = string_list(point, "source_refs")
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
                        "Each proof point must contain a claim and cite only Source IDs assigned to the page.",
                        (page_id,) if page_id else (),
                        retry_strategy="reconcile_page_proof_points",
                    )
                )
        if not boundary_sources.issubset(page_sources) or boundary_sources & proof_sources:
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


__all__ = [
    "ArgumentFlowIssue",
    "CLAIM_ROLES",
    "DEFAULT_ALLOWED_CLAIMS",
    "PAGE_ARGUMENT_ROLES",
    "PAGE_CONTRIBUTION_FIELDS",
    "SEMANTIC_CONTRIBUTION_FIELDS",
    "validate_page_role_fields",
]
