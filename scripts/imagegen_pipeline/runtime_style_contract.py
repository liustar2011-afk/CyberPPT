"""Generic runtime style contract for model-visible ImageGen prompts.

Internal style ids/names remain useful routing and provenance metadata, but the
prompt sent to ImageGen must contain only self-contained visual rules. This
module centralizes that projection and terminal-lock enforcement so all live
styles share one production mechanism.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from scripts.imagegen_pipeline.style_library import load_style_lock

TERMINAL_EXECUTION_HEADING = "【最终视觉执行约束｜最高优先级】"

_INTERNAL_STYLE_TOKEN_RE = re.compile(
    r"(?i)(?:\bstyle\s*0?9\b|\bstyle\s*10\b|风格\s*0?9|风格\s*10)"
)
_LEGACY_TERMINAL_HEADINGS = (
    "【风格09最终执行锁｜最高优先级】",
    "【风格10最终执行锁｜最高优先级】",
    "### Final ImageGen execution lock — hard",
    TERMINAL_EXECUTION_HEADING,
)


@dataclass(frozen=True)
class RuntimeStyleContract:
    contract: str
    terminal_lock: str
    source: str
    sha256: str
    reference_image: Path | None = None


def _model_visible_text(text: str) -> str:
    """Remove routing labels while preserving authored visual rules."""

    cleaned = _INTERNAL_STYLE_TOKEN_RE.sub("当前视觉规则", str(text or ""))
    cleaned = re.sub(r"(?m)^\s*##\s*扩展风格\d+[^\n]*$", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*<!--\s*style\d+:[^>]+-->\s*$", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _split_terminal_contract(raw_contract: str) -> tuple[str, str]:
    """Split the authored terminal section before sanitizing style labels."""

    positions = [
        (raw_contract.find(marker), marker)
        for marker in _LEGACY_TERMINAL_HEADINGS
        if marker in raw_contract
    ]
    if not positions:
        return raw_contract, ""
    index, marker = min(positions, key=lambda item: item[0])
    return raw_contract[:index].rstrip(), raw_contract[index + len(marker) :].strip()


def project_runtime_style_contract(
    raw_contract: str,
    *,
    source: str = "runtime_projection",
    reference_image: Path | None = None,
    digest: str = "",
    explicit_terminal: str = "",
) -> RuntimeStyleContract:
    """Project any authored/transformed style contract into model-visible rules.

    This is deliberately independent of style ids. Callers may first apply
    their existing content-first or creative-brief compatibility transforms,
    then pass that transformed contract here. The projection removes routing
    labels and moves the terminal fragment to one generic execution lock.
    """

    raw = str(raw_contract or "")
    if not raw.strip():
        raise ValueError("runtime style projection requires a non-empty contract")
    raw_body, raw_terminal = _split_terminal_contract(raw)
    if explicit_terminal.strip():
        raw_terminal = explicit_terminal.strip()
    contract = _model_visible_text(raw_body)
    terminal = _model_visible_text(raw_terminal)
    if not contract:
        raise ValueError("runtime style projection has no model-visible rules")
    resolved_digest = str(digest or "").strip()
    if not resolved_digest:
        resolved_digest = sha256((contract + "\n" + terminal).encode("utf-8")).hexdigest().upper()
    return RuntimeStyleContract(
        contract=contract,
        terminal_lock=terminal,
        source=source,
        sha256=resolved_digest,
        reference_image=reference_image,
    )


def load_runtime_style_contract(style_lock: Path) -> RuntimeStyleContract:
    payload = load_style_lock(style_lock)
    style = payload.get("style") if isinstance(payload.get("style"), dict) else payload
    raw_contract = str(style.get("prompt_contract") or style.get("style_prompt_v2") or "")
    if not raw_contract.strip():
        raise ValueError(f"style lock has no runtime prompt contract: {style_lock}")

    reference_image = None
    reference = payload.get("reference_image")
    if isinstance(reference, dict) and reference.get("path"):
        reference_image = Path(str(reference["path"]))
    return project_runtime_style_contract(
        raw_contract,
        source=str(style.get("prompt_contract_source") or payload.get("style_source") or style_lock),
        reference_image=reference_image,
        digest=str(style.get("prompt_contract_sha256") or "").strip(),
        explicit_terminal=str(style.get("terminal_lock") or "").strip(),
    )


def _without_terminal_duplicates(body: str, terminal_lock: str) -> str:
    """Remove exact terminal instruction lines already present in the body.

    Page-specific prose is preserved. Only whole lines that exactly equal a
    non-empty terminal-lock line are removed, preventing the same hard rule from
    being sent to the model twice when the terminal lock is reasserted.
    """

    terminal_lines = {
        line.strip()
        for line in str(terminal_lock or "").splitlines()
        if line.strip()
    }
    if not terminal_lines:
        return body.rstrip()
    retained = [
        line
        for line in body.splitlines()
        if line.strip() not in terminal_lines
    ]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(retained)).rstrip()


def enforce_terminal_execution_lock(prompt: str, runtime: RuntimeStyleContract) -> str:
    """Append exactly one generic terminal lock at the absolute end."""

    body = str(prompt).rstrip()
    for marker in _LEGACY_TERMINAL_HEADINGS:
        pos = body.find(marker)
        if pos >= 0:
            body = body[:pos].rstrip()
    if not runtime.terminal_lock:
        return body
    terminal = runtime.terminal_lock.strip()
    body = _without_terminal_duplicates(body, terminal)
    return f"{body}\n\n{TERMINAL_EXECUTION_HEADING}\n{terminal}\n"


def internal_style_token_leaks(text: str) -> tuple[str, ...]:
    return tuple(match.group(0) for match in _INTERNAL_STYLE_TOKEN_RE.finditer(text))


__all__ = [
    "RuntimeStyleContract",
    "TERMINAL_EXECUTION_HEADING",
    "enforce_terminal_execution_lock",
    "internal_style_token_leaks",
    "load_runtime_style_contract",
    "project_runtime_style_contract",
]
