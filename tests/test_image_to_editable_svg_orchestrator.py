from pathlib import Path

import pytest

from scripts.image_to_editable_svg.orchestrator import run_image_to_editable_svg


def test_retired_ocr_route_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="legacy OCR/image-to-editable-SVG route is disabled"):
        run_image_to_editable_svg(
            project=tmp_path / "project",
            manifest_path=tmp_path / "manifest.json",
            output_dir=tmp_path / "out",
            requested_pages=[1],
        )
