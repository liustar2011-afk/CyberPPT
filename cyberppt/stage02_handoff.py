"""Compile and audit the flexible Stage 01 -> Stage 02 field contract."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.artifact_ledger import write_json_atomic
from cyberppt.script_quality_contract import ScriptPage, parse_script_path


HANDOFF_DIR = Path("workbench/stages/02-handoff")
HANDOFF_JSON = HANDOFF_DIR / "stage02-handoff.json"
HANDOFF_MD = HANDOFF_DIR / "stage02-handoff-review.md"
HANDOFF_AUDIT = HANDOFF_DIR / "stage02-handoff-audit.json"
SCRIPT_PATH = Path("workbench/scripts/final/script-final.md")
SCRIPT_APPROVAL = Path("workbench/approvals/stage01-script-approved.md")
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


def _source_binding(project: Path, relative: Path) -> dict[str, str]:
    path = (project / relative).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"required Stage 02 handoff source is missing: {path}")
    return {"path": str(path)}


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


def _page_record(page: ScriptPage, outline: dict[str, Any] | None) -> dict[str, Any]:
    receipt = page.contract_receipt if isinstance(page.contract_receipt, dict) else {}
    render_role = _render_role(page.page_type)
    record: dict[str, Any] = {
        "page_id": normalize_page_id(page.page_id, page.sequence),
        "page_number": page.sequence,
        "render_role": render_role,
        "argument_role": str((outline or {}).get("argument_role") or ""),
        "title": page.title,
        "subtitle": page.subtitle,
        "page_mission": str(receipt.get("page_mission") or ""),
        "core_message": page.main_message,
        "full_prose": page.full_prose,
        "onscreen_text": page.onscreen_text,
        "onscreen_items": _onscreen_items(page),
        "image_locked_text": page.image_locked_text,
        "editable_body_text": page.onscreen_text,
        "speaker_notes": page.speaker_notes,
        "source_refs": list(page.source_refs),
        "consumed_content_unit_ids": list(receipt.get("consumed_content_unit_ids") or []),
        "must_not_include": list(receipt.get("must_not_include") or []),
        "field_provenance": {
            "content": "script-final.md",
            "page_mission": "script-page-contract",
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
        "page_mission": str(receipt.get("page_mission") or ""),
        "core_message": page.main_message,
        "full_prose": page.full_prose,
        "onscreen_text": page.onscreen_text,
        "module_titles": list(page.module_titles),
        "top_level_module_titles": list(page.top_level_module_titles),
        "approved_stage01_visual_structure": page.visual_structure,
        "source_refs": list(page.source_refs),
        "must_not_include": list(receipt.get("must_not_include") or []),
        "body_image_canvas": dict(BODY_CANVAS),
        "title_render_mode": "external_text_layer",
        "subtitle_render_mode": "external_text_layer",
    }
    return record


def build_stage02_handoff(project: Path, *, script: Path | None = None) -> dict[str, Any]:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve() if script else (project / SCRIPT_PATH).resolve()
    if not script.is_file():
        raise FileNotFoundError(f"approved final script is missing: {script}")

    # The handoff requires an explicit Stage 01 approval record, but does not
    # freeze the approved files. This repository is a single-user script tool,
    # so in-place edits are consumed immediately by the next handoff build.
    approval_path = project / SCRIPT_APPROVAL
    if not approval_path.is_file():
        raise FileNotFoundError(f"Stage 01 script approval is missing: {approval_path}")

    bindings = {
        "script": {"path": str(script)},
        "script_approval": _source_binding(project, SCRIPT_APPROVAL),
        "outline": _source_binding(project, OUTLINE_PATH),
        "source_truth": _source_binding(project, SOURCE_TRUTH_PATH),
    }

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
        "| 页面 | 渲染角色 | 论证角色 | 标题 | 页面使命 | Stage 02 视觉输入 |",
        "|---|---|---|---|---|---|",
    ]
    for page in pages:
        visual_input = page.get("stage02_visual_input") or {}
        mission = str(page.get("page_mission") or "—").replace("|", "｜")
        lines.append(
            f"| {page['page_id']} | {page['render_role']} | {page.get('argument_role') or '—'} | "
            f"{str(page.get('title') or '').replace('|', '｜')} | {mission} | "
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

    if payload.get("schema") != "cyberppt.stage02_handoff.v1":
        issue("HANDOFF_SCHEMA_INVALID", "Stage 02 handoff schema is invalid.")
    bindings = payload.get("source_bindings")
    if not isinstance(bindings, dict):
        issue("HANDOFF_BINDINGS_MISSING", "Source bindings are missing.")
        bindings = {}
    for name, binding in bindings.items():
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
        visual_input = page.get("stage02_visual_input") or {}
        if visual_input.get("body_image_canvas") != BODY_CANVAS:
            issue("BODY_IMAGE_CANVAS_INVALID", f"{page_id} body image canvas must be 2048x1024 (2:1).")

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


def prepare_stage02_handoff(project: Path, *, script: Path | None = None) -> dict[str, Any]:
    project = project.expanduser().resolve()
    payload = build_stage02_handoff(project, script=script)
    handoff_path = project / HANDOFF_JSON
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
