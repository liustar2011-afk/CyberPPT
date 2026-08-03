from __future__ import annotations

from pathlib import Path

from ppt_compiler.extractors import initialise_project
from ppt_compiler.utils import read_json


def test_multi_source_ids_are_global(tmp_path: Path, skill_root: Path) -> None:
    source = skill_root / "references/examples/source_sample.md"
    second = tmp_path / "second.txt"
    second.write_text("一、第二份材料\n\n补充事实。", encoding="utf-8")
    project = tmp_path / "project"
    metadata = initialise_project([source, second], project, skill_root / "assets/profiles/generic_executive.yaml")
    assert metadata["document_count"] == 2
    payload = read_json(project / "source/source_blocks.json", {})
    ids = [block["source_id"] for block in payload["blocks"]]
    assert any(x.startswith("D01-S") for x in ids)
    assert any(x.startswith("D02-S") for x in ids)
    assert len(ids) == len(set(ids))
    assert (project / "source/source_readable.md").exists()
    assert metadata["chunk_count"] >= 1
