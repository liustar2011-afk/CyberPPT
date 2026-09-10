"""Typed evidence-role compatibility checks for Final Script 1.1 provenance.

This module deliberately does not inspect visible prose. Decisions come only from
Foundation typed fields and explicit provenance relations.
"""

from __future__ import annotations

from typing import Any

from .foundation_index import FoundationIndex
from .models import SemanticDiagnostic


RELATION_ALLOWED_EVIDENCE_ROLES: dict[str, frozenset[str]] = {
    "supports": frozenset({"premise", "support", "detail"}),
    "qualifies": frozenset({"boundary", "detail", "constraint"}),
    "implements": frozenset({"response", "recommendation"}),
    "contrasts": frozenset({"gap", "premise", "driver", "consequence"}),
    "sequences": frozenset({"response", "detail"}),
}

ROLE_ALIASES: dict[str, str] = {
    "supporting": "support",
    "support": "support",
    "premise": "premise",
    "detail": "detail",
    "constraint": "constraint",
    "boundary": "boundary",
    "response": "response",
    "recommendation": "recommendation",
    "gap": "gap",
    "driver": "driver",
    "consequence": "consequence",
    "core": "premise",
}


def _text(value: object) -> str:
    return str(value or "").strip()


def _refs(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(_text(item) for item in value if _text(item))


def _role(index: FoundationIndex, ref: str) -> str:
    value = index.argument_duty(ref).strip().lower()
    return ROLE_ALIASES.get(value, "")


def _resolved_roles(
    index: FoundationIndex,
    refs: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    roles: list[str] = []
    unknown_refs: list[str] = []
    for ref in refs:
        role = _role(index, ref)
        if role:
            roles.append(role)
        else:
            unknown_refs.append(ref)
    return tuple(roles), tuple(unknown_refs)


def _diagnostic(
    code: str,
    message: str,
    *,
    slide_id: str,
    module_id: str,
    target: str,
    severity: str,
    claim_refs: tuple[str, ...],
    evidence_refs: tuple[str, ...],
    relation: str,
) -> SemanticDiagnostic:
    return SemanticDiagnostic(
        code=code,
        message=message,
        slide_id=slide_id,
        module_id=module_id,
        target=target,
        severity=severity,
        claim_refs=claim_refs,
        evidence_refs=evidence_refs,
        relation=relation,
    )


def collect_provenance_compatibility_diagnostics(
    final_script: dict[str, Any],
    foundation: dict[str, Any] | None,
) -> list[SemanticDiagnostic]:
    """Validate provenance role compatibility from structured fields only."""

    if _text(final_script.get("version")) != "1.1" or not isinstance(foundation, dict):
        return []

    diagnostics: list[SemanticDiagnostic] = []
    index = FoundationIndex(foundation)

    for slide in final_script.get("slides") or []:
        if not isinstance(slide, dict) or _text(slide.get("page_type")) != "content":
            continue
        slide_id = _text(slide.get("id"))
        for module in slide.get("onscreen") or []:
            if not isinstance(module, dict):
                continue
            module_id = _text(module.get("id"))
            provenance = module.get("provenance")
            if not isinstance(provenance, dict):
                continue
            claim_refs = _refs(provenance.get("claim_refs"))
            claim_roles, unknown_claim_refs = _resolved_roles(index, claim_refs)

            for binding in provenance.get("bindings") or []:
                if not isinstance(binding, dict):
                    continue
                target = _text(binding.get("target"))
                relation = _text(binding.get("relation"))
                evidence_refs = _refs(binding.get("source_refs"))
                if relation == "expresses":
                    continue
                allowed_roles = RELATION_ALLOWED_EVIDENCE_ROLES.get(relation)
                if allowed_roles is None:
                    continue

                evidence_roles, unknown_evidence_refs = _resolved_roles(
                    index, evidence_refs
                )
                if unknown_evidence_refs:
                    diagnostics.append(
                        _diagnostic(
                            "EVIDENCE_ROLE_UNKNOWN",
                            "Foundation does not expose a recognized typed evidence role for every evidence ref; compatibility requires review",
                            slide_id=slide_id,
                            module_id=module_id,
                            target=target,
                            severity="review_required",
                            claim_refs=claim_refs,
                            evidence_refs=unknown_evidence_refs,
                            relation=relation,
                        )
                    )

                incompatible = tuple(
                    sorted({role for role in evidence_roles if role not in allowed_roles})
                )
                if incompatible:
                    diagnostics.append(
                        _diagnostic(
                            "EVIDENCE_ROLE_INCOMPATIBLE",
                            f"evidence role(s) {', '.join(incompatible)} cannot be used as {relation}",
                            slide_id=slide_id,
                            module_id=module_id,
                            target=target,
                            severity="blocking",
                            claim_refs=claim_refs,
                            evidence_refs=evidence_refs,
                            relation=relation,
                        )
                    )
                    continue

                if relation == "implements" and claim_roles:
                    target_incompatible = tuple(
                        sorted(
                            {
                                role
                                for role in claim_roles
                                if role not in {"response", "recommendation"}
                            }
                        )
                    )
                    if target_incompatible:
                        diagnostics.append(
                            _diagnostic(
                                "CLAIM_ROLE_INCOMPATIBLE",
                                "implements requires a response or recommendation claim target",
                                slide_id=slide_id,
                                module_id=module_id,
                                target=target,
                                severity="blocking",
                                claim_refs=claim_refs,
                                evidence_refs=evidence_refs,
                                relation=relation,
                            )
                        )
                elif relation == "implements" and unknown_claim_refs:
                    diagnostics.append(
                        _diagnostic(
                            "CLAIM_ROLE_UNKNOWN",
                            "Foundation does not expose the claim role required to verify implements",
                            slide_id=slide_id,
                            module_id=module_id,
                            target=target,
                            severity="review_required",
                            claim_refs=claim_refs,
                            evidence_refs=evidence_refs,
                            relation=relation,
                        )
                    )

                if relation == "contrasts":
                    independent = set(claim_refs) - set(evidence_refs)
                    if not independent:
                        diagnostics.append(
                            _diagnostic(
                                "CONTRAST_INDEPENDENT_EVIDENCE_REQUIRED",
                                "contrasts requires evidence independent from the module claim refs",
                                slide_id=slide_id,
                                module_id=module_id,
                                target=target,
                                severity="blocking",
                                claim_refs=claim_refs,
                                evidence_refs=evidence_refs,
                                relation=relation,
                            )
                        )

    return diagnostics


def validate_provenance_compatibility(
    final_script: dict[str, Any],
    foundation: dict[str, Any] | None,
) -> list[str]:
    """Compatibility wrapper returning blocking issue strings only."""

    return [
        diagnostic.render()
        for diagnostic in collect_provenance_compatibility_diagnostics(
            final_script, foundation
        )
        if diagnostic.severity == "blocking"
    ]
