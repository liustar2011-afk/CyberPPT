from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..pages_index import active_page_files
from ..render import build_speaker_notes_payload, render_speaker_notes
from ..script_parser import parse_script
from ..workflow import assert_assembly_allowed


def _page_nature(content: str) -> str:
    match = re.search(r"^页面性质[：:]\s*(模板页|内容页)\s*$", content, re.MULTILINE)
    return match.group(1) if match else ""


def assemble_project(
    project: Path,
    meta: dict,
    *,
    build_imagegen: Callable[[str, str], str],
    build_index: Callable[[str, str], dict],
) -> list[Path]:
    assert_assembly_allowed(project)
    pages = active_page_files(project)
    if not pages:
        raise ValueError("pages/ 目录为空，尚无页面文件可组装。")
    output_dir = project / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = output_dir / "script-final.md"
    imagegen_path = output_dir / "script-imagegen.md"
    index_path = output_dir / "outline-index.json"
    notes_path = output_dir / "script-speaker-notes.md"
    notes_json_path = output_dir / "speaker-notes.json"
    now = datetime.now()
    final = [f"# {meta['name']} · PPT内容脚本", f"\n生成时间：{now:%Y-%m-%d %H:%M}", f"页面总数：{len(pages)}", "\n---\n", "## 页面脚本\n"]
    page_contents = [(page, page.read_text(encoding="utf-8").strip()) for page in pages]
    content_pages = [(page, content) for page, content in page_contents if _page_nature(content) == "内容页"]
    template_pages = [page.stem for page, content in page_contents if _page_nature(content) == "模板页"]
    imagegen = [f"# {meta['name']} · IMAGE-2逐页生图提示词", f"\n生成时间：{now:%Y-%m-%d %H:%M}", f"内容页数量：{len(content_pages)}", f"模板页已排除：{'、'.join(template_pages)}", "\n全局约束：只生成下列内容页并保留原始页码；只有每页【画面文字白名单】中的文字允许出现在画面中，其余文字均为语义和构图指令。", "\n---\n"]
    outline = project / "outline/02-outline.md"
    if outline.exists() and outline.stat().st_size > 80:
        final.extend(["## 提纲索引\n", outline.read_text(encoding="utf-8").strip(), "\n\n---\n"])
    entries = []
    for page, content in page_contents:
        if not content:
            continue
        final.extend([content, "\n\n---\n"])
        if _page_nature(content) == "内容页":
            imagegen.extend([build_imagegen(content, page.stem), "\n\n---\n"])
        entries.append(build_index(content, page.name))
    final_path.write_text("\n".join(final), encoding="utf-8")
    imagegen_path.write_text("\n".join(imagegen), encoding="utf-8")
    legacy_compact = output_dir / "script-imagegen-compact.md"
    if legacy_compact.exists():
        legacy_compact.unlink()
    index_path.write_text(json.dumps({"schema": "ppt-script.outline_index.v1", "project": meta["name"], "generated_at": now.isoformat(timespec="seconds"), "pages": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    slides = parse_script("\n\n---\n\n".join(page.read_text(encoding="utf-8") for page in pages))
    notes_path.write_text(render_speaker_notes(meta["name"], slides), encoding="utf-8")
    notes_json_path.write_text(json.dumps(build_speaker_notes_payload(meta["name"], slides), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    meta.update({"stage": "assembled", "assembled": now.isoformat(), "imagegen_assembled": now.isoformat(), "speaker_notes_assembled": now.isoformat()})
    meta.pop("imagegen_compact_assembled", None)
    (project / "project.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return [final_path, imagegen_path, index_path, notes_path, notes_json_path]
