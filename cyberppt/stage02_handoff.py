"""Compile and audit the flexible Stage 01 -> Stage 02 field contract."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from cyberppt.artifact_ledger import write_json_atomic
from cyberppt.script_quality_contract import ScriptPage, parse_script_path
from cyberppt.semantic_digest import (
    outline_semantic_digest,
    script_semantic_digest,
    source_truth_semantic_digest,
)
from cyberppt.onscreen_expression import (
    VALID_EXPRESSION_FORMS,
    expression_constraints,
    resolve_onscreen_expression,
)


HANDOFF_DIR = Path("workbench/stages/02-handoff")
HANDOFF_JSON = HANDOFF_DIR / "stage02-handoff.json"
HANDOFF_MD = HANDOFF_DIR / "stage02-handoff-review.md"
HANDOFF_AUDIT = HANDOFF_DIR / "stage02-handoff-audit.json"
SCRIPT_PATH = Path("workbench/scripts/final/script-final.md")
OUTLINE_PATH = Path("workbench/stages/01-analysis/outline.json")
SOURCE_TRUTH_PATH = Path("workbench/stages/01-analysis/source-truth.json")
BODY_CANVAS = {"width": 2048, "height": 1024, "ratio": "2:1"}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_page_id(value: object, page_number: int | None = None) -> str:
    match = re.fullmatch(r"[pP]0*(\d+)", str(value or "").strip())
    number = int(match.group(1)) if match else int(page_number or 0)
    if number <= 0:
        raise ValueError(f"invalid page id: {value!r}")
    return f"p{number:02d}"


def _compact(value: object) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _file_binding(path: Path, semantic_digest: Callable[[Path], str]) -> dict[str, str]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"required Stage 02 handoff source is missing: {path}")
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "semantic_sha256": semantic_digest(path),
    }


def _source_binding(
    project: Path, relative: Path, semantic_digest: Callable[[Path], str]
) -> dict[str, str]:
    path = (project / relative).resolve()
    return _file_binding(path, semantic_digest)


def _handoff_authority(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the handoff fields that must remain identical for safe reuse.

    ``created_at`` deliberately stays outside this comparison: it is a receipt
    timestamp, not an input to Stage 02.  Every bound Stage 01 source carries
    a content digest, so a changed script, outline, Source Truth, or approval
    cannot be silently reused just because its path is unchanged.
    """

    return {
        "schema": payload.get("schema"),
        "project": payload.get("project"),
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
    items: list[str] = []
    seen: set[str] = set()
    for raw in page.onscreen_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*+]\s*", "", line)
        line = line.replace("**", "").strip()
        if not line:
            continue
        key = _compact(line)
        if key not in seen:
            seen.add(key)
            items.append(line)
    return items


def _locked_text_items(page: ScriptPage) -> list[dict[str, Any]]:
    """Give every locked body string a stable, page-scoped identity."""

    page_id = normalize_page_id(page.page_id, page.sequence).upper()
    return [
        {
            "text_id": f"{page_id}-T{index:02d}",
            "text": text,
            "ordinal": index,
        }
        for index, text in enumerate(_onscreen_items(page), start=1)
    ]


def _stage01_relationship_features(
    relationships: list[dict[str, Any]], visual_notes: str
) -> dict[str, Any]:
    """Preserve relationship-bearing Stage 01 language without promoting layout advice."""

    actors = list(dict.fromkeys(
        str(item.get("subject") or "").strip()
        for item in relationships
        if isinstance(item, dict) and str(item.get("subject") or "").strip()
    ))
    actions: list[dict[str, str]] = []
    for item in relationships:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject") or "").strip()
        relation = str(item.get("relation") or "").strip()
        for obj in item.get("objects") or []:
            text = str(obj or "").strip()
            if text:
                actions.append({"subject": subject, "relation": relation, "object": text})

    clauses = [
        value.strip(" ；。\n")
        for value in str(visual_notes or "").replace("\n", "；").split("；")
        if value.strip(" ；。\n")
    ]
    select = lambda tokens: [value for value in clauses if any(token in value for token in tokens)]
    return {
        "authority": "stage01_semantic_handoff",
        "actors": actors,
        "actions": actions,
        "directions": select(("进入", "形成", "转化", "承接", "汇聚", "贯通", "连接", "回到")),
        "conditions": select(("条件", "只有", "仅", "若", "如果", "通过后", "满足")),
        "branches": select(("分支", "互斥", "分别", "三类", "两类", "暂停", "终止", "再验证")),
        "feedback": select(("反馈", "回流", "闭环", "复盘", "迭代", "持续更新")),
        "source_visual_notes": str(visual_notes or "").strip(),
    }


def _page_record(page: ScriptPage, outline: dict[str, Any] | None) -> dict[str, Any]:
    receipt = page.contract_receipt if isinstance(page.contract_receipt, dict) else {}
    outline = outline or {}
    page_mission = str(receipt.get("page_mission") or outline.get("page_mission") or "")
    must_not_include = list(receipt.get("must_not_include") or outline.get("must_not_include") or [])
    consumed_content_unit_ids = list(
        receipt.get("consumed_content_unit_ids")
        or [
            str(item.get("unit_id") or "")
            for item in (outline.get("content_units") or [])
            if isinstance(item, dict) and str(item.get("unit_id") or "")
        ]
    )
    render_role = _render_role(page.page_type)
    business_relationships = [
        dict(item)
        for item in ((outline or {}).get("content_relations") or page.content_relations)
        if isinstance(item, dict)
    ]
    locked_text_items = _locked_text_items(page)
    relationship_features = _stage01_relationship_features(
        business_relationships, page.visual_structure
    )
    action_text = tuple(
        " ".join(
            str(item.get(field) or "")
            for field in ("subject", "relation", "object")
        ).strip()
        for item in relationship_features["actions"]
        if isinstance(item, dict)
    )
    expression = resolve_onscreen_expression(
        page,
        page_mission=page_mission,
        business_relationships=business_relationships,
        actions=action_text,
        topic_category=str(outline.get("topic_category") or ""),
    ).to_dict()
    constraints = expression_constraints(str(expression["form"]))
    record: dict[str, Any] = {
        "page_id": normalize_page_id(page.page_id, page.sequence),
        "page_number": page.sequence,
        "render_role": render_role,
        "argument_role": str(outline.get("argument_role") or ""),
        "title": page.title,
        "subtitle": page.subtitle,
        "page_mission": page_mission,
        "core_message": page.main_message,
        "full_prose": page.full_prose,
        "onscreen_text": page.onscreen_text,
        "onscreen_items": _onscreen_items(page),
        "locked_text_items": locked_text_items,
        "image_locked_text": page.image_locked_text,
        "editable_body_text": page.onscreen_text,
        "speaker_notes": page.speaker_notes,
        "source_refs": list(page.source_refs),
        "consumed_content_unit_ids": consumed_content_unit_ids,
        "must_not_include": must_not_include,
        "business_relationships": business_relationships,
        "onscreen_expression": expression,
        "expression_constraints": constraints,
        "field_provenance": {
            "content": "script-final.md",
            "page_mission": "script-page-contract-or-outline",
            "visual_structure": "stage02-generated",
            "style": "stage02-style-lock",
        },
    }
    if render_role != "content":
        record["stage02_visual_input"] = None
        return record

    # This is the complete Stage 01 semantic input for Stage 02 visual design.
    # It deliberately contains no visual decision, style, geometry, or prompt
    # copied from a previous Stage 02 run.
    record["stage02_visual_input"] = {
        "page_mission": page_mission,
        "core_message": page.main_message,
        "full_prose": page.full_prose,
        "onscreen_text": page.onscreen_text,
        "locked_text_items": locked_text_items,
        "module_titles": list(page.module_titles),
        "top_level_module_titles": list(page.top_level_module_titles),
        "business_relationships": business_relationships,
        "stage01_relationship_features": relationship_features,
        "onscreen_expression": expression,
        "expression_constraints": constraints,
        "author_visual_notes": page.visual_structure,
        "author_visual_notes_authority": "advisory_only",
        "must_not_include": must_not_include,
        "body_image_canvas": dict(BODY_CANVAS),
        "title_render_mode": "external_text_layer",
        "subtitle_render_mode": "external_text_layer",
    }
    return record


def build_stage02_handoff(
    project: Path,
    *,
    script: Path | None = None,
    lightweight_stage01_confirmed: bool = False,
) -> dict[str, Any]:
    # Kept for direct-call compatibility. Authorization is exclusively the
    # current full-script audit below.
    _ = lightweight_stage01_confirmed
    project = project.expanduser().resolve()
    script = script.expanduser().resolve() if script else (project / SCRIPT_PATH).resolve()
    if not script.is_file():
        raise FileNotFoundError(f"approved final script is missing: {script}")
    bindings = {
        "script": _file_binding(script, script_semantic_digest),
        "outline": _source_binding(project, OUTLINE_PATH, outline_semantic_digest),
        "source_truth": _source_binding(
            project, SOURCE_TRUTH_PATH, source_truth_semantic_digest
        ),
    }
    from cyberppt.commands.script_audit import run_script_audit

    code, audit = run_script_audit(project, script)
    if code != 0 or audit.get("status") != "passed":
        raise ValueError(
            "Stage 02 handoff requires a currently passed full-script audit"
        )

    document = parse_script_path(script)
    outline_payload = _read_json(project / OUTLINE_PATH)
    outline_pages = outline_payload.get("pages") if isinstance(outline_payload.get("pages"), list) else []
    outline_map = {
        normalize_page_id(item.get("page_id"), item.get("page_number")): item
        for item in outline_pages
        if isinstance(item, dict) and (item.get("page_id") or item.get("page_number"))
    }
    records = [
        _page_record(page, outline_map.get(normalize_page_id(page.page_id, page.sequence)))
        for page in document.pages
    ]
    payload = {
        "schema": "cyberppt.stage02_handoff.v1",
        "project": str(project),
        "created_at": _utc_now(),
        "source_bindings": bindings,
        "page_order": [record["page_id"] for record in records],
        "pages": records,
    }
    return payload


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
        "| 页面 | 渲染角色 | 论证角色 | 标题 | 页面使命 | 业务关系 | 作者视觉备注 | Stage 02 视觉输入 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for page in pages:
        visual_input = page.get("stage02_visual_input") or {}
        mission = str(page.get("page_mission") or "—").replace("|", "｜")
        lines.append(
            f"| {page['page_id']} | {page['render_role']} | {page.get('argument_role') or '—'} | "
            f"{str(page.get('title') or '').replace('|', '｜')} | {mission} | "
            f"{len(visual_input.get('business_relationships') or []) if visual_input else '—'} | "
            f"{visual_input.get('author_visual_notes_authority') or '—'} | "
            f"{'已具备' if visual_input else '—'} |"
        )
    if report:
        lines.extend(["", "## 审计问题", ""])
        issues = list(report.get("blocking_issues") or []) + list(report.get("warnings") or [])
        if issues:
            lines.extend(f"- `{item['code']}` {item['message']}" for item in issues)
        else:
            lines.append("- 无。")
    return "\n".join(lines) + "\n"


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
    expected_bindings: dict[str, tuple[Path | None, Callable[[Path], str]]] = {
        "script": (None, script_semantic_digest),
        "outline": ((project / OUTLINE_PATH).resolve(), outline_semantic_digest),
    }
    source_truth = (project / SOURCE_TRUTH_PATH).resolve()
    if source_truth.is_file():
        expected_bindings["source_truth"] = (source_truth, source_truth_semantic_digest)

    for name, (expected_path, semantic_digest) in expected_bindings.items():
        binding = bindings.get(name)
        if not isinstance(binding, dict) or not binding.get("path"):
            issue(
                "HANDOFF_BINDING_STALE",
                f"Binding {name} is absent or incomplete for the current Stage 01 authority.",
            )
            continue
        path = Path(str(binding["path"])).expanduser().resolve()
        if name == "script":
            expected_path = path
        if not path.is_file():
            issue("HANDOFF_BINDING_MISSING", f"Binding {name} is missing: {path}")
            continue
        if expected_path is not None and path != expected_path:
            issue(
                "HANDOFF_BINDING_STALE",
                f"Binding {name} path changed: recorded {path}, current {expected_path}.",
            )
            continue
        current_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            current_semantic_sha256 = semantic_digest(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issue(
                "HANDOFF_BINDING_STALE",
                f"Binding {name} semantic digest cannot be read from {path}: {exc}",
            )
            continue
        if (
            binding.get("sha256") != current_sha256
            or binding.get("semantic_sha256") != current_semantic_sha256
        ):
            issue(
                "HANDOFF_BINDING_STALE",
                f"Binding {name} sha256 or semantic_sha256 differs from the current file: {path}",
            )

    for name, binding in bindings.items():
        if name in expected_bindings:
            continue
        if not isinstance(binding, dict) or not binding.get("path"):
            issue("HANDOFF_BINDING_INVALID", f"Binding {name} is incomplete.")
            continue
        path = Path(str(binding["path"])).expanduser().resolve()
        if not path.is_file():
            issue("HANDOFF_BINDING_MISSING", f"Binding {name} is missing: {path}")

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
        if not isinstance(expression, dict):
            warning("ONSCREEN_EXPRESSION_MISSING", f"{page_id} has no onscreen expression decision.")
        else:
            if str(expression.get("form") or "") not in VALID_EXPRESSION_FORMS:
                issue("ONSCREEN_EXPRESSION_FORM_INVALID", f"{page_id} has an invalid onscreen expression form.")
            if str(expression.get("source") or "") not in {"explicit", "relation", "scored", "fallback"}:
                issue("ONSCREEN_EXPRESSION_SOURCE_INVALID", f"{page_id} has an invalid onscreen expression source.")
            confidence = expression.get("confidence")
            if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
                issue("ONSCREEN_EXPRESSION_CONFIDENCE_INVALID", f"{page_id} has invalid onscreen expression confidence.")
        visual_input = page.get("stage02_visual_input") or {}
        expected_constraints: dict[str, object] | None = None
        if isinstance(expression, dict) and str(expression.get("form") or "") in VALID_EXPRESSION_FORMS:
            expected_constraints = expression_constraints(str(expression["form"]))
        page_constraints = page.get("expression_constraints")
        visual_constraints = visual_input.get("expression_constraints")
        if (
            expected_constraints is None
            or page_constraints != expected_constraints
            or visual_constraints != expected_constraints
        ):
            issue(
                "ONSCREEN_EXPRESSION_CONSTRAINTS_INVALID",
                f"{page_id} expression constraints must match the registered profile for its form.",
            )
        if visual_input.get("body_image_canvas") != BODY_CANVAS:
            issue("BODY_IMAGE_CANVAS_INVALID", f"{page_id} body image canvas must be 2048x1024 (2:1).")
        locked_items = visual_input.get("locked_text_items")
        if not isinstance(locked_items, list) or not locked_items:
            issue("LOCKED_TEXT_ITEMS_MISSING", f"{page_id} has no stable locked body-text items.")
        else:
            ids = [str(item.get("text_id") or "") for item in locked_items if isinstance(item, dict)]
            texts = [str(item.get("text") or "") for item in locked_items if isinstance(item, dict)]
            if len(ids) != len(locked_items) or any(not value for value in ids) or len(ids) != len(set(ids)):
                issue("LOCKED_TEXT_IDS_INVALID", f"{page_id} locked body-text ids must be non-empty and unique.")
            if texts != list(page.get("onscreen_items") or []):
                issue("LOCKED_TEXT_ORDER_DRIFTED", f"{page_id} locked body text must match onscreen_items exactly and in order.")
        relationships = visual_input.get("business_relationships")
        if not isinstance(relationships, list):
            issue("BUSINESS_RELATIONSHIPS_INVALID", f"{page_id} business_relationships must be an array.")
        features = visual_input.get("stage01_relationship_features")
        if not isinstance(features, dict):
            issue("STAGE01_RELATIONSHIP_FEATURES_MISSING", f"{page_id} has no structured Stage 01 relationship features.")
        else:
            if features.get("authority") != "stage01_semantic_handoff":
                issue("STAGE01_RELATIONSHIP_FEATURES_AUTHORITY_INVALID", f"{page_id} relationship features have invalid authority.")
            if not isinstance(features.get("actions"), list) or not features.get("actions"):
                issue("STAGE01_RELATIONSHIP_ACTIONS_MISSING", f"{page_id} has no structured subject-action-object features.")
        if visual_input.get("author_visual_notes_authority") != "advisory_only":
            issue("AUTHOR_VISUAL_NOTES_AUTHORITY_INVALID", f"{page_id} author visual notes must be advisory only.")

    status = "passed" if not blocking else "failed"
    return {
        "schema": "cyberppt.stage02_handoff_audit.v1",
        "status": status,
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
) -> dict[str, Any]:
    # Kept for direct-call compatibility; it cannot authorize Stage 02.
    _ = lightweight_stage01_confirmed
    project = project.expanduser().resolve()
    payload = build_stage02_handoff(
        project,
        script=script,
    )
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
    (project / HANDOFF_MD).write_text(render_handoff_markdown(payload, report), encoding="utf-8")
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
