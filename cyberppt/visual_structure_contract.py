"""Shared contracts for the Stage 02 visual-structure decision package."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


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
    if decisions.get("schema") != "cyberppt.visual_design_decisions.v2":
        issue("VISUAL_DECISIONS_SCHEMA_INVALID", "visual-design-decisions.json must use cyberppt.visual_design_decisions.v2.")
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
        for candidate in candidates:
            if not isinstance(candidate, dict):
                issue("CANDIDATE_INVALID", "Candidate receipt must be an object.", page_id)
                continue
            candidate_id = str(candidate.get("id") or "")
            if not candidate_id or candidate_id in candidate_ids:
                issue("CANDIDATE_ID_INVALID", f"Candidate id is empty or duplicated: {candidate_id!r}", page_id)
            candidate_ids.add(candidate_id)
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
            score = _profile_total(profiles, str(candidate.get("score_profile") or ""), issues, page_id)
            if score is not None:
                candidate_scores[candidate_id] = score
        selected = str(decision.get("selected_candidate") or "")
        if selected not in candidate_ids:
            issue("SELECTED_CANDIDATE_MISSING", f"Selected candidate does not exist: {selected!r}", page_id)
        elif candidate_scores and candidate_scores.get(selected) != max(candidate_scores.values()):
            issue("SELECTED_CANDIDATE_NOT_HIGHEST", "Selected candidate must have the highest validated score.", page_id)

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
