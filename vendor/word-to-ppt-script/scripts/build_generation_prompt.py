#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if SRC_ROOT.exists() and str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from business_semantic_content_pipeline.visual_style import VisualStyleError, load_visual_style, style_summary
from validate_script import Page, parse_pages

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "imagegen-page-contract.yaml"
ACTIVE_STYLE_PATH = REPO_ROOT / "visual" / "ACTIVE-STYLE.md"
LEGACY_STYLE_PATH = ROOT / "templates" / "imagegen" / "visual-style.md"
DEFAULT_STYLE_PATH = ACTIVE_STYLE_PATH if ACTIVE_STYLE_PATH.exists() else LEGACY_STYLE_PATH
PAGE_CONTRACT_RE = re.compile(r"<!--\s*cyberppt-page-contract\s+(\{.*?\})\s*-->", re.S)
BOLD_TITLE_RE = re.compile(r"^-\s*\*\*(.+?)\*\*\s*$", re.M)


def load_yaml(path: Path) -> dict:
    if yaml is None or not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_config() -> dict:
    return load_yaml(CONFIG_PATH).get("contract", {})


def canonical_page_type(page_type: str, config: dict) -> str:
    page_type = page_type.strip().strip("`")
    template_map = config.get("template_page_types", {})
    content_map = config.get("content_page_types", {})
    if page_type in template_map:
        return str(template_map[page_type])
    if page_type in content_map:
        return str(content_map[page_type])
    return "content" if page_type else "content"


def page_contract(page: Page) -> dict:
    match = PAGE_CONTRACT_RE.search(page.raw)
    if not match:
        return {}
    try:
        value = json.loads(match.group(1))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def key_text(page: Page, limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for match in BOLD_TITLE_RE.finditer(page.visible):
        value = match.group(1).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def _visual_fields(page: Page) -> dict[str, str]:
    text = page.visual
    return {match.group(1).strip(): match.group(2).strip() for match in re.finditer(r"^-\s*([^：:\n]+)[：:]\s*(.*)$", text, re.M)}


def visual_structure_text(page: Page) -> str:
    fields = _visual_fields(page)
    relationship = (
        fields.get("decision_relationship")
        or fields.get("决策关系")
        or fields.get("visual_thesis")
        or fields.get("主判断")
        or "围绕本页核心判断形成一个连续业务关系"
    )
    carrier = fields.get("dominant_visual_carrier") or fields.get("主视觉载体") or "由页面业务对象决定的唯一主视觉载体"
    spatial = fields.get("spatial_organization") or fields.get("空间组织") or "非均衡、非对称的一体化正文场"
    reading = fields.get("reading_path") or fields.get("阅读路径") or "沿业务关系方向读取并抵达结果区"
    encoding = fields.get("relationship_encoding") or fields.get("关系编码") or "用位置、尺度、边界和少量方向性连接表达"
    integration = fields.get("text_integration_method") or fields.get("图文融合") or "正文贴附对应业务对象、动作、证据和结果区域"
    scene = fields.get("industry_scene_anchor") or fields.get("行业场景锚点") or "使用与本页业务含义直接相关的具象对象或行业场景"
    hierarchy = fields.get("visual_hierarchy") or fields.get("单一视觉中心") or "核心判断和结果区域承担最大视觉权重"
    avoid = fields.get("avoid_on_this_page") or fields.get("禁止事项") or "均衡卡片墙、图标逐条对应、第二视觉中心和无关装饰"
    return "\n".join([
        f"- 主关系：{relationship}",
        f"- 主视觉载体：{carrier}",
        f"- 空间组织：{spatial}",
        f"- 阅读路径：{reading}",
        f"- 关系编码：{encoding}",
        f"- 文字整合：{integration}",
        f"- 场景锚点：{scene}",
        f"- 结果与层级：{hierarchy}",
        f"- 本页避免：{avoid}",
    ])


def page_mission(page: Page) -> tuple[str, str]:
    contract = page_contract(page)
    mission = str(contract.get("page_mission") or "").strip()
    core = str(contract.get("core_message") or "").strip()
    main = page.fields.get("主判断", "").strip()
    only = page.fields.get("本页只回答", "").strip()
    if not mission:
        mission = main or only
    if not core:
        core = main or mission
    return mission, core


def review_header(
    project: str,
    source_script: str,
    style_source: str,
    config: dict,
    style_meta: dict | None = None,
) -> list[str]:
    lines = [
        f"# ImageGen 送图脚本审阅稿 · {project}",
        "",
        "> 状态：等待用户修改或批准。未经批准不得进入 ImageGen。",
        f"> 源脚本：`{source_script}`",
        f"> 风格来源：`{style_source}`",
        f"> 运行时风格：`{(style_meta or {}).get('style_id', 'custom')}`｜{(style_meta or {}).get('style_name', 'custom')}",
        f"> 风格版本：`{(style_meta or {}).get('version', 'custom')}`",
        f"> 风格 SHA-256：`{(style_meta or {}).get('sha256', 'n/a')}`",
        f"> Prompt compiler: `{config.get('prompt_compiler', 'content-first-v1')}`",
        f"> Visual structure mode: `{config.get('visual_structure_mode', 'off')}`",
        f"> Text render mode: `{config.get('text_render_mode', 'full_image')}`",
        "",
        "## 编入规则",
        "",
        "- 每页独立完整，可直接送入 ImageGen，不依赖批次级公共提示。",
        "- 送入：页面任务、核心判断、锁定关键文字、完整上屏内容、清洗后的页面视觉结构、画布尺寸，以及运行时唯一视觉风格。",
        "- 不送入：源材料全文、完整事实边界、证据编号、讲解提示、文字取舍、图片数量或后期制作规则。",
        "- 页面视觉结构只保留主关系、主视觉载体、空间组织、阅读路径、关系编码、文字整合、场景锚点、结果层级和本页避免；不发送原始 visual_intent_type、证据映射或内部分析标签。",
        "- 页面任务与核心意思只用于理解业务关系；锁定关键文字和完整上屏内容均需进入 full 图。",
        "- 封面、目录、章节过渡、封底不生成正文区 ImageGen，由代码生成模板SVG并写入可编辑PPT。",
        "- 内容页标题、副标题、页码、Logo和模板公共元素由PPT代码层写入，正文区图片不得绘制。",
        "",
    ]
    return lines


def template_page_block(page: Page, canonical_type: str) -> list[str]:
    return [
        f"## 第{page.number}页：{page.title}",
        "",
        f"- 页面类型：`{canonical_type}`",
        "- 结论：本页不生成正文区 ImageGen；标题/章节字由模板文字层输出。",
        "",
    ]


def content_page_block(
    page: Page,
    config: dict,
    style_text: str,
    canvas_width: int,
    canvas_height: int,
    canvas_ratio: str,
) -> list[str]:
    limit = int(config.get("key_text_limit", 7))
    keys = key_text(page, limit)
    mission, core = page_mission(page)
    lines = [f"## 第{page.number}页：{page.title}", "", "【锁定关键文字】"]
    lines.extend(keys or ["（未提取到加粗小标题，请回查完整脚本）"])
    lines.extend([
        "",
        "【完整上屏内容】",
        page.visible.strip(),
        "",
        "【结论句要求｜不上屏】",
        "如【锁定关键文字】含正文结论句，该句是正文结论句，不是页面标题；不得通栏放大或添加标题竖线、横线等装饰。",
        "允许调整换行和文字层级；画面必须参与表达页面逻辑，不得退化为文字排版加装饰图片。",
        "",
        "页面任务：",
        mission or "（缺少页面任务，请回查完整脚本的主判断或页级合同）",
        "",
        "核心意思：",
        core or mission or "（缺少核心意思，请回查完整脚本的主判断或页级合同）",
        "",
        "",
        "",
        "【输出尺寸｜不上屏】",
        f"画布尺寸固定为 {canvas_width}×{canvas_height} 像素（{canvas_ratio} 横向）。必须按该尺寸与比例构图，不得输出 16:9、4:3、方形或其他比例。",
        "",
        "【模板层禁绘｜不上屏】",
        "正文区图只画业务内容，不绘制页面标题、副标题、页码、页面序号（第N页 / Pxx / Slide N）、Logo、页脚或母版装饰线。",
        "标题与副标题由 PPT 模板文字层承载，不得在图内另起通栏标题区。",
        "【锁定关键文字】【完整上屏内容】中的业务编号与模块名必须保留；禁止新增与锁定文案无关的序号条、页码章或装饰编号。",
        "",
        "【页面视觉结构｜不上屏】",
        visual_structure_text(page),
        "",
        "【全局视觉风格｜不上屏】",
        style_text.strip(),
        "",
    ])
    return lines


def build(
    text: str,
    *,
    project: str = "project",
    source_script: str = "script-final.md",
    style_source: str = "visual/ACTIVE-STYLE.md",
    style_text: str | None = None,
    style_metadata: dict | None = None,
    selected_pages: set[int] | None = None,
    canvas_width: int | None = None,
    canvas_height: int | None = None,
    canvas_ratio: str | None = None,
) -> str:
    config = load_config()
    canvas = config.get("canvas", {})
    width = int(canvas_width or canvas.get("width", 2048))
    height = int(canvas_height or canvas.get("height", 1024))
    ratio = str(canvas_ratio or canvas.get("ratio", "2:1"))
    style_meta: dict | None = style_metadata
    if style_text is not None:
        style = style_text
    else:
        profile = load_visual_style(DEFAULT_STYLE_PATH)
        style = profile.prompt_body
        style_meta = style_summary(profile)
        style_source = str(profile.source_path)
    pages = parse_pages(text)
    lines = review_header(project, source_script, style_source, config, style_meta)
    for page in pages:
        if selected_pages is not None and page.number not in selected_pages:
            continue
        canonical = canonical_page_type(page.page_type, config)
        if canonical in {"cover", "contents", "chapter", "closing"}:
            lines.extend(template_page_block(page, canonical))
        else:
            lines.extend(content_page_block(page, config, style, width, height, ratio))
    return "\n".join(lines).rstrip() + "\n"


def parse_page_selection(values: list[str]) -> set[int] | None:
    if not values:
        return None
    result: set[int] = set()
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                left, right = part.split("-", 1)
                result.update(range(int(left), int(right) + 1))
            else:
                result.add(int(part))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile full script into ImageGen review/page contracts")
    parser.add_argument("script", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--project", default=None, help="Project slug shown in review title")
    parser.add_argument("--source-script", default=None, help="Source script path displayed in metadata")
    parser.add_argument("--style-template", type=Path, default=DEFAULT_STYLE_PATH)
    parser.add_argument("--page", action="append", default=[], help="Page number/range, e.g. 4 or 4-8 or 4,6,8")
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--ratio", default=None)
    args = parser.parse_args()

    text = args.script.read_text(encoding="utf-8")
    try:
        profile = load_visual_style(args.style_template)
    except VisualStyleError as exc:
        parser.error(str(exc))
    style = profile.prompt_body
    project = args.project or args.script.stem
    source_script = args.source_script or str(args.script)
    output = build(
        text,
        project=project,
        source_script=source_script,
        style_source=f"{profile.source_path}#{profile.sha256}",
        style_text=style,
        style_metadata=style_summary(profile),
        selected_pages=parse_page_selection(args.page),
        canvas_width=args.width,
        canvas_height=args.height,
        canvas_ratio=args.ratio,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
