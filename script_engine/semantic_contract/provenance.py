"""Validation for Final Script 1.1 module-level semantic provenance."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .foundation_index import FoundationIndex
from .models import PROVENANCE_DERIVATIONS, PROVENANCE_RELATIONS, SemanticDiagnostic


def _text(value: object) -> str:
    return str(value or "").strip()


def _refs(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(_text(item) for item in value if _text(item))


def _plan_page_refs(plan: dict[str, Any] | None) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    if not isinstance(plan, dict):
        return result
    for page in plan.get("pages") or []:
        if not isinstance(page, dict):
            continue
        page_id = _text(page.get("id"))
        if page_id:
            result[page_id] = set(_refs(page.get("source_refs")))
    return result


def _visible_targets(module: dict[str, Any]) -> tuple[str, ...]:
    targets: list[str] = []
    if _text(module.get("heading")):
        targets.append("heading")
    if _text(module.get("text")):
        targets.append("text")
    for item in module.get("items") or []:
        if isinstance(item, dict):
            item_id = _text(item.get("id"))
            if item_id and _text(item.get("text")):
                targets.append(item_id)
    return tuple(targets)


def _diagnostic(
    diagnostics: list[SemanticDiagnostic],
    code: str,
    message: str,
    *,
    slide_id: str = "",
    module_id: str = "",
    target: str = "",
) -> None:
    diagnostics.append(
        SemanticDiagnostic(
            code=code,
            message=message,
            slide_id=slide_id,
            module_id=module_id,
            target=target,
        )
    )


def _validate_ref_scope(
    diagnostics: list[SemanticDiagnostic],
    refs: tuple[str, ...],
    *,
    slide_id: str,
    module_id: str,
    target: str,
    slide_refs: set[str],
    plan_refs: set[str] | None,
    foundation_index: FoundationIndex | None,
) -> None:
    for ref in refs:
        if ref not in slide_refs:
            _diagnostic(
                diagnostics,
                "PROVENANCE_REF_OUTSIDE_SLIDE",
                f"source ref {ref!r} is not declared by slide.source_refs",
                slide_id=slide_id,
                module_id=module_id,
                target=target,
            )
        if plan_refs is not None and ref not in plan_refs:
            _diagnostic(
                diagnostics,
                "PROVENANCE_REF_OUTSIDE_PAGE",
                f"source ref {ref!r} is not declared by the matching plan page",
                slide_id=slide_id,
                module_id=module_id,
                target=target,
            )
        if foundation_index is not None and not foundation_index.contains(ref):
            _diagnostic(
                diagnostics,
                "PROVENANCE_REF_UNKNOWN",
                f"source ref {ref!r} cannot be resolved in Foundation",
                slide_id=slide_id,
                module_id=module_id,
                target=target,
            )


def validate_final_script_provenance(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None = None,
    foundation: dict[str, Any] | None = None,
) -> list[str]:
    """Validate explicit module provenance for Final Script 1.1.

    Version 1.0 remains readable and is intentionally not backfilled by
    inference. New 1.1 content pages must carry stable module/item identifiers
    and explicit source bindings.
    """

    if _text(final_script.get("version")) != "1.1":
        return []

    diagnostics: list[SemanticDiagnostic] = []
    plan_refs_by_page = _plan_page_refs(plan)
    foundation_index = FoundationIndex(foundation) if isinstance(foundation, dict) else None
    module_ids: set[str] = set()
    item_ids: set[str] = set()

    for slide in final_script.get("slides") or []:
        if not isinstance(slide, dict) or _text(slide.get("page_type")) != "content":
            continue
        slide_id = _text(slide.get("id"))
        slide_refs = set(_refs(slide.get("source_refs")))
        plan_refs = plan_refs_by_page.get(slide_id)
        if isinstance(plan, dict) and slide_id not in plan_refs_by_page:
            _diagnostic(
                diagnostics,
                "PROVENANCE_PAGE_NOT_IN_PLAN",
                "content slide has no matching deck-plan page",
                slide_id=slide_id,
            )

        for module in slide.get("onscreen") or []:
            if not isinstance(module, dict):
                continue
            module_id = _text(module.get("id"))
            if module_id:
                if module_id in module_ids:
                    _diagnostic(
                        diagnostics,
                        "PROVENANCE_MODULE_ID_DUPLICATE",
                        f"module id {module_id!r} is not globally unique",
                        slide_id=slide_id,
                        module_id=module_id,
                    )
                module_ids.add(module_id)

            for item in module.get("items") or []:
                if not isinstance(item, dict):
                    continue
                item_id = _text(item.get("id"))
                if not item_id:
                    continue
                if item_id in item_ids:
                    _diagnostic(
                        diagnostics,
                        "PROVENANCE_ITEM_ID_DUPLICATE",
                        f"item id {item_id!r} is not globally unique",
                        slide_id=slide_id,
                        module_id=module_id,
                        target=item_id,
                    )
                item_ids.add(item_id)

            provenance = module.get("provenance")
            if not isinstance(provenance, dict):
                _diagnostic(
                    diagnostics,
                    "PROVENANCE_MISSING",
                    "module requires explicit provenance",
                    slide_id=slide_id,
                    module_id=module_id,
                )
                continue

            derivation = _text(provenance.get("derivation"))
            claim_refs = _refs(provenance.get("claim_refs"))
            if derivation not in PROVENANCE_DERIVATIONS:
                _diagnostic(
                    diagnostics,
                    "PROVENANCE_DERIVATION_UNKNOWN",
                    f"unsupported derivation {derivation!r}",
                    slide_id=slide_id,
                    module_id=module_id,
                )
            elif derivation == "direct" and len(claim_refs) != 1:
                _diagnostic(
                    diagnostics,
                    "PROVENANCE_DIRECT_CLAIM_COUNT",
                    "direct derivation requires exactly one claim_ref",
                    slide_id=slide_id,
                    module_id=module_id,
                )
            elif derivation in {"synthesis", "relation"} and len(claim_refs) < 2:
                _diagnostic(
                    diagnostics,
                    "PROVENANCE_COMPOSED_CLAIM_COUNT",
                    f"{derivation} derivation requires at least two claim_refs",
                    slide_id=slide_id,
                    module_id=module_id,
                )

            _validate_ref_scope(
                diagnostics,
                claim_refs,
                slide_id=slide_id,
                module_id=module_id,
                target="claim_refs",
                slide_refs=slide_refs,
                plan_refs=plan_refs,
                foundation_index=foundation_index,
            )

            expected_targets = _visible_targets(module)
            bindings = provenance.get("bindings")
            binding_list = [item for item in (bindings or []) if isinstance(item, dict)]
            target_counts = Counter(_text(item.get("target")) for item in binding_list)
            expected_set = set(expected_targets)

            for target in expected_targets:
                if target_counts[target] != 1:
                    _diagnostic(
                        diagnostics,
                        "PROVENANCE_TARGET_BINDING_COUNT",
                        f"visible target requires exactly one binding; found {target_counts[target]}",
                        slide_id=slide_id,
                        module_id=module_id,
                        target=target,
                    )
            for target, count in target_counts.items():
                if not target:
                    continue
                if target not in expected_set:
                    _diagnostic(
                        diagnostics,
                        "PROVENANCE_TARGET_UNKNOWN",
                        "binding target does not identify visible module copy",
                        slide_id=slide_id,
                        module_id=module_id,
                        target=target,
                    )
                if count > 1:
                    _diagnostic(
                        diagnostics,
                        "PROVENANCE_TARGET_DUPLICATE",
                        f"binding target is repeated {count} times",
                        slide_id=slide_id,
                        module_id=module_id,
                        target=target,
                    )

            for binding in binding_list:
                target = _text(binding.get("target"))
                relation = _text(binding.get("relation"))
                source_refs = _refs(binding.get("source_refs"))
                if relation not in PROVENANCE_RELATIONS:
                    _diagnostic(
                        diagnostics,
                        "PROVENANCE_RELATION_UNKNOWN",
                        f"unsupported binding relation {relation!r}",
                        slide_id=slide_id,
                        module_id=module_id,
                        target=target,
                    )
                if not source_refs:
                    _diagnostic(
                        diagnostics,
                        "PROVENANCE_BINDING_SOURCE_EMPTY",
                        "binding requires at least one source_ref",
                        slide_id=slide_id,
                        module_id=module_id,
                        target=target,
                    )
                _validate_ref_scope(
                    diagnostics,
                    source_refs,
                    slide_id=slide_id,
                    module_id=module_id,
                    target=target,
                    slide_refs=slide_refs,
                    plan_refs=plan_refs,
                    foundation_index=foundation_index,
                )

    return [diagnostic.render() for diagnostic in diagnostics]
