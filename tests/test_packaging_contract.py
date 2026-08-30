from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_packages_formal_scripts_runtime() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'include = ["cyberppt*", "script_engine*", "scripts*"]' in text
    assert '"Pillow>=10,<13"' in text
    assert 'source = [' in text
    assert '"openpyxl>=3.1,<4"' in text
    assert '"markitdown>=0.1,<1"' in text
    assert '"scripts.imagegen_pipeline" = ["style_presets/*.json"]' in text


def test_ci_contains_wheel_smoke_outside_repository() -> None:
    text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")

    assert "python -m build --wheel" in text
    assert "cd /tmp" in text
    assert "scripts.imagegen_pipeline.page_manifest" in text
    assert "scripts.image_to_pptx_runtime.stage02_adapter" in text
