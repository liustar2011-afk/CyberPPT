from __future__ import annotations

import base64
import importlib.util
import io
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

    assert module.DEFAULT_SIZE == "2048x1024"


def test_ensure_output_size_normalizes_png(tmp_path: Path) -> None:
    module = load_codex_oauth_image()
    output = tmp_path / "generated.png"
    Image.new("RGB", (320, 180), "navy").save(output)

    result = module.ensure_output_size(output, "2048x1024")

    assert result == (4096, 2048)
    with Image.open(output) as normalized:
        assert normalized.size == (4096, 2048)


def test_ensure_output_size_leaves_auto_unchanged(tmp_path: Path) -> None:
    module = load_codex_oauth_image()
    output = tmp_path / "generated.png"
    Image.new("RGB", (320, 180), "navy").save(output)

    result = module.ensure_output_size(output, "auto")

    assert result == (-1, -1)
    with Image.open(output) as unchanged:
        assert unchanged.size == (320, 180)


def test_write_image_preserves_raw_backend_dimensions(tmp_path: Path) -> None:
    module = load_codex_oauth_image()
    output = tmp_path / "generated.png"
    buffer = io.BytesIO()
    Image.new("RGB", (320, 180), "navy").save(buffer, format="PNG")

    module._write_image(
        base64.b64encode(buffer.getvalue()).decode("ascii"),
        output,
        force=False,
        size="2048x1024",
    )

    raw = tmp_path / "generated_raw.png"
    assert raw.is_file()
    with Image.open(raw) as raw_image:
        assert raw_image.size == (320, 180)
    with Image.open(output) as normalized:
        assert normalized.size == (4096, 2048)


def test_write_image_preserves_raw_even_when_size_matches(tmp_path: Path) -> None:
    module = load_codex_oauth_image()
    output = tmp_path / "generated.png"
    buffer = io.BytesIO()
    Image.new("RGB", (2048, 1024), "navy").save(buffer, format="PNG")

    module._write_image(
        base64.b64encode(buffer.getvalue()).decode("ascii"),
        output,
        force=False,
        size="2048x1024",
    )

    raw = tmp_path / "generated_raw.png"
    with Image.open(raw) as raw_image:
        assert raw_image.size == (2048, 1024)
    with Image.open(output) as enhanced:
        assert enhanced.size == (4096, 2048)
