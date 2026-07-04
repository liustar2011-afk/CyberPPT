"""Deck-wide brand chrome via slide-layout injection (not per-page SVG drawing).

A chrome-only brand (e.g. templates/brands/中电联公共元素_轻量版/) declares public
elements — header divider, logo, footer bar, org name, page number — that must
appear on every body page. Earlier this skill told Executor to hand-draw those
into every page's SVG; that duplicates the same shapes dozens of times, is the
opposite of how PPTX is supposed to work, and is one missed page away from a
silently-broken deck. This module instead repurposes one of python-pptx's
built-in slide layouts as a "chrome layout": the chrome shapes (including a
native `sldNum` placeholder, so the page number is a real auto-updating PPTX
field, not literal per-page text) live once in that layout's XML; every body
slide that uses the layout inherits them for free, and editing the layout
later edits every slide at once — the actual PPTX master/layout mechanism.

Two-step usage:
    1. ``read_master_chrome(project_path)`` — parse ``spec_lock.md`` (+ the
       locked brand's ``brand_rules.json`` for the cover/ending exclusion) into
       a plain dict, or ``None`` if no chrome-only brand is locked.
    2. ``inject_chrome_layout(extract_dir, prs, chrome, layout_idx, project_path)``
       — after ``Presentation.save()`` + zip-extract (the point where this
       codebase already does raw XML post-processing for notes slides etc.),
       rewrite the repurposed layout's XML in place and copy the logo into its
       own media folder + relationship.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

EMU_PER_PX = 9525  # 914400 EMU/inch / 96 px/inch


def _px_to_emu(px: float) -> int:
    return round(px * EMU_PER_PX)


def _parse_kv_geometry(line: str) -> dict[str, float]:
    """Parse ``rect x=0 y=82 w=1280 h=7 fill=#8B0000`` style fragments into a dict."""
    out: dict[str, Any] = {}
    for key, val in re.findall(r'(\w+)=("[^"]*"|\S+)', line):
        val = val.strip('"')
        if re.fullmatch(r'-?\d+(\.\d+)?', val):
            out[key] = float(val)
        else:
            out[key] = val
    return out


def strip_full_canvas_background(svg_text: str, width: int, height: int) -> str:
    """Remove the page's own full-canvas opaque background rect.

    Every page SVG in this pipeline conventionally opens with
    ``<rect x="0" y="0" width="<canvas_w>" height="<canvas_h>" fill="#FFFFFF"/>``
    as its very first shape (see CHART_STYLE_GUIDE.md §5.3). On a body page
    that uses the injected chrome layout, that rect — once converted to a
    slide shape — paints on top of the *layout's* chrome (PPTX always
    z-orders slide content above its layout), silently hiding the header
    divider, logo, and footer bar even though they are correctly present in
    the file. The layout itself carries its own full-canvas white background
    behind the chrome (see ``inject_chrome_layout``), so the slide doesn't
    need one — stripping this single boilerplate rect is sufficient; no
    change to how the rest of the page is authored is required.

    Removes only the *first* rect matching the exact canvas-covering
    geometry, attribute order independent; leaves every other shape
    (including same-sized rects further down, if any) untouched.
    """
    def attrs(tag: str) -> dict[str, str]:
        return dict(re.findall(r'(\w[\w:-]*)\s*=\s*"([^"]*)"', tag))

    for m in re.finditer(r'<rect\b[^/>]*/?>', svg_text):
        a = attrs(m.group(0))
        try:
            if (float(a.get('x', 'nan')) == 0 and float(a.get('y', 'nan')) == 0
                    and float(a.get('width', 'nan')) == float(width)
                    and float(a.get('height', 'nan')) == float(height)):
                return svg_text[:m.start()] + svg_text[m.end():]
        except ValueError:
            continue
    return svg_text


def read_master_chrome(project_path: Path) -> dict[str, Any] | None:
    """Parse ``spec_lock.md §master_chrome`` (+ brand cover/ending exclusion).

    Returns ``None`` when no chrome-only brand is locked (the common case) —
    callers should skip layout injection entirely in that case.
    """
    spec_lock = project_path / 'spec_lock.md'
    if not spec_lock.exists():
        return None
    text = spec_lock.read_text(encoding='utf-8')

    m = re.search(r'^## master_chrome\n(.*?)(?=\n##|\Z)', text, re.S | re.M)
    if not m:
        return None
    body = m.group(1)

    chrome: dict[str, Any] = {}
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith('- '):
            continue
        line = line[2:]
        if ':' not in line:
            continue
        key, _, rest = line.partition(':')
        key, rest = key.strip(), rest.strip()
        if key in ('top_divider', 'footer_bar', 'logo'):
            chrome[key] = _parse_kv_geometry(rest)
        elif key == 'footer_org_text':
            geo = _parse_kv_geometry(rest)
            text_m = re.search(r'text="([^"]*)"', rest)
            geo['text'] = text_m.group(1) if text_m else ''
            chrome[key] = geo
        elif key == 'footer_page_num':
            chrome[key] = _parse_kv_geometry(rest)
        elif key == 'protected_region':
            chrome.setdefault('protected_regions', []).append(_parse_kv_geometry(rest))

    if not chrome:
        return None

    chrome['excluded_pages'] = _resolve_excluded_pages(project_path, text)
    return chrome


def _resolve_excluded_pages(project_path: Path, spec_lock_text: str) -> set[int]:
    """Page numbers whose ``page_layouts`` entry resolves to the locked brand's
    own cover/ending template — these must NOT get the chrome layout.
    """
    excluded: set[int] = set()

    brand_template_basenames: set[str] = set()
    brand_rules_path = project_path / 'templates' / 'brand_rules.json'
    if brand_rules_path.exists():
        import json
        try:
            rules = json.loads(brand_rules_path.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            rules = {}
        for entry in (rules.get('brand_page_templates') or {}).values():
            fname = entry.get('file') if isinstance(entry, dict) else None
            if fname:
                brand_template_basenames.add(Path(fname).stem)

    if not brand_template_basenames:
        return excluded

    m = re.search(r'^## page_layouts\n(.*?)(?=\n##|\Z)', spec_lock_text, re.S | re.M)
    if not m:
        return excluded
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith('- '):
            continue
        page_m = re.match(r'-\s*P(\d+)\s*:\s*(\S+)', line)
        if not page_m:
            continue
        page_num, basename = int(page_m.group(1)), page_m.group(2)
        if basename in brand_template_basenames:
            excluded.add(page_num)
    return excluded


def _shape_xml(shape_id: int, name: str, geo: dict, fill_hex: str) -> str:
    x, y = _px_to_emu(geo['x']), _px_to_emu(geo['y'])
    w, h = _px_to_emu(geo['w']), _px_to_emu(geo['h'])
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/>'
        f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{fill_hex.lstrip("#")}"/></a:solidFill>'
        f'<a:ln><a:noFill/></a:ln></p:spPr>'
        f'<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>'
    )


def _text_shape_xml(shape_id: int, name: str, geo: dict, text: str, font_px: float,
                     fill_hex: str = 'FFFFFF', align: str = 'l',
                     font_family: str | None = None) -> str:
    x, y = _px_to_emu(geo['x']), _px_to_emu(geo.get('y', 0))
    w, h = _px_to_emu(geo.get('w', 200)), _px_to_emu(geo.get('h', 24))
    sz = round(font_px * 100)
    font_tags = (
        f'<a:latin typeface="{escape(font_family)}"/><a:ea typeface="{escape(font_family)}"/>'
        if font_family else ''
    )
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/>'
        f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
        f'<p:txBody><a:bodyPr anchor="ctr" lIns="0" tIns="0" rIns="0" bIns="0"/><a:lstStyle/>'
        f'<a:p><a:pPr algn="{align}"/><a:r><a:rPr lang="zh-CN" sz="{sz}">'
        f'<a:solidFill><a:srgbClr val="{fill_hex}"/></a:solidFill>{font_tags}</a:rPr>'
        f'<a:t>{escape(text)}</a:t></a:r></a:p></p:txBody></p:sp>'
    )


def _page_number_field_shape_xml(shape_id: int, geo: dict, footer_bar_geo: dict) -> str:
    """Create a layout-owned DrawingML slide-number field.

    The field lives on the shared chrome layout, rather than in the generated
    page SVG or an individual slide XML part. PowerPoint resolves
    ``type="slidenum"`` for every slide that inherits the layout.
    """
    geo = dict(geo)
    geo['y'], geo['h'] = footer_bar_geo.get('y', 696), footer_bar_geo.get('h', 24)
    geo.setdefault('w', 100)
    box_x = geo['x'] - geo['w']
    x, y = _px_to_emu(box_x), _px_to_emu(geo['y'])
    w, h = _px_to_emu(geo['w']), _px_to_emu(geo['h'])
    size = round(geo.get('size', 10) * 100)
    fill = str(geo.get('fill', '#FFFFFF')).lstrip('#')
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="ChromePageNumber"/>'
        f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
        f'<p:txBody><a:bodyPr anchor="ctr" lIns="0" tIns="0" rIns="0" bIns="0"/><a:lstStyle/>'
        f'<a:p><a:pPr algn="r"/><a:fld id="{{00000000-0008-0000-0000-000000000000}}" type="slidenum">'
        f'<a:rPr lang="zh-CN" sz="{size}"><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
        f'<a:latin typeface="Consolas"/><a:ea typeface="Consolas"/></a:rPr><a:t>1</a:t></a:fld>'
        f'</a:p></p:txBody></p:sp>'
    )


def _picture_xml(shape_id: int, rel_id: str, geo: dict) -> str:
    x, y = _px_to_emu(geo['x']), _px_to_emu(geo['y'])
    w, h = _px_to_emu(geo['w']), _px_to_emu(geo['h'])
    return (
        f'<p:pic><p:nvPicPr><p:cNvPr id="{shape_id}" name="ChromeLogo"/>'
        f'<p:cNvPicPr/><p:nvPr/></p:nvPicPr>'
        f'<p:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
    )


def inject_chrome_layout(
    extract_dir: Path,
    layout_partname: str,
    chrome: dict[str, Any],
    logo_src: Path | None,
) -> None:
    """Rewrite the repurposed layout's XML + rels to carry the chrome shapes.

    ``layout_partname`` is the python-pptx ``layout.part.partname`` string
    (e.g. ``/ppt/slideLayouts/slideLayout6.xml``) captured *before*
    ``Presentation.save()`` — partnames are stable across save, so it
    resolves directly to a file under ``extract_dir``.
    """
    layout_path = extract_dir / layout_partname.lstrip('/')
    rels_path = layout_path.parent / '_rels' / f'{layout_path.name}.rels'

    shapes_xml = []
    shape_id = 99
    # Layout-level white background, painted first (bottom of z-order) so the
    # canvas reads white even though the per-page slide's own background rect
    # is stripped (see strip_full_canvas_background) to let this layout's
    # chrome show through instead of being painted over.
    canvas_w = chrome.get('canvas_width', 1280)
    canvas_h = chrome.get('canvas_height', 720)
    shapes_xml.append(_shape_xml(shape_id, 'ChromeCanvasBackground',
                                  {'x': 0, 'y': 0, 'w': canvas_w, 'h': canvas_h}, '#FFFFFF'))
    shape_id += 1
    if 'top_divider' in chrome:
        shapes_xml.append(_shape_xml(shape_id, 'ChromeTopDivider', chrome['top_divider'],
                                      chrome['top_divider'].get('fill', '#8B0000')))
        shape_id += 1
    if 'footer_bar' in chrome:
        shapes_xml.append(_shape_xml(shape_id, 'ChromeFooterBar', chrome['footer_bar'],
                                      chrome['footer_bar'].get('fill', '#003366')))
        shape_id += 1

    rel_id = None
    if 'logo' in chrome and logo_src and logo_src.exists():
        media_dir = extract_dir / 'ppt' / 'media'
        media_dir.mkdir(parents=True, exist_ok=True)
        dest_name = f'chrome_logo{logo_src.suffix}'
        shutil.copyfile(logo_src, media_dir / dest_name)
        rel_id = 'rIdChromeLogo'
        shapes_xml.append(_picture_xml(shape_id, rel_id, chrome['logo']))
        shape_id += 1

    # footer_org_text / footer_page_num geometry in spec_lock carries a text
    # *baseline* x/y (e.g. "x=40 y=712", matching the original SVG <text>
    # convention), not a box. Anchoring a box's top-left at that baseline
    # (as a naive box would) pushes a centered box's actual center well below
    # the baseline — for a footer sitting near the canvas edge, that overflows
    # past the slide boundary entirely and the text silently never renders.
    # Vertically, align both to the footer_bar's own band instead (its y/h are
    # already a proper box); only x (and text/fill/size) come from each
    # field's own geometry.
    footer_band = chrome.get('footer_bar', {})
    band_y = footer_band.get('y', 696)
    band_h = footer_band.get('h', 24)

    if 'footer_org_text' in chrome:
        geo = dict(chrome['footer_org_text'])
        geo['y'], geo['h'] = band_y, band_h
        geo.setdefault('w', 400)
        shapes_xml.append(_text_shape_xml(
            shape_id, 'ChromeFooterOrgText', geo, geo.get('text', ''),
            font_px=geo.get('size', 10), fill_hex=str(geo.get('fill', '#FFFFFF')).lstrip('#'),
            font_family='Microsoft YaHei',
        ))
        shape_id += 1

    if 'footer_page_num' in chrome:
        shapes_xml.append(_page_number_field_shape_xml(
            shape_id, chrome['footer_page_num'], footer_band,
        ))
        shape_id += 1

    new_sp_tree_extra = ''.join(shapes_xml)

    xml = layout_path.read_text(encoding='utf-8')
    # Insert the chrome shapes just before </p:spTree>, after whatever
    # placeholder shapes the repurposed layout already had (Title/Date/Footer
    # placeholders are left in place but unused — empty placeholders render no
    # prompt text outside PowerPoint's edit view).
    xml = xml.replace('</p:spTree>', new_sp_tree_extra + '</p:spTree>', 1)
    layout_path.write_text(xml, encoding='utf-8')

    if rel_id:
        if rels_path.exists():
            rels_xml = rels_path.read_text(encoding='utf-8')
        else:
            rels_path.parent.mkdir(parents=True, exist_ok=True)
            rels_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '</Relationships>'
            )
        new_rel = (
            f'<Relationship Id="{rel_id}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            f'Target="../media/chrome_logo{logo_src.suffix}"/>'
        )
        rels_xml = rels_xml.replace('</Relationships>', new_rel + '</Relationships>', 1)
        rels_path.write_text(rels_xml, encoding='utf-8')
