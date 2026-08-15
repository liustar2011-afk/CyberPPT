"""Authoring gates shared by the layer-four Outline validator.

The planner may inventory evidence, but it must not silently label that
inventory as professionally authored.  These checks make the authoring
decisions required by the legacy authoring contract explicit while keeping
``key_judgment`` as the canonical layer-four field.
"""

from __future__ import annotations

import re
from typing import Any


AUTHORING_ROLES = ("claim", "reason", "instance", "boundary", "trace_only")
ATTACHMENT_DISPOSITIONS = {"main_deck", "appendix", "trace_only"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _issue(
    issues: list[dict[str, Any]],
    code: str,
    message: str,
    *,
    page_id: str,
) -> None:
    issues.append({"code": code, "message": message, "context": {"page_id": page_id}})


def _exclusion_refs(item: Any) -> list[str]:
    if isinstance(item, str):
        return [item] if item.strip() else []
    if not isinstance(item, dict):
        return []
    refs = item.get("source_refs")
    return [str(value) for value in refs or [] if str(value)] if isinstance(refs, list) else []


def _title_without_number(value: Any) -> str:
    text = re.sub(r"[\s　]+", "", _text(value))
    for pattern in (
        r"^[一二三四五六七八九十百]+、",
        r"^[（(][一二三四五六七八九十百\d]+[）)]",
        r"^\d+(?:\.\d+)*[.、]",
    ):
        text = re.sub(pattern, "", text, count=1)
    return text


def _source_heading_titles(workpack: dict[str, Any] | None) -> set[str]:
    titles: set[str] = set()
    for item in (workpack or {}).get("source_heading_outline") or []:
        if isinstance(item, dict) and _text(item.get("title")):
            titles.add(re.sub(r"[\s　]+", "", _text(item["title"])))
    return titles


def _requires_derivation(outline: dict[str, Any]) -> bool:
    return (
        outline.get("core_message_derivation_mode") == "required"
        or outline.get("schema_version") == "1.1"
    )


def authoring_issues(
    outline: dict[str, Any],
    pages: list[dict[str, Any]],
    *,
    workpack: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return errors for an Outline that claims to be author-complete.

    A mechanical candidate remains valid as a candidate.  The stricter rules
    activate only after the producer explicitly sets ``author_edited``.
    """

    if outline.get("editorial_authoring_mode") != "author_driven":
        return []
    if outline.get("editorial_authoring_status") != "author_edited":
        return []

    issues: list[dict[str, Any]] = []
    heading_titles = _source_heading_titles(workpack)
    require_derivation = _requires_derivation(outline)
    for page in pages:
        if page.get("page_type") != "content":
            continue
        page_id = _text(page.get("page_id")) or "?"

        stripped_title = _title_without_number(page.get("title_intent"))
        if (
            _text(page.get("page_mission")) == f"按源材料说明{stripped_title}。"
            or _text(page.get("audience_question")) == f"源材料如何说明{stripped_title}？"
        ):
            _issue(
                issues,
                "authoring_editorial_placeholder",
                "page_mission/audience_question still use the generic candidate template; author-edited pages must state the page's own non-substitutable role.",
                page_id=page_id,
            )
        if _text(page.get("transition_from_previous")) == "承接源材料前页。" or _text(page.get("transition_to_next")) == "交给源材料下一页继续展开。":
            _issue(
                issues,
                "authoring_editorial_placeholder",
                "transition_from_previous/transition_to_next still use the generic candidate template.",
                page_id=page_id,
            )
        if page.get("must_not_include") == ["后续章节的独立页面使命"]:
            _issue(
                issues,
                "authoring_editorial_placeholder",
                "must_not_include still uses the generic candidate template.",
                page_id=page_id,
            )
        normalized_judgment = re.sub(r"[\s　]+", "", _text(page.get("key_judgment")))
        if normalized_judgment and normalized_judgment in heading_titles:
            _issue(
                issues,
                "authoring_judgment_from_metadata",
                "key_judgment must not equal a source heading title; it must state the page's own claim.",
                page_id=page_id,
            )

        exclusions = page.get("excluded_from_onscreen")
        if not isinstance(exclusions, list):
            _issue(
                issues,
                "authoring_exclusions_missing",
                "Author-edited pages must explicitly record retained evidence excluded from the audience-facing layer.",
                page_id=page_id,
            )
        else:
            page_refs = {
                str(value)
                for value in ((page.get("evidence") or {}).get("normalized_fact_ids") or [])
                if str(value)
            }
            for index, item in enumerate(exclusions):
                refs = _exclusion_refs(item)
                if not refs:
                    _issue(
                        issues,
                        "authoring_exclusion_invalid",
                        "Each excluded_from_onscreen item must name source_refs and a reason.",
                        page_id=f"{page_id}[{index}]",
                    )
                elif not set(refs).issubset(page_refs):
                    _issue(
                        issues,
                        "authoring_exclusion_outside_page",
                        "Excluded evidence must already be declared as direct page evidence.",
                        page_id=page_id,
                    )
                elif isinstance(item, dict) and not _text(item.get("reason")):
                    _issue(
                        issues,
                        "authoring_exclusion_reason_missing",
                        "Each excluded evidence group requires an editorial reason.",
                        page_id=page_id,
                    )

        decisions = page.get("authoring_decisions")
        if not isinstance(decisions, dict) or not all(
            _text(decisions.get(field))
            for field in ("deletion_test", "evidence_selection")
        ):
            _issue(
                issues,
                "authoring_decisions_missing",
                "Author-edited pages must record the deletion test and evidence-selection decision.",
                page_id=page_id,
            )

        derivation = page.get("judgment_derivation") or page.get("core_message_derivation")
        if require_derivation and (
            not isinstance(derivation, dict)
            or not derivation.get("source_refs")
            or not derivation.get("supporting_statements")
            or not _text(derivation.get("derivation"))
        ):
            _issue(
                issues,
                "authoring_judgment_derivation_missing",
                "Author-edited key_judgment requires a source derivation with refs, supporting statements, and derivation text.",
                page_id=page_id,
            )

        roles = page.get("evidence_roles")
        if isinstance(roles, dict):
            claim_refs = {str(value) for value in roles.get("claim") or [] if str(value)}
            derivation_refs = {
                str(value)
                for value in (derivation or {}).get("source_refs", [])
                if str(value)
            } if isinstance(derivation, dict) else set()
            if derivation_refs and not derivation_refs.issubset(claim_refs):
                _issue(
                    issues,
                    "authoring_claim_role_incomplete",
                    "The claim evidence role must cover every source ref used to derive key_judgment.",
                    page_id=page_id,
                )

        chain = page.get("argument_chain")
        statements = [
            re.sub(r"[\s　]+", "", _text(item.get("statement")))
            for item in chain or []
            if isinstance(item, dict) and _text(item.get("statement"))
        ]
        if statements and all(statement in heading_titles for statement in statements):
            _issue(
                issues,
                "authoring_heading_only_argument_chain",
                "A source heading inventory is not an authored argument chain; use source-supported premise, gap, response, or claim statements.",
                page_id=page_id,
            )

        if _text(page.get("title_intent")).startswith("附件"):
            disposition = _text((decisions or {}).get("attachment_disposition")) if isinstance(decisions, dict) else ""
            if disposition not in ATTACHMENT_DISPOSITIONS:
                _issue(
                    issues,
                    "attachment_promotion_decision_missing",
                    "Attachment pages must explicitly decide main-deck, appendix, or trace-only treatment.",
                    page_id=page_id,
                )
            elif disposition == "main_deck" and not _text((decisions or {}).get("attachment_promotion_rationale")):
                _issue(
                    issues,
                    "attachment_promotion_rationale_missing",
                    "An attachment promoted to the main deck requires a business-judgment rationale.",
                    page_id=page_id,
                )

    return issues
