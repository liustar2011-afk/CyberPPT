"""Render a page script's 上屏文字 as real nested Markdown for human review.

The authoritative script format is deliberately plain text with indentation
(no ``-``/``#``/``**`` markers -- see ``ONSCREEN_MARKDOWN_LEAK``), because
``script-audit`` reads hierarchy from indentation, not Markdown syntax. A
generic Markdown viewer ignores leading whitespace on plain paragraph lines,
so that same file does not visually show its hierarchy when previewed.
This command produces a separate, human-facing rendering with real nested
Markdown bullets from the same indentation the authoritative file already
carries. It never edits the source script.
"""

from __future__ import annotations

from pathlib import Path

from cyberppt.script_quality.parsing import _field_blocks, _line_indent


def render_onscreen_markdown(script_path: Path) -> str:
    script_path = script_path.expanduser().resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"script does not exist: {script_path}")
    text = script_path.read_text(encoding="utf-8")
    fields = _field_blocks(text)
    subtitle = fields.get("副标题", "").strip()
    onscreen = fields.get("上屏文字", "")
    lines_out: list[str] = []
    if subtitle:
        lines_out.append(f"**副标题：** {subtitle}")
        lines_out.append("")
    for line in onscreen.splitlines():
        if not line.strip():
            continue
        indent = _line_indent(line)
        level = indent // 2
        lines_out.append(f"{'  ' * level}- {line.strip()}")
    return "\n".join(lines_out) + "\n"


def preview_onscreen_markdown(script_path: Path, output_path: Path | None = None) -> Path | str:
    rendered = render_onscreen_markdown(script_path)
    if output_path is None:
        return rendered
    output_path = output_path.expanduser().resolve()
    output_path.write_text(rendered, encoding="utf-8", newline="\n")
    return output_path
