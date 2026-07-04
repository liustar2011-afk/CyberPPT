#!/usr/bin/env python3
"""
PPT Master - Page Image Pair Batch

Build host-native image generation tasks for page-level PPT images: one full
text-bearing slide image and one clean no-text background image per page.

Usage:
    python3 scripts/page_image_pair_batch.py run --script script-imagegen-compact.md --pages 1-5 --project-name demo
    python3 scripts/page_image_pair_batch.py plan --script script-imagegen-compact.md --pages 11 -o output
    python3 scripts/page_image_pair_batch.py verify output/page_image_pairs.json
    python3 scripts/page_image_pair_batch.py export-pptx output/page_image_pairs.json -o exports

Examples:
    python3 scripts/page_image_pair_batch.py run --script script-imagegen-compact.md --pages 1-5 --project-name script_imagegen_demo
    python3 scripts/page_image_pair_batch.py plan --script script-imagegen-compact.md --pages 8-13 -o projects/demo/images
    python3 scripts/page_image_pair_batch.py verify projects/demo/images/page_image_pairs.json
    python3 scripts/page_image_pair_batch.py export-pptx projects/demo/images/page_image_pairs.json -o projects/demo/exports

Dependencies:
    Pillow is used for image metadata checks. PPTX export is handled by
    template_image_ppt_export.py.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from codex_oauth_image import run_codex_image, run_codex_multi_image_once
from image_prompt_styles import DEFAULT_STYLE_NAME, load_image_style, style_name, style_prompt_block
from project_manager import ProjectManager, sanitize_name
from project_utils import normalize_canvas_format
import template_image_ppt_export as template_image_flow


STATUS_PENDING = "Pending"
STATUS_GENERATED = "Generated"
STATUS_NEEDS_MANUAL = "Needs-Manual"
DEFAULT_ASPECT_RATIO = "content-region"
DEFAULT_IMAGE_SIZE = "2x-content-region"
DRAFT_IMAGE_SIZE = "1x-content-region"


def _default_content_contract() -> dict:
    rules = template_image_flow.load_brand_rules()
    brand_body_region = template_image_flow.scale_region(
        rules["content_regions"]["body_pages"],
        template_image_flow.CANVAS_SIZE,
    )
    body_region = template_image_flow.inset_content_region(brand_body_region)
    generation_size = template_image_flow.generation_size_for_region(body_region)
    return {
        "slide_canvas": {
            "width": template_image_flow.CANVAS_SIZE[0],
            "height": template_image_flow.CANVAS_SIZE[1],
        },
        "brand_body_region": brand_body_region,
        "content_region": body_region,
        "generation_size": generation_size,
    }


DEFAULT_CONTENT_CONTRACT = _default_content_contract()
DEFAULT_GENERATION_SIZE = DEFAULT_CONTENT_CONTRACT["generation_size"]
DEFAULT_TEMPLATE_CONTENT_REGION = DEFAULT_CONTENT_CONTRACT["content_region"]
DEFAULT_CANVAS = f"{DEFAULT_GENERATION_SIZE['width']}x{DEFAULT_GENERATION_SIZE['height']}"
DRAFT_CANVAS = (
    f"{template_image_flow.round_up_16(DEFAULT_TEMPLATE_CONTENT_REGION['width'])}x"
    f"{template_image_flow.round_up_16(DEFAULT_TEMPLATE_CONTENT_REGION['height'])}"
)

PAGE_HEADING_RE = re.compile(r"^##\s*第(?P<num>\d+)页[:：](?P<title>.+?)\s*$", re.M)

QUALITY_RULES = [
    {
        "id": "visible_text_locked",
        "level": "hard_fail",
        "check": "Full image visible text comes only from the page's 【内容锁定】 section.",
    },
    {
        "id": "semantic_graph_first",
        "level": "hard_fail",
        "check": "Full image expresses the page's core relation through a path, hierarchy, mapping, convergence, or other clear business graph; it is not only a card, icon, or table pile.",
    },
    {
        "id": "text_graph_separation",
        "level": "hard_fail",
        "check": "Text sits on clean carriers; lines, arrows, borders, shadows, textures, and decorative images do not pass under or through text.",
    },
    {
        "id": "ppt_recognizable_source_image",
        "level": "hard_fail",
        "check": "Full image is a PPT-recognizable source image with orthogonal layout, clear boundaries, closed contours, and separable modules; it is not poster, illustration, web hero, or complex visual-composite output.",
    },
    {
        "id": "orthogonal_separable_layout",
        "level": "hard_fail",
        "check": "Containers, dividers, arrows, decoration blocks, semantic illustration carriers, and text carriers are cleanly separated and can be cropped or redrawn independently.",
    },
    {
        "id": "semantic_decoration",
        "level": "review",
        "check": "Semantic mini-illustrations are few, content-related, low-saturation, light, and placed at module edges, title-side positions, or background layer.",
    },
    {
        "id": "no_decoration_text",
        "level": "hard_fail",
        "check": "Decorative images contain no readable text, numbers, pseudo-text, watermark, or logo-like noise.",
    },
    {
        "id": "background_text_removed",
        "level": "hard_fail",
        "check": "Background image removes all visible text while preserving non-text structure, semantic mini-illustrations, carriers, arrows, and layout.",
    },
    {
        "id": "pair_alignment",
        "level": "hard_fail",
        "check": "Full and background images have the same dimensions; non-text structure alignment is visually close.",
    },
    {
        "id": "pptx_traceability",
        "level": "hard_fail",
        "check": "Export keeps PPTX and manifest JSON artifacts.",
    },
]

FULL_PROMPT_TEMPLATE = """请严格遵从下方页面生成要求，仅生成脚本中指定的第【{page_number}】页正文内容区 full 图。
【硬性要求】
输出画布尺寸为 {generation_width}×{generation_height}。这不是完整 PPT 页面，而是后续放入 PPT 模板正文内容区的图片（模板坐标 x={content_x}, y={content_y}, w={content_width}, h={content_height}）；不要生成完整 PPT 页面。
页面正式、稳健、清爽、高级、有质感；不得出现页码、页面序号、Logo、页脚、红线、蓝色底栏或任何中电联公共元素。
不要画标题、副标题；标题、副标题由 PPT 模板文字层生成。
页面可见文字只能取自下方【正文内容】中的事实、概念、数字和短语；可以压缩、取舍、重组，但不得新增事实、数字、标语、英文伪字或水印。
脚本中的结构分组编号只用于构图理解，不得作为画面文字出现，也不得按原编号抄写。
【版式规范】
正文内容铺满画布内的主要视觉区，四周保留适度安全边距；不要再预留 PPT 页眉、标题栏、页脚或页面外边框。
【PPT可识别源图约束】
在当前输出画布内按“PPT可识别源图”方式绘制，保留现有正文内容区与模板标题层分工；不得按海报、插画、网页首屏或复杂视觉合成图生成。
整体采用白底，正式、清爽、稳健、低干扰。主要元素必须具备清晰边界、规则几何、闭合轮廓、明确留白和可裁切分离特征，像 PPT 中可单独选中、识别、重绘和替换的基础形状。
页面结构采用正交布局，优先使用横向分栏、纵向分层、矩形卡片、圆角矩形容器、细线分隔、规则箭头和浅色条带。模块之间必须保持明显留白，不得粘连、遮挡、交叉、融合或压叠。
框架、容器、分隔线、装饰块、图标承载区、语义图承载区都应边缘完整、干净、连续；可用 1px 细边框、轻微色差或浅色底板与背景区分，不要使用厚重描边。
装饰图形必须矩形化、块状化、条带化、分区化。只允许使用浅色矩形块、圆角矩形片、细线、分隔条、规则点阵、浅色网格、数据条、信息窗、承载底板等 PPT 常见基础形状；装饰只承担分区、强调和轻量美化作用，不得抢占主体信息，不得与背景、文字或业务容器融合。
正文模块标题、标签和说明文字可以放入独立文本承载区；PPT 页标题、副标题仍不得生成。文字区域必须独立、干净、留白充分，不得压在复杂纹理、图片、渐变、光效或装饰图形上。
连接关系使用直线、折线或规则箭头表达，方向以水平、垂直或 45 度为主；不得使用复杂曲线连接、网状连线、大量交叉线、光束连接或难以分离的动态线效。
禁止使用不规则曲线、大面积波浪、流体渐变、云雾、粒子、散点光效、强发光、强阴影、玻璃拟态、复杂纹理、照片蒙版、强透视、强 3D、强反光、羽化边缘、软融边界、复杂背景图和海报式视觉冲击。
{style_prompt}
【内容表达】
在不新增事实、概念和数字的前提下，根据输入脚本提炼核心语义，不逐字搬运。
页面必须表达明确业务关系，优先用路径、层级、承接、汇聚、映射等图形关系表达业务逻辑。
图标只作辅助标识，原则上 0-3 个，最多不超过 3 个；不得用图标阵列替代业务关系表达。
禁止每个流程节点、阶段节点或模块卡片都配一个图标；如果节点较多，必须省略图标，用文字标签、编号、线段、色块和位置关系表达。
流程链条、阶段轴、九环节加工链、五阶段生命周期节点禁止使用图标；这些节点只能使用文字标签、编号圆点、短线、浅色块或轴线刻度表达。
流程关系必须优先用连续路径轴、泳道、分层带、编号节点、线性证据链、闭环轨道或映射矩阵表达，不得退化为“图标 + 卡片 + 箭头”的重复组合。
优先使用 1-4 个与页面内容直接相关的语义中型配图承载区，替代孤立图标堆砌；语义配图仍必须是可裁切、可替换的 PPT 图形模块。
不得只是卡片堆叠、图标堆砌或表格堆叠。
【图文分离】
文字必须水平清晰，置于纯色、浅色或低纹理承载面上。
文字下方不得穿过流程线、箭头、边框、图案纹理、复杂阴影或高光；每个标题、标签、说明文字四周保留足够内边距。
图形语义层与文字层分离，流程线、关系箭头、容器边框、底座、模块形状不得依赖文字笔画构成，不得让文字压住关键连接关系。
【语义小图】
应加入少量语义配图提升识别度，但必须放在独立矩形或圆角矩形承载区内，作为可裁切的 PPT 图形模块，不得作为插画主视觉。
语义配图必须服务页面内容，采用扁平化、低复杂度、几何化、块状化风格；不得使用真实照片质感、复杂三维模型、强透视或高反光效果。
语义配图不得承载文字、数字、伪字或水印，不得侵入文字区和主框架，不得压住正文，不得切断流程线、箭头或层级关系。

【正文内容】
{visible_text}

【构图要求】
{composition_instruction}
"""

BACKGROUND_PROMPT_TEMPLATE = """请将输入图作为唯一视觉母版进行 image-to-image 编辑，只生成第【{page_number}】页正文内容区的无文字背景图。

【核心任务】
参照输入的 full 正文内容区图片，生成同一内容区、同一构图、同一图形关系的无文字底稿。不要重新文生图，不要更换构图，不要生成同主题新图。输出图必须可以直接作为 PPT 正文区底图，与 full 图形成同版式的图片版页面组合。

必须严格保留：输入图的画布比例、整体版式、空间结构、配色、材质、图形关系、流程线、关系箭头、容器、底座、语义小图、背景装饰、阴影、留白、浅色文字承载面、模块标签条和所有非文字图形元素的位置与尺度。

必须删除：所有可读文字、数字、页码、标题、副标题、标签、注释、标点、水印、伪文字、乱码和文字残影。删除后相应区域应恢复为完整的纯色/浅色/低纹理承载面或原本的底层材质。

禁止：新增任何文字、数字、乱码、符号、水印；禁止生成完整 PPT 页面、页眉、页脚、中电联公共元素；禁止改变图形语义关系；禁止出现模糊补丁、涂抹块、局部重绘错位、重复元素或新装饰。

【相似度自检要求】
在输出前必须以输入 full 图为参照进行内部相似度检查：
1. 以“非文字区域结构相似度”为目标，不按整图像素相似度判断，因为文字必须被删除；
2. 非文字区域结构相似度应达到 95% 以上：正文内容区边界、模块标题承载面、主体容器、流程线、箭头、底座、语义小图、背景装饰、阴影、留白、浅色文字承载面和模块标签条的位置、尺寸、角度、颜色关系应高度一致；
3. 关键对象的位置误差应控制在画布宽高的 2% 以内，箭头方向、流程顺序、模块层级和业务关系不得变化；
4. 文字删除完整度应达到 100%：不得保留任何可读字、数字、伪字、乱码、水印、文字残影或局部笔画；
5. 只允许文字层消失，文字承载面必须保留并补齐，不得把承载面、容器边框、连接线或图形语义一起删掉；
6. 如发现背景图像与输入图明显不一致，应自行修正后再输出；
7. 如果内部自检未达到上述标准，必须放弃当前结果并再次生成，直到满足相似度要求后再输出最终图。
"""

BACKGROUND_PAIR_REQUIREMENTS_TEMPLATE = """参照第 1 页 full 正文内容区图，生成同一内容区、同一构图、同一图形关系的无文字底稿。不要重新文生图，不要更换构图，不要生成同主题新图。第 2 页必须可以直接作为 PPT 正文区底图，与第 1 页形成同版式的图片版页面组合。

必须严格保留：第 1 页的画布比例、整体版式、空间结构、配色、材质、图形关系、流程线、关系箭头、容器、底座、语义小图、背景装饰、阴影、留白、浅色文字承载面、模块标签条和所有非文字图形元素的位置与尺度。

必须删除：所有可读文字、数字、页码、标题、副标题、标签、注释、标点、水印、伪文字、乱码和文字残影。删除后相应区域应恢复为完整的纯色/浅色/低纹理承载面或原本的底层材质。

禁止：新增任何文字、数字、乱码、符号、水印；禁止生成完整 PPT 页面、页眉、页脚、中电联公共元素；禁止改变图形语义关系；禁止出现模糊补丁、涂抹块、局部重绘错位、重复元素或新装饰。

自检标准：非文字区域结构相似度应达到 95% 以上；关键对象的位置误差应控制在画布宽高的 2% 以内；文字删除完整度应达到 100%；只允许文字层消失，文字承载面必须保留并补齐，不得把承载面、容器边框、连接线或图形语义一起删掉。"""

PAIR_PROMPT_TEMPLATE = """请严格遵从下方页面生成要求，基于同一页脚本、同一母版、同一构图逻辑，一次性生成两张 PPT 正文内容区图片：

第 1 页：完整正文内容区图，包含必要标签、说明文字和业务关系表达，但不包含 PPT 页标题和副标题；
第 2 页：无文字背景图，与第 1 页使用同一版式、同一结构、同一图形关系、同一材质和同一留白，只删除全部文字、数字、标点、页码、水印、伪字、乱码和文字残影。

【重要输出约束】
1. 必须输出两张独立图片结果，每张都是 {generation_width}×{generation_height} 的 PPT 正文内容区画布，不是完整 PPT 页面；
2. 不要把两页拼在同一张画布里，不要生成左右对照图、上下对照图、联系表、预览图、网格图或缩略图；
3. 第 1 页与第 2 页必须来自同一页面设计，不得一个完整图、一个另起炉灶的背景图；
4. 第 2 页的非文字区域结构相似度应相对于第 1 页达到 95% 以上，关键对象位置误差应控制在画布宽高的 2% 以内；
5. 第 2 页的文字删除完整度应达到 100%，不得保留任何可读字、数字、伪字、乱码、水印、文字残影或局部笔画；
6. 如果第 2 页与第 1 页的非文字结构相似度自检不通过，必须重新生成第 2 页，直到满足要求后再输出；
7. 不得出现页码、页面序号、Logo、页脚、红线、蓝色底栏或任何中电联公共元素。

【第 1 页完整页面的生成要求】
{full_prompt}

【第 2 页无文字背景的生成要求】
{background_requirements}
"""


@dataclass
class PageBlock:
    page_number: int
    title: str
    text: str


def parse_page_blocks(script_path: Path) -> dict[int, PageBlock]:
    """Parse `## 第N页` blocks from a compact image-generation script."""
    text = script_path.read_text(encoding="utf-8")
    matches = list(PAGE_HEADING_RE.finditer(text))
    pages: dict[int, PageBlock] = {}
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        page_number = int(match.group("num"))
        pages[page_number] = PageBlock(
            page_number=page_number,
            title=match.group("title").strip(),
            text=text[start:end].strip(),
        )
    return pages


def parse_page_selection(raw: str, available: set[int]) -> list[int]:
    """Parse page selections such as `11`, `8-13`, or `1,3,5-7`."""
    if not raw.strip() or raw.strip().lower() == "all":
        return sorted(available)
    selected: set[int] = set()
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            left, right = item.split("-", 1)
            start = int(left.strip())
            end = int(right.strip())
            if end < start:
                raise ValueError(f"Invalid page range: {item}")
            selected.update(range(start, end + 1))
        else:
            selected.add(int(item))
    missing = sorted(selected - available)
    if missing:
        raise ValueError(f"Pages not found in script: {missing}")
    return sorted(selected)


def _page_stem(page_number: int, title: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", title).strip("_")
    normalized = normalized[:36] or "page"
    return f"page_{page_number:03d}_{normalized}"


def _rel_or_abs(path: Path) -> str:
    return str(path)


def _canvas_dimensions(canvas: str) -> tuple[int, int]:
    match = re.fullmatch(r"([1-9][0-9]*)[x×]([1-9][0-9]*)", canvas.strip())
    if not match:
        return DEFAULT_GENERATION_SIZE["width"], DEFAULT_GENERATION_SIZE["height"]
    return int(match.group(1)), int(match.group(2))


def _prompt_payload(page: PageBlock) -> dict[str, str]:
    template_page = template_image_flow.PageBlock(
        page_number=page.page_number,
        title=page.title,
        text=page.text,
    )
    content = template_image_flow.extract_content(template_page)
    role = template_image_flow.page_role(template_page)
    visible_text = template_image_flow.image_visible_text(template_page, content, role)
    composition_instruction = template_image_flow.extract_composition_instruction(template_page)
    return {
        "visible_text": visible_text or content.body or page.title,
        "composition_instruction": composition_instruction or "根据正文内容组织清晰的业务关系图。",
    }


def build_pair_manifest(
    script_path: Path,
    page_numbers: list[int],
    pages: dict[int, PageBlock],
    output_dir: Path,
    *,
    aspect_ratio: str,
    image_size: str,
    canvas: str,
    project_path: Path | None = None,
    image_style_name: str | None = None,
    include_background: bool = False,
) -> dict:
    """Build the pair manifest consumed by Codex host-native generation."""
    pairs = []
    generation_width, generation_height = _canvas_dimensions(canvas)
    content_region = DEFAULT_TEMPLATE_CONTENT_REGION
    image_style = load_image_style(image_style_name)
    rendered_style_prompt = style_prompt_block(image_style)
    for page_number in page_numbers:
        page = pages[page_number]
        stem = _page_stem(page.page_number, page.title)
        full_path = output_dir / f"{stem}_full.png"
        prompt_payload = _prompt_payload(page)
        full_prompt = FULL_PROMPT_TEMPLATE.format(
            page_number=page.page_number,
            generation_width=generation_width,
            generation_height=generation_height,
            content_x=content_region["x"],
            content_y=content_region["y"],
            content_width=content_region["width"],
            content_height=content_region["height"],
            style_prompt=rendered_style_prompt,
            visible_text=prompt_payload["visible_text"],
            composition_instruction=prompt_payload["composition_instruction"],
        ).strip()
        pair = {
            "page_number": page.page_number,
            "title": page.title,
            "page_script": page.text,
            "full": {
                "filename": full_path.name,
                "path": _rel_or_abs(full_path),
                "prompt": full_prompt,
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
                "canvas": canvas,
                "status": STATUS_PENDING,
            },
        }
        if include_background:
            background_path = output_dir / f"{stem}_background.png"
            background_prompt = BACKGROUND_PROMPT_TEMPLATE.format(
                page_number=page.page_number,
            ).strip()
            background_requirements = BACKGROUND_PAIR_REQUIREMENTS_TEMPLATE.strip()
            pair_prompt = PAIR_PROMPT_TEMPLATE.format(
                generation_width=generation_width,
                generation_height=generation_height,
                full_prompt=full_prompt,
                background_requirements=background_requirements,
            ).strip()
            pair["pair_generation"] = {
                "full_path": _rel_or_abs(full_path),
                "background_path": _rel_or_abs(background_path),
                "prompt": pair_prompt,
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
                "canvas": canvas,
                "status": STATUS_PENDING,
            }
            pair["background"] = {
                "filename": background_path.name,
                "path": _rel_or_abs(background_path),
                "prompt": background_prompt,
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
                "canvas": canvas,
                "input_image": _rel_or_abs(full_path),
                "depends_on": _rel_or_abs(full_path),
                "status": STATUS_PENDING,
            }
        pairs.append(pair)
    manifest = {
        "mode": "page-image-pair-batch",
        "output_variants": ["full", "background"] if include_background else ["full"],
        "generation_contract": {
            "mode": "template-content-region",
            "slide_canvas": DEFAULT_CONTENT_CONTRACT["slide_canvas"],
            "brand_body_region": DEFAULT_CONTENT_CONTRACT["brand_body_region"],
            "content_region": DEFAULT_TEMPLATE_CONTENT_REGION,
            "generation_size": {
                "width": generation_width,
                "height": generation_height,
            },
            "rule": "Generate content-area images only; PPT title, subtitle and CEC chrome are handled by template/export code.",
        },
        "source_script": _rel_or_abs(script_path),
        "output_dir": _rel_or_abs(output_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "image_style": {
            "name": style_name(image_style),
            "source_path": image_style.get("source_path", ""),
        },
        "quality_rules": QUALITY_RULES,
        "pairs": pairs,
    }
    if project_path is not None:
        manifest["project_path"] = _rel_or_abs(project_path)
    return manifest


def write_json(path: Path, data: dict) -> None:
    """Write pretty UTF-8 JSON."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _image_size(path: Path) -> dict | None:
    try:
        with Image.open(path) as image:
            return {"width": image.width, "height": image.height}
    except Exception:
        return None


def _mark_generated(item: dict, path: Path, *, method: str | None = None) -> None:
    item["status"] = STATUS_GENERATED
    item["generated_at"] = datetime.now(timezone.utc).isoformat()
    item["path"] = str(path)
    size = _image_size(path)
    if size:
        item["actual_size"] = size
    if method:
        item["generation_method"] = method
    item.pop("last_error", None)


def render_tasks_md(manifest: dict) -> str:
    """Render sequential Codex image-generation tasks."""
    lines: list[str] = []
    lines.append("# Page Image Pair Host-Native Tasks")
    lines.append("")
    if "background" in manifest.get("output_variants", ["full"]):
        lines.append("> 双图模式：每页先生成 full，再以上一张 full 作为参考生成 background。")
    else:
        lines.append("> 默认全图模式：每页只生成 full；不生成无文字 background。")
    lines.append("> Python 不调用 API；由 Codex 宿主生图工具完成图片生成并保存到指定路径。")
    lines.append("")
    lines.append(f"- Source script: `{manifest['source_script']}`")
    lines.append(f"- Output dir: `{manifest['output_dir']}`")
    lines.append(f"- Pair count: {len(manifest['pairs'])}")
    lines.append("")
    lines.append("## Quality Rules")
    lines.append("")
    lines.append("| Level | Rule | Check |")
    lines.append("|---|---|---|")
    for rule in manifest.get("quality_rules", QUALITY_RULES):
        lines.append(f"| `{rule['level']}` | `{rule['id']}` | {rule['check']} |")
    lines.append("")
    for pair in manifest["pairs"]:
        page_number = pair["page_number"]
        title = pair["title"]
        full = pair["full"]
        lines.append(f"## 第{page_number}页：{title}")
        lines.append("")
        if pair.get("pair_generation"):
            pair_task = pair["pair_generation"]
            lines.append("### 0. optional coherent two-page task")
            lines.append("")
            lines.append("> 仅当宿主生图工具支持一次提示返回两页独立图片文件时使用本节。")
            lines.append("> 不允许输出左右拼接或上下拼接画布；如果工具只能返回一张图，请改用下面的 1/2 串行任务。")
            lines.append("")
            lines.append(f"- Save page 1 full image to: `{pair_task['full_path']}`")
            lines.append(f"- Save page 2 no-text background to: `{pair_task['background_path']}`")
            lines.append(f"- Aspect ratio: `{pair_task['aspect_ratio']}`")
            lines.append(f"- Canvas: `{pair_task['canvas']}`")
            lines.append("")
            lines.append(pair_task["prompt"])
            lines.append("")
        lines.append("### 1. full image")
        lines.append("")
        lines.append(f"- Save to: `{full['path']}`")
        lines.append(f"- Aspect ratio: `{full['aspect_ratio']}`")
        lines.append(f"- Canvas: `{full['canvas']}`")
        lines.append("")
        lines.append(full["prompt"])
        lines.append("")
        if "background" in pair:
            background = pair["background"]
            lines.append("### 2. no-text background")
            lines.append("")
            lines.append(f"- Input image: `{background['input_image']}`")
            lines.append(f"- Save to: `{background['path']}`")
            lines.append(f"- Aspect ratio: `{background['aspect_ratio']}`")
            lines.append(f"- Canvas: `{background['canvas']}`")
            lines.append("- Required mode: image editing / image-to-image. Upload or attach the input image above; do not regenerate from text only.")
            lines.append("")
            lines.append(background["prompt"])
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_plan(args: argparse.Namespace) -> int:
    """Create pair manifest and host-native task files."""
    script_path = args.script.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    pages = parse_page_blocks(script_path)
    page_numbers = parse_page_selection(args.pages, set(pages))
    manifest = build_pair_manifest(
        script_path,
        page_numbers,
        pages,
        output_dir,
        aspect_ratio=args.aspect_ratio,
        image_size=args.image_size,
        canvas=args.canvas,
        image_style_name=args.image_style,
        include_background=args.dual_image,
    )
    manifest_path = output_dir / "page_image_pairs.json"
    tasks_json = output_dir / "page_image_pair_tasks.json"
    tasks_md = output_dir / "page_image_pair_tasks.md"
    write_json(manifest_path, manifest)
    write_json(tasks_json, {
        "mode": "host-native-page-image-pairs",
        "manifest": str(manifest_path),
        "tasks": _flatten_tasks(manifest),
    })
    tasks_md.write_text(render_tasks_md(manifest), encoding="utf-8")
    print(f"Pair manifest: {manifest_path}")
    print(f"Host-native task JSON: {tasks_json}")
    print(f"Host-native task Markdown: {tasks_md}")
    print(f"Pages: {', '.join(str(num) for num in page_numbers)}")
    return 0


def _create_plan(
    *,
    script_path: Path,
    pages_raw: str,
    output_dir: Path,
    aspect_ratio: str,
    image_size: str,
    canvas: str,
    project_path: Path | None = None,
    image_style_name: str | None = None,
    resume: bool = False,
    include_background: bool = False,
) -> tuple[dict, Path, list[int]]:
    """Create and persist a page-image-pair plan."""
    script_path = script_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "page_image_pairs.json"
    if resume and manifest_path.is_file():
        manifest = load_manifest(manifest_path)
        page_numbers = [int(pair["page_number"]) for pair in manifest.get("pairs", [])]
        return manifest, manifest_path, page_numbers

    pages = parse_page_blocks(script_path)
    page_numbers = parse_page_selection(pages_raw, set(pages))
    manifest = build_pair_manifest(
        script_path,
        page_numbers,
        pages,
        output_dir,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        canvas=canvas,
        project_path=project_path,
        image_style_name=image_style_name,
        include_background=include_background,
    )
    tasks_json = output_dir / "page_image_pair_tasks.json"
    tasks_md = output_dir / "page_image_pair_tasks.md"
    write_json(manifest_path, manifest)
    write_json(tasks_json, {
        "mode": "host-native-page-image-pairs",
        "manifest": str(manifest_path),
        "tasks": _flatten_tasks(manifest),
    })
    tasks_md.write_text(render_tasks_md(manifest), encoding="utf-8")
    return manifest, manifest_path, page_numbers


def _page_selection_slug(page_numbers: list[int]) -> str:
    """Return a compact filesystem slug for selected pages."""
    if not page_numbers:
        return "all"
    ranges: list[str] = []
    start = previous = page_numbers[0]
    for number in page_numbers[1:]:
        if number == previous + 1:
            previous = number
            continue
        ranges.append(f"{start}-{previous}" if start != previous else str(start))
        start = previous = number
    ranges.append(f"{start}-{previous}" if start != previous else str(start))
    return "p" + "_".join(ranges)


def _unique_project_name(base_name: str, canvas_format: str, projects_dir: Path) -> str:
    """Choose a project name that will not collide with today's project folder."""
    date_str = datetime.now().strftime("%Y%m%d")
    normalized_format = normalize_canvas_format(canvas_format)
    safe_base = sanitize_name(base_name)
    candidate = safe_base
    counter = 2
    while (projects_dir / f"{candidate}_{normalized_format}_{date_str}").exists():
        candidate = f"{safe_base}_{counter:02d}"
        counter += 1
    return candidate


def _resolve_or_create_project(args: argparse.Namespace) -> tuple[Path, Path]:
    """Create or reuse a PPT Master project and archive the source script."""
    original_script = args.script.resolve()
    pages = parse_page_blocks(original_script)
    page_numbers = parse_page_selection(args.pages, set(pages))

    if args.project_path:
        project_path = args.project_path.resolve()
        if not project_path.is_dir():
            raise FileNotFoundError(f"Project directory not found: {project_path}")
    else:
        projects_dir = args.projects_dir.resolve()
        raw_name = args.project_name or f"{original_script.stem}_{_page_selection_slug(page_numbers)}"
        project_name = _unique_project_name(raw_name, args.format, projects_dir)
        project_path = Path(
            ProjectManager(base_dir=projects_dir).init_project(
                project_name,
                canvas_format=args.format,
                base_dir=str(projects_dir),
            )
        ).resolve()

    summary = ProjectManager().import_sources(str(project_path), [str(original_script)], copy=True)
    imported_scripts = summary.get("markdown") or summary.get("archived")
    if not imported_scripts:
        skipped = "; ".join(summary.get("skipped", []))
        raise RuntimeError(f"Failed to import script into project sources: {skipped}")
    return project_path, Path(imported_scripts[0]).resolve()


def _flatten_tasks(manifest: dict) -> list[dict]:
    """Flatten pairs into ordered generation tasks."""
    tasks = []
    for pair in manifest["pairs"]:
        tasks.append({
            "page_number": pair["page_number"],
            "title": pair["title"],
            "kind": "full",
            **pair["full"],
        })
        if "background" in pair:
            tasks.append({
                "page_number": pair["page_number"],
                "title": pair["title"],
                "kind": "background",
                **pair["background"],
            })
    return tasks


def load_manifest(path: Path) -> dict:
    """Load a pair manifest."""
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest(args: argparse.Namespace) -> int:
    """Verify generated image files and update statuses."""
    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    generated = 0
    missing = 0
    for pair in manifest["pairs"]:
        for key in manifest.get("output_variants", ["full"]):
            if key not in pair:
                continue
            item = pair[key]
            path = Path(item["path"])
            if path.is_file() and path.stat().st_size > 0:
                _mark_generated(item, path)
                generated += 1
            else:
                missing += 1
                if args.mark_missing_manual:
                    item["status"] = STATUS_NEEDS_MANUAL
                    item["last_error"] = f"Missing expected image file: {path}"
    write_json(manifest_path, manifest)
    print(f"Verified: {generated} generated / {missing} missing")
    return 0 if missing == 0 or args.mark_missing_manual else 1


def _codex_size(item: dict, override: str | None) -> str:
    if override:
        return override
    canvas = str(item.get("canvas") or DEFAULT_CANVAS)
    return canvas.lower().replace("×", "x")


def apply_run_speed_options(args: argparse.Namespace) -> None:
    """Apply speed-oriented run presets without overriding explicit choices."""
    if not getattr(args, "draft", False):
        return
    if getattr(args, "quality", "high") == "high":
        args.quality = "medium"
    if getattr(args, "image_size", DEFAULT_IMAGE_SIZE) == DEFAULT_IMAGE_SIZE:
        args.image_size = DRAFT_IMAGE_SIZE
    if getattr(args, "canvas", DEFAULT_CANVAS) == DEFAULT_CANVAS:
        args.canvas = DRAFT_CANVAS


def _generate_one_pair(pair: dict, args: argparse.Namespace) -> tuple[int, dict, Exception | None]:
    """Generate one page pair; full and background remain strictly ordered."""
    page_number = pair["page_number"]
    full = pair["full"]
    full_path = Path(full["path"])

    if full_path.exists() and not args.force:
        print(f"Page {page_number}: full exists, skip: {full_path}")
        _mark_generated(full, full_path)
    else:
        print(f"Page {page_number}: generate full -> {full_path}")
        try:
            last_error = None
            for attempt in range(1, args.full_retries + 2):
                try:
                    run_codex_image(
                        prompt=full["prompt"],
                        output_path=full_path,
                        image_paths=[],
                        model=args.model,
                        size=_codex_size(full, args.size),
                        quality=args.quality,
                        force=True,
                        dry_run=args.dry_run,
                        timeout=args.timeout,
                    )
                    full["attempts"] = attempt
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    print(
                        f"Page {page_number}: full attempt {attempt} failed: {exc}",
                        file=sys.stderr,
                    )
            if last_error is not None:
                raise last_error
            if not args.dry_run:
                _mark_generated(full, full_path, method="codex-oauth-generate")
        except Exception as exc:
            full["status"] = "Failed"
            full["last_error"] = str(exc)
            print(f"Error generating full for page {page_number}: {exc}", file=sys.stderr)
            return page_number, pair, exc

    if args.dry_run:
        return page_number, pair, None
    if not getattr(args, "include_background", False) or "background" not in pair:
        return page_number, pair, None

    background = pair["background"]
    background_path = Path(background["path"])
    if not full_path.exists():
        exc = FileNotFoundError(f"Missing dependency full image: {full_path}")
        background["status"] = "Failed"
        background["last_error"] = str(exc)
        return page_number, pair, exc

    if background_path.exists() and not args.force:
        print(f"Page {page_number}: background exists, skip: {background_path}")
        _mark_generated(background, background_path)
        return page_number, pair, None

    try:
        if args.background_method != "codex-edit":
            raise ValueError("Only codex-edit background generation is supported.")
        print(f"Page {page_number}: Codex edit background -> {background_path}")
        last_error = None
        for attempt in range(1, args.background_retries + 2):
            try:
                run_codex_image(
                    prompt=background["prompt"],
                    output_path=background_path,
                    image_paths=[full_path],
                    model=args.model,
                    size=_codex_size(background, args.size),
                    quality=args.quality,
                    force=True,
                    dry_run=False,
                    timeout=args.timeout,
                )
                background["attempts"] = attempt
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                print(
                    f"Page {page_number}: background attempt {attempt} failed: {exc}",
                    file=sys.stderr,
                )
        if last_error is not None:
            raise last_error
        _mark_generated(background, background_path, method="codex-oauth-edit")
    except Exception as exc:
        background["status"] = "Failed"
        background["last_error"] = str(exc)
        print(f"Error generating background for page {page_number}: {exc}", file=sys.stderr)
        return page_number, pair, exc

    return page_number, pair, None


def generate_pairs(args: argparse.Namespace) -> int:
    """Generate images from a manifest."""
    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    if not hasattr(args, "include_background"):
        args.include_background = bool(getattr(args, "dual_image", False))
    parallel_pages = max(1, int(getattr(args, "parallel_pages", 1) or 1))
    pairs = manifest["pairs"]
    if parallel_pages == 1 or len(pairs) <= 1:
        for index, pair in enumerate(pairs):
            _page_number, updated_pair, error = _generate_one_pair(pair, args)
            pairs[index] = updated_pair
            write_json(manifest_path, manifest)
            if error is not None:
                return 1
    else:
        pair_by_page = {int(pair["page_number"]): pair for pair in pairs}
        with ThreadPoolExecutor(max_workers=parallel_pages) as executor:
            futures = [executor.submit(_generate_one_pair, pair, args) for pair in pairs]
            for future in as_completed(futures):
                page_number, updated_pair, error = future.result()
                pair_by_page[int(page_number)] = updated_pair
                manifest["pairs"] = [pair_by_page[int(pair["page_number"])] for pair in pairs]
                write_json(manifest_path, manifest)
                if error is not None:
                    return 1
    write_json(manifest_path, manifest)
    print(f"Generation manifest updated: {manifest_path}")
    return 0


def generate_pair_pages(args: argparse.Namespace) -> int:
    """Generate each full/background pair from one two-page prompt."""
    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    for pair in manifest["pairs"]:
        pair_task = pair.get("pair_generation")
        if not pair_task:
            print(f"Skip page {pair['page_number']}: no pair_generation prompt.", file=sys.stderr)
            continue
        full_path = Path(pair_task["full_path"])
        background_path = Path(pair_task["background_path"])
        if full_path.exists() and background_path.exists() and not args.force:
            print(f"Page {pair['page_number']}: pair images exist, skip.")
            _mark_generated(pair["full"], full_path)
            _mark_generated(pair["background"], background_path)
            pair_task["status"] = STATUS_GENERATED
            continue
        try:
            last_error = None
            for attempt in range(1, args.retries + 2):
                try:
                    run_codex_multi_image_once(
                        prompt=pair_task["prompt"],
                        output_paths=[full_path, background_path],
                        model=args.model,
                        size=_codex_size(pair_task, args.size),
                        quality=args.quality,
                        force=args.force,
                        dry_run=args.dry_run,
                        timeout=args.timeout,
                    )
                    last_error = None
                    pair_task["attempts"] = attempt
                    break
                except Exception as exc:
                    last_error = exc
                    print(
                        f"Page {pair['page_number']}: two-page attempt {attempt} failed: {exc}",
                        file=sys.stderr,
                    )
            if last_error is not None:
                raise last_error
        except Exception as exc:
            pair_task["status"] = "Failed"
            pair_task["last_error"] = str(exc)
            write_json(manifest_path, manifest)
            print(f"Error generating two-page pair for page {pair['page_number']}: {exc}", file=sys.stderr)
            return 1
        if not args.dry_run:
            _mark_generated(pair["full"], full_path, method="codex-oauth-two-page-once")
            _mark_generated(pair["background"], background_path, method="codex-oauth-two-page-once")
            pair_task["status"] = STATUS_GENERATED
            pair_task["generated_at"] = datetime.now(timezone.utc).isoformat()
            pair_task.pop("last_error", None)
        write_json(manifest_path, manifest)
    write_json(manifest_path, manifest)
    print(f"Two-page generation manifest updated: {manifest_path}")
    return 0


def _pair_source_pages(manifest: dict) -> dict[int, template_image_flow.PageBlock]:
    script_path = Path(manifest["source_script"])
    return template_image_flow.parse_page_blocks(script_path) if script_path.is_file() else {}


def build_dual_image_template_manifest(pair_manifest: dict) -> dict:
    """Expand each generated full/background pair into two image-only PPT slides."""
    rules = template_image_flow.load_brand_rules()
    brand_body_region = template_image_flow.scale_region(
        rules["content_regions"]["body_pages"],
        template_image_flow.CANVAS_SIZE,
    )
    body_region = template_image_flow.inset_content_region(brand_body_region)
    source_pages = _pair_source_pages(pair_manifest)
    tasks = []
    for pair in pair_manifest["pairs"]:
        page_number = int(pair["page_number"])
        source_page = source_pages.get(page_number)
        if source_page is not None:
            content = template_image_flow.extract_content(source_page)
            notes_text = template_image_flow.page_notes_text(source_page)
        else:
            content = template_image_flow.PageContent(title=pair.get("title", ""), subtitle="", body="")
            notes_text = ""
        for variant, label in (("full", "完整图"), ("background", "底图")):
            image_item = pair[variant]
            tasks.append(
                {
                    "page_number": page_number,
                    "source_page_number": page_number,
                    "image_variant": variant,
                    "image_variant_label": label,
                    "page_role": "body",
                    "title": f"{pair.get('title', page_number)}_{label}",
                    "slide_title": content.title,
                    "subtitle": content.subtitle,
                    "body_text": content.body,
                    "notes_text": notes_text,
                    "render_mode": "content-image",
                    "image_path": image_item["path"],
                    "status": image_item.get("status", STATUS_GENERATED),
                }
            )
    return {
        "mode": "page-image-pair-dual-image-ppt",
        "source_script": pair_manifest.get("source_script", ""),
        "source_pair_manifest": pair_manifest.get("manifest_path", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "canvas": {
            "width": template_image_flow.CANVAS_SIZE[0],
            "height": template_image_flow.CANVAS_SIZE[1],
        },
        "brand_body_region": brand_body_region,
        "body_region": body_region,
        "body_region_inset": {
            "top": template_image_flow.CONTENT_REGION_TOP_INSET,
            "bottom": template_image_flow.CONTENT_REGION_BOTTOM_INSET,
            "side_outset": template_image_flow.CONTENT_REGION_SIDE_OUTSET,
        },
        "image_generation_scale": pair_manifest.get("generation_contract", {}).get("generation_size"),
        "tasks": tasks,
    }


def build_template_image_manifest(pair_manifest: dict) -> dict:
    """Expand generated full images into one template-image PPT slide per page."""
    rules = template_image_flow.load_brand_rules()
    brand_body_region = template_image_flow.scale_region(
        rules["content_regions"]["body_pages"],
        template_image_flow.CANVAS_SIZE,
    )
    body_region = template_image_flow.inset_content_region(brand_body_region)
    source_pages = _pair_source_pages(pair_manifest)
    tasks = []
    for pair in pair_manifest["pairs"]:
        page_number = int(pair["page_number"])
        source_page = source_pages.get(page_number)
        if source_page is not None:
            content = template_image_flow.extract_content(source_page)
            notes_text = template_image_flow.page_notes_text(source_page)
        else:
            content = template_image_flow.PageContent(title=pair.get("title", ""), subtitle="", body="")
            notes_text = ""
        image_item = pair["full"]
        tasks.append(
            {
                "page_number": page_number,
                "source_page_number": page_number,
                "image_variant": "full",
                "image_variant_label": "完整图",
                "page_role": "body",
                "title": pair.get("title", str(page_number)),
                "slide_title": content.title,
                "subtitle": content.subtitle,
                "body_text": content.body,
                "notes_text": notes_text,
                "render_mode": "content-image",
                "image_path": image_item["path"],
                "status": image_item.get("status", STATUS_GENERATED),
            }
        )
    return {
        "mode": "page-image-full-only-ppt",
        "source_script": pair_manifest.get("source_script", ""),
        "source_pair_manifest": pair_manifest.get("manifest_path", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "canvas": {
            "width": template_image_flow.CANVAS_SIZE[0],
            "height": template_image_flow.CANVAS_SIZE[1],
        },
        "brand_body_region": brand_body_region,
        "body_region": body_region,
        "body_region_inset": {
            "top": template_image_flow.CONTENT_REGION_TOP_INSET,
            "bottom": template_image_flow.CONTENT_REGION_BOTTOM_INSET,
            "side_outset": template_image_flow.CONTENT_REGION_SIDE_OUTSET,
        },
        "image_generation_scale": pair_manifest.get("generation_contract", {}).get("generation_size"),
        "tasks": tasks,
    }


def export_full_image_pptx(args: argparse.Namespace) -> int:
    """Export each script page as one template-image slide using the full image."""
    manifest_path = args.manifest.resolve()
    pair_manifest = load_manifest(manifest_path)
    pair_manifest["manifest_path"] = _rel_or_abs(manifest_path)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    full_manifest = build_template_image_manifest(pair_manifest)
    manifest_out = output_dir / "full_image_template_manifest.json"
    write_json(manifest_out, full_manifest)
    project_path = template_image_flow.write_project(full_manifest, output_dir, "full_image_ppt")
    pptx = template_image_flow.run_export(project_path)
    print(f"Full-image manifest: {manifest_out}")
    print(f"Project: {project_path}")
    print(f"PPTX: {pptx}")
    return 0


def export_dual_image_pptx(args: argparse.Namespace) -> int:
    """Export each script page as two template-image slides: full then background."""
    manifest_path = args.manifest.resolve()
    pair_manifest = load_manifest(manifest_path)
    pair_manifest["manifest_path"] = _rel_or_abs(manifest_path)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dual_manifest = build_dual_image_template_manifest(pair_manifest)
    manifest_out = output_dir / "dual_image_template_manifest.json"
    write_json(manifest_out, dual_manifest)
    project_path = template_image_flow.write_project(dual_manifest, output_dir, "dual_image_pair_ppt")
    pptx = template_image_flow.run_export(project_path)
    print(f"Dual-image manifest: {manifest_out}")
    print(f"Project: {project_path}")
    print(f"PPTX: {pptx}")
    return 0


def export_pptx(args: argparse.Namespace) -> int:
    if getattr(args, "dual_image", False):
        return export_dual_image_pptx(args)
    return export_full_image_pptx(args)


def run_script_image_to_ppt(args: argparse.Namespace) -> int:
    """Run the complete script-image-generation-to-PPT workflow."""
    apply_run_speed_options(args)
    project_path, project_script = _resolve_or_create_project(args)
    images_dir = (
        args.images_dir.resolve()
        if args.images_dir
        else project_path / "images" / "script_imagegen"
    )
    exports_dir = (
        args.output_dir.resolve()
        if args.output_dir
        else project_path / "exports" / "script_imagegen_to_ppt"
    )
    images_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    _manifest, manifest_path, page_numbers = _create_plan(
        script_path=project_script,
        pages_raw=args.pages,
        output_dir=images_dir,
        aspect_ratio=args.aspect_ratio,
        image_size=args.image_size,
        canvas=args.canvas,
        project_path=project_path,
        image_style_name=args.image_style,
        resume=args.resume,
        include_background=args.dual_image,
    )
    print(f"Project: {project_path}")
    print(f"Source script: {project_script}")
    print(f"Pair manifest: {manifest_path}")
    print(f"Image dir: {images_dir}")
    print(f"Export dir: {exports_dir}")
    print(f"Pages: {', '.join(str(num) for num in page_numbers)}")

    generate_args = argparse.Namespace(
        manifest=manifest_path,
        model=args.model,
        size=args.size,
        quality=args.quality,
        background_method="codex-edit",
        timeout=args.timeout,
        full_retries=args.full_retries,
        background_retries=args.background_retries,
        parallel_pages=args.parallel_pages,
        include_background=args.dual_image,
        force=args.force,
        dry_run=args.dry_run,
    )
    rc = generate_pairs(generate_args)
    if rc != 0 or args.dry_run:
        return rc

    verify_args = argparse.Namespace(
        manifest=manifest_path,
        mark_missing_manual=False,
    )
    rc = verify_manifest(verify_args)
    if rc != 0:
        return rc

    export_args = argparse.Namespace(
        manifest=manifest_path,
        output_dir=exports_dir,
        dual_image=args.dual_image,
    )
    return export_pptx(export_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch full-slide and no-text-background image generation tasks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Create pair manifest and host-native tasks.")
    plan.add_argument("--script", required=True, type=Path, help="script-imagegen-compact.md")
    plan.add_argument("--pages", default="all", help="Page selection, e.g. 11, 8-13, 1,3,5-7, or all.")
    plan.add_argument("-o", "--output-dir", required=True, type=Path, help="Output image/task directory.")
    plan.add_argument("--aspect-ratio", default=DEFAULT_ASPECT_RATIO, help="Generation aspect ratio.")
    plan.add_argument("--image-size", default=DEFAULT_IMAGE_SIZE, help="Generation image size label.")
    plan.add_argument("--canvas", default=DEFAULT_CANVAS, help="Canvas size label written into tasks.")
    plan.add_argument("--image-style", default=DEFAULT_STYLE_NAME, help="Image style preset name or style JSON/Markdown path.")
    plan.add_argument("--dual-image", action="store_true", help="Also plan no-text background images. Default is full images only.")
    plan.set_defaults(func=write_plan)

    run = subparsers.add_parser(
        "run",
        help="Run the complete 脚本生图转ppt workflow: plan, generate, verify, export-pptx.",
    )
    run.add_argument("--script", required=True, type=Path, help="script-imagegen-compact.md")
    run.add_argument("--pages", default="all", help="Page selection, e.g. 11, 8-13, 1,3,5-7, or all.")
    run.add_argument("--project-name", default=None, help="Project name prefix. Defaults to script stem + selected pages.")
    run.add_argument("--projects-dir", default=Path("projects"), type=Path, help="Base directory for newly created projects.")
    run.add_argument("--project-path", default=None, type=Path, help="Reuse an existing PPT Master project instead of creating a new one.")
    run.add_argument("--format", default="ppt169", help="Canvas format for newly created projects.")
    run.add_argument("--images-dir", default=None, type=Path, help="Override image/task directory. Defaults to <project>/images/script_imagegen.")
    run.add_argument("-o", "--output-dir", default=None, type=Path, help="Override PPTX output directory. Defaults to <project>/exports/script_imagegen_to_ppt.")
    run.add_argument("--aspect-ratio", default=DEFAULT_ASPECT_RATIO, help="Generation aspect ratio.")
    run.add_argument("--image-size", default=DEFAULT_IMAGE_SIZE, help="Generation image size label.")
    run.add_argument("--canvas", default=DEFAULT_CANVAS, help="Canvas size label written into tasks.")
    run.add_argument("--image-style", default=DEFAULT_STYLE_NAME, help="Image style preset name or style JSON/Markdown path.")
    run.add_argument("--model", default="gpt-image-2", help="Image model for Codex OAuth.")
    run.add_argument("--size", default=None, help="Codex output size, e.g. 1280x720. Defaults to each task canvas.")
    run.add_argument("--quality", choices=("low", "medium", "high", "auto"), default="high")
    run.add_argument("--timeout", type=int, default=300)
    run.add_argument("--full-retries", type=int, default=1)
    run.add_argument("--background-retries", type=int, default=1)
    run.add_argument(
        "--parallel-pages",
        type=int,
        default=1,
        help="Generate different pages concurrently; each page still runs full before background.",
    )
    run.add_argument(
        "--draft",
        action="store_true",
        help="Use faster draft defaults: medium quality plus 1x content-region image-size/canvas unless explicitly overridden.",
    )
    run.add_argument(
        "--resume",
        action="store_true",
        help="Reuse an existing page_image_pairs.json in the image directory instead of rebuilding the plan.",
    )
    run.add_argument(
        "--dual-image",
        action="store_true",
        help="Generate and export full/background image pairs. Default is full images only.",
    )
    run.add_argument("--force", action="store_true", help="Overwrite existing images.")
    run.add_argument("--dry-run", action="store_true", help="Plan and show image request metadata without calling the backend.")
    run.set_defaults(func=run_script_image_to_ppt)

    verify = subparsers.add_parser("verify", help="Verify generated images and update manifest statuses.")
    verify.add_argument("manifest", type=Path, help="page_image_pairs.json")
    verify.add_argument("--mark-missing-manual", action="store_true", help="Mark missing images as Needs-Manual.")
    verify.set_defaults(func=verify_manifest)

    generate = subparsers.add_parser("generate", help="Generate image pairs with Codex OAuth.")
    generate.add_argument("manifest", type=Path, help="page_image_pairs.json")
    generate.add_argument("--model", default="gpt-image-2", help="Image model for Codex OAuth.")
    generate.add_argument("--size", default=None, help="Codex output size, e.g. 1280x720. Defaults to each task canvas.")
    generate.add_argument("--quality", choices=("low", "medium", "high", "auto"), default="high")
    generate.add_argument(
        "--background-method",
        choices=("codex-edit",),
        default="codex-edit",
        help="How to create no-text backgrounds.",
    )
    generate.add_argument("--timeout", type=int, default=600)
    generate.add_argument(
        "--full-retries",
        type=int,
        default=1,
        help="Retry Codex full image generation this many times after a failed request.",
    )
    generate.add_argument(
        "--background-retries",
        type=int,
        default=1,
        help="Retry Codex background edit this many times after a failed request.",
    )
    generate.add_argument(
        "--parallel-pages",
        type=int,
        default=1,
        help="Generate different pages concurrently; each page still runs full before background.",
    )
    generate.add_argument("--dual-image", action="store_true", help="Generate background images when present in the manifest. Default is full images only.")
    generate.add_argument("--force", action="store_true", help="Overwrite existing images.")
    generate.add_argument("--dry-run", action="store_true", help="Print Codex request metadata without calling the backend.")
    generate.set_defaults(func=generate_pairs)

    generate_pair = subparsers.add_parser(
        "generate-pair",
        help="Generate full/background as two independent images from one two-page prompt.",
    )
    generate_pair.add_argument("manifest", type=Path, help="page_image_pairs.json")
    generate_pair.add_argument("--model", default="gpt-image-2", help="Image model for Codex OAuth.")
    generate_pair.add_argument("--size", default=None, help="Codex output size, e.g. 1280x720. Defaults to each task canvas.")
    generate_pair.add_argument("--quality", choices=("low", "medium", "high", "auto"), default="high")
    generate_pair.add_argument("--timeout", type=int, default=300)
    generate_pair.add_argument("--retries", type=int, default=1, help="Retry failed two-page requests this many times.")
    generate_pair.add_argument("--force", action="store_true", help="Overwrite existing images.")
    generate_pair.add_argument("--dry-run", action="store_true", help="Print Codex request metadata without calling the backend.")
    generate_pair.set_defaults(func=generate_pair_pages)

    export = subparsers.add_parser("export-pptx", help="Convert generated image pairs to PPTX.")
    export.add_argument("manifest", type=Path, help="page_image_pairs.json")
    export.add_argument("-o", "--output-dir", required=True, type=Path, help="PPTX output directory.")
    export.add_argument("--dual-image", action="store_true", help="Export full/background pairs. Default exports full images only.")
    export.set_defaults(func=export_pptx)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
