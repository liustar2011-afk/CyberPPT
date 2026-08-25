from __future__ import annotations

from cyberppt.stage02_cli import STAGE02_COMMANDS, main


def test_public_cli_exposes_stage02_production_commands() -> None:
    assert "prepare-stage02-handoff" in STAGE02_COMMANDS
    assert "prepare-visual-structure" in STAGE02_COMMANDS
    assert "final-script-pages" in STAGE02_COMMANDS
    assert "review-quick-page" in STAGE02_COMMANDS


def test_public_cli_does_not_expose_stage01_authoring_commands() -> None:
    for command in (
        "prepare-source-map",
        "prepare-semantic-understanding",
        "compile-source-truth",
        "prepare-outline-input",
        "compile-outline-draft",
        "assemble-final-script",
        "script-audit",
    ):
        assert command not in STAGE02_COMMANDS
        assert main([command]) == 2


def test_public_cli_help_is_available(capsys) -> None:
    assert main(["--help"]) == 0
    captured = capsys.readouterr()
    assert "CyberPPT-Stage02" in captured.out
    assert "final-script-pages" in captured.out
