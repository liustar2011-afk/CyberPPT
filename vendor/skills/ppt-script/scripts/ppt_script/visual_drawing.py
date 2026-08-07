from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from .visual_focus import parse_visual_focus

_SOURCE_ID_LEAK_RE = re.compile(r"(?<![A-Za-z0-9])S\d{3,4}(?![A-Za-z0-9])")


@dataclass(frozen=True, slots=True)
class DrawingIssue:
    code: str
    page: str
    message: str
    text: str = ""
    level: str = "WARN"


def _extract_section(content: str, heading: str) -> str:
    pattern = rf"(?:^|\n){re.escape(heading)}[：:]\s*\n?(.*?)(?=\n---|\n(?:本页内容关系判断|推荐主语义图类型|第二段视觉转译接口|页面类型|落图策略建议)[：:]|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_image_prompt(content: str) -> str:
    """Prefer 生图提示词; fall back to legacy 内容关系草图."""
    direct = _extract_section(content, "生图提示词")
    if direct:
        return direct
    return _extract_section(content, "内容关系草图")


def has_direct_image_prompt(content: str) -> bool:
    return bool(_extract_section(content, "生图提示词"))


def _extract_block(content: str, name: str) -> str:
    match = re.search(rf"(?:^|\n)\s*{re.escape(name)}[：:]\s*(.*?)(?=\n\S|\Z)", content, re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _section_present(sketch: str, labels: list[str]) -> bool:
    for label in labels:
        if re.search(rf"(?:^|\n)\s*(?:【\s*)?{re.escape(label)}(?:\s*】)?\s*[：:]", sketch):
            return True
        if f"【{label}】" in sketch:
            return True
    return False


def _is_abstract_center(center: str, patterns: list[str]) -> bool:
    text = center.strip()
    if not text:
        return False
    for raw in patterns:
        try:
            if re.search(raw, text):
                return True
        except re.error:
            if raw in text:
                return True
    return False


def audit_visual_drawing(
    *,
    page: str,
    content: str,
    nature: str,
    rules: Mapping[str, Any] | Any,
) -> list[DrawingIssue]:
    drawing = getattr(rules, "visual_drawing", None)
    if drawing is None and isinstance(rules, Mapping):
        drawing = rules.get("visual_drawing")
    if not isinstance(drawing, dict):
        return []
    required_for = set(drawing.get("required_for") or ["内容页"])
    if nature not in required_for:
        return []

    level = str(drawing.get("level") or "WARN")
    issues: list[DrawingIssue] = []
    prompt = extract_image_prompt(content)
    direct = has_direct_image_prompt(content)

    leaked_ids = sorted(set(_SOURCE_ID_LEAK_RE.findall(prompt)))
    if leaked_ids:
        issues.append(
            DrawingIssue(
                "visual-prompt-source-id-leak",
                page,
                "生图提示词混入内部 Source ID，应删除并改写为可直接画图的描述",
                "、".join(leaked_ids),
                "ERROR",
            )
        )
    min_chars = int(drawing.get("min_prompt_chars") or drawing.get("min_sketch_chars") or 0)
    if len(re.sub(r"\s+", "", prompt)) < min_chars:
        issues.append(
            DrawingIssue(
                "visual-prompt-thin",
                page,
                f"生图提示词过短（<{min_chars}字有效字符），不足以直接画图",
                prompt[:120],
                level,
            )
        )

    # Legacy structured sketch only required when no direct 生图提示词
    if not direct:
        sections = drawing.get("sketch_sections") or []
        require_all = set(drawing.get("require_all") or [])
        found_ids: set[str] = set()
        for item in sections:
            if not isinstance(item, dict):
                continue
            section_id = str(item.get("id") or "")
            labels = [str(label) for label in (item.get("labels") or []) if str(label).strip()]
            if section_id and labels and _section_present(prompt, labels):
                found_ids.add(section_id)
        missing = [section_id for section_id in require_all if section_id not in found_ids]
        if missing:
            issues.append(
                DrawingIssue(
                    "visual-sketch-incomplete",
                    page,
                    "缺少「生图提示词」且内容关系草图缺少可绘制分段：" + "、".join(missing),
                    "请改写为完整「生图提示词」，或补齐【可绘制节点】等分段",
                    level,
                )
            )

        skeleton = _extract_block(content, "语义骨架说明")
        min_skeleton = int(drawing.get("min_skeleton_chars") or 0)
        if len(skeleton) < min_skeleton:
            issues.append(
                DrawingIssue(
                    "visual-skeleton-thin",
                    page,
                    f"语义骨架说明过短（<{min_skeleton}字），无法说明如何建立视觉承载",
                    skeleton,
                    level,
                )
            )
        cues = [str(item) for item in (drawing.get("skeleton_layout_cues") or []) if str(item).strip()]
        if skeleton and cues and not any(cue in skeleton for cue in cues):
            issues.append(
                DrawingIssue(
                    "visual-skeleton-no-layout",
                    page,
                    "语义骨架说明缺少布局动作词（如纵向/横向/汇聚/环绕/主区/辅助区）",
                    skeleton,
                    level,
                )
            )

        focus_cfg = getattr(rules, "visual_focus", None)
        if focus_cfg is None and isinstance(rules, Mapping):
            focus_cfg = rules.get("visual_focus")
        focus_cfg = focus_cfg if isinstance(focus_cfg, dict) else {}
        focus = parse_visual_focus(content)
        patterns = [str(item) for item in (focus_cfg.get("abstract_center_patterns") or []) if str(item).strip()]
        if focus.center and _is_abstract_center(focus.center, patterns):
            issues.append(
                DrawingIssue(
                    "visual-center-abstract",
                    page,
                    "主视觉中心过于抽象，无法落笔；应写上屏可见的对象/路径/汇聚块",
                    focus.center,
                    level,
                )
            )

    if drawing.get("prompt_style") and prompt:
        verbs = [str(item) for item in (drawing.get("prompt_verbs") or []) if str(item).strip()]
        min_verbs = int(drawing.get("min_prompt_verbs") or 0)
        if verbs and min_verbs:
            hit_count = sum(1 for verb in verbs if verb in prompt)
            if hit_count < min_verbs:
                issues.append(
                    DrawingIssue(
                        "visual-prompt-style-thin",
                        page,
                        f"生图提示词缺少画图动词（命中{hit_count}/{min_verbs}）",
                        prompt[:160],
                        level,
                    )
                )
        bans = [str(item) for item in (drawing.get("editorial_ban_patterns") or []) if str(item).strip()]
        hits = [pat for pat in bans if pat in prompt]
        if hits:
            issues.append(
                DrawingIssue(
                    "visual-editorial-prose",
                    page,
                    "生图提示词出现审稿散文，应改为可直接画图的提示词",
                    "、".join(hits),
                    level,
                )
            )
    return issues


def format_sketch_for_imagegen(sketch: str) -> str:
    text = sketch.strip()
    if not text:
        return ""
    return re.sub(r"\n{3,}", "\n\n", text)
