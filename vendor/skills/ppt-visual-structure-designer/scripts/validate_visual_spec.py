#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

MINIMUM_FONT_PT = 14

REQUIRED_MD_SECTIONS = [
    "页面角色", "页面使命", "核心结论", "内容锁定", "证据单元与语义关系",
    "视觉意图", "页面草图", "页面构图", "实景锚点与图文融合",
    "元素与空间关系", "箭头与连接关系", "标题与文字渲染",
    "终稿文字", "生图执行摘要", "禁止事项"
]
PLACEHOLDERS = ["文案略", "文字略", "同上", "沿用前页", "参考原文", "待补充", "TODO"]
RISK_TERMS = ["等宽三列", "并列卡片", "六宫格", "一项一图", "一条内容一个图标", "左文右图"]
# Structural row markers are authoring aids, not presentation copy.  If they
# reach locked/final text they are likely to be rendered verbatim by ImageGen.
ROW_MARKER_RE = re.compile(r"^\s*第\s*[0-9一二三四五六七八九十]+\s*行\s*[｜|:]", re.MULTILINE)
STYLE_IMPLEMENTATION_RE = re.compile(
    r"(?:#[0-9a-f]{3,8}\b|rgb\(|\bfont\b|字体|字号|\b[0-9]+\s*pt\b|颜色|色彩|深蓝|象牙白|"
    r"线宽|粗细|圆角|阴影|发光|渐变|材质|箭头头|stroke(?:-width)?|shadow|glow|gradient)",
    re.IGNORECASE,
)


def add(issues: list[dict[str, Any]], level: str, code: str, message: str, page: int | None = None) -> None:
    item: dict[str, Any] = {"level": level, "code": code, "message": message}
    if page is not None:
        item["page"] = page
    issues.append(item)


def load_json_schema(skill_root: Path, name: str) -> dict:
    return json.loads((skill_root / "assets" / name).read_text(encoding="utf-8"))


def schema_validate(data: dict, path: Path, skill_root: Path, issues: list[dict[str, Any]]) -> None:
    is_deck = "pages" in data
    schema_name = "deck-visual-spec.schema.json" if is_deck else "page-visual-spec.schema.json"
    schema = load_json_schema(skill_root, schema_name)
    if is_deck:
        # Inline the page schema so validation stays fully offline.
        schema["properties"]["pages"]["items"] = load_json_schema(
            skill_root, "page-visual-spec.schema.json"
        )
    validator = Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        where = ".".join(str(p) for p in error.absolute_path) or "root"
        add(issues, "error", "schema", f"{where}: {error.message}")


def semantic_checks_page(page: dict, issues: list[dict[str, Any]]) -> None:
    n = page.get("page_number")
    schema_version = str(page.get("schema_version") or "")
    vd = page.get("visual_decision", {})
    if vd.get("visual_center_count") != 1:
        add(issues, "error", "visual_center", "Page must have exactly one visual center", n)
    if schema_version == "1.0" and not vd.get("dominant_visual_carrier"):
        add(issues, "error", "dominant_carrier", "Dominant visual carrier is required", n)
    if schema_version == "1.0":
        add(
            issues,
            "notice",
            "legacy_schema",
            "Schema 1.0 is supported for compatibility; migrate to structural_decision v1.1",
            n,
        )
    structural = page.get("structural_decision")
    if isinstance(structural, dict):
        graph = page.get("semantic_graph", {})
        nodes = {str(value) for value in graph.get("nodes", [])}
        evidence = {
            str(item.get("id")): item
            for item in page.get("evidence_units", [])
            if isinstance(item, dict) and item.get("id")
        }
        focus = structural.get("semantic_focus", {})
        focus_ref = str(focus.get("ref") or "") if isinstance(focus, dict) else ""
        if focus_ref not in nodes:
            add(issues, "error", "semantic_focus_ref", f"Semantic focus ref is not a graph node: {focus_ref}", n)
        primary_refs = [str(value) for value in structural.get("primary_refs", [])]
        secondary_refs = [str(value) for value in structural.get("secondary_refs", [])]
        reading_sequence = [str(value) for value in structural.get("reading_sequence", [])]
        for field, refs in (
            ("primary_refs", primary_refs),
            ("secondary_refs", secondary_refs),
            ("reading_sequence", reading_sequence),
        ):
            unknown = sorted(set(refs) - nodes)
            if unknown:
                add(issues, "error", "structural_ref", f"{field} contains unknown graph nodes: {unknown}", n)
        overlap = sorted(set(primary_refs).intersection(secondary_refs))
        if overlap:
            add(issues, "error", "structural_hierarchy", f"Primary and secondary refs overlap: {overlap}", n)
        if focus_ref and focus_ref not in primary_refs:
            add(issues, "error", "semantic_focus_hierarchy", "Semantic focus must be included in primary_refs", n)
        bound_evidence: set[str] = set()
        for binding in structural.get("text_bindings", []):
            if not isinstance(binding, dict):
                continue
            evidence_id = str(binding.get("evidence_id") or "")
            target_ref = str(binding.get("target_ref") or "")
            if evidence_id not in evidence:
                add(issues, "error", "text_binding_evidence", f"Unknown evidence id in text binding: {evidence_id}", n)
            else:
                bound_evidence.add(evidence_id)
            if target_ref not in nodes:
                add(issues, "error", "text_binding_target", f"Unknown graph node in text binding: {target_ref}", n)
        missing_p0 = sorted(
            evidence_id
            for evidence_id, item in evidence.items()
            if item.get("priority") == "P0" and evidence_id not in bound_evidence
        )
        if missing_p0:
            add(issues, "error", "p0_text_binding", f"P0 evidence has no structural text binding: {missing_p0}", n)
    ti = page.get("text_integration", {})
    if schema_version == "1.0" and ti.get("minimum_font_pt", 0) < MINIMUM_FONT_PT:
        add(
            issues,
            "error",
            "font_size",
            f"Minimum font size must be at least {MINIMUM_FONT_PT}pt",
            n,
        )
    if ti.get("title_render_mode") != "external_text_layer":
        add(issues, "warning", "title_mode", "Default profile expects external title text layer", n)
    ip = page.get("image_plan", {})
    if schema_version == "1.0" and ip.get("front_facing_people") is not False:
        add(issues, "error", "front_portrait", "Front-facing people are prohibited by default", n)
    if ip.get("identifiable_location") is not False:
        add(issues, "error", "location", "Identifiable location is prohibited by default", n)
    sg = page.get("semantic_graph", {})
    if sg.get("primary_relation") not in (None, "none") and not sg.get("edges"):
        add(issues, "error", "semantic_edges", "A relational page requires semantic edges", n)
    if sg.get("primary_relation") in {"flow", "transform", "converge", "diverge", "loop", "control", "exchange", "boundary", "responsibility"} and not page.get("connectors"):
        add(issues, "error", "connectors", "This relation type requires explicit connectors", n)
    final_text = "\n".join(item.get("text", "") for item in page.get("final_text", []))
    if ROW_MARKER_RE.search(final_text):
        add(issues, "error", "structural_row_marker", "Structural '第N行' marker must not appear in final on-screen text", n)
    for token in PLACEHOLDERS:
        if token.lower() in final_text.lower():
            add(issues, "error", "placeholder", f"Placeholder text found: {token}", n)
    handoff = page.get("generation_handoff", {})
    structural_handoff = handoff.get("structural_guidance", {})
    additional_constraints = (
        structural_handoff.get("additional_constraints", [])
        if isinstance(structural_handoff, dict)
        else []
    )
    merged = "\n".join([
        handoff.get("composition_guidance", ""),
        handoff.get("style_guidance", ""),
        "\n".join(handoff.get("negative_constraints", [])),
        "\n".join(additional_constraints),
        "\n".join(page.get("avoid", [])),
    ]).lower()
    if "overlay" in merged:
        add(issues, "error", "overlay", "overlay field or instruction is not allowed", n)
    if schema_version == "1.0":
        neg = " ".join(handoff.get("negative_constraints", [])).lower()
        for required in ["equal card", "one-icon-per-bullet", "left-text/right-image", "front-facing portrait"]:
            if required not in neg:
                add(issues, "warning", "negative_constraint", f"Missing recommended negative constraint: {required}", n)
    if schema_version == "1.1":
        structural_text = json.dumps(
            {
                "structural_decision": page.get("structural_decision", {}),
                "visual_decision": page.get("visual_decision", {}),
                "image_plan": page.get("image_plan", {}),
                "structural_guidance": structural_handoff,
                "avoid": page.get("avoid", []),
            },
            ensure_ascii=False,
        )
        match = STYLE_IMPLEMENTATION_RE.search(structural_text)
        if match:
            add(
                issues,
                "error",
                "style_in_structure",
                f"Style implementation detail must come from style_source_ref, not structural fields: {match.group(0)}",
                n,
            )
    if page.get("qa", {}).get("score", 0) < 80:
        add(issues, "error", "qa_score", "QA score below 80", n)
    elif page.get("qa", {}).get("score", 0) < 90:
        add(issues, "warning", "qa_score", "QA score below direct-generation threshold 90", n)


def validate_json(path: Path, skill_root: Path) -> dict:
    issues: list[dict[str, Any]] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        add(issues, "error", "json_parse", str(exc))
        return summarize(issues)
    if not isinstance(data, dict):
        add(issues, "error", "json_type", "Top-level JSON must be an object")
        return summarize(issues)
    schema_validate(data, path, skill_root, issues)
    pages = data.get("pages", [data])
    numbers = []
    intents = []
    for page in pages:
        if isinstance(page, dict):
            semantic_checks_page(page, issues)
            numbers.append(page.get("page_number"))
            intents.append(page.get("visual_decision", {}).get("visual_intent_type"))
    seen = set()
    for number in numbers:
        if number in seen:
            add(issues, "error", "duplicate_page", f"Duplicate page number: {number}")
        seen.add(number)
    for i in range(len(intents) - 2):
        if intents[i] and intents[i] == intents[i + 1] == intents[i + 2]:
            add(issues, "warning", "repetition", f"Pages {numbers[i]}-{numbers[i+2]} repeat visual intent {intents[i]}")
    return summarize(issues)


def split_md_pages(text: str) -> list[tuple[int, str]]:
    matches = list(re.finditer(r"^##\s*第\s*(\d+)\s*页[^\n]*$", text, re.MULTILINE))
    pages: list[tuple[int, str]] = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        pages.append((int(match.group(1)), text[match.start():end]))
    return pages


def section_text(block: str, title: str) -> str:
    m = re.search(rf"^###\s*{re.escape(title)}\s*$", block, re.MULTILINE)
    if not m:
        return ""
    next_m = re.search(r"^###\s+", block[m.end():], re.MULTILINE)
    end = m.end() + next_m.start() if next_m else len(block)
    return block[m.end():end].strip()


def validate_markdown(path: Path) -> dict:
    issues: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    if "overlay" in text.lower():
        add(issues, "error", "overlay", "overlay field is not allowed")
    if re.search(r"^\s*\*\s+", text, re.MULTILINE):
        add(issues, "error", "star_bullet", "Use hyphen bullets, not asterisk bullets")
    pages = split_md_pages(text)
    if not pages:
        add(issues, "error", "page_heading", "No page headings matching '## 第N页' found")
        return summarize(issues)
    seen = set()
    intents: list[str] = []
    numbers: list[int] = []
    for number, block in pages:
        numbers.append(number)
        if number in seen:
            add(issues, "error", "duplicate_page", f"Duplicate page number: {number}", number)
        seen.add(number)
        for section in REQUIRED_MD_SECTIONS:
            value = section_text(block, section)
            if not value:
                add(issues, "error", "missing_section", f"Missing or empty section: {section}", number)
        final = section_text(block, "终稿文字")
        if ROW_MARKER_RE.search(final):
            add(issues, "error", "structural_row_marker", "Structural '第N行' marker must not appear in final on-screen text", number)
        for token in PLACEHOLDERS:
            if token.lower() in final.lower():
                add(issues, "error", "placeholder", f"Placeholder text found: {token}", number)
        visual = section_text(block, "视觉意图")
        legacy_visual = "主视觉载体" in visual and "单一视觉中心" in visual
        structural_visual = all(
            token in visual
            for token in ("语义焦点", "空间语法", "主结构", "文字归属")
        )
        if not (legacy_visual or structural_visual):
            add(
                issues,
                "error",
                "visual_decision",
                "视觉意图 must state either the legacy carrier contract or semantic focus, spatial grammar, primary structure and text bindings",
                number,
            )
        match = re.search(r"视觉意图类型[：:]\s*`?([a-z0-9_-]+)", visual)
        intents.append(match.group(1) if match else "")
        rendering = section_text(block, "标题与文字渲染")
        if "外部" not in rendering and "PPT文字层" not in rendering:
            add(issues, "warning", "title_mode", "Title rendering should state external PPT text layer", number)
        arrows = section_text(block, "箭头与连接关系")
        relation = section_text(block, "证据单元与语义关系")
        if any(t in relation for t in ["流程", "汇聚", "闭环", "控制", "流转", "责任"]) and (not arrows or arrows in {"无", "无。"}):
            add(issues, "error", "connectors", "Relational page requires explicit arrow/connector description", number)
        risk_sections = "\n".join([section_text(block, "页面构图"), section_text(block, "元素与空间关系"), section_text(block, "实景锚点与图文融合")])
        for term in RISK_TERMS:
            if term in risk_sections:
                add(issues, "warning", "layout_risk", f"Potential generic layout term: {term}", number)
    for i in range(len(intents) - 2):
        if intents[i] and intents[i] == intents[i + 1] == intents[i + 2]:
            add(issues, "warning", "repetition", f"Pages {numbers[i]}-{numbers[i+2]} repeat visual intent {intents[i]}")
    return summarize(issues)


def summarize(issues: list[dict[str, Any]]) -> dict:
    errors = [i for i in issues if i["level"] == "error"]
    warnings = [i for i in issues if i["level"] == "warning"]
    notices = [i for i in issues if i["level"] == "notice"]
    base = 100 - 10 * len(errors) - 2 * len(warnings)
    return {
        "valid": not errors,
        "score": max(0, base),
        "errors": errors,
        "warnings": warnings,
        "notices": notices,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--strict", action="store_true", help="Treat warnings as failure")
    ap.add_argument("--json-report", action="store_true")
    args = ap.parse_args()
    path = Path(args.input).resolve()
    skill_root = Path(__file__).resolve().parents[1]
    if not path.exists():
        print(f"Input not found: {path}", file=sys.stderr)
        return 2
    result = validate_json(path, skill_root) if path.suffix.lower() == ".json" else validate_markdown(path)
    if args.json_report:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("PASS" if result["valid"] and (not args.strict or not result["warnings"]) else "FAIL")
        print(f"Score: {result['score']}")
        for group in ("errors", "warnings", "notices"):
            for item in result[group]:
                page = f" page={item['page']}" if "page" in item else ""
                print(f"[{item['level'].upper()}] {item['code']}{page}: {item['message']}")
    failed = (not result["valid"]) or (args.strict and bool(result["warnings"]))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
