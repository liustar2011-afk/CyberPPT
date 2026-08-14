from __future__ import annotations

import json
import os
from importlib.metadata import PackageNotFoundError, version
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .normalize import normalize_markdown
from .quality import check_quality


class ConversionError(RuntimeError):
    """Raised when a source cannot be converted under the selected policy."""


@dataclass(slots=True)
class ConversionOptions:
    force: bool = False
    allow_empty: bool = False
    ocr: bool = False
    ocr_model: str | None = None


@dataclass(slots=True)
class ConversionResult:
    source: Path
    destination: Path
    warnings: list[dict[str, str]] = field(default_factory=list)
    text_chars: int = 0


def default_output_path(source: Path) -> Path:
    return source.with_suffix(".md")


def _yaml_string(value: str) -> str:
    # JSON strings are valid YAML scalars and give deterministic escaping.
    return json.dumps(value, ensure_ascii=False)


def _front_matter(source: Path, options: ConversionOptions) -> str:
    converted_at = datetime.now().astimezone().isoformat(timespec="seconds")
    return "\n".join(
        [
            "---",
            f"source_file: {_yaml_string(source.name)}",
            f"source_format: {_yaml_string(source.suffix.lower())}",
            'conversion_engine: "Microsoft MarkItDown"',
            f"converted_at: {_yaml_string(converted_at)}",
            f"ocr_requested: {'true' if options.ocr else 'false'}",
            "---",
            "",
        ]
    )


def _default_converter_factory(options: ConversionOptions) -> Any:
    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise ConversionError(
            "Microsoft MarkItDown is not installed. Install this skill with `pip install -e .`."
        ) from exc

    if not options.ocr:
        return MarkItDown()

    try:
        from openai import OpenAI
        import markitdown_ocr  # noqa: F401  # ensures an actionable import check
    except ImportError as exc:
        raise ConversionError(
            "OCR requested but optional dependencies are missing. Install with "
            "`pip install -e '.[ocr]'` so `markitdown-ocr` and `openai` are available."
        ) from exc

    if not os.getenv("OPENAI_API_KEY"):
        raise ConversionError(
            "OCR requested but OPENAI_API_KEY is not set. Configure an OpenAI-compatible "
            "client credential or run without --ocr."
        )

    model = options.ocr_model or os.getenv("MARKITDOWN_OCR_MODEL")
    if not model:
        raise ConversionError(
            "OCR requested but no model was specified. Use --ocr-model MODEL or set "
            "MARKITDOWN_OCR_MODEL."
        )

    return MarkItDown(enable_plugins=True, llm_client=OpenAI(), llm_model=model)


def convert_file(
    source: Path,
    destination: Path,
    options: ConversionOptions,
    converter_factory: Callable[[ConversionOptions], Any] | None = None,
) -> ConversionResult:
    source = Path(source)
    destination = Path(destination)

    if source.resolve(strict=False) == destination.resolve(strict=False):
        raise ConversionError(
            f"Source and destination resolve to the same path: {source}. "
            "Choose a different output path."
        )

    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {source}")
    if destination.exists() and not options.force:
        raise FileExistsError(
            f"Destination already exists: {destination}. Use --force to overwrite."
        )

    factory = converter_factory or _default_converter_factory
    converter = factory(options)
    try:
        convert_local = getattr(converter, "convert_local", None)
        if callable(convert_local):
            converted = convert_local(str(source))
        else:
            converted = converter.convert(str(source))
        raw_text = getattr(converted, "text_content")
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Failed to convert {source.name}: {exc}") from exc

    normalized = normalize_markdown(raw_text or "")
    warnings = check_quality(normalized, source_size=source.stat().st_size)
    has_empty_error = any(
        item["code"] == "empty_output" and item["severity"] == "error"
        for item in warnings
    )
    if has_empty_error and not options.allow_empty:
        raise ConversionError(
            f"Conversion produced no text for {source.name}; the source may require OCR."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    body = _front_matter(source, options) + normalized
    destination.write_text(body, encoding="utf-8", newline="\n")

    return ConversionResult(
        source=source,
        destination=destination,
        warnings=warnings,
        text_chars=len(normalized),
    )
