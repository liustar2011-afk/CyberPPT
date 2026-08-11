"""Cross-audit semantic claims against stable source units and Source Truth.

Stage 00 owns interpretation; Source Truth owns normalized evidence records.
This module checks their bindings without allowing either side to silently
rewrite the other.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.source_document_map import load_source_units


CROSS_AUDIT_SCHEMA = "cyberppt.semantic_evidence_cross_audit.v1"
CROSS_AUDIT_JSON = Path("workbench/stages/01-analysis/semantic-evidence-cross-audit.json")
CROSS_AUDIT_MD = Path("workbench/stages/01-analysis/semantic-evidence-cross-audit.md")
CLAIM_ORIGINS = frozenset(
    {"source_explicit", "source_implied", "editorial_hypothesis"}
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value: object) -> str:
    return str(value or "").strip()


def _items(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _refs(value: object) -> list[str]:
    return [_text(item) for item in value if _text(item)] if isinstance(value, list) else []


def _issue(
    code: str,
    message: str,
    *,
    source_ids: list[str] | None = None,
    node_id: str = "",
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "code": code,
        "message": message,
        "source_ids": source_ids or [],
        "retry_strategy": "rebuild_semantic_evidence_binding",
    }
    if node_id:
        result["node_id"] = node_id
    return result


def _semantic_claims(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    thesis = model.get("document_thesis")
    if isinstance(thesis, dict):
        result["document_thesis"] = thesis
    for field in ("section_nodes", "subsection_nodes"):
        for item in _items(model.get(field)):
            node_id = _text(item.get("id"))
            if node_id:
                result[node_id] = item
    return result


def _all_model_refs(model: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    thesis = model.get("document_thesis")
    if isinstance(thesis, dict):
        refs.update(_refs(thesis.get("evidence_refs")))
    for field in ("section_nodes", "subsection_nodes", "argument_relations", "heading_semantic_cards"):
        for item in _items(model.get(field)):
            refs.update(_refs(item.get("evidence_refs")))
    context = model.get("document_semantics")
    if isinstance(context, dict):
        for field in ("argument_method", "supporting_basis"):
            for item in _items(context.get(field)):
                refs.update(_refs(item.get("source_refs")))
    for item in _items(model.get("inference_register")):
        refs.update(_refs(item.get("basis_refs")))
    graph = model.get("concept_occurrence_graph")
    if isinstance(graph, dict):
        for item in _items(graph.get("concepts")):
            refs.update(_refs(item.get("occurrence_unit_ids")))
        for item in _items(graph.get("relations")):
            refs.update(_refs(item.get("evidence_refs")))
    return refs


def semantic_evidence_cross_issues(
    model: dict[str, Any],
    source_truth: dict[str, Any],
    *,
    source_unit_ids: set[str],
) -> list[dict[str, Any]]:
    """Return deterministic semantic/evidence binding issues."""

    issues: list[dict[str, Any]] = []
    strict = model.get("interpretation_contract_mode") == "strict"
    records = _items(source_truth.get("records"))
    record_index = {
        _text(item.get("id")): item for item in records if _text(item.get("id"))
    }
    claims = _semantic_claims(model)
    all_refs = _all_model_refs(model)
    legacy_refs = {ref for ref in all_refs if ref.startswith("S") and ref[1:].isdigit()}
    stable_refs = {ref for ref in all_refs if ref.startswith("SU-")}

    unknown_records = sorted(legacy_refs - set(record_index))
    if unknown_records:
        issues.append(
            _issue(
                "SEMANTIC_LEGACY_EVIDENCE_UNKNOWN",
                "语义模型引用了 Source Truth 中不存在的旧式证据记录：" + "、".join(unknown_records),
                source_ids=unknown_records,
            )
        )
    unknown_units = sorted(stable_refs - source_unit_ids)
    if unknown_units:
        issues.append(
            _issue(
                "SEMANTIC_SOURCE_UNIT_UNKNOWN",
                "语义模型引用了源材料地图中不存在的稳定单元：" + "、".join(unknown_units),
            )
        )

    for node_id, claim in claims.items():
        if node_id == "document_thesis" or _text(claim.get("argument_weight")) == "core":
            evidence = set(_refs(claim.get("evidence_refs")))
            resolved = bool(evidence & (set(record_index) | source_unit_ids))
            if not resolved:
                issues.append(
                    _issue(
                        "SEMANTIC_CORE_CLAIM_UNRESOLVED",
                        "核心论点必须至少绑定一条当前可解析的 Source Truth 记录或稳定源材料单元。",
                        node_id=node_id,
                    )
                )
        if _text(claim.get("claim_origin")) == "editorial_hypothesis" and (
            node_id == "document_thesis" or _text(claim.get("argument_weight")) == "core"
        ):
            issues.append(
                _issue(
                    "SEMANTIC_EDITORIAL_HYPOTHESIS_CORE",
                    "编辑性假设不得成为全文主论点或核心源论点。",
                    node_id=node_id,
                )
            )

    if not strict:
        return issues

    truth_omissions: dict[str, dict[str, Any]] = {}
    for item in _items(source_truth.get("intentional_source_unit_omissions")):
        if not isinstance(item, dict):
            continue
        for unit_id in _refs(item.get("source_unit_refs")):
            truth_omissions[unit_id] = item

    # Reverse coverage: important semantic claims must be reconstructed from
    # Source Truth records, not merely point at one representative paragraph.
    subsection_ids = {
        _text(item.get("id"))
        for item in _items(model.get("subsection_nodes"))
        if _text(item.get("id"))
    }
    for node_id, claim in claims.items():
        if node_id not in subsection_ids:
            continue
        weight = _text(claim.get("argument_weight"))
        evidence_refs = {
            ref for ref in _refs(claim.get("evidence_refs"))
            if ref.startswith("SU-") and "-HEADING-" not in ref
        }
        protected = (
            weight in {"core", "constraint"}
            or (
                weight == "supporting"
                and bool(_text(claim.get("source_heading")))
                and len(evidence_refs) >= 6
            )
        )
        if not protected:
            continue
        mapped_records = [
            record for record in records
            if node_id in set(_refs(record.get("semantic_node_ids")))
        ]
        if not mapped_records:
            issues.append(_issue(
                "SOURCE_TRUTH_PROTECTED_NODE_MISSING",
                "核心、关键约束或证据充分的独立语义论点没有任何 Source Truth 记录承载。",
                node_id=node_id,
            ))
            continue
        mapped_units = {
            unit_id
            for record in mapped_records
            for unit_id in _refs(record.get("source_unit_refs"))
        }
        missing_units: list[str] = []
        unauthorized_omissions: list[str] = []
        for unit_id in sorted(evidence_refs - mapped_units):
            omission = truth_omissions.get(unit_id)
            if omission is None:
                missing_units.append(unit_id)
                continue
            if not (
                omission.get("user_authorized_omission") is True
                and _text(omission.get("user_decision_ref"))
                and len(_text(omission.get("reason"))) >= 8
            ):
                unauthorized_omissions.append(unit_id)
        if missing_units:
            issues.append(_issue(
                "SOURCE_TRUTH_PROTECTED_EVIDENCE_GAP",
                "重要语义论点的部分来源证据单元未进入 Source Truth；代表性摘要不能替代逐项事实、关系、条件和状态保留。",
                node_id=node_id,
                source_ids=missing_units,
            ))
        if unauthorized_omissions:
            issues.append(_issue(
                "SOURCE_TRUTH_PROTECTED_OMISSION_UNAUTHORIZED",
                "重要语义论点的来源单元不得由生成器自行舍弃；必须记录明确用户决定。",
                node_id=node_id,
                source_ids=unauthorized_omissions,
            ))

    for record in records:
        record_id = _text(record.get("id"))
        origin = _text(record.get("claim_origin"))
        if origin not in CLAIM_ORIGINS:
            issues.append(
                _issue(
                    "SOURCE_TRUTH_CLAIM_ORIGIN_INVALID",
                    "严格语义合同下，每条 Source Truth 记录必须声明 claim_origin。",
                    source_ids=[record_id] if record_id else [],
                )
            )
        unit_refs = set(_refs(record.get("source_unit_refs")))
        unknown_record_units = sorted(unit_refs - source_unit_ids)
        if unknown_record_units:
            issues.append(
                _issue(
                    "SOURCE_TRUTH_SOURCE_UNIT_UNKNOWN",
                    "Source Truth 记录引用了不存在的 source_unit_id：" + "、".join(unknown_record_units),
                    source_ids=[record_id] if record_id else [],
                )
            )
        semantic_node_ids = set(_refs(record.get("semantic_node_ids")))
        unknown_nodes = sorted(semantic_node_ids - set(claims))
        if unknown_nodes:
            issues.append(
                _issue(
                    "SOURCE_TRUTH_SEMANTIC_NODE_UNKNOWN",
                    "Source Truth 记录引用了不存在的语义节点：" + "、".join(unknown_nodes),
                    source_ids=[record_id] if record_id else [],
                )
            )
        if _text(record.get("priority")) == "P0":
            if not semantic_node_ids:
                issues.append(
                    _issue(
                        "SOURCE_TRUTH_P0_SEMANTIC_MAPPING_MISSING",
                        "P0 证据必须明确声明 semantic_node_ids，证明它服务于哪个已批准源论点。",
                        source_ids=[record_id] if record_id else [],
                    )
                )
            if not unit_refs:
                issues.append(
                    _issue(
                        "SOURCE_TRUTH_P0_SOURCE_UNIT_MISSING",
                        "P0 证据必须回挂稳定 source_unit_refs，不能只保留自由文本定位。",
                        source_ids=[record_id] if record_id else [],
                    )
                )
            mapped_evidence = {
                ref
                for node_id in semantic_node_ids
                for ref in _refs((claims.get(node_id) or {}).get("evidence_refs"))
            }
            if semantic_node_ids and unit_refs and not (mapped_evidence & unit_refs):
                issues.append(
                    _issue(
                        "SOURCE_TRUTH_P0_SEMANTIC_EVIDENCE_DISCONNECTED",
                        "P0 记录的 source_unit_refs 与其 semantic_node_ids 的论点证据没有交集。",
                        source_ids=[record_id] if record_id else [],
                    )
                )
        if origin == "editorial_hypothesis" and (
            _text(record.get("priority")) == "P0"
            or _text(record.get("claim_role")) == "fact"
        ):
            issues.append(
                _issue(
                    "SOURCE_TRUTH_EDITORIAL_HYPOTHESIS_PROMOTED",
                    "编辑性假设不得被标为 P0 或事实记录。",
                    source_ids=[record_id] if record_id else [],
                )
            )
        mapped_origins = {
            _text((claims.get(node_id) or {}).get("claim_origin"))
            for node_id in semantic_node_ids
        }
        if origin == "source_explicit" and mapped_origins == {"editorial_hypothesis"}:
            issues.append(
                _issue(
                    "SOURCE_TRUTH_CLAIM_ORIGIN_DRIFTED",
                    "Source Truth 不得把仅属编辑假设的语义节点改写为原文明示。",
                    source_ids=[record_id] if record_id else [],
                )
            )
    return issues


def run_semantic_evidence_cross_audit(
    project: Path,
    model: dict[str, Any],
    source_truth: dict[str, Any],
) -> dict[str, Any]:
    project = project.expanduser().resolve()
    units = load_source_units(project)
    unit_ids = {_text(item.get("unit_id")) for item in units if _text(item.get("unit_id"))}
    issues = semantic_evidence_cross_issues(
        model,
        source_truth,
        source_unit_ids=unit_ids,
    )
    records = _items(source_truth.get("records"))
    p0_records = [item for item in records if _text(item.get("priority")) == "P0"]
    report = {
        "schema": CROSS_AUDIT_SCHEMA,
        "status": "passed" if not issues else "rewrite_required",
        "interpretation_contract_mode": model.get("interpretation_contract_mode", "legacy"),
        "source_unit_count": len(unit_ids),
        "semantic_claim_count": len(_semantic_claims(model)),
        "source_truth_record_count": len(records),
        "p0_record_count": len(p0_records),
        "p0_semantic_mapped_count": sum(
            bool(_refs(item.get("semantic_node_ids"))) for item in p0_records
        ),
        "p0_source_unit_mapped_count": sum(
            bool(_refs(item.get("source_unit_refs"))) for item in p0_records
        ),
        "issues": issues,
        "audited_at": _utc_now(),
    }
    json_path = project / CROSS_AUDIT_JSON
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 语义—证据交叉审计",
        "",
        f"- 状态：**{report['status']}**",
        f"- 语义主张：{report['semantic_claim_count']}",
        f"- Source Truth 记录：{report['source_truth_record_count']}",
        f"- P0 语义节点映射：{report['p0_semantic_mapped_count']}/{report['p0_record_count']}",
        f"- P0 稳定源单元映射：{report['p0_source_unit_mapped_count']}/{report['p0_record_count']}",
        f"- 稳定源材料单元：{report['source_unit_count']}",
        "",
        "## 问题",
        "",
    ]
    if issues:
        lines.extend(f"- `{item['code']}`：{item['message']}" for item in issues)
    else:
        lines.append("- 无。语义论点、稳定源材料单元与 Source Truth 记录形成双向可回查关系。")
    (project / CROSS_AUDIT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    report["artifact"] = str(json_path)
    report["markdown"] = str(project / CROSS_AUDIT_MD)
    return report
