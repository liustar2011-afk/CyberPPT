#!/usr/bin/env python3
"""
PPT Master - PPTX Package Sanitizer

Validate and clean common OOXML package issues before PowerPoint/WPS opens a
generated PPTX.

Usage:
    python3 scripts/sanitize_pptx_package.py <pptx_or_extracted_dir> [--in-place]

Examples:
    python3 scripts/sanitize_pptx_package.py projects/demo/exports/deck.pptx --in-place
    python3 scripts/sanitize_pptx_package.py /tmp/pptx_content --report compat_report.json

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import posixpath
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

ET.register_namespace("", PKG_REL_NS)
ET.register_namespace("", CT_NS)
ET.register_namespace("p", P_NS)
ET.register_namespace("a", "http://schemas.openxmlformats.org/drawingml/2006/main")
ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")

REL = f"{{{PKG_REL_NS}}}Relationship"
DEFAULT = f"{{{CT_NS}}}Default"
OVERRIDE = f"{{{CT_NS}}}Override"
SLD_SZ = f"{{{P_NS}}}sldSz"
MAJOR_FONT = f"{{{A_NS}}}majorFont"
MINOR_FONT = f"{{{A_NS}}}minorFont"
LATIN = f"{{{A_NS}}}latin"
EA = f"{{{A_NS}}}ea"
CS = f"{{{A_NS}}}cs"
SP = f"{{{P_NS}}}sp"
SP_PR = f"{{{P_NS}}}spPr"
XFRM = f"{{{A_NS}}}xfrm"
OFF = f"{{{A_NS}}}off"
EXT = f"{{{A_NS}}}ext"
PRST_GEOM = f"{{{A_NS}}}prstGeom"
SRGB_CLR = f"{{{A_NS}}}srgbClr"

MEDIA_CONTENT_TYPES = {
    "bmp": "image/bmp",
    "emf": "image/x-emf",
    "gif": "image/gif",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "png": "image/png",
    "svg": "image/svg+xml",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "wav": "audio/wav",
    "webp": "image/webp",
    "wmf": "image/x-wmf",
}

PART_OVERRIDES = {
    "ppt/notesSlides/notesSlide": "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml",
    "ppt/slides/slide": "application/vnd.openxmlformats-officedocument.presentationml.slide+xml",
}

DROP_REL_TYPE_TOKENS = (
    "/printerSettings",
)


@dataclass
class Finding:
    level: str
    code: str
    message: str
    path: str = ""

    def as_dict(self) -> dict[str, str]:
        payload = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.path:
            payload["path"] = self.path
        return payload


def _read_xml(path: Path) -> ET.Element | None:
    try:
        return ET.parse(path).getroot()
    except ET.ParseError:
        return None


def _source_part_from_rels(rels_name: str) -> str:
    if rels_name == "_rels/.rels":
        return ""
    return rels_name.replace("/_rels/", "/")[:-5]


def _resolve_target(source_part: str, target: str) -> str:
    if source_part:
        base = posixpath.dirname(source_part)
        return posixpath.normpath(posixpath.join(base, target))
    return posixpath.normpath(target.lstrip("/"))


def _is_external(rel: ET.Element) -> bool:
    return rel.get("TargetMode") == "External"


def _should_drop_rel(rel: ET.Element, target_exists: bool) -> bool:
    rel_type = rel.get("Type", "")
    target = rel.get("Target", "")
    if not target.strip():
        return True
    if any(token in rel_type for token in DROP_REL_TYPE_TOKENS):
        return True
    if "/notesSlide" in rel_type and not target_exists:
        return True
    return False


def _write_xml(path: Path, root: ET.Element) -> None:
    # ET.register_namespace("", uri) keeps only the LAST uri registered for the
    # empty prefix (earlier mappings are deleted), so module-level registration
    # is unreliable: rels/content-types parts then serialize as `ns0:` —
    # PowerPoint's OPC reader rejects prefixed names there and offers repair.
    # Re-register the document's own namespace as default right before writing.
    if root.tag.startswith("{"):
        ns = root.tag[1:].split("}", 1)[0]
        if ns in (PKG_REL_NS, CT_NS):
            ET.register_namespace("", ns)
    tree = ET.ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def apply_wps_cn_theme_fonts(root_dir: Path) -> dict[str, Any]:
    """Apply WPS-friendly Chinese font declarations to package theme files."""
    theme_dir = root_dir / "ppt" / "theme"
    summary: dict[str, Any] = {
        "font": "微软雅黑",
        "theme_files": 0,
        "updated_theme_files": 0,
        "font_slots_touched": 0,
        "theme_cn_font_count": 0,
        "errors": [],
    }
    if not theme_dir.is_dir():
        return summary
    for theme_path in sorted(theme_dir.glob("theme*.xml")):
        summary["theme_files"] += 1
        try:
            tree = ET.parse(theme_path)
        except ET.ParseError as exc:
            summary["errors"].append(f"{theme_path.relative_to(root_dir).as_posix()}: {exc}")
            continue
        root = tree.getroot()
        changed = False
        for font_group in root.findall(f".//{MAJOR_FONT}") + root.findall(f".//{MINOR_FONT}"):
            for tag in [LATIN, EA, CS]:
                elem = font_group.find(tag)
                if elem is None:
                    elem = ET.SubElement(font_group, tag)
                if elem.get("typeface") != "微软雅黑":
                    elem.set("typeface", "微软雅黑")
                    summary["font_slots_touched"] += 1
                    changed = True
        if changed:
            _write_xml(theme_path, root)
            summary["updated_theme_files"] += 1
        try:
            summary["theme_cn_font_count"] += theme_path.read_text(encoding="utf-8").count("微软雅黑")
        except OSError:
            pass
    return summary


def _inspect_wps_cn_theme_fonts(root_dir: Path) -> dict[str, Any]:
    theme_dir = root_dir / "ppt" / "theme"
    summary: dict[str, Any] = {
        "font": "微软雅黑",
        "theme_files": 0,
        "theme_cn_font_count": 0,
    }
    if not theme_dir.is_dir():
        return summary
    for theme_path in sorted(theme_dir.glob("theme*.xml")):
        summary["theme_files"] += 1
        try:
            summary["theme_cn_font_count"] += theme_path.read_text(encoding="utf-8").count("微软雅黑")
        except OSError:
            pass
    return summary


def _iter_package_files(root_dir: Path) -> list[str]:
    files: list[str] = []
    for path in root_dir.rglob("*"):
        if path.is_file():
            files.append(path.relative_to(root_dir).as_posix())
    return sorted(files)


def _sanitize_relationships(root_dir: Path, findings: list[Finding]) -> int:
    removed = 0
    file_names = set(_iter_package_files(root_dir))
    for rels_path in root_dir.rglob("*.rels"):
        rels_name = rels_path.relative_to(root_dir).as_posix()
        root = _read_xml(rels_path)
        if root is None:
            findings.append(Finding("error", "invalid_rels_xml", "Relationship XML is not parseable.", rels_name))
            continue
        source_part = _source_part_from_rels(rels_name)
        changed = False
        for rel in list(root.findall(REL)):
            target = rel.get("Target", "")
            if _is_external(rel):
                continue
            resolved = _resolve_target(source_part, target)
            exists = resolved in file_names
            if _should_drop_rel(rel, exists):
                root.remove(rel)
                removed += 1
                changed = True
                findings.append(Finding(
                    "warning",
                    "removed_stale_relationship",
                    f"Removed stale relationship {rel.get('Id', '')} -> {target or '<empty>'}.",
                    rels_name,
                ))
                continue
            if not exists:
                findings.append(Finding(
                    "error",
                    "missing_relationship_target",
                    f"Relationship {rel.get('Id', '')} target does not exist: {target} -> {resolved}",
                    rels_name,
                ))
        if changed:
            _write_xml(rels_path, root)
    return removed


def _content_type_for_extension(ext: str) -> str | None:
    clean = ext.lower().lstrip(".")
    return MEDIA_CONTENT_TYPES.get(clean) or mimetypes.guess_type(f"x.{clean}")[0]


def _ensure_default(root: ET.Element, ext: str, content_type: str, findings: list[Finding]) -> bool:
    clean = ext.lower().lstrip(".")
    for elem in root.findall(DEFAULT):
        if elem.get("Extension", "").lower() == clean:
            return False
    ET.SubElement(root, DEFAULT, {"Extension": clean, "ContentType": content_type})
    findings.append(Finding(
        "warning",
        "added_content_type_default",
        f"Added content type for .{clean}: {content_type}",
        "[Content_Types].xml",
    ))
    return True


def _ensure_override(root: ET.Element, part_name: str, content_type: str, findings: list[Finding]) -> bool:
    normalized = "/" + part_name.lstrip("/")
    for elem in root.findall(OVERRIDE):
        if elem.get("PartName") == normalized:
            return False
    ET.SubElement(root, OVERRIDE, {"PartName": normalized, "ContentType": content_type})
    findings.append(Finding(
        "warning",
        "added_content_type_override",
        f"Added content type override for {normalized}.",
        "[Content_Types].xml",
    ))
    return True


def _sanitize_content_types(root_dir: Path, findings: list[Finding]) -> None:
    path = root_dir / "[Content_Types].xml"
    root = _read_xml(path)
    if root is None:
        findings.append(Finding("error", "invalid_content_types_xml", "Content types XML is not parseable.", str(path)))
        return
    changed = False
    # Duplicate Default/Override entries violate OPC (one declaration per
    # extension/part) and make PowerPoint reject the whole package.
    seen_defaults: set[str] = set()
    seen_overrides: set[str] = set()
    for elem in list(root):
        if elem.tag == DEFAULT:
            key = (elem.get("Extension") or "").lower()
            if key in seen_defaults:
                root.remove(elem)
                changed = True
                findings.append(Finding(
                    "warning", "removed_duplicate_content_type_default",
                    f"Removed duplicate Default for extension `{key}`.",
                    "[Content_Types].xml",
                ))
                continue
            seen_defaults.add(key)
        elif elem.tag == OVERRIDE:
            key = elem.get("PartName") or ""
            if key in seen_overrides:
                root.remove(elem)
                changed = True
                findings.append(Finding(
                    "warning", "removed_duplicate_content_type_override",
                    f"Removed duplicate Override for `{key}`.",
                    "[Content_Types].xml",
                ))
                continue
            seen_overrides.add(key)
    for file_name in _iter_package_files(root_dir):
        if file_name == "[Content_Types].xml" or file_name.endswith(".rels"):
            continue
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if file_name.startswith("ppt/media/") and ext:
            content_type = _content_type_for_extension(ext)
            if content_type:
                changed = _ensure_default(root, ext, content_type, findings) or changed
            else:
                findings.append(Finding(
                    "error",
                    "unknown_media_content_type",
                    f"Cannot infer content type for {file_name}.",
                    "[Content_Types].xml",
                ))
        for prefix, content_type in PART_OVERRIDES.items():
            if file_name.startswith(prefix) and file_name.endswith(".xml"):
                changed = _ensure_override(root, file_name, content_type, findings) or changed
    if changed:
        _write_xml(path, root)


R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
SLD_MASTER_ID_LST = f"{{{P_NS}}}sldMasterIdLst"
SLD_MASTER_ID = f"{{{P_NS}}}sldMasterId"
NOTES_MASTER_ID_LST = f"{{{P_NS}}}notesMasterIdLst"
NOTES_MASTER_ID = f"{{{P_NS}}}notesMasterId"
SLD_LAYOUT_ID_LST = f"{{{P_NS}}}sldLayoutIdLst"
SLD_LAYOUT = f"{{{P_NS}}}sldLayout"
R_ID = f"{{{R_NS}}}id"


def _normalize_opc_namespace_prefixes(root_dir: Path, findings: list[Finding]) -> None:
    """Rewrite rels/content-types parts that carry prefixed namespaces.

    PowerPoint's OPC reader rejects `ns0:Relationships` / `ns0:Types` (legal
    XML, but Office requires the default namespace there) and offers repair.
    """
    targets = [root_dir / "[Content_Types].xml", *root_dir.rglob("*.rels")]
    for path in targets:
        if not path.is_file():
            continue
        try:
            head = path.read_text(encoding="utf-8", errors="ignore")[:300]
        except OSError:
            continue
        if "<Relationships" in head or "<Types" in head:
            continue
        root = _read_xml(path)
        if root is None:
            continue
        _write_xml(path, root)
        findings.append(Finding(
            "warning",
            "normalized_opc_namespace_prefix",
            "Rewrote prefixed OPC namespace to the default namespace.",
            path.relative_to(root_dir).as_posix(),
        ))


def _remove_dropped_type_parts(root_dir: Path, findings: list[Finding]) -> None:
    """Delete parts whose relationships are dropped by DROP_REL_TYPE_TOKENS.

    Removing the relationship but keeping the part (and its content-type
    Default) leaves an orphan that some consumers flag on open.
    """
    printer_dir = root_dir / "ppt" / "printerSettings"
    if not printer_dir.is_dir():
        return
    removed = [item.name for item in sorted(printer_dir.iterdir()) if item.is_file()]
    shutil.rmtree(printer_dir)
    for name in removed:
        findings.append(Finding(
            "warning",
            "removed_orphan_printer_settings",
            f"Removed orphan part ppt/printerSettings/{name}.",
            "ppt/printerSettings",
        ))
    if any(name.endswith(".bin") for name in _iter_package_files(root_dir)):
        return
    path = root_dir / "[Content_Types].xml"
    root = _read_xml(path)
    if root is None:
        return
    for elem in list(root.findall(DEFAULT)):
        if (elem.get("Extension") or "").lower() == "bin":
            root.remove(elem)
            _write_xml(path, root)
            findings.append(Finding(
                "warning",
                "removed_unused_bin_default",
                "Removed unused bin content-type default after printerSettings cleanup.",
                "[Content_Types].xml",
            ))
            break


def _sanitize_empty_slide_masters(root_dir: Path, findings: list[Finding]) -> None:
    """Drop slide masters that declare zero layouts.

    PowerPoint expects every registered master to own at least one layout; an
    empty `p:sldLayoutIdLst` (e.g. a brand-page master scaffolded for a deck
    that never used brand layouts) triggers the repair dialog.
    """
    masters_dir = root_dir / "ppt" / "slideMasters"
    pres_path = root_dir / "ppt" / "presentation.xml"
    pres_rels_path = root_dir / "ppt" / "_rels" / "presentation.xml.rels"
    if not masters_dir.is_dir() or not pres_path.is_file() or not pres_rels_path.is_file():
        return
    masters = sorted(masters_dir.glob("slideMaster*.xml"))
    empty: list[Path] = []
    for master in masters:
        root = _read_xml(master)
        if root is None:
            continue
        layout_lst = root.find(SLD_LAYOUT_ID_LST)
        if layout_lst is None or len(list(layout_lst)) == 0:
            empty.append(master)
    if not empty or len(empty) == len(masters):
        return

    pres_root = _read_xml(pres_path)
    rels_root = _read_xml(pres_rels_path)
    ct_path = root_dir / "[Content_Types].xml"
    ct_root = _read_xml(ct_path)
    if pres_root is None or rels_root is None or ct_root is None:
        return
    pres_changed = rels_changed = ct_changed = False
    for master in empty:
        part_name = f"ppt/slideMasters/{master.name}"
        rid = None
        for rel in list(rels_root.findall(REL)):
            target = _resolve_target("ppt/presentation.xml", rel.get("Target", ""))
            if target == part_name and rel.get("Type", "").endswith("/slideMaster"):
                rid = rel.get("Id")
                rels_root.remove(rel)
                rels_changed = True
                break
        master_lst = pres_root.find(SLD_MASTER_ID_LST)
        if rid and master_lst is not None:
            for entry in list(master_lst.findall(SLD_MASTER_ID)):
                if entry.get(R_ID) == rid:
                    master_lst.remove(entry)
                    pres_changed = True
        for elem in list(ct_root.findall(OVERRIDE)):
            if elem.get("PartName") == f"/{part_name}":
                ct_root.remove(elem)
                ct_changed = True
        rels_file = masters_dir / "_rels" / f"{master.name}.rels"
        master.unlink()
        if rels_file.is_file():
            rels_file.unlink()
        findings.append(Finding(
            "warning",
            "removed_empty_slide_master",
            f"Removed slide master with no layouts: {part_name}.",
            part_name,
        ))
    if pres_changed:
        _write_xml(pres_path, pres_root)
    if rels_changed:
        _write_xml(pres_rels_path, rels_root)
    if ct_changed:
        _write_xml(ct_path, ct_root)


def _validate_slide_master_topology(root_dir: Path, findings: list[Finding]) -> None:
    """Require the generated brand layouts to use one primary slide master."""
    masters_dir = root_dir / "ppt" / "slideMasters"
    if not masters_dir.is_dir():
        return

    masters = sorted(path.name for path in masters_dir.glob("slideMaster*.xml"))
    extra_masters = [name for name in masters if name != "slideMaster1.xml"]
    for master_name in extra_masters:
        findings.append(Finding(
            "error",
            "unexpected_extra_slide_master",
            f"Generated package contains unsupported extra slide master: {master_name}.",
            f"ppt/slideMasters/{master_name}",
        ))

    layouts_dir = root_dir / "ppt" / "slideLayouts"
    for layout_name in ("slideLayout12.xml", "slideLayout13.xml"):
        layout_path = layouts_dir / layout_name
        rels_path = layouts_dir / "_rels" / f"{layout_name}.rels"
        if not layout_path.is_file():
            continue

        rels_root = _read_xml(rels_path) if rels_path.is_file() else None
        master_targets = []
        if rels_root is not None:
            master_targets = [
                rel.get("Target", "")
                for rel in rels_root.findall(REL)
                if rel.get("Type", "").endswith("/slideMaster")
            ]
        if master_targets != ["../slideMasters/slideMaster1.xml"]:
            findings.append(Finding(
                "error",
                "brand_layout_not_on_primary_master",
                (
                    f"{layout_name} must reference ../slideMasters/slideMaster1.xml; "
                    f"found {master_targets or '<missing>'}."
                ),
                rels_path.relative_to(root_dir).as_posix(),
            ))

        layout_root = _read_xml(layout_path)
        if (
            layout_root is None
            or layout_root.tag != SLD_LAYOUT
            or layout_root.get("type") != "blank"
            or str(layout_root.get("showMasterSp") or "").lower() not in {"0", "false", "off"}
        ):
            findings.append(Finding(
                "error",
                "brand_layout_inherits_master_chrome",
                (
                    f"{layout_name} must be type=\"blank\" with "
                    "p:sldLayout showMasterSp=\"0\"."
                ),
                layout_path.relative_to(root_dir).as_posix(),
            ))


def _ensure_notes_master_id_lst(root_dir: Path, findings: list[Finding]) -> None:
    """Register an existing notesMaster part in presentation.xml.

    A notesMaster part + relationship without a `p:notesMasterIdLst` entry is
    inconsistent and makes PowerPoint offer to repair the file.
    """
    notes_masters = sorted((root_dir / "ppt" / "notesMasters").glob("notesMaster*.xml"))
    pres_path = root_dir / "ppt" / "presentation.xml"
    pres_rels_path = root_dir / "ppt" / "_rels" / "presentation.xml.rels"
    if not notes_masters or not pres_path.is_file() or not pres_rels_path.is_file():
        return
    pres_root = _read_xml(pres_path)
    rels_root = _read_xml(pres_rels_path)
    if pres_root is None or rels_root is None:
        return
    if pres_root.find(NOTES_MASTER_ID_LST) is not None:
        return
    rid = None
    for rel in rels_root.findall(REL):
        if rel.get("Type", "").endswith("/notesMaster"):
            rid = rel.get("Id")
            break
    if rid is None:
        return
    lst = ET.Element(NOTES_MASTER_ID_LST)
    entry = ET.SubElement(lst, NOTES_MASTER_ID)
    entry.set(R_ID, rid)
    children = list(pres_root)
    index = 0
    for pos, child in enumerate(children):
        if child.tag == SLD_MASTER_ID_LST:
            index = pos + 1
            break
    pres_root.insert(index, lst)
    _write_xml(pres_path, pres_root)
    findings.append(Finding(
        "warning",
        "added_notes_master_id_lst",
        f"Registered notesMaster relationship {rid} in p:notesMasterIdLst.",
        "ppt/presentation.xml",
    ))


def _sanitize_slide_size(
    root_dir: Path,
    findings: list[Finding],
    *,
    width_emu: int | None = None,
    height_emu: int | None = None,
) -> None:
    if width_emu is None or height_emu is None:
        return
    path = root_dir / "ppt" / "presentation.xml"
    root = _read_xml(path)
    if root is None:
        findings.append(Finding("error", "invalid_presentation_xml", "presentation.xml is not parseable.", "ppt/presentation.xml"))
        return
    size = root.find(SLD_SZ)
    if size is None:
        size = ET.SubElement(root, SLD_SZ)
    expected = {"cx": str(width_emu), "cy": str(height_emu)}
    changed = False
    if size.get("cx") != expected["cx"] or size.get("cy") != expected["cy"]:
        old = {"cx": size.get("cx", ""), "cy": size.get("cy", "")}
        size.set("cx", expected["cx"])
        size.set("cy", expected["cy"])
        changed = True
        findings.append(Finding(
            "warning",
            "normalized_slide_size",
            f"Updated p:sldSz from {old} to {expected}.",
            "ppt/presentation.xml",
        ))
    # python-pptx's default template stamps type="screen4x3"; drop the hint
    # when it contradicts the actual EMU ratio instead of relabelling it.
    size_type = size.get("type")
    if size_type and size_type != "custom":
        ratio = width_emu / height_emu if height_emu else 0
        is_4x3 = abs(ratio - 4 / 3) < 0.01
        if (size_type == "screen4x3") != is_4x3:
            del size.attrib["type"]
            changed = True
            findings.append(Finding(
                "warning",
                "removed_mismatched_slide_size_type",
                f"Removed p:sldSz type=\"{size_type}\" that contradicts {width_emu}x{height_emu}.",
                "ppt/presentation.xml",
            ))
    if changed:
        _write_xml(path, root)


def _bool_attr_enabled(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "on"}


def _toggle_bool_attr(elem: ET.Element, name: str) -> None:
    if _bool_attr_enabled(elem.get(name)):
        elem.attrib.pop(name, None)
    else:
        elem.set(name, "1")


def _int_attr(elem: ET.Element, name: str) -> int | None:
    raw = elem.get(name)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _sanitize_preset_line_extents(root_dir: Path, findings: list[Finding]) -> int:
    """Normalize preset line transforms so PowerPoint accepts the package.

    WPS and LibreOffice tolerate `<a:ext cx/cy>` values that are negative or
    zero on preset line shapes. Microsoft PowerPoint is stricter: negative
    extents can trigger the "found a problem with content" repair dialog, and
    zero extents are fragile in some builds. Preserve direction with flipH/flipV
    and use 1 EMU for visually-zero horizontal/vertical lines.
    """
    normalized_total = 0
    for xml_path in sorted((root_dir / "ppt").rglob("*.xml")):
        root = _read_xml(xml_path)
        if root is None:
            continue
        normalized_in_file = 0
        for shape in root.iter(SP):
            sp_pr = shape.find(SP_PR)
            if sp_pr is None:
                continue
            geom = sp_pr.find(PRST_GEOM)
            if geom is None or geom.get("prst") != "line":
                continue
            xfrm = sp_pr.find(XFRM)
            if xfrm is None:
                continue
            off = xfrm.find(OFF)
            ext = xfrm.find(EXT)
            if off is None or ext is None:
                continue
            x = _int_attr(off, "x")
            y = _int_attr(off, "y")
            cx = _int_attr(ext, "cx")
            cy = _int_attr(ext, "cy")
            if x is None or y is None or cx is None or cy is None:
                continue

            old = (x, y, cx, cy, xfrm.get("flipH"), xfrm.get("flipV"))
            if cx < 0:
                x += cx
                cx = abs(cx)
                _toggle_bool_attr(xfrm, "flipH")
            if cy < 0:
                y += cy
                cy = abs(cy)
                _toggle_bool_attr(xfrm, "flipV")
            if cx == 0:
                cx = 1
            if cy == 0:
                cy = 1

            new = (x, y, cx, cy, xfrm.get("flipH"), xfrm.get("flipV"))
            if old == new:
                continue
            off.set("x", str(x))
            off.set("y", str(y))
            ext.set("cx", str(cx))
            ext.set("cy", str(cy))
            normalized_total += 1
            normalized_in_file += 1

        if normalized_in_file:
            _write_xml(xml_path, root)
            findings.append(Finding(
                "warning",
                "normalized_preset_line_extents",
                f"Normalized {normalized_in_file} preset line shape extent(s) for PowerPoint compatibility.",
                xml_path.relative_to(root_dir).as_posix(),
            ))
    return normalized_total


def _validate_xml_parts(root_dir: Path, findings: list[Finding]) -> None:
    for path in root_dir.rglob("*"):
        if not path.is_file() or not path.name.endswith((".xml", ".rels")):
            continue
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            findings.append(Finding(
                "error",
                "invalid_xml_part",
                f"XML parser failed: {exc}",
                path.relative_to(root_dir).as_posix(),
            ))


def _validate_drawingml_colors(root_dir: Path, findings: list[Finding]) -> None:
    """Reject malformed DrawingML RGB values that PowerPoint repairs on open."""
    for path in sorted((root_dir / "ppt").rglob("*.xml")):
        root = _read_xml(path)
        if root is None:
            continue
        for color in root.iter(SRGB_CLR):
            value = color.get("val", "")
            if len(value) == 6 and all(char in "0123456789abcdefABCDEF" for char in value):
                continue
            findings.append(Finding(
                "error",
                "invalid_drawingml_srgb_color",
                f"DrawingML a:srgbClr requires exactly six hexadecimal digits; found {value!r}.",
                path.relative_to(root_dir).as_posix(),
            ))


def sanitize_extracted_package(
    root_dir: Path,
    *,
    width_emu: int | None = None,
    height_emu: int | None = None,
    font_profile: str | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """Sanitize an extracted PPTX package directory and return a report."""
    findings: list[Finding] = []
    wps_cn_theme_fonts: dict[str, Any] = {}
    if font_profile == "wps-cn":
        wps_cn_theme_fonts = apply_wps_cn_theme_fonts(root_dir)
        for message in wps_cn_theme_fonts.get("errors", []):
            findings.append(Finding("error", "wps_cn_theme_font_parse_error", str(message), "ppt/theme"))
    _sanitize_relationships(root_dir, findings)
    _normalize_opc_namespace_prefixes(root_dir, findings)
    _remove_dropped_type_parts(root_dir, findings)
    _sanitize_empty_slide_masters(root_dir, findings)
    _validate_slide_master_topology(root_dir, findings)
    _ensure_notes_master_id_lst(root_dir, findings)
    _sanitize_content_types(root_dir, findings)
    _sanitize_slide_size(root_dir, findings, width_emu=width_emu, height_emu=height_emu)
    _sanitize_preset_line_extents(root_dir, findings)
    _validate_drawingml_colors(root_dir, findings)
    _validate_xml_parts(root_dir, findings)
    if font_profile == "wps-cn":
        wps_cn_theme_fonts = {
            **wps_cn_theme_fonts,
            **_inspect_wps_cn_theme_fonts(root_dir),
        }
        if not wps_cn_theme_fonts.get("theme_cn_font_count"):
            findings.append(Finding(
                "error",
                "missing_wps_cn_theme_font",
                "wps-cn requires theme font declarations containing `微软雅黑`.",
                "ppt/theme",
            ))
    errors = [finding.as_dict() for finding in findings if finding.level == "error"]
    warnings = [finding.as_dict() for finding in findings if finding.level == "warning"]
    report = {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "files": len(_iter_package_files(root_dir)),
    }
    if font_profile:
        report["font_profile"] = font_profile
    if wps_cn_theme_fonts:
        report["wps_cn_theme_fonts"] = wps_cn_theme_fonts
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _zip_dir(root_dir: Path, output_path: Path) -> None:
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as package:
        for file_path in root_dir.rglob("*"):
            if file_path.is_file():
                package.write(file_path, file_path.relative_to(root_dir).as_posix())


def sanitize_pptx_file(
    pptx_path: Path,
    *,
    output_path: Path | None = None,
    report_path: Path | None = None,
    font_profile: str | None = None,
) -> dict[str, Any]:
    """Sanitize a PPTX file, writing either in-place or to output_path."""
    target = output_path or pptx_path
    temp_dir = Path(tempfile.mkdtemp())
    temp_output = Path(tempfile.mkdtemp()) / "sanitized.pptx"
    try:
        with zipfile.ZipFile(pptx_path, "r") as package:
            package.extractall(temp_dir)
        report = sanitize_extracted_package(temp_dir, report_path=report_path, font_profile=font_profile)
        _zip_dir(temp_dir, temp_output)
        shutil.copy2(temp_output, target)
        return report
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(temp_output.parent, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and sanitize generated PPTX package structure.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", help="PPTX file or extracted PPTX package directory")
    parser.add_argument("--in-place", action="store_true", help="Rewrite a PPTX file in place")
    parser.add_argument("--output", help="Output PPTX path when target is a PPTX file")
    parser.add_argument("--report", help="Report JSON path (default: <target>.compat_report.json)")
    parser.add_argument("--width-emu", type=int, default=None, help="Expected slide width in EMU")
    parser.add_argument("--height-emu", type=int, default=None, help="Expected slide height in EMU")
    parser.add_argument("--font-profile", choices=["office", "wps-cn"], default=None, help="Optional package font compatibility profile")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    target = Path(args.target).resolve()
    if not target.exists():
        print(json.dumps({
            "valid": False,
            "errors": [{"level": "error", "code": "missing_target", "message": f"Target not found: {target}"}],
            "warnings": [],
        }, ensure_ascii=False, indent=2))
        return 1

    report_path = Path(args.report).resolve() if args.report else None
    if target.is_dir():
        report = sanitize_extracted_package(
            target,
            width_emu=args.width_emu,
            height_emu=args.height_emu,
            font_profile=args.font_profile,
            report_path=report_path or target / "compat_report.json",
        )
    else:
        if not args.in_place and not args.output:
            parser.error("PPTX file targets require --in-place or --output")
        output = Path(args.output).resolve() if args.output else None
        report = sanitize_pptx_file(
            target,
            output_path=output,
            font_profile=args.font_profile,
            report_path=report_path or Path(str(output or target) + ".compat_report.json"),
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
