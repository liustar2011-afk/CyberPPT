#!/usr/bin/env python3
"""Build CyberPPT-owned dual-image pair manifests.

This is the CyberPPT side of the "approved body blueprint -> full/background
images -> editable PPT" pipeline. It can promote approved blueprint PNGs to
full images, compiles final-deliverable content-region prompts for repairs, writes
a page_image_pairs.json compatible with the editable overlay rebuild step, and
verifies that the expected image files exist.

It intentionally does not import any legacy image-pair batch generator or
external style preset system.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.dual_image_overlay.deliverable_prompt import (
    compile_pages,
    parse_page_blocks,
    parse_pages,
    render_prompt,
)
from scripts.dual_image_overlay.rebuild_engine.codex_oauth_image import ensure_output_size
from scripts.dual_image_overlay.style_library import write_project_style_lock
from cyberppt.commands.script_gate import assert_approved_final_script


# Stage 02 images are body-only assets.  Their native contract is 2:1; the
# 16:9 slide canvas and chrome are supplied later by the PPT template.
CANVAS = {"width": 2048, "height": 1024}
CONTENT_REGION = {"x": 0, "y": 0, "width": 2048, "height": 1024}
# API-valid 16-multiple canvas used for ImageGen request + full-image ingest resize.
GENERATION_SIZE = {"width": 2048, "height": 1024}
GENERATION_SIZE_TEXT = f"{GENERATION_SIZE['width']}x{GENERATION_SIZE['height']}"
FULL_IMAGE_MODE = "full-image"
DUAL_IMAGE_MODE = "editable-overlay"
TRIPLE_IMAGE_MODE = "editable-overlay-text-reference"
PRODUCTION_MODES = (FULL_IMAGE_MODE, DUAL_IMAGE_MODE, TRIPLE_IMAGE_MODE)
FULL_GENERATION_METHOD = "text_to_image_generate_full"
BACKGROUND_GENERATION_METHOD = "image_to_image_edit_from_full"
TEXT_REFERENCE_GENERATION_METHOD = "image_to_image_edit_from_full"
BLUEPRINT_PATTERNS = (
    "slide-{page:03d}-blueprint.png",
    "slide-{page:02d}-blueprint.png",
    "slide-{page}-blueprint.png",
    "page_{page:03d}_blueprint.png",
    "page-{page:03d}-blueprint.png",
)


def _slug(text: str, fallback: str = "page") -> str:
    normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", text).strip("_")
    return (normalized or fallback)[:36]


def _page_stem(page_number: int, title: str) -> str:
    return f"page_{page_number:03d}_{_slug(title)}"


def _compiled_script_path(output_dir: Path, source: Path, pages: list[int]) -> Path:
    first = pages[0]
    last = pages[-1]
    return output_dir / f"{source.stem}_cyberppt_deliverable_p{first}_p{last}.md"


FULL_DUAL_IMAGE_CONTAINER_CONTRACT = """【双图容器隔离规则｜不上屏】
所有插图、照片、界面、图表、教材、文件或设备画面必须完整位于独立且边界清晰的矩形或圆形插图容器内。
页面级标题、正文、编号、标签和结论文字必须位于插图容器之外；不得覆盖插图，不得与插图容器交叠，并与容器保持清晰留白。
插图容器内部允许出现属于插图内容的自然文字，例如界面标签、图表刻度、教材封面、文件内容和设备铭牌；这些文字视为插图像素的一部分。
容器数量、位置、尺寸和组合方式由本页内容决定；不得为了满足容器规则机械生成等权卡片、固定分栏或一项内容一个容器。
优先使用矩形插图容器；圆形容器仅用于适合圆形裁切的局部物件或小型图表。禁止使用半透明页面正文浮层覆盖插图。"""


def _full_prompt_for_variants(prompt: str, output_variants: list[str]) -> str:
    """Add separability guidance only when a no-text background will be derived."""

    if "background" not in output_variants:
        return prompt
    return f"{prompt.rstrip()}\n\n{FULL_DUAL_IMAGE_CONTAINER_CONTRACT}\n"


def _background_prompt(page_number: int) -> str:
    return f"""请将输入图作为唯一视觉母版进行 image-to-image 编辑，只生成第【{page_number}】页正文内容区的无文字背景图。

【核心任务】
参照输入的 full 正文内容区图片，生成同一内容区、同一构图、同一图形关系的无文字底稿。不要重新文生图，不要更换构图，不要生成同主题新图。输出图必须可以直接作为 PPT 正文区底图，与 full 图形成同版式的图片版页面组合。

必须严格保留：输入图的画布比例、整体版式、空间结构、配色、材质、图形关系、流程线、关系箭头、容器、底座、语义小图、背景装饰、阴影、留白、浅色文字承载面、模块标签条和所有非文字图形元素的位置与尺度。

插图容器识别规则：先识别边界清晰的矩形或圆形插图容器。照片、界面、图表、教材、文件或设备画面均属于插图；插图容器内部的全部像素和文字视为一个不可拆分的整体。

必须保留：所有插图容器及其内部的全部像素和文字，包括界面标签、图表刻度、教材封面、文件内容和设备铭牌。不得删除、翻译、纠正、重写或重新生成插图容器内部的文字。

必须删除：插图容器之外的页面级标题、正文、编号、标签、结论文字、页码、水印、伪文字、乱码和文字残影。删除后相应区域应恢复为完整的纯色/浅色/低纹理承载面或原本的底层材质。

禁止：在插图容器之外新增任何文字、数字、乱码、符号或水印；禁止生成完整 PPT 页面、页眉、页脚、中电联公共元素；禁止改变图形语义关系；禁止出现模糊补丁、涂抹块、局部重绘错位、重复元素或新装饰。
"""


def _text_reference_prompt(page_number: int) -> str:
    return f"""Edit the supplied full content image for page {page_number} into an OCR reference.
Keep the exact canvas, text positions, line breaks, font scale hierarchy, and reading order.
Remove every non-text visual element, photograph, icon, chart mark, connector, texture, decoration, shadow, and background scene.
Render all readable text and numbers in high-contrast dark text on a plain white background.
Do not add, rewrite, translate, summarize, correct, or omit any text. Do not generate slide chrome, logo, title bar, footer, or page number.
This image is only an OCR aid; it will never be used as the visible PowerPoint background."""


def output_variants_for_mode(production_mode: str) -> list[str]:
    if production_mode == FULL_IMAGE_MODE:
        return ["full"]
    if production_mode == DUAL_IMAGE_MODE:
        return ["full", "background"]
    if production_mode == TRIPLE_IMAGE_MODE:
        return ["full", "background", "text_reference"]
    raise ValueError(
        f"unsupported production mode: {production_mode}; "
        f"expected one of {', '.join(PRODUCTION_MODES)}"
    )


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


def _relationship_aware_canonical_prompts(
    *,
    script: Path,
    project_path: Path,
    style_lock: Path,
    page_numbers: list[int],
) -> dict[int, str]:
    """Compile strict prompts through the same page-intent path used for approval."""

    from cyberppt.script_quality_contract import parse_script_markdown
    from scripts.dual_image_overlay.imagegen_handoff import (
        _page_missions,
        _page_visual_contexts,
        _page_visual_intent_overrides,
        build_page_prompt,
    )

    document = parse_script_markdown(script.read_text(encoding="utf-8"))
    pages = {
        int(page.page_id[1:]): page
        for page in document.pages
        if page.page_type == "content"
    }
    missions = _page_missions(project_path)
    contexts = _page_visual_contexts(project_path)
    overrides = _page_visual_intent_overrides(project_path)
    return {
        page_number: build_page_prompt(
            pages[page_number],
            style_lock,
            page_mission=missions.get(pages[page_number].page_id, ""),
            visual_context=contexts.get(pages[page_number].page_id),
            visual_intent_override=overrides.get(pages[page_number].page_id),
        )
        for page_number in page_numbers
        if page_number in pages
    }


def build_manifest(
    *,
    script: Path,
    pages_raw: str,
    output_dir: Path,
    project_path: Path | None,
    style_lock: Path | None,
    force_pending: bool = False,
    require_approved_prompts: bool = False,
    production_mode: str = FULL_IMAGE_MODE,
) -> tuple[dict[str, Any], Path, Path, list[int]]:
    output_variants = output_variants_for_mode(production_mode)
    source_pages = parse_page_blocks(script)
    page_numbers = parse_pages(pages_raw, set(source_pages))
    from cyberppt.script_quality_contract import parse_script_markdown

    script_pages = {
        int(page.page_id[1:]): page
        for page in parse_script_markdown(script.read_text(encoding="utf-8")).pages
    }
    role_aliases = {
        "cover": "cover",
        "contents": "agenda",
        "agenda": "agenda",
        "chapter": "section",
        "section": "section",
        "closing": "ending",
        "ending": "ending",
    }
    page_roles = {
        number: role_aliases.get(
            script_pages.get(number).page_type if number in script_pages else "",
            "content",
        )
        for number in page_numbers
    }
    content_page_numbers = [
        number for number in page_numbers if page_roles[number] == "content"
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    compiled_script = _compiled_script_path(output_dir, script, page_numbers)
    approved_prompts: dict[int, tuple[str, Path]] = {}
    relationship_aware_prompts: dict[int, str] = {}
    if require_approved_prompts:
        if project_path is None:
            raise ValueError("per-slide prompt approval requires --project-path")
        if style_lock is None:
            raise ValueError("per-slide prompt approval requires a visual style lock")
        relationship_aware_prompts = _relationship_aware_canonical_prompts(
            script=script,
            project_path=project_path,
            style_lock=style_lock,
            page_numbers=content_page_numbers,
        )
        for page_number in content_page_numbers:
            approved_path = assert_approved_final_script(project_path, page_number, "imagegen")
            approved_prompts[page_number] = (
                approved_path.read_text(encoding="utf-8-sig"),
                approved_path,
            )
        compiled = "\n\n".join(
            approved_prompts[page_number][0].strip()
            for page_number in content_page_numbers
        ) + "\n"
    else:
        compiled = compile_pages(script, content_page_numbers, style_lock_path=style_lock)
    compiled_script.write_text(compiled, encoding="utf-8")

    # Compiled prompts no longer carry "## 第N页：" headers; use source page
    # metadata + per-page render_prompt for pair entries.
    pairs: list[dict[str, Any]] = []
    for page_number in content_page_numbers:
        page = source_pages[page_number]
        prompt = render_prompt(page, style_lock_path=style_lock)
        approval_path: Path | None = None
        if page_number in approved_prompts:
            approved_prompt, approval_path = approved_prompts[page_number]
            canonical_prompt = relationship_aware_prompts.get(page_number, prompt).strip()
            if approved_prompt.strip() != canonical_prompt:
                raise ValueError(
                    f"approved ImageGen prompt is stale for page {page_number}; "
                    "restage and reapprove the canonical prompt before manifest creation"
                )
            prompt = approved_prompt
        prompt = _full_prompt_for_variants(prompt, output_variants)
        stem = _page_stem(page_number, page.title)
        full_path = output_dir / f"{stem}_full.png"
        full = {
            "filename": full_path.name,
            "path": str(full_path),
            "prompt": prompt,
            "generation_method": FULL_GENERATION_METHOD,
            "operation": "generate",
            "output_role": "full_textual_visual_reference",
            "aspect_ratio": "content-region",
            "image_size": "2x-content-region",
            "canvas": f"{GENERATION_SIZE['width']}x{GENERATION_SIZE['height']}",
        }
        _mark_status(full, force_pending=force_pending)
        variants: dict[str, dict[str, Any]] = {"full": full}
        if "background" in output_variants:
            background_path = output_dir / f"{stem}_background.png"
            background = {
                "filename": background_path.name,
                "path": str(background_path),
                "prompt": _background_prompt(page_number),
                "generation_method": BACKGROUND_GENERATION_METHOD,
                "operation": "edit",
                "input_variant": "full",
                "depends_on_full_path": str(full_path),
                "requires_input_image": True,
                "output_role": "no_text_visible_background",
                "aspect_ratio": "content-region",
                "image_size": "2x-content-region",
                "canvas": f"{GENERATION_SIZE['width']}x{GENERATION_SIZE['height']}",
            }
            _mark_status(background, force_pending=force_pending)
            variants["background"] = background
        if "text_reference" in output_variants:
            text_reference_path = output_dir / f"{stem}_text_reference.png"
            text_reference = {
                "filename": text_reference_path.name,
                "path": str(text_reference_path),
                "prompt": _text_reference_prompt(page_number),
                "generation_method": TEXT_REFERENCE_GENERATION_METHOD,
                "operation": "edit",
                "input_variant": "full",
                "depends_on_full_path": str(full_path),
                "requires_input_image": True,
                "output_role": "ocr_only_text_reference",
                "visible_in_ppt": False,
                "aspect_ratio": "content-region",
                "image_size": "2x-content-region",
                "canvas": f"{GENERATION_SIZE['width']}x{GENERATION_SIZE['height']}",
            }
            _mark_status(text_reference, force_pending=force_pending)
            variants["text_reference"] = text_reference
        pairs.append(
            {
                "page_number": page_number,
                "page_code": f"P{page_number:02d}",
                "title": page.title,
                "page_script": prompt,
                **({"prompt_approval": str(approval_path.resolve())} if approval_path else {}),
                **variants,
            }
        )

    manifest = {
        "mode": (
            "cyberppt-full-image-only"
            if production_mode == FULL_IMAGE_MODE
            else "cyberppt-dual-image-pair"
        ),
        "production_mode": production_mode,
        "requested_pages": page_numbers,
        "content_page_numbers": content_page_numbers,
        "skipped_pages": [
            {
                "page_number": number,
                "page_role": page_roles[number],
                "render_mode": "template",
                "status": "skipped",
                "reason": "template_only_page",
            }
            for number in page_numbers
            if page_roles[number] != "content"
        ],
        "output_variants": output_variants,
        "generation_contract": {
            "mode": "full-image-only" if production_mode == FULL_IMAGE_MODE else production_mode,
            "owner": "CyberPPT",
            "slide_canvas": CANVAS,
            "content_region": CONTENT_REGION,
            "generation_size": GENERATION_SIZE,
            "rule": (
                "Generate full content-area images only; PPT title, subtitle and enterprise chrome are handled by template/export code."
                if production_mode == FULL_IMAGE_MODE
                else "Generate a full reference plus a derived no-text background; rebuild editable text through OCR/semantic overlay."
            ),
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
    contract_errors: list[str] = []
    production_mode = str(manifest.get("production_mode") or FULL_IMAGE_MODE)
    output_variants = output_variants_for_mode(production_mode)
    for pair in manifest.get("pairs", []):
        page_number = pair.get("page_number", "?")
        full_item = pair.get("full") or {}
        full_path_value = str(full_item.get("path", ""))
        if full_item.get("generation_method") != FULL_GENERATION_METHOD:
            contract_errors.append(
                f"page {page_number} full.generation_method must be {FULL_GENERATION_METHOD}"
            )
        if "background" in output_variants:
            background_item = pair.get("background") or {}
            if background_item.get("generation_method") != BACKGROUND_GENERATION_METHOD:
                contract_errors.append(
                    f"page {page_number} background.generation_method must be {BACKGROUND_GENERATION_METHOD}"
                )
            if background_item.get("operation") != "edit":
                contract_errors.append(f"page {page_number} background.operation must be edit")
            if str(background_item.get("depends_on_full_path", "")) != full_path_value:
                contract_errors.append(f"page {page_number} background must depend on full.path")
        if "text_reference" in output_variants:
            text_item = pair.get("text_reference") or {}
            if text_item.get("visible_in_ppt") is not False:
                contract_errors.append(f"page {page_number} text_reference.visible_in_ppt must be false")
            if str(text_item.get("depends_on_full_path", "")) != full_path_value:
                contract_errors.append(f"page {page_number} text_reference must depend on full.path")
        for variant in output_variants:
            item = pair.get(variant) or {}
            path = Path(str(item.get("path", "")))
            if not path.is_file() or path.stat().st_size <= 0:
                missing.append(str(path))
    if contract_errors:
        raise ValueError(
            "CyberPPT image contract violation.\n"
            + "\n".join(contract_errors)
        )
    if missing:
        raise FileNotFoundError(
            "CyberPPT image files are not generated yet. Generate the pending manifest variants, "
            "then rerun with --require-images.\nMissing:\n"
            + "\n".join(missing)
        )


def _normalize_ingest_image(path: Path) -> None:
    """Resize a stored full/background image to the project generation canvas."""

    ensure_output_size(path, GENERATION_SIZE_TEXT)


def _copy_existing_images(existing_manifest: Path, output_dir: Path, *, force: bool = False) -> None:
    data = json.loads(existing_manifest.read_text(encoding="utf-8"))
    variants = output_variants_for_mode(str(data.get("production_mode") or FULL_IMAGE_MODE))
    for pair in data.get("pairs", []):
        page_number = int(pair["page_number"])
        title = str(pair.get("title") or f"page_{page_number}")
        stem = _page_stem(page_number, title)
        for variant in variants:
            item = pair.get(variant) or {}
            source = Path(str(item.get("path", ""))).expanduser()
            if not source.is_file():
                continue
            target = output_dir / f"{stem}_{variant}.png"
            if target.exists() and not force:
                continue
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            _normalize_ingest_image(target)


def _find_blueprint_image(blueprint_dir: Path, page_number: int) -> Path | None:
    for pattern in BLUEPRINT_PATTERNS:
        candidate = blueprint_dir / pattern.format(page=page_number)
        if candidate.is_file():
            return candidate
    matches = sorted(blueprint_dir.glob(f"*{page_number:03d}*blueprint*.png"))
    if not matches:
        matches = sorted(blueprint_dir.glob(f"*{page_number}*blueprint*.png"))
    return matches[0] if matches else None


def _copy_full_images_from_blueprints(
    *,
    blueprint_dir: Path,
    output_dir: Path,
    script: Path,
    pages_raw: str,
    force: bool = False,
) -> None:
    source_pages = parse_page_blocks(script)
    page_numbers = parse_pages(pages_raw, set(source_pages))
    for page_number in page_numbers:
        blueprint = _find_blueprint_image(blueprint_dir, page_number)
        if blueprint is None:
            continue
        page = source_pages[page_number]
        target = output_dir / f"{_page_stem(page_number, page.title)}_full.png"
        if target.exists() and not force:
            continue
        output_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(blueprint, target)
        _normalize_ingest_image(target)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create CyberPPT dual-image pair manifests.")
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--pages", default="all")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--project-path", type=Path)
    parser.add_argument("--style-lock", type=Path)
    parser.add_argument("--style-id", type=int, choices=range(1, 11), metavar="1-10")
    parser.add_argument("--style-name")
    parser.add_argument("--production-mode", choices=PRODUCTION_MODES, default=FULL_IMAGE_MODE)
    parser.add_argument("--resume", action="store_true", help="Reuse existing images in output-dir if present.")
    parser.add_argument("--force", action="store_true", help="Mark images pending and overwrite copied cache images.")
    parser.add_argument("--require-generated", action="store_true", help="Fail if full/background images are missing.")
    parser.add_argument("--copy-images-from", type=Path, help="Optional existing page_image_pairs.json to seed image files.")
    parser.add_argument(
        "--promote-blueprints-from",
        type=Path,
        help="Optional approved blueprint image directory; matching blueprint PNGs are copied as full images.",
    )
    args = parser.parse_args(argv)

    if args.copy_images_from:
        _copy_existing_images(args.copy_images_from.resolve(), args.output_dir.resolve(), force=args.force)
    if args.promote_blueprints_from:
        _copy_full_images_from_blueprints(
            blueprint_dir=args.promote_blueprints_from.resolve(),
            output_dir=args.output_dir.resolve(),
            script=args.script.resolve(),
            pages_raw=args.pages,
            force=args.force,
        )

    style_lock = args.style_lock.resolve() if args.style_lock else None
    if style_lock is not None and (args.style_id is not None or args.style_name):
        raise ValueError("--style-lock cannot be combined with --style-id or --style-name")
    if style_lock is None:
        if args.project_path is None:
            raise ValueError("--project-path is required when selecting a default CyberPPT style")
        style_lock = write_project_style_lock(
            project=args.project_path.resolve(),
            style_id=args.style_id,
            style_name=args.style_name,
            source_script=args.script.resolve(),
        )

    manifest, manifest_path, compiled_script, page_numbers = build_manifest(
        script=args.script.resolve(),
        pages_raw=args.pages,
        output_dir=args.output_dir.resolve(),
        project_path=args.project_path.resolve() if args.project_path else None,
        style_lock=style_lock,
        force_pending=bool(args.force and not args.resume),
        production_mode=args.production_mode,
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
