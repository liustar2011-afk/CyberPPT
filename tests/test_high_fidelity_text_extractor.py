from pathlib import Path
import sys
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REBUILD_ENGINE_DIR = ROOT / "scripts" / "dual_image_overlay" / "rebuild_engine"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(REBUILD_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(REBUILD_ENGINE_DIR))

from scripts.dual_image_overlay.rebuild_engine.high_fidelity_text_extractor import extract_text_info


def test_extract_text_info_accepts_one_image_and_returns_complete_lines(tmp_path: Path) -> None:
    image = tmp_path / "slide.png"
    Image.new("RGB", (100, 60), "white").save(image)
    layout = {
        "backend": "paddleocr-local",
        "image_size": {"width": 100, "height": 60},
        "items": [{"text": "标题", "bbox": [10, 10, 30, 20], "confidence": 0.99}],
    }
    with patch("scripts.dual_image_overlay.rebuild_engine.high_fidelity_text_extractor.run_local_ocr", return_value=layout):
        result = extract_text_info(image, runtime_dir=tmp_path / "runtime", correction=False)
    assert set(result) == {"image", "lines", "quality", "artifacts", "provenance"}
    assert result["lines"][0]["observed_text"] == "标题"
    assert result["lines"][0]["glyph_crop"]
    assert result["provenance"]["remote_vision"] is False


def test_local_facade_never_invokes_remote_vision(tmp_path: Path) -> None:
    image = tmp_path / "slide.png"
    Image.new("RGB", (20, 20), "white").save(image)
    layout = {"backend": "paddleocr-local", "image_size": {"width": 20, "height": 20}, "items": []}
    with patch("scripts.dual_image_overlay.rebuild_engine.high_fidelity_text_extractor.run_local_ocr", return_value=layout), patch(
        "scripts.dual_image_overlay.rebuild_engine.ocr_text_locator.run_codex_vision_text",
        side_effect=AssertionError("remote Vision called"),
    ):
        extract_text_info(image, correction=False)


def test_page_specific_arguments_are_rejected(tmp_path: Path) -> None:
    image = tmp_path / "slide.png"
    Image.new("RGB", (20, 20), "white").save(image)
    try:
        extract_text_info(image, page_number=1)  # type: ignore[call-arg]
    except TypeError as exc:
        assert "page_number" in str(exc)
    else:
        raise AssertionError("page-specific argument unexpectedly accepted")
