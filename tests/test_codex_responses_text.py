from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from scripts.dual_image_overlay.rebuild_engine import codex_oauth_image as module


def test_post_codex_sse_returns_after_response_completed_without_connection_close() -> None:
    response_completed = threading.Event()
    release_connection = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: object) -> None:
            return

        def do_POST(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            payload = json.dumps({"type": "response.completed"}).encode("utf-8")
            self.wfile.write(b"data: " + payload + b"\n\n")
            self.wfile.flush()
            response_completed.set()
            release_connection.wait(timeout=2)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    result: list[str] = []
    errors: list[BaseException] = []
    request_finished = threading.Event()

    def request_sse() -> None:
        try:
            result.append(module._post_codex_sse({}, timeout=2))
        except BaseException as exc:  # pragma: no cover - surfaced by the assertion below
            errors.append(exc)
        finally:
            request_finished.set()

    request_thread = threading.Thread(target=request_sse, daemon=True)
    started = time.monotonic()
    with (
        patch.object(module, "_load_codex_auth", return_value=("test-token", None)),
        patch.object(module, "_codex_responses_url", return_value=f"http://127.0.0.1:{server.server_port}/responses"),
    ):
        request_thread.start()
        assert response_completed.wait(timeout=1)
        completed = request_finished.wait(timeout=0.3)

    release_connection.set()
    request_thread.join(timeout=2)
    server.shutdown()
    server.server_close()
    server_thread.join(timeout=2)

    assert completed
    assert not request_thread.is_alive()
    assert not errors
    assert result and "response.completed" in result[0]
    assert time.monotonic() - started < 0.8


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
