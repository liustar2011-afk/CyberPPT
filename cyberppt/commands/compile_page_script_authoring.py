"""Compile the formal page-authoring JSON into chapter draft Markdown."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cyberppt.onscreen_text_rules import strip_terminal_punctuation
from cyberppt.onscreen_expression import validate_expression_form


AUTHORING_SCHEMA = "cyberppt.page_script_authoring.v1"
RECEIPT_SCHEMA = "cyberppt.page_contract_receipt.v2"
CONTENT_FIELDS = ("prose", "selection", "onscreen", "visual", "notes", "consumes")
RECEIPT_FIELDS = (
    "page_mission",
    "audience_question",
    "business_question",
    "must_not_include",
    "split_risk",
    "split_risk_reason",
    "core_message",
    "onscreen_conclusion",
    "core_message_derivation",
    "content_relations",
    "onscreen_conclusion_mode",
    "new_value_vs_previous",
    "reserved_for_later",
    "visual_intent_type",
    "visual_proof",
    "content_units",
    "detail_refs",
    "boundary_refs",
    "new_value_realized",
    "reserved_for_later_respected",
    "audience_question_answered",
    "must_not_include_respected",
    "split_risk_resolved",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _page_number(page_id: str) -> int:
    raw = page_id.removeprefix("p")
    if not raw.isdigit():
        raise ValueError(f"invalid page id: {page_id}")
    return int(raw)


def _expected_consumes(page: dict[str, Any]) -> list[str]:
    return [
        str(unit["unit_id"])
        for unit in page.get("content_units") or []
        if isinstance(unit, dict)
        and unit.get("unit_id")
        and str(unit.get("role") or "") != "boundary"
    ]


def _validate_authoring(
    project: Path,
    outline_path: Path,
    outline: dict[str, Any],
    authoring: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if authoring.get("schema") != AUTHORING_SCHEMA:
        raise ValueError(f"authoring schema must be {AUTHORING_SCHEMA}")
    if str(authoring.get("project") or "") != project.name:
        raise ValueError("authoring project does not match the target project")
    if str(authoring.get("outline_sha256") or "").lower() != _sha256(outline_path):
        raise ValueError("page authoring artifact is stale for the current Outline")

    expected_pages = {
        str(page["page_id"]): page
        for page in outline.get("pages") or []
        if isinstance(page, dict)
        and page.get("page_type") == "content"
        and page.get("page_id")
    }
    authored_pages = authoring.get("pages")
    if not isinstance(authored_pages, dict):
        raise ValueError("authoring pages must be an object")
    if set(authored_pages) != set(expected_pages):
        missing = sorted(set(expected_pages) - set(authored_pages))
        extra = sorted(set(authored_pages) - set(expected_pages))
        raise ValueError(f"authoring page coverage mismatch: missing={missing}, extra={extra}")

    for page_id, contract in expected_pages.items():
        authored = authored_pages.get(page_id)
        if not isinstance(authored, dict):
            raise ValueError(f"authoring page must be an object: {page_id}")
        for field in CONTENT_FIELDS:
            if field not in authored:
                raise ValueError(f"{page_id} missing authoring field: {field}")
        for field in ("prose", "onscreen", "visual", "notes"):
            if not str(authored.get(field) or "").strip():
                raise ValueError(f"{page_id} authoring field is empty: {field}")
        if "onscreen_expression_form" in authored:
            try:
                validate_expression_form(str(authored.get("onscreen_expression_form") or ""))
            except ValueError as exc:
                raise ValueError(f"{page_id} {exc}") from exc
        selection = authored.get("selection")
        if (
            not isinstance(selection, list)
            or len(selection) != 3
            or any(not str(value).strip() for value in selection)
        ):
            raise ValueError(f"{page_id} selection must contain three non-empty buckets")
        expected_consumes = _expected_consumes(contract)
        actual_consumes = [str(value) for value in authored.get("consumes") or []]
        if actual_consumes != expected_consumes:
            raise ValueError(
                f"{page_id} consumes mismatch: expected={expected_consumes}, actual={actual_consumes}"
            )
    return expected_pages


def _receipt(page: dict[str, Any], consumes: list[str]) -> str:
    payload: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "page_id": str(page["page_id"]),
    }
    for field in RECEIPT_FIELDS:
        payload[field] = page.get(field)
    payload["consumed_content_unit_ids"] = consumes
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _logic_skeleton(page: dict[str, Any]) -> str:
    lines: list[str] = []
    for relation in page.get("content_relations") or []:
        if not isinstance(relation, dict):
            continue
        subject = str(relation.get("subject") or "").strip()
        objects = "、".join(str(value) for value in relation.get("objects") or [])
        relation_name = str(relation.get("relation") or "relates_to")
        if subject and objects:
            lines.append(f"{subject} --{relation_name}--> {objects}")
    return "\n".join(lines) or str(page.get("core_message") or "").strip()


def _expression_model_block(page: dict[str, Any]) -> list[str]:
    """Render the Outline's author-selected expression model outside the audience layer."""

    selection = page.get("expression_model_selection")
    if not isinstance(selection, dict) or selection.get("fit") != "selected":
        return ["- 模型：source_native", "- 使用方式：沿用来源已证实的论证顺序，不另套表达模型。"]
    model_id = str(selection.get("model_id") or "source_native").strip()
    lines = [f"- 模型：{model_id}"]
    reason = str(selection.get("fit_reason") or "").strip()
    if reason:
        lines.append(f"- 匹配理由：{reason}")
    mappings = selection.get("source_mapping")
    if isinstance(mappings, list):
        lines.append("- 槽位映射：")
        for mapping in mappings:
            if not isinstance(mapping, dict):
                continue
            slot = str(mapping.get("slot") or "未命名槽位").strip()
            refs = "、".join(str(ref) for ref in mapping.get("source_refs") or [] if str(ref))
            detail = refs or "未引用"
            if mapping.get("implicit") is True:
                detail += "（隐含推导）"
            statement = str(mapping.get("statement") or "").strip()
            if statement:
                detail += f"：{statement}"
            lines.append(f"  - {slot}＝{detail}")
    return lines


def _onscreen_provenance_block(page: dict[str, Any]) -> list[str]:
    """Render source grounding for authors without leaking it to the audience."""

    lines: list[str] = []
    for module in page.get("onscreen_modules") or []:
        if not isinstance(module, dict):
            continue
        module_id = str(module.get("module_id") or "").strip()
        title = str(module.get("display_title") or "").strip()
        mode = str(module.get("derivation_mode") or "").strip()
        slots = "、".join(str(value) for value in module.get("model_slots") or [] if str(value)) or "未映射槽位"
        refs = "、".join(str(value) for value in module.get("source_refs") or [] if str(value)) or "未引用"
        lines.append(f"- {module_id}｜{title}｜{mode}｜{slots}｜{refs}")
        claim = str(module.get("allowed_visible_claim") or "").strip()
        if claim:
            lines.append(f"  - 允许命题：{claim}")
        characteristics = "、".join(
            str(value) for value in module.get("required_characteristics") or []
            if str(value)
        )
        if characteristics:
            lines.append(f"  - 必留特征：{characteristics}")
        if mode in {"synthesis", "relation"}:
            lines.append(f"  - 关系：{str(module.get('relation') or '').strip()}")
            lines.append(f"  - 综合理由：{str(module.get('synthesis_rationale') or '').strip()}")
    return lines or ["- 未启用来源归属契约。"]


def _template_page(page: dict[str, Any]) -> str:
    page_id = str(page["page_id"])
    number = _page_number(page_id)
    title = str(page.get("title") or "").strip()
    subtitle = str(page.get("subtitle") or "").strip()
    type_labels = {
        "cover": "封面",
        "chapter": "章节过渡页",
        "ending": "封底",
    }
    page_type = str(page.get("page_type") or "")
    lines = [
        f"## 第{number}页：{title}",
        "",
        f"- 页面类型：{type_labels.get(page_type, page_type)}",
        f"- 页面标题：{title}",
    ]
    if subtitle:
        lines.append(f"- 副标题：{subtitle}")
    lines += ["", "### 上屏文字（模板层）", "", title]
    if subtitle:
        lines += ["", subtitle]
    return "\n".join(lines).rstrip() + "\n"


def _onscreen_with_explicit_hierarchy(text: str) -> str:
    """Preserve paragraph groups as explicit top-level/module hierarchy.

    The authoring contract uses blank lines to separate peer business groups.
    Within a group, its first line is the group label and the remaining lines
    are its source-supported child details. Existing indentation is retained.
    """

    groups = [group for group in str(text).strip().split("\n\n") if group.strip()]
    rendered_groups: list[str] = []
    for group in groups:
        lines = [line.rstrip() for line in group.splitlines() if line.strip()]
        if not lines:
            continue
        rendered = [lines[0].lstrip()]
        for line in lines[1:]:
            # Detail items are rendered as child lines; normalize their
            # terminal punctuation while preserving internal copy.
            detail = strip_terminal_punctuation(line)
            rendered.append(detail if line[:1].isspace() else f"    {detail}")
        rendered_groups.append("\n".join(rendered))
    return "\n\n".join(rendered_groups)


def _default_prose_paragraph_map(
    page: dict[str, Any], records_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Emit one provenance line per source paragraph when that boundary matters."""

    detail_refs = {str(value) for value in page.get("detail_refs") or []}
    groups: dict[tuple[str, ...], list[str]] = {}
    order: dict[tuple[str, ...], int] = {}
    for ref in (str(value) for value in page.get("source_refs") or []):
        if ref in detail_refs:
            continue
        record = records_by_id.get(ref)
        if not record:
            continue
        unit_refs = tuple(str(value) for value in record.get("source_unit_refs") or [] if str(value))
        if not unit_refs:
            continue
        groups.setdefault(unit_refs, []).append(ref)
        locator = record.get("source_locator") if isinstance(record.get("source_locator"), dict) else {}
        order[unit_refs] = min(order.get(unit_refs, 10**9), int(locator.get("paragraph") or 10**9))
    if len(groups) < 3:
        return []
    return [f"- {'、'.join(groups[key])}" for key in sorted(groups, key=lambda key: order[key])]


def _content_page(
    page: dict[str, Any], authored: dict[str, Any], records_by_id: dict[str, dict[str, Any]],
) -> str:
    page_id = str(page["page_id"])
    number = _page_number(page_id)
    title = str(page.get("title") or "").strip()
    subtitle = str(authored.get("subtitle") or page.get("subtitle") or "").strip()
    core_message = str(page.get("core_message") or "").strip()
    source_refs = [str(value) for value in page.get("source_refs") or []]
    detail_refs = {str(value) for value in page.get("detail_refs") or []}
    primary_refs = [value for value in source_refs if value not in detail_refs]
    selection = [str(value).strip() for value in authored["selection"]]
    authored_map = authored.get("prose_paragraph_map")
    paragraph_map = (
        [str(value).strip() for value in authored_map if str(value).strip()]
        if isinstance(authored_map, list)
        else _default_prose_paragraph_map(page, records_by_id)
    )
    evidence = "、".join(source_refs)
    primary = "、".join(primary_refs)
    details = "、".join(sorted(detail_refs))
    lines = [
        f"## 第{number}页：{title}",
        "",
        "- 页面类型：内容页",
        f"- 页面标题：{title}",
    ]
    if subtitle:
        lines.append(f"- 副标题：{subtitle}")
    expression_form = str(authored.get("onscreen_expression_form") or "").strip()
    if expression_form:
        lines.append(f"- 上屏表达结构：{expression_form}")
    lines += [
        f"- 主判断：{core_message}",
        f"- 证据：{evidence}",
        f"- 视觉意图类型：{str(page.get('visual_intent_type') or '').strip()}",
        "",
        "### 完整文字稿",
        "",
        str(authored["prose"]).strip(),
    ]
    if paragraph_map:
        lines += ["", "### 完整文字稿段落映射（不上屏）", "", *paragraph_map]
    lines += [
        "",
        "### 文字稿取舍说明",
        "",
        *selection,
        "",
        "### 证据映射",
        "",
        f"[primary] {core_message} → {primary}",
    ]
    if details:
        lines.append(f"[detail] 讲解与约束细节，仅追溯不上屏 → {details}")
    lines += [
        "",
        "### 上屏文字（严格锁定）",
        "",
        _onscreen_with_explicit_hierarchy(str(authored["onscreen"])),
        "",
        "### 逻辑骨架",
        "",
        "```text",
        _logic_skeleton(page),
        "```",
        "",
        "### 表达模型（不上屏）",
        "",
        *_expression_model_block(page),
        "",
        "### 上屏来源归属（不上屏）",
        "",
        *_onscreen_provenance_block(page),
        "",
        "### 视觉结构（不上屏）",
        "",
        str(authored["visual"]).strip(),
        "",
        "### 演讲者备注",
        "",
        str(authored["notes"]).strip(),
        "",
        f"<!-- cyberppt-page-contract {_receipt(page, [str(value) for value in authored['consumes']])} -->",
    ]
    return "\n".join(lines).rstrip() + "\n"


def compile_page_script_authoring(
    project: Path,
    *,
    authoring_path: Path | None = None,
    output_dir: Path,
) -> dict[str, Any]:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise FileNotFoundError(f"project does not exist: {project}")
    outline_path = project / "workbench/stages/01-analysis/outline.json"
    resolved_authoring = (
        authoring_path.expanduser().resolve()
        if authoring_path is not None
        else project / "workbench/scripts/page-script-authoring.json"
    )
    resolved_output = output_dir.expanduser().resolve()
    if not outline_path.is_file():
        raise FileNotFoundError(f"outline does not exist: {outline_path}")
    if not resolved_authoring.is_file():
        raise FileNotFoundError(f"authoring artifact does not exist: {resolved_authoring}")
    if resolved_output.exists() and any(resolved_output.iterdir()):
        raise ValueError(f"output directory must be new or empty: {resolved_output}")

    outline = _load_json(outline_path)
    source_truth_path = project / "workbench/stages/01-analysis/source-truth.json"
    source_truth = _load_json(source_truth_path) if source_truth_path.is_file() else {}
    records_by_id = {
        str(record.get("id") or ""): record
        for record in source_truth.get("records") or []
        if isinstance(record, dict) and str(record.get("id") or "")
    }
    authoring = _load_json(resolved_authoring)
    content_contracts = _validate_authoring(
        project, outline_path, outline, authoring
    )
    authored_pages = authoring["pages"]
    all_pages = [
        page for page in outline.get("pages") or [] if isinstance(page, dict)
    ]
    numbers = [_page_number(str(page.get("page_id") or "")) for page in all_pages]
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError(f"Outline pages must be continuous from p01: {numbers}")

    grouped: dict[str, list[dict[str, Any]]] = {}
    for page in all_pages:
        page_type = str(page.get("page_type") or "")
        if page_type == "cover":
            group = "00-cover"
        elif page_type == "ending":
            group = "99-ending"
        else:
            chapter_id = str(page.get("chapter_id") or "unassigned").lower()
            group = chapter_id
        grouped.setdefault(group, []).append(page)

    resolved_output.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for group, pages in grouped.items():
        blocks: list[str] = []
        for page in pages:
            page_id = str(page["page_id"])
            if page_id in content_contracts:
                blocks.append(_content_page(page, authored_pages[page_id], records_by_id))
            else:
                blocks.append(_template_page(page))
        path = resolved_output / f"{group}.md"
        path.write_text("\n".join(blocks).rstrip() + "\n", encoding="utf-8")
        written.append(str(path))

    return {
        "schema": "cyberppt.compile_page_script_authoring.v1",
        "project": str(project),
        "authoring": str(resolved_authoring),
        "authoring_sha256": _sha256(resolved_authoring),
        "outline": str(outline_path),
        "outline_sha256": _sha256(outline_path),
        "output_dir": str(resolved_output),
        "page_count": len(all_pages),
        "content_page_count": len(content_contracts),
        "drafts": written,
    }
