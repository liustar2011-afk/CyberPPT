from __future__ import annotations

import io
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cyberppt import __main__ as entry
from cyberppt.commands.build import build_presentation, compact_build_result
from cyberppt.commands.build_cli import main as build_cli_main


def _script(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """## P01 第一页

第一段正文。

## P02 第二页

第二段正文。
""",
        encoding="utf-8",
    )
    return path


def test_root_help_is_small_tool_first() -> None:
    output = io.StringIO()
    with redirect_stdout(output):
        code = entry.main([])

    assert code == 0
    text = output.getvalue()
    assert "cyberppt build SCRIPT" in text
    assert "--advanced-help" in text
    assert "prepare-semantic-understanding" not in text


def test_console_entry_routes_build_to_small_facade() -> None:
    with patch("cyberppt.commands.build_cli.main", return_value=0) as build_main:
        code = entry.main(["build", "deck.md", "--mode", "image"])

    assert code == 0
    build_main.assert_called_once_with(["deck.md", "--mode", "image"])


def test_build_defaults_to_all_pages_visible_workspace_and_image_mode() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        script = _script(Path(tmp) / "deck.md")
        with patch(
            "cyberppt.commands.build.run_final_script_pages",
            return_value={"status": "production_ready"},
        ) as production:
            first = build_presentation(script)
            second = build_presentation(script)

        assert first["status"] == "production_ready"
        assert second["status"] == "production_ready"
        first_call = production.call_args_list[0].kwargs
        second_call = production.call_args_list[1].kwargs
        assert first_call["project"] == Path(tmp) / "deck.cyberppt"
        assert first_call["pages_raw"] == "1-2"
        assert first_call["assembly_mode"] == "image"
        assert first_call["production_build"] is True
        assert first_call["generate_images"] is True
        assert first_call["external_script"] is True
        assert first_call["build_id"] == second_call["build_id"]
        assert first_call["build_id"].startswith("build-")


def test_image_editable_and_both_share_the_same_image_batch_id() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        script = _script(Path(tmp) / "deck.md")
        with patch(
            "cyberppt.commands.build.run_final_script_pages",
            return_value={"status": "production_ready"},
        ) as production:
            build_presentation(script, mode="image")
            build_presentation(script, mode="editable")
            build_presentation(script, mode="both")

        calls = [call.kwargs for call in production.call_args_list]
        assert {call["assembly_mode"] for call in calls} == {"image", "editable", "both"}
        assert len({call["build_id"] for call in calls}) == 1


def test_build_uses_nearest_initialized_project_for_internal_script() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        (project / "manifest.yml").parent.mkdir(parents=True, exist_ok=True)
        (project / "manifest.yml").write_text("profile: script\n", encoding="utf-8")
        script = _script(project / "script" / "dist" / "final-script.md")

        with patch(
            "cyberppt.commands.build.run_final_script_pages",
            return_value={"status": "production_ready"},
        ) as production:
            build_presentation(script, mode="both")

        call = production.call_args.kwargs
        assert call["project"] == project
        assert call["external_script"] is False
        assert call["assembly_mode"] == "both"


def test_compact_result_hides_internal_receipt_noise() -> None:
    summary = {
        "status": "production_ready",
        "build_id": "build-123",
        "pages": [1, 2],
        "artifacts": {
            "output_dir": "/tmp/work",
            "exported_pptx_by_mode": {
                "image": "/tmp/work/image.pptx",
                "editable": "/tmp/work/editable.pptx",
            },
        },
        "production_readiness": {"lots": "of internal data"},
        "tool_consumption": {"more": "internal data"},
    }

    result = compact_build_result(
        summary,
        script=Path("deck.md"),
        project=Path("project"),
        mode="both",
    )

    assert result["status"] == "production_ready"
    assert result["pptx"] == summary["artifacts"]["exported_pptx_by_mode"]
    assert "production_readiness" not in result
    assert "tool_consumption" not in result


def test_build_cli_treats_needs_action_as_resumable_not_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        script = _script(Path(tmp) / "deck.md")
        summary = {
            "status": "needs_action",
            "build_id": "build-123",
            "pages": [1, 2],
            "manifest": str(Path(tmp) / "run" / "page_image_pairs.json"),
            "actions": [{"action": "prepare_editable_page"}],
        }
        output = io.StringIO()
        with (
            patch("cyberppt.commands.build_cli.build_presentation", return_value=summary),
            redirect_stdout(output),
        ):
            code = build_cli_main([str(script), "--mode", "editable"])

        assert code == 0
        text = output.getvalue()
        assert "status: needs_action" in text
        assert "action: prepare_editable_page" in text
        assert "rerun the same cyberppt build command" in text
