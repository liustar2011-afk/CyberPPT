from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import re
from typing import Any

from .prepare import REQUIRED_FILES, _json_sha256
from .authoring import authoring_issues
from .status import build_layer4_status

REPORT_SCHEMA_VERSION="1.0"
EVIDENCE_ROLE_KEYS=("claim","reason","instance","boundary","trace_only")
FACT_DISPOSITION_VALUES={"page","shared","detail","trace","deferred_to","intentional_omission"}
NON_CONTENT_FACT_TYPES={"metadata","trace","trace_only","attachment","attachment_reference","reference","administrative"}
FORBIDDEN_DOWNSTREAM_FIELDS={"body_text","final_copy","screen_text","bullets","speaker_notes","image_prompt","layout","colors","fonts"}
ARGUMENT_CHAIN_ROLES={"premise","driver","background","problem","cause","constraint","gap","response","claim","reason","instance","mechanism","condition","consequence","judgment","conclusion","recommendation","implementation","support","detail","boundary","evidence","other"}

def _read(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def _write(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def _err(items:list[dict[str,Any]],code:str,message:str,**ctx:Any)->None: items.append({"code":code,"message":message,"context":ctx})
def _warn(items:list[dict[str,Any]],code:str,message:str,**ctx:Any)->None: items.append({"code":code,"message":message,"context":ctx})
def _scan(value:Any,errors:list[dict[str,Any]],path:str="")->None:
    if isinstance(value,dict):
        for key,child in value.items():
            p=f"{path}.{key}" if path else key
            if key in FORBIDDEN_DOWNSTREAM_FIELDS: _err(errors,"forbidden_downstream_field","Outline planning must stop before script copy or detailed visual design.",field=key,path=p)
            _scan(child,errors,p)
    elif isinstance(value,list):
        for i,child in enumerate(value): _scan(child,errors,f"{path}[{i}]")
def _semantic(semantic:Path)->tuple[dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any]]:
    files=["normalized-facts.json","concept-base.json","relation-graph.json","argument-chain.json","semantic-report.json"]
    values=[]
    for name in files:
        path=semantic/name
        if not path.is_file(): raise FileNotFoundError(f"Missing layer-three artifact: {path}")
        values.append(_read(path))
    return tuple(values)  # type: ignore[return-value]


def _semantic_binding_issues(
    plan: dict[str, Any],
    argument: dict[str, Any],
    concepts: dict[str, Any],
    relations: dict[str, Any],
) -> list[dict[str, Any]]:
    if plan.get("semantic_argument_model_mode") != "required":
        return []
    errors: list[dict[str, Any]] = []
    registry = {
        str(item.get("id")): item
        for item in plan.get("argument_node_registry") or []
        if isinstance(item, dict) and item.get("id")
    }
    for group in (argument.get("source_chain") or [], argument.get("reconstructed_chain") or []):
        for item in group:
            if not isinstance(item, dict) or not item.get("node_id"):
                continue
            node_id = str(item["node_id"])
            registry.setdefault(
                node_id,
                {
                    "id": node_id,
                    "argument_role": item.get("argument_role") or item.get("role") or "other",
                    "argument_weight": item.get("argument_weight") or "detail",
                    "status": item.get("status") or "mixed",
                    "evidence_refs": list(item.get("normalized_fact_ids") or []),
                },
            )
    concept_ids = {
        str(item.get("concept_id"))
        for item in concepts.get("concepts") or []
        if isinstance(item, dict) and item.get("concept_id")
    }
    relation_by_id = {
        str(item.get("relation_id")): item
        for item in relations.get("relations") or []
        if isinstance(item, dict) and item.get("relation_id")
    }
    pages = [item for item in plan.get("pages") or [] if isinstance(item, dict) and item.get("page_type") == "content"]
    for page in pages:
        page_id = str(page.get("page_id") or "?")
        primary = str(page.get("primary_argument_node_id") or "")
        assigned = [str(value) for value in page.get("source_argument_node_ids") or [] if str(value)]
        if not primary or not assigned:
            _err(errors, "semantic_argument_binding_missing", "内容页必须绑定主论点节点和消费节点列表", page_id=page_id)
            continue
        if primary not in assigned:
            _err(errors, "semantic_primary_argument_unassigned", "主论点节点必须包含在页面消费节点列表中", page_id=page_id)
        unknown = sorted(set(assigned) - set(registry))
        if unknown:
            _err(errors, "semantic_argument_node_unknown", "页面引用了未登记的层三论点节点", page_id=page_id, node_ids=unknown)
        for field in ("source_argument_node_roles", "source_argument_node_weights", "source_argument_node_statuses"):
            values = page.get(field)
            if not isinstance(values, dict) or set(assigned) - set(str(key) for key in values):
                _err(errors, "semantic_argument_metadata_missing", "页面必须复制所消费论点节点的角色、权重和状态", page_id=page_id, field=field)
        derivation = page.get("core_message_derivation") or page.get("judgment_derivation")
        if not isinstance(derivation, dict) or not set(assigned).issubset({str(value) for value in derivation.get("argument_node_ids") or []}):
            _err(errors, "semantic_argument_derivation_missing", "页面核心判断推导必须覆盖全部页面论点节点", page_id=page_id)
        evidence = page.get("evidence") if isinstance(page.get("evidence"), dict) else {}
        direct_fact_ids = {str(value) for value in evidence.get("normalized_fact_ids") or []}
        page_concept_ids = [str(value) for value in evidence.get("concept_ids") or [] if str(value)]
        unknown_concepts = sorted(set(page_concept_ids) - concept_ids)
        if unknown_concepts:
            _err(errors, "unknown_concept", "页面引用了不存在的概念节点", page_id=page_id, concept_ids=unknown_concepts)
        relation_ids = [str(value) for value in evidence.get("relation_ids") or [] if str(value)]
        unknown_relations = sorted(set(relation_ids) - set(relation_by_id))
        if unknown_relations:
            _err(errors, "unknown_relation", "页面引用了不存在的关系节点", page_id=page_id, relation_ids=unknown_relations)
        for relation_id in relation_ids:
            relation = relation_by_id.get(relation_id) or {}
            relation_fact_ids = {str(value) for value in relation.get("normalized_fact_ids") or []}
            if not relation_fact_ids.issubset(direct_fact_ids):
                _err(errors, "relation_fact_outside_page", "页面关系只能消费页面已声明的直接事实", page_id=page_id, relation_id=relation_id)
            if relation.get("basis") == "inferred" and not str(evidence.get("inference_note") or "").strip():
                _err(errors, "inferred_relation_note_missing", "页面消费推断关系时必须保留上游推断说明", page_id=page_id, relation_id=relation_id)
    try:
        from cyberppt.source_argument_model import audit_outline_consumption

        model_nodes = []
        page_consumers: dict[str, list[str]] = {}
        for page in pages:
            for node_id in page.get("source_argument_node_ids") or []:
                page_consumers.setdefault(str(node_id), []).append(str(page.get("page_id") or ""))
        for node_id, node in registry.items():
            consumers = page_consumers.get(node_id, [])
            model_nodes.append({
                "id": node_id,
                "parent_id": (node.get("source_heading_ids") or [""])[0],
                "source_heading": node.get("source_heading") or "",
                "argument_role": node.get("argument_role") or "other",
                "argument_weight": node.get("argument_weight") or "detail",
                "status": node.get("status") or "mixed",
                "evidence_refs": list(node.get("evidence_refs") or []),
                "primary_consumer": consumers[0] if consumers else "",
                "allowed_merges": consumers,
                "required_for_primary_consumer": False,
                "source_gap_ids": [],
            })
        audit_outline = deepcopy(plan)
        audit_outline["semantic_argument_model_mode"] = "projection"
        audit_outline["argument_node_disposition_mode"] = "projection"
        model = {"section_nodes": [], "subsection_nodes": model_nodes, "argument_relations": [], "source_gaps": []}
        for item in audit_outline_consumption(audit_outline, model, None):
            _err(errors, str(item.get("code") or "argument_model_audit_error"), str(item.get("message") or "语义论点消费审计失败"), node_id=item.get("node_id"))
    except (ImportError, ModuleNotFoundError):
        _err(errors, "argument_consumption_audit_unavailable", "无法加载既有语义论点消费审计器")
    return errors


def _normalized_title(value: Any) -> str:
    text = re.sub(r"[\s　]+", "", str(value or ""))
    prefixes = (
        r"^[一二三四五六七八九十百]+、",
        r"^[（(][一二三四五六七八九十百\d]+[）)]",
        r"^\d+(?:\.\d+)*[.、]",
    )
    for pattern in prefixes:
        text = re.sub(pattern, "", text, count=1)
    return text


def _title_matches_source(title: Any, source_title: Any) -> bool:
    title_text = _normalized_title(title)
    source_text = _normalized_title(source_title)
    if not title_text or not source_text:
        return False
    if title_text == source_text:
        return True
    suffix = title_text[len(source_text):] if title_text.startswith(source_text) else ""
    return bool(
        suffix
        and re.fullmatch(
            r"[（(](?:[一二三四五六七八九十百\d]+|上|下|续)[）)]",
            suffix,
        )
    )


def _page_evidence_ids(page: dict[str, Any]) -> set[str]:
    evidence = page.get("evidence") if isinstance(page.get("evidence"), dict) else {}
    return {
        str(value)
        for field in ("normalized_fact_ids", "relation_ids", "argument_node_ids")
        for value in evidence.get(field) or []
        if str(value)
    }


def _role_map(value: Any) -> dict[str, list[str]] | None:
    if isinstance(value, dict):
        return {
            role: [str(item) for item in refs if str(item)]
            for role, refs in value.items()
            if role in EVIDENCE_ROLE_KEYS and isinstance(refs, list)
        }
    if isinstance(value, list):
        result: dict[str, list[str]] = {role: [] for role in EVIDENCE_ROLE_KEYS}
        for item in value:
            if not isinstance(item, dict):
                return None
            role = str(item.get("role") or "")
            refs = item.get("source_refs")
            if role not in EVIDENCE_ROLE_KEYS or not isinstance(refs, list) or not refs:
                return None
            result[role].extend(str(ref) for ref in refs if str(ref))
        return result
    return None


def _title_only_chain(page: dict[str, Any], workpack: dict[str, Any] | None) -> bool:
    chain = page.get("argument_chain")
    if not isinstance(chain, list) or not chain:
        return False
    statements = [
        _normalized_title(item.get("statement"))
        for item in chain
        if isinstance(item, dict) and str(item.get("statement") or "").strip()
    ]
    if len(statements) != len(chain) or not statements:
        return False
    titles = {_normalized_title(page.get("title_intent"))}
    for heading in (workpack or {}).get("source_heading_outline") or []:
        if not isinstance(heading, dict):
            continue
        if str(heading.get("section_id") or heading.get("heading_id") or "") in {
            str(value) for value in page.get("source_heading_ids") or []
        }:
            titles.add(_normalized_title(heading.get("title")))
    titles.discard("")
    return bool(titles) and all(statement in titles for statement in statements)


def _validate_workpack(
    workpack: dict[str, Any],
    semantic_payloads: dict[str, dict[str, Any]],
    deck: dict[str, Any],
    pages: list[Any],
    errors: list[dict[str, Any]],
) -> None:
    if workpack.get("artifact_type") != "ppt_outline_workpack":
        _err(
            errors,
            "wrong_workpack_artifact_type",
            "outline-workpack.json must be ppt_outline_workpack",
        )
        return

    recorded_hashes = ((workpack.get("semantic") or {}).get("artifact_sha256") or {})
    stale_files = [
        name
        for name in REQUIRED_FILES
        if recorded_hashes.get(name) != _json_sha256(semantic_payloads[name])
    ]
    if stale_files:
        _err(
            errors,
            "stale_outline_workpack",
            "Outline workpack semantic hashes do not match current inputs; regenerate the workpack.",
            files=stale_files,
        )

    workpack_binding = workpack.get("binding") or {}
    invalid_internal_binding = []
    expected_internal_hashes = {
        "request_sha256": _json_sha256(workpack.get("request") or {}),
        "planning_policy_sha256": _json_sha256(workpack.get("planning_policy") or {}),
    }
    for field, expected in expected_internal_hashes.items():
        if workpack_binding.get(field) != expected:
            invalid_internal_binding.append(field)
    if invalid_internal_binding:
        _err(
            errors,
            "invalid_workpack_binding",
            "Workpack request or planning policy changed after preparation; regenerate the workpack.",
            fields=invalid_internal_binding,
        )

    deck_binding = deck.get("workpack_binding") or {}
    binding_fields = ("request_sha256", "planning_policy_sha256")
    mismatched_binding = [
        field
        for field in binding_fields
        if not workpack_binding.get(field)
        or deck_binding.get(field) != workpack_binding.get(field)
    ]
    if mismatched_binding:
        _err(
            errors,
            "workpack_binding_mismatch",
            "Deck brief must bind to the current workpack request and planning policy.",
            fields=mismatched_binding,
        )

    policy = workpack.get("planning_policy") or {}
    locked = policy.get("source_structure_mode") == "locked"
    if not locked:
        return

    task = deck.get("task_understanding") or {}
    mismatched_policy = {}
    for field in ("writing_style_mode", "source_structure_mode"):
        if task.get(field) != policy.get(field):
            mismatched_policy[field] = {
                "expected": policy.get(field),
                "actual": task.get(field),
            }
    if mismatched_policy:
        _err(
            errors,
            "planning_policy_mismatch",
            "Deck brief writing and source-structure modes must match the locked workpack.",
            fields=mismatched_policy,
        )

    headings = workpack.get("source_heading_outline") or []
    heading_by_id = {
        str(item.get("section_id")): item
        for item in headings
        if isinstance(item, dict) and item.get("section_id")
    }
    if not heading_by_id:
        _err(
            errors,
            "missing_source_heading_outline",
            "Locked source structure requires source_heading_outline in the workpack.",
        )
        return

    agenda_title = ((workpack.get("source_metadata") or {}).get("agenda_title") or "目录")
    previous_order = 0
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_id = str(page.get("page_id") or "")
        role = str(page.get("template_role") or "")
        if page.get("page_type") == "template" and role == "agenda":
            if _normalized_title(page.get("title_intent")) != _normalized_title(agenda_title):
                _err(
                    errors,
                    "invalid_locked_agenda_title",
                    "Locked agenda title must use the source agenda title or 目录.",
                    page_id=page_id,
                    expected=agenda_title,
                    actual=page.get("title_intent"),
                )
            continue

        requires_heading = page.get("page_type") == "content" or (
            page.get("page_type") == "template" and role == "section_divider"
        )
        if not requires_heading:
            continue

        source_heading_ids = page.get("source_heading_ids")
        primary_id = str(page.get("primary_source_heading_id") or "")
        if not isinstance(source_heading_ids, list) or not source_heading_ids or not primary_id:
            _err(
                errors,
                "missing_source_heading_ownership",
                "Locked section and content pages require source_heading_ids and primary_source_heading_id.",
                page_id=page_id,
            )
            continue
        normalized_ids = [str(value) for value in source_heading_ids]
        if primary_id not in normalized_ids:
            _err(
                errors,
                "primary_source_heading_not_declared",
                "primary_source_heading_id must be included in source_heading_ids.",
                page_id=page_id,
                primary_source_heading_id=primary_id,
            )
        unknown_ids = [value for value in normalized_ids if value not in heading_by_id]
        if unknown_ids:
            _err(
                errors,
                "unknown_source_heading",
                "Page references source heading IDs that are not present in the workpack.",
                page_id=page_id,
                ids=unknown_ids,
            )
        primary = heading_by_id.get(primary_id)
        if primary is None:
            continue
        editorial_title = str(page.get("title_authoring_mode") or "") == "editorial"
        source_heading_title = str(page.get("source_heading_title") or "")
        if editorial_title and _normalized_title(source_heading_title) != _normalized_title(primary.get("title")):
            _err(
                errors,
                "editorial_title_source_trace_missing",
                "Editorial page titles must retain the mapped primary source heading in source_heading_title.",
                page_id=page_id,
                expected=primary.get("title"),
                actual=source_heading_title,
            )
        if not editorial_title and not _title_matches_source(page.get("title_intent"), primary.get("title")):
            _err(
                errors,
                "source_heading_title_mismatch",
                "Source-heading titles must preserve the primary source heading; editorial titles require title_authoring_mode=editorial and source_heading_title.",
                page_id=page_id,
                expected=primary.get("title"),
                actual=page.get("title_intent"),
            )
        current_order = int(primary.get("order") or 0)
        if current_order < previous_order:
            _err(
                errors,
                "source_heading_order_regression",
                "Locked pages must preserve source heading order.",
                page_id=page_id,
                previous_source_order=previous_order,
                current_source_order=current_order,
            )
        previous_order = max(previous_order, current_order)


def _fact_source_headings(
    fact: dict[str, Any],
    headings: list[dict[str, Any]],
) -> list[str]:
    """Map normalized-fact evidence lines to the nearest source headings."""

    if not headings:
        return []
    ordered = sorted(
        (item for item in headings if item.get("section_id") and item.get("line") is not None),
        key=lambda item: int(item.get("line") or 0),
    )
    result: list[str] = []
    for evidence in fact.get("evidence") or []:
        if not isinstance(evidence, dict) or evidence.get("line_start") is None:
            continue
        line = int(evidence.get("line_start") or 0)
        candidates = [item for item in ordered if int(item.get("line") or 0) <= line]
        if candidates:
            section_id = str(candidates[-1]["section_id"])
            if section_id not in result:
                result.append(section_id)
    return result


def _fact_dispositions(
    plan: dict[str, Any],
    page_order: dict[str, int],
    fact_ids: set[str],
    errors: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    raw = plan.get("fact_dispositions")
    if raw is None:
        return {}
    if not isinstance(raw, list):
        _err(errors, "invalid_fact_dispositions", "fact_dispositions must be an array")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            _err(errors, "invalid_fact_disposition", "Each fact disposition must be an object", index=index)
            continue
        fact_id = str(item.get("normalized_fact_id") or "")
        disposition = str(item.get("disposition") or "")
        if not fact_id or fact_id not in fact_ids:
            _err(errors, "unknown_fact_disposition", "Fact disposition must reference a known normalized fact", index=index, normalized_fact_id=fact_id)
            continue
        if fact_id in result:
            _err(errors, "duplicate_fact_disposition", "Each normalized fact may have at most one fact disposition", normalized_fact_id=fact_id)
            continue
        if disposition not in FACT_DISPOSITION_VALUES:
            _err(errors, "invalid_fact_disposition", "Unsupported normalized fact disposition", normalized_fact_id=fact_id, disposition=disposition)
            continue
        rationale = str(item.get("rationale") or "").strip()
        if not rationale:
            _err(errors, "fact_disposition_rationale_missing", "Fact dispositions require a rationale", normalized_fact_id=fact_id, disposition=disposition)
        page_ids = [str(value) for value in item.get("page_ids") or [] if str(value)]
        unknown_pages = sorted(set(page_ids) - set(page_order))
        if unknown_pages:
            _err(errors, "unknown_fact_disposition_page", "Fact disposition references an unknown page", normalized_fact_id=fact_id, page_ids=unknown_pages)
        target = str(item.get("deferred_to") or item.get("target_page") or "")
        if disposition == "deferred_to":
            if not target:
                _err(errors, "deferred_fact_target_missing", "deferred_to requires a later target page", normalized_fact_id=fact_id)
            elif target not in page_order:
                _err(errors, "unknown_fact_disposition_page", "deferred_to references an unknown page", normalized_fact_id=fact_id, deferred_to=target)
            elif page_ids and page_order[target] <= max(page_order.get(page_id, 0) for page_id in page_ids):
                _err(errors, "invalid_deferred_fact_target", "deferred_to target must be later than the declared source page", normalized_fact_id=fact_id, deferred_to=target, page_ids=page_ids)
            elif not page_ids and page_order[target] <= 1:
                _err(errors, "invalid_deferred_fact_target", "deferred_to target must be a later page", normalized_fact_id=fact_id, deferred_to=target)
        if disposition in {"page", "shared"} and not page_ids:
            _err(errors, "fact_page_ownership_missing", "Page/shared fact disposition requires page_ids", normalized_fact_id=fact_id, disposition=disposition)
        if disposition in {"detail", "trace"} and not page_ids:
            _err(errors, "fact_page_ownership_missing", "Detail/trace fact disposition requires page_ids", normalized_fact_id=fact_id, disposition=disposition)
        result[fact_id] = {
            **item,
            "normalized_fact_id": fact_id,
            "disposition": disposition,
            "page_ids": page_ids,
            "deferred_to": target or None,
            "rationale": rationale,
        }
    return result


def _fact_coverage(
    normalized: dict[str, Any],
    plan: dict[str, Any],
    workpack: dict[str, Any] | None,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    pages = [page for page in plan.get("pages") or [] if isinstance(page, dict)]
    page_order = {
        str(page.get("page_id")): int(page.get("order") or 0)
        for page in pages
        if page.get("page_id")
    }
    facts = [fact for fact in normalized.get("facts") or [] if isinstance(fact, dict)]
    fact_by_id = {
        str(fact.get("normalized_fact_id")): fact
        for fact in facts
        if fact.get("normalized_fact_id")
    }
    important = [
        fact for fact in facts
        if str(fact.get("fact_type") or "").strip().lower() not in NON_CONTENT_FACT_TYPES
    ]
    important_ids = {str(fact["normalized_fact_id"]) for fact in important}
    dispositions = _fact_dispositions(plan, page_order, set(fact_by_id), errors)
    workpack_headings = (workpack or {}).get("source_heading_outline") or []

    page_refs: dict[str, list[str]] = {fact_id: [] for fact_id in fact_by_id}
    page_roles: dict[str, dict[str, list[str]]] = {fact_id: {} for fact_id in fact_by_id}
    page_heading_ids: dict[str, list[str]] = {}
    for page in pages:
        page_id = str(page.get("page_id") or "")
        if not page_id:
            continue
        page_heading_ids[page_id] = [
            str(value)
            for value in page.get("source_heading_ids") or []
            if str(value)
        ]
        evidence = page.get("evidence") if isinstance(page.get("evidence"), dict) else {}
        refs = [str(value) for value in evidence.get("normalized_fact_ids") or [] if str(value)]
        roles = page.get("evidence_roles") if isinstance(page.get("evidence_roles"), dict) else {}
        for fact_id in refs:
            if fact_id not in page_refs:
                continue
            if page_id not in page_refs[fact_id]:
                page_refs[fact_id].append(page_id)
            for role, role_refs in roles.items():
                if isinstance(role_refs, list) and fact_id in {str(value) for value in role_refs}:
                    page_roles[fact_id].setdefault(str(role), []).append(page_id)

    items: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for fact in important:
        fact_id = str(fact["normalized_fact_id"])
        refs = page_refs[fact_id]
        declared = dispositions.get(fact_id)
        source_heading_ids = _fact_source_headings(fact, workpack_headings)
        cross_page = any(
            source_heading_ids
            and not set(source_heading_ids).intersection(page_heading_ids.get(page_id, []))
            for page_id in refs
        )
        if declared:
            disposition = str(declared["disposition"])
            if disposition in {"page", "shared"}:
                declared_pages = sorted(set(declared.get("page_ids") or []), key=lambda value: page_order.get(value, 0))
                actual_pages = sorted(set(refs), key=lambda value: page_order.get(value, 0))
                if declared_pages != actual_pages:
                    _err(
                        errors,
                        "fact_page_ownership_mismatch",
                        "Explicit fact page ownership must equal the page plan's direct fact references",
                        normalized_fact_id=fact_id,
                        declared_page_ids=declared_pages,
                        actual_page_ids=actual_pages,
                    )
            disposition_status = disposition
        elif not refs:
            _err(
                errors,
                "uncovered_important_normalized_fact",
                "Every important normalized fact requires page evidence, detail/trace handling, a later-page deferral, or a justified intentional omission",
                normalized_fact_id=fact_id,
                statement=fact.get("statement"),
            )
            unresolved.append(fact_id)
            disposition_status = "unresolved"
        elif cross_page:
            _err(
                errors,
                "cross_page_fact_ownership_missing",
                "A fact used across pages or outside its source heading requires explicit page/shared ownership or deferred handling",
                normalized_fact_id=fact_id,
                page_ids=refs,
                source_heading_ids=source_heading_ids,
            )
            unresolved.append(fact_id)
            disposition_status = "unresolved"
        else:
            role_names = sorted(page_roles[fact_id])
            disposition_status = "trace" if "trace_only" in role_names else ("detail" if "detail" in role_names else "page")
        item = {
            "normalized_fact_id": fact_id,
            "statement": fact.get("statement"),
            "fact_type": fact.get("fact_type"),
            "source_assertion_ids": [str(value) for value in fact.get("source_assertion_ids") or []],
            "source_block_ids": sorted({str(value.get("block_id")) for value in fact.get("evidence") or [] if isinstance(value, dict) and value.get("block_id")}),
            "source_heading_ids": source_heading_ids,
            "page_ids": refs,
            "roles": sorted(page_roles[fact_id]),
            "disposition": disposition_status,
            "deferred_to": declared.get("deferred_to") if declared else None,
            "rationale": declared.get("rationale") if declared else None,
        }
        items.append(item)
    return {
        "schema": "ppt_outline_fact_coverage.v1",
        "status": "error" if unresolved or any(item.get("code", "").startswith(("fact_", "uncovered_", "cross_page_", "deferred_", "unknown_fact_")) for item in errors) else "ok",
        "important_fact_ids": sorted(important_ids),
        "excluded_fact_ids": sorted(set(fact_by_id) - important_ids),
        "resolved_fact_ids": [item["normalized_fact_id"] for item in items if item["disposition"] != "unresolved"],
        "unresolved_fact_ids": sorted(set(unresolved)),
        "items": items,
    }


def validate_fact_coverage(semantic_dir: Path | str, outline_dir: Path | str) -> dict[str, Any]:
    """Validate only the source-fact coverage contract before handoff."""

    semantic = Path(semantic_dir)
    outline = Path(outline_dir)
    normalized = _read(semantic / "normalized-facts.json")
    plan = _read(outline / "page-plan.json")
    workpack_path = outline / "outline-workpack.json"
    workpack = _read(workpack_path) if workpack_path.is_file() else None
    errors: list[dict[str, Any]] = []
    coverage = _fact_coverage(normalized, plan, workpack, errors)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": "ok" if not errors else "error",
        "errors": errors,
        "coverage": coverage,
    }


def validate_outline_outputs(semantic_dir:Path|str,outline_dir:Path|str,*,write_report:bool=False)->dict[str,Any]:
    semantic=Path(semantic_dir); outline=Path(outline_dir)
    normalized,concepts,relations,argument,semantic_report=_semantic(semantic)
    deck_path=outline/"deck-brief.json"; page_path=outline/"page-plan.json"
    if not deck_path.is_file() or not page_path.is_file(): raise FileNotFoundError("deck-brief.json and page-plan.json are required")
    deck=_read(deck_path); plan=_read(page_path); errors=[]; warnings=[]
    if semantic_report.get("status")!="ok": _err(errors,"semantic_not_validated","semantic-report.json must report status: ok")
    if deck.get("artifact_type")!="ppt_deck_brief": _err(errors,"wrong_artifact_type","deck-brief.json must be ppt_deck_brief")
    if plan.get("artifact_type")!="ppt_page_plan": _err(errors,"wrong_artifact_type","page-plan.json must be ppt_page_plan")
    if deck.get("deck_id")!=plan.get("deck_id") or not deck.get("deck_id"): _err(errors,"deck_id_mismatch","deck IDs must match and be non-empty")
    _scan(deck,errors,"deck"); _scan(plan,errors,"page-plan")
    task=deck.get("task_understanding") or {}; strategy=deck.get("deck_strategy") or {}
    for field in ("audience","purpose"):
        if not str(task.get(field) or "").strip(): _err(errors,"missing_task_context",f"task_understanding.{field} is required")
    for field in ("working_title","core_question","deck_thesis"):
        if not str(strategy.get(field) or "").strip(): _err(errors,"missing_deck_strategy",f"deck_strategy.{field} is required")
    sections=deck.get("sections") if isinstance(deck.get("sections"),list) else []; section_by_id={str(s.get("section_id")):s for s in sections if isinstance(s,dict) and s.get("section_id")}
    pages=plan.get("pages") if isinstance(plan.get("pages"),list) else []
    workpack_path=outline/"outline-workpack.json"
    workpack_payload: dict[str, Any] | None = None
    if workpack_path.is_file():
        workpack_payload = _read(workpack_path)
        _validate_workpack(
            workpack_payload,
            {
                "normalized-facts.json": normalized,
                "concept-base.json": concepts,
                "relation-graph.json": relations,
                "argument-chain.json": argument,
                "semantic-report.json": semantic_report,
            },
            deck,
            pages,
            errors,
        )
    for issue in authoring_issues(
        plan,
        [page for page in pages if isinstance(page, dict)],
        workpack=workpack_payload,
    ):
        context = issue.get("context") if isinstance(issue.get("context"), dict) else {}
        _err(
            errors,
            str(issue.get("code") or "authoring_contract_error"),
            str(issue.get("message") or "Outline authoring contract failed."),
            **context,
        )
    orders=[p.get("order") for p in pages if isinstance(p,dict)]
    if orders!=list(range(1,len(pages)+1)): _err(errors,"non_contiguous_page_order","Page order must be contiguous and match array order",orders=orders)
    page_ids=[str(p.get("page_id")) for p in pages if isinstance(p,dict) and p.get("page_id")]
    if len(page_ids)!=len(set(page_ids)): _err(errors,"duplicate_page_id","page_id values must be unique")
    nf_ids={str(x.get("normalized_fact_id")) for x in normalized.get("facts") or [] if isinstance(x,dict)}
    relation_by_id={str(x.get("relation_id")):x for x in relations.get("relations") or [] if isinstance(x,dict)}
    arg_ids={str(x.get("node_id")) for group in (argument.get("source_chain") or [],argument.get("reconstructed_chain") or []) for x in group if isinstance(x,dict)}
    arg_ids.update(
        str(item.get("id"))
        for item in plan.get("argument_node_registry") or []
        if isinstance(item, dict) and item.get("id")
    )
    page_order={str(p.get("page_id")):int(p.get("order")) for p in pages if isinstance(p,dict) and p.get("page_id") and isinstance(p.get("order"),int)}
    content_count=0; template_count=0; evidence_count=0
    for page in pages:
        if not isinstance(page,dict): _err(errors,"invalid_page","Page entries must be objects"); continue
        pid=str(page.get("page_id") or "")
        if page.get("page_type")=="template":
            template_count+=1
            forbidden=[k for k in ("key_judgment","argument_chain","evidence_roles","evidence") if page.get(k) not in (None,"",[],{})]
            if forbidden: _err(errors,"template_page_has_business_content","Template page may not carry business reasoning",page_id=pid,fields=forbidden)
            continue
        if page.get("page_type")!="content": _err(errors,"invalid_page_type","page_type must be template or content",page_id=pid); continue
        content_count+=1
        key_judgment = str(page.get("key_judgment") or "").strip()
        compatibility_core_message = str(page.get("core_message") or "").strip()
        if key_judgment and compatibility_core_message and key_judgment != compatibility_core_message:
            _err(
                errors,
                "semantic_center_alias_conflict",
                "key_judgment is the canonical layer-four field; an optional core_message alias must match it exactly.",
                page_id=pid,
            )
        for field in ("audience_question","page_mission","non_substitutable_value","argument_role","must_not_include","reserved_for_later","split_risk","transition_from_previous","transition_to_next"):
            value=page.get(field)
            if value is None or value=="" or (field=="must_not_include" and value==[]): _err(errors,"missing_page_boundary_field",f"Content page requires {field}",page_id=pid,field=field)
        author_driven = plan.get("editorial_authoring_mode") == "author_driven"
        awaiting_authoring = author_driven and plan.get("editorial_authoring_status") != "author_edited"
        if not author_driven:
            if not key_judgment:
                _err(errors,"missing_page_boundary_field","Content page requires key_judgment",page_id=pid,field="key_judgment")
        elif not awaiting_authoring:
            if not key_judgment:
                _err(errors,"missing_page_boundary_field","Content page requires key_judgment",page_id=pid,field="key_judgment")
            if page.get("judgment_status") != "author_edited":
                _err(errors,"outline_judgment_status_incomplete","author_edited pages must record judgment_status: author_edited",page_id=pid)
        else:
            if key_judgment:
                _err(errors,"outline_judgment_before_authoring","Candidate pages may not carry a business key_judgment before authoring",page_id=pid)
            if page.get("judgment_status") != "authoring_required":
                _err(errors,"outline_judgment_status_incomplete","Candidate pages must record judgment_status: authoring_required",page_id=pid)

        # A page whose key_judgment is still authoring_required has no judgment to
        # derive yet; the receipt-integrity checks below only apply once a real
        # judgment exists (legacy non-author_driven pages, or author_edited pages).
        if not awaiting_authoring:
            receipt = page.get("judgment_derivation") or page.get("core_message_derivation")
            if not isinstance(receipt, dict):
                _err(errors,"judgment_derivation_missing","Every content page judgment requires an explicit judgment_derivation receipt",page_id=pid)
            else:
                receipt_refs = {str(value) for value in receipt.get("source_refs") or [] if str(value)}
                outside = sorted(receipt_refs - _page_evidence_ids(page))
                if not receipt_refs:
                    _err(errors,"judgment_derivation_refs_missing","judgment_derivation.source_refs must be non-empty",page_id=pid)
                if outside:
                    _err(errors,"judgment_derivation_outside_page","judgment_derivation.source_refs must be declared by the page evidence",page_id=pid,ids=outside)
                if not receipt.get("supporting_statements") or not str(receipt.get("derivation") or "").strip():
                    _err(errors,"judgment_derivation_incomplete","judgment_derivation must state supporting_statements and an equal-strength derivation",page_id=pid)
                if receipt.get("introduced_relations") or receipt.get("introduced_modalities"):
                    _err(errors,"judgment_derivation_introduces_meaning","judgment_derivation may not introduce relations or modalities absent from the cited material",page_id=pid)
        if page.get("split_risk") in {"medium","high"} and not str(page.get("split_risk_reason") or "").strip(): _err(errors,"missing_split_risk_reason","Medium/high split risk requires split_risk_reason",page_id=pid)
        evidence=page.get("evidence") if isinstance(page.get("evidence"),dict) else {}; nfs=[str(x) for x in evidence.get("normalized_fact_ids") or []]; rels=[str(x) for x in evidence.get("relation_ids") or []]; args=[str(x) for x in evidence.get("argument_node_ids") or []]
        if not nfs: _err(errors,"missing_direct_fact_grounding","Every content page requires at least one direct normalized_fact_id",page_id=pid)
        for ref in nfs:
            if ref not in nf_ids: _err(errors,"unknown_normalized_fact","Unknown normalized fact",page_id=pid,id=ref)
        inferred=[]
        for ref in rels:
            relation=relation_by_id.get(ref)
            if relation is None: _err(errors,"unknown_relation","Unknown relation",page_id=pid,id=ref)
            elif relation.get("basis")=="inferred": inferred.append(ref)
        if inferred and not str(evidence.get("inference_note") or "").strip(): _err(errors,"undisclosed_inferred_relation","Inferred relations require evidence.inference_note",page_id=pid,relation_ids=inferred)
        for ref in args:
            if ref not in arg_ids: _err(errors,"unknown_argument_node","Unknown argument node",page_id=pid,id=ref)
        page_evidence=set(nfs)|set(rels)|set(args); evidence_count+=len(page_evidence)
        chain=page.get("argument_chain")
        if not isinstance(chain,list) or not chain: _err(errors,"invalid_argument_chain","argument_chain must be non-empty",page_id=pid)
        else:
            if not awaiting_authoring and _title_only_chain(page, workpack_payload):
                _err(errors,"title_only_argument_chain","An argument_chain cannot use only the page or source chapter title as its argument",page_id=pid)
            for idx,node in enumerate(chain,1):
                if not isinstance(node,dict): _err(errors,"invalid_argument_chain","argument_chain entries must be objects",page_id=pid,index=idx); continue
                if node.get("role") not in ARGUMENT_CHAIN_ROLES: _err(errors,"invalid_argument_chain_role","Unknown argument role",page_id=pid,index=idx)
                if not str(node.get("statement") or "").strip(): _err(errors,"invalid_argument_chain","argument_chain statement required",page_id=pid,index=idx)
                ev=node.get("evidence") if isinstance(node.get("evidence"),dict) else {}; refs=set(str(x) for key in ("normalized_fact_ids","relation_ids","argument_node_ids") for x in ev.get(key) or [])
                if not refs: _err(errors,"invalid_argument_chain","argument_chain evidence required",page_id=pid,index=idx)
                outside=sorted(refs-page_evidence)
                if outside: _err(errors,"argument_chain_evidence_outside_page","Chain evidence must already be declared by page",page_id=pid,index=idx,ids=outside)
        roles=page.get("evidence_roles")
        role_map = _role_map(roles)
        if role_map is None: _err(errors,"invalid_evidence_roles","evidence_roles must use explicit role records or a role-to-reference object",page_id=pid)
        else:
            assigned={}
            for role in EVIDENCE_ROLE_KEYS:
                refs=role_map.get(role)
                if not isinstance(refs,list): _err(errors,"invalid_evidence_roles",f"evidence_roles.{role} must be array",page_id=pid); continue
                for ref in refs: assigned.setdefault(str(ref),[]).append(role)
            for ref,names in assigned.items():
                if ref not in page_evidence: _err(errors,"evidence_role_outside_page","Role can classify only page evidence",page_id=pid,id=ref)
                if len(names)>1: _err(errors,"evidence_role_overlap","One evidence ID may have one role only",page_id=pid,id=ref,roles=names)
            missing=sorted(page_evidence-set(assigned))
            if missing: _err(errors,"unassigned_page_evidence","Every page evidence ID must have exactly one role",page_id=pid,ids=missing)
        if page.get("judgment_basis")=="planning_inference" and not str(page.get("inference_rationale") or "").strip(): _err(errors,"missing_inference_rationale","planning_inference requires inference_rationale",page_id=pid)
        reserved=page.get("reserved_for_later")
        if isinstance(reserved,list):
            for item in reserved:
                if not isinstance(item,dict) or not item.get("topic") or not item.get("target_page"): _err(errors,"invalid_reserved_for_later","Reserved item requires topic and target_page",page_id=pid); continue
                target=str(item.get("target_page"))
                if target not in page_order: _err(errors,"invalid_reserved_target","reserved target must exist",page_id=pid,target_page=target)
                elif page_order[target]<=page_order.get(pid,0): _err(errors,"reserved_target_not_later","reserved target must be later page",page_id=pid,target_page=target)
    for section_id,section in section_by_id.items():
        planned=[str(x) for x in section.get("page_ids") or []]; actual=[str(p.get("page_id")) for p in pages if isinstance(p,dict) and str(p.get("section_id") or "")==section_id]
        if planned!=actual: _err(errors,"section_page_mismatch","Section page_ids must match page plan",section_id=section_id,planned=planned,actual=actual)
    coverage = _fact_coverage(normalized, plan, workpack_payload, errors)
    errors.extend(_semantic_binding_issues(plan, argument, concepts, relations))
    budget=strategy.get("page_budget") if isinstance(strategy.get("page_budget"),dict) else {}
    target=budget.get("target"); minimum=budget.get("min"); maximum=budget.get("max")
    if not all(isinstance(v,int) and v>0 for v in (target,minimum,maximum)): _err(errors,"invalid_page_budget","page_budget target/min/max must be positive integers")
    elif not minimum<=len(pages)<=maximum: _err(errors,"page_count_out_of_range","Page count outside budget",actual=len(pages),min=minimum,max=maximum)
    result={"schema_version":REPORT_SCHEMA_VERSION,"artifact_type":"ppt_outline_validation_report","status":"ok" if not errors else "error","errors":errors,"warnings":warnings,"coverage":coverage,"counts":{"sections":len(sections),"pages":len(pages),"content_pages":content_count,"template_pages":template_count,"evidence_references":evidence_count,"important_normalized_facts":len(coverage["important_fact_ids"]),"resolved_normalized_facts":len(coverage["resolved_fact_ids"]),"unresolved_normalized_facts":len(coverage["unresolved_fact_ids"])} }
    result["gates"] = build_layer4_status(deck, plan, result)
    if write_report: _write(outline/"outline-report.json",result)
    return result
