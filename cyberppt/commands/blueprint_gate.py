"""Stage-02 review gates for visual style, drawing input, and generated images."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.commands.analysis_expression_gate import assert_analysis_expression_ready, validate_drawing_script
from scripts.dual_image_overlay.style_library import (
    STYLE_LIBRARY_PATH,
    load_style_library,
    load_style_lock,
    write_project_style_lock,
)


STAGE_ROOT = Path("workbench/stages/02-blueprint-dual-image")
ANALYSIS_ROOT = Path("workbench/analysis_expression")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _stage_path(project: Path, name: str) -> Path:
    return project.expanduser().resolve() / STAGE_ROOT / name


def _editable_text_review_is_current(project: Path) -> bool:
    manifest = project.expanduser().resolve() / "manifest.yml"
    if not manifest.is_file() or not re.search(
        r"^production_mode:\s*editable_text_three_image\s*$",
        manifest.read_text(encoding="utf-8"),
        re.MULTILINE,
    ):
        return False
    review_files = sorted(
        (project.expanduser().resolve() / STAGE_ROOT / "editable_text").glob(
            "*/editable_text_review.approved.json"
        )
    )
    for review_path in review_files:
        try:
            approval = _read_json(review_path)
            result_path = Path(str(approval.get("result_manifest", ""))).expanduser().resolve()
            if not result_path.is_file() or approval.get("result_sha256") != _sha256(result_path):
                continue
            result = _read_json(result_path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        pages = result.get("pages")
        if approval.get("approved") is True and isinstance(pages, dict) and pages:
            if all(isinstance(item, dict) and item.get("status") != "failed" for item in pages.values()):
                return True
    return False


def _analysis_approval(project: Path, gate: str) -> dict[str, Any]:
    path = project / ANALYSIS_ROOT / f"{gate}.approved.json"
    if not path.is_file():
        raise ValueError(f"{gate} approval is required")
    return _read_json(path)


def _approved_business(project: Path) -> tuple[Path, str, str]:
    approval = _analysis_approval(project, "business_script")
    artifact = Path(str(approval["artifact"]))
    if not artifact.is_file():
        raise ValueError(f"approved business_script artifact is missing: {artifact}")
    source = artifact.read_text(encoding="utf-8")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if digest != approval.get("source_sha256"):
        raise ValueError("approved business_script has changed; approve business_script again")
    return artifact, source, digest


def stage_visual_style_options(project: Path) -> Path:
    """Persist the selectable visual-style options after business content is approved."""

    root = project.expanduser().resolve()
    assert_analysis_expression_ready(root)
    business_path, _, business_sha256 = _approved_business(root)
    library = load_style_library(STYLE_LIBRARY_PATH)
    options = [
        {
            "id": f"style_{style['id']}",
            "style_id": style["id"],
            "label": style["name"],
            "description": style["scenario"],
        }
        for style in library["styles"]
    ]
    artifact = _stage_path(root, "visual_style_options.json")
    _write_json(
        artifact,
        {
            "schema": "cyberppt.visual_style_options.v1",
            "created_at": _utc_now(),
            "business_script": str(business_path),
            "business_script_sha256": business_sha256,
            "style_library": str(STYLE_LIBRARY_PATH),
            "options": options,
        },
    )
    pending = _stage_path(root, "visual_style.pending-confirmation.json")
    _write_json(
        pending,
        {
            "schema": "cyberppt.visual_style.pending_confirmation.v1",
            "status": "pending_confirmation",
            "artifact": str(artifact),
            "business_script_sha256": business_sha256,
            "question": "请选择本次汇报的视觉风格。",
            "options": options,
            "created_at": _utc_now(),
        },
    )
    approval = _stage_path(root, "visual_style.approved.json")
    if approval.exists():
        approval.unlink()
    return pending


def approve_visual_style(project: Path, option_id: str, note: str = "") -> Path:
    root = project.expanduser().resolve()
    pending = _stage_path(root, "visual_style.pending-confirmation.json")
    if not pending.is_file():
        raise FileNotFoundError("no pending visual-style selection; stage visual style options first")
    data = _read_json(pending)
    selected = next((item for item in data.get("options", []) if item.get("id") == option_id), None)
    if not isinstance(selected, dict):
        raise ValueError(f"style option is not available: {option_id}")
    _, _, business_sha256 = _approved_business(root)
    if business_sha256 != data.get("business_script_sha256"):
        raise ValueError("business_script changed; stage visual style options again")
    lock = write_project_style_lock(project=root, style_id=int(selected["style_id"]))
    approval = _stage_path(root, "visual_style.approved.json")
    _write_json(
        approval,
        {
            "schema": "cyberppt.visual_style.approval.v1",
            "approved": True,
            "approved_at": _utc_now(),
            "pending_confirmation": str(pending),
            "artifact": str(_stage_path(root, "visual_style_options.json")),
            "option_id": option_id,
            "style_lock": str(lock),
            "style_lock_sha256": _sha256(lock),
            "business_script_sha256": business_sha256,
            "note": note,
        },
    )
    return approval


def _approved_visual_style(project: Path) -> tuple[Path, str]:
    approval = _stage_path(project, "visual_style.approved.json")
    if not approval.is_file():
        raise ValueError("visual style approval is required")
    data = _read_json(approval)
    lock = Path(str(data.get("style_lock", "")))
    if not lock.is_file():
        raise ValueError(f"approved visual style lock is missing: {lock}")
    if _sha256(lock) != data.get("style_lock_sha256"):
        raise ValueError("approved visual style lock has changed; approve visual style again")
    load_style_lock(lock)
    return lock, str(data["style_lock_sha256"])


def stage_blueprint_input(
    project: Path,
    source: str,
    recommendation: str,
    options: list[dict[str, Any]],
    question: str | None = None,
) -> Path:
    """Save the clean, style-bound drawing input for human review before image generation."""

    root = project.expanduser().resolve()
    assert_analysis_expression_ready(root)
    business_path, business, business_sha256 = _approved_business(root)
    style_lock, style_lock_sha256 = _approved_visual_style(root)
    errors = validate_drawing_script(source, business)
    if errors:
        raise ValueError("; ".join(dict.fromkeys(errors)))
    if not options or any(not isinstance(item, dict) or not item.get("id") for item in options):
        raise ValueError("blueprint input requires selectable confirmation options")
    artifact = _stage_path(root, "blueprint_input.md")
    artifact.write_text(source, encoding="utf-8")
    pending = _stage_path(root, "blueprint_input.pending-confirmation.json")
    _write_json(
        pending,
        {
            "schema": "cyberppt.blueprint_input.pending_confirmation.v1",
            "status": "pending_confirmation",
            "artifact": str(artifact),
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "business_script": str(business_path),
            "business_script_sha256": business_sha256,
            "style_lock": str(style_lock),
            "style_lock_sha256": style_lock_sha256,
            "recommendation": recommendation,
            "question": question or "是否确认该蓝图输入，并据此生成逐页图片？",
            "options": options,
            "created_at": _utc_now(),
        },
    )
    approval = _stage_path(root, "blueprint_input.approved.json")
    if approval.exists():
        approval.unlink()
    return pending


def approve_blueprint_input(project: Path, option_id: str, note: str = "") -> Path:
    root = project.expanduser().resolve()
    pending = _stage_path(root, "blueprint_input.pending-confirmation.json")
    if not pending.is_file():
        raise FileNotFoundError("no pending blueprint input; stage blueprint input first")
    data = _read_json(pending)
    valid_ids = {item.get("id") for item in data.get("options", []) if isinstance(item, dict)}
    if option_id not in valid_ids:
        raise ValueError(f"blueprint input option is not available: {option_id}")
    artifact = Path(str(data["artifact"]))
    if not artifact.is_file() or _sha256(artifact) != data.get("source_sha256"):
        raise ValueError("blueprint input changed; stage it again")
    _, _, business_sha256 = _approved_business(root)
    style_lock, style_lock_sha256 = _approved_visual_style(root)
    if business_sha256 != data.get("business_script_sha256") or style_lock_sha256 != data.get("style_lock_sha256"):
        raise ValueError("business content or style changed; stage blueprint input again")
    approved = not str(option_id).startswith("revise")
    approval = _stage_path(root, "blueprint_input.approved.json")
    _write_json(
        approval,
        {
            "schema": "cyberppt.blueprint_input.approval.v1",
            "approved": approved,
            "approved_at": _utc_now(),
            "pending_confirmation": str(pending),
            "artifact": str(artifact),
            "source_sha256": data["source_sha256"],
            "business_script_sha256": business_sha256,
            "style_lock": str(style_lock),
            "style_lock_sha256": style_lock_sha256,
            "option_id": option_id,
            "note": note,
        },
    )
    return approval


def assert_blueprint_input_ready(project: Path, script: Path, style_lock: Path | None) -> Path:
    """Bind compilation to the reviewed clean drawing input and approved style lock."""

    root = project.expanduser().resolve()
    if not (root / ANALYSIS_ROOT / "contract.json").is_file():
        if style_lock is None:
            raise ValueError("an explicit visual style selection is required")
        return style_lock
    assert_analysis_expression_ready(root)
    approved_lock, approved_lock_sha256 = _approved_visual_style(root)
    if style_lock is not None and style_lock.resolve() != approved_lock.resolve():
        raise ValueError("final-script-pages must use the approved visual style lock")
    approval = _stage_path(root, "blueprint_input.approved.json")
    if not approval.is_file():
        raise ValueError("blueprint input approval is required")
    data = _read_json(approval)
    if data.get("approved") is not True:
        raise ValueError("blueprint input approval is required")
    if not script.is_file() or _sha256(script) != data.get("source_sha256"):
        raise ValueError("final-script-pages script must match the approved blueprint input")
    if data.get("style_lock_sha256") != approved_lock_sha256:
        raise ValueError("blueprint input style dependency is stale; stage and approve blueprint input again")
    business_path, business, business_sha256 = _approved_business(root)
    if data.get("business_script_sha256") != business_sha256:
        raise ValueError("blueprint input business dependency is stale; stage and approve blueprint input again")
    errors = validate_drawing_script(script.read_text(encoding="utf-8"), business)
    if errors:
        raise ValueError("approved blueprint input is invalid: " + "; ".join(errors))
    return approved_lock


def stage_speaker_notes_review(project: Path, manifest_path: Path, pages_raw: str) -> Path:
    """Persist generated speaker notes for explicit review before production assembly."""

    root = project.expanduser().resolve()
    manifest = manifest_path.expanduser().resolve()
    if not manifest.is_file():
        raise FileNotFoundError(f"speaker notes manifest not found: {manifest}")
    business_path, _, business_sha256 = _approved_business(root)
    review = _stage_path(root, "speaker_notes_review.json")
    manifest_sha256 = _sha256(manifest)
    _write_json(
        review,
        {
            "schema": "cyberppt.speaker_notes_review.v1",
            "created_at": _utc_now(),
            "manifest": str(manifest),
            "manifest_sha256": manifest_sha256,
            "business_script": str(business_path),
            "business_script_sha256": business_sha256,
            "pages_raw": pages_raw,
        },
    )
    pending = _stage_path(root, "speaker_notes_review.pending-confirmation.json")
    _write_json(
        pending,
        {
            "schema": "cyberppt.speaker_notes_review.pending_confirmation.v1",
            "status": "pending_confirmation",
            "artifact": str(review),
            "manifest": str(manifest),
            "manifest_sha256": manifest_sha256,
            "business_script": str(business_path),
            "business_script_sha256": business_sha256,
            "pages_raw": pages_raw,
            "option_id": None,
            "question": "是否确认本轮演讲者备注，并进入图片版 PPT 组装？",
            "options": [
                {"id": "confirm_speaker_notes", "label": "确认备注"},
                {"id": "revise_speaker_notes", "label": "返回修改"},
            ],
            "created_at": _utc_now(),
        },
    )
    approval = _stage_path(root, "speaker_notes_review.approved.json")
    if approval.exists():
        approval.unlink()
    return pending


def approve_speaker_notes_review(project: Path, option_id: str, note: str = "") -> Path:
    root = project.expanduser().resolve()
    pending = _stage_path(root, "speaker_notes_review.pending-confirmation.json")
    if not pending.is_file():
        raise FileNotFoundError("no pending speaker-notes review; stage speaker notes review first")
    data = _read_json(pending)
    if option_id not in {"confirm_speaker_notes", "revise_speaker_notes"}:
        raise ValueError(f"speaker notes review option is not available: {option_id}")
    manifest = Path(str(data.get("manifest", ""))).expanduser().resolve()
    if not manifest.is_file() or _sha256(manifest) != data.get("manifest_sha256"):
        raise ValueError("speaker notes changed; stage speaker notes review again")
    business_path, _, business_sha256 = _approved_business(root)
    if str(business_path) != data.get("business_script") or business_sha256 != data.get("business_script_sha256"):
        raise ValueError("business script changed; stage speaker notes review again")
    approval = _stage_path(root, "speaker_notes_review.approved.json")
    _write_json(
        approval,
        {
            "schema": "cyberppt.speaker_notes_review.approval.v1",
            "approved": option_id == "confirm_speaker_notes",
            "approved_at": _utc_now(),
            "pending_confirmation": str(pending),
            "artifact": str(_stage_path(root, "speaker_notes_review.json")),
            "manifest": str(manifest),
            "manifest_sha256": data["manifest_sha256"],
            "business_script": str(business_path),
            "business_script_sha256": business_sha256,
            "pages_raw": data["pages_raw"],
            "option_id": option_id,
            "note": note,
        },
    )
    return approval


def assert_speaker_notes_review_ready(project: Path, pages_raw: str) -> Path:
    """Require an approved, unchanged speaker-notes manifest for the selected pages."""

    root = project.expanduser().resolve()
    approval = _stage_path(root, "speaker_notes_review.approved.json")
    if not approval.is_file():
        raise ValueError("speaker notes approval is required")
    data = _read_json(approval)
    if data.get("approved") is not True:
        raise ValueError("speaker notes approval is required")
    manifest = Path(str(data.get("manifest", ""))).expanduser().resolve()
    if not manifest.is_file() or _sha256(manifest) != data.get("manifest_sha256"):
        raise ValueError("speaker notes changed; stage and approve speaker notes again")
    if data.get("pages_raw") != pages_raw:
        raise ValueError("approved speaker notes do not match the current page selection")
    business_path, _, business_sha256 = _approved_business(root)
    if str(business_path) != data.get("business_script") or business_sha256 != data.get("business_script_sha256"):
        raise ValueError("business script changed; stage and approve speaker notes again")
    return manifest


def stage_blueprint_image_review(project: Path, manifest_path: Path) -> Path:
    """Persist the generated image set as a separate review artifact before PPT assembly."""

    root = project.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"page image manifest not found: {manifest_path}")
    manifest = _read_json(manifest_path)
    images: list[dict[str, Any]] = []
    for pair in manifest.get("pairs", []):
        if not isinstance(pair, dict):
            continue
        full = pair.get("full")
        if not isinstance(full, dict):
            raise ValueError("page image manifest contains a page without a full image definition")
        image = Path(str(full.get("path", "")))
        if not image.is_file() or image.stat().st_size <= 0:
            raise FileNotFoundError(f"generated full image is missing: {image}")
        images.append({"page": pair.get("page_number"), "path": str(image), "sha256": _sha256(image)})
    if not images:
        raise ValueError("page image manifest contains no generated full images")
    artifact = _stage_path(root, "blueprint_image_review.json")
    _write_json(
        artifact,
        {
            "schema": "cyberppt.blueprint_image_review.v1",
            "created_at": _utc_now(),
            "page_image_manifest": str(manifest_path),
            "page_image_manifest_sha256": _sha256(manifest_path),
            "images": images,
        },
    )
    pending = _stage_path(root, "blueprint_image_review.pending-confirmation.json")
    _write_json(
        pending,
        {
            "schema": "cyberppt.blueprint_image_review.pending_confirmation.v1",
            "status": "pending_confirmation",
            "artifact": str(artifact),
            "question": "是否确认本轮逐页蓝图图片，并进入图片版 PPT 组装？",
            "options": [
                {"id": "confirm_blueprint_images", "label": "确认图片"},
                {"id": "revise_blueprint_images", "label": "返回调整"},
            ],
            "created_at": _utc_now(),
        },
    )
    approval = _stage_path(root, "blueprint_image_review.approved.json")
    if approval.exists():
        approval.unlink()
    return pending


def assert_controlled_imagegen_ready(project: Path, manifest_path: Path) -> None:
    """Require current, QA-passed sealed ImageGen records for every content pair."""

    root = project.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"page image manifest not found: {manifest_path}")
    manifest = _read_json(manifest_path)
    manifest_sha256 = _sha256(manifest_path)
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("page image manifest contains no content pairs")
    for pair in pairs:
        if not isinstance(pair, dict) or not isinstance(pair.get("page_number"), int):
            raise ValueError("page image manifest contains an invalid content pair")
        page = pair["page_number"]
        full = pair.get("full")
        if not isinstance(full, dict):
            raise ValueError(f"page {page} full image definition is required")
        prompt = full.get("prompt")
        path_value = full.get("path")
        if not isinstance(prompt, str) or not prompt or not isinstance(path_value, str) or not path_value:
            raise ValueError(f"page {page} full prompt and output path are required")
        output_path = Path(path_value).expanduser()
        if not output_path.is_absolute():
            output_path = (manifest_path.parent / output_path).resolve()
        else:
            output_path = output_path.resolve()
        run_path = root / "imagegen_runs" / f"page_{page}.json"
        if not run_path.is_file():
            raise ValueError(f"page {page} requires a controlled ImageGen run record")
        run = _read_json(run_path)
        if run.get("status") != "passed":
            raise ValueError(f"page {page} controlled ImageGen run is not passed")
        if run.get("manifest_sha256") != manifest_sha256:
            raise ValueError(f"page {page} controlled ImageGen manifest hash is stale")
        prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if run.get("prompt_sha256") != prompt_sha256:
            raise ValueError(f"page {page} controlled ImageGen prompt hash is stale")
        if not output_path.is_file():
            raise ValueError(f"page {page} controlled ImageGen output is missing")
        if Path(str(run.get("output_path", ""))).expanduser().resolve() != output_path:
            raise ValueError(f"page {page} controlled ImageGen output path is stale")
        output_sha256 = _sha256(output_path)
        if run.get("output_sha256") != output_sha256:
            raise ValueError(f"page {page} controlled ImageGen output hash is stale")
        qa_path = Path(str(run.get("image_text_qa", ""))).expanduser()
        if not qa_path.is_file():
            raise ValueError(f"page {page} requires passed image-text QA")
        qa = _read_json(qa_path)
        if qa.get("status") != "passed" or qa.get("deliverable_allowed") is not True:
            raise ValueError(f"page {page} image-text QA is not passed")
        if qa.get("page") != page:
            raise ValueError(f"page {page} image-text QA does not match the generated page")
        if Path(str(qa.get("image_path", ""))).expanduser().resolve() != output_path:
            raise ValueError(f"page {page} image-text QA does not match the generated output")
        if qa.get("image_sha256") != output_sha256:
            raise ValueError(f"page {page} image-text QA output hash is stale")


def approve_blueprint_image_review(project: Path, option_id: str, note: str = "") -> Path:
    root = project.expanduser().resolve()
    pending = _stage_path(root, "blueprint_image_review.pending-confirmation.json")
    if not pending.is_file():
        raise FileNotFoundError("no pending blueprint-image review; stage image review first")
    data = _read_json(pending)
    valid_ids = {item.get("id") for item in data.get("options", []) if isinstance(item, dict)}
    if option_id not in valid_ids:
        raise ValueError(f"blueprint image review option is not available: {option_id}")
    artifact = Path(str(data["artifact"]))
    review = _read_json(artifact)
    approved = option_id == "confirm_blueprint_images"
    if approved:
        manifest_path = Path(str(review.get("page_image_manifest", "")))
        if _editable_text_review_is_current(root):
            if not manifest_path.is_file():
                raise FileNotFoundError(f"page image manifest not found: {manifest_path}")
        else:
            assert_controlled_imagegen_ready(root, manifest_path)
    for image in review.get("images", []):
        path = Path(str(image.get("path", "")))
        if not path.is_file() or _sha256(path) != image.get("sha256"):
            raise ValueError("generated blueprint images changed; stage image review again")
    approval = _stage_path(root, "blueprint_image_review.approved.json")
    _write_json(
        approval,
        {
            "schema": "cyberppt.blueprint_image_review.approval.v1",
            "approved": approved,
            "approved_at": _utc_now(),
            "pending_confirmation": str(pending),
            "artifact": str(artifact),
            "option_id": option_id,
            "note": note,
        },
    )
    return approval


def assert_blueprint_image_review_ready(project: Path, manifest: dict[str, Any]) -> None:
    """Require an approved, unchanged generated-image set before image-PPT assembly."""

    root = project.expanduser().resolve()
    approval = _stage_path(root, "blueprint_image_review.approved.json")
    if not approval.is_file():
        raise ValueError("blueprint image review approval is required before image-PPT assembly")
    data = _read_json(approval)
    if data.get("approved") is not True:
        raise ValueError("blueprint image review approval is required before image-PPT assembly")
    review = _read_json(Path(str(data["artifact"])))
    reviewed_pages = {item.get("page") for item in review.get("images", []) if isinstance(item, dict)}
    manifest_pages = {
        item.get("page_number") for item in manifest.get("pairs", []) if isinstance(item, dict)
    }
    if reviewed_pages != manifest_pages:
        raise ValueError("approved blueprint images do not match the current page selection")
    for image in review.get("images", []):
        path = Path(str(image.get("path", "")))
        if not path.is_file() or _sha256(path) != image.get("sha256"):
            raise ValueError("approved blueprint images changed; stage and approve image review again")
