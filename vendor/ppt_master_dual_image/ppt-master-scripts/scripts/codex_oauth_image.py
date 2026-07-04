#!/usr/bin/env python3
"""Codex OAuth image generation/editing helper.

This script is intentionally self-contained and uses only the Python standard
library. It reads the local Codex/ChatGPT OAuth token from `~/.codex/auth.json`
and calls the host image backend directly, so no OpenAI API key is required.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib import error, request


DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "1280x720"
DEFAULT_QUALITY = "high"
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_TIMEOUT = 600
DEFAULT_CODEX_AUTH_FILE = "~/.codex/auth.json"
DEFAULT_CODEX_IMAGES_BASE_URL = "https://chatgpt.com/backend-api/codex"
DEFAULT_CODEX_RESPONSES_BASE_URL = "https://chatgpt.com/backend-api/codex"
DEFAULT_CODEX_RESPONSES_MODEL = "gpt-5.5"
MAX_IMAGE_BYTES = 50 * 1024 * 1024
MAX_CODEX_RESPONSE_BYTES = 96 * 1024 * 1024
MAX_CODEX_BASE64_CHARS = 96 * 1024 * 1024
GPT_IMAGE_2_MIN_PIXELS = 655_360
GPT_IMAGE_2_MAX_PIXELS = 8_294_400
GPT_IMAGE_2_MAX_EDGE = 3840
GPT_IMAGE_2_MAX_RATIO = 3.0
CHATGPT_AUTH_CLAIM = "https://api.openai.com/auth"
CHATGPT_ACCOUNT_ID_CLAIM = "chatgpt_account_id"


def _die(message: str, code: int = 1) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _codex_auth_file() -> Path:
    return Path(os.getenv("CODEX_AUTH_FILE", DEFAULT_CODEX_AUTH_FILE)).expanduser()


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _infer_codex_account_id(tokens: dict[str, Any]) -> str | None:
    account_id = tokens.get("account_id")
    if isinstance(account_id, str) and account_id.strip():
        return account_id.strip()
    id_token = tokens.get("id_token")
    if not isinstance(id_token, str) or not id_token.strip():
        return None
    auth_claim = _decode_jwt_payload(id_token).get(CHATGPT_AUTH_CLAIM)
    if not isinstance(auth_claim, dict):
        return None
    chatgpt_account_id = auth_claim.get(CHATGPT_ACCOUNT_ID_CLAIM)
    if isinstance(chatgpt_account_id, str) and chatgpt_account_id.strip():
        return chatgpt_account_id.strip()
    return None


def _load_codex_auth() -> tuple[str, str | None] | None:
    path = _codex_auth_file()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    tokens = data.get("tokens")
    if not isinstance(tokens, dict):
        return None
    token = tokens.get("access_token")
    if isinstance(token, str) and token.strip():
        return token.strip(), _infer_codex_account_id(tokens)
    return None


def codex_available() -> bool:
    """Return whether local Codex OAuth credentials are available."""
    return _load_codex_auth() is not None


def _codex_base_url() -> str:
    raw = (
        os.getenv("CODEX_IMAGES_BASE_URL")
        or DEFAULT_CODEX_IMAGES_BASE_URL
    ).strip()
    if not raw:
        return DEFAULT_CODEX_IMAGES_BASE_URL
    if re.fullmatch(r"https?://chatgpt\.com/backend-api(?:/codex)?(?:/v1)?/?", raw, re.I):
        return DEFAULT_CODEX_IMAGES_BASE_URL
    return raw.rstrip("/")


def _codex_image_url(operation: str) -> str:
    endpoint = "images/edits" if operation == "edit" else "images/generations"
    return f"{_codex_base_url()}/{endpoint}"


def _codex_responses_base_url() -> str:
    raw = os.getenv("CODEX_RESPONSES_BASE_URL", DEFAULT_CODEX_RESPONSES_BASE_URL).strip()
    if not raw:
        return DEFAULT_CODEX_RESPONSES_BASE_URL
    if re.fullmatch(r"https?://chatgpt\.com/backend-api(?:/codex)?(?:/v1)?/?", raw, re.I):
        return DEFAULT_CODEX_RESPONSES_BASE_URL
    return raw.rstrip("/")


def _codex_responses_url() -> str:
    return f"{_codex_responses_base_url()}/responses"


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if mime and mime.startswith("image/"):
        return mime
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


def _image_to_data_url(path: Path) -> str:
    if not path.exists():
        _die(f"Image file not found: {path}")
    if path.stat().st_size > MAX_IMAGE_BYTES:
        print(f"Warning: image exceeds 50MB limit: {path}", file=sys.stderr)
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{_guess_mime(path)};base64,{encoded}"


def _codex_image_reference(path: Path) -> dict[str, str]:
    return {"image_url": _image_to_data_url(path)}


def _parse_size(size: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"([1-9][0-9]*)x([1-9][0-9]*)", size)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def validate_gpt_image_2_size(size: str) -> None:
    """Validate gpt-image-2 size constraints."""
    if size == "auto":
        return
    parsed = _parse_size(size)
    if parsed is None:
        _die("size must be auto or WIDTHxHEIGHT, for example 1280x720.")
    width, height = parsed
    max_edge = max(width, height)
    min_edge = min(width, height)
    total_pixels = width * height
    if max_edge > GPT_IMAGE_2_MAX_EDGE:
        _die("gpt-image-2 size maximum edge length must be <= 3840px.")
    if width % 16 != 0 or height % 16 != 0:
        _die("gpt-image-2 size width and height must be multiples of 16px.")
    if max_edge / min_edge > GPT_IMAGE_2_MAX_RATIO:
        _die("gpt-image-2 size long edge to short edge ratio must not exceed 3:1.")
    if total_pixels < GPT_IMAGE_2_MIN_PIXELS or total_pixels > GPT_IMAGE_2_MAX_PIXELS:
        _die("gpt-image-2 size total pixels must be between 655,360 and 8,294,400.")


def _build_body(
    *,
    prompt: str,
    image_paths: list[Path],
    model: str,
    size: str,
    quality: str,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "prompt": prompt,
        "model": model,
        "size": size,
        "quality": quality,
    }
    if image_paths:
        body["images"] = [_codex_image_reference(path) for path in image_paths]
    return body


def _codex_content(prompt: str, image_paths: list[Path]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    for path in image_paths:
        content.append(
            {
                "type": "input_image",
                "image_url": _image_to_data_url(path),
                "detail": "auto",
            }
        )
    return content


def _build_responses_body(
    *,
    prompt: str,
    image_paths: list[Path],
    model: str,
    size: str,
    quality: str,
    force_tool_choice: bool = True,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": os.getenv("CODEX_RESPONSES_MODEL", DEFAULT_CODEX_RESPONSES_MODEL),
        "input": [{"role": "user", "content": _codex_content(prompt, image_paths)}],
        "instructions": "You are an image generation assistant.",
        "tools": [
            {
                "type": "image_generation",
                "model": model,
                "size": size,
                "quality": quality,
                "output_format": DEFAULT_OUTPUT_FORMAT,
            }
        ],
        "stream": True,
        "store": False,
    }
    if force_tool_choice:
        body["tool_choice"] = {"type": "image_generation"}
    return body


def _build_text_responses_body(
    *,
    prompt: str,
    image_paths: list[Path],
    model: str | None = None,
) -> dict[str, Any]:
    """Build a Codex Responses request for text/JSON vision analysis."""
    return {
        "model": model or os.getenv("CODEX_RESPONSES_MODEL", DEFAULT_CODEX_RESPONSES_MODEL),
        "input": [{"role": "user", "content": _codex_content(prompt, image_paths)}],
        "instructions": (
            "You are a precise slide image analysis assistant. "
            "Return only valid JSON when the user asks for JSON."
        ),
        "stream": True,
        "store": False,
    }


def _post_codex_image_json(url: str, body: dict[str, Any], timeout: int) -> dict[str, Any]:
    auth = _load_codex_auth()
    if not auth:
        _die(
            f"Codex OAuth auth is missing. Expected {_codex_auth_file()}. "
            "Run `codex login` in this account first."
        )
    token, account_id = auth
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "originator": "ppt-master-image-cli",
        "User-Agent": "ppt-master-image-cli/0.1.0",
    }
    if account_id:
        headers["ChatGPT-Account-ID"] = account_id
    req = request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            text = resp.read(MAX_CODEX_RESPONSE_BYTES).decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        detail = exc.read(4096).decode("utf-8", errors="replace")
        raise RuntimeError(f"Codex Images request failed (HTTP {exc.code}): {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Codex Images request failed: {exc.reason}") from exc
    try:
        response = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Expected JSON Codex Images response, got: {text[:500]}") from exc
    if not isinstance(response, dict):
        raise RuntimeError("Expected JSON object Codex Images response.")
    return response


def _post_codex_sse(body: dict[str, Any], timeout: int) -> str:
    auth = _load_codex_auth()
    if not auth:
        _die(
            f"Codex OAuth auth is missing. Expected {_codex_auth_file()}. "
            "Run `codex login` in this account first."
        )
    token, _account_id = auth
    req = request.Request(
        _codex_responses_url(),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": "ppt-master-image-cli/0.1.0",
        },
    )
    try:
        started = time.time()
        with request.urlopen(req, timeout=timeout) as resp:
            chunks: list[bytes] = []
            total = 0
            while True:
                if time.time() - started > timeout:
                    _die(f"Codex Responses request exceeded total timeout of {timeout}s.")
                chunk = resp.read(1024 * 64)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_CODEX_RESPONSE_BYTES:
                    _die("Codex image response exceeded size limit.")
                chunks.append(chunk)
            return b"".join(chunks).decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        detail = exc.read(4096).decode("utf-8", errors="replace")
        raise RuntimeError(f"Codex Responses request failed (HTTP {exc.code}): {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Codex Responses request failed: {exc.reason}") from exc


def _extract_image_payloads(response: dict[str, Any]) -> list[str]:
    error_obj = response.get("error")
    if isinstance(error_obj, dict):
        message = error_obj.get("message") or error_obj.get("code")
        raise RuntimeError(str(message or "Codex image generation failed."))
    data = response.get("data")
    if not isinstance(data, list):
        raise RuntimeError("Codex image response did not include a data array.")
    payloads = [
        item["b64_json"]
        for item in data
        if isinstance(item, dict) and isinstance(item.get("b64_json"), str)
    ]
    if not payloads:
        raise RuntimeError("No image payload found in Codex image response.")
    return payloads


def _parse_sse_events(body: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in body.splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[6:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _extract_responses_payloads(body: str) -> list[str]:
    events = _parse_sse_events(body)
    for event in events:
        if event.get("type") in {"response.failed", "error"}:
            error_obj = event.get("error")
            if isinstance(error_obj, dict):
                message = error_obj.get("message") or error_obj.get("code")
            else:
                message = event.get("message")
            raise RuntimeError(str(message or "Codex image generation failed."))

    payloads: list[str] = []
    for event in events:
        item = event.get("item")
        if (
            event.get("type") == "response.output_item.done"
            and isinstance(item, dict)
            and item.get("type") == "image_generation_call"
            and isinstance(item.get("result"), str)
        ):
            payloads.append(item["result"])

    if payloads:
        return payloads

    for event in events:
        if event.get("type") != "response.completed":
            continue
        response_obj = event.get("response")
        output = response_obj.get("output") if isinstance(response_obj, dict) else None
        if not isinstance(output, list):
            continue
        for item in output:
            if (
                isinstance(item, dict)
                and item.get("type") == "image_generation_call"
                and isinstance(item.get("result"), str)
            ):
                payloads.append(item["result"])
    if not payloads:
        raise RuntimeError("No image payload found in Codex Responses response.")
    return payloads


def _extract_responses_text(body: str) -> str:
    """Extract final text output from a Codex Responses SSE body."""
    events = _parse_sse_events(body)
    for event in events:
        if event.get("type") in {"response.failed", "error"}:
            error_obj = event.get("error")
            if isinstance(error_obj, dict):
                message = error_obj.get("message") or error_obj.get("code")
            else:
                message = event.get("message")
            raise RuntimeError(str(message or "Codex vision analysis failed."))

    delta_chunks: list[str] = []
    final_chunks: list[str] = []
    for event in events:
        if event.get("type") in {"response.output_text.delta", "response.refusal.delta"}:
            delta = event.get("delta")
            if isinstance(delta, str):
                delta_chunks.append(delta)
        if event.get("type") == "response.output_item.done":
            item = event.get("item")
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") in {"output_text", "text"}:
                    text = part.get("text")
                    if isinstance(text, str):
                        final_chunks.append(text)

    if delta_chunks:
        return "".join(delta_chunks).strip()
    if final_chunks:
        return "".join(final_chunks).strip()

    completed_chunks: list[str] = []
    for event in events:
        if event.get("type") != "response.completed":
            continue
        response_obj = event.get("response")
        output = response_obj.get("output") if isinstance(response_obj, dict) else None
        if not isinstance(output, list):
            continue
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") in {"output_text", "text"}:
                    text = part.get("text")
                    if isinstance(text, str):
                        completed_chunks.append(text)
    text = "".join(completed_chunks).strip()
    if not text:
        raise RuntimeError("No text output found in Codex Responses response.")
    return text


def _write_image(image_b64: str, output_path: Path, *, force: bool) -> None:
    if len(image_b64) > MAX_CODEX_BASE64_CHARS:
        _die("Image payload exceeded size limit.")
    if output_path.exists() and not force:
        _die(f"Output already exists: {output_path} (use --force to overwrite)")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(image_b64))


def _write_images(payloads: list[str], output_paths: list[Path], *, force: bool) -> None:
    if len(payloads) < len(output_paths):
        _die(
            f"Codex returned {len(payloads)} image(s), but {len(output_paths)} independent image(s) were required. "
            "Do not accept a stitched comparison image as a substitute."
        )
    for payload, output_path in zip(payloads, output_paths):
        _write_image(payload, output_path, force=force)
        print(f"Wrote {output_path}")


def run_codex_image(
    *,
    prompt: str,
    output_path: Path,
    image_paths: list[Path] | None = None,
    model: str = DEFAULT_MODEL,
    size: str = DEFAULT_SIZE,
    quality: str = DEFAULT_QUALITY,
    force: bool = False,
    dry_run: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
) -> Path:
    """Generate or edit one image through Codex OAuth."""
    image_paths = image_paths or []
    if "gpt-image-2" in model:
        validate_gpt_image_2_size(size)
    operation = "edit" if image_paths else "generate"
    body = _build_body(
        prompt=prompt,
        image_paths=image_paths,
        model=model,
        size=size,
        quality=quality,
    )
    url = _codex_image_url(operation)
    if dry_run:
        preview = {
            "backend": "codex-oauth",
            "endpoint": url,
            "fallback_endpoint": _codex_responses_url(),
            "operation": operation,
            "auth_file": str(_codex_auth_file()),
            "model": model,
            "size": size,
            "quality": quality,
            "input_images": [str(path) for path in image_paths],
            "output": str(output_path),
        }
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return output_path
    print(
        f"Calling Codex OAuth image backend ({operation}) with {len(image_paths)} input image(s).",
        file=sys.stderr,
    )
    started = time.time()
    try:
        response = _post_codex_image_json(url, body, timeout)
        payloads = _extract_image_payloads(response)
        endpoint_label = "images"
    except Exception as first_error:
        print(f"Codex Images endpoint failed; retrying Responses endpoint: {first_error}", file=sys.stderr)
        responses_body = _build_responses_body(
            prompt=prompt,
            image_paths=image_paths,
            model=model,
            size=size,
            quality=quality,
            force_tool_choice=False,
        )
        response_text = _post_codex_sse(responses_body, timeout)
        payloads = _extract_responses_payloads(response_text)
        endpoint_label = "responses"
    elapsed = time.time() - started
    print(f"Codex OAuth image completed via {endpoint_label} in {elapsed:.1f}s.", file=sys.stderr)
    _write_image(payloads[0], output_path, force=force)
    print(f"Wrote {output_path}")
    return output_path


def run_codex_multi_image_once(
    *,
    prompt: str,
    output_paths: list[Path],
    model: str = DEFAULT_MODEL,
    size: str = DEFAULT_SIZE,
    quality: str = DEFAULT_QUALITY,
    force: bool = False,
    dry_run: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[Path]:
    """Ask Codex once for multiple independent image outputs.

    This is for ChatGPT-style "generate two pages from one prompt" workflows.
    It intentionally does not loop `n` separate requests.
    """
    if "gpt-image-2" in model:
        validate_gpt_image_2_size(size)
    if dry_run:
        preview = {
            "backend": "codex-oauth-responses",
            "endpoint": _codex_responses_url(),
            "operation": "generate-multiple-once",
            "auth_file": str(_codex_auth_file()),
            "model": model,
            "size": size,
            "quality": quality,
            "outputs": [str(path) for path in output_paths],
            "required_images": len(output_paths),
        }
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return output_paths
    body = _build_responses_body(
        prompt=prompt,
        image_paths=[],
        model=model,
        size=size,
        quality=quality,
        force_tool_choice=False,
    )
    print(
        f"Calling Codex OAuth Responses backend once for {len(output_paths)} image output(s).",
        file=sys.stderr,
    )
    started = time.time()
    response_text = _post_codex_sse(body, timeout)
    payloads = _extract_responses_payloads(response_text)
    elapsed = time.time() - started
    print(f"Codex OAuth multi-image request completed in {elapsed:.1f}s.", file=sys.stderr)
    _write_images(payloads, output_paths, force=force)
    return output_paths


def run_codex_vision_text(
    *,
    prompt: str,
    image_paths: list[Path],
    model: str | None = None,
    dry_run: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Analyze images with Codex OAuth Responses and return text output."""
    if dry_run:
        preview = {
            "backend": "codex-oauth-responses",
            "endpoint": _codex_responses_url(),
            "operation": "vision-text",
            "auth_file": str(_codex_auth_file()),
            "model": model or os.getenv("CODEX_RESPONSES_MODEL", DEFAULT_CODEX_RESPONSES_MODEL),
            "input_images": [str(path) for path in image_paths],
        }
        return json.dumps(preview, ensure_ascii=False, indent=2)
    body = _build_text_responses_body(prompt=prompt, image_paths=image_paths, model=model)
    print(
        f"Calling Codex OAuth Responses vision backend with {len(image_paths)} image(s).",
        file=sys.stderr,
    )
    started = time.time()
    response_text = _post_codex_sse(body, timeout)
    output_text = _extract_responses_text(response_text)
    elapsed = time.time() - started
    print(f"Codex OAuth vision analysis completed in {elapsed:.1f}s.", file=sys.stderr)
    return output_text


def _read_prompt(prompt: str | None, prompt_file: str | None) -> str:
    if prompt and prompt_file:
        _die("Use --prompt or --prompt-file, not both.")
    if prompt_file:
        return Path(prompt_file).read_text(encoding="utf-8").strip()
    if prompt:
        return prompt.strip()
    _die("Missing prompt. Use --prompt or --prompt-file.")
    return ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate/edit images through Codex OAuth.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("generate", "Create a new image"), ("edit", "Edit an input image")):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("--prompt")
        sub.add_argument("--prompt-file")
        sub.add_argument("--out", required=True, type=Path)
        sub.add_argument("--model", default=DEFAULT_MODEL)
        sub.add_argument("--size", default=DEFAULT_SIZE)
        sub.add_argument("--quality", default=DEFAULT_QUALITY)
        sub.add_argument("--force", action="store_true")
        sub.add_argument("--dry-run", action="store_true")
        sub.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
        if name == "edit":
            sub.add_argument("--image", action="append", required=True, type=Path)
    many = subparsers.add_parser("generate-many", help="Ask once for multiple independent images")
    many.add_argument("--prompt")
    many.add_argument("--prompt-file")
    many.add_argument("--out", action="append", required=True, type=Path, help="Output path. Repeat for each required image.")
    many.add_argument("--model", default=DEFAULT_MODEL)
    many.add_argument("--size", default=DEFAULT_SIZE)
    many.add_argument("--quality", default=DEFAULT_QUALITY)
    many.add_argument("--force", action="store_true")
    many.add_argument("--dry-run", action="store_true")
    many.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    if args.command == "generate-many":
        run_codex_multi_image_once(
            prompt=prompt,
            output_paths=args.out,
            model=args.model,
            size=args.size,
            quality=args.quality,
            force=args.force,
            dry_run=args.dry_run,
            timeout=args.timeout,
        )
    else:
        run_codex_image(
            prompt=prompt,
            output_path=args.out,
            image_paths=getattr(args, "image", []) or [],
            model=args.model,
            size=args.size,
            quality=args.quality,
            force=args.force,
            dry_run=args.dry_run,
            timeout=args.timeout,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
