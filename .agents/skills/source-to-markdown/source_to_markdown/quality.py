from __future__ import annotations

import re


def _warning(code: str, severity: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def check_quality(text: str, source_size: int | None = None) -> list[dict[str, str]]:
    """Return non-destructive quality warnings for converted Markdown."""
    warnings: list[dict[str, str]] = []
    stripped = text.strip()

    if not stripped:
        return [
            _warning(
                "empty_output",
                "error",
                "Conversion produced no text. The source may be unsupported or require OCR.",
            )
        ]

    if source_size and source_size >= 100_000:
        ratio = len(stripped.encode("utf-8")) / max(source_size, 1)
        if ratio < 0.005:
            warnings.append(
                _warning(
                    "low_text_yield",
                    "warning",
                    "Very little text was extracted relative to source size; consider OCR for scanned/image-heavy material.",
                )
            )

    if len(stripped) >= 5_000 and not re.search(r"(?m)^#{1,6}\s+\S", stripped):
        warnings.append(
            _warning(
                "no_headings",
                "warning",
                "Long output contains no Markdown headings; verify source structure and reading order.",
            )
        )

    lowered = stripped.lower()
    if "[image ocr]" in lowered:
        warnings.append(
            _warning(
                "ocr_content_present",
                "info",
                "Output contains OCR-extracted image text from a MarkItDown OCR plugin.",
            )
        )

    suspicious_tokens = ("unsupported format", "conversion failed", "could not convert")
    if any(token in lowered for token in suspicious_tokens):
        warnings.append(
            _warning(
                "conversion_placeholder",
                "warning",
                "Output appears to contain a conversion error or placeholder message.",
            )
        )

    return warnings
