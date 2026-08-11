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
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.dual_image_overlay.deliverable_prompt import (
    _style09_terminal_execution_lock,
    append_composition_guidance,
    compile_pages,
    enforce_style09_terminal_lock,
    parse_page_blocks,
    parse_pages,
    render_prompt,
    source_visual_structure_guidance,
    style_contract,
    visible_deliverable_lines,
)
from scripts.dual_image_overlay.rebuild_engine.codex_oauth_image import ensure_output_size
from scripts.dual_image_overlay.style_library import write_project_style_lock
from scripts.dual_image_overlay.prompt_approval import (
    assert_prompt_fresh,
    build_prompt_approval,
    prompt_sha256,
)
from scripts.dual_image_overlay.build_transaction import (
    atomic_copy,
    atomic_write_json,
    atomic_write_text,
    build_lock,
)
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


def _sha256_text(value: str) -> str:
    return prompt_sha256(value)


def _compiled_script_path(output_dir: Path, source: Path, pages: list[int]) -> Path:
    first = pages[0]
    last = pages[-1]
    return output_dir / f"{source.stem}_cyberppt_deliverable_p{first}_p{last}.md"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_reference_map(project_path: Path | None) -> dict[int, list[dict[str, Any]]]:
    """Load optional per-page ImageGen reference images.

    References are project-owned, hash-bound assets.  They guide composition
    and material only; the approved page prompt remains the content source of
    truth.  Keeping the map in the manifest makes every attachment auditable.
    """

    if project_path is None:
        return {}
    map_path = project_path / "workbench" / "locks" / "imagegen_reference_map.json"
    if not map_path.is_file():
        return {}
    payload = json.loads(map_path.read_text(encoding="utf-8"))
    raw_pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(raw_pages, dict):
        raise ValueError(f"ImageGen reference map pages must be an object: {map_path}")
    result: dict[int, list[dict[str, Any]]] = {}
    for raw_page, raw_items in raw_pages.items():
        try:
            page_number = int(raw_page)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid ImageGen reference page {raw_page!r}: {map_path}") from exc
        if not isinstance(raw_items, list):
            raise ValueError(f"reference map page {page_number} must be a list: {map_path}")
        items: list[dict[str, Any]] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict) or not raw_item.get("path"):
                raise ValueError(f"reference map page {page_number} has an invalid item: {map_path}")
            path = Path(str(raw_item["path"])).expanduser()
            if not path.is_absolute():
                path = (project_path / path).resolve()
            else:
                path = path.resolve()
            if not path.is_file():
                raise FileNotFoundError(f"ImageGen reference image not found: {path}")
            expected = str(raw_item.get("sha256") or "").lower()
            actual = _sha256_file(path)
            if expected and expected != actual:
                raise ValueError(
                    f"ImageGen reference hash mismatch: {path}; expected {expected}, got {actual}"
                )
            items.append(
                {
                    "path": str(path),
                    "role": str(raw_item.get("role") or "style_and_composition_reference"),
                    "sha256": actual,
                }
            )
        result[page_number] = items
    return result


FULL_DUAL_IMAGE_CONTAINER_CONTRACT = """【双图文字可分离规则｜不上屏】
使用一幅完整的生成式视觉构图组织页面表达。通过具有设计感的图形形态、色带、路径、箭头、空间层次、聚合、分支、支撑、包裹与状态变化，直观呈现模块之间的主线和逻辑关系。
图形构图是主要组织层，不受插图矩形容器限制；可根据技术方案或业务关系选择架构图、流程图、分层图、关系场或其他有设计感的表达。
生成页面前先区分主体、支撑、输入、输出、分支、汇聚、闭环、层级、对比、因果与结论等关系角色，再决定视觉主线；不得仅按文本顺序机械排列或连接。
页面级标题、正文、编号、关键数字、外围标签和结论嵌入视觉主线，位于稳定、低纹理、对比充分的文字承载面上；图形可以环绕、承托、连接和引导文字，但不得穿过字形或侵入正文安全区。
可使用少量实景、近实景或物件型语义图作为辅助点缀。只有这类独立语义插图需要完整位于边界清晰的矩形容器内；矩形仅指图片区域，不是正文卡片、页面分栏或通用排版单元。
小型语义图默认不生成可读文字，以场景、物体、动作和状态点题；界面截图、图表或离开标签便无法理解的专业插图才允许少量必要的图内文字，并与容器内图形共同保留。
不得拆成半屏文字加半屏图片；不得把可靠脚本复制成图内文字墙。视觉载体的数量、位置、尺寸和形态由本页逻辑决定。"""


def _full_prompt_for_variants(prompt: str, output_variants: list[str]) -> str:
    """Keep the approved script prompt unchanged for every output mode.

    The script compiler is the single source of prompt truth.  Dual-image
    background generation uses its own operation prompt, but must not mutate
    or append a second generic contract to the approved full-image prompt.
    """

    return prompt


def _background_prompt(page_number: int) -> str:
    return f"""请将输入图作为唯一视觉母版进行 image-to-image 编辑，只生成第【{page_number}】页正文内容区的无文字背景图。

【核心任务】
参照输入的 full 正文内容区图片，生成同一内容区、同一构图、同一图形关系的无文字底稿。不要重新文生图，不要更换构图，不要生成同主题新图。输出图必须可以直接作为 PPT 正文区底图，与 full 图形成同版式的图片版页面组合。

必须严格保留：输入图的画布比例、整体版式、空间结构、配色、材质、图形关系、流程线、关系箭头、容器、底座、语义小图、背景装饰、阴影、留白、浅色文字承载面、模块标签条和所有非文字图形元素的位置与尺度。

插图容器识别规则：先识别边界清晰的矩形或圆形插图容器。照片、界面、图表、教材、文件或设备画面均属于插图；插图容器内部的全部像素和文字视为一个不可拆分的整体。

必须保留：所有插图容器及其内部的全部像素和文字，包括界面标签、图表刻度、教材封面、文件内容和设备铭牌。不得删除、翻译、纠正、重写或重新生成插图容器内部的文字。

必须删除：插图容器之外的页面级标题、正文、编号、标签、结论文字、页码、水印、伪文字、乱码和文字残影。删除后相应区域应恢复为完整的纯色/浅色/低纹理承载面或原本的底层材质。

禁止：在插图容器之外新增任何文字、数字、乱码、符号或水印；禁止生成完整 PPT 页面、页眉、页脚、中电联公共元素；禁止改变图形语义关系；禁止出现模糊补丁、涂抹块、局部重绘错位、重复元素或新装饰。

不得在输入图不存在关系型图形的位置新增流程图、架构图、拓扑图、节点连线图、模块框、图标卡片、连接线、方向箭头、分支、回路或层级框线。
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


def _compact_blueprint_prompt(
    *,
    page_number: int,
    handoff_page: dict[str, Any],
    visual_prompt: str,
    style_lock: Path | None,
) -> str:
    parts = [
            f"【页面编码】P{page_number:02d}",
            "【正文画布合同】\n2048×1024（2:1）正文内容区。不得绘制标题、副标题、Logo、页码、页脚或模板外框。",
            (
                "【构图优先级｜不上屏】\n页面视觉设计模块对空间关系和主视觉载体具有最高优先级；"
                "正式风格锁只控制色彩、材质、字体气质和表面语言，不得把页面改造成卡片矩阵、"
                "左侧分类栏、编号 chips、图标节点或一条文字配一个图标。必须形成一个连续、"
                "具有真实行业对象和空间关系的主视觉场景，正文作为对象标签、路径节点或场景内工作面板附着其中。"
            ),
            "【语义背景｜不上屏】\n" + str(handoff_page.get("core_message") or "").strip(),
            "【严格上屏文字】\n" + str(handoff_page.get("onscreen_text") or "").strip(),
            "【视觉设计｜不上屏】\n" + visual_prompt.strip(),
            "【正式风格锁｜不上屏】\n" + style_contract(style_lock).strip(),
            "【生成约束】\n只渲染“严格上屏文字”中的文字；语义背景、字段名、指令、证据编号和调试信息均不得上屏。",
        ]
    terminal_execution_lock = _style09_terminal_execution_lock(style_lock)
    if terminal_execution_lock:
        parts.append("【风格09最终执行锁｜最高优先级】\n" + terminal_execution_lock)
    return "\n\n".join(parts)


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
        compile_page_prompt,
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
    try:
        from cyberppt.stage02_handoff import handoff_page_map, load_stage02_handoff

        handoff = load_stage02_handoff(project_path)
    except (FileNotFoundError, ValueError):
        handoff = None
    handoff_pages = handoff_page_map(handoff) if handoff else {}
    # The approved prompt owns content and the selected style.  The separately
    # audited visual-structure module is appended only after freshness has
    # been checked, so it must not be compiled into the approval baseline too.
    canonical: dict[int, str] = {}
    prior_decisions: list[Any] = []
    prior_semantic_carriers: list[str] = []
    for page_number in page_numbers:
        page = pages.get(page_number)
        if page is None:
            continue
        handoff_page = handoff_pages.get(page_number) or {}
        handoff_visual = handoff_page.get("visual_structure") or {}
        page_mission = str(handoff_page.get("page_mission") or missions.get(page.page_id, ""))
        visual_context = dict(contexts.get(page.page_id) or {})
        if isinstance(handoff_visual, dict):
            if handoff_visual.get("intent_type"):
                visual_context["visual_intent_type"] = str(handoff_visual["intent_type"])
            if handoff_visual.get("dominant_carrier"):
                visual_context["visual_carrier"] = str(handoff_visual["dominant_carrier"])
        compiled = compile_page_prompt(
            page,
            style_lock,
            page_mission=page_mission,
            visual_context=visual_context,
            visual_intent_override=overrides.get(page.page_id),
            prior_decisions=tuple(prior_decisions),
            prior_semantic_carriers=tuple(prior_semantic_carriers),
            visual_structure_mode="off",
        )
        canonical[page_number] = compiled.prompt
        if compiled.presentation is not None:
            prior_decisions.append(compiled.presentation)
        if compiled.semantic_structure is not None:
            carrier = compiled.semantic_structure.get("visual_carrier") or {}
            if isinstance(carrier, dict) and carrier.get("selected"):
                prior_semantic_carriers.append(str(carrier["selected"]))
    return canonical


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
    prompt_enrich: str = "off",
    require_send_approval: bool = False,
    enforce_prompt_freshness: bool = False,
    compact_blueprint: bool = False,
) -> tuple[dict[str, Any], Path, Path, list[int]]:
    output_variants = output_variants_for_mode(production_mode)
    source_pages = parse_page_blocks(script)
    page_numbers = parse_pages(pages_raw, set(source_pages))
    from cyberppt.script_quality_contract import parse_script_markdown
    from cyberppt.visual_prompt_consumer import (
        append_visual_prompt_module,
        load_visual_prompt_module,
        visual_module_metadata,
    )
    from scripts.dual_image_overlay.prompt_send_enrich import (
        enrich_result_as_dict,
        resolve_send_prompt,
    )
    from scripts.dual_image_overlay.imagegen_handoff import select_image_locked_text

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
    stage02_handoff: dict[str, Any] | None = None
    stage02_handoff_path: Path | None = None
    handoff_pages: dict[int, dict[str, Any]] = {}
    if project_path is not None:
        from cyberppt.stage02_handoff import HANDOFF_JSON, handoff_page_map, load_stage02_handoff

        stage02_handoff = load_stage02_handoff(project_path)
        if stage02_handoff is not None:
            stage02_handoff_path = project_path / HANDOFF_JSON
            handoff_pages = handoff_page_map(stage02_handoff)
            role_aliases_from_handoff = {
                "cover": "cover",
                "agenda": "agenda",
                "section": "section",
                "content": "content",
                "ending": "ending",
            }
            for number in page_numbers:
                handoff_page = handoff_pages.get(number)
                if handoff_page is None:
                    raise ValueError(f"Stage 02 handoff is missing requested page {number}")
                page_roles[number] = role_aliases_from_handoff[str(handoff_page["render_role"])]
    content_page_numbers = [
        number for number in page_numbers if page_roles[number] == "content"
    ]
    # Style 09 is assembled exclusively from the source-authored style lock.
    # Do not append the page visual-structure handoff or a synthetic adapter:
    # that handoff contains internal refs, text bindings and carrier metadata,
    # not reusable style rules.
    style09_source_contract = bool(_style09_terminal_execution_lock(style_lock))
    effective_compact_blueprint = bool(
        compact_blueprint and handoff_pages and not style09_source_contract
    )
    reference_map = _load_reference_map(project_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    compiled_script = _compiled_script_path(output_dir, script, page_numbers)
    approved_prompts: dict[int, tuple[str, Path]] = {}
    relationship_aware_prompts: dict[int, str] = {}
    enrich_mode = (prompt_enrich or "off").strip().lower()
    if require_approved_prompts:
        if project_path is None:
            raise ValueError("per-slide prompt approval requires --project-path")
        if style_lock is None:
            raise ValueError("per-slide prompt approval requires a visual style lock")
        if effective_compact_blueprint:
            relationship_aware_prompts = {}
            for page_number in content_page_numbers:
                module = load_visual_prompt_module(project_path, page_number)
                if module is None:
                    raise ValueError(
                        f"compact production prompt requires visual design module for page {page_number}"
                    )
                relationship_aware_prompts[page_number] = _compact_blueprint_prompt(
                    page_number=page_number,
                    handoff_page=handoff_pages[page_number],
                    visual_prompt=module.prompt_text,
                    style_lock=style_lock,
                )
        else:
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
        # Keep explicit page delimiters in the compiled deliverable so the
        # prompt file remains auditable and can be traced back to its page.
        compiled = "\n\n".join(
            f"## p{page_number:02d}\n\n{approved_prompts[page_number][0].strip()}"
            for page_number in content_page_numbers
        ) + "\n"
    else:
        compiled = compile_pages(
            script,
            content_page_numbers,
            style_lock_path=style_lock,
            composition_guidance_by_page={
                number: source_visual_structure_guidance(
                    str(script_pages[number].visual_structure or ""),
                    "\n".join(visible_deliverable_lines(source_pages[number])),
                )
                for number in content_page_numbers
                if number in script_pages
            },
        )
    with build_lock(output_dir, f"pair-manifest-{compiled_script.stem}"):
        atomic_write_text(compiled_script, compiled)

    # Compiled prompts no longer carry "## 第N页：" headers; use source page
    # metadata + per-page render_prompt for pair entries.
    pairs: list[dict[str, Any]] = []
    enrich_ledger: list[dict[str, Any]] = []
    for page_number in content_page_numbers:
        page = source_pages[page_number]
        reference_images = reference_map.get(page_number, [])
        prompt = render_prompt(
            page,
            style_lock_path=style_lock,
            composition_guidance=source_visual_structure_guidance(
                str(
                    script_pages.get(page_number).visual_structure
                    if script_pages.get(page_number) is not None
                    else ""
                ),
                "\n".join(visible_deliverable_lines(page)),
            ),
        )
        visual_module = (
            load_visual_prompt_module(project_path, page_number)
            if project_path is not None
            else None
        )
        if effective_compact_blueprint:
            handoff_page = handoff_pages.get(page_number) or {}
            if not handoff_page:
                raise ValueError(
                    f"compact blueprint requires Stage 02 handoff page {page_number}"
                )
            if visual_module is None:
                raise ValueError(
                    f"compact blueprint requires visual design module for page {page_number}"
                )
            prompt = _compact_blueprint_prompt(
                page_number=page_number,
                handoff_page=handoff_page,
                visual_prompt=visual_module.prompt_text,
                style_lock=style_lock,
            )
        approval_path: Path | None = None
        approval_meta: dict[str, Any] | None = None
        if page_number in approved_prompts:
            approved_prompt, approval_path = approved_prompts[page_number]
            canonical_prompt = relationship_aware_prompts.get(page_number, prompt).strip()
            approval = build_prompt_approval(
                approved_path=approval_path,
                approved_prompt=approved_prompt,
                canonical_prompt=canonical_prompt,
                consumed_prompt=approved_prompt,
            )
            approval_meta = approval.metadata()
            if enforce_prompt_freshness:
                assert_prompt_fresh(approval, page_number=page_number)
            # Style 09 is a live source-authored contract. Reassembly after a
            # source style edit must consume the freshly compiled canonical
            # prompt; a historical approval remains audit evidence only.
            if style09_source_contract:
                prompt = canonical_prompt
                approval_meta["consumed_from"] = "canonical_style09_refresh"
            else:
                prompt = approved_prompt
        send_final: Path | None = None
        if project_path is not None and enrich_mode == "send":
            try:
                send_final = assert_approved_final_script(
                    project_path, page_number, "imagegen-send"
                )
            except (FileNotFoundError, PermissionError):
                if require_send_approval:
                    raise
                send_final = None
        enrich = resolve_send_prompt(
            approved_prompt=prompt,
            mode=enrich_mode,
            send_final_path=send_final,
            require_send=require_send_approval and enrich_mode == "send",
        )
        prompt = enrich.prompt
        source_visual_structure = source_visual_structure_guidance(
            str(
                script_pages.get(page_number).visual_structure
                if script_pages.get(page_number) is not None
                else ""
            ),
            "\n".join(visible_deliverable_lines(page)),
        )
        prompt = append_composition_guidance(prompt, source_visual_structure)
        if visual_module is not None and not effective_compact_blueprint:
            if not style09_source_contract and "【视觉设计｜不上屏】" not in prompt:
                prompt = append_visual_prompt_module(prompt, visual_module)
        # The visual-structure handoff is page-specific composition guidance.
        # Reassert the source-authored Style 09 lock after that handoff so a
        # matrix/swim-lane recipe cannot turn the whole page into a generic
        # infographic or override the shared surface language.
        prompt = enforce_style09_terminal_lock(prompt, style_lock)
        enrich_ledger.append({"page_number": page_number, **enrich_result_as_dict(enrich)})
        prompt = _full_prompt_for_variants(prompt, output_variants)
        if approval_meta is not None:
            approval_meta["consumed_prompt_sha256"] = _sha256_text(prompt)
            approval_meta.setdefault("consumed_from", "approved_prompt")
        visual_handoff_metadata = visual_module_metadata(
            None if style09_source_contract else visual_module
        )
        stem = _page_stem(page_number, page.title)
        prompt_file = output_dir / "prompts" / f"p{page_number:02d}.txt"
        atomic_write_text(prompt_file, prompt.rstrip() + "\n")
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
            "prompt_enrich": enrich_result_as_dict(enrich),
            "visual_structure_handoff": visual_handoff_metadata,
            "prompt_provenance": {
                **(approval_meta or {}),
                **({
                    "consumed_prompt_sha256": _sha256_text(prompt),
                    "consumed_from": "script_compiler",
                } if approval_meta is None else {}),
            },
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
        required_image_text = [
            line
            for line in select_image_locked_text(script_pages[page_number]).splitlines()
            if line.strip()
        ]
        allowed_image_text = "\n".join(
            value
            for value in (script_pages[page_number].onscreen_text, *required_image_text)
            if str(value).strip()
        )
        pairs.append(
            {
                "page_number": page_number,
                "page_code": f"P{page_number:02d}",
                "title": page.title,
                "page_script": prompt,
                "image_text_truth": {
                    "script_text": allowed_image_text,
                    "scope": "typo_and_gibberish_only",
                },
                "prompt_file": str(prompt_file),
                **({"reference_images": reference_images} if reference_images else {}),
                "visual_structure_handoff": visual_handoff_metadata,
                **(
                    {
                        "stage02_handoff": str(stage02_handoff_path.resolve()),
                    }
                    if stage02_handoff_path is not None
                    else {}
                ),
                **({"prompt_approval": str(approval_path.resolve())} if approval_path else {}),
                **({"prompt_provenance": approval_meta} if approval_meta else {}),
                **variants,
            }
        )

    # The compiled deliverable must be the exact prompt collection consumed
    # by the image manifest, including visual-structure handoff and send-time
    # deterministic enrichment.  Do not leave a pre-handoff audit artifact.
    compiled = "\n\n".join(
        f"## p{int(pair['page_number']):02d}\n\n{str((pair.get('full') or {}).get('prompt', '')).strip()}"
        for pair in pairs
    ) + ("\n" if pairs else "")
    with build_lock(output_dir, f"pair-manifest-{compiled_script.stem}"):
        atomic_write_text(compiled_script, compiled)

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
        "text_audit_contract": {
            "required_before_enhancement": True,
            "scope": "typo_and_gibberish_only",
            "max_generation_attempts": 3,
            "failure_action": "regenerate_image",
        },
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
        "stage02_handoff": (
            {
                "path": str(stage02_handoff_path.resolve()),
                "schema": stage02_handoff.get("schema"),
            }
            if stage02_handoff_path is not None and stage02_handoff is not None
            else None
        ),
        "output_dir": str(output_dir.resolve()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt_contract": {
            "approved_prompt_is_source": bool(require_approved_prompts),
            "freshness_enforced": bool(require_approved_prompts and enforce_prompt_freshness),
            "canonical_prompt_is_diagnostic_only": bool(require_approved_prompts),
            "compact_blueprint": effective_compact_blueprint,
        },
        "prompt_enrich": {
            "mode": enrich_mode,
            "require_send_approval": require_send_approval,
            "pages": enrich_ledger,
        },
        "pairs": pairs,
    }
    manifest_path = output_dir / "page_image_pairs.json"
    with build_lock(output_dir, f"pair-manifest-{manifest_path.stem}"):
        atomic_write_json(manifest_path, manifest)
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
        provenance = full_item.get("prompt_provenance") or {}
        prompt_contract = manifest.get("prompt_contract", {})
        if prompt_contract.get("approved_prompt_is_source"):
            if prompt_contract.get("freshness_enforced") and provenance.get("status") == "stale":
                contract_errors.append(f"page {page_number} approved prompt is stale")
        if full_item.get("generation_method") != FULL_GENERATION_METHOD:
            contract_errors.append(
                f"page {page_number} full.generation_method must be {FULL_GENERATION_METHOD}"
            )
        if (manifest.get("text_audit_contract") or {}).get("required_before_enhancement"):
            text_audit = full_item.get("text_audit") or {}
            if text_audit.get("valid") is not True:
                contract_errors.append(
                    f"page {page_number} full image has no passed pre-enhancement text audit"
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
            atomic_copy(source, target)
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
        atomic_copy(blueprint, target)
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
    parser.add_argument(
        "--prompt-enrich",
        choices=("off", "deterministic", "send"),
        default="off",
        help="Send-time prompt enrichment mode (default: off; approved prompt is consumed verbatim).",
    )
    parser.add_argument(
        "--require-send-approval",
        action="store_true",
        help="With --prompt-enrich send, require approved imagegen-send finals.",
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
        prompt_enrich=args.prompt_enrich,
        require_send_approval=args.require_send_approval,
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
