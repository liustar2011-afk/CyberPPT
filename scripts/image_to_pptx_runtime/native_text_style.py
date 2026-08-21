"""Default source-derived styling for editable SVG text layers.

The image-to-editable route keeps authored SVGs as the source of geometry and
copy.  This module supplies a conservative default for authored text that
does not carry a locked style: preserve authored coordinates and font sizes,
make short headings editorial blue/bold, and split ``label：sentence`` text
into editable styled runs.  A root ``data-cyberppt-native-text-style=locked``
attribute is an explicit opt-out for pages whose authored SVG already owns its
text styling.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SVG_NS = "http://www.w3.org/2000/svg"
STYLE_ATTR = "data-cyberppt-native-text-style"
DEFAULT_PROFILE = "editorial-source-text-v1"
NAVY = "#12355B"
BODY = "#202020"
FONT_STACK = "Microsoft YaHei, SimHei, Arial, sans-serif"
_HEADING_RE = re.compile(r"^【[^】]+】$|^[^：:，。！？]{2,16}$")


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _svg_tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def _is_heading(text: str) -> bool:
    return bool(_HEADING_RE.fullmatch(text.strip()))


def _set_if_missing(element: ET.Element, key: str, value: str) -> bool:
    if element.get(key) is not None:
        return False
    element.set(key, value)
    return True


def _split_label_text(element: ET.Element, text: str) -> bool:
    if "：" not in text or len(list(element)):
        return False
    label, body = text.split("：", 1)
    if not label.strip() or not body.strip():
        return False
    element.text = None
    label_node = ET.SubElement(element, _svg_tag("tspan"))
    label_node.set("fill", NAVY)
    label_node.set("font-weight", "700")
    label_node.text = f"{label}："
    body_node = ET.SubElement(element, _svg_tag("tspan"))
    body_node.set("fill", BODY)
    body_node.set("font-weight", "400")
    body_node.text = body
    return True


def apply_default_native_text_style(
    svg_path: Path | str,
    *,
    profile: str = DEFAULT_PROFILE,
) -> dict[str, Any]:
    """Apply the default editable-text style contract in place.

    Existing coordinates, font sizes, line positions, and authored ``tspan``
    styles are preserved.  The operation is idempotent and returns a compact
    QA receipt for the Stage 02 production report.
    """

    path = Path(svg_path).expanduser().resolve()
    tree = ET.parse(path)
    root = tree.getroot()
    locked = root.get(STYLE_ATTR) == "locked"
    text_nodes = [node for node in root.iter() if _local_name(node) == "text"]
    receipt: dict[str, Any] = {
        "schema": "cyberppt.native_text_style.v1",
        "profile": "locked" if locked else profile,
        "path": str(path),
        "text_count": len(text_nodes),
        "changed": False,
        "split_label_count": 0,
        "styled_heading_count": 0,
        "preserved_locked": locked,
    }
    if locked:
        return receipt

    ET.register_namespace("", SVG_NS)
    changed = root.get(STYLE_ATTR) != profile
    root.set(STYLE_ATTR, profile)
    for node in text_nodes:
        changed = _set_if_missing(node, "font-family", FONT_STACK) or changed
        text = "".join(node.itertext()).strip()
        if not text:
            continue
        if _split_label_text(node, text):
            receipt["split_label_count"] += 1
            changed = True
            continue
        if len(list(node)):
            continue
        if _is_heading(text):
            if node.get("fill") != NAVY:
                node.set("fill", NAVY)
                changed = True
            if node.get("font-weight") != "700":
                node.set("font-weight", "700")
                changed = True
            receipt["styled_heading_count"] += 1
        else:
            changed = _set_if_missing(node, "fill", BODY) or changed
            changed = _set_if_missing(node, "font-weight", "400") or changed

    receipt["changed"] = changed
    if changed:
        tree.write(path, encoding="utf-8", xml_declaration=False)
    return receipt


def write_native_text_style_receipt(
    reports: list[dict[str, Any]],
    output_path: Path | str,
) -> Path:
    """Persist the per-page default text-style QA receipt."""

    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "cyberppt.native_text_style_qa.v1",
                "profile": DEFAULT_PROFILE,
                "pages": reports,
                "valid": all(
                    report.get("profile")
                    for report in reports
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path
