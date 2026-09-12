from __future__ import annotations

import json
from pathlib import Path

from script_engine.author_preflight import author_preflight_report
from script_engine.delivery_commands import render_stage02_delivery
from script_engine.final_source_provenance import source_provenance_for_page
from script_engine.page_source_command import page_source_report


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_stage02_blocks_added_number_after_lineage_passes(tmp_path: Path) -> None:
    script_dir = tmp_path / "script"
    cache_dir = script_dir / ".cache"
    packet_dir = cache_dir / "page-source"
    plan_path = script_dir / "deck-plan.json"
    foundation_path = script_dir / "foundation.json"
    source_index_path = cache_dir / "source-index.json"
    packet_path = packet_dir / "P01.json"
    manifest_path = cache_dir / "author-preflight.json"
    final_path = script_dir / "dist" / "final-script.json"
    output_path = script_dir / "dist" / "final-script.md"

    plan = {
        "authoring_mode": "faithful",
        "pages": [
            {
                "id": "P01",
                "title": "覆盖情况",
                "page_role": "content",
                "source_refs": ["F1"],
            }
        ],
    }
    foundation = {
        "facts": [
            {
                "id": "F1",
                "statement": "平台覆盖600家主体。",
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
                "text": "平台覆盖600家主体。",
            }
        ],
    }
    _write_json(plan_path, plan)
    _write_json(foundation_path, foundation)
    _write_json(source_index_path, source_index)

    packet, packet_exit = page_source_report(
        plan_path,
        foundation_path,
        "P01",
        source_index_path=source_index_path,
        output_path=packet_path,
    )
    assert packet_exit == 0
    manifest, preflight_exit = author_preflight_report(
        plan_path,
        foundation_path,
        source_index_path=source_index_path,
        packet_dir=packet_dir,
        output_path=manifest_path,
    )
    assert preflight_exit == 0

    final_script = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {
            "title": "覆盖情况",
            "communication_goal": "说明平台覆盖情况。",
            "authoring_mode": "faithful",
        },
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "覆盖情况",
                "full_copy": "平台覆盖700家主体。",
                "onscreen": [{"heading": "平台覆盖700家主体"}],
                "source_refs": ["F1"],
                "source_provenance": source_provenance_for_page(manifest, "P01"),
            }
        ],
    }
    _write_json(final_path, final_script)

    rendered, report, exit_code = render_stage02_delivery(
        final_path,
        output_path,
        plan_path=plan_path,
        foundation_path=foundation_path,
        final_lint_findings=lambda _payload, _markdown: ([], []),
    )

    assert exit_code == 1
    assert rendered is None
    assert report is not None
    assert report["kind"] == "native-source-fidelity"
    assert any("NATIVE_NUMBER_OR_DATE_ADDED" in issue and "700家" in issue for issue in report["issues"])
    assert not output_path.exists()
