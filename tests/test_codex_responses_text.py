from __future__ import annotations

from unittest.mock import patch

from scripts.dual_image_overlay.rebuild_engine import codex_oauth_image as module


def test_text_response_body_uses_caller_instructions() -> None:
    body = module._build_text_responses_body(
        prompt="Return JSON",
        image_paths=[],
        model="gpt-test",
        instructions="You are a grounded report analyst.",
    )

    assert body["instructions"] == "You are a grounded report analyst."
    assert body["model"] == "gpt-test"


def test_run_codex_text_returns_response_text_with_custom_instructions() -> None:
    with (
        patch.object(module, "_post_codex_sse", return_value="sse-body") as post,
        patch.object(module, "_extract_responses_text", return_value='{"ok":true}') as extract,
    ):
        result = module.run_codex_text(
            prompt="Return JSON",
            instructions="You are a grounded report analyst.",
            model="gpt-test",
        )

    assert result == '{"ok":true}'
    body = post.call_args.args[0]
    assert body["instructions"] == "You are a grounded report analyst."
    extract.assert_called_once_with("sse-body")


def test_run_codex_vision_text_keeps_existing_vision_instruction() -> None:
    with (
        patch.object(module, "_post_codex_sse", return_value="sse-body") as post,
        patch.object(module, "_extract_responses_text", return_value="{}"),
    ):
        assert module.run_codex_vision_text(prompt="Analyze", image_paths=[]) == "{}"

    body = post.call_args.args[0]
    assert "slide image analysis" in body["instructions"]
