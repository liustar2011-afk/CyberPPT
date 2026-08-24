from __future__ import annotations

import json
import re
from pathlib import Path

from script_engine.contracts import validate_final_script
from script_engine.render import render_stage02_markdown


ROOT = Path(__file__).resolve().parents[1]


def _example() -> dict:
    return json.loads((ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"))


def test_example_validates() -> None:
    assert validate_final_script(_example()) == []


def test_stage02_markdown_uses_compatible_page_heading() -> None:
    markdown = render_stage02_markdown(_example())
    assert re.search(r"^## P01 .+$", markdown, flags=re.MULTILINE)
    assert "- 页面类型：内容页" in markdown
    assert "- 核心结论：" in markdown
    assert "### 完整文字稿" in markdown
    assert "### 上屏文字" in markdown
    assert "### 视觉结构" in markdown
    assert "### 演讲者备注" in markdown


def test_stage02_boundary_does_not_leak_internal_artifacts() -> None:
    markdown = render_stage02_markdown(_example())
    forbidden = (
        "foundation.json",
        "deck-plan.json",
        "source-truth.json",
        "semantic-argument-model.json",
        "outline-audit",
    )
    assert all(token not in markdown for token in forbidden)
