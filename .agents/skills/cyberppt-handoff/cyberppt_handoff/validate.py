from __future__ import annotations

from typing import Any


def _issue(errors: list[dict[str, Any]], code: str, message: str, **context: Any) -> None:
    errors.append({"code": code, "message": message, "context": context})


def validate_projection(projection: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    required = (
        "source_registry", "source_units", "source_heading_tree", "semantic_argument_model",
        "source_truth", "outline", "authority_map", "report",
    )
    for key in required:
        if key not in projection:
            _issue(errors, "missing_projection_artifact", "Projection artifact is missing", artifact=key)

    units = projection.get("source_units") if isinstance(projection.get("source_units"), list) else []
    unit_ids = {str(item.get("unit_id")) for item in units if isinstance(item, dict) and item.get("unit_id")}
    if len(unit_ids) != len(units):
        _issue(errors, "duplicate_or_missing_source_unit_id", "Every source unit requires one unique unit_id")

    truth = projection.get("source_truth") if isinstance(projection.get("source_truth"), dict) else {}
    records = [item for item in truth.get("records") or [] if isinstance(item, dict)]
    st_ids = {str(item.get("id")) for item in records if item.get("id")}
    authority = projection.get("authority_map") if isinstance(projection.get("authority_map"), dict) else {}
    nf_map = authority.get("normalized_fact_to_source_truth") if isinstance(authority.get("normalized_fact_to_source_truth"), dict) else {}
    mapped_st_ids = {str(value) for value in nf_map.values()}

    for record in records:
        record_id = str(record.get("id") or "")
        authority_ref = str(record.get("authority_ref") or "")
        if not record_id or not authority_ref or nf_map.get(authority_ref) != record_id:
            _issue(errors, "missing_authority_mapping", "Every Source Truth record must map back to exactly one normalized fact", source_truth_id=record_id, authority_ref=authority_ref)
        for ref in record.get("source_unit_refs") or []:
            if str(ref) not in unit_ids:
                _issue(errors, "unknown_source_unit_ref", "Source Truth record references an unknown projected source unit", source_truth_id=record_id, source_unit_id=ref)
        locator = record.get("source_locator")
        if not isinstance(locator, dict) or locator.get("line_start") is None:
            _issue(errors, "missing_projected_locator", "Source Truth record must preserve a projected source line locator", source_truth_id=record_id)
    for st_id in mapped_st_ids:
        if st_id not in st_ids:
            _issue(errors, "authority_map_points_to_unknown_source_truth", "Authority map points to missing Source Truth record", source_truth_id=st_id)

    model = projection.get("semantic_argument_model") if isinstance(projection.get("semantic_argument_model"), dict) else {}
    if model.get("authority_mode") != "projection_only":
        _issue(errors, "semantic_projection_authority_invalid", "Projected semantic model must declare authority_mode=projection_only")
    for relation in model.get("argument_relations") or []:
        if not isinstance(relation, dict):
            continue
        if relation.get("basis") == "inferred" and relation.get("claim_origin") == "source_explicit":
            _issue(errors, "inferred_relation_upgraded", "An inferred layer-three relation may not be upgraded to source_explicit", relation_id=relation.get("id"))
        if relation.get("basis") == "inferred" and not str(relation.get("inference_rationale") or "").strip():
            _issue(errors, "inferred_relation_missing_rationale", "Projected inferred relation must keep its upstream inference rationale", relation_id=relation.get("id"))

    outline = projection.get("outline") if isinstance(projection.get("outline"), dict) else {}
    if outline.get("authority_mode") != "projection_only":
        _issue(errors, "outline_projection_authority_invalid", "Projected outline must declare authority_mode=projection_only")
    pages = [item for item in outline.get("pages") or [] if isinstance(item, dict)]
    page_map = authority.get("page_to_cyberppt_page") if isinstance(authority.get("page_to_cyberppt_page"), dict) else {}
    cyber_to_authority = {str(cyber): str(source) for source, cyber in page_map.items()}
    direct_source_truth = authority.get("page_direct_source_truth") if isinstance(authority.get("page_direct_source_truth"), dict) else {}
    for page in pages:
        if page.get("page_type") != "content":
            continue
        page_id = str(page.get("page_id") or "")
        refs = {str(ref) for ref in page.get("source_refs") or []}
        authority_page_id = cyber_to_authority.get(page_id, "")
        expected_direct_refs = {str(ref) for ref in direct_source_truth.get(authority_page_id, [])}
        if authority_page_id and refs != expected_direct_refs:
            _issue(
                errors,
                "page_source_refs_exceed_direct_authority",
                "Projected CyberPPT source_refs must equal the page's explicitly assigned normalized-fact projection; semantic relations and broader argument nodes may not add sibling facts.",
                page_id=page_id,
                authority_page_id=authority_page_id,
                extra=sorted(refs - expected_direct_refs),
                missing=sorted(expected_direct_refs - refs),
            )
        unknown = sorted(refs - st_ids)
        for ref in unknown:
            _issue(errors, "unknown_source_truth_ref", "CyberPPT page references unknown projected Source Truth", page_id=page_id, source_truth_id=ref)
        for unit in page.get("content_units") or []:
            if not isinstance(unit, dict):
                _issue(errors, "invalid_content_unit", "Projected page content_units must contain objects", page_id=page_id)
                continue
            unit_refs = {str(ref) for ref in unit.get("source_refs") or []}
            outside = sorted(unit_refs - refs)
            if outside:
                _issue(errors, "content_unit_ref_outside_page", "Content unit may only consume Source Truth already declared by its page", page_id=page_id, unit_id=unit.get("unit_id"), source_truth_ids=outside)
        for field in ("audience_question", "page_mission", "core_message", "non_substitutable_value", "must_not_include", "argument_chain", "evidence_roles", "content_units"):
            value = page.get(field)
            if value is None or value == "" or value == []:
                _issue(errors, "missing_downstream_page_field", "Projected content page is missing a CyberPPT downstream authoring field", page_id=page_id, field=field)

    if authority.get("authority_mode") != "projection_only":
        _issue(errors, "authority_map_mode_invalid", "authority-map must declare projection_only")

    report = projection.get("report") if isinstance(projection.get("report"), dict) else {}
    runtime = report.get("runtime_validation") if isinstance(report.get("runtime_validation"), dict) else {}
    if runtime.get("status") not in {"not_run", "passed", "failed"}:
        _issue(errors, "invalid_runtime_validation_status", "runtime_validation status must be not_run, passed, or failed")
    if runtime.get("status") == "not_run":
        warnings.append({"code": "cyberppt_runtime_not_executed", "message": "Projection contract is validated locally, but CyberPPT runtime audit has not been executed."})

    return {
        "schema": "source-material-foundation.cyberppt_projection_validation.v1",
        "status": "ok" if not errors else "error",
        "errors": errors,
        "warnings": warnings,
        "counts": {"source_units": len(units), "source_truth_records": len(records), "pages": len(pages)},
    }
