#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REQUIRED_MD_SECTIONS = [
    "页面角色", "页面使命", "核心结论", "内容锁定", "证据单元与语义关系",
    "视觉意图", "页面草图", "页面构图", "实景锚点与图文融合",
    "元素与空间关系", "箭头与连接关系", "标题与文字渲染",
    "终稿文字", "生图执行摘要", "禁止事项"
]
PLACEHOLDERS = ["文案略", "文字略", "同上", "沿用前页", "参考原文", "待补充", "TODO"]
RISK_TERMS = ["等宽三列", "并列卡片", "六宫格", "一项一图", "一条内容一个图标", "左文右图"]


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
    vd = page.get("visual_decision", {})
    if vd.get("visual_center_count") != 1:
        add(issues, "error", "visual_center", "Page must have exactly one visual center", n)
    if not vd.get("dominant_visual_carrier"):
        add(issues, "error", "dominant_carrier", "Dominant visual carrier is required", n)
    ti = page.get("text_integration", {})
    if ti.get("minimum_font_pt", 0) < 12:
        add(issues, "error", "font_size", "Minimum font size must be at least 12pt", n)
    if ti.get("title_render_mode") != "external_text_layer":
        add(issues, "warning", "title_mode", "Default profile expects external title text layer", n)
    ip = page.get("image_plan", {})
    if ip.get("front_facing_people") is not False:
        add(issues, "error", "front_portrait", "Front-facing people are prohibited by default", n)
    if ip.get("identifiable_location") is not False:
        add(issues, "error", "location", "Identifiable location is prohibited by default", n)
    sg = page.get("semantic_graph", {})
    if sg.get("primary_relation") not in (None, "none") and not sg.get("edges"):
        add(issues, "error", "semantic_edges", "A relational page requires semantic edges", n)
    if sg.get("primary_relation") in {"flow", "transform", "converge", "diverge", "loop", "control", "exchange", "boundary", "responsibility"} and not page.get("connectors"):
        add(issues, "error", "connectors", "This relation type requires explicit connectors", n)
    final_text = "\n".join(item.get("text", "") for item in page.get("final_text", []))
    for token in PLACEHOLDERS:
        if token.lower() in final_text.lower():
            add(issues, "error", "placeholder", f"Placeholder text found: {token}", n)
    handoff = page.get("generation_handoff", {})
    merged = "\n".join([
        handoff.get("composition_guidance", ""),
        handoff.get("style_guidance", ""),
        "\n".join(handoff.get("negative_constraints", [])),
        "\n".join(page.get("avoid", [])),
    ]).lower()
    if "overlay" in merged:
        add(issues, "error", "overlay", "overlay field or instruction is not allowed", n)
    neg = " ".join(handoff.get("negative_constraints", [])).lower()
    for required in ["equal card", "one-icon-per-bullet", "left-text/right-image", "front-facing portrait"]:
        if required not in neg:
            add(issues, "warning", "negative_constraint", f"Missing recommended negative constraint: {required}", n)
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
        for token in PLACEHOLDERS:
            if token.lower() in final.lower():
                add(issues, "error", "placeholder", f"Placeholder text found: {token}", number)
        visual = section_text(block, "视觉意图")
        if "主视觉载体" not in visual or "单一视觉中心" not in visual:
            add(issues, "error", "visual_decision", "视觉意图 must state dominant carrier and single visual center", number)
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
    base = 100 - 10 * len(errors) - 2 * len(warnings)
    return {"valid": not errors, "score": max(0, base), "errors": errors, "warnings": warnings}


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
        for group in ("errors", "warnings"):
            for item in result[group]:
                page = f" page={item['page']}" if "page" in item else ""
                print(f"[{item['level'].upper()}] {item['code']}{page}: {item['message']}")
    failed = (not result["valid"]) or (args.strict and bool(result["warnings"]))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
