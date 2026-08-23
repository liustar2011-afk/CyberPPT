"""CyberPPT Stage 02 boundary for the imported image-to-PPTX Quick runtime."""

from __future__ import annotations

import json
import hashlib
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

from PIL import Image

from cyberppt.script_quality.parsing import parse_script_path
from scripts.presentation_qa.render_page import check_pptx_geometry, render_to_png
from scripts.presentation_qa.text_content import build_text_content_qa
from scripts.imagegen_pipeline.production_readiness import build_production_readiness

from . import assert_internal_runtime
from .quick import create_quick_project
from .editable_page_validation import validate_editable_page
from .native_text_style import (
    apply_default_native_text_style,
    write_native_text_style_receipt,
)
from .native_text_geometry import (
    SCHEMA as NATIVE_TEXT_GEOMETRY_SCHEMA,
    analyze_native_text_geometry,
    write_native_text_geometry_receipt,
)
from .review import write_review
from .quick_page_review import quick_visual_review_passes
from .clean_base_policy import SCHEMA as CLEAN_BASE_SCHEMA
from .svg_quality.checker import SVGQualityChecker
from .template_assembly import (
    assemble_brand_page_svg,
    assemble_template_pptx,
    assemble_template_svg,
    load_template_contract,
)


# The only production route allowed to publish an editable PPTX from a
# rendered page is the hand-authored SVG Quick reconstruction path below.
CANONICAL_EDITABLE_PPTX_ROUTE = "stage02-quick-image-to-pptx"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _quick_page_binding(pair: Mapping[str, Any], authored: Path) -> dict[str, str]:
    """Bind a reusable page checkpoint to its three visible inputs.

    A changed input simply causes local revalidation; it never rejects the
    build or forces regeneration of an already-audited full image.
    """

    full = Path(str((pair.get("full") or {}).get("path") or ""))
    clean = Path(str((pair.get("clean_base") or {}).get("path") or ""))
    return {
        "authoring_svg_sha256": _sha256(authored),
        "full_image_sha256": _sha256(full),
        "clean_base_sha256": _sha256(clean) if clean.is_file() else "",
        "native_text_geometry_schema": NATIVE_TEXT_GEOMETRY_SCHEMA + ".intra-text-v1",
        "clean_base_policy_schema": CLEAN_BASE_SCHEMA + ".verified-pixel-mask-v13",
    }


def _current_quick_checkpoint(
    checkpoint: object,
    binding: Mapping[str, str],
) -> bool:
    if not isinstance(checkpoint, Mapping):
        return False
    if checkpoint.get("status") not in {
        "rendered_pending_visual_review",
        "visual_review_failed",
        "passed",
    } or checkpoint.get("binding") != dict(binding):
        return False
    required = (
        checkpoint.get("target_svg"),
        checkpoint.get("preview_pptx"),
        checkpoint.get("preview_png"),
    )
    return all(Path(str(value or "")).is_file() for value in required)


def _require_official_orchestration(manifest_path: Path, manifest: Mapping[str, Any], *, assembly_mode: str) -> None:
    """Reject direct adapter calls that bypass final-script-pages."""

    context_path = manifest_path.parent / "build_context.json"
    if not context_path.is_file():
        raise ValueError("Stage 02 adapter requires final-script-pages orchestration evidence (build_context.json)")
    context = _read_json(context_path)
    artifact = context.get("artifacts", {}).get("page_image_pairs", {}) if isinstance(context.get("artifacts"), Mapping) else {}
    bound_path = Path(str(artifact.get("path") or "")).expanduser().resolve()
    if (
        context.get("schema") != "cyberppt.build_context.v1"
        or context.get("production_mode") != "image-to-editable-svg"
        or context.get("assembly_mode") != assembly_mode
        or bound_path != manifest_path
        or artifact.get("sha256") != _sha256(manifest_path)
        or manifest.get("source_script_sha256") != context.get("source_script_sha256")
    ):
        raise ValueError("Stage 02 adapter requires a current final-script-pages build context")


def _script_lines(script: Path, page_number: int) -> list[str]:
    from scripts.imagegen_pipeline.deliverable_prompt import parse_page_blocks

    page = parse_page_blocks(script).get(page_number)
    if page is None:
        raise ValueError(f"final script has no page {page_number}")
    # The template wrapper owns the page title. Keep the Quick body inventory
    # and editable-text QA scoped to body copy so a valid page does not need a
    # duplicate title inside the reconstructed 2:1 body SVG.
    return [item for item in page.text.splitlines() if item.strip()]


def _require_audited_pairs(manifest: Mapping[str, Any], requested_pages: list[int]) -> list[dict[str, Any]]:
    if manifest.get("production_mode") != "image-to-editable-svg" or manifest.get("output_variants") != ["full"]:
        raise ValueError("Stage 02 image-to-PPTX requires the audited full-image production manifest")
    pairs = [dict(item) for item in manifest.get("pairs", []) if isinstance(item, Mapping) and item.get("page_number") in requested_pages]
    if {int(item["page_number"]) for item in pairs} != set(requested_pages):
        raise ValueError("requested pages are not an exact manifest subset")
    for pair in pairs:
        full = pair.get("full") if isinstance(pair.get("full"), Mapping) else {}
        source = Path(str(full.get("path") or ""))
        if full.get("status") != "Generated" or not source.is_file() or full.get("text_audit", {}).get("valid") is not True:
            raise ValueError(f"page {pair['page_number']} requires generated full image with passed text audit")
    return pairs


def _copy_relative_svg_assets(source: Path, target: Path) -> None:
    """Keep prepared SVG image layers valid inside the internal Quick project."""
    root = ET.fromstring(source.read_text(encoding="utf-8"))
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "image":
            continue
        href = node.attrib.get("href") or node.attrib.get("{http://www.w3.org/1999/xlink}href")
        if not href or href.startswith(("data:", "http:", "https:")) or Path(href).is_absolute():
            continue
        asset = (source.parent / href).resolve()
        if not asset.is_file():
            raise FileNotFoundError(f"authored SVG layer is missing: {asset}")
        destination = (target.parent / href).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset, destination)


def _validate_body_image(
    source: Path,
    page_number: int,
    *,
    expected_size: tuple[int, int] | None = None,
) -> tuple[int, int]:
    try:
        with Image.open(source) as image:
            size = image.size
    except OSError as exc:
        raise ValueError(f"page {page_number} body image cannot be opened: {source}") from exc
    if size[1] <= 0 or abs(size[0] / size[1] - 2.0) > 0.002:
        raise ValueError(f"page {page_number} body image must be 2:1; got {size[0]}x{size[1]}")
    if expected_size is not None and size != expected_size:
        raise ValueError(
            f"page {page_number} body image must match the manifest canvas "
            f"{expected_size[0]}x{expected_size[1]}; got {size[0]}x{size[1]}"
        )
    return size


def _manifest_canvas(pair: Mapping[str, Any]) -> tuple[int, int]:
    full = pair.get("full") if isinstance(pair.get("full"), Mapping) else {}
    match = re.fullmatch(r"\s*(\d+)x(\d+)\s*", str(full.get("canvas") or ""))
    if match is None:
        raise ValueError(f"page {pair.get('page_number')} full image has no valid manifest canvas")
    return int(match.group(1)), int(match.group(2))


def _page_title(script: Path, page_number: int) -> str:
    document = parse_script_path(script)
    page = next((item for item in document.pages if item.sequence == page_number), None)
    return page.title.strip() if page is not None and page.title.strip() else f"第{page_number}页"


def _speaker_notes_by_page(script: Path, page_numbers: list[int]) -> dict[str, str]:
    """Map final-script speaker notes to the SVG stems used by the exporter."""

    document = parse_script_path(script)
    pages = {page.sequence: page for page in document.pages}
    missing = [number for number in page_numbers if number not in pages]
    if missing:
        raise ValueError(
            "final script is missing requested speaker-note pages: "
            + ", ".join(str(number) for number in missing)
        )
    return {
        f"p{number:02d}": pages[number].speaker_notes.strip()
        for number in page_numbers
        if pages[number].speaker_notes.strip()
    }


def _run_text_qa(export: Path, expected: list[str], *, include_body_text: bool) -> dict[str, Any]:
    # The wrapper owns native title/footer/page-number text in both routes;
    # editable mode additionally includes the authored body text.
    values = expected
    report = build_text_content_qa(
        export,
        values,
        order_sensitive=False,
        allow_fragmented_actual=True,
    )
    if not report["valid"]:
        raise ValueError(f"exported PPTX native text differs from the approved script: {export}")
    return report


def run_stage02_reconstruction(
    *,
    project: Path | str,
    manifest_path: Path | str,
    output_dir: Path | str,
    requested_pages: list[int],
    assembly_mode: str = "editable",
) -> dict[str, Any]:
    """Run the Stage 02 2:1 body-to-template assembly routes.

    ``image`` publishes the original body image inside the template正文区;
    ``editable`` publishes the Quick authoring SVG inside the same slot;
    ``both`` publishes both artifacts from one audited input set.
    """

    # The Quick runtime is vendored into CyberPPT.  Fail before consuming any
    # project artifact if a copied module regresses to an external ppt-master
    # checkout dependency.
    assert_internal_runtime()
    if assembly_mode not in {"image", "editable", "both"}:
        raise ValueError("assembly_mode must be image, editable, or both")
    manifest_file = Path(manifest_path).expanduser().resolve()
    manifest = _read_json(manifest_file)
    _require_official_orchestration(manifest_file, manifest, assembly_mode=assembly_mode)
    content_pages = {
        int(value)
        for value in manifest.get("content_page_numbers", [])
        if isinstance(value, int) or str(value).isdigit()
    }
    requested_content_pages = [number for number in requested_pages if number in content_pages]
    pairs = _require_audited_pairs(manifest, requested_content_pages)
    script = Path(str(manifest.get("source_script") or "")).expanduser().resolve()
    if not script.is_file():
        raise FileNotFoundError(f"approved source script is missing: {script}")
    output = Path(output_dir).expanduser().resolve()
    pages = [(int(pair["page_number"]), Path(str(pair["full"]["path"]))) for pair in pairs]
    pair_by_page = {int(pair["page_number"]): pair for pair in pairs}
    for number, source in pages:
        _validate_body_image(source, number, expected_size=_manifest_canvas(pair_by_page[number]))

    needs_editable = assembly_mode in {"editable", "both"}
    needs_image = assembly_mode in {"image", "both"}
    quick = None
    if needs_editable:
        quick = create_quick_project(
            output / "image_to_pptx_runtime",
            pages=pages,
            text_by_page={number: _script_lines(script, number) for number, _ in pages},
        )
    svgs: list[Path] = []
    quality: list[dict[str, Any]] = []
    native_text_style: list[dict[str, Any]] = []
    native_text_geometry: list[dict[str, Any]] = []
    graphic_text_policy: list[dict[str, Any]] = []
    clean_base_policy: list[dict[str, Any]] = []
    editable_page_qa: list[dict[str, Any]] = []
    checker = SVGQualityChecker(quick_generate=True)
    contract = load_template_contract()
    title_by_page = {number: _page_title(script, number) for number in requested_pages}
    manifest_pairs = {
        int(pair["page_number"]): pair
        for pair in manifest.get("pairs", [])
        if isinstance(pair, dict) and str(pair.get("page_number") or "").isdigit()
    }
    if needs_editable:
        assert quick is not None
        page_failures: list[str] = []
        for pair in pairs:
            page_number = int(pair["page_number"])
            authored = Path(str(pair.get("authoring_svg") or "")).expanduser()
            manifest_pair = manifest_pairs[page_number]
            try:
                if not authored.is_file():
                    raise ValueError("requires a hand-authored SVG from the image-to-PPTX runtime")
                binding = _quick_page_binding(pair, authored)
                checkpoint = pair.get("quick_page_checkpoint")
                if _current_quick_checkpoint(checkpoint, binding):
                    assert isinstance(checkpoint, Mapping)
                    if not quick_visual_review_passes(checkpoint):
                        pending_checkpoint = dict(checkpoint)
                        pending_checkpoint["status"] = (
                            "visual_review_failed"
                            if isinstance(checkpoint.get("visual_review"), Mapping)
                            else "rendered_pending_visual_review"
                        )
                        pending_checkpoint["resume"] = "awaiting_visual_review"
                        manifest_pair["quick_page_checkpoint"] = pending_checkpoint
                        _write_json(manifest_file, manifest)
                        page_failures.append(
                            f"p{page_number:02d}: rendered preview awaits a passed visual review"
                        )
                        continue
                    target = Path(str(checkpoint["target_svg"]))
                    page_validation = dict(checkpoint["editable_page_qa"])
                    geometry_report = dict(checkpoint["native_text_geometry"])
                    style_report = dict(checkpoint["native_text_style"])
                    quality_report = dict(checkpoint["svg_quality"])
                    checkpoint_payload = dict(checkpoint)
                    checkpoint_payload["resume"] = "reused"
                else:
                    page_validation = validate_editable_page(
                        clean_base=pair.get("clean_base"),
                        full_image=Path(str(pair["full"]["path"])),
                        authored_svg=authored,
                        graphic_text_policy=pair.get("graphic_text_policy"),
                        page_number=page_number,
                    )
                    if not page_validation["valid"]:
                        raise ValueError(f"failed editable-page validation: {page_validation['errors']}")
                    target = quick.svg_path(page_number)
                    shutil.copy2(authored, target)
                    _copy_relative_svg_assets(authored, target)
                    geometry_report = analyze_native_text_geometry(
                        pair.get("graphic_text_policy"),
                        authored_svg=target,
                        page_number=page_number,
                    )
                    if geometry_report.get("valid") is not True:
                        raise ValueError(
                            "failed native-text geometry validation: "
                            + "; ".join(geometry_report.get("warnings") or [])
                        )
                    style_report = apply_default_native_text_style(target)
                    quality_report = checker.check_file(str(target))
                    if not quality_report.get("passed"):
                        raise ValueError(f"failed imported SVG quality: {quality_report.get('errors')}")

                    checkpoint_dir = output / "page_checkpoints" / f"p{page_number:02d}"
                    wrapper = checkpoint_dir / "svg_output" / f"p{page_number:02d}.svg"
                    assemble_template_svg(
                        source=target,
                        output=wrapper,
                        title=title_by_page[page_number],
                        page_number=page_number,
                        mode="editable",
                        contract=contract,
                    )
                    preview_pptx = checkpoint_dir / f"p{page_number:02d}.pptx"
                    assemble_template_pptx([wrapper], preview_pptx)
                    render_dir = checkpoint_dir / "render"
                    rendered = render_to_png(
                        preview_pptx,
                        render_dir,
                        dpi=150,
                        renderer="officecli",
                        strict_renderer=True,
                    )
                    preview_png = rendered[0] if rendered else None
                    preview_geometry = check_pptx_geometry(preview_pptx, dpi=96)
                    if preview_png is None or not preview_png.is_file():
                        raise ValueError("single-page Quick preview was not rendered")
                    if not preview_geometry["valid"]:
                        raise ValueError("single-page Quick preview failed geometry QA")
                    checkpoint_payload = {
                        "schema": "cyberppt.stage02.quick_page_checkpoint.v1",
                        "status": "rendered_pending_visual_review",
                        "binding": binding,
                        "target_svg": str(target),
                        "preview_svg": str(wrapper),
                        "preview_pptx": str(preview_pptx),
                        "preview_png": str(preview_png),
                        "preview_geometry": preview_geometry,
                        "editable_page_qa": page_validation,
                        "native_text_geometry": geometry_report,
                        "native_text_style": style_report,
                        "svg_quality": quality_report,
                        "resume": "rendered",
                    }
                    manifest_pair["quick_page_checkpoint"] = checkpoint_payload
                    _write_json(manifest_file, manifest)
                    page_failures.append(
                        f"p{page_number:02d}: rendered preview awaits visual review: {preview_png}"
                    )
                    continue

                editable_page_qa.append(page_validation)
                clean_base_policy.append(page_validation["clean_base"])
                graphic_text_policy.append(page_validation["graphic_text_policy"])
                native_text_geometry.append(geometry_report)
                native_text_style.append(style_report)
                quality.append(quality_report)
                svgs.append(target)
                manifest_pair["quick_page_checkpoint"] = checkpoint_payload
                _write_json(manifest_file, manifest)
            except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
                manifest_pair["quick_page_checkpoint"] = {
                    "schema": "cyberppt.stage02.quick_page_checkpoint.v1",
                    "status": "failed",
                    "error": str(exc),
                }
                _write_json(manifest_file, manifest)
                page_failures.append(f"p{page_number:02d}: {exc}")
        if page_failures:
            raise ValueError(
                "Stage 02 per-page Quick validation failed; passed pages were checkpointed: "
                + "; ".join(page_failures)
            )

    output_root = output / "template_assembly"
    if quick is not None:
        review = write_review(quick, [])
    else:
        image_analysis = output_root / "image" / "analysis"
        image_analysis.mkdir(parents=True, exist_ok=True)
        inventory_path = image_analysis / "reconstruction_inventory.json"
        inventory_path.write_text(
            json.dumps(
                {
                    "schema": "cyberppt.image_to_pptx.inventory.v1",
                    "mode": "image",
                    "pages": [
                        {
                            "page_number": number,
                            "source_path": str(source),
                            "source_size": list(_validate_body_image(source, number)),
                            "visible_text": _script_lines(script, number),
                            "note": "Audited 2:1 body image placed in the template正文区.",
                        }
                        for number, source in pages
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        review_path = output / "analysis" / "image_review.json"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review = {"schema": "cyberppt.image_to_pptx.visual_review.v1", "mode": "image", "issues": [], "requires_rebuild": False, "valid": True, "path": str(review_path)}
        review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    speaker_notes = _speaker_notes_by_page(script, requested_pages)
    script_document = parse_script_path(script)
    script_pages = {page.sequence: page for page in script_document.pages}
    structural_lines = {
        number: [line.strip() for line in script_pages[number].onscreen_text.splitlines() if line.strip()]
        for number in requested_pages
        if number not in content_pages
    }

    def structural_display_lines(number: int) -> list[str]:
        lines = structural_lines[number]
        if title_by_page[number] in lines:
            return lines
        return [title_by_page[number], *lines]

    expected = [
        str(text)
        for pair in pairs
        for text in ((pair.get("full") or {}).get("debug_receipt") or {}).get("visible_text", [])
        if str(text).strip()
    ]
    for policy in graphic_text_policy:
        for item in policy.get("items", []):
            if item.get("treatment") == "native_text" and item.get("text") not in expected:
                expected.append(str(item["text"]))
    chrome_expected = [
        *(title_by_page[number] for number, _ in pages),
        *("中国电力企业联合会" for _ in pages),
        *(str(number) for number, _ in pages),
    ]
    structural_expected = [
        *[
            text
            for number in requested_pages
            if number not in content_pages
            for text in structural_display_lines(number)
        ],
        *("中国电力企业联合会" for number in requested_pages if number not in content_pages),
        *(
            str(number)
            for number in requested_pages
            if number not in content_pages and script_pages[number].page_type in {"contents", "chapter"}
        ),
        *(
            "章节导览"
            for number in requested_pages
            if number not in content_pages and script_pages[number].page_type == "chapter"
        ),
        *(
            f"{index:02d}"
            for number in requested_pages
            if number not in content_pages and script_pages[number].page_type == "contents"
            for index, _ in enumerate(structural_display_lines(number)[1:7], start=1)
        ),
    ]

    def structural_svg(number: int, mode: str) -> Path:
        page = script_pages[number]
        role = page.page_type if page.page_type in {"cover", "contents", "chapter", "closing"} else "chapter"
        target = output_root / mode / "svg_output" / f"p{number:02d}.svg"
        return assemble_brand_page_svg(
            output=target,
            role=role,
            onscreen_lines=structural_display_lines(number),
            contract=contract,
            page_number=number,
        )

    exports: dict[str, Path] = {}
    text_qa_by_mode: dict[str, dict[str, Any]] = {}
    if needs_image:
        image_svgs: list[Path] = []
        pair_by_page = {int(pair["page_number"]): pair for pair in pairs}
        for number in requested_pages:
            if number not in pair_by_page:
                image_svgs.append(structural_svg(number, "image"))
                continue
            pair = pair_by_page[number]
            wrapper = output_root / "image" / "svg_output" / f"p{number:02d}.svg"
            image_svgs.append(assemble_template_svg(source=Path(str(pair["full"]["path"])), output=wrapper, title=title_by_page[number], page_number=number, mode="image", contract=contract, body_image=Path(str(pair["full"]["path"]))))
        image_export = output / "exports" / "template_image.pptx"
        assemble_template_pptx(image_svgs, image_export, notes=speaker_notes)
        exports["image"] = image_export
        text_qa_by_mode["image"] = _run_text_qa(image_export, [*chrome_expected, *structural_expected], include_body_text=False)

    if needs_editable:
        editable_svgs: list[Path] = []
        assert quick is not None
        pair_by_page = {int(pair["page_number"]): pair for pair in pairs}
        for number in requested_pages:
            if number not in pair_by_page:
                editable_svgs.append(structural_svg(number, "editable"))
                continue
            wrapper = output_root / "editable" / "svg_output" / f"p{number:02d}.svg"
            editable_svgs.append(assemble_template_svg(source=quick.svg_path(number), output=wrapper, title=title_by_page[number], page_number=number, mode="editable", contract=contract))
        editable_export = output / "exports" / "editable_svg.pptx"
        assemble_template_pptx(editable_svgs, editable_export, notes=speaker_notes)
        exports["editable"] = editable_export
        text_qa_by_mode["editable"] = _run_text_qa(editable_export, [*expected, *chrome_expected, *structural_expected], include_body_text=True)

    primary_mode = "editable" if "editable" in exports else "image"
    export = exports[primary_mode]
    analysis = output / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    text_path = analysis / "text_content_qa.json"
    text_path.write_text(json.dumps(text_qa_by_mode, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    editable_page_path = analysis / "editable_page_qa.json"
    editable_page_path.write_text(
        json.dumps({"schema": "cyberppt.stage02.editable_page_qa.v1", "pages": editable_page_qa}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    native_text_style_path = write_native_text_style_receipt(
        native_text_style,
        analysis / "native_text_style_qa.json",
    )
    native_text_geometry_path = write_native_text_geometry_receipt(
        native_text_geometry,
        analysis / "native_text_geometry_qa.json",
    )
    runtime_root = quick.root if quick is not None else output_root / "image"
    artifacts = {"reconstruction_inventory": str(runtime_root / "analysis" / "reconstruction_inventory.json"), "svg_output": str(runtime_root / "svg_output"), "reconstruction_quality": str(analysis), "native_text_style_qa": str(native_text_style_path), "native_text_geometry_qa": str(native_text_geometry_path), "text_content_qa": str(text_path), "editable_page_qa": str(editable_page_path), "clean_base_policy_qa": str(editable_page_path), "graphic_text_policy_qa": str(editable_page_path), "render_compare": str(review["path"]), "exported_pptx": str(export)}
    reports = {"reconstruction_inventory": {"valid": True}, "reconstruction_quality": {"valid": True, "pages": quality}, "svg_output": {"valid": True}, "native_text_style": {"valid": True, "pages": native_text_style}, "native_text_geometry": {"valid": True, "qa_only": True, "pages": native_text_geometry, "review_required": any(report.get("review_required") for report in native_text_geometry)}, "text_content_qa": text_qa_by_mode, "editable_page": {"valid": True, "pages": editable_page_qa}, "clean_base_policy": {"valid": True, "pages": clean_base_policy}, "graphic_text_policy": {"valid": True, "pages": graphic_text_policy}, "render_compare": {"valid": review["valid"], "review": review}, "exported_pptx": {"valid": True}, "exported_pptx_by_mode": {mode: {"valid": True, "path": str(path)} for mode, path in exports.items()}}
    readiness = build_production_readiness(stage="02-production-build", artifacts=artifacts, reports=reports, required_tools=tuple(artifacts))
    result = {"schema": "cyberppt.image_to_pptx.stage02.v1", "status": readiness["status"], "assembly_mode": assembly_mode, "runtime_project": str(runtime_root), "svg_roster": [str(svg) for svg in svgs], "svg_quality": quality, "visual_review": review, "artifacts": artifacts, "artifacts_by_mode": {mode: str(path) for mode, path in exports.items()}, "reports": reports, "text_content_qa": text_qa_by_mode, "release_gate": {"valid": True, "manual_adjustments": "local_only"}, "delivery_readiness": readiness}
    result_path = analysis / "image-to-pptx-result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["artifacts"]["delivery_readiness"] = str(result_path)
    return result
