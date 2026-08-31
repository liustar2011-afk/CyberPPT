from __future__ import annotations

import json
from pathlib import Path

from script_engine import cli
from script_engine.contracts import load_json
from script_engine.render import render_stage02_markdown


ROOT = Path(__file__).resolve().parents[2]
ADVISORY = "AUTHOR_MISSION_GENERIC: slides.0.mission: wording heuristic"
BLOCKER = "SOME_NEW_GATE: future deterministic issue"


def test_lint_advisory_only_passes_with_advisory_status(monkeypatch, capsys) -> None:
    final_path = ROOT / "examples" / "final-script.example.json"
    monkeypatch.setattr(cli, "_final_lint_issues", lambda payload, markdown: [ADVISORY])

    exit_code = cli.main(["lint", str(final_path)])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["status"] == "passed_with_advisories"
    assert report["issues"] == []
    assert report["advisories"] == [ADVISORY]


def test_lint_unknown_finding_remains_blocking(monkeypatch, capsys) -> None:
    final_path = ROOT / "examples" / "final-script.example.json"
    monkeypatch.setattr(cli, "_final_lint_issues", lambda payload, markdown: [BLOCKER])

    exit_code = cli.main(["lint", str(final_path)])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert report["status"] == "failed"
    assert report["issues"] == [BLOCKER]
    assert report["advisories"] == []


def test_render_stage02_does_not_block_on_advisory(monkeypatch, tmp_path, capsys) -> None:
    final_path = ROOT / "examples" / "final-script.example.json"
    output_path = tmp_path / "final-script.md"
    monkeypatch.setattr(cli, "_final_lint_issues", lambda payload, markdown: [ADVISORY])

    exit_code = cli.main(["render-stage02", str(final_path), "--output", str(output_path)])

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
    assert report["advisories"] == [ADVISORY]


def test_status_keeps_advisory_only_final_script_ready(monkeypatch, tmp_path, capsys) -> None:
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
    assert report["final_script"]["lint_advisories"] == [ADVISORY]
    assert report["stage"] == "最终脚本文件已就绪，确定性检查通过；作者化完成情况由当前主 Agent 按 cyberppt-script-workflow 确认"
