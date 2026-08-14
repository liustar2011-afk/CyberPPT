from pathlib import Path

from PIL import Image

from scripts.image_to_editable_svg.reconstruct import inspect_page, prepare_scene_layers
from scripts.image_to_editable_svg.roster import normalize_full_page


def _frame(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 50), "white").save(source)
    return normalize_full_page(page_number=4, source=source, output_dir=tmp_path / "frames")


def test_text_is_bound_to_script_truth_not_ocr_guess(tmp_path):
    result = inspect_page(_frame(tmp_path), script_text=["核心结论"], ocr_layout={"items": [{"text": "核心结论（OCR猜测）", "bbox": [1, 2, 30, 10]}]})
    text = result["layers"][-1]
    assert text["truth_text"] == "核心结论"
    assert text["truth_source"] == "script"


def test_unverified_data_and_identity_regions_require_manual_work(tmp_path):
    result = inspect_page(_frame(tmp_path), regions=[{"id": "chart", "type": "chart", "bbox": [1, 1, 10, 10]}, {"id": "logo", "type": "logo", "bbox": [20, 1, 10, 10]}])
    assert {item["id"] for item in result["manual_required"]} == {"chart", "logo"}


def test_registered_scene_layers_keep_the_source_canvas(tmp_path):
    frame = _frame(tmp_path)
    layers = prepare_scene_layers(frame, [{"id": "scene", "family": "scene", "bbox": [1, 1, 10, 10], "asset_path": "/asset.png"}])
    assert all(layer["registration_group"] == "page-004" for layer in layers)
    assert all(layer["canvas"] == [100, 50] for layer in layers)
