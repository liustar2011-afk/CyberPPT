"""Structured page-level source-scope checks for Final Script."""

from __future__ import annotations

from typing import Any

from script_engine.source_trace_contracts import FOUNDATION_CITABLE_KEYS


_STRUCTURAL_PAGE_ROLES = frozenset({"cover", "contents", "chapter", "closing"})
_PAGE_ROLE_ALIASES = {
    "agenda": "contents",
    "ending": "closing",
}


def _normalized_page_role(page: dict[str, Any]) -> str:
    role = str(page.get("page_type") or page.get("page_role") or "").strip()
    return _PAGE_ROLE_ALIASES.get(role, role)


def _requires_source_consumption(
    page: dict[str, Any],
    foundation: dict[str, Any],
) -> bool:
    return (
        foundation.get("source_consumption_policy") == "required"
        and bool(
            [
                ref
                for ref in page.get("source_refs") or []
                if isinstance(ref, str) and ref
            ]
        )
        and _normalized_page_role(page) not in _STRUCTURAL_PAGE_ROLES
    )


def _foundation_record_ids(foundation: dict[str, Any]) -> set[str]:
    """Return directly addressable Foundation record IDs.

    Strict AUTHOR ``slide.source_refs`` declares Foundation records actually
    consumed. Source-unit aliases are intentionally not accepted here: allowing a
    nested ``source_refs`` value to stand in for its owning Foundation record
    would weaken the page-level provenance contract.
    """

    known: set[str] = set()
    for key in FOUNDATION_CITABLE_KEYS:
        for item in foundation.get(key) or []:
            if not isinstance(item, dict):
                continue
            ref = item.get("id")
            if isinstance(ref, str) and ref:
                known.add(ref)
    return known


def validate_source_scope(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
    foundation: dict[str, Any] | None,
) -> list[str]:
    """Validate strict Final Script source declarations against PLAN scope.

    Only deterministic cross-artifact facts are checked here:

    - a sourced non-structural page declares the Foundation records AUTHOR used;
    - every declared record exists in Foundation;
    - every declared record lies inside the PLAN-approved page ``source_refs``.

    Coverage counts, paragraph counts and lexical overlap remain compatibility
    advisories and are deliberately excluded from this structured validator.
    """

    plan = plan if isinstance(plan, dict) else {}
    foundation = foundation if isinstance(foundation, dict) else {}
    pages = {
        page.get("id"): page
        for page in plan.get("pages") or []
        if isinstance(page, dict) and isinstance(page.get("id"), str)
    }
    known = _foundation_record_ids(foundation)
    issues: list[str] = []

    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        page = pages.get(slide_id)
        if not isinstance(page, dict) or not _requires_source_consumption(page, foundation):
            continue

        page_refs = {
            ref
            for ref in page.get("source_refs") or []
            if isinstance(ref, str) and ref
        }
        slide_refs = [
            ref
            for ref in slide.get("source_refs") or []
            if isinstance(ref, str) and ref
        ]
        scope = f"slides.{index} ({slide_id})"

        if not slide_refs:
            issues.append(
                f"{scope}: AUTHOR_SOURCE_CONSUMPTION_MISSING: strict sourced content page "
                "requires slide.source_refs to declare the Foundation records AUTHOR actually used"
            )
            continue

        unknown = sorted({ref for ref in slide_refs if ref not in known})
        if unknown:
            issues.append(
                f"{scope}: AUTHOR_SOURCE_REF_UNKNOWN: slide.source_refs cites unknown "
                f"foundation records {unknown}"
            )

        outside = sorted({ref for ref in slide_refs if ref not in page_refs} - set(unknown))
        if outside:
            issues.append(
                f"{scope}: AUTHOR_SOURCE_REF_OUTSIDE_PLAN_SCOPE: slide.source_refs "
                f"{outside} fall outside the page's PLAN-approved source_refs boundary"
            )

    return issues
