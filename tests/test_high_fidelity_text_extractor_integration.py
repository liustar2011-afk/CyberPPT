from pathlib import Path
from unittest.mock import patch

from PIL import Image

from scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild import _extract_legacy_page_text


def test_legacy_caller_sends_one_selected_image_to_facade(tmp_path: Path) -> None:
    image = tmp_path / "page-004_full.png"
    Image.new("RGB", (40, 30), "white").save(image)
    facade_result = {
        "image": {"path": str(image), "width": 40, "height": 30},
        "lines": [],
        "quality": {},
        "artifacts": {},
        "provenance": {"remote_vision": False},
    }
    with patch(
        "scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild.extract_text_info",
        return_value=facade_result,
    ) as facade:
        result = _extract_legacy_page_text(
            image,
            ocr_backend="paddleocr-local",
            ocr_scale=1.25,
        )

    assert result is facade_result
    facade.assert_called_once_with(
        image,
        runtime_dir=Path("/Volumes/DOC/CyberPPT/tools/paddleocr_runtime"),
        scale=1.25,
        correction=True,
    )


def test_legacy_caller_keeps_non_local_backend_out_of_facade(tmp_path: Path) -> None:
    image = tmp_path / "page-004_full.png"
    Image.new("RGB", (40, 30), "white").save(image)
    with patch(
        "scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild.extract_text_info",
    ) as facade:
        assert _extract_legacy_page_text(image, ocr_backend="none", ocr_scale=1.0) is None
    facade.assert_not_called()
