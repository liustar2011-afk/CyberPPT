from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.dual_image_overlay.clean_stage import clean_stage, clear_stale_bytecode_cache


def _make_project(root: Path) -> None:
    (root / "analysis" / "ocr").mkdir(parents=True)
    (root / "analysis" / "ocr" / "page_006_text_layout.json").write_text("{}", encoding="utf-8")
    (root / "analysis" / "semantic_plan").mkdir(parents=True)
    (root / "analysis" / "semantic_plan" / "page_006_semantic_plan.json").write_text("{}", encoding="utf-8")
    (root / "analysis" / "workspace_assignment").mkdir(parents=True)
    (root / "analysis" / "workspace_assignment" / "page_006_workspace_assignment.json").write_text(
        "{}", encoding="utf-8"
    )
    (root / "analysis" / "template_gate.json").write_text("{}", encoding="utf-8")
    (root / "exports").mkdir(parents=True)
    (root / "exports" / "project.pptx").write_text("stub", encoding="utf-8")
    (root / "svg_output").mkdir(parents=True)
    (root / "svg_output" / "page_006.svg").write_text("<svg/>", encoding="utf-8")


def test_default_keeps_ocr_cache_and_clears_downstream_dirs() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        _make_project(root)

        clean_stage(root)

        assert (root / "analysis" / "ocr" / "page_006_text_layout.json").is_file()
        assert not (root / "analysis" / "semantic_plan" / "page_006_semantic_plan.json").exists()
        assert not (root / "analysis" / "workspace_assignment" / "page_006_workspace_assignment.json").exists()
        assert not (root / "exports" / "project.pptx").exists()
        assert not (root / "svg_output" / "page_006.svg").exists()
        assert not (root / "analysis" / "template_gate.json").exists()
        # Directories themselves should be recreated empty, ready for a rerun.
        assert (root / "analysis" / "semantic_plan").is_dir()
        assert (root / "exports").is_dir()


def test_fresh_ocr_flag_also_clears_ocr_cache() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        _make_project(root)

        clean_stage(root, keep_ocr=False)

        assert not (root / "analysis" / "ocr" / "page_006_text_layout.json").exists()
        assert (root / "analysis" / "ocr").is_dir()


def test_dry_run_reports_without_deleting() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        _make_project(root)

        removed = clean_stage(root, dry_run=True)

        assert any("semantic_plan" in path for path in removed)
        assert (root / "analysis" / "semantic_plan" / "page_006_semantic_plan.json").is_file()
        assert (root / "analysis" / "ocr" / "page_006_text_layout.json").is_file()


def test_handles_missing_directories_gracefully() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        # No pre-existing structure at all.
        removed = clean_stage(root)
        assert removed == []
        assert (root / "analysis" / "semantic_plan").is_dir()


def test_clear_stale_bytecode_cache_removes_pycache_dirs() -> None:
    package_dir = Path(__file__).resolve().parents[1] / "scripts" / "dual_image_overlay"
    marker_dir = package_dir / "__pycache__"
    already_existed = marker_dir.is_dir()
    marker_dir.mkdir(exist_ok=True)
    marker_file = marker_dir / "_test_clean_stage_marker.pyc"
    marker_file.write_bytes(b"stale")
    try:
        removed = clear_stale_bytecode_cache()
        assert str(marker_dir) in removed
        assert not marker_file.exists()
    finally:
        if marker_dir.is_dir() and not already_existed:
            shutil.rmtree(marker_dir, ignore_errors=True)


def test_clear_stale_bytecode_cache_dry_run_does_not_delete() -> None:
    package_dir = Path(__file__).resolve().parents[1] / "scripts" / "dual_image_overlay"
    marker_dir = package_dir / "__pycache__"
    already_existed = marker_dir.is_dir()
    marker_dir.mkdir(exist_ok=True)
    marker_file = marker_dir / "_test_clean_stage_marker.pyc"
    marker_file.write_bytes(b"stale")
    try:
        removed = clear_stale_bytecode_cache(dry_run=True)
        assert str(marker_dir) in removed
        assert marker_file.exists()
    finally:
        marker_file.unlink(missing_ok=True)
        if marker_dir.is_dir() and not already_existed:
            shutil.rmtree(marker_dir, ignore_errors=True)
