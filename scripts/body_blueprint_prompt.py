from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.dual_image_overlay.deliverable_prompt import (
    PageBlock,
    layout_density_directives,
    parse_page_blocks,
    parse_pages,
    template_title,
    visible_deliverable_lines,
)


DEFAULT_PRESET_DIR = Path(__file__).parent / "dual_image_overlay" / "style_presets"


def available_style_presets(preset_dir: Path = DEFAULT_PRESET_DIR) -> dict[str, Path]:
    presets: dict[str, Path] = {}
    if not preset_dir.exists():
        return presets
    for path in sorted(preset_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        preset_id = str(data.get("id") or path.stem)
        presets[preset_id] = path
    return presets


def load_style(*, preset: str | None = None, style_file: Path | None = None) -> dict[str, Any]:
    if style_file is not None:
        return json.loads(style_file.read_text(encoding="utf-8"))
    presets = available_style_presets()
    preset_id = preset or "gray_green"
    if preset_id not in presets:
        raise ValueError(f"Unknown style preset '{preset_id}'. Available: {', '.join(sorted(presets))}")
    return json.loads(presets[preset_id].read_text(encoding="utf-8"))


def style_contract(style: dict[str, Any]) -> str:
    return str(style.get("prompt_contract") or f"视觉风格使用 {style.get('name', style.get('id', 'selected style'))}。")


def neutralize_style_words(text: str) -> str:
    return (
        text.replace("墨绿通栏", "强调色通栏")
        .replace("墨绿结论条", "强调色结论条")
        .replace("墨绿", "强调色")
        .replace("深蓝结论条", "强调色结论条")
        .replace("深蓝通栏", "强调色通栏")
    )


def render_body_blueprint_prompt(page: PageBlock, style: dict[str, Any]) -> str:
    body = "\n".join(f"- {line}" for line in visible_deliverable_lines(page))
    directives = "\n".join(f"- {neutralize_style_words(line)}" for line in layout_density_directives(page))
    return f"""## 第{page.page_number}页：{page.title}

【用途】
生成企业模板正文内容区的高密度视觉蓝图，不是完整 PPT 页面，也不是最终文字成品。最终 PPT 的标题、副标题、蓝线、Logo、页码和页脚由企业模板脚本确定性生成。

【内容锁定】
模板标题：{template_title(page)}
正文区可见内容：
{body}

【正文区边界】
只生成正文内容区画面。不要生成标题、副标题、蓝线、Logo、页脚、页码、母版红线、完整 PPT 外框或任何企业公共元素。
正文区内部必须保持高信息密度，允许使用矩阵、右侧栏、编号 chips、细线分隔、流程轴、分层带、底部 SO WHAT 条和克制线性图标。
图片中的小字只作为蓝图占位，最终可编辑 PPT 文字必须使用 content-lock / 脚本文本重建。

【风格】
{style_contract(style)}

【结构密度】
不要生成稀疏卡片页。保留原脚本组件数量、组件关系、网格/流程/卡片结构和底部 SO WHAT 区。
{directives}

【质量约束】
中文为主；不得新增事实、数字、标语、伪字水印、来源编号或调试文字。正文区内部容器要边界清楚、网格对齐、细线分隔稳定，适合后续按视觉蓝图重建为可编辑 PPT 对象。
""".strip() + "\n"


def compile_body_blueprint_prompts(script_path: Path, pages: Iterable[int], style: dict[str, Any]) -> str:
    blocks = parse_page_blocks(script_path)
    rendered: list[str] = []
    for page_number in pages:
        if page_number not in blocks:
            raise ValueError(f"Page {page_number} not found in script: {script_path}")
        rendered.append(render_body_blueprint_prompt(blocks[page_number], style))
    return "\n".join(rendered)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile high-density body-region blueprint prompts with selectable style presets.")
    parser.add_argument("script", type=Path)
    parser.add_argument("--pages", default="all")
    parser.add_argument("--style-preset", default="gray_green")
    parser.add_argument("--style-file", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    blocks = parse_page_blocks(args.script)
    pages = parse_pages(args.pages, set(blocks))
    style = load_style(preset=args.style_preset, style_file=args.style_file)
    output = compile_body_blueprint_prompts(args.script, pages, style)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(output, encoding="utf-8")
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(
                {
                    "schema": "cyberppt.body_blueprint_prompt_manifest.v1",
                    "source_script": str(args.script),
                    "pages": pages,
                    "style": {
                        "id": style.get("id"),
                        "name": style.get("name"),
                    },
                    "style_file": str(args.style_file) if args.style_file else str(available_style_presets().get(str(style.get("id")))),
                    "output": str(args.out),
                    "policy": {
                        "body_region_only": True,
                        "enterprise_chrome_generated_by_template": True,
                        "blueprint_text_is_placeholder": True,
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
