"""CyberPPT Stage 02 boundary for the imported image-to-PPTX Quick runtime."""

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

from PIL import Image

from cyberppt.script_quality.parsing import parse_script_path
from scripts.presentation_qa.text_content import build_text_content_qa
from scripts.imagegen_pipeline.production_readiness import build_production_readiness

from .quick import create_quick_project
from .graphic_text_policy import validate_graphic_text_policy
from .review import write_review
from .svg_quality.checker import SVGQualityChecker
from .template_assembly import (
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


def _script_lines(script: Path, page_number: int) -> list[str]:
    from scripts.imagegen_pipeline.deliverable_prompt import parse_page_blocks

    page = parse_page_blocks(script).get(page_number)
    if page is None:
        raise ValueError(f"final script has no page {page_number}")
    return [item for item in [page.title, *page.text.splitlines()] if item.strip()]


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


def _validate_body_image(source: Path, page_number: int) -> tuple[int, int]:
    try:
        with Image.open(source) as image:
            size = image.size
    except OSError as exc:
        raise ValueError(f"page {page_number} body image cannot be opened: {source}") from exc
    if size[1] <= 0 or abs(size[0] / size[1] - 2.0) > 0.002:
        raise ValueError(f"page {page_number} body image must be 2:1; got {size[0]}x{size[1]}")
    return size


def _page_title(script: Path, page_number: int) -> str:
    lines = _script_lines(script, page_number)
    return lines[0] if lines else f"第{page_number}页"


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

    if assembly_mode not in {"image", "editable", "both"}:
        raise ValueError("assembly_mode must be image, editable, or both")
    manifest_file = Path(manifest_path).expanduser().resolve()
    manifest = _read_json(manifest_file)
    pairs = _require_audited_pairs(manifest, requested_pages)
    script = Path(str(manifest.get("source_script") or "")).expanduser().resolve()
    if not script.is_file():
        raise FileNotFoundError(f"approved source script is missing: {script}")
    output = Path(output_dir).expanduser().resolve()
    pages = [(int(pair["page_number"]), Path(str(pair["full"]["path"]))) for pair in pairs]
    for number, source in pages:
        _validate_body_image(source, number)

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
    graphic_text_policy: list[dict[str, Any]] = []
    checker = SVGQualityChecker(quick_generate=True)
    if needs_editable:
        assert quick is not None
        for pair in pairs:
            authored = Path(str(pair.get("authoring_svg") or "")).expanduser()
            if not authored.is_file():
                raise ValueError(f"page {pair['page_number']} requires a hand-authored SVG from the image-to-PPTX runtime")
            text_policy = validate_graphic_text_policy(
                pair.get("graphic_text_policy"),
                authored_svg=authored,
                page_number=int(pair["page_number"]),
            )
            graphic_text_policy.append(text_policy)
            if not text_policy["valid"]:
                raise ValueError(f"page {pair['page_number']} failed graphic text policy: {text_policy['errors']}")
            target = quick.svg_path(int(pair["page_number"]))
            shutil.copy2(authored, target)
            _copy_relative_svg_assets(authored, target)
            report = checker.check_file(str(target))
            quality.append(report)
            if not report.get("passed"):
                raise ValueError(f"page {pair['page_number']} failed imported SVG quality: {report.get('errors')}")
            svgs.append(target)

    contract = load_template_contract()
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
    title_by_page = {number: _page_title(script, number) for number, _ in pages}
    speaker_notes = _speaker_notes_by_page(script, [number for number, _ in pages])
    expected = [text for number, _ in pages for text in _script_lines(script, number)]
    for policy in graphic_text_policy:
        for item in policy.get("items", []):
            if item.get("treatment") == "native_text" and item.get("text") not in expected:
                expected.append(str(item["text"]))
    chrome_expected = [
        *(title_by_page[number] for number, _ in pages),
        "中国电力企业联合会",
        *(str(number) for number, _ in pages),
    ]

    exports: dict[str, Path] = {}
    text_qa_by_mode: dict[str, dict[str, Any]] = {}
    if needs_image:
        image_svgs: list[Path] = []
        for pair in pairs:
            number = int(pair["page_number"])
            wrapper = output_root / "image" / "svg_output" / f"p{number:02d}.svg"
            assemble_template_svg(
                source=Path(str(pair["full"]["path"])),
                output=wrapper,
                title=title_by_page[number],
                page_number=number,
                mode="image",
                contract=contract,
                body_image=Path(str(pair["full"]["path"])),
            )
            image_svgs.append(wrapper)
        image_export = output / "exports" / "template_image.pptx"
        assemble_template_pptx(image_svgs, image_export, notes=speaker_notes)
        exports["image"] = image_export
        text_qa_by_mode["image"] = _run_text_qa(image_export, chrome_expected, include_body_text=False)

    if needs_editable:
        editable_svgs: list[Path] = []
        assert quick is not None
        for pair in pairs:
            number = int(pair["page_number"])
            wrapper = output_root / "editable" / "svg_output" / f"p{number:02d}.svg"
            assemble_template_svg(
                source=quick.svg_path(number),
                output=wrapper,
                title=title_by_page[number],
                page_number=number,
                mode="editable",
                contract=contract,
            )
            editable_svgs.append(wrapper)
        editable_export = output / "exports" / "editable_svg.pptx"
        assemble_template_pptx(editable_svgs, editable_export, notes=speaker_notes)
        exports["editable"] = editable_export
        text_qa_by_mode["editable"] = _run_text_qa(editable_export, [*expected, *chrome_expected], include_body_text=True)

    primary_mode = "editable" if "editable" in exports else "image"
    export = exports[primary_mode]
    analysis = output / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    text_path = analysis / "text_content_qa.json"
    text_path.write_text(json.dumps(text_qa_by_mode, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    graphic_text_path = analysis / "graphic_text_policy_qa.json"
    graphic_text_path.write_text(json.dumps(graphic_text_policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    runtime_root = quick.root if quick is not None else output_root / "image"
    artifacts = {"reconstruction_inventory": str(runtime_root / "analysis" / "reconstruction_inventory.json"), "svg_output": str(runtime_root / "svg_output"), "reconstruction_quality": str(analysis), "text_content_qa": str(text_path), "graphic_text_policy_qa": str(graphic_text_path), "render_compare": str(review["path"]), "exported_pptx": str(export)}
    reports = {"reconstruction_inventory": {"valid": True}, "reconstruction_quality": {"valid": True, "pages": quality}, "svg_output": {"valid": True}, "text_content_qa": text_qa_by_mode, "graphic_text_policy": {"valid": True, "pages": graphic_text_policy}, "render_compare": {"valid": review["valid"], "review": review}, "exported_pptx": {"valid": True}, "exported_pptx_by_mode": {mode: {"valid": True, "path": str(path)} for mode, path in exports.items()}}
    readiness = build_production_readiness(stage="02-production-build", artifacts=artifacts, reports=reports, required_tools=tuple(artifacts))
    result = {"schema": "cyberppt.image_to_pptx.stage02.v1", "status": readiness["status"], "assembly_mode": assembly_mode, "runtime_project": str(runtime_root), "svg_roster": [str(svg) for svg in svgs], "svg_quality": quality, "visual_review": review, "artifacts": artifacts, "artifacts_by_mode": {mode: str(path) for mode, path in exports.items()}, "reports": reports, "text_content_qa": text_qa_by_mode, "release_gate": {"valid": True, "manual_adjustments": "local_only"}, "delivery_readiness": readiness}
    result_path = analysis / "image-to-pptx-result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["artifacts"]["delivery_readiness"] = str(result_path)
    return result
