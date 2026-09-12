"""Small-tool build facade for CyberPPT.

This module deliberately keeps the user-facing command thin.  The existing
Stage 02 implementation remains the production engine; ``cyberppt build`` only
chooses practical defaults, infers the page range/workspace, and gives repeated
runs a stable build id so successful pages can be reused automatically.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cyberppt.commands.final_script_pages import run_final_script_pages
from scripts.imagegen_pipeline.deliverable_prompt import parse_page_blocks


def _project_root_for_script(script: Path) -> Path | None:
    """Return the nearest initialized CyberPPT project containing ``script``."""

    script = script.expanduser().resolve()
    for candidate in (script.parent, *script.parent.parents):
        if (candidate / "manifest.yml").is_file():
            return candidate
    return None


def _default_workspace(script: Path) -> Path:
    script = script.expanduser().resolve()
    return script.parent / f"{script.stem}.cyberppt"


def _all_pages_arg(script: Path) -> str:
    pages = sorted(int(page) for page in parse_page_blocks(script))
    if not pages:
        raise ValueError(f"script contains no numbered pages: {script}")
    if len(pages) == 1:
        return str(pages[0])
    if pages == list(range(pages[0], pages[-1] + 1)):
        return f"{pages[0]}-{pages[-1]}"
    return ",".join(str(page) for page in pages)


def _stable_build_id(
    *,
    script: Path,
    pages_raw: str,
    mode: str,
    image_model: str | None,
    image_quality: str,
) -> str:
    material = {
        "script": str(script.expanduser().resolve()),
        "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        "pages": pages_raw,
        "mode": mode,
        "image_model": image_model or "<default>",
        "image_quality": image_quality,
    }
    payload = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "build-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def build_presentation(
    script: Path,
    *,
    project: Path | None = None,
    pages_raw: str | None = None,
    mode: str = "image",
    image_model: str | None = None,
    image_quality: str = "max",
    image_timeout: int = 600,
    force: bool = False,
    build_id: str | None = None,
) -> dict[str, Any]:
    """Build a presentation through the existing production engine.

    ``image`` is the zero-manual-step default.  ``editable`` and ``both`` use
    the same audited full image and may pause once for the existing local SVG
    author/review step; rerunning the same command resumes the same build.
    """

    source = script.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"script not found: {source}")
    if mode not in {"image", "editable", "both"}:
        raise ValueError("mode must be image, editable, or both")

    detected_project = _project_root_for_script(source)
    workspace = (
        project.expanduser().resolve()
        if project is not None
        else detected_project or _default_workspace(source)
    )
    pages = pages_raw.strip() if pages_raw and pages_raw.strip() else _all_pages_arg(source)
    resolved_build_id = build_id or _stable_build_id(
        script=source,
        pages_raw=pages,
        mode=mode,
        image_model=image_model,
        image_quality=image_quality,
    )

    # A script outside an initialized project is treated as an external Stage 02
    # input.  This is the common small-tool path and intentionally avoids asking
    # the user to understand Stage 01 project state.
    external_script = detected_project is None or workspace != detected_project

    return run_final_script_pages(
        project=workspace,
        script=source,
        pages_raw=pages,
        production_build=True,
        assembly_mode=mode,
        generate_images=True,
        image_model=image_model,
        image_quality=image_quality,
        image_timeout=image_timeout,
        force_images=force,
        build_id=resolved_build_id,
        external_script=external_script,
    )


def compact_build_result(
    summary: dict[str, Any],
    *,
    script: Path,
    project: Path,
    mode: str,
) -> dict[str, Any]:
    """Return the small user-facing result instead of the internal run receipt."""

    artifacts = summary.get("artifacts") if isinstance(summary.get("artifacts"), dict) else {}
    outputs = artifacts.get("exported_pptx_by_mode") if isinstance(artifacts, dict) else None
    if not isinstance(outputs, dict) or not outputs:
        exported = artifacts.get("exported_pptx") if isinstance(artifacts, dict) else None
        outputs = {mode: exported} if isinstance(exported, str) and exported else {}

    workspace = artifacts.get("output_dir") if isinstance(artifacts, dict) else None
    if not workspace:
        manifest = summary.get("manifest")
        workspace = str(Path(str(manifest)).parent) if manifest else str(project)

    result: dict[str, Any] = {
        "status": summary.get("status", "unknown"),
        "mode": mode,
        "script": str(script.expanduser().resolve()),
        "project": str(project.expanduser().resolve()),
        "pages": summary.get("pages") or [],
        "build_id": summary.get("build_id"),
        "workspace": workspace,
        "pptx": outputs,
    }
    actions = summary.get("actions")
    if isinstance(actions, list) and actions:
        result["actions"] = actions
    if result["status"] == "needs_action":
        result["next"] = "Complete the listed editable-page action, then rerun the same cyberppt build command."
    return result


__all__ = [
    "build_presentation",
    "compact_build_result",
]
