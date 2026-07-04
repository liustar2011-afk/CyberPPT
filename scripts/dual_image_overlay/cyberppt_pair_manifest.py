#!/usr/bin/env python3
"""Build CyberPPT-owned dual-image pair manifests.

This is the CyberPPT side of the "script -> dual images -> editable PPT"
pipeline. It compiles the repo's stage/ImageGen script into final-deliverable
content-region prompts, writes a page_image_pairs.json compatible with the
editable overlay rebuild step, and verifies that the expected image files exist.

It intentionally does not import ppt-master's page_image_pair_batch.py or its
style preset system.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.dual_image_overlay.deliverable_prompt import (
    compile_pages,
    parse_page_blocks,
    parse_pages,
)


CANVAS = {"width": 1280, "height": 720}
CONTENT_REGION = {"x": 32, "y": 98, "width": 1216, "height": 589}
GENERATION_SIZE = {"width": 2432, "height": 1184}
OUTPUT_VARIANTS = ["full", "background"]


def _slug(text: str, fallback: str = "page") -> str:
    normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", text).strip("_")
    return (normalized or fallback)[:36]


def _page_stem(page_number: int, title: str) -> str:
    return f"page_{page_number:03d}_{_slug(title)}"


def _compiled_script_path(output_dir: Path, source: Path, pages: list[int]) -> Path:
    first = pages[0]
    last = pages[-1]
    return output_dir / f"{source.stem}_cyberppt_deliverable_p{first}_p{last}.md"


def _background_prompt(page_number: int) -> str:
    return f"""请将输入图作为唯一视觉母版进行 image-to-image 编辑，只生成第【{page_number}】页正文内容区的无文字背景图。

【核心任务】
参照输入的 full 正文内容区图片，生成同一内容区、同一构图、同一图形关系的无文字底稿。不要重新文生图，不要更换构图，不要生成同主题新图。输出图必须可以直接作为 PPT 正文区底图，与 full 图形成同版式的图片版页面组合。

必须严格保留：输入图的画布比例、整体版式、空间结构、配色、材质、图形关系、流程线、关系箭头、容器、底座、语义小图、背景装饰、阴影、留白、浅色文字承载面、模块标签条和所有非文字图形元素的位置与尺度。

必须删除：所有可读文字、数字、页码、标题、副标题、标签、注释、标点、水印、伪文字、乱码和文字残影。删除后相应区域应恢复为完整的纯色/浅色/低纹理承载面或原本的底层材质。

禁止：新增任何文字、数字、乱码、符号、水印；禁止生成完整 PPT 页面、页眉、页脚、中电联公共元素；禁止改变图形语义关系；禁止出现模糊补丁、涂抹块、局部重绘错位、重复元素或新装饰。
"""


def _mark_status(item: dict[str, Any], *, force_pending: bool = False) -> None:
    path = Path(item["path"])
    if path.is_file() and path.stat().st_size > 0 and not force_pending:
        item["status"] = "Generated"
        item["generated_at"] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        item.pop("last_error", None)
    else:
        item["status"] = "Pending"
        item.pop("generated_at", None)
        if not path.is_file():
            item["last_error"] = f"Missing expected CyberPPT image file: {path}"


def build_manifest(
    *,
    script: Path,
    pages_raw: str,
    output_dir: Path,
    project_path: Path | None,
    style_lock: Path | None,
    force_pending: bool = False,
) -> tuple[dict[str, Any], Path, Path, list[int]]:
    source_pages = parse_page_blocks(script)
    page_numbers = parse_pages(pages_raw, set(source_pages))
    output_dir.mkdir(parents=True, exist_ok=True)
    compiled_script = _compiled_script_path(output_dir, script, page_numbers)
    compiled = compile_pages(script, page_numbers, style_lock_path=style_lock)
    compiled_script.write_text(compiled, encoding="utf-8")

    compiled_pages = parse_page_blocks(compiled_script)
    pairs: list[dict[str, Any]] = []
    for page_number in page_numbers:
        page = compiled_pages[page_number]
        stem = _page_stem(page_number, page.title)
        full_path = output_dir / f"{stem}_full.png"
        background_path = output_dir / f"{stem}_background.png"
        full = {
            "filename": full_path.name,
            "path": str(full_path),
            "prompt": page.text,
            "aspect_ratio": "content-region",
            "image_size": "2x-content-region",
            "canvas": f"{GENERATION_SIZE['width']}x{GENERATION_SIZE['height']}",
        }
        background = {
            "filename": background_path.name,
            "path": str(background_path),
            "prompt": _background_prompt(page_number),
            "aspect_ratio": "content-region",
            "image_size": "2x-content-region",
            "canvas": f"{GENERATION_SIZE['width']}x{GENERATION_SIZE['height']}",
        }
        _mark_status(full, force_pending=force_pending)
        _mark_status(background, force_pending=force_pending)
        pairs.append(
            {
                "page_number": page_number,
                "title": page.title,
                "page_script": page.text,
                "full": full,
                "background": background,
            }
        )

    manifest = {
        "mode": "cyberppt-dual-image-pair",
        "output_variants": OUTPUT_VARIANTS,
        "generation_contract": {
            "mode": "template-content-region",
            "owner": "CyberPPT",
            "slide_canvas": CANVAS,
            "content_region": CONTENT_REGION,
            "generation_size": GENERATION_SIZE,
            "rule": "Generate content-area images only; PPT title, subtitle and enterprise chrome are handled by template/export code.",
        },
        "project_path": str(project_path.resolve()) if project_path else "",
        "source_script": str(compiled_script.resolve()),
        "original_script": str(script.resolve()),
        "style_lock": str(style_lock.resolve()) if style_lock else None,
        "output_dir": str(output_dir.resolve()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pairs": pairs,
    }
    manifest_path = output_dir / "page_image_pairs.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest, manifest_path, compiled_script, page_numbers


def require_generated(manifest: dict[str, Any]) -> None:
    missing: list[str] = []
    for pair in manifest.get("pairs", []):
        for variant in OUTPUT_VARIANTS:
            item = pair.get(variant) or {}
            path = Path(str(item.get("path", "")))
            if not path.is_file() or path.stat().st_size <= 0:
                missing.append(str(path))
    if missing:
        raise FileNotFoundError(
            "CyberPPT image files are not generated yet. Generate full/background images with the "
            "CyberPPT image workflow, then rerun with --resume.\nMissing:\n"
            + "\n".join(missing)
        )


def _copy_existing_images(existing_manifest: Path, output_dir: Path, *, force: bool = False) -> None:
    data = json.loads(existing_manifest.read_text(encoding="utf-8"))
    for pair in data.get("pairs", []):
        page_number = int(pair["page_number"])
        title = str(pair.get("title") or f"page_{page_number}")
        stem = _page_stem(page_number, title)
        for variant in OUTPUT_VARIANTS:
            item = pair.get(variant) or {}
            source = Path(str(item.get("path", ""))).expanduser()
            if not source.is_file():
                continue
            target = output_dir / f"{stem}_{variant}.png"
            if target.exists() and not force:
                continue
            shutil.copy2(source, target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create CyberPPT dual-image pair manifests.")
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--pages", default="all")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--project-path", type=Path)
    parser.add_argument("--style-lock", type=Path)
    parser.add_argument("--resume", action="store_true", help="Reuse existing images in output-dir if present.")
    parser.add_argument("--force", action="store_true", help="Mark images pending and overwrite copied cache images.")
    parser.add_argument("--require-generated", action="store_true", help="Fail if full/background images are missing.")
    parser.add_argument("--copy-images-from", type=Path, help="Optional existing page_image_pairs.json to seed image files.")
    args = parser.parse_args()

    if args.copy_images_from:
        _copy_existing_images(args.copy_images_from.resolve(), args.output_dir.resolve(), force=args.force)

    manifest, manifest_path, compiled_script, page_numbers = build_manifest(
        script=args.script.resolve(),
        pages_raw=args.pages,
        output_dir=args.output_dir.resolve(),
        project_path=args.project_path.resolve() if args.project_path else None,
        style_lock=args.style_lock.resolve() if args.style_lock else None,
        force_pending=bool(args.force and not args.resume),
    )
    if args.require_generated:
        require_generated(manifest)
    print(json.dumps({
        "manifest": str(manifest_path),
        "compiled_script": str(compiled_script),
        "pages": page_numbers,
        "pairs": len(manifest["pairs"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
