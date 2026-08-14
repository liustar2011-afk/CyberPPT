from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
FACT_TYPES = {
    "actor", "organization", "project", "platform", "service", "capability",
    "requirement", "goal", "metric", "process", "deliverable", "constraint",
    "relationship", "event", "policy_basis", "problem", "technology", "dataset",
    "scenario", "responsibility", "condition", "other",
}
NORMALIZATION_TYPES = {"verbatim", "canonicalized", "merged"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
CONCEPT_TYPES = {
    "organization", "actor", "project", "platform", "service", "capability",
    "dataset", "policy", "requirement", "process", "technology", "scenario",
    "deliverable", "metric", "goal", "problem", "constraint", "domain_term", "other",
}
RELATION_TYPES = {
    "has_goal", "has_capability", "provides", "uses", "depends_on", "supports",
    "enables", "governs", "contains", "outputs", "serves", "collaborates_with",
    "requires", "constrains", "addresses", "measures", "precedes", "flows_to",
    "part_of", "responsible_for", "operates", "builds", "owns", "associated_with", "other",
}
RELATION_BASIS = {"explicit", "inferred"}
ARGUMENT_ROLES = {
    "context", "background", "problem", "cause", "policy_basis", "requirement", "goal",
    "principle", "approach", "capability", "mechanism", "process", "responsibility",
    "input", "output", "deliverable", "benefit", "evidence", "constraint", "risk",
    "condition", "implementation", "conclusion", "recommendation", "other",
}
DIAGNOSTIC_TYPES = {
    "duplicate_argument", "overlap_or_non_mece", "logic_gap", "missing_bridge", "mixed_level",
    "scope_shift", "unsupported_jump", "contradictory_claims", "unbalanced_parallelism",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten_section_ids(nodes: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for node in nodes:
        section_id = node.get("section_id")
        if section_id:
            result.add(section_id)
        result.update(_flatten_section_ids(list(node.get("children", []))))
    return result


def _error(errors: list[dict[str, Any]], code: str, message: str, **context: Any) -> None:
    item: dict[str, Any] = {"code": code, "message": message}
    if context:
        item["context"] = context
    errors.append(item)


def _warning(warnings: list[dict[str, Any]], code: str, message: str, **context: Any) -> None:
    item: dict[str, Any] = {"code": code, "message": message}
    if context:
        item["context"] = context
    warnings.append(item)


def _check_header(payload: dict[str, Any], expected_type: str, filename: str, errors: list[dict[str, Any]]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        _error(errors, "unsupported_schema_version", f"{filename} must use schema_version {SCHEMA_VERSION}.", file=filename)
    if payload.get("artifact_type") != expected_type:
        _error(errors, "invalid_artifact_type", f"{filename} must have artifact_type {expected_type}.", file=filename)


def _duplicate_ids(items: list[dict[str, Any]], key: str, scope: str, errors: list[dict[str, Any]]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value:
            _error(errors, "missing_id", f"{scope} item is missing {key}.", scope=scope)
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    for value in sorted(duplicates):
        _error(errors, "duplicate_id", f"Duplicate {key}: {value}.", scope=scope, id=value)
    return seen


def _validate_normalized(
    payload: dict[str, Any],
    source_facts: dict[str, dict[str, Any]],
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> set[str]:
    facts = payload.get("facts")
    if not isinstance(facts, list):
        _error(errors, "invalid_shape", "normalized-facts.json facts must be an array.")
        return set()
    normalized_ids = _duplicate_ids(facts, "normalized_fact_id", "normalized_facts", errors)

    for fact in facts:
        nf_id = fact.get("normalized_fact_id", "<missing>")
        if not str(fact.get("statement", "")).strip():
            _error(errors, "missing_statement", "Normalized fact statement cannot be empty.", normalized_fact_id=nf_id)
        if fact.get("fact_type") not in FACT_TYPES:
            _error(errors, "invalid_fact_type", "Normalized fact uses an unsupported fact_type.", normalized_fact_id=nf_id, value=fact.get("fact_type"))
        if fact.get("normalization") not in NORMALIZATION_TYPES:
            _error(errors, "invalid_normalization", "Normalized fact uses an unsupported normalization mode.", normalized_fact_id=nf_id, value=fact.get("normalization"))
        if fact.get("verification_status") != "unverified":
            _error(errors, "invalid_verification_status", "Layer three cannot mark source material as externally verified.", normalized_fact_id=nf_id)
        if fact.get("confidence") not in CONFIDENCE_LEVELS:
            _error(errors, "invalid_confidence", "Normalized fact confidence must be high, medium, or low.", normalized_fact_id=nf_id)
        if fact.get("confidence") == "low":
            _warning(warnings, "low_confidence_fact", "Normalized fact is marked low confidence.", normalized_fact_id=nf_id)

        source_ids = fact.get("source_assertion_ids")
        if not isinstance(source_ids, list) or not source_ids:
            _error(errors, "missing_source_support", "Every normalized fact must reference at least one source assertion.", normalized_fact_id=nf_id)
            source_ids = []
        for source_id in source_ids:
            if source_id not in source_facts:
                _error(errors, "unknown_source_assertion", f"Unknown source assertion: {source_id}.", normalized_fact_id=nf_id, source_assertion_id=source_id)

        evidence = fact.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            _error(errors, "missing_evidence", "Every normalized fact must carry evidence copied from layer two.", normalized_fact_id=nf_id)
            evidence = []
        evidence_fact_ids: set[str] = set()
        for ref in evidence:
            source_id = ref.get("fact_id")
            if source_id:
                evidence_fact_ids.add(source_id)
            source_fact = source_facts.get(source_id)
            if not source_fact:
                _error(errors, "unknown_source_assertion", f"Evidence references unknown source assertion: {source_id}.", normalized_fact_id=nf_id, source_assertion_id=source_id)
                continue
            expected = source_fact.get("source_ref", {})
            actual = {key: ref.get(key) for key in ("block_id", "line_start", "line_end")}
            expected_compact = {key: expected.get(key) for key in ("block_id", "line_start", "line_end")}
            if actual != expected_compact:
                _error(errors, "evidence_mismatch", "Evidence must exactly match the layer-two source reference.", normalized_fact_id=nf_id, fact_id=source_id, expected=expected_compact, actual=actual)
        for source_id in source_ids:
            if source_id in source_facts and source_id not in evidence_fact_ids:
                _error(errors, "missing_evidence_for_source", "Every source_assertion_id must have a matching evidence record.", normalized_fact_id=nf_id, source_assertion_id=source_id)

    conflicts = payload.get("conflicts", [])
    ambiguities = payload.get("ambiguities", [])
    if not isinstance(conflicts, list) or not isinstance(ambiguities, list):
        _error(errors, "invalid_shape", "conflicts and ambiguities must be arrays.")
    if isinstance(conflicts, list) and conflicts:
        _warning(warnings, "source_conflicts_present", "Semantic normalization retained source conflicts.", count=len(conflicts))
    if isinstance(ambiguities, list) and ambiguities:
        _warning(warnings, "unresolved_ambiguities_present", "Semantic normalization retained unresolved ambiguities.", count=len(ambiguities))
    return normalized_ids


def _validate_concepts(payload: dict[str, Any], normalized_ids: set[str], errors: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> set[str]:
    concepts = payload.get("concepts")
    if not isinstance(concepts, list):
        _error(errors, "invalid_shape", "concept-base.json concepts must be an array.")
        return set()
    concept_ids = _duplicate_ids(concepts, "concept_id", "concepts", errors)
    canonical_names: dict[str, str] = {}
    for concept in concepts:
        concept_id = concept.get("concept_id", "<missing>")
        name = str(concept.get("canonical_name", "")).strip()
        if not name:
            _error(errors, "missing_concept_name", "Concept canonical_name cannot be empty.", concept_id=concept_id)
        folded = name.casefold()
        if name and folded in canonical_names and canonical_names[folded] != concept_id:
            _warning(warnings, "duplicate_concept_name", "Multiple concepts use the same canonical name.", canonical_name=name)
        canonical_names[folded] = concept_id
        if concept.get("concept_type") not in CONCEPT_TYPES:
            _error(errors, "invalid_concept_type", "Concept uses an unsupported concept_type.", concept_id=concept_id, value=concept.get("concept_type"))
        refs = concept.get("normalized_fact_ids")
        if not isinstance(refs, list) or not refs:
            _error(errors, "concept_without_evidence", "Every concept must be supported by normalized facts.", concept_id=concept_id)
            refs = []
        for ref in refs:
            if ref not in normalized_ids:
                _error(errors, "unknown_normalized_fact", f"Concept references unknown normalized fact: {ref}.", concept_id=concept_id, normalized_fact_id=ref)
        if concept.get("confidence") not in CONFIDENCE_LEVELS:
            _error(errors, "invalid_confidence", "Concept confidence must be high, medium, or low.", concept_id=concept_id)
    return concept_ids


def _validate_relations(payload: dict[str, Any], concept_ids: set[str], normalized_ids: set[str], errors: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> int:
    relations = payload.get("relations")
    if not isinstance(relations, list):
        _error(errors, "invalid_shape", "relation-graph.json relations must be an array.")
        return 0
    _duplicate_ids(relations, "relation_id", "relations", errors)
    for relation in relations:
        relation_id = relation.get("relation_id", "<missing>")
        for key in ("from_concept_id", "to_concept_id"):
            concept_id = relation.get(key)
            if concept_id not in concept_ids:
                _error(errors, "unknown_concept", f"Relation references unknown concept: {concept_id}.", relation_id=relation_id, field=key)
        if relation.get("relation_type") not in RELATION_TYPES:
            _error(errors, "invalid_relation_type", "Relation uses an unsupported relation_type.", relation_id=relation_id, value=relation.get("relation_type"))
        basis = relation.get("basis")
        if basis not in RELATION_BASIS:
            _error(errors, "invalid_relation_basis", "Relation basis must be explicit or inferred.", relation_id=relation_id)
        if basis == "inferred" and not str(relation.get("inference_rationale", "")).strip():
            _error(errors, "missing_inference_rationale", "Inferred relations require inference_rationale.", relation_id=relation_id)
        refs = relation.get("normalized_fact_ids")
        if not isinstance(refs, list) or not refs:
            _error(errors, "relation_without_evidence", "Every relation must reference normalized facts.", relation_id=relation_id)
            refs = []
        for ref in refs:
            if ref not in normalized_ids:
                _error(errors, "unknown_normalized_fact", f"Relation references unknown normalized fact: {ref}.", relation_id=relation_id, normalized_fact_id=ref)
        if relation.get("confidence") not in CONFIDENCE_LEVELS:
            _error(errors, "invalid_confidence", "Relation confidence must be high, medium, or low.", relation_id=relation_id)
        if basis == "inferred":
            _warning(warnings, "inferred_relation", "Relation is explicitly labeled as model inference.", relation_id=relation_id)
    return len(relations)


def _validate_chain_nodes(
    nodes: Any,
    scope: str,
    normalized_ids: set[str],
    section_ids: set[str],
    errors: list[dict[str, Any]],
) -> int:
    if not isinstance(nodes, list):
        _error(errors, "invalid_shape", f"argument-chain.json {scope} must be an array.")
        return 0
    _duplicate_ids(nodes, "node_id", scope, errors)
    seen_orders: set[int] = set()
    for node in nodes:
        node_id = node.get("node_id", "<missing>")
        order = node.get("order")
        if not isinstance(order, int) or order < 1:
            _error(errors, "invalid_argument_order", "Argument node order must be a positive integer.", node_id=node_id, scope=scope)
        elif order in seen_orders:
            _error(errors, "duplicate_argument_order", "Argument node order must be unique within a chain.", node_id=node_id, scope=scope, order=order)
        else:
            seen_orders.add(order)
        if node.get("role") not in ARGUMENT_ROLES:
            _error(errors, "invalid_argument_role", "Argument node uses an unsupported role.", node_id=node_id, scope=scope, value=node.get("role"))
        refs = node.get("normalized_fact_ids")
        if not isinstance(refs, list) or not refs:
            _error(errors, "argument_without_evidence", "Argument nodes must reference normalized facts.", node_id=node_id, scope=scope)
            refs = []
        for ref in refs:
            if ref not in normalized_ids:
                _error(errors, "unknown_normalized_fact", f"Argument node references unknown normalized fact: {ref}.", node_id=node_id, scope=scope, normalized_fact_id=ref)
        sections = node.get("section_ids")
        if not isinstance(sections, list) or not sections:
            _error(errors, "argument_without_section", "Argument nodes must reference at least one source section.", node_id=node_id, scope=scope)
            sections = []
        for section_id in sections:
            if section_id not in section_ids:
                _error(errors, "unknown_section", f"Argument node references unknown section: {section_id}.", node_id=node_id, scope=scope, section_id=section_id)
    return len(nodes)


def _validate_argument(payload: dict[str, Any], normalized_ids: set[str], section_ids: set[str], errors: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> tuple[int, int, int]:
    source_count = _validate_chain_nodes(payload.get("source_chain"), "source_chain", normalized_ids, section_ids, errors)
    reconstructed_count = _validate_chain_nodes(payload.get("reconstructed_chain"), "reconstructed_chain", normalized_ids, section_ids, errors)
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, list):
        _error(errors, "invalid_shape", "argument-chain.json diagnostics must be an array.")
        diagnostics = []
    _duplicate_ids(diagnostics, "diagnostic_id", "argument_diagnostics", errors)
    for diagnostic in diagnostics:
        diagnostic_id = diagnostic.get("diagnostic_id", "<missing>")
        if diagnostic.get("type") not in DIAGNOSTIC_TYPES:
            _error(errors, "invalid_diagnostic_type", "Argument diagnostic uses an unsupported type.", diagnostic_id=diagnostic_id, value=diagnostic.get("type"))
        refs = diagnostic.get("normalized_fact_ids", [])
        if not isinstance(refs, list):
            _error(errors, "invalid_shape", "Diagnostic normalized_fact_ids must be an array.", diagnostic_id=diagnostic_id)
            refs = []
        for ref in refs:
            if ref not in normalized_ids:
                _error(errors, "unknown_normalized_fact", f"Diagnostic references unknown normalized fact: {ref}.", diagnostic_id=diagnostic_id, normalized_fact_id=ref)
        sections = diagnostic.get("section_ids", [])
        if not isinstance(sections, list):
            _error(errors, "invalid_shape", "Diagnostic section_ids must be an array.", diagnostic_id=diagnostic_id)
            sections = []
        for section_id in sections:
            if section_id not in section_ids:
                _error(errors, "unknown_section", f"Diagnostic references unknown section: {section_id}.", diagnostic_id=diagnostic_id, section_id=section_id)
    if diagnostics:
        _warning(warnings, "argument_diagnostics_present", "Source argument-chain diagnostics were retained rather than silently repaired.", count=len(diagnostics))
    return source_count, reconstructed_count, len(diagnostics)


def validate_semantic_outputs(
    foundation_dir: Path | str,
    semantic_dir: Path | str,
    *,
    write_report: bool = False,
) -> dict[str, Any]:
    foundation = Path(foundation_dir)
    semantic = Path(semantic_dir)
    required = {
        "structure": foundation / "structure.json",
        "fact_base": foundation / "fact-base.json",
        "normalized": semantic / "normalized-facts.json",
        "concepts": semantic / "concept-base.json",
        "relations": semantic / "relation-graph.json",
        "argument": semantic / "argument-chain.json",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        result = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "semantic_validation_report",
            "status": "error",
            "errors": [{"code": "missing_artifact", "message": f"Missing required artifact: {path}"} for path in missing],
            "warnings": [],
            "counts": {},
        }
        if write_report:
            semantic.mkdir(parents=True, exist_ok=True)
            (semantic / "semantic-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result

    structure = _read_json(required["structure"])
    fact_base = _read_json(required["fact_base"])
    normalized = _read_json(required["normalized"])
    concepts = _read_json(required["concepts"])
    relations = _read_json(required["relations"])
    argument = _read_json(required["argument"])

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    _check_header(normalized, "normalized_facts", "normalized-facts.json", errors)
    _check_header(concepts, "concept_base", "concept-base.json", errors)
    _check_header(relations, "relation_graph", "relation-graph.json", errors)
    _check_header(argument, "argument_chain", "argument-chain.json", errors)

    source_facts = {entry.get("fact_id"): entry for entry in fact_base.get("entries", []) if entry.get("fact_id")}
    normalized_ids = _validate_normalized(normalized, source_facts, errors, warnings)
    concept_ids = _validate_concepts(concepts, normalized_ids, errors, warnings)
    relation_count = _validate_relations(relations, concept_ids, normalized_ids, errors, warnings)
    section_ids = _flatten_section_ids(list(structure.get("outline", [])))
    source_chain_count, reconstructed_count, diagnostic_count = _validate_argument(argument, normalized_ids, section_ids, errors, warnings)

    result = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "semantic_validation_report",
        "status": "error" if errors else "ok",
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "normalized_facts": len(normalized.get("facts", [])) if isinstance(normalized.get("facts"), list) else 0,
            "concepts": len(concepts.get("concepts", [])) if isinstance(concepts.get("concepts"), list) else 0,
            "relations": relation_count,
            "source_chain_nodes": source_chain_count,
            "reconstructed_chain_nodes": reconstructed_count,
            "diagnostics": diagnostic_count,
        },
    }
    if write_report:
        semantic.mkdir(parents=True, exist_ok=True)
        (semantic / "semantic-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
