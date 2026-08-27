"""Generic runtime style contract for model-visible ImageGen prompts.

Internal style ids/names remain useful routing and provenance metadata, but the
prompt sent to ImageGen must contain only self-contained visual rules.  This
module centralizes that projection and terminal-lock enforcement so Style 09,
Style 10, and future live styles share one production mechanism.
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
    """Remove routing labels while preserving the authored visual rules."""

    cleaned = _INTERNAL_STYLE_TOKEN_RE.sub("当前视觉规则", str(text or ""))
    cleaned = re.sub(r"(?m)^\s*##\s*扩展风格\d+[^\n]*$", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*<!--\s*style\d+:[^>]+-->\s*$", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _terminal_lock(contract: str) -> str:
    positions = [
        (contract.find(marker), marker)
        for marker in _LEGACY_TERMINAL_HEADINGS
        if marker in contract
    ]
    if not positions:
        return ""
    index, marker = min(positions, key=lambda item: item[0])
    return contract[index + len(marker) :].strip()


def load_runtime_style_contract(style_lock: Path) -> RuntimeStyleContract:
    payload = load_style_lock(style_lock)
    style = payload.get("style") if isinstance(payload.get("style"), dict) else payload
    contract = _model_visible_text(str(style.get("prompt_contract") or style.get("style_prompt_v2") or ""))
    if not contract:
        raise ValueError(f"style lock has no runtime prompt contract: {style_lock}")
    terminal = _terminal_lock(contract)
    if terminal:
        for marker in _LEGACY_TERMINAL_HEADINGS:
            pos = contract.find(marker)
            if pos >= 0:
                contract = contract[:pos].rstrip()
                break
    source = str(style.get("prompt_contract_source") or payload.get("style_source") or style_lock)
    reference_image = None
    reference = payload.get("reference_image")
    if isinstance(reference, dict) and reference.get("path"):
        reference_image = Path(str(reference["path"]))
    digest = str(style.get("prompt_contract_sha256") or "").strip()
    if not digest:
        digest = sha256((contract + "\n" + terminal).encode("utf-8")).hexdigest().upper()
    return RuntimeStyleContract(
        contract=contract,
        terminal_lock=terminal,
        source=source,
        sha256=digest,
        reference_image=reference_image,
    )


def enforce_terminal_execution_lock(prompt: str, runtime: RuntimeStyleContract) -> str:
    """Append exactly one generic terminal lock at the absolute end."""

    body = str(prompt).rstrip()
    for marker in _LEGACY_TERMINAL_HEADINGS:
        pos = body.find(marker)
        if pos >= 0:
            body = body[:pos].rstrip()
    if not runtime.terminal_lock:
        return body + "\n"
    return f"{body}\n\n{TERMINAL_EXECUTION_HEADING}\n{runtime.terminal_lock.strip()}\n"


def internal_style_token_leaks(text: str) -> tuple[str, ...]:
    return tuple(match.group(0) for match in _INTERNAL_STYLE_TOKEN_RE.finditer(text))


__all__ = [
    "RuntimeStyleContract",
    "TERMINAL_EXECUTION_HEADING",
    "enforce_terminal_execution_lock",
    "internal_style_token_leaks",
    "load_runtime_style_contract",
]
