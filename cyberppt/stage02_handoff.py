"""Compile and audit the governed Stage 01 -> Stage 02 semantic handoff."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from cyberppt.artifact_ledger import write_json_atomic
from cyberppt.content_integrity_contract import (
    CONTENT_INTEGRITY_SCHEMA,
    build_content_integrity_contract,
    extract_onscreen_line_items,
    structure_hash_from_node_dicts,
)
from cyberppt.script_quality_contract import ScriptPage, parse_script_path
from cyberppt.script_quality.models import ScriptDocument
from cyberppt.semantic_digest import script_semantic_digest
from cyberppt.stage02_semantic_intake import normalize_semantic_proposals
from cyberppt.semantic_verifier import verify_semantic_proposals
from cyberppt.topology_resolver import resolve_semantic_topology
from cyberppt.onscreen_expression import (
    VALID_EXPRESSION_FORMS,
    expression_constraints,
    resolve_onscreen_expression,
)
from cyberppt.visual_structure_contract import normalize_page_id, read_json as _read_json


HANDOFF_DIR = Path("workbench/stages/02-handoff")
HANDOFF_JSON = HANDOFF_DIR / "stage02-handoff.json"
HANDOFF_MD = HANDOFF_DIR / "stage02-handoff-review.md"
HANDOFF_AUDIT = HANDOFF_DIR / "stage02-handoff-audit.json"
SCRIPT_PATH = Path("workbench/scripts/final/script-final.md")
BODY_CANVAS = {"width": 2048, "height": 1024, "ratio": "2:1"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _compact(value: object) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _file_binding(
    path: Path,
    semantic_digest: Callable[[Path], str],
    *,
    project: Path | None = None,
) -> dict[str, str]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"required Stage 02 handoff source is missing: {path}")
    binding = {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "semantic_sha256": semantic_digest(path),
    }
    if project is not None:
        project = project.expanduser().resolve()
        if _is_within(path, project):
            binding["scope"] = "project"
            binding["path"] = path.relative_to(project).as_posix()
    return binding


def _relocated_project_path(project: Path, raw_path: str) -> Path | None:
    """Resolve a legacy absolute project path after the project was moved.

    Older handoffs stored Windows or POSIX absolute paths.  When the original
    path is unavailable, recover only the suffix below this exact project
    directory name; hashes still decide whether the recovered file is valid.
    """

    normalized = raw_path.replace("\\", "/")
    marker = f"/{project.name}/"
    if marker not in f"/{normalized.lstrip('/')}":
        return None
    suffix = f"/{normalized.lstrip('/')}".split(marker, 1)[1]
    candidate = (project / suffix).resolve()
    return candidate if _is_within(candidate, project) else None


def _resolve_binding_path(
    project: Path,
    binding: dict[str, Any],
    *,
    field: str = "path",
) -> Path | None:
    raw = str(binding.get(field) or "").strip()
    if not raw:
        return None
    if field == "path" and binding.get("scope") == "project":
        candidate = (project / raw).resolve()
        return candidate if _is_within(candidate, project) else None
    candidate = Path(raw).expanduser()
    if candidate.is_absolute() and candidate.is_file():
        return candidate.resolve()
    relocated = _relocated_project_path(project, raw)
    if relocated is not None and relocated.is_file():
        return relocated
    return candidate.resolve()


def ensure_project_script(project: Path, script: Path) -> Path:
    """Persist an external final script under the project's canonical path.

    Stage 02 may receive a script outside the project.  The project copy is the
    durable authority for handoff and resume; the external path remains only
    provenance.  If the external source is temporarily unavailable, reuse the
    copy only when the existing handoff proves that it came from that exact
    path and still has the bound bytes.
    """

    project = project.expanduser().resolve()
    requested = script.expanduser().resolve()
    target = (project / SCRIPT_PATH).resolve()
    formal = (project / "script" / "dist" / "final-script.md").resolve()
    if requested in {target, formal}:
        if not requested.is_file():
            raise FileNotFoundError(f"approved final script is missing: {requested}")
        return requested

    if requested.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        if requested != target:
            shutil.copyfile(requested, target)
        return target

    if target.is_file():
        handoff_path = project / HANDOFF_JSON
        if handoff_path.is_file():
            try:
                payload = _read_json(handoff_path)
            except (OSError, json.JSONDecodeError, ValueError):
                payload = None
            binding = (payload or {}).get("source_bindings", {}).get("script", {})
            external_path = _resolve_binding_path(
                project, binding, field="external_path"
            )
            if (
                external_path == requested
                and binding.get("sha256") == hashlib.sha256(target.read_bytes()).hexdigest()
            ):
                return target

    raise FileNotFoundError(f"approved final script is missing: {requested}")


def _handoff_authority(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": payload.get("schema"),
        "project": payload.get("project"),
        "planning_policy": payload.get("planning_policy"),
        "source_bindings": payload.get("source_bindings"),
        "page_order": payload.get("page_order"),
        "pages": payload.get("pages"),
    }


def _render_role(page_type: str) -> str:
    aliases = {
        "cover": "cover",
        "contents": "agenda",
        "agenda": "agenda",
        "chapter": "section",
        "section": "section",
        "closing": "ending",
        "ending": "ending",
        "content": "content",
    }
    return aliases.get(page_type, "content")


def _onscreen_items(page: ScriptPage) -> list[str]:
    return [text for text, _indent in extract_onscreen_line_items(page.onscreen_text)]


def _locked_text_items(page: ScriptPage) -> list[dict[str, Any]]:
    page_id = normalize_page_id(page.page_id, page.sequence).upper()
    return [
        {"text_id": f"{page_id}-T{index:02d}", "text": text, "ordinal": index}
        for index, text in enumerate(_onscreen_items(page), start=1)
    ]


def _relationship_features(
    relationships: list[dict[str, Any]], visual_notes: str, *, authority: str
) -> dict[str, Any]:
    actors = list(dict.fromkeys(
        str(item.get("subject") or "").strip()
        for item in relationships
        if isinstance(item, dict) and str(item.get("subject") or "").strip()
    ))
    actions: list[dict[str, Any]] = []
    for item in relationships:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject") or "").strip()
        relation = str(item.get("relation") or "").strip()
        for obj in item.get("objects") or []:
            text = str(obj or "").strip()
            if not text:
                continue
            action: dict[str, Any] = {"subject": subject, "relation": relation, "object": text}
            for field in (
                "direction", "condition", "modality", "basis", "confidence",
                "origin", "authority", "constraint_authority", "proposal_id",
                "proposal_verdict", "proposed_relation",
            ):
                if field in item:
                    action[field] = item[field]
            actions.append(action)

    visual_note = re.split(
        r"\n\s*-\s*【(?:视觉结构，不上屏|演讲者备注)】",
        str(visual_notes or ""),
        maxsplit=1,
    )[0]
    clauses = [
        value.strip(" ；。\n")
        for value in visual_note.replace("\n", "；").split("；")
        if value.strip(" ；。\n")
    ]
    select = lambda tokens: [value for value in clauses if any(token in value for token in tokens)]
    return {
        "authority": authority,
        "actors": actors,
        "actions": actions,
        "directions": select(("进入", "形成", "转化", "承接", "汇聚", "贯通", "连接", "回到")),
        "conditions": select(("条件", "只有", "仅", "若", "如果", "通过后", "满足")),
        "branches": select(("分支", "互斥", "分别", "三类", "两类", "暂停", "终止", "再验证")),
        "feedback": select(("反馈", "回流", "复盘", "迭代", "持续更新", "回到")),
        "source_visual_notes": visual_note.strip(),
    }


def _stage01_relationship_features(
    relationships: list[dict[str, Any]], visual_notes: str
) -> dict[str, Any]:
    return _relationship_features(
        relationships,
        visual_notes,
        authority="stage01_semantic_handoff",
    )


def _verified_relationship_features(
    relationships: list[dict[str, Any]], visual_notes: str
) -> dict[str, Any]:
    return _relationship_features(
        relationships,
        visual_notes,
        authority="stage02_semantic_verifier",
    )


def _visual_relationship_contract(
    raw_relationships: list[dict[str, Any]],
    proposals: list[dict[str, Any]],
    verification: dict[str, Any],
    verified_relationships: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Choose the relationship collection exposed to the legacy visual interface.

    Source/author/structured relations that the verifier accepts unchanged stay
    byte-compatible with the existing workbench contract.  Model/script/adapter
    inference, or anything refined/rejected/unresolved, is replaced by the
    verifier-canonical relationship set so the visual stage cannot re-promote a
    bad upstream proposal simply because an older consumer reads the legacy
    ``business_relationships`` field.
    """

    verdicts = [
        item for item in verification.get("verdicts") or [] if isinstance(item, dict)
    ]
    changed = any(
        str(item.get("verdict") or "") in {"refined", "rejected", "unresolved"}
        for item in verdicts
    )
    soft = any(
        str(item.get("constraint_authority") or "soft") == "soft"
        for item in proposals
    )
    if changed or soft:
        return [dict(item) for item in verified_relationships], "stage02_semantic_verifier"
    return [dict(item) for item in raw_relationships], "stage01_authoritative"


def _page_record(page: ScriptPage, outline: dict[str, Any] | None) -> dict[str, Any]:
    receipt = page.contract_receipt if isinstance(page.contract_receipt, dict) else {}
    outline = outline or {}
    receipt_logic = receipt.get("page_logic_contract")
    expression_ir = receipt.get("onscreen_expression_ir")
    if not isinstance(expression_ir, dict) and isinstance(receipt_logic, dict):
        expression_ir = receipt_logic.get("onscreen_expression")
    if not isinstance(expression_ir, dict):
        expression_ir = None
    page_mission = str(
        receipt.get("page_mission")
        or outline.get("page_mission")
        or outline.get("logic")
        or page.page_mission
        or page.main_message
    )
    must_not_include = list(receipt.get("must_not_include") or outline.get("must_not_include") or [])
    consumed_content_unit_ids = list(
        receipt.get("consumed_content_unit_ids")
        or [
            str(item.get("unit_id") or "")
            for item in (outline.get("content_units") or [])
            if isinstance(item, dict) and str(item.get("unit_id") or "")
        ]
    )
    source_refs = tuple(
        page.source_refs
        or tuple(
            str(value)
            for value in outline.get("source_refs") or []
            if str(value)
        )
    )
    render_role = _render_role(page.page_type)
    business_relationships = [
        dict(item)
        for item in ((outline or {}).get("content_relations") or page.content_relations)
        if isinstance(item, dict)
    ]
    locked_text_items = _locked_text_items(page)
    content_integrity = build_content_integrity_contract(page).to_dict()
    upstream_features = _stage01_relationship_features(business_relationships, page.visual_structure)

    proposals = list(normalize_semantic_proposals(
        business_relationships,
        default_source_refs=source_refs,
        origin="stage01",
    ))
    verification = verify_semantic_proposals(
        proposals,
        page_text="\n".join((page_mission, page.main_message, page.full_prose, page.onscreen_text)),
        visual_notes=page.visual_structure,
    )
    verified_relationships = [
        dict(item)
        for item in verification.get("verified_relationships") or []
        if isinstance(item, dict)
    ]
    verified_features = _verified_relationship_features(verified_relationships, page.visual_structure)
    semantic_topology = resolve_semantic_topology(
        verified_relationships,
        module_count=len(page.top_level_module_titles),
        page_text="\n".join((page_mission, page.main_message, page.full_prose, page.onscreen_text)),
    )
    explicit_prompt_mode = str(
        receipt.get("stage02_prompt_mode")
        or outline.get("stage02_prompt_mode")
        or ""
    ).strip()
    if explicit_prompt_mode and explicit_prompt_mode not in {
        "semantic_brief",
        "directed_composition",
    }:
        raise ValueError(
            f"unsupported Stage 02 prompt mode for {page.page_id}: {explicit_prompt_mode}"
        )
    directed_topologies = {
        "sequence",
        "dependency_chain",
        "causal_chain",
        "feedback_loop",
        "layered_structure",
        "support_convergence",
    }
    has_explicit_directed_relationship = any(
        str(item.get("basis") or "").strip() == "explicit"
        and bool(
            str(item.get("direction") or "").strip()
            or str(item.get("condition") or "").strip()
            or str(item.get("relation") or "").strip()
        )
        for item in business_relationships
    )
    prompt_mode = explicit_prompt_mode or (
        "directed_composition"
        if (
            str(semantic_topology.get("constraint_authority") or "") == "hard"
            and str(semantic_topology.get("primary_topology") or "") in directed_topologies
            and has_explicit_directed_relationship
        )
        else "semantic_brief"
    )
    visual_relationships, visual_relationship_source = _visual_relationship_contract(
        business_relationships,
        proposals,
        verification,
        verified_relationships,
    )
    visual_features = _stage01_relationship_features(visual_relationships, page.visual_structure)
    visual_features.update({
        "semantic_verification_status": verification.get("status"),
        "semantic_topology": semantic_topology,
        "constraint_authority": semantic_topology.get("constraint_authority") or "soft",
        "relationship_source": visual_relationship_source,
    })

    action_text = tuple(
        " ".join(str(item.get(field) or "") for field in ("subject", "relation", "object")).strip()
        for item in verified_features["actions"]
        if isinstance(item, dict)
    )
    expression = resolve_onscreen_expression(
        page,
        page_mission=page_mission,
        business_relationships=verified_relationships,
        actions=action_text,
        topic_category=str(outline.get("topic_category") or ""),
        semantic_topology=semantic_topology,
    ).to_dict()
    expression["constraint_authority"] = str(semantic_topology.get("constraint_authority") or "soft")
    constraints = expression_constraints(str(expression["form"]))

    record: dict[str, Any] = {
        "page_id": normalize_page_id(page.page_id, page.sequence),
        "page_number": page.sequence,
        "render_role": render_role,
        "argument_role": str(outline.get("argument_role") or outline.get("page_role") or ""),
        "title": page.title,
        "subtitle": page.subtitle,
        "page_mission": page_mission,
        "core_message": page.main_message,
        "full_prose": page.full_prose,
        "onscreen_text": page.onscreen_text,
        "onscreen_items": _onscreen_items(page),
        "locked_text_items": locked_text_items,
        "content_integrity": content_integrity,
        "image_locked_text": page.image_locked_text,
        "editable_body_text": page.onscreen_text,
        "speaker_notes": page.speaker_notes,
        "source_refs": list(source_refs),
        "provenance_refs": list(page.provenance_refs),
        "argument_chain": page.argument_chain or str(outline.get("argument_chain") or ""),
        "prompt_mode": prompt_mode,
        "consumed_content_unit_ids": consumed_content_unit_ids,
        "must_not_include": must_not_include,
        "business_relationships": business_relationships,
        "semantic_proposals": proposals,
        "semantic_verification": verification,
        "verified_business_relationships": verified_relationships,
        "semantic_topology": semantic_topology,
        "onscreen_expression": expression,
        "onscreen_expression_ir": expression_ir,
        "expression_constraints": constraints,
        "field_provenance": {
            "content": "script-final.md",
            "page_mission": (
                "script-final.md"
                if page.page_mission
                else "script-page-contract-or-deck-plan"
                if receipt.get("page_mission") or outline.get("page_mission") or outline.get("logic")
                else "core-message-compatibility-fallback"
            ),
            "argument_chain": "script-final.md" if page.argument_chain else "deck-plan",
            "provenance_refs": "script-final.md",
            "business_relationships": "stage01-proposal",
            "verified_business_relationships": "stage02-semantic-verifier",
            "semantic_topology": "stage02-topology-resolver",
            "onscreen_expression_ir": "stage01-author-declared",
            "visual_structure": "stage02-generated",
            "style": "stage02-style-lock",
        },
    }
    for field in ("source_heading_ids", "primary_source_heading_id", "subtitle_policy"):
        if field in outline:
            value = outline[field]
            record[field] = list(value) if isinstance(value, list) else dict(value) if isinstance(value, dict) else value

    if render_role != "content":
        record["stage02_visual_input"] = None
        return record

    record["stage02_visual_input"] = {
        "page_mission": page_mission,
        "core_message": page.main_message,
        "full_prose": page.full_prose,
        "argument_chain": page.argument_chain or str(outline.get("argument_chain") or ""),
        "prompt_mode": prompt_mode,
        "onscreen_text": page.onscreen_text,
        "locked_text_items": locked_text_items,
        "content_integrity": content_integrity,
        "module_titles": list(page.module_titles),
        "top_level_module_titles": list(page.top_level_module_titles),
        # Compatibility-facing fields contain verified semantics whenever the
        # upstream relation was inferred or the verifier changed it.
        "business_relationships": visual_relationships,
        "stage01_relationship_features": visual_features,
        # Raw upstream material remains separately auditable.
        "upstream_business_relationships": business_relationships,
        "upstream_relationship_features": upstream_features,
        "semantic_proposals": proposals,
        "semantic_verification": verification,
        "verified_business_relationships": verified_relationships,
        "verified_relationship_features": verified_features,
        "semantic_topology": semantic_topology,
        "relationship_authority": visual_relationship_source,
        "onscreen_expression": expression,
        "onscreen_expression_ir": expression_ir,
        "expression_constraints": constraints,
        "constraint_authority": expression["constraint_authority"],
        "author_visual_notes": page.visual_structure,
        "author_visual_notes_authority": "advisory_only",
        "must_not_include": must_not_include,
        "body_image_canvas": dict(BODY_CANVAS),
        "title_render_mode": "external_text_layer",
        "subtitle_render_mode": "external_text_layer",
    }
    return record


def _deck_plan_page_map(
    project: Path,
    requested_script: Path,
    document: ScriptDocument,
) -> dict[str, dict[str, Any]]:
    """Load only legacy strict planning data for a project-owned script.

    Lean Deck Plans are transitional outlines.  Stage 02 consumes the locked
    Final Script directly and must not freeze tentative PLAN wording.
    """

    try:
        requested_script.relative_to(project / "script")
    except ValueError:
        return {}
    plan_path = project / "script" / "deck-plan.json"
    if not plan_path.is_file():
        return {}
    payload = _read_json(plan_path)
    if payload.get("plan_contract_version") == 2 and payload.get("planning_profile") == "lean":
        return {}
    pages = {
        normalize_page_id(item.get("id") or item.get("page_id")):
        item
        for item in payload.get("pages") or []
        if isinstance(item, dict) and (item.get("id") or item.get("page_id"))
    }
    for page in document.pages:
        page_id = normalize_page_id(page.page_id, page.sequence)
        plan = pages.get(page_id)
        if plan is None:
            raise ValueError(f"DECK_PLAN_SCRIPT_DRIFT: {page_id} is absent from deck-plan.json")
        plan_title = str(plan.get("title") or "").strip()
        plan_message = str(plan.get("message") or plan.get("core_message") or "").strip()
        if (plan_title and plan_title != page.title) or (
            plan_message and plan_message != page.main_message
        ):
            raise ValueError(
                f"DECK_PLAN_SCRIPT_DRIFT: {page_id} title or core judgment differs from final-script.md"
            )
    return pages


def build_stage02_handoff(
    project: Path,
    *,
    script: Path | None = None,
    lightweight_stage01_confirmed: bool = False,
    allow_script_edit: bool = False,
) -> dict[str, Any]:
    _ = lightweight_stage01_confirmed, allow_script_edit
    project = project.expanduser().resolve()
    requested_script = script.expanduser().resolve() if script else (project / SCRIPT_PATH).resolve()
    script = ensure_project_script(project, requested_script)
    bindings = {
        "script": _file_binding(
            script, script_semantic_digest, project=project
        )
    }
    if requested_script != script:
        external: dict[str, Any] = {
            "source_mode": "external_script",
            "external_path": str(requested_script),
        }
        if requested_script.is_file():
            external.update(
                {
                    "external_sha256": hashlib.sha256(
                        requested_script.read_bytes()
                    ).hexdigest(),
                    "external_semantic_sha256": script_semantic_digest(
                        requested_script
                    ),
                }
            )
        else:
            handoff_path = project / HANDOFF_JSON
            if handoff_path.is_file():
                previous = _read_json(handoff_path).get("source_bindings", {}).get(
                    "script", {}
                )
                for key in ("external_sha256", "external_semantic_sha256"):
                    if previous.get(key):
                        external[key] = previous[key]
        bindings["script"].update(external)
    document = parse_script_path(script)
    deck_plan_pages = _deck_plan_page_map(project, requested_script, document)
    records = [
        _page_record(
            page,
            deck_plan_pages.get(normalize_page_id(page.page_id, page.sequence)),
        )
        for page in document.pages
    ]
    return {
        "schema": "cyberppt.stage02_handoff.v1",
        "project": str(project),
        "created_at": _utc_now(),
        "source_bindings": bindings,
        "page_order": [record["page_id"] for record in records],
        "pages": records,
    }


def render_handoff_markdown(payload: dict[str, Any], report: dict[str, Any] | None = None) -> str:
    pages = list(payload.get("pages") or [])
    content = [page for page in pages if page.get("render_role") == "content"]
    templates = [page for page in pages if page.get("render_role") != "content"]
    lines = [
        "# Stage 01 → Stage 02 字段交接审阅",
        "",
        f"- 页面总数：{len(pages)}",
        f"- 内容页：{len(content)}",
        f"- 模板页：{len(templates)}",
        f"- 审计状态：{(report or {}).get('status', 'pending')}",
        "",
        "| 页面 | 渲染角色 | 标题 | 上游关系 | 校验关系 | 语义拓扑 | 约束权威 | Stage 02 视觉输入 |",
        "|---|---|---|---:|---:|---|---|---|",
    ]
    for page in pages:
        visual = page.get("stage02_visual_input") or {}
        topology = visual.get("semantic_topology") or {}
        lines.append(
            f"| {page['page_id']} | {page['render_role']} | {str(page.get('title') or '').replace('|', '｜')} | "
            f"{len(visual.get('upstream_business_relationships') or visual.get('business_relationships') or []) if visual else '—'} | "
            f"{len(visual.get('verified_business_relationships') or []) if visual else '—'} | "
            f"{topology.get('primary_topology') or '—'} | "
            f"{visual.get('constraint_authority') or '—'} | "
            f"{'已具备' if visual else '—'} |"
        )
    if report:
        lines.extend(["", "## 审计问题", ""])
        issues = list(report.get("blocking_issues") or []) + list(report.get("warnings") or [])
        if issues:
            lines.extend(f"- `{item['code']}` {item['message']}" for item in issues)
        else:
            lines.append("- 无。")
    return "\n".join(lines) + "\n"


def _has_verifier_contract(page: dict[str, Any], visual: dict[str, Any], expression: object) -> bool:
    """Return True only for handoffs authored by the verifier-aware pipeline.

    Existing v1 handoff fixtures and already-approved projects remain readable.
    Once any verifier field is present, however, the complete verifier contract
    becomes mandatory so partially migrated handoffs cannot silently bypass the
    new semantic safeguards.
    """

    verifier_fields = {
        "semantic_proposals",
        "semantic_verification",
        "verified_business_relationships",
        "verified_relationship_features",
        "semantic_topology",
    }
    if any(field in visual for field in verifier_fields):
        return True
    if any(field in page for field in ("semantic_proposals", "semantic_verification", "semantic_topology")):
        return True
    return isinstance(expression, dict) and str(expression.get("source") or "") == "verified_topology"


def _audit_content_integrity(
    page_id: str,
    visual: dict[str, Any],
    locked_items: object,
    issue: Callable[[str, str], None],
) -> None:
    contract = visual.get("content_integrity")
    if not isinstance(contract, dict) or contract.get("schema") != CONTENT_INTEGRITY_SCHEMA:
        issue("CONTENT_STRUCTURE_MISSING", f"{page_id} has no valid content integrity contract.")
        return
    nodes = contract.get("nodes")
    if not isinstance(nodes, list) or not all(isinstance(node, dict) for node in nodes):
        issue("CONTENT_STRUCTURE_MISSING", f"{page_id} content integrity contract has no nodes.")
        return

    node_ids = {str(node.get("text_id") or "") for node in nodes}
    if len(node_ids) != len(nodes) or any(not value for value in node_ids):
        issue("CONTENT_PARENT_INVALID", f"{page_id} content integrity nodes must have non-empty, unique text_ids.")
        return
    for node in nodes:
        parent_id = node.get("parent_id")
        if parent_id is not None and str(parent_id) not in node_ids:
            issue("CONTENT_PARENT_INVALID", f"{page_id} content node {node.get('text_id')} has an unresolved parent_id.")

    expected_roots = [str(node.get("text_id")) for node in nodes if node.get("parent_id") is None]
    if list(contract.get("root_nodes") or []) != expected_roots:
        issue("CONTENT_ROOT_INVALID", f"{page_id} root_nodes must match every node whose parent_id is null, in order.")

    try:
        expected_order = [
            str(node.get("text_id"))
            for node in sorted(nodes, key=lambda item: item.get("ordinal") if isinstance(item.get("ordinal"), int) else -1)
        ]
    except TypeError:
        expected_order = []
    if list(contract.get("source_order") or []) != expected_order:
        issue("CONTENT_ORDER_INVALID", f"{page_id} source_order must match nodes sorted by ordinal.")
    elif isinstance(locked_items, list) and locked_items:
        locked_ids = [str(item.get("text_id") or "") for item in locked_items if isinstance(item, dict)]
        if locked_ids != expected_order:
            issue("CONTENT_ORDER_INVALID", f"{page_id} content integrity text_ids must match locked_text_items exactly.")

    for node in nodes:
        is_root = node.get("parent_id") is None
        expected_role = "root_module" if is_root else "detail"
        if node.get("content_role") != expected_role:
            issue("CONTENT_ROLE_INVALID", f"{page_id} content node {node.get('text_id')} has content_role {node.get('content_role')!r}, expected {expected_role!r}.")
        expected_policy = "root_only" if is_root else "forbidden"
        if node.get("promotion_policy") != expected_policy:
            issue("CONTENT_PROMOTION_POLICY_INVALID", f"{page_id} content node {node.get('text_id')} has promotion_policy {node.get('promotion_policy')!r}, expected {expected_policy!r}.")

    if contract.get("structure_hash") != structure_hash_from_node_dicts(nodes):
        issue("CONTENT_STRUCTURE_HASH_INVALID", f"{page_id} content integrity structure_hash does not match its own nodes.")


def audit_stage02_handoff(project: Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    project = project.expanduser().resolve()
    handoff_path = project / HANDOFF_JSON
    payload = payload or _read_json(handoff_path)
    blocking: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    def issue(code: str, message: str) -> None:
        blocking.append({"code": code, "message": message})

    def warning(code: str, message: str) -> None:
        warnings.append({"code": code, "message": message})

    if payload.get("schema") != "cyberppt.stage02_handoff.v1":
        issue("HANDOFF_SCHEMA_INVALID", "Stage 02 handoff schema is invalid.")
    bindings = payload.get("source_bindings")
    if not isinstance(bindings, dict):
        issue("HANDOFF_BINDINGS_MISSING", "Source bindings are missing.")
        bindings = {}
    for name, semantic_digest in {"script": script_semantic_digest}.items():
        binding = bindings.get(name)
        if not isinstance(binding, dict) or not binding.get("path"):
            issue("HANDOFF_BINDING_STALE", f"Binding {name} is absent or incomplete for the current Stage 01 authority.")
            continue
        path = _resolve_binding_path(project, binding)
        if path is None or not path.is_file():
            issue(
                "HANDOFF_BINDING_MISSING",
                f"Binding {name} is missing: {binding.get('path')}",
            )
            continue
        current_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            current_semantic_sha256 = semantic_digest(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issue("HANDOFF_BINDING_STALE", f"Binding {name} semantic digest cannot be read from {path}: {exc}")
            continue
        if binding.get("sha256") != current_sha256 or binding.get("semantic_sha256") != current_semantic_sha256:
            issue("HANDOFF_BINDING_STALE", f"Binding {name} sha256 or semantic_sha256 differs from the current file: {path}")
            continue
        if name == "script" and binding.get("source_mode") == "external_script":
            upstream = _resolve_binding_path(
                project, binding, field="external_path"
            )
            if upstream is not None and upstream.is_file():
                upstream_sha256 = hashlib.sha256(upstream.read_bytes()).hexdigest()
                upstream_semantic_sha256 = semantic_digest(upstream)
                expected_upstream_sha256 = binding.get("external_sha256")
                expected_upstream_semantic = binding.get(
                    "external_semantic_sha256"
                )
                upstream_changed = (
                    expected_upstream_sha256
                    and expected_upstream_sha256 != upstream_sha256
                ) or (
                    expected_upstream_semantic
                    and expected_upstream_semantic != upstream_semantic_sha256
                )
                snapshot_drift = (
                    upstream_sha256 != current_sha256
                    or upstream_semantic_sha256 != current_semantic_sha256
                )
                if upstream_changed or snapshot_drift:
                    issue(
                        "HANDOFF_UPSTREAM_SCRIPT_STALE",
                        "The external/upstream final script differs from the bound project snapshot; "
                        f"rerun prepare-stage02-handoff: {upstream}",
                    )

    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        issue("HANDOFF_PAGES_MISSING", "Handoff pages are missing.")
        pages = []
    seen: set[str] = set()
    content_count = 0
    template_count = 0
    for page in pages:
        if not isinstance(page, dict):
            issue("HANDOFF_PAGE_INVALID", "A handoff page is not an object.")
            continue
        page_id = normalize_page_id(page.get("page_id"), page.get("page_number"))
        if page_id in seen:
            issue("HANDOFF_PAGE_DUPLICATE", f"Duplicate handoff page: {page_id}")
        seen.add(page_id)
        if page_id != str(page.get("page_id")):
            issue("HANDOFF_PAGE_ID_NOT_NORMALIZED", f"Page id must be normalized: {page_id}")
        role = str(page.get("render_role") or "")
        if role not in {"cover", "agenda", "section", "content", "ending"}:
            issue("HANDOFF_RENDER_ROLE_INVALID", f"{page_id} has invalid render_role: {role}")
        if role != "content":
            template_count += 1
            if page.get("stage02_visual_input") is not None:
                issue("TEMPLATE_PAGE_HAS_VISUAL_PRODUCTION", f"{page_id} template page has visual production fields.")
            continue

        content_count += 1
        for field in ("title", "page_mission", "core_message", "onscreen_text"):
            if not str(page.get(field) or "").strip():
                issue("HANDOFF_REQUIRED_FIELD_MISSING", f"{page_id} is missing {field}.")

        expression = page.get("onscreen_expression")
        visual = page.get("stage02_visual_input") or {}
        verifier_contract = _has_verifier_contract(page, visual, expression)
        if not isinstance(expression, dict):
            warning("ONSCREEN_EXPRESSION_MISSING", f"{page_id} has no onscreen expression decision.")
        else:
            if str(expression.get("form") or "") not in VALID_EXPRESSION_FORMS:
                issue("ONSCREEN_EXPRESSION_FORM_INVALID", f"{page_id} has an invalid onscreen expression form.")
            if str(expression.get("source") or "") not in {"explicit", "verified_topology", "relation", "scored", "fallback"}:
                issue("ONSCREEN_EXPRESSION_SOURCE_INVALID", f"{page_id} has an invalid onscreen expression source.")
            confidence = expression.get("confidence")
            if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
                issue("ONSCREEN_EXPRESSION_CONFIDENCE_INVALID", f"{page_id} has invalid onscreen expression confidence.")
            if verifier_contract and str(expression.get("constraint_authority") or "") not in {"hard", "strong", "soft"}:
                issue("ONSCREEN_EXPRESSION_AUTHORITY_INVALID", f"{page_id} has invalid expression constraint authority.")

        expected_constraints: dict[str, object] | None = None
        if isinstance(expression, dict) and str(expression.get("form") or "") in VALID_EXPRESSION_FORMS:
            expected_constraints = expression_constraints(str(expression["form"]))
        if expected_constraints is None or page.get("expression_constraints") != expected_constraints or visual.get("expression_constraints") != expected_constraints:
            issue("ONSCREEN_EXPRESSION_CONSTRAINTS_INVALID", f"{page_id} expression constraints must match the registered profile for its form.")

        if visual.get("body_image_canvas") != BODY_CANVAS:
            issue("BODY_IMAGE_CANVAS_INVALID", f"{page_id} body image canvas must be 2048x1024 (2:1).")
        locked_items = visual.get("locked_text_items")
        if not isinstance(locked_items, list) or not locked_items:
            issue("LOCKED_TEXT_ITEMS_MISSING", f"{page_id} has no stable locked body-text items.")
        else:
            ids = [str(item.get("text_id") or "") for item in locked_items if isinstance(item, dict)]
            texts = [str(item.get("text") or "") for item in locked_items if isinstance(item, dict)]
            if len(ids) != len(locked_items) or any(not value for value in ids) or len(ids) != len(set(ids)):
                issue("LOCKED_TEXT_IDS_INVALID", f"{page_id} locked body-text ids must be non-empty and unique.")
            if texts != list(page.get("onscreen_items") or []):
                issue("LOCKED_TEXT_ORDER_DRIFTED", f"{page_id} locked body text must match onscreen_items exactly and in order.")

        _audit_content_integrity(page_id, visual, locked_items, issue)

        relationships = visual.get("business_relationships")
        if not isinstance(relationships, list):
            issue("BUSINESS_RELATIONSHIPS_INVALID", f"{page_id} business_relationships must be an array.")
            relationships = []

        if verifier_contract:
            proposals = visual.get("semantic_proposals")
            verification = visual.get("semantic_verification")
            verified = visual.get("verified_business_relationships")
            topology = visual.get("semantic_topology")
            if not isinstance(proposals, list):
                issue("SEMANTIC_PROPOSALS_INVALID", f"{page_id} semantic_proposals must be an array.")
            if not isinstance(verification, dict) or verification.get("schema") != "cyberppt.semantic_verification.v1":
                issue("SEMANTIC_VERIFICATION_INVALID", f"{page_id} has no valid semantic verification receipt.")
            if not isinstance(verified, list):
                issue("VERIFIED_BUSINESS_RELATIONSHIPS_INVALID", f"{page_id} verified_business_relationships must be an array.")
                verified = []
            if not isinstance(topology, dict) or topology.get("schema") != "cyberppt.semantic_topology.v1":
                issue("SEMANTIC_TOPOLOGY_INVALID", f"{page_id} has no valid semantic topology receipt.")
                topology = {}
            elif str(topology.get("constraint_authority") or "") not in {"hard", "strong", "soft"}:
                issue("SEMANTIC_TOPOLOGY_AUTHORITY_INVALID", f"{page_id} topology has invalid constraint authority.")
            if str(topology.get("primary_topology") or "") != "peer_set" and isinstance(expression, dict) and expression.get("form") == "parallel_classification_3_6":
                issue("PARALLEL_EXPRESSION_WITHOUT_VERIFIED_PEER_TOPOLOGY", f"{page_id} cannot use parallel_classification without a verified peer_set topology.")
            verified_features = visual.get("verified_relationship_features")
            if not isinstance(verified_features, dict) or verified_features.get("authority") != "stage02_semantic_verifier":
                issue("VERIFIED_RELATIONSHIP_FEATURES_MISSING", f"{page_id} has no verifier-derived relationship features.")
            elif not isinstance(verified_features.get("actions"), list) or (verified and not verified_features.get("actions")):
                issue("VERIFIED_RELATIONSHIP_ACTIONS_MISSING", f"{page_id} verified relations have no structured subject-action-object features.")

        features = visual.get("stage01_relationship_features")
        if not isinstance(features, dict):
            issue("STAGE01_RELATIONSHIP_FEATURES_MISSING", f"{page_id} has no structured Stage 01 relationship features.")
        else:
            if features.get("authority") != "stage01_semantic_handoff":
                issue("STAGE01_RELATIONSHIP_FEATURES_AUTHORITY_INVALID", f"{page_id} relationship features have invalid authority.")
            if not isinstance(features.get("actions"), list) or (relationships and not features.get("actions")):
                issue("STAGE01_RELATIONSHIP_ACTIONS_MISSING", f"{page_id} has no structured subject-action-object features.")
        if visual.get("author_visual_notes_authority") != "advisory_only":
            issue("AUTHOR_VISUAL_NOTES_AUTHORITY_INVALID", f"{page_id} author visual notes must be advisory only.")

    return {
        "schema": "cyberppt.stage02_handoff_audit.v1",
        "status": "passed" if not blocking else "failed",
        "handoff": str(handoff_path.resolve()),
        "page_count": len(pages),
        "content_page_count": content_count,
        "template_page_count": template_count,
        "blocking_issues": blocking,
        "warnings": warnings,
        "audited_at": _utc_now(),
    }


def prepare_stage02_handoff(
    project: Path,
    *,
    script: Path | None = None,
    lightweight_stage01_confirmed: bool = False,
    reuse_current_handoff: bool = False,
    allow_script_edit: bool = False,
) -> dict[str, Any]:
    _ = lightweight_stage01_confirmed
    project = project.expanduser().resolve()
    payload = build_stage02_handoff(project, script=script, allow_script_edit=allow_script_edit)
    handoff_path = project / HANDOFF_JSON
    if reuse_current_handoff and handoff_path.is_file():
        try:
            current = _read_json(handoff_path)
        except (OSError, json.JSONDecodeError, ValueError):
            current = None
        if current is not None and _handoff_authority(current) == _handoff_authority(payload):
            report = audit_stage02_handoff(project, current)
            if report.get("status") == "passed":
                return {**report, "reused": True}

    write_json_atomic(handoff_path, payload)
    report = audit_stage02_handoff(project, payload)
    write_json_atomic(project / HANDOFF_AUDIT, report)
    (project / HANDOFF_MD).write_text(render_handoff_markdown(payload, report), encoding="utf-8", newline="\n")
    return report


def load_stage02_handoff(project: Path, *, required: bool = False) -> dict[str, Any] | None:
    project = project.expanduser().resolve()
    path = project / HANDOFF_JSON
    if not path.is_file():
        if required:
            raise FileNotFoundError(f"Stage 02 handoff is missing: {path}")
        return None
    payload = _read_json(path)
    report = audit_stage02_handoff(project, payload)
    if report["status"] != "passed":
        codes = ", ".join(item["code"] for item in report["blocking_issues"])
        raise ValueError(f"Stage 02 handoff is invalid or stale: {codes}")
    return payload


def handoff_page_map(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        int(page["page_number"]): page
        for page in payload.get("pages") or []
        if isinstance(page, dict) and page.get("page_number")
    }


__all__ = [
    "HANDOFF_AUDIT",
    "HANDOFF_JSON",
    "HANDOFF_MD",
    "audit_stage02_handoff",
    "build_stage02_handoff",
    "handoff_page_map",
    "load_stage02_handoff",
    "normalize_page_id",
    "prepare_stage02_handoff",
    "render_handoff_markdown",
]
