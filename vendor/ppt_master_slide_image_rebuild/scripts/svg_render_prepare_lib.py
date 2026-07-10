"""Shared SVG preparation for preview rendering (inline icons, resolve hrefs)."""

from __future__ import annotations

import hashlib
import logging
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

_FINALIZE_DIR = _SCRIPTS_DIR / "svg_finalize"
if str(_FINALIZE_DIR) not in sys.path:
    sys.path.insert(0, str(_FINALIZE_DIR))

from embed_icons import (  # noqa: E402
    extract_paths_from_icon,
    generate_icon_group,
    parse_use_element,
    resolve_icon_path,
)

try:
    from shared_ppt_resources import icons_dir as resolve_shared_icons_dir  # noqa: E402
except ImportError:  # pragma: no cover
    resolve_shared_icons_dir = None

_ICONS_DIR = (
    resolve_shared_icons_dir()
    if resolve_shared_icons_dir is not None
    else _SCRIPTS_DIR.parent / "templates" / "icons"
)
_USE_ICON_PATTERN = re.compile(r'<use\s+[^>]*data-icon="[^"]*"[^>]*/>')
_HREF_PATTERN = re.compile(
    r'((?:xlink:)?href=")([^"]+)(")',
    re.IGNORECASE,
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inline_data_icons(content: str) -> tuple[str, list[dict[str, str]]]:
    """Replace ``<use data-icon=.../>`` with rendered ``<g>`` groups."""
    warnings: list[dict[str, str]] = []
    matches = list(_USE_ICON_PATTERN.finditer(content))
    if not matches:
        return content, warnings
    new_content = content
    for match in reversed(matches):
        use_str = match.group(0)
        icon_name = ""
        try:
            attrs = parse_use_element(use_str)
            icon_name = str(attrs.get("icon") or "")
            if not icon_name:
                warnings.append({"icon": "", "reason": "missing data-icon attribute"})
                continue
            icon_path, _ = resolve_icon_path(icon_name, _ICONS_DIR)
            color = str(attrs.get("fill", "#000000"))
            elements, style, base_size = extract_paths_from_icon(icon_path, color)
        except Exception as exc:  # noqa: BLE001
            warnings.append({"icon": icon_name, "reason": f"{type(exc).__name__}: {exc}"})
            logger.warning("icon inline failed: name=%r reason=%s", icon_name, exc)
            continue
        if not elements:
            warnings.append({"icon": icon_name, "reason": "no renderable paths in icon"})
            continue
        replacement = generate_icon_group(attrs, elements, style, base_size)
        id_match = re.search(r'\bid="([^"]+)"', use_str)
        if id_match:
            replacement = replacement.replace(
                "<g ",
                f'<g id="{id_match.group(1)}" data-icon="{icon_name}" ',
                1,
            )
        new_content = new_content[: match.start()] + replacement + new_content[match.end() :]
    return new_content, warnings


def resolve_relative_hrefs(content: str, svg_path: Path) -> str:
    """Rewrite relative image hrefs to absolute file URLs for off-directory render-ready SVG."""

    def _replace(match: re.Match[str]) -> str:
        prefix, href, suffix = match.group(1), match.group(2), match.group(3)
        if href.startswith(("http://", "https://", "data:", "file:")):
            return match.group(0)
        target = (svg_path.parent / href).resolve()
        if target.is_file():
            return f'{prefix}{target.as_uri()}{suffix}'
        return match.group(0)

    return _HREF_PATTERN.sub(_replace, content)


def _strip_element_namespace(elem: ET.Element) -> None:
    """Remove Clark notation from element namespace for SVG rendering compatibility."""
    if "}" in elem.tag:
        elem.tag = elem.tag.split("}", 1)[1]
    stripped_attribs = {
        (key.split("}", 1)[1] if "}" in key else key): value for key, value in elem.attrib.items()
    }
    elem.attrib.clear()
    elem.attrib.update(stripped_attribs)
    for child in elem:
        _strip_element_namespace(child)


def prepare_svg_content(svg_path: Path) -> tuple[str, list[dict[str, str]]]:
    """Parse SVG, inline icons, absolutize image hrefs; return UTF-8 SVG document string."""
    raw = svg_path.read_text(encoding="utf-8")
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        _strip_element_namespace(root)
        if root.tag == "svg" and not root.get("xmlns"):
            root.set("xmlns", "http://www.w3.org/2000/svg")
        content = ET.tostring(root, encoding="unicode", xml_declaration=False)
    except ET.ParseError:
        content = raw
    content, warnings = inline_data_icons(content)
    content = resolve_relative_hrefs(content, svg_path)
    if not content.lstrip().startswith("<"):
        content = f'<svg xmlns="http://www.w3.org/2000/svg">{content}</svg>'
    return content, warnings
