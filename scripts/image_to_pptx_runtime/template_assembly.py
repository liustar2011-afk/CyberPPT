"""Template body-slot assembly for Stage 02 image and editable outputs.

The Stage 02 visual contract is a 2:1 body canvas.  This module wraps either
the audited body image or a Quick authoring SVG in the repository's 1280x720
CEC lightweight chrome without changing the body geometry.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from xml.sax.saxutils import quoteattr

from .svg_to_pptx.pptx_package.builder import create_pptx_with_native_svg
from .svg_to_pptx.drawingml.theme_fonts import MasterTextStyleSpec


CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720
TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "assets" / "presentation-templates" / "cec-lightweight"
TEMPLATE_BACKGROUND = "#FFFFFF"
TEMPLATE_FONT_FAMILY = "Source Han Sans CN, Hiragino Sans GB, STHeiti, Arial, sans-serif"
TEMPLATE_ASSEMBLY_PROFILE = "cec-structured-master-v1"


def load_template_contract(template_dir: Path | None = None) -> dict:
    """Load the current repository-owned presentation template contract."""

    root = (template_dir or TEMPLATE_DIR).expanduser().resolve()
    rules_path = root / "brand_rules.json"
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    if not isinstance(rules, dict):
        raise ValueError(f"template rules must be an object: {rules_path}")
    canvas = rules.get("canvas") if isinstance(rules.get("canvas"), dict) else {}
    if canvas.get("width") != CANVAS_WIDTH or canvas.get("height") != CANVAS_HEIGHT:
        raise ValueError("CEC template canvas must remain 1280x720")
    body = (rules.get("content_regions") or {}).get("body_pages")
    if not isinstance(body, dict):
        raise ValueError("CEC template is missing content_regions.body_pages")
    if not _is_two_to_one(float(body.get("width", 0)), float(body.get("height", 0))):
        raise ValueError("CEC template body region must remain 2:1")
    return {"root": root, "rules": rules}


def _is_two_to_one(width: float, height: float, *, tolerance: float = 0.002) -> bool:
    return height > 0 and abs(width / height - 2.0) <= tolerance


def _viewbox(root: ET.Element, source: Path) -> tuple[float, float, float, float]:
    raw = (root.get("viewBox") or "").replace(",", " ")
    values = [float(value) for value in raw.split() if value.strip()]
    if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
        raise ValueError(f"{source} must declare a positive four-value viewBox")
    if not _is_two_to_one(values[2], values[3]):
        raise ValueError(f"{source} must use a 2:1 authoring canvas; got {values[2]}x{values[3]}")
    return values[0], values[1], values[2], values[3]


def _body_region(contract: dict) -> tuple[float, float, float, float]:
    body = contract["rules"]["content_regions"]["body_pages"]
    return float(body["x"]), float(body["y"]), float(body["width"]), float(body["height"])


def _asset_copy(template_root: Path, assembly_root: Path) -> Path:
    images = assembly_root / "images"
    images.mkdir(parents=True, exist_ok=True)
    logo = template_root / "logo.png"
    target = images / logo.name
    shutil.copy2(logo, target)
    return target


def _rules_number(rules: dict, section: str, field: str, default: float) -> float:
    value = ((rules.get("master_elements") or {}).get(section) or {}).get(field, default)
    return float(value)


def _render_chrome(
    *,
    rules: dict,
    logo_href: str,
    title: str,
    subtitle: str,
    page_number: int,
) -> list[str]:
    master = rules.get("master_elements") or {}
    top = master.get("top_divider") or {}
    footer = master.get("footer_bar") or {}
    logo = master.get("logo") or {}
    org = master.get("footer_company_text") or {}
    number = master.get("footer_page_num") or {}
    header = (rules.get("content_regions") or {}).get("body_header_region") or {}
    title_y = float(header.get("y", 16)) + 31
    lines = [
        f'<rect id="masterBackground" data-pptx-layer="master" x="0" y="0" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" fill="{TEMPLATE_BACKGROUND}"/>',
        f'<rect id="topDivider" data-pptx-layer="master" x="0" y="{top.get("y", 84)}" width="{CANVAS_WIDTH}" height="{top.get("height", 3)}" fill={quoteattr(str(top.get("fill", "#8B0000")))}/>',
        f'<image id="companyLogo" data-pptx-layer="master" x="{logo.get("x", 1050)}" y="{logo.get("y", 13)}" width="{logo.get("width", 210)}" height="{logo.get("height", 70)}" href={quoteattr(logo_href)} preserveAspectRatio="xMidYMid meet"/>',
        f'<text x="{header.get("x", 58)}" y="{title_y:g}" font-family={quoteattr(TEMPLATE_FONT_FAMILY)} font-size="32" font-weight="700" fill="#123B66">{xml_escape(title)}</text>',
    ]
    if subtitle.strip():
        lines.append(
            f'<text x="{header.get("x", 58)}" y="{float(header.get("y", 16)) + 56:g}" font-family={quoteattr(TEMPLATE_FONT_FAMILY)} font-size="14" fill="#60758A">{xml_escape(subtitle)}</text>'
        )
    lines.extend(
        [
            f'<rect id="footerBar" data-pptx-layer="master" x="0" y="{footer.get("y", 698)}" width="{CANVAS_WIDTH}" height="{footer.get("height", 22)}" fill={quoteattr(str(footer.get("fill", "#123B66")))}/>',
            f'<text id="footerCompany" data-pptx-layer="master" x="{org.get("x", 58)}" y="{org.get("y", 709)}" font-family={quoteattr(TEMPLATE_FONT_FAMILY)} font-size="{org.get("font_size", 9)}" fill={quoteattr(str(org.get("fill", "#FFFFFF")))}>{xml_escape(str(org.get("text", "中国电力企业联合会")))}</text>',
            f'<text id="pageNumber" data-pptx-layer="master" x="{number.get("x", 1240)}" y="{number.get("y", 709)}" text-anchor="end" font-family="Consolas, Arial, sans-serif" font-size="{number.get("font_size", 9)}" fill={quoteattr(str(number.get("fill", "#FFFFFF")))}>{int(page_number)}</text>',
        ]
    )
    return [line for line in lines if 'data-pptx-layer="master"' in line] + [
        line for line in lines if 'data-pptx-layer="master"' not in line
    ]


_NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
_GEOMETRY_SCALE_ATTRS = {
    "x": "x",
    "y": "y",
    "x1": "x",
    "x2": "x",
    "y1": "y",
    "y2": "y",
    "cx": "x",
    "cy": "y",
    "dx": "x",
    "dy": "y",
    "width": "x",
    "height": "y",
    "rx": "x",
    "ry": "y",
    "r": "x",
    "stroke-width": "x",
    "font-size": "y",
    "letter-spacing": "x",
    "word-spacing": "x",
}


def _local_tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _scaled_numbers(value: str, factor: float) -> str:
    def replace(match: re.Match[str]) -> str:
        number = float(match.group(0)) * factor
        if math.isclose(number, round(number), abs_tol=1e-9):
            return str(int(round(number)))
        return f"{number:.12g}"

    return _NUMBER_RE.sub(replace, value)


def _materialize_body_scale(element: ET.Element, *, scale_x: float, scale_y: float) -> None:
    """Bake the 2:1-to-body scale into leaf geometry.

    The native converter intentionally rejects a scale/matrix on a group that
    contains text.  A translation-only wrapper plus scaled leaf coordinates
    preserves the same visual geometry while keeping native text editable.
    """

    tag = _local_tag(element)
    transform = element.get("transform")
    if transform:
        rotation = re.fullmatch(r"\s*rotate\(\s*([^()]*)\s*\)\s*", transform)
        args = rotation.group(1).replace(",", " ").split() if rotation else []
        if (tag == "text" and len(args) in {1, 3}
                and all(_NUMBER_RE.fullmatch(value) for value in args)
                and math.isclose(scale_x, scale_y)):
            # Uniform scaling retains the angle and scales the rotation pivot.
            angle = float(args[0])
            pivot = (float(args[1]) * scale_x, float(args[2]) * scale_y) if len(args) == 3 else (0, 0)
            element.set("transform", f"rotate({angle:g} {pivot[0]:.12g} {pivot[1]:.12g})")
        else:
            raise ValueError(
                f"Quick authoring SVG element {tag!r} has a source transform; "
                "template assembly requires untransformed 2:1 geometry or uniformly scaled text rotation"
            )
    if tag == "path":
        # Paths keep their original metrics: the matrix scales geometry/stroke.
        element.set("transform", f"matrix({scale_x:.12g} 0 0 {scale_y:.12g} 0 0)")
        return
    # Presentation attributes also live on groups and are inherited by text.
    # Scale every explicit declaration once, before recursing into containers.
    for name, axis in _GEOMETRY_SCALE_ATTRS.items():
        if tag in {"g", "defs", "clipPath", "mask", "symbol"} and name not in {"font-size", "letter-spacing", "word-spacing"}:
            continue
        value = element.get(name)
        if value is not None:
            element.set(name, _scaled_numbers(value, scale_x if axis == "x" else scale_y))
    if tag in {"g", "defs", "clipPath", "mask", "symbol"}:
        for child in list(element):
            _materialize_body_scale(child, scale_x=scale_x, scale_y=scale_y)
        return
    points = element.get("points")
    if points is not None:
        values = [float(value) for value in _NUMBER_RE.findall(points)]
        scaled: list[str] = []
        for index, value in enumerate(values):
            factor = scale_x if index % 2 == 0 else scale_y
            scaled.append(f"{value * factor:.12g}")
        element.set("points", " ".join(scaled))
    for child in list(element):
        _materialize_body_scale(child, scale_x=scale_x, scale_y=scale_y)


def _source_children(source_svg: Path) -> tuple[ET.Element, list[ET.Element]]:
    try:
        root = ET.parse(source_svg).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValueError(f"cannot read authoring SVG {source_svg}: {exc}") from exc
    x, y, width, height = _viewbox(root, source_svg)
    if not math.isclose(x, 0.0, abs_tol=0.01) or not math.isclose(y, 0.0, abs_tol=0.01):
        raise ValueError(f"{source_svg} must use a zero-origin 2:1 viewBox")
    return root, list(root)


def _rewrite_source_hrefs(children: list[ET.Element], *, source_svg: Path, target_svg: Path) -> list[str]:
    """Copy relative SVG assets beside the wrapper and retain source hrefs."""

    target_svg.parent.mkdir(parents=True, exist_ok=True)
    rewritten: list[str] = []
    for child in children:
        for node in child.iter():
            for attribute in ("href", "{http://www.w3.org/1999/xlink}href"):
                href = node.get(attribute)
                if not href or href.startswith(("data:", "http:", "https:")):
                    continue
                source_asset = (
                    Path(href).expanduser().resolve()
                    if Path(href).is_absolute()
                    else (source_svg.parent / href).resolve()
                )
                if not source_asset.is_file():
                    raise FileNotFoundError(f"authoring SVG asset is missing: {source_asset}")
                target_asset = (
                    target_svg.parent / source_asset.name
                    if Path(href).is_absolute()
                    else target_svg.parent / href
                ).resolve()
                target_asset.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_asset, target_asset)
                if Path(href).is_absolute():
                    node.set(attribute, os.path.relpath(target_asset, target_svg.parent))
        rewritten.append(ET.tostring(child, encoding="unicode"))
    return rewritten


def assemble_template_svg(
    *,
    source: Path,
    output: Path,
    title: str,
    subtitle: str = "",
    page_number: int,
    mode: str,
    contract: dict | None = None,
    body_image: Path | None = None,
) -> Path:
    """Create a 1280x720 template wrapper around a 2:1 body asset."""

    if mode not in {"image", "editable"}:
        raise ValueError(f"unsupported template assembly mode: {mode}")
    loaded = contract or load_template_contract()
    root = loaded["root"]
    rules = loaded["rules"]
    body_x, body_y, body_width, body_height = _body_region(loaded)
    output.parent.mkdir(parents=True, exist_ok=True)
    logo_target = _asset_copy(root, output.parent.parent)
    logo_href = Path("..").joinpath("images", logo_target.name).as_posix()
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}" data-template-assembly="cec-lightweight" data-pptx-master="cec-content" data-pptx-master-name="CEC Content Master" data-pptx-layout="cec-content" data-pptx-layout-name="CEC Content">'
    ]
    elements.extend(_render_chrome(rules=rules, logo_href=logo_href, title=title, subtitle=subtitle, page_number=page_number))
    if mode == "image":
        if body_image is None or not body_image.is_file():
            raise FileNotFoundError(f"template image assembly requires body image: {body_image}")
        image_target = output.parent.parent / "images" / body_image.name
        image_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(body_image, image_target)
        image_href = Path("..").joinpath("images", image_target.name).as_posix()
        insert_at = len(elements)
        elements.insert(
            insert_at,
            f'<image x="{body_x:g}" y="{body_y:g}" width="{body_width:g}" height="{body_height:g}" href={quoteattr(image_href)} preserveAspectRatio="none"/>',
        )
    else:
        source_root, children = _source_children(source)
        viewbox = [float(value) for value in (source_root.get("viewBox") or "").replace(",", " ").split()]
        scale_x = body_width / viewbox[2]
        scale_y = body_height / viewbox[3]
        _materialize_body_scale(source_root, scale_x=scale_x, scale_y=scale_y)
        copied = _rewrite_source_hrefs(list(source_root), source_svg=source, target_svg=output)
        body_group = [
            f'<g id="quick-body" transform="translate({body_x:g} {body_y:g})">',
            *copied,
            "</g>",
        ]
        insert_at = len(elements)
        elements[insert_at:insert_at] = body_group
    elements.append("</svg>\n")
    output.write_text("\n".join(elements), encoding="utf-8", newline="\n")
    return output


def assemble_brand_page_svg(
    *,
    output: Path,
    role: str,
    onscreen_lines: list[str],
    contract: dict | None = None,
    page_number: int | None = None,
) -> Path:
    """Materialize a native structural page from the CEC template assets."""

    if role not in {"cover", "contents", "chapter", "closing"}:
        raise ValueError(f"unsupported brand page role: {role}")
    loaded = contract or load_template_contract()
    template_root = loaded["root"]
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [line.strip() for line in onscreen_lines if line.strip()]

    def numbered_entry(line: str, fallback: str) -> tuple[str, str]:
        match = re.match(r"^(\d{1,2})\s*(?:[：:、.｜|\-—]\s*)?(.+)$", line)
        return (match.group(1).zfill(2), match.group(2).strip()) if match else (fallback, line)

    def copy_asset(name: str) -> str:
        source = template_root / name
        target = output.parent / name
        shutil.copy2(source, target)
        return target.name

    def template_chrome() -> str:
        return "\n".join(_render_chrome(
            rules=loaded["rules"], logo_href=copy_asset("logo.png"),
            title="", subtitle="", page_number=int(page_number or 0),
        )[1:6])

    def write_brand_svg(markup: str) -> None:
        # Separate master families keep cover/navigation art independent from
        # content-page chrome, while all variants use the structured exporter.
        root = ET.fromstring(markup)
        for key, value in {
            "data-pptx-master": f"cec-{role}",
            "data-pptx-master-name": f"CEC {role.title()} Master",
            "data-pptx-layout": f"cec-{role}",
            "data-pptx-layout-name": f"CEC {role.title()}",
        }.items():
            root.set(key, value)
        for index, child in enumerate(root):
            if (_local_tag(child) in {"rect", "image"}
                    and child.get("x", "0") == "0" and child.get("y", "0") == "0"
                    and child.get("width") == str(CANVAS_WIDTH)
                    and child.get("height") == str(CANVAS_HEIGHT)):
                child.set("id", child.get("id") or f"brandBackground{index}")
                child.set("data-pptx-layer", "master")
        definitions = [child for child in root if _local_tag(child) == "defs"]
        master = [child for child in root if child.get("data-pptx-layer") == "master"]
        content = [child for child in root if child not in definitions and child not in master]
        root[:] = definitions + master + content
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
        output.write_text(ET.tostring(root, encoding="unicode") + "\n", encoding="utf-8")

    if role == "cover":
        copy_asset("cover_bg.jpg")
        template = (template_root / "01_cover.svg").read_text(encoding="utf-8")
        template = template.replace("{{TITLE}}", xml_escape(lines[0] if lines else ""))
        template = template.replace("{{AUTHOR}}", xml_escape(lines[1] if len(lines) > 1 else ""))
        template = template.replace("{{DATE}}", xml_escape(lines[2] if len(lines) > 2 else ""))
        write_brand_svg(template)
        return output

    if role in {"contents", "chapter"}:
        template_name = "02_agenda.svg" if role == "contents" else "03_section.svg"
        background_name = "agenda_bg.png" if role == "contents" else "section_bg.png"
        copy_asset(background_name)
        template = (template_root / template_name).read_text(encoding="utf-8")
        if role == "contents":
            agenda_items = "\n".join(
                "\n".join(
                    [
                        f'<g class="agenda-item-card" data-index="{index + 1}">',
                        f'<rect x="{74 + (index % 2) * 566}" y="{210 + (index // 2) * 118}" width="536" height="94" fill="#FFFFFF" fill-opacity="0.84" stroke="#C8D5E5" stroke-width="1"/>',
                        f'<rect x="{74 + (index % 2) * 566}" y="{210 + (index // 2) * 118}" width="58" height="94" fill="#123B66"/>',
                        f'<text x="{103 + (index % 2) * 566}" y="{266 + (index // 2) * 118}" text-anchor="middle" font-family="Consolas, Arial, sans-serif" font-size="20" font-weight="700" fill="#FFFFFF">{numbered_entry(line, f"{index + 1:02d}")[0]}</text>',
                        f'<text x="{156 + (index % 2) * 566}" y="{266 + (index // 2) * 118}" font-family={quoteattr(TEMPLATE_FONT_FAMILY)} font-size="21" font-weight="700" fill="#123B66">{xml_escape(numbered_entry(line, f"{index + 1:02d}")[1])}</text>',
                        "</g>",
                    ]
                )
                for index, line in enumerate(lines[1:7])
            )
            template = template.replace("{{AGENDA_ITEMS}}", agenda_items)
        else:
            if lines and re.fullmatch(r"\d{1,2}", lines[0]) and len(lines) > 1:
                section_no, section_title, subtitle = lines[0].zfill(2), lines[1], lines[2] if len(lines) > 2 else ""
            else:
                section_no, section_title = numbered_entry(lines[0] if lines else "章节", "章节导览")
                subtitle = lines[1] if len(lines) > 1 else ""
            template = template.replace("{{SECTION_NO}}", xml_escape(section_no))
            template = template.replace("{{SECTION_TITLE}}", xml_escape(section_title))
            template = template.replace("{{SECTION_SUBTITLE}}", xml_escape(subtitle))
        template = template.replace("</svg>", f"{template_chrome()}\n</svg>")
        write_brand_svg(template)
        return output

    # The ending page can carry a project-specific decision request, so its
    # title and supporting line remain authored here while sharing the CEC
    # closing background.  The generic ``04_ending.svg`` remains available for
    # decks that intentionally use its fixed “感谢聆听 / THANK YOU” copy.
    href = copy_asset("cover_bg.jpg")
    title = lines[0] if lines else "请审议"
    subtitle = lines[1] if len(lines) > 1 else ""
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}" data-brand-template={quoteattr(role)}>',
        f'<image x="0" y="0" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" href={quoteattr(href)} preserveAspectRatio="xMidYMid slice"/>',
    ]
    elements.extend(
        [
            f'<text x="640" y="240" text-anchor="middle" font-family={quoteattr(TEMPLATE_FONT_FAMILY)} font-size="44" font-weight="700" fill="#1F2933">{xml_escape(title)}</text>',
            f'<text x="640" y="320" text-anchor="middle" font-family={quoteattr(TEMPLATE_FONT_FAMILY)} font-size="27" fill="#60758A">{xml_escape(subtitle)}</text>',
            f'<text x="640" y="620" text-anchor="middle" font-family={quoteattr(TEMPLATE_FONT_FAMILY)} font-size="24" fill="#FFFFFF" fill-opacity="0.85">中国电力企业联合会</text>',
        ]
    )
    elements.append("</svg>\n")
    write_brand_svg("\n".join(elements))
    return output


def assemble_template_pptx(svg_files: list[Path], output: Path, *, notes: dict[str, str] | None = None) -> Path:
    """Export wrapped template SVGs through the existing native builder."""

    output.parent.mkdir(parents=True, exist_ok=True)
    ok = create_pptx_with_native_svg(
        svg_files,
        output,
        verbose=False,
        use_compat_mode=False,
        use_native_shapes=True,
        pptx_structure="structured",
        # Defaults for new inherited text; authored page metrics stay explicit.
        master_text_style_spec=MasterTextStyleSpec(title_hpt=2400, body_hpt=1350),
        text_flow="split",
        notes=notes,
        enable_notes=notes is not None,
    )
    if not ok:
        raise RuntimeError(f"template SVG/PPTX export failed: {output}")
    return output
