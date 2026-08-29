from __future__ import annotations
import json
from pathlib import Path
from script_engine.cli import main

ROOT = Path(__file__).resolve().parents[2]


def test_cli_validate_final_passes_on_example(capsys) -> None:
    path = ROOT / "examples" / "final-script.example.json"
    exit_code = main(["validate", "final", str(path)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert out["status"] == "passed"
    assert out["issues"] == []


def test_cli_validate_plan_passes_on_example(capsys) -> None:
    path = ROOT / "examples" / "deck-plan.example.json"
    exit_code = main(["validate", "plan", str(path)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert out["status"] == "passed"


def test_cli_validate_final_fails_on_broken_payload(tmp_path, capsys) -> None:
    payload = json.loads((ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"))
    del payload["slides"][0]["core_message"]
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")
    exit_code = main(["validate", "final", str(broken)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert out["status"] == "failed"
    assert out["issues"]


def test_cli_trace_composed_reports_priorities_and_blocks_source_absent_number(
    tmp_path, capsys
) -> None:
    foundation = {
        "facts": [{"id": "F1", "statement": "平台覆盖600家主体", "source_refs": ["S1"]}],
        "concepts": [],
        "relations": [],
        "arguments": [],
    }
    final = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "平台覆盖700家主体",
                "mission": "说明覆盖目标",
                "core_message": "平台覆盖700家主体",
                "onscreen": [{"heading": "平台覆盖700家主体"}],
                "source_refs": ["S1"],
            }
        ]
    }
    final_path = tmp_path / "final.json"
    foundation_path = tmp_path / "foundation.json"
    final_path.write_text(json.dumps(final, ensure_ascii=False), encoding="utf-8")
    foundation_path.write_text(json.dumps(foundation, ensure_ascii=False), encoding="utf-8")

    exit_code = main(["trace-composed", str(final_path), str(foundation_path)])
    out = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert out["status"] == "failed"
    assert out["hard_findings"][0]["absent_numbers"] == ["700"]
    assert out["critic_priorities"][0]["page_id"] == "P01"


def test_cli_render_stage02_writes_output_file(tmp_path, capsys) -> None:
    input_path = ROOT / "examples" / "final-script.example.json"
    output_path = tmp_path / "nested" / "final-script.md"
    exit_code = main(["render-stage02", str(input_path), "--output", str(output_path)])
    printed = capsys.readouterr().out.strip()
    assert exit_code == 0
    assert printed == str(output_path.resolve())
    assert output_path.is_file()
    assert "## P01" in output_path.read_text(encoding="utf-8")
    assert b"\r\n" not in output_path.read_bytes()


def test_cli_render_stage02_fails_on_invalid_input(tmp_path, capsys) -> None:
    payload = json.loads((ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"))
    payload["slides"][0]["page_type"] = "sidebar"
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")
    output_path = tmp_path / "out.md"
    exit_code = main(["render-stage02", str(broken), "--output", str(output_path)])
    captured = capsys.readouterr()
    err = json.loads(captured.err)
    assert exit_code == 1
    assert err["status"] == "failed"
    assert not output_path.exists()


def test_cli_check_refs_passes_when_all_citations_known(capsys) -> None:
    final_path = ROOT / "examples" / "final-script.example.json"
    foundation_path = ROOT / "examples" / "foundation.example.json"
    exit_code = main(["check-refs", str(final_path), str(foundation_path)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert out["status"] == "passed"
    assert out["issues"] == []


def test_cli_check_refs_fails_on_orphaned_citation(tmp_path, capsys) -> None:
    payload = json.loads((ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"))
    payload["slides"][0]["source_refs"] = ["ST999"]
    broken = tmp_path / "broken-final.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")
    foundation_path = ROOT / "examples" / "foundation.example.json"
    exit_code = main(["check-refs", str(broken), str(foundation_path)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert out["status"] == "failed"
    assert any("ST999" in issue for issue in out["issues"])


def test_cli_new_project_scaffolds_sources_and_dist(tmp_path, capsys) -> None:
    exit_code = main(["new-project", "demo-slug", "--base-dir", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert out["status"] == "created"
    project_dir = tmp_path / "demo-slug"
    assert (project_dir / "dist" / ".gitkeep").is_file()
    assert (project_dir / "sources" / ".gitkeep").is_file()


def test_cli_new_project_rejects_invalid_slug(tmp_path, capsys) -> None:
    exit_code = main(["new-project", "Not A Slug!", "--base-dir", str(tmp_path)])
    err = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert err["status"] == "failed"
    assert not (tmp_path / "Not A Slug!").exists()


def test_cli_new_project_refuses_to_overwrite_existing(tmp_path, capsys) -> None:
    main(["new-project", "demo-slug", "--base-dir", str(tmp_path)])
    capsys.readouterr()
    exit_code = main(["new-project", "demo-slug", "--base-dir", str(tmp_path)])
    err = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert err["status"] == "failed"
    assert "already exists" in err["issues"][0]


def test_cli_status_reports_waiting_for_sources_on_fresh_project(tmp_path, capsys) -> None:
    main(["new-project", "demo-slug", "--base-dir", str(tmp_path)])
    capsys.readouterr()
    exit_code = main(["status", str(tmp_path / "demo-slug")])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert "等待源材料" in out["stage"]
    assert out["sources"] == []
    assert out["foundation"]["exists"] is False


def test_cli_status_progresses_as_artifacts_are_added(tmp_path, capsys) -> None:
    main(["new-project", "demo-slug", "--base-dir", str(tmp_path)])
    capsys.readouterr()
    project_dir = tmp_path / "demo-slug"
    (project_dir / "sources" / "brief.docx").write_bytes(b"placeholder")
    exit_code = main(["status", str(project_dir)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert "待理解材料" in out["stage"]
    assert out["sources"] == ["brief.docx"]

    foundation_payload = json.loads((ROOT / "examples" / "foundation.example.json").read_text(encoding="utf-8"))
    (project_dir / "foundation.json").write_text(json.dumps(foundation_payload), encoding="utf-8")
    exit_code = main(["status", str(project_dir)])
    out = json.loads(capsys.readouterr().out)
    assert "待规划" in out["stage"]
    assert out["foundation"]["valid"] is True

    plan_payload = json.loads((ROOT / "examples" / "deck-plan.example.json").read_text(encoding="utf-8"))
    (project_dir / "deck-plan.json").write_text(json.dumps(plan_payload), encoding="utf-8")
    exit_code = main(["status", str(project_dir)])
    out = json.loads(capsys.readouterr().out)
    assert "脚本规划待确认" in out["stage"]

    final_payload = json.loads((ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"))
    (project_dir / "dist" / "final-script.json").write_text(json.dumps(final_payload), encoding="utf-8")
    exit_code = main(["status", str(project_dir)])
    out = json.loads(capsys.readouterr().out)
    assert out["stage"] == "最终脚本文件已就绪，确定性检查通过；作者化完成情况由当前主 Agent 按 cyberppt-script-workflow 确认"
    assert out["final_script"]["page_count"] == len(final_payload["slides"])


def test_cli_status_supports_repository_source_and_script_layout(tmp_path, capsys) -> None:
    project_dir = tmp_path / "repository-layout"
    (project_dir / "source").mkdir(parents=True)
    (project_dir / "script" / "dist").mkdir(parents=True)
    (project_dir / "source" / "brief.docx").write_bytes(b"placeholder")
    (project_dir / "script" / "foundation.json").write_text(
        (ROOT / "examples" / "foundation.example.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (project_dir / "script" / "deck-plan.json").write_text(
        (ROOT / "examples" / "deck-plan.example.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    exit_code = main(["status", str(project_dir)])
    out = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert "脚本规划待确认" in out["stage"]
    assert out["sources"] == ["brief.docx"]
    assert Path(out["foundation"]["path"]).parts[-2:] == ("script", "foundation.json")
    assert Path(out["deck_plan"]["path"]).parts[-2:] == ("script", "deck-plan.json")


def test_cli_status_does_not_apply_a_fixed_onscreen_density_floor(tmp_path, capsys) -> None:
    main(["new-project", "demo-slug", "--base-dir", str(tmp_path)])
    capsys.readouterr()
    project_dir = tmp_path / "demo-slug"
    (project_dir / "sources" / "brief.docx").write_bytes(b"placeholder")
    (project_dir / "foundation.json").write_text(
        (ROOT / "examples" / "foundation.example.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (project_dir / "deck-plan.json").write_text(
        (ROOT / "examples" / "deck-plan.example.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    final_payload = json.loads((ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"))
    final_payload["slides"][0]["page_type"] = "content"
    final_payload["slides"][0]["onscreen"] = [{"heading": "模块", "text": "简短说明"}]
    (project_dir / "dist" / "final-script.json").write_text(
        json.dumps(final_payload, ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = main(["status", str(project_dir)])
    out = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert out["stage"] == "最终脚本文件已就绪，确定性检查通过；作者化完成情况由当前主 Agent 按 cyberppt-script-workflow 确认"
    assert out["final_script"]["lint"] == "passed"
    assert out["final_script"].get("lint_warnings", []) == []


def test_cli_lint_passes_on_example(capsys) -> None:
    path = ROOT / "examples" / "final-script.example.json"
    exit_code = main(["lint", str(path)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert out["status"] == "passed"
    assert out["issues"] == []


def test_cli_lint_does_not_apply_a_fixed_onscreen_density_floor(tmp_path, capsys) -> None:
    payload = json.loads((ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"))
    payload["slides"][0]["page_type"] = "content"
    payload["slides"][0]["onscreen"] = [{"heading": "模块", "text": "简短说明"}]
    path = tmp_path / "underfilled.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    exit_code = main(["lint", str(path)])
    out = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert out["status"] == "passed"
    assert out["issues"] == []
    assert out["warnings"] == []


def test_cli_lint_reports_empty_warnings_list_on_clean_example(capsys) -> None:
    path = ROOT / "examples" / "final-script.example.json"
    exit_code = main(["lint", str(path)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert out["warnings"] == []

def test_cli_lint_fails_on_placeholder_speaker_notes(tmp_path, capsys) -> None:
    payload = json.loads((ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"))
    payload["slides"][0]["speaker_notes"] = "过渡。"
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")
    exit_code = main(["lint", str(broken)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert out["status"] == "failed"
    assert any("characters" in issue for issue in out["issues"])

def test_cli_lint_declared_count_mismatch_is_a_warning_not_a_failure(tmp_path, capsys) -> None:
    payload = json.loads((ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"))
    payload["slides"][0]["subtitle"] = "五方面基础"
    payload["slides"][0]["onscreen_expected_peer_count"] = 5
    filler = ["甲乙丙丁戊己庚辛壬癸子丑", "寅卯辰巳午未申酉戌亥零一", "二三四五六七八九十百千万", "东西南北春夏秋冬金木水火"]
    payload["slides"][0]["onscreen"] = [
        {"heading": h, "text": f"{h}项说明{filler[i]}", "items": [f"{h}项细节{filler[(i + 1) % 4]}", f"{h}项细节{filler[(i + 2) % 4]}", f"{h}项补充{filler[(i + 3) % 4]}"]}
        for i, h in enumerate(("一", "二", "三", "四"))
    ]
    broken = tmp_path / "mismatch.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")
    exit_code = main(["lint", str(broken)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert out["status"] == "passed"
    assert any("expects 5 visible peers" in warning for warning in out["warnings"])

def test_cli_lint_flags_duplicate_onscreen_heading(tmp_path, capsys) -> None:
    payload = json.loads((ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"))
    payload["slides"][0]["onscreen"] = [{"heading": "重复标题", "text": "第一段"}, {"heading": "重复标题", "text": "第二段"}]
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")
    exit_code = main(["lint", str(broken)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert out["status"] == "failed"
    assert any("duplicate module heading" in issue for issue in out["issues"])


def test_cli_lint_fails_on_overlong_onscreen_detail_line(tmp_path, capsys) -> None:
    payload = json.loads((ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"))
    payload["slides"][0]["onscreen"] = [{"heading": "模块", "items": ["需求识别到持续优化经过八个连续环节层层推进形成完整闭环缺一不可"]}]
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")
    exit_code = main(["lint", str(broken)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert out["status"] == "failed"
    assert any("meaningful characters (> 30)" in issue for issue in out["issues"])


def test_cli_outline_lists_slides_with_onscreen_module_counts(capsys) -> None:
    path = ROOT / "examples" / "final-script.example.json"
    exit_code = main(["outline", str(path)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert out["slides"]
    row = out["slides"][0]
    assert set(("id", "title", "page_type", "onscreen_module_count", "onscreen_headings")) <= set(row)
    assert row["onscreen_module_count"] == len(row["onscreen_headings"])


def test_cli_check_sync_passes_when_markdown_matches_fresh_render(tmp_path, capsys) -> None:
    final_path = ROOT / "examples" / "final-script.example.json"
    markdown_path = tmp_path / "final-script.md"
    main(["render-stage02", str(final_path), "--output", str(markdown_path)])
    capsys.readouterr()
    exit_code = main(["check-sync", str(final_path), str(markdown_path)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert out["status"] == "passed"
    assert out["issues"] == []


def test_cli_check_sync_fails_when_markdown_is_stale(tmp_path, capsys) -> None:
    final_path = ROOT / "examples" / "final-script.example.json"
    markdown_path = tmp_path / "final-script.md"
    main(["render-stage02", str(final_path), "--output", str(markdown_path)])
    capsys.readouterr()
    with markdown_path.open("a", encoding="utf-8") as handle:
        handle.write("\nhand-edited drift\n")
    exit_code = main(["check-sync", str(final_path), str(markdown_path)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert out["status"] == "failed"
    assert "does not match a fresh render" in out["issues"][0]


def test_cli_check_sync_fails_when_markdown_missing(tmp_path, capsys) -> None:
    final_path = ROOT / "examples" / "final-script.example.json"
    markdown_path = tmp_path / "does-not-exist.md"
    exit_code = main(["check-sync", str(final_path), str(markdown_path)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert out["status"] == "failed"
    assert "does not exist" in out["issues"][0]


def test_cli_status_flags_invalid_artifact(tmp_path, capsys) -> None:
    project_dir = tmp_path / "demo"
    (project_dir / "sources").mkdir(parents=True)
    (project_dir / "sources" / "a.txt").write_text("x", encoding="utf-8")
    (project_dir / "foundation.json").write_text(json.dumps({"not": "valid"}), encoding="utf-8")
    exit_code = main(["status", str(project_dir)])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert "校验未通过" in out["stage"]
    assert out["foundation"]["valid"] is False
    assert out["foundation"]["issues"]
