from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "scripts"
    / "dual_image_overlay"
    / "rebuild_engine"
    / "codex_oauth_image.py"
)


def load_codex_oauth_image():
    spec = importlib.util.spec_from_file_location(
        "codex_oauth_image_for_size_test", SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_default_size_matches_slide_content_ratio() -> None:
    module = load_codex_oauth_image()

    assert module.DEFAULT_SIZE == "1680x944"


def test_ensure_output_size_normalizes_png(tmp_path: Path) -> None:
    module = load_codex_oauth_image()
    output = tmp_path / "generated.png"
    Image.new("RGB", (320, 180), "navy").save(output)

    result = module.ensure_output_size(output, "1680x944")

    assert result == (1680, 944)
    with Image.open(output) as normalized:
        assert normalized.size == (1680, 944)


def test_ensure_output_size_leaves_auto_unchanged(tmp_path: Path) -> None:
    module = load_codex_oauth_image()
    output = tmp_path / "generated.png"
    Image.new("RGB", (320, 180), "navy").save(output)

    result = module.ensure_output_size(output, "auto")

    assert result == (-1, -1)
    with Image.open(output) as unchanged:
        assert unchanged.size == (320, 180)
