"""Local, reviewed layer handoff for the integrated Quick authoring workflow.

The main agent edits the reference image and authors SVG. This module binds and
validates those assets; it never generates a replacement layout or clears text.
All receipts live in the existing production page manifest.
"""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from PIL import Image

SCHEMA = "cyberppt.stage02.authored_clean_base.v1"
REVIEW_CHECKS = frozenset({
    "source_layout", "graphic_identity", "text_removed", "background_continuity",
})


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _policy_sha(policy: Mapping[str, Any] | None) -> str:
    data = json.dumps(dict(policy or {}), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def local_svg_assets(svg: Path, root: Path) -> list[Path]:
    """Resolve every raster layer, rejecting network links and path escapes."""
    assets = set()
    for node in ET.parse(svg).getroot().iter():
        if node.tag.rsplit("}", 1)[-1] != "image":
            continue
        href = node.get("href") or node.get("{http://www.w3.org/1999/xlink}href") or ""
        if not href or ":" in href or Path(href).is_absolute():
            raise ValueError("Quick layers require relative local image references")
        asset = (svg.parent / href).resolve()
        if not asset.is_relative_to(root.resolve()) or not asset.is_file():
            raise ValueError(f"Quick layer is missing or escapes the active build: {href}")
        assets.add(asset)
    return sorted(assets)


def validate_authored_layers(
    clean_base: Mapping[str, Any], *, full_image: Path | str,
    authored_svg: Path | str, graphic_text_policy: Mapping[str, Any] | None,
    page_number: int,
) -> dict[str, Any]:
    """Recompute hashes and geometry; visual decisions must match these bytes."""
    errors = []
    try:
        full, svg = Path(full_image).resolve(), Path(authored_svg).resolve()
        base = Path(str(clean_base.get("path") or "")).resolve()
        root = Path(str(clean_base.get("build_root") or "")).resolve()
        if clean_base.get("schema") != SCHEMA or clean_base.get("status") != "complete":
            raise ValueError("authored layers have not been registered")
        if not svg.is_relative_to(root) or not base.is_relative_to(root):
            raise ValueError("authored layers must stay inside the active build")
        if clean_base.get("method") != "reference-image-edit":
            raise ValueError("authored base requires reference-image-edit provenance")
        if clean_base.get("source_sha256") != _sha(full):
            raise ValueError("authored base source hash differs from the audited full image")
        if clean_base.get("sha256") != _sha(base):
            raise ValueError("authored base changed; inspect and register it again")
        if _sha(base) == _sha(full):
            raise ValueError("audited full image cannot serve as the text-free base")
        with Image.open(full) as source, Image.open(base) as background:
            canvas = list(source.size)
            if list(background.size) != canvas or clean_base.get("canvas") != canvas:
                raise ValueError("authored base must retain the audited source canvas")
        svg_root = ET.parse(svg).getroot()
        viewbox = [float(n) for n in svg_root.get("viewBox", "").replace(",", " ").split()]
        if viewbox != [0, 0, *canvas]:
            raise ValueError("authored SVG must use the audited source coordinate system")
        if svg_root.get("data-cyberppt-native-text-style") != "locked":
            raise ValueError("authored SVG must lock its explicit native text style")
        native = [item for item in (graphic_text_policy or {}).get("items", [])
                  if item.get("treatment") == "native_text"]
        if not native:
            raise ValueError("editable page requires classified native text")
        for item in native:
            box = item.get("bbox")
            if not isinstance(box, list) or len(box) != 4:
                raise ValueError("native text requires observed source coordinates")
            left, top, right, bottom = map(float, box)
            if not (0 <= left < right <= canvas[0] and 0 <= top < bottom <= canvas[1]):
                raise ValueError("native text region is outside the source canvas")
        assets = local_svg_assets(svg, root)
        if base not in assets:
            raise ValueError("authored SVG must reference the registered text-free base")
        if any(_sha(asset) == _sha(full) for asset in assets):
            raise ValueError("audited full image cannot be an SVG raster layer")
        for asset in assets:
            with Image.open(asset) as image:
                image.verify()
        actual = {str(asset): _sha(asset) for asset in assets}
        if clean_base.get("assets") != actual:
            raise ValueError("an SVG layer changed; inspect and register the page again")
        review = clean_base.get("visual_review") or {}
        if (review.get("status") != "passed" or not str(review.get("reviewer") or "").strip()
                or review.get("svg_sha256") != _sha(svg)
                or review.get("graphic_text_policy_sha256") != _policy_sha(graphic_text_policy)
                or any((review.get("checks") or {}).get(key) != "passed" for key in REVIEW_CHECKS)):
            raise ValueError("authored layer review is missing or stale")
    except (OSError, ValueError, TypeError, ET.ParseError) as exc:
        errors.append({"code": "invalid_authored_layers", "message": str(exc)})
    return {"schema": SCHEMA + ".qa", "page_number": page_number, "valid": not errors, "errors": errors}


def register_quick_page(
    manifest_path: Path, *, page_number: int, authored_svg: Path,
    clean_base: Path, source_sha256: str, reviewer: str,
    checks: Mapping[str, str], notes: str = "",
) -> dict[str, Any]:
    """Register already-inspected local assets without assembling or redrawing."""
    from .authored_svg_preflight import validate_authored_svg_preflight
    from .graphic_text_policy import validate_graphic_text_policy

    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    context = json.loads((manifest_path.parent / "build_context.json").read_text(encoding="utf-8"))
    if (context.get("schema") != "cyberppt.build_context.v1"
            or context.get("stage") != "02-production-build"
            or context.get("build_id") != manifest.get("run_id")
            or context.get("source_script_sha256") != manifest.get("source_script_sha256")
            or context.get("assembly_mode") not in {"editable", "both"}):
        raise ValueError("register-quick-page requires an existing final-script-pages production build")
    script = Path(str(manifest.get("source_script") or ""))
    if not script.is_file() or _sha(script) != manifest.get("source_script_sha256"):
        raise ValueError("locked script changed; resume final-script-pages before authoring")
    pair = next((p for p in manifest.get("pairs", []) if p.get("page_number") == page_number), None)
    if pair is None or page_number not in manifest.get("requested_pages", []):
        raise ValueError(f"page {page_number} is outside the active build scope")
    full = pair.get("full") or {}
    source = Path(str(full.get("path") or "")).resolve()
    if full.get("status") != "Generated" or (full.get("text_audit") or {}).get("valid") is not True:
        raise ValueError("page requires a passed full-image text audit")
    if not source_sha256 or _sha(source) != source_sha256:
        raise ValueError("source hash must identify the exact image inspected during authoring")
    authority = full.get("reconstruction_visual_source") or {}
    if authority.get("sha256") != source_sha256:
        raise ValueError("page requires a current reconstruction visual-source binding")
    if not reviewer.strip() or set(checks) != REVIEW_CHECKS or any(v != "passed" for v in checks.values()):
        raise ValueError("all authored layer review checks must explicitly pass")
    svg, base, root = authored_svg.resolve(), clean_base.resolve(), manifest_path.parent
    if not svg.is_relative_to(root) or not base.is_relative_to(root):
        raise ValueError("author SVG and layers inside the active production build")
    policy = pair.get("graphic_text_policy")
    for report in (
        validate_authored_svg_preflight(svg, page_number=page_number),
        validate_graphic_text_policy(
            policy,
            authored_svg=svg,
            page_number=page_number,
            source_image=source,
            require_exact_fidelity=True,
        ),
    ):
        if not report.get("valid"):
            raise ValueError(f"authored page is incomplete: {report.get('errors')}")
    with Image.open(source) as image:
        canvas = list(image.size)
    contract = {
        "schema": SCHEMA, "status": "complete", "method": "reference-image-edit",
        "build_root": str(root), "authoring_svg": str(svg), "path": str(base),
        "source_sha256": source_sha256, "sha256": _sha(base), "canvas": canvas,
        "assets": {str(p): _sha(p) for p in local_svg_assets(svg, root)},
        "visual_review": {
            "status": "passed", "reviewer": reviewer.strip(), "checks": dict(checks),
            "reviewed_at": datetime.now(timezone.utc).isoformat(), "notes": notes,
            "svg_sha256": _sha(svg), "graphic_text_policy_sha256": _policy_sha(policy),
        },
    }
    report = validate_authored_layers(contract, full_image=source, authored_svg=svg,
                                     graphic_text_policy=policy, page_number=page_number)
    if not report["valid"]:
        raise ValueError(str(report["errors"]))
    pair["clean_base"], pair["authoring_svg"] = contract, str(svg)
    pair.pop("quick_page_checkpoint", None)
    # Retire provisional external-import receipts without touching their files.
    pair.pop("authoring_svg_import", None)
    manifest.pop("quick_backend", None)
    manifest.pop("quick_authoring_import", None)
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(manifest_path)
    return {"page_number": page_number, "status": "registered", "authoring_svg": str(svg), "clean_base": str(base)}
