"""CyberPPT adapter contract for the vendored three-image-to-PPT pipeline."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from PIL import Image, UnidentifiedImageError

from scripts.dual_image_overlay.rebuild_engine.codex_oauth_image import run_codex_image


FULL_IMAGE_MODE = "full_image_ppt"
EDITABLE_TEXT_MODE = "editable_text_three_image"
VENDOR_TWO_IMAGE_MODE = "two-image"
VENDOR_THREE_IMAGE_MODE = "three-image"
_SUPPORTED_VENDOR_INPUT_MODES = {VENDOR_TWO_IMAGE_MODE, VENDOR_THREE_IMAGE_MODE}
_SUPPORTED_MODES = {FULL_IMAGE_MODE, EDITABLE_TEXT_MODE}
_REPO_ROOT = Path(__file__).resolve().parents[2]
VENDOR_ROOT = _REPO_ROOT / "vendor" / "three-image-to-ppt"
VENDOR_RUNNER = _REPO_ROOT / "vendor" / "three-image-to-ppt" / "scripts" / "run_pipeline.py"
VENDOR_VISION_OCR = VENDOR_ROOT / "scripts" / "vision_ocr.swift"
VENDOR_TEXT_RENDERER = VENDOR_ROOT / "scripts" / "render_text_image.py"

FullGenerator = Callable[[str, Path], Path]
BackgroundGenerator = Callable[[Path, Path], Path]
OcrGenerator = Callable[[Path, Path], Path]
TextRenderer = Callable[[Path, Path, Path], Path]

BACKGROUND_PROMPT = (
    "Edit the supplied slide image into a text-free background. Remove only letters, "
    "numbers, and punctuation. Preserve the canvas size, layout, containers, icons, "
    "arrows, borders, shadows, colors, spacing, and all non-text geometry exactly. "
    "Do not recenter or rebalance the composition."
)


def _read_project_manifest(project: Path) -> str:
    path = project.expanduser().resolve() / "manifest.yml"
    if not path.is_file():
        raise ValueError(f"project manifest is missing: {path}")
    return path.read_text(encoding="utf-8")


def get_production_mode(project: Path) -> str:
    """Return the explicit project mode, preserving legacy defaults."""

    match = re.search(r"^production_mode:\s*([^\s#]+)\s*$", _read_project_manifest(project), re.MULTILINE)
    mode = match.group(1) if match else FULL_IMAGE_MODE
    if mode not in _SUPPORTED_MODES:
        supported = ", ".join(sorted(_SUPPORTED_MODES))
        raise ValueError(f"unsupported production_mode: {mode}; expected one of {supported}")
    return mode


def _parse_pages(pages_raw: str) -> list[int]:
    pages: set[int] = set()
    for raw in pages_raw.split(","):
        item = raw.strip()
        if not item:
            continue
        if "-" in item:
            start, end = (int(value.strip()) for value in item.split("-", 1))
            if start > end:
                raise ValueError(f"invalid page range: {item}")
            pages.update(range(start, end + 1))
        else:
            pages.add(int(item))
    if not pages:
        raise ValueError("at least one page is required")
    return sorted(pages)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _path_from_role(role: dict[str, Any] | None, base: Path) -> Path | None:
    if not isinstance(role, dict):
        return None
    raw = role.get("path") or role.get("filename")
    if not raw:
        return None
    path = Path(str(raw)).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def _path_from_value(value: object, base: Path) -> Path | None:
    if not value:
        return None
    path = Path(str(value)).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def _path_from_role_or_default(
    role: dict[str, Any] | None,
    base: Path,
    default_path: Path,
) -> Path:
    path = _path_from_role(role, base)
    return path if path is not None else default_path.resolve()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_image_set(paths: dict[str, Path]) -> tuple[int, int]:
    sizes: dict[str, tuple[int, int]] = {}
    for role, path in paths.items():
        if not path.is_file():
            raise ValueError(f"{role} image is not readable: {path}")
        try:
            with Image.open(path) as image:
                image.load()
                sizes[role] = image.size
        except (OSError, UnidentifiedImageError) as exc:
            raise ValueError(f"{role} image is not readable: {path}") from exc
    if len(set(sizes.values())) != 1:
        roles = ", ".join(role.upper() for role in paths)
        raise ValueError(f"{roles} image dimensions must be identical")
    width, height = next(iter(sizes.values()))
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")
    return width, height


def _default_full_generator(prompt: str, output_path: Path) -> Path:
    return run_codex_image(prompt=prompt, output_path=output_path)


def _default_background_generator(full_path: Path, output_path: Path) -> Path:
    return run_codex_image(
        prompt=BACKGROUND_PROMPT,
        output_path=output_path,
        image_paths=[full_path],
    )


def _default_ocr_generator(image_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["swift", str(VENDOR_VISION_OCR), str(image_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "Vision OCR failed"
        raise RuntimeError(message)
    output_path.write_text(completed.stdout, encoding="utf-8")
    return output_path


def _default_text_renderer(ocr_path: Path, reference_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, str(VENDOR_TEXT_RENDERER), str(ocr_path), str(reference_path), str(output_path)],
        check=True,
    )
    return output_path


def _write_identity_registration(path: Path, page_number: int) -> Path:
    return _write_json(
        path,
        {
            "transform_id": f"TF-PAGE{page_number:03d}-IDENTITY",
            "matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        },
    )


def _asset_dir(project: Path, pages_raw: str, page_number: int) -> Path:
    return _editable_text_root(project, pages_raw) / "assets" / f"page_{page_number:03d}"


def _ensure_editable_assets(
    project: Path,
    pages_raw: str,
    page: dict[str, Any],
    manifest_dir: Path,
    input_mode: str,
    *,
    full_generator: FullGenerator,
    background_generator: BackgroundGenerator,
    ocr_generator: OcrGenerator,
    text_renderer: TextRenderer,
) -> dict[str, Any]:
    page_number = int(page.get("page_number", 0))
    if page_number <= 0:
        raise ValueError("editable-text pair is missing a positive page_number")
    asset_dir = _asset_dir(project, pages_raw, page_number)
    asset_dir.mkdir(parents=True, exist_ok=True)

    full_role = page.get("full") if isinstance(page.get("full"), dict) else {}
    full_path = _path_from_role_or_default(
        full_role,
        manifest_dir,
        asset_dir / f"page_{page_number:03d}_full.png",
    )
    if not full_path.is_file():
        prompt = full_role.get("prompt") if isinstance(full_role, dict) else None
        if not isinstance(prompt, str) or not prompt:
            raise ValueError(f"{input_mode} page {page_number} requires FULL image or full.prompt")
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_generator(prompt, full_path)
    if not full_path.is_file():
        raise ValueError(f"FULL image was not produced for page {page_number}: {full_path}")

    background_path = _path_from_role_or_default(
        page.get("background") if isinstance(page.get("background"), dict) else None,
        manifest_dir,
        asset_dir / f"page_{page_number:03d}_background.png",
    )
    if not background_path.is_file():
        background_path.parent.mkdir(parents=True, exist_ok=True)
        background_generator(full_path, background_path)
    if not background_path.is_file():
        raise ValueError(f"BACKGROUND image was not produced for page {page_number}: {background_path}")

    ocr_path = _path_from_value(page.get("ocr"), manifest_dir) or asset_dir / f"page_{page_number:03d}_ocr.full.json"
    if not ocr_path.is_file():
        ocr_generator(full_path, ocr_path)
    if not ocr_path.is_file():
        raise ValueError(f"OCR JSON was not produced for page {page_number}: {ocr_path}")

    registration_path = _path_from_value(page.get("registration"), manifest_dir) or asset_dir / f"page_{page_number:03d}_registration.json"
    if not registration_path.is_file():
        _write_identity_registration(registration_path, page_number)

    prepared = {
        **page,
        "full": {**(full_role if isinstance(full_role, dict) else {}), "path": str(full_path)},
        "background": {
            **(page.get("background") if isinstance(page.get("background"), dict) else {}),
            "path": str(background_path),
        },
        "ocr": str(ocr_path),
        "registration": str(registration_path),
    }
    if input_mode == VENDOR_THREE_IMAGE_MODE:
        text_path = _path_from_role_or_default(
            page.get("text") if isinstance(page.get("text"), dict) else None,
            manifest_dir,
            asset_dir / f"page_{page_number:03d}_text.png",
        )
        if not text_path.is_file():
            text_renderer(ocr_path, full_path, text_path)
        if not text_path.is_file():
            raise ValueError(f"TEXT image was not produced for page {page_number}: {text_path}")
        prepared["text"] = {
            **(page.get("text") if isinstance(page.get("text"), dict) else {}),
            "path": str(text_path),
        }
    _write_json(
        asset_dir / "asset_manifest.json",
        {
            "schema": "cyberppt.editable_text_assets.v1",
            "page_number": page_number,
            "input_mode": input_mode,
            "full": str(full_path),
            "background": str(background_path),
            "ocr": str(ocr_path),
            "registration": str(registration_path),
            **({"text": str(prepared["text"]["path"])} if input_mode == VENDOR_THREE_IMAGE_MODE else {}),
        },
    )
    return prepared


def _editable_text_job(
    project: Path,
    page: dict[str, Any],
    manifest_dir: Path,
    input_mode: str,
) -> dict[str, Any]:
    page_number = int(page.get("page_number", 0))
    if page_number <= 0:
        raise ValueError("editable-text pair is missing a positive page_number")
    paths = {
        "full": _path_from_role(page.get("full"), manifest_dir),
        "background": _path_from_role(page.get("background"), manifest_dir),
    }
    if input_mode == VENDOR_THREE_IMAGE_MODE:
        paths["text"] = _path_from_role(page.get("text"), manifest_dir)
    missing = [role.upper() for role, path in paths.items() if path is None]
    if missing:
        raise ValueError(f"{input_mode} page {page_number} requires: {', '.join(missing)}")
    resolved = {role: path for role, path in paths.items() if path is not None}
    width, height = _validate_image_set(resolved)
    output_dir = (
        project.expanduser().resolve()
        / "workbench/stages/02-blueprint-dual-image"
        / "editable_text"
        / f"page_{page_number:03d}"
    )
    ocr_path = _path_from_value(page.get("ocr"), manifest_dir)
    registration_path = _path_from_value(page.get("registration"), manifest_dir)
    if ocr_path is None or registration_path is None:
        raise ValueError(f"{input_mode} page {page_number} requires OCR and registration JSON")
    for role, path in (("OCR", ocr_path), ("registration", registration_path)):
        if not path.is_file():
            raise ValueError(f"{role} input is not readable: {path}")
    job = {
        "page_id": f"page-{page_number:03d}",
        "page_number": page_number,
        "full": str(resolved["full"]),
        "background": str(resolved["background"]),
        "ocr": str(ocr_path),
        "registration": str(registration_path),
        "output_dir": str(output_dir),
        "inputs": {
            role: {"path": str(path), "sha256": _sha256(path)}
            for role, path in {
                "full": resolved["full"],
                "background": resolved["background"],
                "ocr": ocr_path,
                "registration": registration_path,
            }.items()
        },
        "canvas": {"width_px": width, "height_px": height},
    }
    if input_mode == VENDOR_THREE_IMAGE_MODE:
        job["text"] = str(resolved["text"])
        job["inputs"]["text"] = {"path": str(resolved["text"]), "sha256": _sha256(resolved["text"])}
    return job


def build_editable_text_batch(
    project: Path,
    pages_raw: str,
    pairs_path: Path,
    *,
    input_mode: str = VENDOR_TWO_IMAGE_MODE,
    full_generator: FullGenerator | None = None,
    background_generator: BackgroundGenerator | None = None,
    ocr_generator: OcrGenerator | None = None,
    text_renderer: TextRenderer | None = None,
) -> dict[str, Any]:
    """Build a deterministic vendor batch manifest from approved page pairs."""

    manifest_path = pairs_path.expanduser().resolve()
    if input_mode not in _SUPPORTED_VENDOR_INPUT_MODES:
        supported = ", ".join(sorted(_SUPPORTED_VENDOR_INPUT_MODES))
        raise ValueError(f"unsupported vendor input_mode: {input_mode}; expected one of {supported}")
    payload = _read_json(manifest_path)
    pairs = payload.get("pairs")
    if not isinstance(pairs, list):
        raise ValueError(f"page image manifest must contain pairs[]: {manifest_path}")
    wanted = set(_parse_pages(pages_raw))
    selected = [pair for pair in pairs if isinstance(pair, dict) and int(pair.get("page_number", 0)) in wanted]
    if {int(pair["page_number"]) for pair in selected} != wanted:
        raise ValueError("page image manifest does not contain every requested page")
    jobs = [
        _editable_text_job(
            project,
            _ensure_editable_assets(
                project,
                pages_raw,
                pair,
                manifest_path.parent,
                input_mode,
                full_generator=full_generator or _default_full_generator,
                background_generator=background_generator or _default_background_generator,
                ocr_generator=ocr_generator or _default_ocr_generator,
                text_renderer=text_renderer or _default_text_renderer,
            ),
            manifest_path.parent,
            input_mode,
        )
        for pair in sorted(selected, key=lambda item: int(item["page_number"]))
    ]
    return {
        "schema": "cyberppt.editable_text_batch.v1",
        "input_mode": input_mode,
        "pages": jobs,
    }


def build_three_image_batch(project: Path, pages_raw: str, pairs_path: Path) -> dict[str, Any]:
    """Backward-compatible wrapper for the default editable-text vendor batch."""

    return build_editable_text_batch(project, pages_raw, pairs_path)


def _find_pairs_manifest(project: Path, pages_raw: str) -> Path:
    root = project.expanduser().resolve()
    candidates = list((root / "workbench/stages/02-blueprint-dual-image").glob("*/page_image_pairs.json"))
    candidates.extend(path for path in root.glob("page_image_pairs.json") if path not in candidates)
    if not candidates:
        candidates = list(root.rglob("page_image_pairs.json"))
    if not candidates:
        raise ValueError(f"page image manifest is required for editable-text pages {pages_raw}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _editable_text_root(project: Path, pages_raw: str) -> Path:
    return project.expanduser().resolve() / "workbench/stages/02-blueprint-dual-image" / "editable_text" / _pages_slug(pages_raw)


def _pages_slug(pages_raw: str) -> str:
    pages = _parse_pages(pages_raw)
    return f"pages_{pages[0]:03d}_{pages[-1]:03d}" if pages == list(range(pages[0], pages[-1] + 1)) else "pages_" + "_".join(f"{page:03d}" for page in pages)


def _result_path(project: Path, pages_raw: str) -> Path:
    return _editable_text_root(project, pages_raw) / "editable_text_result.json"


def editable_text_result_path(project: Path, pages_raw: str) -> Path:
    """Return the deterministic result manifest path for a page selection."""

    return _result_path(project, pages_raw)


def _collect_vendor_results(project: Path, pages_raw: str, batch: dict[str, Any], exit_code: int) -> dict[str, Any]:
    pages: dict[str, dict[str, Any]] = {}
    has_review = False
    has_failed = False
    for job in batch["pages"]:
        page_number = int(job["page_number"])
        output_dir = Path(str(job["output_dir"]))
        qa_path = output_dir / "qa.json"
        page_json = output_dir / "page.json"
        render_path = output_dir / "slide-1.png"
        status = "failed"
        qa: dict[str, Any] = {}
        if qa_path.is_file():
            try:
                qa = _read_json(qa_path)
                status = str(qa.get("status", "failed"))
            except (OSError, ValueError, json.JSONDecodeError):
                status = "failed"
        if status not in {"passed", "review", "failed"} or not page_json.is_file() or not render_path.is_file():
            status = "failed"
        has_review = has_review or status == "review"
        has_failed = has_failed or status == "failed"
        pages[str(page_number)] = {
            "page_number": page_number,
            "status": status,
            "output_dir": str(output_dir),
            "full_path": str(job.get("full", "")),
            "background_path": str(job.get("background", "")),
            "text_path": str(job.get("text", "")),
            "page_json": str(page_json),
            "qa": str(qa_path),
            "render": str(render_path),
            "artifacts_sha256": {
                name: _sha256(path)
                for name, path in (("page_json", page_json), ("qa", qa_path), ("render", render_path))
                if path.is_file()
            },
        }
    status = "failed" if has_failed else "review_required" if has_review else "passed"
    result = {
        "schema": "cyberppt.editable_text_result.v1",
        "project": str(project.expanduser().resolve()),
        "pages_raw": pages_raw,
        "status": status,
        "vendor_exit_code": exit_code,
        "batch_manifest": str(_editable_text_root(project, pages_raw) / "three_image_batch.json"),
        "pages": pages,
    }
    result_path = _result_path(project, pages_raw)
    _write_json(result_path, result)
    result["result_manifest"] = str(result_path)
    _write_json(result_path, result)
    return result


def run_three_image_batch(
    project: Path,
    pages_raw: str,
    *,
    input_mode: str = VENDOR_TWO_IMAGE_MODE,
) -> dict[str, Any]:
    """Run the vendored batch pipeline and collect authoritative page QA."""

    root = project.expanduser().resolve()
    pairs_path = _find_pairs_manifest(root, pages_raw)
    batch = build_editable_text_batch(root, pages_raw, pairs_path, input_mode=input_mode)
    batch_root = _editable_text_root(root, pages_raw)
    batch_path = _write_json(batch_root / "three_image_batch.json", batch)
    completed = subprocess.run(
        [sys.executable, str(VENDOR_RUNNER), "--mode", "batch", "--manifest", str(batch_path)],
        check=False,
        cwd=str(_REPO_ROOT),
    )
    return _collect_vendor_results(root, pages_raw, batch, completed.returncode)


def _approval_path(project: Path, pages_raw: str) -> Path:
    return _editable_text_root(project, pages_raw) / "editable_text_review.approved.json"


def stage_editable_text_review(project: Path, pages_raw: str) -> Path:
    result_path = _result_path(project, pages_raw)
    if not result_path.is_file():
        raise ValueError("editable-text result is required; run the editable-text batch first")
    pending = _editable_text_root(project, pages_raw) / "editable_text_review.pending.json"
    return _write_json(
        pending,
        {
            "schema": "cyberppt.editable_text_review.v1",
            "status": "pending_confirmation",
            "result_manifest": str(result_path),
            "result_sha256": _sha256(result_path),
            "option_id": "confirm_editable_text",
        },
    )


def approve_editable_text_review(project: Path, pages_raw: str) -> Path:
    result_path = _result_path(project, pages_raw)
    if not result_path.is_file():
        raise ValueError("editable-text result is required before approval")
    return _write_json(
        _approval_path(project, pages_raw),
        {
            "schema": "cyberppt.editable_text_review_approval.v1",
            "approved": True,
            "result_manifest": str(result_path),
            "result_sha256": _sha256(result_path),
            "option_id": "confirm_editable_text",
        },
    )


def _approval_is_current(project: Path, pages_raw: str, result_path: Path) -> bool:
    approval = _approval_path(project, pages_raw)
    if not approval.is_file():
        return False
    try:
        payload = _read_json(approval)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return payload.get("approved") is True and payload.get("result_sha256") == _sha256(result_path)


def assert_editable_text_batch_ready(project: Path, pages_raw: str) -> Path:
    result_path = _result_path(project, pages_raw)
    if not result_path.is_file():
        raise ValueError("editable-text result is required; run the editable-text batch first")
    result = _read_json(result_path)
    pages = result.get("pages")
    if not isinstance(pages, dict) or not pages:
        raise ValueError("editable-text batch contains no page results")
    if any(item.get("status") == "failed" for item in pages.values() if isinstance(item, dict)):
        raise ValueError("editable-text batch has failed pages")
    if result.get("status") == "review_required" and not _approval_is_current(project, pages_raw, result_path):
        raise ValueError("editable-text review approval is required")
    if result.get("status") not in {"passed", "review_required"}:
        raise ValueError(f"editable-text batch is not ready: {result.get('status')}")
    return result_path
