#!/usr/bin/env python3
"""Reusable image prompt style presets for script-imagegen flows."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
STYLE_LIBRARY_DIR = SKILL_DIR / "templates" / "image_styles"
DEFAULT_STYLE_NAME = "象牙白深蓝图文分离摄影彩色"

DEFAULT_FONT_RULES = [
    "中文文字采用接近微软雅黑特征的现代中文无衬线风格，字形端正清晰，笔画均匀，结构略圆润，字面宽度适中偏宽，字距自然，行距宽松稳定。",
    "正文主色必须使用深墨蓝或深灰（优先 #0F172A、#111827、#1E293B），次级说明文字不得浅于 #334155；禁止使用 #64748B 或更浅颜色作为正文主文字。",
    "标题可适度加粗，但不得过粗、过硬、过窄、过度压缩或形成厚重黑块感；正文至少采用 regular-medium 字重，关键短语采用 semibold，禁止细体、半透明文字和低对比浅灰字。",
    "文字与承载面视觉对比度不得低于 4.5:1；小字号、注释、图例和标签应更接近 7:1。正文必须落在纯白或近白承载面上，不得压在渐变、纹理、阴影、高光或发光区域上。",
    "文字不得密排、贴边、挤压、溢出，不得使用过窄行高。常规文字容器应保留充足留白，左右内边距不低于10%，上下内边距不低于8%，模块标题区和正文内容区均应避免文字过满。",
    "正文模块标题约 14–16pt，标签约 11–12pt，辅助说明约 9–10pt；文字需要水平清晰、左对齐优先，同列元素严格对齐。",
]


def _extract_json_from_markdown(text: str, path: Path) -> dict[str, Any]:
    match = re.search(r"```(?:json)?\s*(?P<body>\{.*?\})\s*```", text, re.S)
    if not match:
        raise ValueError(f"No fenced JSON style brief found in {path}")
    return json.loads(match.group("body"))


def _read_style_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".md":
        return _extract_json_from_markdown(text, path)
    return json.loads(text)


def resolve_style_path(style: str | Path | None) -> Path:
    """Resolve a style name or file path to a local preset file."""
    if style is None or str(style).strip() == "":
        style = DEFAULT_STYLE_NAME
    raw = Path(str(style))
    if raw.is_file():
        return raw.resolve()
    candidates = [
        STYLE_LIBRARY_DIR / str(style),
        STYLE_LIBRARY_DIR / f"{style}.json",
        STYLE_LIBRARY_DIR / f"{style}.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    available = ", ".join(sorted(p.stem for p in STYLE_LIBRARY_DIR.glob("*") if p.is_file()))
    raise FileNotFoundError(f"Image style not found: {style}. Available styles: {available}")


def load_image_style(style: str | Path | None = None) -> dict[str, Any]:
    """Load and normalize one image prompt style preset."""
    path = resolve_style_path(style)
    data = _read_style_file(path)
    if not isinstance(data, dict):
        raise ValueError(f"Image style must be a JSON object: {path}")
    normalized = dict(data)
    normalized.setdefault("style_name", path.stem)
    normalized.setdefault("source_path", str(path))
    normalized.setdefault("font_rules", DEFAULT_FONT_RULES)
    return normalized


def style_name(style: dict[str, Any]) -> str:
    return str(style.get("style_name") or style.get("name") or DEFAULT_STYLE_NAME)


def _format_value(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, list):
        return "；".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if item in (None, "", [], {}):
                continue
            parts.append(f"{key}: {_format_value(item)}")
        return "；".join(parts)
    return str(value).strip()


def _bullet(label: str, value: Any) -> str:
    formatted = _format_value(value)
    return f"- {label}：{formatted}" if formatted else ""


def style_prompt_block(style: dict[str, Any]) -> str:
    """Render the reusable style block injected into image prompts."""
    visual_elements = style.get("visual_elements") if isinstance(style.get("visual_elements"), dict) else {}
    lines = [
        f"【风格预设：{style_name(style)}】",
        _bullet("视觉方向", style.get("visual_direction")),
        _bullet("配色规则", style.get("color_palette")),
        _bullet("版式模式", style.get("layout_patterns")),
        _bullet("版式使用", style.get("layout_usage_rule")),
        _bullet("允许元素", visual_elements.get("allowed")),
        _bullet("避免元素", visual_elements.get("avoid")),
        _bullet("渲染约束", style.get("rendering_constraints")),
        "layout_blueprints 仅作为构图候选，不得把其中的 labels 当作必须出现的画面文字；只有页面正文内容明确要求的文字才可见。",
        "",
        "【字体与文字排版规则】",
    ]
    for rule in style.get("font_rules") or DEFAULT_FONT_RULES:
        if str(rule).strip():
            lines.append(str(rule).strip())
    return "\n".join(line for line in lines if line != "")
