"""Stage 02 file-input boundary.

Stage 02 accepts one script file, snapshots it into its own workspace, and
builds every downstream visual/production artifact from that snapshot. The
producer of the file is intentionally unknown to this module.

This module must not discover Stage 01 state or legacy handoff artifacts. Legacy
migration support belongs outside the canonical Stage 02 runtime.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any

from cyberppt.artifact_ledger import write_json_atomic
from cyberppt.content_integrity_contract import (
    build_content_integrity_contract,
    extract_onscreen_line_items,
)
from cyberppt.onscreen_expression import expression_constraints, resolve_onscreen_expression
from cyberppt.script_quality_contract import ScriptPage, parse_script_markdown
from cyberppt.semantic_verifier import verify_semantic_proposals
from cyberppt.stage02_semantic_intake import normalize_semantic_proposals
from cyberppt.topology_resolver import resolve_semantic_topology
from cyberppt.visual_structure_contract import normalize_page_id


INPUT_DIR = Path("workbench/stages/02-input")
INPUT_JSON = INPUT_DIR / "script-intake.json"
INPUT_AUDIT = INPUT_DIR / "script-intake-audit.json"
INPUT_REVIEW = INPUT_DIR / "script-intake-review.md"
INPUT_SCRIPT_PATH = Path("workbench/inputs/final-script.md")
BODY_CANVAS = {"width": 2048, "height": 1024, "ratio": "2:1"}


_DIRECTED_TOPOLOGIES = {
    "sequence",
    "dependency_chain",
    "causal_chain",
    "feedback_loop",
    "layered_structure",
    "support_convergence",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_role(page_type: str) -> str:
    return {
        "cover": "cover",
        "contents": "agenda",
        "agenda": "agenda",
        "chapter": "section",
        "section": "section",
        "closing": "ending",
        "ending": "ending",
        "content": "content",
    }.get(page_type, "content")


def _onscreen_items(page: ScriptPage) -> list[str]:
    return [text for text, _indent in extract_onscreen_line_items(page.onscreen_text)]


def _locked_text_items(page: ScriptPage) -> list[dict[str, Any]]:
    page_id = normalize_page_id(page.page_id, page.sequence).upper()
    return [
        {
            "text_id": f"{page_id}-T{index:02d}",
            "text": text,
            "ordinal": index,
        }
        for index, text in enumerate(_onscreen_items(page), start=1)
    ]


def _relationship_features(
    relationships: list[dict[str, Any]],
    visual_notes: str,
    *,
    authority: str,
) -> dict[str, Any]:
    actors = list(
        dict.fromkeys(
            str(item.get("subject") or "").strip()
            for item in relationships
            if isinstance(item, dict) and str(item.get("subject") or "").strip()
        )
    )
    actions: list[dict[str, Any]] = []
    for item in relationships:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject") or "").strip()
        relation = str(item.get("relation") or "").strip()
        for raw in item.get("objects") or []:
            object_ = str(raw or "").strip()
            if object_:
                actions.append(
                    {"subject": subject, "relation": relation, "object": object_}
                )

    notes = re.split(
        r"\n\s*-\s*【(?:视觉结构，不上屏|演讲者备注)】",
        str(visual_notes or ""),
        maxsplit=1,
    )[0]
    clauses = [
        value.strip(" ；。\n")
        for value in notes.replace("\n", "；").split("；")
        if value.strip(" ；。\n")
    ]

    def select(tokens: tuple[str, ...]) -> list[str]:
        return [value for value in clauses if any(token in value for token in tokens)]

    return {
        "authority": authority,
        "actors": actors,
        "actions": actions,
        "directions": select(("进入", "形成", "转化", "承接", "汇聚", "贯通", "连接", "回到")),
        "conditions": select(("条件", "只有", "仅", "若", "如果", "通过后", "满足")),
        "branches": select(("分支", "互斥", "分别", "三类", "两类", "暂停", "终止", "再验证")),
        "feedback": select(("反馈", "回流", "复盘", "迭代", "持续更新", "回到")),
        "source_visual_notes": notes.strip(),
    }


def _reject_invalid_authoritative_relations(
    page_id: str,
    verification: dict[str, Any],
) -> None:
    blockers = [
        item
        for item in verification.get("verdicts") or []
        if isinstance(item, dict)
        and str(item.get("verdict") or "") in {"rejected", "unresolved"}
        and str(item.get("constraint_authority") or "soft") in {"hard", "strong"}
    ]
    if not blockers:
        return

    details = "; ".join(
        f"{item.get('proposal_id') or '?'}:{item.get('verdict')}:"
        f"{','.join(item.get('conflict_codes') or [])}"
        for item in blockers
    )
    raise ValueError(
        f"input script relationship contract is invalid for {page_id}: {details}"
    )


def _page_record(page: ScriptPage) -> dict[str, Any]:
    page_mission = str(page.page_mission or page.main_message)
    source_refs = tuple(page.source_refs)
    render_role = _render_role(page.page_type)
    content_load = page.content_load or "standard"
    business_relationships = [
        dict(item) for item in page.content_relations if isinstance(item, dict)
    ]

    input_features = _relationship_features(
        business_relationships,
        page.visual_structure,
        authority="input_script",
    )
    proposals = list(
        normalize_semantic_proposals(
            business_relationships,
            default_source_refs=source_refs,
            origin="input_file",
        )
    )
    page_text = "\n".join(
        (page_mission, page.main_message, page.full_prose, page.onscreen_text)
    )
    verification = verify_semantic_proposals(
        proposals,
        page_text=page_text,
        visual_notes=page.visual_structure,
    )
    verified_relationships = [
        dict(item)
        for item in verification.get("verified_relationships") or []
        if isinstance(item, dict)
    ]
    _reject_invalid_authoritative_relations(page.page_id, verification)

    verified_features = _relationship_features(
        verified_relationships,
        page.visual_structure,
        authority="stage02_semantic_verifier",
    )
    render_topology = resolve_semantic_topology(
        verified_relationships,
        module_count=len(page.top_level_module_titles),
        page_text=page_text,
    )
    has_direction = any(
        bool(
            str(item.get("direction") or "").strip()
            or str(item.get("condition") or "").strip()
        )
        for item in business_relationships
    )
    prompt_mode = (
        "directed_composition"
        if str(render_topology.get("primary_topology") or "") in _DIRECTED_TOPOLOGIES
        and has_direction
        else "semantic_brief"
    )

    action_text = tuple(
        " ".join(
            str(item.get(field) or "")
            for field in ("subject", "relation", "object")
        ).strip()
        for item in input_features["actions"]
        if isinstance(item, dict)
    )
    expression = resolve_onscreen_expression(
        page,
        page_mission=page_mission,
        business_relationships=business_relationships,
        actions=action_text,
        topic_category="",
        semantic_topology=render_topology,
    ).to_dict()
    expression["constraint_authority"] = str(
        render_topology.get("constraint_authority") or "soft"
    )
    constraints = expression_constraints(str(expression["form"]))
    locked_text_items = _locked_text_items(page)
    content_integrity = build_content_integrity_contract(page).to_dict()
    receipt = page.contract_receipt if isinstance(page.contract_receipt, dict) else {}
    expression_ir = (
        receipt.get("onscreen_expression_ir")
        if isinstance(receipt.get("onscreen_expression_ir"), dict)
        else None
    )

    record: dict[str, Any] = {
        "page_id": normalize_page_id(page.page_id, page.sequence),
        "page_number": page.sequence,
        "render_role": render_role,
        "argument_role": "",
        "title": page.title,
        "subtitle": page.subtitle,
        "content_load": content_load,
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
        "argument_chain": page.argument_chain,
        "prompt_mode": prompt_mode,
        "business_relationships": business_relationships,
        "semantic_proposals": proposals,
        "semantic_verification": verification,
        "verified_business_relationships": verified_relationships,
        "render_topology": render_topology,
        "onscreen_expression": expression,
        "onscreen_expression_ir": expression_ir,
        "expression_constraints": constraints,
        "field_provenance": {
            "content": "input_script",
            "business_relationships": "input_script",
            "render_topology": "stage02_derived",
            "visual_structure": "stage02_derived",
            "style": "stage02_owned",
        },
    }
    if render_role != "content":
        record["stage02_visual_input"] = None
        return record

    record["stage02_visual_input"] = {
        "page_mission": page_mission,
        "core_message": page.main_message,
        "full_prose": page.full_prose,
        "content_load": content_load,
        "argument_chain": page.argument_chain,
        "prompt_mode": prompt_mode,
        "onscreen_text": page.onscreen_text,
        "locked_text_items": locked_text_items,
        "content_integrity": content_integrity,
        "module_titles": list(page.module_titles),
        "top_level_module_titles": list(page.top_level_module_titles),
        "business_relationships": business_relationships,
        "input_relationship_features": input_features,
        "semantic_proposals": proposals,
        "semantic_verification": verification,
        "verified_business_relationships": verified_relationships,
        "verified_relationship_features": verified_features,
        "render_topology": render_topology,
        "relationship_authority": "input_file_authoritative",
        "onscreen_expression": expression,
        "onscreen_expression_ir": expression_ir,
        "expression_constraints": constraints,
        "constraint_authority": expression["constraint_authority"],
        "author_visual_notes": page.visual_structure,
        "author_visual_notes_authority": "advisory_only",
        "must_not_include": [],
        "body_image_canvas": dict(BODY_CANVAS),
        "title_render_mode": "external_text_layer",
        "subtitle_render_mode": "external_text_layer",
    }
    return record


def input_path(project: Path) -> Path:
    """Return the canonical Stage 02 intake path.

    No legacy handoff discovery is allowed here. Migration code must opt into a
    compatibility adapter explicitly instead of becoming part of normal Stage 02
    execution.
    """

    return project.expanduser().resolve() / INPUT_JSON


def _load_current_input(project: Path) -> dict[str, Any] | None:
    path = input_path(project)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def snapshot_input_script(project: Path, source_script: Path) -> Path:
    project = project.expanduser().resolve()
    source = source_script.expanduser().resolve()
    target = (project / INPUT_SCRIPT_PATH).resolve()

    if source == target:
        if not target.is_file():
            raise FileNotFoundError(f"Stage 02 script snapshot is missing: {target}")
        return target

    if source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return target

    if target.is_file():
        payload = _load_current_input(project)
        binding = (payload or {}).get("source_bindings", {}).get("script", {})
        recorded = str(binding.get("source_path") or "").strip()
        if (
            recorded
            and Path(recorded).expanduser().resolve() == source
            and binding.get("sha256") == _sha256(target)
        ):
            return target

    raise FileNotFoundError(f"Stage 02 script input is missing: {source}")


def resolve_input_script(project: Path, source_script: Path) -> Path:
    project = project.expanduser().resolve()
    source = source_script.expanduser().resolve()
    target = (project / INPUT_SCRIPT_PATH).resolve()
    payload = _load_current_input(project)

    if payload and payload.get("schema") == "cyberppt.stage02_script_input.v1":
        binding = (payload.get("source_bindings") or {}).get("script") or {}
        recorded = str(binding.get("source_path") or "").strip()
        if recorded and Path(recorded).expanduser().resolve() == source:
            if (
                source.is_file()
                and binding.get("source_sha256")
                and binding.get("source_sha256") != _sha256(source)
            ):
                raise ValueError(
                    "Stage 02 script input changed; rebuild Stage 02 visual artifacts "
                    "from the updated file"
                )
            if target.is_file() and binding.get("sha256") == _sha256(target):
                return target

    if source == target and source.is_file():
        return source

    raise ValueError(
        "Stage 02 script input is not prepared for this file; prepare the Stage 02 "
        "visual stage again"
    )


def build_stage02_input(project: Path, *, script: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    source = script.expanduser().resolve()
    snapshot = snapshot_input_script(project, source)

    # Parse exactly the snapshotted file and explicitly disable sidecar loading.
    document = parse_script_markdown(
        snapshot.read_text(encoding="utf-8-sig"),
        page_contracts={},
    )
    records = [_page_record(page) for page in document.pages]
    binding: dict[str, Any] = {
        "scope": "project",
        "path": INPUT_SCRIPT_PATH.as_posix(),
        "sha256": _sha256(snapshot),
        # Kept for serialized-contract compatibility. It is intentionally the
        # same raw file digest; Stage 02 does not invoke Stage 01 semantic digest.
        "semantic_sha256": _sha256(snapshot),
        "source_path": str(source),
    }
    if source.is_file():
        binding["source_sha256"] = _sha256(source)
        binding["source_semantic_sha256"] = _sha256(source)

    return {
        "schema": "cyberppt.stage02_script_input.v1",
        "project": str(project),
        "created_at": _utc_now(),
        "source_bindings": {"script": binding},
        "page_order": [record["page_id"] for record in records],
        "pages": records,
    }


def input_page_map(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        int(page.get("page_number") or 0): page
        for page in payload.get("pages") or []
        if isinstance(page, dict) and int(page.get("page_number") or 0) > 0
    }


def audit_stage02_input(
    project: Path,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = project.expanduser().resolve()
    path = input_path(project)
    if payload is None:
        payload = _load_current_input(project)
        if payload is None:
            return {
                "schema": "cyberppt.stage02_script_input_audit.v1",
                "status": "failed",
                "blocking_issues": [
                    {
                        "code": "INPUT_MISSING",
                        "message": f"Stage 02 script input is missing: {path}",
                    }
                ],
            }

    issues: list[dict[str, str]] = []
    if payload.get("schema") != "cyberppt.stage02_script_input.v1":
        issues.append(
            {
                "code": "INPUT_SCHEMA_INVALID",
                "message": "Unsupported Stage 02 input schema.",
            }
        )
    else:
        binding = (payload.get("source_bindings") or {}).get("script") or {}
        snapshot = (project / str(binding.get("path") or INPUT_SCRIPT_PATH)).resolve()
        if not snapshot.is_file() or binding.get("sha256") != _sha256(snapshot):
            issues.append(
                {
                    "code": "INPUT_SNAPSHOT_STALE",
                    "message": "Stage 02-owned script snapshot is missing or changed.",
                }
            )

        source_path = str(binding.get("source_path") or "").strip()
        if source_path:
            source = Path(source_path).expanduser()
            if (
                source.is_file()
                and binding.get("source_sha256")
                and binding.get("source_sha256") != _sha256(source.resolve())
            ):
                issues.append(
                    {
                        "code": "INPUT_SOURCE_CHANGED",
                        "message": (
                            "The supplied script file changed after Stage 02 prepared "
                            "its input snapshot."
                        ),
                    }
                )

        if not isinstance(payload.get("pages"), list) or not payload.get("pages"):
            issues.append(
                {
                    "code": "INPUT_PAGES_MISSING",
                    "message": "Stage 02 script input contains no pages.",
                }
            )

    return {
        "schema": "cyberppt.stage02_script_input_audit.v1",
        "status": "passed" if not issues else "failed",
        "blocking_issues": issues,
    }


def prepare_stage02_input(
    project: Path,
    *,
    script: Path,
    reuse_current: bool = True,
) -> dict[str, Any]:
    project = project.expanduser().resolve()
    source = script.expanduser().resolve()
    current = project / INPUT_JSON

    if reuse_current and current.is_file():
        existing = _load_current_input(project)
        binding = (existing or {}).get("source_bindings", {}).get("script", {})
        recorded = str(binding.get("source_path") or "").strip()
        same_source = bool(recorded) and Path(recorded).expanduser().resolve() == source
        source_fresh = (
            not source.is_file()
            or not binding.get("source_sha256")
            or binding.get("source_sha256") == _sha256(source)
        )
        report = audit_stage02_input(project, existing)
        if same_source and source_fresh and report.get("status") == "passed":
            report["reused"] = True
            return report

    payload = build_stage02_input(project, script=source)
    current.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(current, payload)
    report = audit_stage02_input(project, payload)
    write_json_atomic(project / INPUT_AUDIT, report)
    (project / INPUT_REVIEW).write_text(
        "# Stage 02 script input\n\n"
        + "\n".join(
            f"- P{page['page_number']:02d} {page.get('title', '')}"
            for page in payload.get("pages") or []
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    report["reused"] = False
    return report


def load_stage02_input(
    project: Path,
    *,
    required: bool = False,
) -> dict[str, Any] | None:
    path = input_path(project)
    if not path.is_file():
        if required:
            raise FileNotFoundError(f"Stage 02 script input is missing: {path}")
        return None

    payload = _load_current_input(project)
    report = audit_stage02_input(project, payload)
    if required and report.get("status") != "passed":
        raise ValueError("Stage 02 script input is invalid or stale")
    return payload


__all__ = [
    "BODY_CANVAS",
    "INPUT_AUDIT",
    "INPUT_DIR",
    "INPUT_JSON",
    "INPUT_REVIEW",
    "INPUT_SCRIPT_PATH",
    "audit_stage02_input",
    "build_stage02_input",
    "input_page_map",
    "input_path",
    "load_stage02_input",
    "prepare_stage02_input",
    "resolve_input_script",
    "snapshot_input_script",
]
