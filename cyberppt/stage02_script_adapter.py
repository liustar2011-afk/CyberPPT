"""Stage 02-only script adaptation.

Stage 01 owns the Final Script contract.  Stage 02 may additionally accept an
external manuscript, but external aliases must never leak back into the Stage 01
parser because that would create two content authorities there.
"""

from __future__ import annotations

from dataclasses import replace
import re

from cyberppt.script_quality.models import ScriptDocument, ScriptPage
from cyberppt.script_quality.parsing import PAGE_HEADING_RE, parse_script_markdown


VALID_SOURCE_MODES = frozenset({"script_file", "external_script", "autonomous_contract"})
_EXTERNAL_CONTENT_HEADING_RE = re.compile(r"(?m)^###\s+内容\s*$")
_EXTERNAL_CONTENT_FIELD_RE = re.compile(r"(?m)^(?P<prefix>\s*-\s*)内容(?P<sep>[：:])(?P<value>.*)$")
_FORMAL_PAGE_MARKER_RE = re.compile(
    r"(?m)^(?:\s*-\s*(?:页面类型|页面标题|页面使命|核心结论|主判断|完整文字稿|上屏文字)[：:]|"
    r"###\s+(?:完整文字稿|上屏文字|保真文字)\s*$)"
)


def _normalize_external_aliases(text: str) -> str:
    text = _EXTERNAL_CONTENT_HEADING_RE.sub("### 完整文字稿", text)
    return _EXTERNAL_CONTENT_FIELD_RE.sub(
        lambda match: (
            f"{match.group('prefix')}完整文字稿{match.group('sep')}"
            f"{match.group('value')}"
        ),
        text,
    )


def _normalize_external_numbered_pages(text: str) -> str:
    """Make numbered free-form external pages readable by the Stage 1 parser.

    Structured external pages use the Stage 02-only ``内容`` alias, normalized
    above.  A numbered page with no formal CyberPPT fields is a free manuscript:
    everything below its page heading is content.  Existing formal CyberPPT
    scripts remain untouched for backward compatibility.
    """

    matches = list(PAGE_HEADING_RE.finditer(text))
    if not matches:
        return text

    chunks: list[str] = []
    prefix = text[: matches[0].start()]
    if prefix:
        chunks.append(prefix.rstrip())

    for index, match in enumerate(matches):
        sequence = int(match.group(1) or match.group(3))
        title = (match.group(2) or match.group(4)).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip("\n")
        heading = match.group(0).strip()
        if _FORMAL_PAGE_MARKER_RE.search(body):
            chunks.append(f"{heading}\n{body}".rstrip())
            continue

        chunks.append(
            "\n".join(
                (
                    f"## P{sequence:02d} {title}",
                    "",
                    "- 页面类型：内容页",
                    f"- 页面标题：{title}",
                    "",
                    "### 完整文字稿",
                    "",
                    body.strip(),
                )
            ).rstrip()
        )

    return "\n\n".join(chunk for chunk in chunks if chunk).rstrip() + "\n"


def normalize_external_script(text: str) -> str:
    """Normalize only Stage 02 external-manuscript syntax."""

    return _normalize_external_numbered_pages(_normalize_external_aliases(text))


def parse_stage02_script(text: str, *, source_mode: str) -> ScriptDocument:
    """Parse a Stage 02 input without expanding the Stage 01 grammar."""

    if source_mode not in VALID_SOURCE_MODES:
        raise ValueError(f"unsupported Stage 02 source_mode: {source_mode}")
    normalized = normalize_external_script(text) if source_mode == "external_script" else text
    return parse_script_markdown(normalized, page_contracts={})


def project_stage02_runtime_page(page: ScriptPage, *, source_mode: str) -> ScriptPage:
    """Return the page projection Stage 02 is allowed to rewrite visually.

    Final Script 1.2 deliberately has no AUTHOR-owned ``onscreen`` layer.  Its
    complete copy therefore becomes the Stage 02 runtime text source.  External
    manuscripts follow the same rule.  Legacy Final Script 1.0/1.1 pages keep
    their authored onscreen text.
    """

    if source_mode not in VALID_SOURCE_MODES:
        raise ValueError(f"unsupported Stage 02 source_mode: {source_mode}")

    derive_from_content = (
        source_mode == "external_script"
        or page.onscreen_source == "full_copy_stage02_source"
    )
    if not derive_from_content:
        return page

    runtime_text = page.full_prose.strip() or page.onscreen_text
    runtime_source = (
        "external_content_stage02_source"
        if source_mode == "external_script"
        else "full_copy_stage02_source"
    )
    return replace(
        page,
        onscreen_text=runtime_text,
        raw_onscreen_text=runtime_text,
        onscreen_source=runtime_source,
    )


__all__ = [
    "VALID_SOURCE_MODES",
    "normalize_external_script",
    "parse_stage02_script",
    "project_stage02_runtime_page",
]
