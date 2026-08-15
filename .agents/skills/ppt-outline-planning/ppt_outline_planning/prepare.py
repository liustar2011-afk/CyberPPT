from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any


REQUIRED_FILES = (
    "normalized-facts.json",
    "concept-base.json",
    "relation-graph.json",
    "argument-chain.json",
    "semantic-report.json",
)

DEFAULT_PLANNING_POLICY: dict[str, Any] = {
    "one_page_one_core_point": True,
    "cyberppt_ready_page_boundary_contract": True,
    "audience_question_distinct_from_page_mission": True,
    "evidence_roles_required": ["claim", "reason", "instance", "boundary", "trace_only"],
    "cross_page_leakage_guards_required": True,
    "writing_style_mode": "government_official",
    "source_structure_mode": "locked",
    "source_title_mode": "locked",
    "source_order_mode": "locked",
    "source_content_mode": "preserve",
    "capacity_split_allowed": True,
    "duplicate_content_merge_allowed": True,
    "explicit_merge_group_required": True,
    "attachment_default_disposition": "trace_only",
    "attachment_main_deck_requires_author_decision": True,
    "page_budget_is_authoring_constraint": True,
    "reframing_requires_explicit_user_request": True,
    "agenda_mode": "source_sections_only",
    "may_bridge_logic_gaps_only_when_inference_is_labeled": True,
    "new_source_facts_forbidden": True,
    "template_pages_have_no_business_body_content": True,
    "final_on_screen_copy_forbidden": True,
    "detailed_visual_design_forbidden": True,
}

OVERRIDABLE_POLICY_FIELDS = frozenset(
    {
        "writing_style_mode",
        "source_structure_mode",
        "source_title_mode",
        "source_order_mode",
        "source_content_mode",
        "capacity_split_allowed",
        "duplicate_content_merge_allowed",
        "agenda_mode",
    }
)

REFRAMING_TERMS = (
    "重构叙事",
    "重组叙事",
    "咨询式表达",
    "咨询化表达",
    "路演式表达",
    "路演化表达",
    "压缩重组",
)


def _json_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _compact_fact(item: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "normalized_fact_id",
        "statement",
        "fact_type",
        "verification_status",
        "confidence",
    )
    return {key: deepcopy(item.get(key)) for key in keys if key in item}


def _compact_concept(item: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "concept_id",
        "canonical_name",
        "aliases",
        "concept_type",
        "definition",
        "normalized_fact_ids",
        "confidence",
    )
    return {key: deepcopy(item.get(key)) for key in keys if key in item}


def _compact_relation(item: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "relation_id",
        "from_concept_id",
        "relation_type",
        "to_concept_id",
        "basis",
        "normalized_fact_ids",
        "confidence",
        "inference_rationale",
    )
    return {key: deepcopy(item.get(key)) for key in keys if key in item}


def _validate_artifacts(payloads: dict[str, dict[str, Any]]) -> None:
    expected_types = {
        "normalized-facts.json": "normalized_facts",
        "concept-base.json": "concept_base",
        "relation-graph.json": "relation_graph",
        "argument-chain.json": "argument_chain",
        "semantic-report.json": "semantic_validation_report",
    }
    for name, artifact_type in expected_types.items():
        payload = payloads.get(name)
        if payload is None:
            raise FileNotFoundError(f"Missing layer-three artifact: {name}")
        if payload.get("artifact_type") != artifact_type:
            raise ValueError(f"{name} is not a {artifact_type} artifact")
    if payloads["semantic-report.json"].get("status") != "ok":
        raise ValueError("semantic-report.json must report status: ok before PPT outline planning")


def _request_payload(
    request: dict[str, Any] | None,
    request_text: str | None,
) -> dict[str, Any]:
    if request is not None:
        return {"mode": "structured", "data": deepcopy(request)}
    if request_text is not None:
        return {"mode": "text", "text": request_text}
    return {
        "mode": "conversation",
        "note": "Use the current user task and conversation constraints; record unresolved assumptions in deck-brief.json.",
    }


def _normalized_request_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def _explicit_reframing_request(request_text: str) -> bool:
    text = _normalized_request_text(request_text)
    if not text:
        return False
    terms = "|".join(re.escape(term) for term in REFRAMING_TERMS)
    if re.search(rf"(?:不要|不得|禁止|不允许|无需|不需).{{0,10}}(?:{terms})", text):
        return False
    patterns = (
        rf"(?:请|需要|要求|允许).{{0,10}}(?:{terms})",
        rf"(?:改为|改成|采用|按照|使用).{{0,6}}(?:咨询式|咨询化|路演式|路演化)",
        rf"(?:{terms})",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _resolve_planning_policy(
    request: dict[str, Any] | None,
    request_text: str | None,
) -> dict[str, Any]:
    policy = deepcopy(DEFAULT_PLANNING_POLICY)
    if request is not None:
        requested_policy = request.get("planning_policy")
        if not isinstance(requested_policy, dict):
            requested_policy = request
        provided = set()
        for key, value in requested_policy.items():
            if key in OVERRIDABLE_POLICY_FIELDS:
                policy[key] = deepcopy(value)
                provided.add(key)
        if policy.get("source_structure_mode") == "flexible":
            if "source_title_mode" not in provided:
                policy["source_title_mode"] = "flexible"
            if "source_order_mode" not in provided:
                policy["source_order_mode"] = "flexible"
            if "agenda_mode" not in provided:
                policy["agenda_mode"] = "planned_sections"
        return policy

    if request_text and _explicit_reframing_request(request_text):
        policy["source_structure_mode"] = "flexible"
        policy["source_title_mode"] = "flexible"
        policy["source_order_mode"] = "flexible"
        policy["agenda_mode"] = "planned_sections"
        text = _normalized_request_text(request_text)
        if "咨询式" in text or "咨询化" in text:
            policy["writing_style_mode"] = "consulting"
        if "压缩重组" in text:
            policy["source_content_mode"] = "selective"
    return policy


def _flatten_source_outline(source_structure: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(source_structure, dict):
        return []
    flattened: list[dict[str, Any]] = []

    def visit(items: Any, parent_id: str | None = None) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict) or not item.get("section_id"):
                continue
            compact = {
                "section_id": str(item["section_id"]),
                "order": len(flattened) + 1,
                "level": int(item.get("level") or 0),
                "title": str(item.get("title") or ""),
                "line": item.get("line"),
                "parent_id": parent_id,
            }
            flattened.append(compact)
            visit(item.get("children"), compact["section_id"])

    visit(source_structure.get("outline"))
    return flattened


def _source_metadata(normalized: dict[str, Any]) -> dict[str, Any]:
    agenda_title = "目录"
    for item in normalized.get("facts") or []:
        if not isinstance(item, dict):
            continue
        statement = str(item.get("statement") or "")
        if re.sub(r"[\s　]+", "", statement) == "目录":
            agenda_title = "目录"
            break
    return {"agenda_title": agenda_title}


def build_outline_workpack(
    payloads: dict[str, dict[str, Any]],
    *,
    request: dict[str, Any] | None = None,
    request_text: str | None = None,
    source_structure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if request is not None and request_text is not None:
        raise ValueError("request and request_text are mutually exclusive")
    _validate_artifacts(payloads)

    normalized = payloads["normalized-facts.json"]
    concepts = payloads["concept-base.json"]
    relations = payloads["relation-graph.json"]
    argument = payloads["argument-chain.json"]
    report = payloads["semantic-report.json"]
    request_payload = _request_payload(request, request_text)
    planning_policy = _resolve_planning_policy(request, request_text)

    binding = {
        "request_sha256": _json_sha256(request_payload),
        "planning_policy_sha256": _json_sha256(planning_policy),
    }
    if source_structure is not None:
        binding["source_structure_sha256"] = _json_sha256(source_structure)

    return {
        "schema_version": "1.1",
        "artifact_type": "ppt_outline_workpack",
        "source": deepcopy(normalized.get("source", {})),
        "semantic": {
            "validated": True,
            "report_status": report.get("status"),
            "counts": deepcopy(report.get("counts", {})),
            "warnings": deepcopy(report.get("warnings", [])),
            "artifact_sha256": {
                name: _json_sha256(payloads[name]) for name in REQUIRED_FILES
            },
        },
        "request": request_payload,
        "binding": binding,
        "source_metadata": _source_metadata(normalized),
        "source_heading_outline": _flatten_source_outline(source_structure),
        "planning_index": {
            "normalized_facts": [
                _compact_fact(item) for item in normalized.get("facts", [])
            ],
            "conflicts": deepcopy(normalized.get("conflicts", [])),
            "ambiguities": deepcopy(normalized.get("ambiguities", [])),
            "concepts": [
                _compact_concept(item) for item in concepts.get("concepts", [])
            ],
            "relations": [
                _compact_relation(item) for item in relations.get("relations", [])
            ],
            "source_chain": deepcopy(argument.get("source_chain", [])),
            "reconstructed_chain": deepcopy(argument.get("reconstructed_chain", [])),
            "diagnostics": deepcopy(argument.get("diagnostics", [])),
        },
        "planning_policy": planning_policy,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _standard_source_structure_path(semantic: Path) -> Path:
    return semantic.parent.parent / "foundation" / semantic.name / "structure.json"


def prepare_outline_workpack(
    semantic_dir: Path | str,
    output_dir: Path | str,
    *,
    request: dict[str, Any] | None = None,
    request_text: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if request is not None and request_text is not None:
        raise ValueError("request and request_text are mutually exclusive")
    semantic = Path(semantic_dir)
    output = Path(output_dir)
    payloads: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_FILES:
        path = semantic / name
        if not path.is_file():
            raise FileNotFoundError(f"Missing layer-three artifact: {path}")
        payloads[name] = _read_json(path)

    source_structure_path = _standard_source_structure_path(semantic)
    source_structure = (
        _read_json(source_structure_path) if source_structure_path.is_file() else None
    )
    workpack_path = output / "outline-workpack.json"
    if workpack_path.exists() and not force:
        raise FileExistsError(f"Outline workpack already exists: {workpack_path}")
    workpack = build_outline_workpack(
        payloads,
        request=request,
        request_text=request_text,
        source_structure=source_structure,
    )
    output.mkdir(parents=True, exist_ok=True)
    _write_json(workpack_path, workpack)
    return {
        "status": "prepared",
        "semantic": str(semantic),
        "output": str(output),
        "workpack": str(workpack_path),
        "semantic_counts": workpack["semantic"]["counts"],
        "source_structure": str(source_structure_path) if source_structure else None,
    }
