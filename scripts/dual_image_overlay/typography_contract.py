from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PX_PER_PT = 4 / 3

DEFAULT_BOUNDS = {
    "left": 32.0,
    "right": 1248.0,
    "header_right": 1040.0,
}

TYPOGRAPHY_TARGETS_PT = {
    "T2": 22.5,
    "T3": 11.0,
    "T4": 13.0,
    "T6": 12.5,
    "T7": 10.5,
    "T8": 12.0,
    "T10": 11.0,
    "T13": 24.0,
}

TYPOGRAPHY_MIN_PT = {
    "T2": 18.0,
    "T3": 10.0,
    "T4": 11.0,
    "T6": 11.0,
    "T7": 9.5,
    "T8": 10.0,
    "T10": 9.5,
    "T13": 18.0,
}

TEXT_RE = re.compile(r"<text(?P<attrs>[^>]*)>(?P<text>.*?)</text>", re.S)
ATTR_RE = re.compile(r"(?P<name>[\w:-]+)=(?P<quote>[\"'])(?P<value>.*?)(?P=quote)")
DEFAULT_RULES_PATH = Path(__file__).with_name("default_layout_rules.json")


@dataclass(frozen=True)
class TypographyDecision:
    text: str
    rendered_text: str
    role: str
    x: float
    y: float
    original_px: float
    target_px: float
    applied_px: float


def pt_to_px(value: float) -> float:
    return value * PX_PER_PT


def _attrs_to_dict(raw: str) -> dict[str, str]:
    return {match.group("name"): match.group("value") for match in ATTR_RE.finditer(raw)}


def _replace_attr(raw: str, name: str, value: str) -> str:
    pattern = re.compile(rf"({re.escape(name)}=)([\"']).*?\2")
    if pattern.search(raw):
        return pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}{value}{match.group(2)}", raw, count=1)
    return raw.rstrip() + f' {name}="{value}"'


def _number(value: str | None, default: float = 0.0) -> float:
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def load_layout_rules(path: Path | None = None) -> dict[str, Any]:
    rules_path = path or DEFAULT_RULES_PATH
    if not rules_path.exists():
        return {}
    return json.loads(rules_path.read_text(encoding="utf-8"))


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _match_rule(text: str, attrs: dict[str, str], match: dict[str, Any]) -> bool:
    compact = _compact_text(text)
    x = _number(attrs.get("x"))
    y = _number(attrs.get("y"))
    anchor = attrs.get("text-anchor", attrs.get("text_anchor", "start"))
    if "x_min" in match and x < float(match["x_min"]):
        return False
    if "x_max" in match and x > float(match["x_max"]):
        return False
    if "y_min" in match and y < float(match["y_min"]):
        return False
    if "y_max" in match and y > float(match["y_max"]):
        return False
    if "text_anchor" in match and anchor != match["text_anchor"]:
        return False
    if "text_equals_any" in match and compact not in {_compact_text(str(item)) for item in match["text_equals_any"]}:
        return False
    if "text_contains_any" in match and not any(str(item) in compact for item in match["text_contains_any"]):
        return False
    return True


def estimate_text_width_px(text: str, font_size_px: float) -> float:
    def line_width(line: str) -> float:
        width = 0.0
        for char in line:
            if ord(char) > 127:
                width += font_size_px
            elif char.isspace():
                width += font_size_px * 0.3
            elif char.isdigit() or char in ".%":
                width += font_size_px * 0.58
            else:
                width += font_size_px * 0.56
        return width

    return max((line_width(line) for line in text.splitlines()), default=0.0)


def _tokenize_for_wrap(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9&./%+-]+|[\u4e00-\u9fff]|[^\s]", text)


def _semantic_wrap_candidates(text: str, rules: dict[str, Any]) -> list[tuple[int, str]]:
    compact = _compact_text(text)
    candidates: list[tuple[int, str]] = []
    line_break_rules = rules.get("line_break", {})
    phrase_breaks = line_break_rules.get("phrase_breaks", {})
    if compact in phrase_breaks:
        candidates.append((0, phrase_breaks[compact]))
    break_before = tuple(line_break_rules.get("break_before", []))
    for marker in break_before:
        index = compact.find(marker)
        if index > 1:
            candidates.append((1, compact[:index] + "\n" + compact[index:]))
    break_after = tuple(line_break_rules.get("break_after", []))
    for marker in break_after:
        index = compact.find(marker)
        if 1 <= index < len(compact) - 2:
            candidates.append((2, compact[: index + 1] + "\n" + compact[index + 1 :]))
    midpoint = len(compact) // 2
    if len(compact) >= 8:
        for offset in (0, -1, 1, -2, 2):
            index = midpoint + offset
            if 2 <= index <= len(compact) - 2:
                candidates.append((3, compact[:index] + "\n" + compact[index:]))
    seen: set[str] = set()
    unique: list[tuple[int, str]] = []
    for priority, candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique.append((priority, candidate))
    return unique


def _best_semantic_wrap(text: str, font_size_px: float, width_px: float, max_lines: int, rules: dict[str, Any]) -> str | None:
    best: tuple[float, str] | None = None
    for priority, candidate in _semantic_wrap_candidates(text, rules):
        lines = candidate.splitlines()
        if len(lines) > max_lines or any(not line for line in lines):
            continue
        line_widths = [estimate_text_width_px(line, font_size_px) for line in lines]
        if max(line_widths) > width_px:
            continue
        balance = max(line_widths) - min(line_widths)
        crowding = max(line_widths) / max(width_px, 1.0)
        score = priority * 1000 + balance + crowding * font_size_px
        if best is None or score < best[0]:
            best = (score, candidate)
    return best[1] if best else None


def wrap_text_to_width(text: str, font_size_px: float, width_px: float, max_lines: int = 2, rules: dict[str, Any] | None = None) -> str:
    rules = rules or {}
    compact = _compact_text(text)
    if not compact:
        return compact
    semantic = _best_semantic_wrap(compact, font_size_px, width_px, max_lines, rules)
    if semantic and len(compact) >= 6:
        return semantic
    if estimate_text_width_px(compact, font_size_px) <= width_px:
        return compact

    lines: list[str] = []
    current = ""
    for token in _tokenize_for_wrap(compact):
        candidate = current + token
        if current and estimate_text_width_px(candidate, font_size_px) > width_px:
            lines.append(current)
            current = token
        else:
            current = candidate
    if current:
        lines.append(current)

    for index in range(len(lines) - 1):
        if lines[index].endswith(("与", "和")):
            moved = lines[index][-1]
            candidate_next = moved + lines[index + 1]
            if estimate_text_width_px(candidate_next, font_size_px) <= width_px:
                lines[index] = lines[index][:-1]
                lines[index + 1] = candidate_next
    lines = [line for line in lines if line]

    if len(lines) <= max_lines:
        return "\n".join(lines)

    balanced: list[str] = []
    remaining = "".join(lines)
    remaining_tokens = _tokenize_for_wrap(remaining)
    for line_index in range(max_lines):
        if line_index == max_lines - 1:
            balanced.append("".join(remaining_tokens))
            break
        current = ""
        while remaining_tokens:
            candidate = current + remaining_tokens[0]
            remaining_text = "".join(remaining_tokens[1:])
            remaining_lines = max_lines - line_index - 1
            if (
                current
                and estimate_text_width_px(candidate, font_size_px) > width_px
                and estimate_text_width_px(remaining_text, font_size_px) <= width_px * remaining_lines
            ):
                break
            current = candidate
            remaining_tokens.pop(0)
        balanced.append(current)
    return "\n".join(line for line in balanced if line)


def classify_text(text: str, x: float, y: float, fill: str, font_weight: str) -> str:
    compact = _compact_text(text)
    if y < 80:
        return "T2"
    if compact.isdigit() and len(compact) <= 2:
        return "T4"
    if re.fullmatch(r"\d+\.\d+", compact) and y < 360:
        return "T13"
    if fill.upper() == "#FFFFFF" and y > 560 and len(compact) >= 16:
        return "T8"
    if fill.upper() == "#FFFFFF" and y > 560:
        return "T10"
    if y > 560 and ("建议" in compact or "趋势" in compact or "根本动因" in compact):
        return "T10"
    if font_weight in {"700", "bold"} or len(compact) <= 22:
        return "T6"
    return "T7"


def _available_width(
    attrs: dict[str, str],
    role: str,
    bounds: dict[str, float],
    text: str = "",
    rules: dict[str, Any] | None = None,
) -> float:
    for rule in (rules or {}).get("available_width_rules", []):
        if _match_rule(text, attrs, rule.get("match", {})):
            return float(rule["width"])
    x = _number(attrs.get("x"))
    y = _number(attrs.get("y"))
    anchor = attrs.get("text-anchor", "start")
    if 160 <= y <= 430:
        if x >= 560:
            return 132.0
        if x <= 460:
            return 150.0
    if 480 <= y <= 560 and anchor == "middle":
        return 170.0
    right = bounds["header_right"] if role == "T2" else bounds["right"]
    left = bounds["left"]
    if anchor == "middle":
        return max(1.0, 2 * min(abs(x - left), abs(right - x)))
    if anchor == "end":
        return max(1.0, x - left)
    return max(1.0, right - x)


def _wrap_rule_for_text(text: str, attrs: dict[str, str], rules: dict[str, Any]) -> dict[str, Any] | None:
    for rule in rules.get("wrap_rules", []):
        if _match_rule(text, attrs, rule.get("match", {})):
            return rule
    return None


def _should_wrap_before_fitting(text: str, role: str, attrs: dict[str, str], rules: dict[str, Any]) -> bool:
    if _wrap_rule_for_text(text, attrs, rules) is not None:
        return True
    if role in {"T4", "T13"}:
        return False
    compact = _compact_text(text)
    if len(compact) <= 4:
        return False
    x = _number(attrs.get("x"))
    y = _number(attrs.get("y"))
    return 160 <= y <= 430 and (x >= 560 or x <= 460)


def _wrapped_text_for_fit(text: str, role: str, attrs: dict[str, str], bounds: dict[str, float], rules: dict[str, Any]) -> str:
    target = pt_to_px(TYPOGRAPHY_TARGETS_PT[role])
    available = _available_width(attrs, role, bounds, text, rules) * 0.96
    wrap_rule = _wrap_rule_for_text(text, attrs, rules)
    max_lines = int(wrap_rule.get("max_lines", 2)) if wrap_rule else 2
    if not _should_wrap_before_fitting(text, role, attrs, rules):
        return text
    return wrap_text_to_width(text, target, available, max_lines=max_lines, rules=rules)


def _alignment_adjusted_attrs(text: str, attrs: dict[str, str], rules: dict[str, Any]) -> dict[str, str]:
    adjusted = dict(attrs)
    for rule in rules.get("alignment_rules", []):
        if _match_rule(text, adjusted, rule.get("match", {})):
            adjusted.update({str(key): str(value) for key, value in rule.get("set", {}).items()})
    return adjusted


def _line_height_ratio(text: str, attrs: dict[str, str], rules: dict[str, Any]) -> float:
    for rule in rules.get("line_height_rules", []):
        if _match_rule(text, attrs, rule.get("match", {})):
            return float(rule.get("ratio", 1.16))
    return 1.16


def _baseline_center_offset_px(text: str, attrs: dict[str, str], font_size_px: float, rules: dict[str, Any]) -> float:
    for rule in rules.get("baseline_offset_rules", []):
        if _match_rule(text, attrs, rule.get("match", {})):
            return font_size_px * float(rule.get("em", 0.0))
    return 0.0


def _render_svg_text_body(text: str, attrs: dict[str, str], font_size_px: float, rules: dict[str, Any]) -> str:
    lines = text.splitlines()
    if len(lines) <= 1:
        return html.escape(text, quote=False)

    x = _number(attrs.get("x"))
    y = _number(attrs.get("y"))
    line_height = font_size_px * _line_height_ratio(text, attrs, rules)
    first_y = y + _baseline_center_offset_px(text, attrs, font_size_px, rules) - ((len(lines) - 1) * line_height / 2)
    return "".join(
        f'<tspan x="{x:.2f}" y="{first_y + index * line_height:.2f}">{html.escape(line, quote=False)}</tspan>'
        for index, line in enumerate(lines)
    )


def fitted_font_px(
    text: str,
    role: str,
    attrs: dict[str, str],
    bounds: dict[str, float],
    rules: dict[str, Any] | None = None,
) -> float:
    target = pt_to_px(TYPOGRAPHY_TARGETS_PT[role])
    minimum = pt_to_px(TYPOGRAPHY_MIN_PT[role])
    available = _available_width(attrs, role, bounds, text, rules) * 0.96
    estimated = estimate_text_width_px(text, target)
    if estimated <= available:
        return target
    if estimated <= 0:
        return target
    return max(minimum, target * available / estimated)


def apply_typography_to_svg_text(
    svg: str,
    bounds: dict[str, float] | None = None,
    rules: dict[str, Any] | None = None,
) -> tuple[str, list[TypographyDecision]]:
    bounds = {**DEFAULT_BOUNDS, **(bounds or {})}
    rules = rules if rules is not None else load_layout_rules()
    decisions: list[TypographyDecision] = []

    def replace(match: re.Match[str]) -> str:
        raw_attrs = match.group("attrs")
        attrs = _attrs_to_dict(raw_attrs)
        text = html.unescape(re.sub(r"<.*?>", "", match.group("text")).strip())
        if not text:
            return match.group(0)
        x = _number(attrs.get("x"))
        y = _number(attrs.get("y"))
        original = _number(attrs.get("font-size"), 16.0)
        role = classify_text(text, x, y, attrs.get("fill", ""), attrs.get("font-weight", "400"))
        layout_attrs = _alignment_adjusted_attrs(text, attrs, rules)
        rendered_text = _wrapped_text_for_fit(text, role, layout_attrs, bounds, rules)
        applied = round(fitted_font_px(rendered_text, role, layout_attrs, bounds, rules), 2)
        decisions.append(
            TypographyDecision(
                text=text,
                rendered_text=rendered_text,
                role=role,
                x=_number(layout_attrs.get("x")),
                y=_number(layout_attrs.get("y")),
                original_px=original,
                target_px=round(pt_to_px(TYPOGRAPHY_TARGETS_PT[role]), 2),
                applied_px=applied,
            )
        )
        updated = _replace_attr(raw_attrs, "font-size", f"{applied:.2f}")
        if layout_attrs.get("x") != attrs.get("x"):
            updated = _replace_attr(updated, "x", layout_attrs["x"])
        if layout_attrs.get("y") != attrs.get("y"):
            updated = _replace_attr(updated, "y", layout_attrs["y"])
        if layout_attrs.get("text-anchor") != attrs.get("text-anchor"):
            updated = _replace_attr(updated, "text-anchor", layout_attrs["text-anchor"])
        if role in {"T2", "T4", "T6", "T8", "T10", "T13"}:
            updated = _replace_attr(updated, "font-weight", "700")
        return f"<text{updated}>{_render_svg_text_body(rendered_text, layout_attrs, applied, rules)}</text>"

    return TEXT_RE.sub(replace, svg), decisions


def apply_typography_file(
    input_svg: Path,
    output_svg: Path | None = None,
    report_path: Path | None = None,
    rules_path: Path | None = None,
) -> list[TypographyDecision]:
    rules = load_layout_rules(rules_path)
    updated, decisions = apply_typography_to_svg_text(input_svg.read_text(encoding="utf-8"), rules=rules)
    target = output_svg or input_svg
    target.write_text(updated, encoding="utf-8")
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "schema": "cyberppt.dual_image.typography_contract.v1",
                    "source": str(input_svg),
                    "output": str(target),
                    "rules": str(rules_path or DEFAULT_RULES_PATH),
                    "decisions": [asdict(decision) for decision in decisions],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return decisions


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply CyberPPT Typography Scale to overlay SVG text.")
    parser.add_argument("svg", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--rules", type=Path)
    args = parser.parse_args()
    decisions = apply_typography_file(args.svg, args.out, args.report, args.rules)
    print(json.dumps({"updated": len(decisions)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
