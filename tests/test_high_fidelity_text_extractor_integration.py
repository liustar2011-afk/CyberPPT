from pathlib import Path
import inspect
from unittest.mock import patch

from PIL import Image

from scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild import _extract_legacy_page_text, _full_layout_for_page, _layout_from_facade

ROOT = Path(__file__).resolve().parents[1]


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
        runtime_dir=ROOT / "tools" / "paddleocr_runtime",
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


def test_full_local_layout_and_forensics_share_one_facade_ocr_call(tmp_path: Path) -> None:
    image = tmp_path / "page-004_full.png"
    Image.new("RGB", (40, 30), "white").save(image)
    info = {
        "image": {"path": str(image), "width": 40, "height": 30},
        "lines": [{"confidence": 0.9, "items": [{"text": "标题", "bbox": [1, 2, 20, 10]}]}],
        "quality": {}, "artifacts": {}, "provenance": {},
    }
    with patch(
        "scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild.extract_text_info",
        return_value=info,
    ) as facade:
        _, layout, forensics = _full_layout_for_page(
            full_image=image,
            ocr_dir=tmp_path / "ocr",
            page_number=4,
            ocr_backend="paddleocr-local",
            force_ocr=False,
            timeout=10,
            ocr_scale=1.0,
        )
    assert facade.call_count == 1
    assert layout["items"][0]["text"] == "标题"
    assert forensics is info


def test_main_full_future_uses_three_tuple_facade_helper() -> None:
    source = inspect.getsource(
        __import__(
            "scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild",
            fromlist=["rebuild_from_manifest"],
        ).rebuild_from_manifest
    )
    assert "full_future = ocr_pool.submit(\n                _full_layout_for_page," in source


def test_local_prefetch_is_disabled_to_prevent_duplicate_facade_ocr() -> None:
    module = __import__(
        "scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild",
        fromlist=["_prefetch_page_ocr_layouts"],
    )
    source = inspect.getsource(module._prefetch_page_ocr_layouts)
    assert 'if ocr_backend == "paddleocr-local":' in source
    assert "return" in source


def test_facade_final_text_reaches_overlay_layout_deterministically() -> None:
    info = {
        "image": {"width": 40, "height": 30},
        "lines": [{
            "observed_text": "甲乙",
            "final_text": "甲丙",
            "items": [
                {"text": "甲", "bbox": [1, 1, 5, 8]},
                {"text": "乙", "bbox": [6, 1, 10, 8]},
            ],
        }],
    }
    layout = _layout_from_facade(info)
    assert [item["text"] for item in layout["items"]] == ["甲", "丙"]
