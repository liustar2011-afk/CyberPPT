#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

PAGE_RE = re.compile(r"^##\s*第(\d+)页[：:]\s*(.+?)\s*$", re.M)
TYPE_RE = re.compile(r"^-\s*页面类型[：:]\s*`?([^`\n]+)`?\s*$", re.M)
KEY_RE = re.compile(r"【锁定关键文字】\s*\n(.*?)\n\s*【完整上屏内容】", re.S)
VISIBLE_RE = re.compile(r"【完整上屏内容】\s*\n(.*?)\n\s*【结论句要求｜不上屏】", re.S)
MISSION_RE = re.compile(r"页面任务[：:]\s*\n(.*?)\n\s*核心意思[：:]", re.S)
CORE_RE = re.compile(r"核心意思[：:]\s*\n(.*?)\n\s*【输出尺寸｜不上屏】", re.S)
SIZE_RE = re.compile(r"画布尺寸固定为\s*(\d+)×(\d+)\s*像素（([^）]+)）")
BANNED = [
    "演讲者备注", "证据映射", "Source IDs", "source_refs", "consumed_content_unit_ids",
    "逻辑骨架", "视觉结构（不上屏）", "visual_intent_type", "visual_thesis",
    "dominant_visual_carrier", "spatial_organization", "reading_path", "avoid_on_this_page",
]
TEMPLATE_TYPES = {"cover", "contents", "chapter", "closing"}


@dataclass
class Issue:
    level: str
    code: str
    page: int | None
    message: str


def plain(text: str) -> str:
    text = re.sub(r"[#>*_`\-]", "", text)
    text = re.sub(r"\s+", "", text)
    return text


def pages(text: str) -> list[tuple[int, str, str]]:
    matches = list(PAGE_RE.finditer(text))
    result = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        result.append((int(m.group(1)), m.group(2).strip(), text[m.start():end].strip()))
    return result


def add(issues: list[Issue], level: str, code: str, page: int | None, message: str) -> None:
    issues.append(Issue(level, code, page, message))


def validate(path: Path, strict: bool = False) -> tuple[int, list[Issue]]:
    text = path.read_text(encoding="utf-8")
    parsed = pages(text)
    issues: list[Issue] = []
    if not parsed:
        add(issues, "error", "NO_PAGES", None, "未识别到送图页面")
        return 0, issues

    numbers = [x[0] for x in parsed]
    if numbers != list(range(numbers[0], numbers[-1] + 1)):
        add(issues, "warning" if not strict else "error", "PAGE_SEQUENCE", None, f"页码不连续：{numbers}")

    canvas_values: set[tuple[str, str, str]] = set()
    for number, title, raw in parsed:
        type_match = TYPE_RE.search(raw)
        page_type = type_match.group(1).strip() if type_match else "content"
        is_template = page_type in TEMPLATE_TYPES

        if is_template:
            if "不生成正文区 ImageGen" not in raw:
                add(issues, "error", "TEMPLATE_CONCLUSION", number, "模板页缺少不进入ImageGen的结论")
            for marker in ["【锁定关键文字】", "【完整上屏内容】", "【页面视觉结构｜不上屏】", "【全局视觉风格｜不上屏】"]:
                if marker in raw:
                    add(issues, "error", "TEMPLATE_CONTENT_LEAK", number, f"模板页不应包含：{marker}")
            continue

        for marker in [
            "【锁定关键文字】", "【完整上屏内容】", "【结论句要求｜不上屏】",
            "页面任务：", "核心意思：", "【输出尺寸｜不上屏】",
            "【模板层禁绘｜不上屏】", "【页面视觉结构｜不上屏】", "【全局视觉风格｜不上屏】",
        ]:
            if marker not in raw:
                add(issues, "error", "MISSING_BLOCK", number, f"内容页缺少：{marker}")

        for token in BANNED:
            if token in raw:
                add(issues, "error", "FORBIDDEN_UPSTREAM_FIELD", number, f"送图页包含不应送入ImageGen的字段：{token}")

        key_match = KEY_RE.search(raw)
        visible_match = VISIBLE_RE.search(raw)
        mission_match = MISSION_RE.search(raw)
        core_match = CORE_RE.search(raw)
        size_match = SIZE_RE.search(raw)

        keys = []
        if key_match:
            keys = [line.strip() for line in key_match.group(1).splitlines() if line.strip()]
            if len(keys) > 7:
                add(issues, "warning" if not strict else "error", "TOO_MANY_KEY_TEXT", number, f"锁定关键文字超过7项：{len(keys)}")
        else:
            add(issues, "error", "KEY_TEXT_PARSE", number, "无法解析锁定关键文字")

        visible = visible_match.group(1).strip() if visible_match else ""
        if not visible:
            add(issues, "error", "EMPTY_VISIBLE", number, "完整上屏内容为空或无法解析")
        for key in keys:
            if plain(key) not in plain(visible):
                add(issues, "error", "KEY_NOT_IN_VISIBLE", number, f"锁定关键文字未出现在完整上屏内容：{key}")

        mission = mission_match.group(1).strip() if mission_match else ""
        core = core_match.group(1).strip() if core_match else ""
        if not mission:
            add(issues, "error", "EMPTY_MISSION", number, "页面任务为空")
        if not core:
            add(issues, "error", "EMPTY_CORE", number, "核心意思为空")
        if title and plain(title) in plain(visible[:80]):
            add(issues, "warning", "TITLE_MAY_BE_REDRAWN", number, "完整上屏内容开头疑似重复页面标题")

        if "不绘制页面标题" not in raw or "PPT 模板文字层" not in raw:
            add(issues, "error", "TITLE_LAYER_RULE", number, "缺少标题由PPT模板层处理的禁绘规则")
        if size_match:
            canvas_values.add((size_match.group(1), size_match.group(2), size_match.group(3)))
        else:
            add(issues, "error", "CANVAS_RULE", number, "无法解析画布尺寸")

    if len(canvas_values) > 1:
        add(issues, "error", "MIXED_CANVAS", None, f"项目内画布尺寸不一致：{sorted(canvas_values)}")
    return len(parsed), issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate single-page ImageGen review contract")
    parser.add_argument("script", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    count, issues = validate(args.script, strict=args.strict)
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    payload = {
        "passed": not errors,
        "pages": count,
        "errors": len(errors),
        "warnings": len(warnings),
        "issues": [i.__dict__ for i in issues],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"pages={count} errors={len(errors)} warnings={len(warnings)}")
        for issue in issues:
            where = f"P{issue.page}" if issue.page is not None else "DECK"
            print(f"[{issue.level.upper()}] {where} {issue.code}: {issue.message}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
