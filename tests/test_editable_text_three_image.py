from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from cyberppt.commands.editable_text_three_image import (
    build_three_image_batch,
    get_production_mode,
)
from cyberppt.commands.init_project import init_project


def _write_image(path: Path, size: tuple[int, int] = (320, 180)) -> Path:
    Image.new("RGB", size, "#ffffff").save(path)
    return path


def test_default_production_mode_is_full_image_ppt(tmp_path: Path) -> None:
    project = tmp_path / "project"
    init_project(project)

    assert get_production_mode(project) == "full_image_ppt"


def test_three_image_batch_requires_full_background_and_text(tmp_path: Path) -> None:
    pairs = tmp_path / "page_image_pairs.json"
    full = _write_image(tmp_path / "full.png")
    pairs.write_text(
        json.dumps(
            {
                "pairs": [
                    {
                        "page_number": 4,
                        "full": {"path": str(full)},
                        "background": {"path": str(tmp_path / "background.png")},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="TEXT"):
        build_three_image_batch(tmp_path, "4", pairs)
