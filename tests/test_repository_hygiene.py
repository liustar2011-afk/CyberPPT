from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_MARKER = "/workbench/imagegen/builds/"
TRANSIENT_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
TRANSIENT_DIR_NAMES = {"raw", "renders", "office_render", "image_to_pptx_runtime"}
TRANSIENT_REPORT_SUFFIXES = (
    ".png.report.json",
    ".jpg.report.json",
    ".jpeg.report.json",
    ".webp.report.json",
)


def _tracked_files() -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(path for path in result.stdout.split("\0") if path)


def _is_stage02_build_path(path: str) -> bool:
    return BUILD_MARKER in f"/{path}"


def test_stage02_runtime_images_are_not_tracked() -> None:
    offenders = [
        path
        for path in _tracked_files()
        if _is_stage02_build_path(path)
        and PurePosixPath(path).suffix.lower() in TRANSIENT_IMAGE_SUFFIXES
    ]
    assert not offenders, "Stage 02 runtime images must stay out of Git:\n" + "\n".join(offenders)


def test_stage02_runtime_directories_are_not_tracked() -> None:
    offenders: list[str] = []
    for path in _tracked_files():
        if not _is_stage02_build_path(path):
            continue
        parts = set(PurePosixPath(path).parts)
        if parts & TRANSIENT_DIR_NAMES:
            offenders.append(path)
    assert not offenders, "Stage 02 transient runtime directories must stay out of Git:\n" + "\n".join(offenders)


def test_stage02_image_enhancer_reports_are_not_tracked() -> None:
    offenders = [
        path
        for path in _tracked_files()
        if _is_stage02_build_path(path)
        and path.lower().endswith(TRANSIENT_REPORT_SUFFIXES)
    ]
    assert not offenders, "Image enhancer reports are machine-local runtime evidence:\n" + "\n".join(offenders)
