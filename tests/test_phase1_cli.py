from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cyberppt.cli import build_parser, main


def test_phase1_help_lists_prompt_first_commands() -> None:
    help_text = build_parser().format_help()

    assert "phase1" in help_text
    assert "codex-oauth" not in help_text


def test_phase1_prepare_routes_input_to_workflow(tmp_path: Path) -> None:
    source = tmp_path / "source_extract.md"
    source.write_text("source", encoding="utf-8")
    output = io.StringIO()

    with patch("cyberppt.cli.prepare_phase1_prompt", return_value={"status": "prompt_ready"}) as prepare, redirect_stdout(output):
        code = main(["phase1", "prepare", str(tmp_path), "--gate", "source_analysis", "--input", str(source)])

    assert code == 0
    prepare.assert_called_once_with(tmp_path, "source_analysis", source)
    assert json.loads(output.getvalue())["status"] == "prompt_ready"


def test_phase1_generate_defaults_to_manual_confirmation(tmp_path: Path) -> None:
    output = io.StringIO()

    with redirect_stdout(output):
        code = main(["phase1", "generate", str(tmp_path), "--gate", "source_analysis"])

    assert code == 3
    assert json.loads(output.getvalue())["status"] == "manual_confirmation_required"


def test_phase1_stage_parses_options_json(tmp_path: Path) -> None:
    options = [{"id": "confirm", "label": "确认"}, {"id": "revise", "label": "修改"}]

    with patch("cyberppt.cli.stage_phase1_candidate", return_value=tmp_path / "pending.json") as stage:
        code = main(
            [
                "phase1",
                "stage",
                str(tmp_path),
                "--gate",
                "source_analysis",
                "--recommendation",
                "confirm",
                "--options-json",
                json.dumps(options, ensure_ascii=False),
            ]
        )

    assert code == 0
    stage.assert_called_once_with(tmp_path, "source_analysis", "confirm", options, None)


def test_phase1_status_supports_json(tmp_path: Path) -> None:
    payload = {"schema": "cyberppt.phase1_status.v1", "gates": {}}

    with patch("cyberppt.cli.get_phase1_status", return_value=payload):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["phase1", "status", str(tmp_path), "--json"])

    assert code == 0
    assert json.loads(output.getvalue()) == payload
