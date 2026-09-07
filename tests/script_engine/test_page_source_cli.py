from __future__ import annotations

import json
from pathlib import Path

from script_engine.cli import main


def _write_project(tmp_path: Path) -> tuple[Path, Path, Path]:
    script_dir = tmp_path / "script"
    cache_dir = script_dir / ".cache"
    cache_dir.mkdir(parents=True)

    plan = {
        "authoring_mode": "faithful",
        "pages": [
            {
                "id": "P01",
                "title": "来源页",
                "source_refs": ["F1"],
            }
        ],
    }
    foundation = {
        "facts": [
            {
                "id": "F1",
                "statement": "完整来源事实。",
                "source_refs": ["SU-001"],
            }
        ]
    }
    source_index = {
        "schema": "cyberppt.source_index.v2",
        "units": [
            {
                "unit_id": "SU-001",
                "source_id": "SRC-1",
                "kind": "paragraph",
                "heading_id": "H-01",
                "text": "这是 AUTHOR 必须读取的完整来源事实。",
            }
        ],
    }

    plan_path = script_dir / "deck-plan.json"
    foundation_path = script_dir / "foundation.json"
    index_path = cache_dir / "source-index.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    foundation_path.write_text(json.dumps(foundation, ensure_ascii=False), encoding="utf-8")
    index_path.write_text(json.dumps(source_index, ensure_ascii=False), encoding="utf-8")
    return plan_path, foundation_path, index_path


def test_page_source_cli_uses_sibling_source_index_and_writes_derived_packet(
    tmp_path, capsys
) -> None:
    plan_path, foundation_path, index_path = _write_project(tmp_path)
    output = tmp_path / "script/.cache/page-source/P01.json"

    exit_code = main(
        [
            "page-source",
            str(plan_path),
            str(foundation_path),
            "P01",
            "--output",
            str(output),
        ]
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["status"] == "passed"
    assert report["authority"] == "derived_runtime_context"
    assert report["source_index"] == str(index_path.resolve())
    assert report["authoring_mode"] == "faithful"
    assert report["evidence"][0]["exact_source_units"][0]["text"] == "这是 AUTHOR 必须读取的完整来源事实。"
    assert report["output"] == str(output.resolve())

    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["authority"] == "derived_runtime_context"
    assert "output" not in saved
    assert saved["evidence"][0]["exact_source_units"][0]["unit_id"] == "SU-001"


def test_page_source_cli_fails_when_page_is_unknown(tmp_path, capsys) -> None:
    plan_path, foundation_path, _ = _write_project(tmp_path)

    exit_code = main(["page-source", str(plan_path), str(foundation_path), "P99"])
    captured = capsys.readouterr()
    report = json.loads(captured.err)

    assert exit_code == 1
    assert report["status"] == "rewrite_required"
    assert report["issues"] == ["PAGE_SOURCE_PAGE_UNKNOWN: page 'P99' is not in deck-plan.json"]


def test_page_source_cli_fails_when_source_index_is_missing(tmp_path, capsys) -> None:
    plan_path, foundation_path, index_path = _write_project(tmp_path)
    index_path.unlink()

    exit_code = main(["page-source", str(plan_path), str(foundation_path), "P01"])
    captured = capsys.readouterr()
    report = json.loads(captured.err)

    assert exit_code == 1
    assert report["status"] == "rewrite_required"
    assert report["issues"][0].startswith("PAGE_SOURCE_INDEX_MISSING:")
