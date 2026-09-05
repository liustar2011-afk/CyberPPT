"""One-pass validation for an editable Stage 02 page."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

from .clean_base_policy import validate_clean_base
from .graphic_text_policy import validate_graphic_text_policy


SCHEMA = "cyberppt.stage02.editable_page_qa.v1"


def _svg_evidence(path: Path) -> tuple[list[str], list[str]]:
    root = ET.parse(path).getroot()
    texts: list[str] = []
    hrefs: list[str] = []
    for node in root.iter():
        local = node.tag.rsplit("}", 1)[-1]
        if local == "text":
            value = re.sub(r"\s+", " ", "".join(node.itertext())).strip()
            if value:
                texts.append(value)
        elif local == "image":
            href = node.attrib.get("href") or node.attrib.get("{http://www.w3.org/1999/xlink}href")
            if href:
                hrefs.append(href)
    return texts, hrefs


def validate_editable_page(
    *,
    clean_base: Mapping[str, Any] | None,
    full_image: Path | str,
    authored_svg: Path | str,
    graphic_text_policy: Mapping[str, Any] | None,
    page_number: int,
    require_exact_fidelity: bool = False,
) -> dict[str, Any]:
    """Validate clean base and text policy from one parsed authored SVG."""

    svg_path = Path(authored_svg).expanduser().resolve()
    evidence_error: str | None = None
    try:
        svg_texts, image_hrefs = _svg_evidence(svg_path)
    except (OSError, ET.ParseError) as exc:
        svg_texts, image_hrefs = [], []
        evidence_error = str(exc)
    clean = validate_clean_base(
        clean_base,
        full_image=full_image,
        authored_svg=svg_path,
        graphic_text_policy=graphic_text_policy,
        page_number=page_number,
        image_hrefs=image_hrefs,
    )
    policy = validate_graphic_text_policy(
        graphic_text_policy,
        authored_svg=svg_path,
        page_number=page_number,
        svg_text_values=svg_texts,
        image_href_values=image_hrefs,
        source_image=full_image,
        require_exact_fidelity=require_exact_fidelity,
    )
    errors: list[dict[str, str]] = []
    if evidence_error:
        errors.append({"code": "invalid_authored_svg", "message": evidence_error})
    errors.extend(dict(item) for item in clean.get("errors", []))
    errors.extend(dict(item) for item in policy.get("errors", []))
    return {
        "schema": SCHEMA,
        "page_number": page_number,
        "valid": not errors,
        "clean_base": clean,
        "graphic_text_policy": policy,
        "svg_text_count": len(svg_texts),
        "image_layer_count": len(image_hrefs),
        "errors": errors,
    }
