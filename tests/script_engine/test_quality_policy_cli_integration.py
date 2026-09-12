from __future__ import annotations

import json
from pathlib import Path

from script_engine import cli
from script_engine.author_preflight import author_preflight_report
from script_engine.contracts import load_json
from script_engine.final_source_provenance import source_provenance_for_page
from script_engine.onscreen_contracts import onscreen_alignment_advisories
from script_engine.page_source_command import page_source_report
from script_engine.render import render_stage02_markdown


ROOT = Path(__file__).resolve().parents[2]
ADVISORY = "AUTHOR_MISSION_GENERIC: slides.0.mission: wording heuristic"
BLOCKER = "SOME_NEW_GATE: future deterministic issue"


def example_advisories():
    return onscreen_alignment_advisories(load_json(ROOT / "examples" / "final-script.example.json"))


def _write_render_gate(tmp_path: Path) -> tuple[Path, Path, dict]:
    script_dir = tmp_path / "stage1-gate" / "script"
    cache_dir = script_dir / ".cache"
    packet_dir = cache_dir / "page-source"
    packet_dir.mkdir(parents=True)
    plan_path = script_dir / "deck-plan.json"
    foundation_path = script_dir / "foundation.json"
    source_index_path = cache_dir / "source-index.json"
    packet_path = packet_dir / "P01.json"
    preflight_path = cache_dir / "author-preflight.json"
    plan = {
        "authoring_mode": "faithful",
        "pages": [{"id": "P01", "page_role": "content", "source_refs": ["F1"]}],
    }
    foundation = {
        "facts": [
            {
                "id": "F1",
                "statement": "用于质量策略渲染测试的来源事实。",
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
                "text": "用于质量策略渲染测试的来源事实。",
            }
        ],
    }
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    foundation_path.write_text(json.dumps(foundation, ensure_ascii=False), encoding="utf-8")
    source_index_path.write_text(json.dumps(source_index, ensure_ascii=False), encoding="utf-8")
    packet, packet_exit = page_source_report(
        plan_path,
        foundation_path,
        "P01",
        source_index_path=source_index_path,
        output_path=packet_path,
    )
    assert packet_exit == 0 and packet["status"] == "passed"
    manifest, preflight_exit = author_preflight_report(
        plan_path,
        foundation_path,
        source_index_path=source_index_path,
        packet_dir=packet_dir,
        output_path=preflight_path,
    )
    assert preflight_exit == 0 and manifest["summary"]["overall_status"] == "passed"
    return plan_path, foundation_path, manifest


def test_lint_advisory_only_passes_with_advisory_status(monkeypatch, capsys) -> None:
    final_path = ROOT / "examples" / "final-script.example.json"
    monkeypatch.setattr(cli, "_final_lint_issues", lambda payload, markdown: [ADVISORY])

    exit_code = cli.main(["lint", str(final_path)])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["status"] == "passed_with_advisories"
    assert report["issues"] == []
    assert report["advisories"] == [ADVISORY, *example_advisories()]


def test_lint_unknown_finding_remains_blocking(monkeypatch, capsys) -> None:
    final_path = ROOT / "examples" / "final-script.example.json"
    monkeypatch.setattr(cli, "_final_lint_issues", lambda payload, markdown: [BLOCKER])

    exit_code = cli.main(["lint", str(final_path)])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert report["status"] == "failed"
    assert report["issues"] == [BLOCKER]
    assert report["advisories"] == example_advisories()


def test_render_stage02_does_not_block_on_advisory(monkeypatch, tmp_path, capsys) -> None:
    output_path = tmp_path / "final-script.md"
    plan_path, foundation_path, manifest = _write_render_gate(tmp_path)
    payload = load_json(ROOT / "examples" / "final-script.example.json")
    payload["slides"][0]["source_refs"] = list(manifest["pages"][0]["source_refs"])
    payload["slides"][0]["source_provenance"] = source_provenance_for_page(manifest, "P01")
    final_path = tmp_path / "gated-final-script.json"
    final_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(cli, "_final_lint_issues", lambda payload, markdown: [ADVISORY])

    exit_code = cli.main(
        [
            "render-stage02",
            str(final_path),
            "--plan",
            str(plan_path),
            "--foundation",
            str(foundation_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == str(output_path.resolve())
    assert output_path.is_file()


def test_check_sync_reports_advisory_without_failing(monkeypatch, tmp_path, capsys) -> None:
    final_path = ROOT / "examples" / "final-script.example.json"
    markdown_path = tmp_path / "final-script.md"
    markdown_path.write_text(
        render_stage02_markdown(load_json(final_path)),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_final_lint_issues", lambda payload, markdown: [ADVISORY])

    exit_code = cli.main(["check-sync", str(final_path), str(markdown_path)])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["status"] == "passed_with_advisories"
    assert report["issues"] == []
    assert report["advisories"] == [ADVISORY, *example_advisories()]


def test_status_reports_advisories_without_bypassing_stage1_gate(monkeypatch, tmp_path, capsys) -> None:
    project = tmp_path / "project"
    (project / "sources").mkdir(parents=True)
    (project / "sources" / "brief.md").write_text("source", encoding="utf-8")
    (project / "dist").mkdir()
    (project / "foundation.json").write_text(
        (ROOT / "examples" / "foundation.example.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (project / "deck-plan.json").write_text(
        (ROOT / "examples" / "deck-plan.example.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (project / "dist" / "final-script.json").write_text(
        (ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_final_lint_issues", lambda payload, markdown: [ADVISORY])

    exit_code = cli.main(["status", str(project)])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["final_script"]["lint"] == "passed_with_advisories"
    assert report["final_script"]["lint_advisories"] == [ADVISORY, *example_advisories()]
    assert report["stage"] == "Stage1 Author Preflight 未通过：待补齐或刷新逐页精确来源证据"
    assert report["stage1"]["author_preflight"]["status"] == "not_run"
