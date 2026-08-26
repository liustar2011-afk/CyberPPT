from __future__ import annotations

import re


_FENCE_OPEN = re.compile(r"^[ \t]*([`~]{3,})")


def _is_closing_fence(line: str, marker: str) -> bool:
    char = re.escape(marker[0])
    minimum = len(marker)
    return re.match(rf"^[ \t]*{char}{{{minimum},}}[ \t]*$", line) is not None


def _split_fenced_segments(text: str) -> list[tuple[bool, str]]:
    """Split Markdown into fenced and non-fenced segments, preserving text exactly."""
    segments: list[tuple[bool, str]] = []
    buffer: list[str] = []
    in_fence = False
    marker = ""

    for line in text.splitlines(keepends=True):
        logical = line[:-1] if line.endswith("\n") else line

        if not in_fence:
            match = _FENCE_OPEN.match(logical)
            if match:
                if buffer:
                    segments.append((False, "".join(buffer)))
                    buffer = []
                in_fence = True
                marker = match.group(1)
                buffer.append(line)
                continue

            buffer.append(line)
            continue

        buffer.append(line)
        if _is_closing_fence(logical, marker):
            segments.append((True, "".join(buffer)))
            buffer = []
            in_fence = False
            marker = ""

    if buffer:
        segments.append((in_fence, "".join(buffer)))

    return segments


def _normalize_plain_segment(text: str) -> str:
    lines = [line.rstrip(" \t") for line in text.split("\n")]
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"(?m)^(#{1,6} .+)\n(?!\n|$)", r"\1\n\n", normalized)
    if re.search(r"(?m)^#{1,6} .+\n$", normalized) and not normalized.endswith("\n\n"):
        normalized += "\n"
    return normalized


def normalize_markdown(text: str) -> str:
    """Normalize Markdown presentation without rewriting source wording.

    Normalization applies only outside fenced code/text blocks. Fenced content is
    preserved byte-for-byte except for global newline normalization.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text:
        return ""

    parts = [
        segment if fenced else _normalize_plain_segment(segment)
        for fenced, segment in _split_fenced_segments(text)
    ]
    normalized = "".join(parts).strip("\n")
    return normalized + "\n" if normalized else ""
