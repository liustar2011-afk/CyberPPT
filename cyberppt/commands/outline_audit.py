"""Persist outline audit attempts and bounded retry directions."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

from cyberppt.argument_flow_contract import (
    argument_graph_summary,
    audit_argument_flow,
)
from cyberppt.content_review import content_review_status
from cyberppt.semantic_digest import (
    json_semantic_digest,
    outline_semantic_digest,
    source_truth_semantic_digest,
)
from cyberppt.outline_contract import AuditIssue, audit_outline, load_outline, retry_directive
from cyberppt.semantic_understanding import (
    SEMANTIC_ARGUMENT_MODEL,
    assert_semantic_understanding_ready,
    semantic_binding_issues,
)
from cyberppt.source_argument_model import audit_outline_consumption, load_model
from cyberppt.communication_strategy import (
    audience_concern_binding_issues,
    assert_communication_strategy_ready,
    communication_strategy_binding_issues,
    frontstage_posture_issues,
)
from cyberppt.source_truth_contract import load_source_truth
from cyberppt.semantic_proposition_contract import build_proposition_graph
from cyberppt.stage01_controls import (
    assert_escalation_resolved,
    snapshot_reference_gate,
)
from cyberppt.storyline_director import (
    assert_storyline_director_ready,
    storyline_director_binding_issues,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


# Judgment dimensions checked by an independent reviewer at the PAGE
# PLANNING stage, before script text exists — narrower than the script
# stage's CONTENT_REVIEW_DECISIONS (script_audit.py) because on-screen
# module grouping isn't decided yet at outline time. These three catch
# problems that are cheaper to fix here than after a page is fully
# scripted: two sibling pages planned to cover materially the same
# content, or a page's own content_units already reaching beyond what its
# own page_mission promises.
OUTLINE_CONTENT_REVIEW_DECISIONS = (
    "single_mission",
    "no_cross_page_duplication",
    "content_within_mission_scope",
)


def _outline_content_review_status(
    project: Path,
    payload: dict[str, object],
    outline_path: Path,
    outline_sha256: str,
) -> dict[str, object]:
    required_pages = [
        str(page.get("page_id"))
        for page in payload.get("pages", [])
        if isinstance(page, dict) and page.get("page_type") == "content"
    ]
    return content_review_status(
        project / "workbench" / "stages" / "01-analysis" / "outline-content-review.json",
        schema="cyberppt.outline_content_review.v1",
        decision_keys=OUTLINE_CONTENT_REVIEW_DECISIONS,
        required_page_ids=required_pages,
        content_sha256=outline_sha256,
        content_semantic_sha256=outline_semantic_digest(outline_path),
        manifest_path=project / "review" / "chapter-review-manifest.json",
    )


def _source_consumption_manifest_issues(
    project: Path,
    outline: dict[str, object],
    source_truth_path: Path,
) -> list[AuditIssue]:
    if outline.get("source_truth_mapping_mode") != "consumption_manifest":
        return []
    raw_path = str(outline.get("source_consumption_manifest") or "").strip()
    if not raw_path:
        return [
            AuditIssue(
                "SOURCE_CONSUMPTION_MANIFEST_MISSING",
                "Frozen Source Truth mode requires an independent source consumption manifest.",
                retry_strategy="rebuild_outline_consumption_manifest",
            )
        ]
    manifest_path = Path(raw_path)
    if not manifest_path.is_absolute():
        manifest_path = project / manifest_path
    if not manifest_path.is_file():
        return [
            AuditIssue(
                "SOURCE_CONSUMPTION_MANIFEST_MISSING",
                "The Outline source consumption manifest does not exist.",
                retry_strategy="rebuild_outline_consumption_manifest",
            )
        ]
    declared_semantic_hash = str(
        outline.get("source_consumption_semantic_sha256") or ""
    ).lower()
    declared_hash = str(outline.get("source_consumption_sha256") or "").lower()
    manifest_matches = (
        declared_semantic_hash == json_semantic_digest(manifest_path)
        if declared_semantic_hash
        else declared_hash == _sha256(manifest_path)
    )
    if not manifest_matches:
        return [
            AuditIssue(
                "SOURCE_CONSUMPTION_MANIFEST_STALE",
                "The Outline source consumption manifest hash does not match the current manifest.",
                retry_strategy="rebuild_outline_consumption_manifest",
            )
        ]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return [
            AuditIssue(
                "SOURCE_CONSUMPTION_MANIFEST_INVALID",
                "The Outline source consumption manifest is not valid JSON.",
                retry_strategy="rebuild_outline_consumption_manifest",
            )
        ]
    declared_truth_semantic = str(
        manifest.get("source_truth_semantic_sha256") or ""
    ).lower()
    truth_matches = (
        declared_truth_semantic == source_truth_semantic_digest(source_truth_path)
        if declared_truth_semantic
        else str(manifest.get("source_truth_sha256") or "").lower()
        == _sha256(source_truth_path)
    )
    if not truth_matches:
        return [
            AuditIssue(
                "SOURCE_CONSUMPTION_SOURCE_BINDING_STALE",
                "The source consumption manifest is bound to a different Source Truth artifact.",
                retry_strategy="rebuild_outline_consumption_manifest",
            )
        ]
    return []


def render_outline_markdown(payload: dict[str, object], report: dict[str, object]) -> str:
    """Render the audited outline as the human review artifact."""

    pages = payload.get("pages") if isinstance(payload.get("pages"), list) else []
    content_pages = [
        page for page in pages
        if isinstance(page, dict) and page.get("page_type") == "content"
    ]
    lines = [
        "# Stage 01 逐页大纲（人类审阅稿）",
        "",
        "> 本文件由 `cyberppt outline-audit` 从 `outline.json` 自动生成。",
        "> Markdown 是大纲确认入口；JSON 仅作为机器审计合同。",
        "",
        "## 大纲摘要",
        "",
        f"- 架构：`{payload.get('architecture_mode', '未声明')}`",
        f"- 材料类型：{payload.get('material_type', '未声明')}",
        f"- 受众：{payload.get('audience', '未声明')}",
        f"- 总页数：{len(pages)}",
        f"- 内容页：{len(content_pages)}",
        f"- 大纲审计：**{report.get('status', 'unknown')}**",
        "",
    ]
    semantics = payload.get("document_semantics")
    if isinstance(semantics, dict):
        lines.extend(
            [
                "## 文档语义身份",
                "",
                f"- 文档身份：{semantics.get('document_role', '未声明')}",
                f"- 汇报对象：{semantics.get('subject_of_report', '未声明')}",
                f"- 全篇核心命题：{semantics.get('primary_thesis', '未声明')}",
                f"- 成果边界：{semantics.get('decision_boundary', '未声明')}",
                "",
            ]
        )
    narrative_logic = payload.get("narrative_logic")
    if isinstance(narrative_logic, list) and narrative_logic:
        lines.extend(["## 全篇逻辑", ""])
        for index, item in enumerate(narrative_logic, 1):
            if str(item).strip():
                lines.append(f"{index}. {item}")
        lines.append("")
    storyline = payload.get("storyline")
    if isinstance(storyline, dict) and storyline:
        destination_label = (
            "交流落点"
            if storyline.get("interaction_posture") == "peer_exchange"
            else "决策终点"
        )
        lines.extend(
            [
                "## 提纲导演合同",
                "",
                f"- 主题：{storyline.get('theme', '未声明')}",
                f"- {destination_label}：{storyline.get('decision_destination', '未声明')}",
                "",
                "### 故事线",
                "",
            ]
        )
        for index, item in enumerate(storyline.get("story_arc") or [], 1):
            if str(item).strip():
                lines.append(f"{index}. {item}")
        lines.extend(["", "### 章节问题", ""])
        for mission in storyline.get("chapter_missions") or []:
            if isinstance(mission, dict):
                lines.append(
                    f"- `{mission.get('chapter_id', '')}` {mission.get('question', '')} → {mission.get('contribution', '')}"
                )
        lines.append("")
    lines.extend(["## 逐页大纲", ""])
    for index, raw_page in enumerate(pages, start=1):
        if not isinstance(raw_page, dict):
            continue
        sequence = raw_page.get("sequence", index)
        page_id = raw_page.get("page_id", f"p{index:02d}")
        page_type = str(raw_page.get("page_type") or "content")
        title = str(raw_page.get("title") or "未命名页面")
        lines.append(f"### 第 {sequence} 页｜{title}")
        lines.append("")
        lines.append(f"- 页面编号：`{page_id}`")
        lines.append(f"- 页面类型：`{page_type}`")
        if raw_page.get("chapter_id"):
            lines.append(f"- 所属章节：`{raw_page['chapter_id']}`")
        if page_type == "content":
            fields = (
                ("故事线角色", raw_page.get("storyline_role")),
                ("承接前页", raw_page.get("transition_from_previous")),
                ("交给后页", raw_page.get("transition_to_next")),
                ("页面使命", raw_page.get("page_mission") or raw_page.get("page_job") or raw_page.get("business_question")),
                ("受众问题", raw_page.get("audience_question")),
                ("受众关注", "、".join(str(item) for item in raw_page.get("audience_concern_ids", [])) if isinstance(raw_page.get("audience_concern_ids"), list) else ""),
                ("受众相关性", raw_page.get("audience_relevance")),
                ("核心结论", raw_page.get("core_message") or raw_page.get("main_message")),
                ("上屏结论", raw_page.get("onscreen_conclusion") or raw_page.get("onscreen_judgment")),
                ("主视觉", raw_page.get("visual_center")),
                ("相对前页新增价值", raw_page.get("new_value_vs_previous")),
                ("留待后文", raw_page.get("reserved_for_later")),
            )
            for label, value in fields:
                if value:
                    lines.append(f"- {label}：{value}")
            exclusions = raw_page.get("must_not_include")
            if isinstance(exclusions, list) and exclusions:
                lines.append("- 本页不得混入：" + "；".join(str(item) for item in exclusions))
            if raw_page.get("split_risk"):
                risk = str(raw_page["split_risk"])
                reason = str(raw_page.get("split_risk_reason") or "")
                lines.append(f"- 拆页风险：`{risk}`" + (f"（{reason}）" if reason else ""))
            derivation = raw_page.get("core_message_derivation") or raw_page.get("judgment_derivation")
            if isinstance(derivation, dict) and derivation:
                refs = derivation.get("source_refs")
                if isinstance(refs, list) and refs:
                    lines.append("- 核心结论依据：" + "、".join(f"`{ref}`" for ref in refs))
                if derivation.get("derivation"):
                    lines.append(f"- 核心结论推导：{derivation['derivation']}")
            relations = raw_page.get("content_relations")
            if isinstance(relations, list) and relations:
                lines.extend(["", "  内容关系：", ""])
                for relation in relations:
                    if not isinstance(relation, dict):
                        continue
                    subject = str(relation.get("subject") or "")
                    predicate = str(relation.get("relation") or "")
                    objects = relation.get("objects") or relation.get("object") or ""
                    if isinstance(objects, list):
                        objects = "、".join(str(item) for item in objects)
                    lines.append(f"  - {subject} → `{predicate}` → {objects}")
            refs = raw_page.get("source_refs")
            if isinstance(refs, list) and refs:
                lines.append("- 证据 ID：" + "、".join(f"`{ref}`" for ref in refs))
            modules = raw_page.get("modules")
            if isinstance(modules, list) and modules:
                labels = []
                for module in modules:
                    if not isinstance(module, dict):
                        continue
                    name = str(module.get("title") or module.get("role") or "未命名模块")
                    role = str(module.get("role") or "")
                    labels.append(f"{name}（{role}）" if role else name)
                if labels:
                    lines.append("- 页面模块：" + "；".join(labels))
            content_units = raw_page.get("content_units") or raw_page.get("proof_points")
            if isinstance(content_units, list) and content_units:
                lines.extend(["", "  内容单元：", ""])
                for point in content_units:
                    if not isinstance(point, dict):
                        continue
                    claim = str(point.get("statement") or point.get("claim") or "").strip()
                    point_refs = point.get("source_refs")
                    suffix = ""
                    if isinstance(point_refs, list) and point_refs:
                        suffix = "（" + "、".join(str(ref) for ref in point_refs) + "）"
                    if claim:
                        lines.append(f"  - {claim}{suffix}")
            boundaries = raw_page.get("boundary_refs")
            if isinstance(boundaries, list) and boundaries:
                lines.append("- 边界证据：" + "、".join(f"`{ref}`" for ref in boundaries))
        lines.append("")

    issues = report.get("issues") if isinstance(report.get("issues"), list) else []
    lines.extend(["## 审计结论", ""])
    if issues:
        lines.append(f"当前有 {len(issues)} 个未关闭问题，大纲不得批准。")
        for issue in issues:
            if isinstance(issue, dict):
                lines.append(f"- `{issue.get('code', 'ISSUE')}`：{issue.get('message', '')}")
    else:
        lines.append("结构化大纲审计已通过；请人工确认架构、页数、章节边界和逐页核心结论。")
    lines.append("")
    return "\n".join(lines)


def _write_outline_markdown(
    path: Path, payload: dict[str, object], report: dict[str, object]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_outline_markdown(payload, report), encoding="utf-8")


def _escalation_options(codes: list[str]) -> list[dict[str, str]]:
    options = [
        {"id": "source_native", "label": "恢复源材料方案顺序", "action": "按材料角色和正式章节使命重建连续页面序列。"},
        {"id": "business_aggregation", "label": "按业务问题聚合", "action": "合并重复业务问题与视觉中心，重新分配页面密度。"},
    ]
    if "SOURCE_WEIGHT_DISTORTED" in codes or "SOLUTION_ARCHITECTURE_REQUIRED" in codes:
        options.append({"id": "user_priority", "label": "由用户明确优先级", "action": "提交主体内容权重冲突，请用户选择优先方向。"})
    return options[:3]


def run_outline_audit(
    project: Path,
    input_path: Path,
    max_attempts: int = 3,
    source_truth_path: Path | None = None,
    *,
    lightweight: bool = False,
) -> tuple[int, dict[str, object]]:
    if not lightweight and not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts must be between 1 through 5")
    project = project.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    semantic_gate = None if lightweight else assert_semantic_understanding_ready(project)
    communication_gate = None if lightweight else assert_communication_strategy_ready(project)
    director_gate = None if lightweight else assert_storyline_director_ready(project)
    if not lightweight:
        assert_escalation_resolved(project, "source_truth")
    payload = load_outline(input_path.expanduser().resolve(), lightweight=lightweight)
    resolved_source_truth = (
        source_truth_path.expanduser().resolve()
        if source_truth_path is not None
        else project
        / "workbench"
        / "stages"
        / "01-analysis"
        / "source-truth.json"
    )
    source_truth = (
        load_source_truth(resolved_source_truth)
        if resolved_source_truth.exists()
        else None
    )
    if source_truth_path is not None and source_truth is None:
        raise FileNotFoundError(f"source truth does not exist: {resolved_source_truth}")
    argument_model = None
    argument_model_path = project / SEMANTIC_ARGUMENT_MODEL
    if lightweight and argument_model_path.is_file():
        argument_model = load_model(argument_model_path)
    elif semantic_gate is not None and semantic_gate.get("semantic_argument_model_sha256"):
        argument_model = load_model(project / SEMANTIC_ARGUMENT_MODEL)
    retry = (
        payload.get("retry")
        if not lightweight and isinstance(payload.get("retry"), dict)
        else {}
    )
    attempt = int(retry.get("attempt", 1))
    effective_max = int(retry.get("max_attempts", max_attempts))
    if not lightweight and not 1 <= effective_max <= 5:
        raise ValueError("retry.max_attempts must be between 1 through 5")
    stage = project / "workbench" / "stages" / "01-analysis"
    argument_issues = (
        audit_argument_flow(payload, source_truth)
        if source_truth is not None
        else []
    )
    issues = audit_outline(payload, source_truth, argument_model)
    if not lightweight:
        issues.extend(
            _source_consumption_manifest_issues(
                project,
                payload,
                resolved_source_truth,
            )
        )
    argument_model_issues = (
        audit_outline_consumption(payload, argument_model)
        if payload.get("semantic_argument_model_mode") == "required" or argument_model is not None
        else []
    )
    if payload.get("semantic_argument_model_mode") == "required" or argument_model is not None:
        issues.extend(
            AuditIssue(
                item["code"],
                item["message"],
                (item["node_id"],) if item.get("node_id") else (),
                "rebuild_from_semantic_argument_model",
            )
            for item in argument_model_issues
        )
    if not lightweight:
        issues.extend(
            AuditIssue(
                item["code"], item["message"], (), item["retry_strategy"]
            )
            for item in semantic_binding_issues(payload, semantic_gate)
        )
        issues.extend(
            AuditIssue(
                item["code"], item["message"], (), item["retry_strategy"]
            )
            for item in communication_strategy_binding_issues(payload, communication_gate)
        )
        issues.extend(
            AuditIssue(
                item["code"],
                item["message"],
                tuple(str(page) for page in item.get("pages", [])),
                item["retry_strategy"],
            )
            for item in frontstage_posture_issues(payload, communication_gate)
        )
        issues.extend(
            AuditIssue(
                item["code"], item["message"], (), item["retry_strategy"]
            )
            for item in audience_concern_binding_issues(payload, communication_gate)
        )
        issues.extend(
            AuditIssue(
                item["code"], item["message"], (), item["retry_strategy"]
            )
            for item in storyline_director_binding_issues(payload, director_gate)
        )
    directive = retry_directive(issues, str(retry.get("strategy") or ""))
    content_review = (
        None
        if lightweight
        else _outline_content_review_status(project, payload, input_path, _sha256(input_path))
    )
    report: dict[str, object] = {
        "schema": "cyberppt.outline_audit.v1",
        # Keep editorial review as evidence, not a second approval gate.
        # The existing Stage 01 approval command is the single human gate.
        "status": "rewrite_required" if issues else "passed",
        "content_review": content_review,
        "content_review_gate": "advisory",
        "attempt": attempt,
        "max_attempts": effective_max,
        "remaining_attempts": max(0, effective_max - attempt),
        "issues": [issue.to_dict() for issue in issues],
        "retry_directive": directive,
        "argument_contract_mode": str(
            payload.get("argument_contract_mode") or "legacy"
        ),
        "semantic_contract_mode": (
            "source_relations"
            if payload.get("schema") == "cyberppt.outline.v2"
            else "legacy_argument_roles"
        ),
        "checked_source_truth": (
            str(resolved_source_truth) if source_truth is not None else None
        ),
        "semantic_argument_model": (
            str(project / SEMANTIC_ARGUMENT_MODEL) if argument_model is not None else None
        ),
        "semantic_argument_model_sha256": (
            semantic_gate.get("semantic_argument_model_sha256") if semantic_gate else None
        ),
        "argument_graph": argument_graph_summary(payload, source_truth),
        "argument_model_issues": argument_model_issues,
        "failed_edges": [
            list(edge)
            for issue in argument_issues
            for edge in issue.failed_edges
        ],
        "retry_scope": sorted(
            {
                page
                for issue in argument_issues
                for page in issue.pages
                if page
            }
        ),
        "reference_gate": (
            None if lightweight else snapshot_reference_gate("outline", project)
        ),
        "semantic_gate": semantic_gate,
        "communication_strategy_gate": communication_gate,
        "storyline_director_gate": director_gate,
        "mode": "lightweight" if lightweight else "controlled",
    }
    if lightweight:
        report.pop("reference_gate", None)
        report.pop("semantic_gate", None)
        report.pop("communication_strategy_gate", None)
        report.pop("storyline_director_gate", None)
        report.pop("semantic_argument_model_sha256", None)
        report.pop("attempt", None)
        report.pop("max_attempts", None)
        report.pop("remaining_attempts", None)
        report.pop("content_review", None)
        report.pop("content_review_gate", None)
        return (0 if not issues else 4), report

    _write_json(stage / "outline-contract.json", payload)
    _write_json(stage / "proposition-graph.json", build_proposition_graph(payload))
    _write_json(stage / "outline-audit.json", report)
    _write_json(stage / "outline-attempts" / f"attempt-{attempt:02d}.json", {"outline": payload, "audit": report})
    _write_outline_markdown(stage / "01-outline-readable.md", payload, report)
    if not issues:
        return 0, report
    if attempt < effective_max:
        return 4, report
    codes = list(directive["issue_codes"])
    report["status"] = "user_decision_required"
    report["options"] = _escalation_options(codes)
    _write_json(stage / "outline-audit.json", report)
    _write_json(stage / "outline-escalation.json", report)
    _write_outline_markdown(stage / "01-outline-readable.md", payload, report)
    return 5, report
