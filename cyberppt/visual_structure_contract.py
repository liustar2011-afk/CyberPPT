"""Shared contracts for the Stage 02 visual-structure decision package."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from cyberppt.onscreen_expression import expression_constraints, expression_constraints_sha256


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def skill_bundle_sha256(skill_root: Path) -> str:
    """Hash every authoritative Skill source file, excluding runtime caches."""

    digest = hashlib.sha256()
    for path in sorted(
        (
            item
            for item in skill_root.rglob("*")
            if item.is_file()
            and "__pycache__" not in item.parts
            and item.suffix.casefold() not in {".pyc", ".pyo"}
        ),
        key=lambda item: item.relative_to(skill_root).as_posix(),
    ):
        relative = path.relative_to(skill_root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def prompt_contract_hashes(skill_root: Path) -> dict[str, str]:
    paths = {
        "skill": skill_root / "SKILL.md",
        "prompt_builder": skill_root / "scripts" / "build_generation_prompt.py",
        "validator": skill_root / "scripts" / "validate_visual_spec.py",
        "page_schema": skill_root / "assets" / "page-visual-spec.schema.json",
        "deck_schema": skill_root / "assets" / "deck-visual-spec.schema.json",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("visual structure Skill contract file is missing: " + ", ".join(missing))
    result = {name: sha256(path) for name, path in paths.items()}
    result["skill_bundle"] = skill_bundle_sha256(skill_root)
    return result


def normalize_page_id(value: object) -> str:
    match = re.fullmatch(r"[pP]0*(\d+)", str(value or "").strip())
    if not match:
        return str(value or "").strip().casefold()
    return f"p{int(match.group(1)):02d}"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _index_pages(pages: object) -> tuple[dict[str, dict[str, Any]], list[str]]:
    indexed: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    if not isinstance(pages, list):
        return indexed, duplicates
    for raw in pages:
        if not isinstance(raw, dict):
            continue
        page_id = normalize_page_id(raw.get("page_id"))
        if page_id in indexed:
            duplicates.append(page_id)
        indexed[page_id] = raw
    return indexed, duplicates


def _locked_pairs(page: dict[str, Any]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for item in page.get("locked_text_items") or []:
        if isinstance(item, dict):
            result.append((str(item.get("text_id") or ""), str(item.get("text") or "")))
    return result


def _profile_total(
    profiles: dict[str, Any],
    name: str,
    issues: list[dict[str, Any]],
    page_id: str,
) -> int | None:
    profile = profiles.get(name)
    if not isinstance(profile, dict):
        issues.append({"code": "CANDIDATE_SCORE_PROFILE_UNKNOWN", "page_id": page_id, "message": f"Unknown score profile: {name}"})
        return None
    dimensions = profile.get("dimensions")
    if not isinstance(dimensions, dict) or not dimensions:
        issues.append({"code": "CANDIDATE_SCORE_DIMENSIONS_MISSING", "page_id": page_id, "message": f"Score profile has no dimensions: {name}"})
        return None
    try:
        total = sum(int(value) for value in dimensions.values())
        declared = int(profile.get("total"))
    except (TypeError, ValueError):
        issues.append({"code": "CANDIDATE_SCORE_INVALID", "page_id": page_id, "message": f"Score profile is not numeric: {name}"})
        return None
    if total != declared:
        issues.append({"code": "CANDIDATE_SCORE_TOTAL_MISMATCH", "page_id": page_id, "message": f"Score profile {name} sums to {total}, declared {declared}."})
        return None
    return total


def _expression_profile(
    source: dict[str, Any],
    issue: Any,
    page_id: str,
) -> dict[str, object] | None:
    expression = source.get("onscreen_expression")
    form = str(expression.get("form") or "").strip() if isinstance(expression, dict) else ""
    if not form:
        issue("ONSCREEN_EXPRESSION_CONSTRAINTS_INVALID", "Visual input must declare an on-screen expression form.", page_id)
        return None
    try:
        expected = expression_constraints(form)
    except ValueError:
        issue("ONSCREEN_EXPRESSION_CONSTRAINTS_INVALID", "Visual input has an invalid on-screen expression form.", page_id)
        return None
    if source.get("expression_constraints") != expected:
        issue("ONSCREEN_EXPRESSION_CONSTRAINTS_INVALID", "Visual input expression constraints must match the registered profile.", page_id)
        return None
    return expected


def _audit_expression_fit(
    candidate: dict[str, Any],
    constraints: dict[str, object],
    issue: Any,
    page_id: str,
) -> dict[str, Any] | None:
    candidate_id = str(candidate.get("id") or "")
    fit = candidate.get("expression_fit")
    if not isinstance(fit, dict):
        issue("CANDIDATE_EXPRESSION_FIT_MISSING", f"{candidate_id} has no expression_fit receipt.", page_id)
        return None
    form = str(constraints["form"])
    status = str(fit.get("constraint_status") or "")
    satisfied = fit.get("satisfied_constraints")
    changed = fit.get("changed_constraints")
    reading_relation = str(fit.get("reading_relation") or "").strip()
    balance_strategy = str(fit.get("balance_strategy") or "").strip()
    deviation_reason = str(fit.get("deviation_reason") or "").strip()
    if (
        str(fit.get("form") or "") != form
        or status not in {"default_profile", "adapted"}
        or not isinstance(satisfied, list)
        or any(not isinstance(value, str) or not value.strip() for value in satisfied)
        or not reading_relation
        or not balance_strategy
        or not isinstance(changed, list)
        or any(not isinstance(value, str) or not value.strip() for value in changed)
    ):
        issue("CANDIDATE_EXPRESSION_FIT_INVALID", f"{candidate_id} has an invalid expression_fit receipt.", page_id)
        return None
    required_features = set(str(value) for value in constraints["required_features"])
    if not required_features.issubset(set(satisfied)) or "relation_pattern" in changed:
        issue("CANDIDATE_EXPRESSION_CORE_MISSING", f"{candidate_id} does not retain the expression profile core.", page_id)
    if status == "default_profile" and (changed or deviation_reason):
        issue("CANDIDATE_EXPRESSION_DEVIATION_INVALID", f"{candidate_id} default profile must not declare a deviation.", page_id)
    if status == "adapted" and (not changed or not deviation_reason):
        issue("CANDIDATE_EXPRESSION_DEVIATION_INVALID", f"{candidate_id} adapted profile requires changed constraints and a business reason.", page_id)
    return fit


def _required_relationships(source: dict[str, Any]) -> set[tuple[str, str, str]]:
    """Return the normalized Stage 01 business relations that need a disposition."""

    result: set[tuple[str, str, str, str]] = set()
    for item in source.get("business_relationships") or []:
        if not isinstance(item, dict):
            continue
        subject, relation = str(item.get("subject") or "").strip(), str(item.get("relation") or "").strip()
        objects = item.get("objects") if isinstance(item.get("objects"), list) else [item.get("object")]
        for value in objects:
            object_ = str(value or "").strip()
            if subject and relation and object_:
                result.add((subject, relation, object_))
    features = source.get("stage01_relationship_features")
    for item in features.get("actions") if isinstance(features, dict) and isinstance(features.get("actions"), list) else []:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject") or "").strip()
        relation = str(item.get("relation") or "").strip()
        object_ = str(item.get("object") or "").strip()
        if subject and relation and object_:
            result.add((subject, relation, object_))
    return result


def _audit_candidate_selection_rationale(candidate: dict[str, Any], issue: Any, page_id: str) -> None:
    candidate_id = str(candidate.get("id") or "")
    rationale = candidate.get("selection_rationale")
    if not isinstance(rationale, dict):
        issue("CANDIDATE_SELECTION_RATIONALE_MISSING", f"{candidate_id} has no selection rationale.", page_id)
        return
    if not str(rationale.get("mission_fit") or "").strip() or not isinstance(rationale.get("generation_feasibility"), dict):
        issue("CANDIDATE_SELECTION_RATIONALE_INVALID", f"{candidate_id} must state mission fit and generation feasibility.", page_id)


def _audit_rejection_rationale(candidate: dict[str, Any], selected: str, issue: Any, page_id: str) -> None:
    if str(candidate.get("id") or "") == selected:
        return
    rationale = str(candidate.get("rejection_rationale") or "").strip()
    specific_signal = re.search(
        r"(?:focus|relation|capacity|reading|coverage|constraint|feedback|text|evidence|焦点|关系|容量|阅读|覆盖|约束|反馈|文字|证据)",
        rationale,
        flags=re.IGNORECASE,
    )
    generic_only = re.fullmatch(r"(?:lower\s+score|得分更低|较低|美观|一般|不适合)[。.!！ ]*", rationale, flags=re.IGNORECASE)
    if not rationale or generic_only or not specific_signal:
        issue(
            "CANDIDATE_REJECTION_RATIONALE_INVALID",
            f"{candidate.get('id')!s} needs a concrete counterfactual disadvantage relative to {selected!r}.",
            page_id,
        )


def _audit_relationship_coverage(
    source: dict[str, Any],
    decision: dict[str, Any],
    expected_text_ids: list[str],
    evidence_ids: set[str],
    issue: Any,
    page_id: str,
) -> None:
    required = _required_relationships(source)
    coverage = decision.get("relationship_coverage")
    if not isinstance(coverage, list) or not coverage:
        issue("RELATIONSHIP_COVERAGE_MISSING", "Every authoritative Stage 01 relation needs a visual coverage receipt.", page_id)
        return
    covered: set[tuple[str, str, str]] = set()
    for item in coverage:
        if not isinstance(item, dict):
            issue("RELATIONSHIP_COVERAGE_INVALID", "Relationship coverage entries must be objects.", page_id)
            continue
        source_name = str(item.get("source") or "").strip()
        subject = str(item.get("subject") or "").strip()
        relation = str(item.get("relation") or "").strip()
        object_ = str(item.get("object") or "").strip()
        status = str(item.get("visual_status") or "").strip()
        evidence_refs = [str(value) for value in item.get("evidence_refs") or []]
        text_ids = [str(value) for value in item.get("text_ids") or []]
        rationale = str(item.get("rationale") or "").strip()
        triple = (subject, relation, object_)
        if (
            not str(item.get("relation_key") or "").strip()
            or source_name not in {"business_relationships", "stage01_relationship_features.actions"}
            or triple not in required
            or status not in {"primary", "secondary", "not_rendered"}
            or not rationale
            or not evidence_refs
            or not text_ids
            or set(evidence_refs) - evidence_ids
            or set(text_ids) - set(expected_text_ids)
        ):
            issue("RELATIONSHIP_COVERAGE_INVALID", f"Invalid relationship coverage receipt: {triple!r}.", page_id)
            continue
        if status == "not_rendered" and not rationale:
            issue("RELATIONSHIP_COVERAGE_NOT_RENDERED_INVALID", f"{triple!r} needs a business rationale when not rendered.", page_id)
        covered.add(triple)
    missing = sorted(required - covered)
    if missing:
        issue("RELATIONSHIP_COVERAGE_MISSING", f"Missing relationship coverage: {missing}", page_id)


_FEASIBILITY_DIMENSIONS = {
    "single_focus",
    "text_capacity",
    "relation_clarity",
    "composition_stability",
    "anti_pattern_risk",
}


def _audit_generation_feasibility(candidate: dict[str, Any], issue: Any, page_id: str) -> int | None:
    rationale = candidate.get("selection_rationale")
    feasibility = rationale.get("generation_feasibility") if isinstance(rationale, dict) else None
    if not isinstance(feasibility, dict):
        return None
    dimensions = feasibility.get("dimensions")
    try:
        score = int(feasibility.get("score"))
    except (TypeError, ValueError):
        score = -1
    if (
        not isinstance(dimensions, dict)
        or set(dimensions) != _FEASIBILITY_DIMENSIONS
        or any(not isinstance(value, int) or not 0 <= value <= 20 for value in dimensions.values())
        or sum(dimensions.values()) != 100
        or score != 100
        or not isinstance(feasibility.get("risks"), list)
    ):
        issue("CANDIDATE_GENERATION_SCORE_INVALID", f"{candidate.get('id')!s} must provide five 0–20 generation dimensions totaling 100.", page_id)
        return None
    return score


def _audit_text_capacity(candidate: dict[str, Any], expected_text_ids: list[str], evidence_ids: set[str], issue: Any, page_id: str) -> dict[str, Any] | None:
    budget = candidate.get("text_capacity_budget")
    if not isinstance(budget, dict):
        issue("TEXT_CAPACITY_MISSING", f"{candidate.get('id')!s} has no text capacity budget.", page_id)
        return None
    text_ids = [str(value) for value in budget.get("locked_text_ids") or []]
    counts = budget.get("evidence_text_counts")
    risk = str(budget.get("risk_level") or "")
    numeric_keys = ("locked_text_count", "max_lines", "max_chars_per_line")
    if (
        text_ids != expected_text_ids
        or not isinstance(counts, dict)
        or set(counts) != evidence_ids
        or any(not isinstance(value, int) or value < 0 for value in counts.values())
        or any(not isinstance(budget.get(key), int) or budget[key] < 1 for key in numeric_keys)
        or budget.get("locked_text_count") != len(expected_text_ids)
        or not str(budget.get("estimated_density") or "").strip()
        or risk not in {"low", "medium", "high", "blocking"}
        or not isinstance(budget.get("risks"), list)
    ):
        issue("TEXT_CAPACITY_INVALID", f"{candidate.get('id')!s} has an invalid text capacity budget.", page_id)
        return None
    if risk == "blocking":
        issue("TEXT_CAPACITY_BLOCKING", f"{candidate.get('id')!s} exceeds its text capacity budget.", page_id)
    return budget


def _audit_focus_competition(page_spec: dict[str, Any], issue: Any, page_id: str) -> dict[str, Any]:
    structural = page_spec.get("structural_decision") if isinstance(page_spec.get("structural_decision"), dict) else {}
    focus = structural.get("semantic_focus") if isinstance(structural.get("semantic_focus"), dict) else {}
    focus_ref = str(focus.get("ref") or "")
    p0_ids = {
        str(item.get("id") or "")
        for item in page_spec.get("evidence_units") or []
        if isinstance(item, dict) and item.get("priority") == "P0"
    }
    result_bindings = [
        binding for binding in structural.get("text_bindings") or []
        if isinstance(binding, dict) and binding.get("binding") == "result"
    ]
    result_refs = [str(binding.get("target_ref") or binding.get("evidence_id") or "") for binding in result_bindings]
    if not focus_ref or focus_ref not in p0_ids or focus_ref not in result_refs or len(result_refs) != 1:
        issue("FOCUS_COMPETITION_DETECTED", "The selected focus must be the sole P0 result-binding target.", page_id)
        return {"status": "failed", "primary_ref": focus_ref}
    return {"status": "passed", "primary_ref": focus_ref}


def audit_visual_deck_rhythm(spec: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]:
    """Audit repetition among adjacent content-page visual structures."""

    by_id, _ = _index_pages(decisions.get("pages"))
    pages = [page for page in spec.get("pages") or [] if isinstance(page, dict) and str(page.get("page_role") or "") != "chapter"]
    signatures: list[tuple[str, tuple[object, ...], str]] = []
    for page in pages:
        structural = page.get("structural_decision") if isinstance(page.get("structural_decision"), dict) else {}
        focus = structural.get("semantic_focus") if isinstance(structural.get("semantic_focus"), dict) else {}
        bindings = tuple(sorted(str(item.get("binding") or "") for item in structural.get("text_bindings") or [] if isinstance(item, dict)))
        signature = (
            str(page.get("visual_decision", {}).get("visual_intent_type") or ""),
            tuple(sorted(str(value) for value in structural.get("spatial_grammar") or [])),
            str(focus.get("kind") or ""),
            str(page.get("semantic_graph", {}).get("direction") or ""),
            bindings,
        )
        signatures.append((normalize_page_id(page.get("page_id")), signature, str(by_id.get(normalize_page_id(page.get("page_id")), {}).get("rhythm_exception_reason") or "").strip()))
    blocking, warnings = [], []
    for index in range(len(signatures) - 1):
        left, right = signatures[index], signatures[index + 1]
        if left[1] == right[1]:
            warnings.append({"code": "DECK_RHYTHM_REPETITION_WARNING", "page_ids": [left[0], right[0]], "message": "Adjacent content pages have the same visual structure signature.", "exception_reason": right[2]})
    for index in range(len(signatures) - 2):
        group = signatures[index:index + 3]
        if group[0][1] == group[1][1] == group[2][1]:
            blocking.append({"code": "DECK_RHYTHM_REPETITION_BLOCKING", "page_ids": [item[0] for item in group], "message": "Three adjacent content pages repeat the same visual structure signature."})
    return {"status": "failed" if blocking else "passed", "blocking_issues": blocking, "warnings": warnings}


def audit_visual_design_package(
    design_input_path: Path,
    decisions_path: Path,
    spec_path: Path,
) -> dict[str, Any]:
    """Cross-audit candidates, page coverage, locked copy, and exact text IDs."""

    design_input = _read_json(design_input_path)
    decisions = _read_json(decisions_path)
    spec = _read_json(spec_path)
    issues: list[dict[str, Any]] = []

    def issue(code: str, message: str, page_id: str | None = None) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if page_id:
            item["page_id"] = page_id
        issues.append(item)

    if design_input.get("schema") != "cyberppt.visual_design_input.v2":
        issue("VISUAL_DESIGN_INPUT_SCHEMA_INVALID", "visual-design-input.json must use cyberppt.visual_design_input.v2.")
    if decisions.get("schema") != "cyberppt.visual_design_decisions.v3":
        issue("VISUAL_DECISIONS_SCHEMA_INVALID", "visual-design-decisions.json must use cyberppt.visual_design_decisions.v3.")
    if decisions.get("source_sha256") != sha256(design_input_path):
        issue("VISUAL_DECISIONS_INPUT_STALE", "Visual decisions are not bound to the current visual-design-input.json.")

    input_pages, input_duplicates = _index_pages(design_input.get("pages"))
    decision_pages, decision_duplicates = _index_pages(decisions.get("pages"))
    spec_pages, spec_duplicates = _index_pages(spec.get("pages"))
    for label, duplicates in (
        ("input", input_duplicates),
        ("decisions", decision_duplicates),
        ("spec", spec_duplicates),
    ):
        if duplicates:
            issue("VISUAL_PAGE_DUPLICATE", f"Duplicate {label} page ids: {sorted(set(duplicates))}")
    expected_ids = list(input_pages)
    for label, pages in (("decisions", decision_pages), ("spec", spec_pages)):
        if set(pages) != set(input_pages):
            issue(
                "VISUAL_PAGE_SET_MISMATCH",
                f"{label} page set differs from input: missing={sorted(set(input_pages) - set(pages))}, extra={sorted(set(pages) - set(input_pages))}",
            )

    profiles = decisions.get("score_profiles")
    if not isinstance(profiles, dict):
        profiles = {}
        issue("CANDIDATE_SCORE_PROFILES_MISSING", "Decision receipt has no score_profiles object.")

    for page_id in expected_ids:
        source = input_pages[page_id]
        decision = decision_pages.get(page_id)
        page_spec = spec_pages.get(page_id)
        if decision is None or page_spec is None:
            continue

        relationships = source.get("business_relationships")
        if not isinstance(relationships, list) or not relationships:
            issue("BUSINESS_RELATIONSHIPS_MISSING", "Authoritative business relationships are missing.", page_id)
        if source.get("author_visual_notes_authority") != "advisory_only":
            issue("AUTHOR_VISUAL_NOTES_AUTHORITY_INVALID", "Author visual notes must be advisory_only.", page_id)
        features = source.get("stage01_relationship_features")
        if not isinstance(features, dict) or not isinstance(features.get("actions"), list) or not features.get("actions"):
            issue("STAGE01_RELATIONSHIP_FEATURES_MISSING", "Structured Stage 01 relationship features are missing.", page_id)

        expression = source.get("onscreen_expression")
        constraints = _expression_profile(source, issue, page_id)
        if isinstance(expression, dict) and str(expression.get("form") or "").strip():
            disposition = decision.get("onscreen_expression_disposition")
            if not isinstance(disposition, dict):
                issue("ONSCREEN_EXPRESSION_DISPOSITION_MISSING", "Decision receipt must explain how the on-screen expression form shaped visual reading order and balance.", page_id)
            elif (
                str(disposition.get("form") or "").strip() != str(expression.get("form") or "").strip()
                or not str(disposition.get("reading_relation") or "").strip()
                or not str(disposition.get("balance_strategy") or "").strip()
            ):
                issue("ONSCREEN_EXPRESSION_DISPOSITION_INVALID", "Expression disposition must preserve the received form and state a reading relation plus balance strategy.", page_id)

        disposition = decision.get("stage01_visual_note_disposition")
        if not isinstance(disposition, dict):
            issue("STAGE01_VISUAL_NOTE_DISPOSITION_MISSING", "Decision receipt must explain how Stage 01 visual guidance was inherited, adjusted, or rejected.", page_id)
        else:
            disposition_items: list[Any] = []
            for key in ("inherited", "adjusted", "rejected"):
                values = disposition.get(key)
                if not isinstance(values, list):
                    issue("STAGE01_VISUAL_NOTE_DISPOSITION_INVALID", f"Disposition field {key} must be an array.", page_id)
                    continue
                disposition_items.extend(values)
            if not disposition_items:
                issue("STAGE01_VISUAL_NOTE_DISPOSITION_EMPTY", "At least one Stage 01 visual feature must be dispositioned.", page_id)
            for item in disposition_items:
                if not isinstance(item, dict) or not str(item.get("feature") or "").strip() or not str(item.get("reason") or "").strip():
                    issue("STAGE01_VISUAL_NOTE_DISPOSITION_ITEM_INVALID", "Every disposition item requires feature and reason.", page_id)

        expected_lock = _locked_pairs(source)
        expected_text_ids = [item[0] for item in expected_lock]
        expected_text = [item[1] for item in expected_lock]
        if not expected_lock or any(not item_id or not text for item_id, text in expected_lock):
            issue("LOCKED_TEXT_ITEMS_INVALID", "Locked body-text items must have non-empty ids and text.", page_id)
        if len(expected_text_ids) != len(set(expected_text_ids)):
            issue("LOCKED_TEXT_IDS_DUPLICATE", "Locked body-text ids must be unique.", page_id)

        evidence = decision.get("evidence_units")
        evidence = evidence if isinstance(evidence, list) else []
        if len(evidence) > 7:
            issue(
                "EVIDENCE_UNITS_TOO_MANY",
                "The executable visual-spec schema allows at most seven evidence units; group contiguous locked copy into business evidence units.",
                page_id,
            )
        evidence_keys = [str(item.get("key") or "") for item in evidence if isinstance(item, dict)]
        if not evidence_keys or any(not value for value in evidence_keys) or len(evidence_keys) != len(set(evidence_keys)):
            issue("DECISION_EVIDENCE_KEYS_INVALID", "Decision evidence keys must be non-empty and unique.", page_id)
        evidence_key_set = set(evidence_keys)

        candidates = decision.get("candidates")
        candidates = candidates if isinstance(candidates, list) else []
        if len(candidates) < 3:
            issue("CANDIDATE_COUNT_INSUFFICIENT", "At least three candidate receipts are required.", page_id)
        signatures: set[tuple[Any, ...]] = set()
        candidate_scores: dict[str, int] = {}
        candidate_ids: set[str] = set()
        candidate_records: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            if not isinstance(candidate, dict):
                issue("CANDIDATE_INVALID", "Candidate receipt must be an object.", page_id)
                continue
            candidate_id = str(candidate.get("id") or "")
            if not candidate_id or candidate_id in candidate_ids:
                issue("CANDIDATE_ID_INVALID", f"Candidate id is empty or duplicated: {candidate_id!r}", page_id)
            candidate_ids.add(candidate_id)
            candidate_records[candidate_id] = candidate
            visual_thesis = str(candidate.get("visual_thesis") or "").strip()
            if len(visual_thesis) < 8:
                issue(
                    "CANDIDATE_VISUAL_THESIS_MISSING",
                    f"{candidate_id} must state the visible relationship that proves the page judgment.",
                    page_id,
                )
            focus = candidate.get("semantic_focus") if isinstance(candidate.get("semantic_focus"), dict) else {}
            focus_key = str(focus.get("evidence_key") or "")
            if focus_key not in evidence_key_set:
                issue("CANDIDATE_FOCUS_UNKNOWN", f"{candidate_id} references unknown focus {focus_key!r}.", page_id)
            sequence = [str(value) for value in candidate.get("reading_sequence") or []]
            if len(sequence) != len(set(sequence)) or set(sequence) != evidence_key_set:
                issue("CANDIDATE_EVIDENCE_COVERAGE", f"{candidate_id} must cover every evidence key exactly once.", page_id)
            signature = (
                str(candidate.get("visual_intent_type") or ""),
                str(focus.get("kind") or ""),
                focus_key,
                tuple(str(value) for value in candidate.get("spatial_grammar") or []),
                str(candidate.get("direction") or ""),
                tuple(sequence),
            )
            if signature in signatures:
                issue("CANDIDATE_STRUCTURE_DUPLICATE", f"{candidate_id} is not materially different from another candidate.", page_id)
            signatures.add(signature)
            if constraints is not None:
                _audit_expression_fit(candidate, constraints, issue, page_id)
            _audit_candidate_selection_rationale(candidate, issue, page_id)
            _audit_generation_feasibility(candidate, issue, page_id)
            score = _profile_total(profiles, str(candidate.get("score_profile") or ""), issues, page_id)
            if score is not None:
                candidate_scores[candidate_id] = score
        selected = str(decision.get("selected_candidate") or "")
        if selected not in candidate_ids:
            issue("SELECTED_CANDIDATE_MISSING", f"Selected candidate does not exist: {selected!r}", page_id)
        elif candidate_scores and candidate_scores.get(selected) != max(candidate_scores.values()):
            issue("SELECTED_CANDIDATE_NOT_HIGHEST", "Selected candidate must have the highest validated score.", page_id)

        for candidate in candidate_records.values():
            _audit_rejection_rationale(candidate, selected, issue, page_id)
            _audit_text_capacity(candidate, expected_text_ids, evidence_key_set, issue, page_id)

        execution_design = decision.get("execution_design")
        required_execution_text = (
            "business_object",
            "visual_focus",
            "text_integration_method",
            "spatial_organization",
            "relationship_encoding",
            "semantic_role",
            "scene_type",
        )
        if not isinstance(execution_design, dict) or any(
            not str(execution_design.get(key) or "").strip()
            for key in required_execution_text
        ) or not isinstance(execution_design.get("use_scene"), bool):
            issue(
                "EXECUTION_DESIGN_INVALID",
                "Selected execution design must preserve its carrier, scene policy, semantic role, composition, and text integration.",
                page_id,
            )

        if selected in candidate_records:
            selected_candidate = candidate_records[selected]
            visual_decision = page_spec.get("visual_decision")
            actual_thesis = (
                str(visual_decision.get("visual_thesis") or "").strip()
                if isinstance(visual_decision, dict)
                else ""
            )
            expected_thesis = str(selected_candidate.get("visual_thesis") or "").strip()
            if actual_thesis != expected_thesis:
                issue(
                    "SPEC_VISUAL_THESIS_DRIFTED",
                    "Spec visual thesis must match the selected Stage 02 candidate.",
                    page_id,
                )
            if isinstance(execution_design, dict):
                image_plan = page_spec.get("image_plan")
                image_plan = image_plan if isinstance(image_plan, dict) else {}
                expected_scene = {
                    "business_object": execution_design.get("business_object"),
                    "semantic_role": execution_design.get("semantic_role"),
                    "use_scene": execution_design.get("use_scene"),
                    "scene_type": execution_design.get("scene_type"),
                }
                actual_scene = {key: image_plan.get(key) for key in expected_scene}
                if actual_scene != expected_scene:
                    issue(
                        "SPEC_SCENE_POLICY_DRIFTED",
                        "Spec image plan must match the selected carrier and scene policy.",
                        page_id,
                    )
                visual_decision = page_spec.get("visual_decision")
                visual_decision = visual_decision if isinstance(visual_decision, dict) else {}
                hierarchy = visual_decision.get("visual_hierarchy")
                hierarchy = hierarchy if isinstance(hierarchy, dict) else {}
                expected_execution = {
                    "visual_focus": execution_design.get("visual_focus"),
                    "spatial_organization": execution_design.get("spatial_organization"),
                    "text_integration_method": execution_design.get("text_integration_method"),
                    "relationship_encoding": execution_design.get("relationship_encoding"),
                    "placement": execution_design.get("spatial_organization"),
                }
                actual_execution = {
                    "visual_focus": hierarchy.get("primary"),
                    "spatial_organization": visual_decision.get("spatial_organization"),
                    "text_integration_method": visual_decision.get("text_integration_method"),
                    "relationship_encoding": visual_decision.get("relationship_encoding"),
                    "placement": image_plan.get("placement"),
                }
                if actual_execution != expected_execution:
                    issue(
                        "SPEC_EXECUTION_DESIGN_DRIFTED",
                        "Spec composition must match the selected executable design.",
                        page_id,
                    )

        if constraints is not None and selected in candidate_records:
            selected_fit = candidate_records[selected].get("expression_fit")
            contract = page_spec.get("expression_contract")
            if not isinstance(contract, dict):
                issue("SPEC_EXPRESSION_CONTRACT_MISSING", "Spec must retain the selected expression contract.", page_id)
            elif not isinstance(selected_fit, dict):
                # The candidate-specific diagnostic above is the authoritative
                # explanation; do not fabricate a comparison from missing data.
                pass
            else:
                expected_contract = {
                    "form": constraints["form"],
                    "constraints_sha256": expression_constraints_sha256(constraints),
                    "selected_candidate_id": selected,
                    "fit_status": selected_fit.get("constraint_status"),
                    "reading_relation": selected_fit.get("reading_relation"),
                    "balance_strategy": selected_fit.get("balance_strategy"),
                    "deviation_reason": selected_fit.get("deviation_reason"),
                }
                if contract != expected_contract:
                    issue("SPEC_EXPRESSION_CONTRACT_DRIFTED", "Spec expression contract must match the input profile and selected candidate receipt.", page_id)

        locked_items = page_spec.get("content_lock", {}).get("locked_items", [])
        actual_body_lock = [
            (str(item.get("id") or ""), str(item.get("text") or ""))
            for item in locked_items
            if isinstance(item, dict) and item.get("type") == "body"
        ]
        if actual_body_lock != expected_lock:
            issue("SPEC_CONTENT_LOCK_DRIFTED", "Spec body lock must match the input text ids and text exactly and in order.", page_id)
        final_text = [
            (str(item.get("id") or ""), str(item.get("text") or ""))
            for item in page_spec.get("final_text") or []
            if isinstance(item, dict)
        ]
        if final_text != expected_lock:
            issue("SPEC_FINAL_TEXT_DRIFTED", "final_text must match the input text ids and text exactly and in order.", page_id)
        handoff = page_spec.get("generation_handoff") if isinstance(page_spec.get("generation_handoff"), dict) else {}
        if [str(value) for value in handoff.get("required_text_ids") or []] != expected_text_ids:
            issue("SPEC_REQUIRED_TEXT_IDS_DRIFTED", "required_text_ids must match every locked body-text id in order.", page_id)
        if [str(value) for value in handoff.get("required_text") or []] != expected_text:
            issue("SPEC_REQUIRED_TEXT_DRIFTED", "required_text must match every locked body string in order.", page_id)

        graph_evidence_ids = {
            str(item.get("id") or "")
            for item in page_spec.get("evidence_units") or []
            if isinstance(item, dict)
        }
        bound_text_ids: list[str] = []
        bound_evidence_ids: set[str] = set()
        structural = page_spec.get("structural_decision") if isinstance(page_spec.get("structural_decision"), dict) else {}
        for binding in structural.get("text_bindings") or []:
            if not isinstance(binding, dict):
                continue
            evidence_id = str(binding.get("evidence_id") or "")
            if evidence_id not in graph_evidence_ids:
                issue("TEXT_BINDING_EVIDENCE_UNKNOWN", f"Unknown binding evidence id: {evidence_id}", page_id)
            bound_evidence_ids.add(evidence_id)
            text_ids = [str(value) for value in binding.get("text_ids") or []]
            if not text_ids:
                issue("TEXT_BINDING_IDS_MISSING", f"{evidence_id} has no exact locked text ids.", page_id)
            bound_text_ids.extend(text_ids)
        unknown_text_ids = sorted(set(bound_text_ids) - set(expected_text_ids))
        if unknown_text_ids:
            issue("TEXT_BINDING_ID_UNKNOWN", f"Bindings contain unknown text ids: {unknown_text_ids}", page_id)
        duplicates = sorted({value for value in bound_text_ids if bound_text_ids.count(value) > 1})
        if duplicates:
            issue("TEXT_BINDING_ID_DUPLICATE", f"Locked text ids are bound more than once: {duplicates}", page_id)
        missing_text_ids = [value for value in expected_text_ids if value not in set(bound_text_ids)]
        if missing_text_ids:
            issue("TEXT_BINDING_ID_MISSING", f"Locked text ids are not bound: {missing_text_ids}", page_id)
        p0_evidence_ids = {
            str(item.get("id") or "")
            for item in page_spec.get("evidence_units") or []
            if isinstance(item, dict) and item.get("priority") == "P0"
        }
        if p0_evidence_ids - bound_evidence_ids:
            issue("P0_TEXT_BINDING_MISSING", f"P0 evidence has no exact text binding: {sorted(p0_evidence_ids - bound_evidence_ids)}", page_id)

        _audit_focus_competition(page_spec, issue, page_id)

        _audit_relationship_coverage(
            source,
            decision,
            expected_text_ids,
            graph_evidence_ids,
            issue,
            page_id,
        )

        author_notes = str(source.get("author_visual_notes") or "").strip()
        decision_relationship = str(page_spec.get("semantic_graph", {}).get("decision_relationship") or "").strip()
        if author_notes and decision_relationship == author_notes:
            issue("LAYOUT_NOTES_USED_AS_RELATION", "decision_relationship must not copy advisory author visual notes.", page_id)

    return {
        "schema": "cyberppt.visual_design_package_audit.v1",
        "status": "passed" if not issues else "failed",
        "page_count": len(input_pages),
        "candidate_page_count": len(decision_pages),
        "spec_page_count": len(spec_pages),
        "blocking_issues": issues,
    }
