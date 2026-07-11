from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from scripts.dual_image_overlay.rebuild_engine import paddleocr_local


def _write_image(path: Path, size: tuple[int, int] = (320, 180)) -> Path:
    Image.new("RGB", size, "#ffffff").save(path)
    return path


def test_run_local_ocr_maps_runtime_result_to_canonical_json(monkeypatch, tmp_path: Path) -> None:
    image = _write_image(tmp_path / "page.png", size=(640, 360))
    output = tmp_path / "ocr.json"

    def fake_invoke_runtime(*, image_path: Path, runtime_dir: Path, model_dir: Path | None, timeout: int) -> dict:
        assert image_path == image
        assert runtime_dir == tmp_path
        assert model_dir is None
        assert timeout > 0
        return {
            "rec_texts": ["经营管理能力"],
            "rec_scores": [0.98],
            "rec_boxes": [[112, 237, 418, 276]],
            "dt_polys": [[[112, 237], [418, 237], [418, 276], [112, 276]]],
            "styles": [{"font_size": 22, "bold": True, "color": "12355B"}],
        }

    monkeypatch.setattr(paddleocr_local, "_invoke_runtime", fake_invoke_runtime)

    result_path = paddleocr_local.run_local_ocr(image, output_path=output, runtime_dir=tmp_path)

    assert result_path == output
    payload = json.loads(output.read_text(encoding="utf-8"))
    line = payload["canonical"]["lines"][0]
    assert line["text"] == "经营管理能力"
    assert line["bbox"] == [112, 237, 306, 39]
    assert line["polygon"] == [[112, 237], [418, 237], [418, 276], [112, 276]]
    assert line["score"] == 0.98
    assert line["runs"] == [{"text": "经营管理能力", "font_size": 22, "bold": True, "color": "12355B"}]
    assert payload["canonical"]["metadata"]["backend"] == "paddleocr-local"
