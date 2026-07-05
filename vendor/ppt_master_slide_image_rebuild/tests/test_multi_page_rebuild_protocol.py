from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import verify_slide_image_rebuild_manifest as verifier


def _write_minimal_export_project(project: Path) -> None:
    (project / "images" / "reference_pages").mkdir(parents=True)
    (project / "pages" / "P01" / "svg_output").mkdir(parents=True)
    (project / "pages" / "P02" / "svg_output").mkdir(parents=True)
    (project / "notes").mkdir()
    (project / "exports" / "qa").mkdir(parents=True)
    (project / "exports").mkdir(exist_ok=True)

    # Existence is enough for manifest export-stage checks.
    (project / "images" / "reference_pages" / "P01.png").write_bytes(b"png")
    (project / "images" / "reference_pages" / "P02.png").write_bytes(b"png")
    (project / "pages" / "P01" / "svg_output" / "P01.svg").write_text("<svg/>", encoding="utf-8")
    (project / "pages" / "P02" / "svg_output" / "P02.svg").write_text("<svg/>", encoding="utf-8")
    (project / "image_crops_manifest.json").write_text("{}", encoding="utf-8")
    (project / "exports" / "qa" / "repair_tasks.json").write_text(
        json.dumps({"blocking_open_count": 0}),
        encoding="utf-8",
    )
    (project / "exports" / "deck.pptx").write_bytes(b"pptx")
    for page_id in ["P01", "P02"]:
        page_dir = project / "pages" / page_id
        (page_dir / "layout_reference.json").write_text(
            json.dumps({
                "version": "2.0",
                "workflow": "layout-reference-rebuild-2",
                "structure_contract": {},
            }),
            encoding="utf-8",
        )
        (page_dir / "content_mapping.json").write_text("{}", encoding="utf-8")
        (page_dir / "text_region_map.json").write_text("{}", encoding="utf-8")

    (project / "slide_image_rebuild_manifest.json").write_text(
        json.dumps({
            "workflow": "slide-image-rebuild",
            "rebuild_mode": "vector-hifi",
            "pptx_export_mode": "hifi",
            "pages": [
                {
                    "page_id": "P01",
                    "reference_image": "images/reference_pages/P01.png",
                    "page_dir": "pages/P01",
                },
                {
                    "page_id": "P02",
                    "reference_image": "images/reference_pages/P02.png",
                    "page_dir": "pages/P02",
                },
            ],
        }),
        encoding="utf-8",
    )


def _stub_delegated_validators(monkeypatch: Any) -> None:
    monkeypatch.setattr(verifier, "_run_json", lambda _cmd: (0, {"valid": True}))


def test_multi_page_export_requires_notes_heading_per_page(tmp_path: Path, monkeypatch: Any) -> None:
    _stub_delegated_validators(monkeypatch)
    _write_minimal_export_project(tmp_path)
    (tmp_path / "notes" / "total.md").write_text("# P01\n\n第一页。\n", encoding="utf-8")

    payload = verifier.verify_project(tmp_path, stage="export")

    assert not payload["valid"]
    assert any(error["code"] == "missing_page_notes_heading" for error in payload["errors"])


def test_multi_page_export_accepts_notes_headings(tmp_path: Path, monkeypatch: Any) -> None:
    _stub_delegated_validators(monkeypatch)
    _write_minimal_export_project(tmp_path)
    (tmp_path / "notes" / "total.md").write_text(
        "# P01\n\n第一页。\n\n# P02\n\n第二页。\n",
        encoding="utf-8",
    )

    payload = verifier.verify_project(tmp_path, stage="export")

    assert payload["valid"]
