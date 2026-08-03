from __future__ import annotations

import zipfile
from pathlib import Path

from ppt_compiler.exporters import export_project


def test_export_outputs(complete_project: Path) -> None:
    outputs = export_project(complete_project)
    assert outputs["markdown"].exists()
    assert outputs["json"].exists()
    assert outputs["yaml"].exists()
    assert outputs["zip"].exists()
    text = outputs["markdown"].read_text(encoding="utf-8")
    assert "## 第2页｜持续用数需要可信服务通道" in text
    assert "### 来源追溯" in text
    with zipfile.ZipFile(outputs["zip"]) as zf:
        names = set(zf.namelist())
        assert "exports/ppt_script.md" in names
        assert "stages/05_semantic_audit.json" in names
