import json
from pathlib import Path
import sys

import pytest
from PIL import Image


PROJECT_ROOT = Path(__file__).parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def image_factory():
    def create(path: Path, size: tuple[int, int], mode: str = "RGB") -> Path:
        color = (255, 255, 255, 0) if mode == "RGBA" else (255, 255, 255)
        Image.new(mode, size, color).save(path)
        return path

    return create


@pytest.fixture
def sample_page():
    from scripts.models import BBox, PageSpec, TextLine

    line = TextLine(
        line_id="T02-L01",
        group_id="T02",
        line_index=1,
        text="103682 亿千瓦时，",
        bbox=BBox(181, 111, 373, 59),
        polygon=((181, 111), (554, 111), (554, 170), (181, 170)),
        confidence=0.99,
    )
    return PageSpec.sample(
        page_id="page_004", width_px=1672, height_px=941, lines=[line]
    )


@pytest.fixture
def sample_page_json(tmp_path, sample_page):
    path = tmp_path / "page.json"
    path.write_text(
        json.dumps(sample_page.to_dict(), ensure_ascii=False), encoding="utf-8"
    )
    return path
