"""Send-time ImageGen prompt enrichment (deterministic + LLM-send gate).

Layer 1 — deterministic (default, silent): append a compact visual cue block
derived from the approved page prompt's 【页面逻辑】. Never rewrites locked
on-screen Chinese. Applied automatically on final-script-pages / pair-manifest
unless --prompt-enrich off.

Layer 2 — LLM send script: optional approved `imagegen-send` final that an
agent/LLM may rewrite for image-model sensitivity. Must keep locked text;
generation prefers it when --prompt-enrich send.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SEND_ENRICH_HEADER = "【Send enrich｜不上屏】"
LOCKED_MARKERS = ("【锁定关键文字】", "【完整上屏内容】")

DETERMINISTIC_MATERIALS = (
    "Materials: low-relief paper / resin / frosted; soft contact shadows; "
    "ban exaggerated 3D, metal specular, glassmorphism, neon glow."
)
DETERMINISTIC_PEOPLE = "People: default absent unless semantics need distant small-scale support."
DETERMINISTIC_BAN = (
    "Ban: 50/50 text-vs-image splits (left-right or top-bottom), magazine cover+caption, "
    "background photo + foreground text block, equal card walls, step cards, timelines, "
    "hub-and-spoke, SaaS/dashboard/architecture looks, file cabinets, folders, kraft paper, "
    "DB cylinders, server racks, logos, seals, org names, page numbers, footers, evidence IDs "
    "in the body image."
)
DETERMINISTIC_COMPOSITION = (
    "Composition: one integrated layout; weave locked Chinese into the business structure; "
    "optional industry scene ≤ ~1/4 as local embed — never a half-page panel."
)
DETERMINISTIC_CHROME = (
    "Chrome ban: do not draw slide title, subtitle, page number, slide index "
    "(第N页 / Pxx / Slide N), logo, footer, or master chrome. Keep locked business "
    "module numbers (e.g. 01｜); invent no decorative serials."
)
DETERMINISTIC_FIDELITY = (
    "Fidelity: keep all locked on-screen Chinese text verbatim; do not invent facts, "
    "service names, or slogans."
)

_RELATION_EN = {
    "路径转化": "path transformation / through-going chain",
    "贯穿主链": "crosscutting chain along the main path",
    "闭环": "closed loop",
    "分层": "hierarchy / layered support",
    "对比": "contrast",
    "边界": "boundary / guardrail",
    "因果": "cause → effect",
    "并列": "peer modules with clear hierarchy",
    "汇聚": "convergence",
    "分支": "branching",
}


@dataclass(frozen=True)
class SendEnrichResult:
    prompt: str
    mode: str  # off | deterministic | send
    source_prompt_sha256: str
    structure_cue: str
    used_send_script: bool
    send_script_path: str | None
    enrich_block: str


def _sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest().lower()


def _section(prompt: str, header: str) -> str:
    pattern = re.compile(
        rf"{re.escape(header)}\s*\n(.*?)(?=\n【|\Z)",
        re.DOTALL,
    )
    match = pattern.search(prompt)
    return match.group(1).strip() if match else ""


def extract_structure_cue(prompt: str) -> str:
    """Build a short English structure cue from 【页面逻辑】 when present."""

    logic = _section(prompt, "【页面逻辑｜不上屏】") or _section(prompt, "【页面逻辑】")
    if not logic:
        # Fall back to semantic-relations header used in older drafts.
        logic = _section(prompt, "【页面语义关系｜仅供理解，不上屏】")
    if not logic:
        return "Structure: follow page logic and locked module hierarchy; content decides layout."

    lines = [line.strip(" -•\t") for line in logic.splitlines() if line.strip()]
    compact = "；".join(lines) if lines else logic
    # Prefer explicit 主导关系 / 结构形态 lines.
    dominant = ""
    morph = ""
    for line in lines:
        if line.startswith("主导关系"):
            dominant = line.split("：", 1)[-1].split(":", 1)[-1].strip(" 。.")
        elif line.startswith("结构形态"):
            morph = line.split("：", 1)[-1].split(":", 1)[-1].strip(" 。.")
    parts: list[str] = []
    if dominant:
        mapped = next((en for zh, en in _RELATION_EN.items() if zh in dominant), dominant)
        parts.append(f"dominant relation = {mapped}")
    if morph:
        mapped = morph
        for zh, en in _RELATION_EN.items():
            if zh in morph:
                mapped = f"{en}: {morph}"
                break
        parts.append(f"form = {mapped}")
    if not parts:
        # Translate a few known tokens inside free text.
        mapped = compact
        for zh, en in _RELATION_EN.items():
            if zh in compact:
                mapped = f"{en} — {compact}"
                break
        parts.append(mapped[:180])
    return "Structure: " + "; ".join(parts)


def strip_send_enrich_block(prompt: str) -> str:
    text = prompt.strip()
    if SEND_ENRICH_HEADER not in text:
        return text
    return text.split(SEND_ENRICH_HEADER, 1)[0].rstrip()


def build_deterministic_enrich_block(prompt: str) -> str:
    structure = extract_structure_cue(prompt)
    return "\n".join(
        [
            SEND_ENRICH_HEADER,
            structure,
            DETERMINISTIC_COMPOSITION,
            DETERMINISTIC_MATERIALS,
            DETERMINISTIC_PEOPLE,
            DETERMINISTIC_BAN,
            DETERMINISTIC_CHROME,
            DETERMINISTIC_FIDELITY,
        ]
    )


def apply_deterministic_enrich(prompt: str) -> str:
    base = strip_send_enrich_block(prompt)
    block = build_deterministic_enrich_block(base)
    return f"{base.rstrip()}\n\n{block}\n"


def assert_locked_text_preserved(source: str, enriched: str) -> None:
    """Require locked on-screen blocks from source to appear in enriched text."""

    for marker in LOCKED_MARKERS:
        src_section = _section(source, marker)
        if not src_section:
            continue
        # Compare normalized whitespace so minor formatting drift is allowed.
        src_norm = re.sub(r"\s+", "", src_section)
        dst_norm = re.sub(r"\s+", "", enriched)
        if src_norm and src_norm not in dst_norm:
            raise ValueError(
                f"LLM/send enrich dropped locked section {marker}; "
                "on-screen Chinese must remain verbatim."
            )


def llm_enrich_brief(*, page_number: int, approved_prompt: str) -> str:
    """Instruction brief for an agent/LLM that rewrites the send prompt."""

    return f"""# ImageGen send enrich brief — P{page_number:02d}

You will rewrite the approved ImageGen script into a **send prompt** optimized for image models.

## Hard rules
1. Keep 【锁定关键文字】 and 【完整上屏内容】 Chinese text **verbatim** (same characters).
2. Do not invent facts, numbers, service names, slogans, logos, or page chrome.
3. You MAY: compress/English-ize style cues; add structure/material/people/ban cues image models hear; clarify path vs crosscut relations from 【页面逻辑】.
4. You MUST NOT: replace STYLE09 with another palette; force a fixed card/timeline/hub template unless the page logic requires it.
5. Output only the full send prompt body (no markdown commentary).

## Suggested adds (if missing)
- Structure cue from page logic (path / crosscut / loop / hierarchy)
- Materials: low-relief paper/resin/frosted; soft contact shadows
- People: default absent
- Short ban list for card walls / SaaS UI / file cabinets / neon

## Approved source
```
{approved_prompt.rstrip()}
```
"""


def resolve_send_prompt(
    *,
    approved_prompt: str,
    mode: str,
    send_final_path: Path | None = None,
    require_send: bool = False,
) -> SendEnrichResult:
    """Resolve the prompt actually sent to the image backend.

    mode:
      - off: approved/canonical prompt unchanged
      - deterministic: append deterministic enrich block
      - send: use approved imagegen-send final when available; else deterministic
        (or error if require_send)
    """

    mode = (mode or "off").strip().lower()
    if mode not in {"off", "deterministic", "send"}:
        raise ValueError(f"unsupported prompt enrich mode: {mode}")

    source = approved_prompt.strip()
    source_hash = _sha256_text(source)

    if mode == "off":
        return SendEnrichResult(
            prompt=source,
            mode=mode,
            source_prompt_sha256=source_hash,
            structure_cue="",
            used_send_script=False,
            send_script_path=None,
            enrich_block="",
        )

    if mode == "send" and send_final_path is not None and send_final_path.is_file():
        send_text = send_final_path.read_text(encoding="utf-8-sig").strip()
        assert_locked_text_preserved(source, send_text)
        return SendEnrichResult(
            prompt=send_text,
            mode=mode,
            source_prompt_sha256=source_hash,
            structure_cue=extract_structure_cue(source),
            used_send_script=True,
            send_script_path=str(send_final_path),
            enrich_block="",
        )

    if mode == "send" and require_send:
        raise FileNotFoundError(
            "prompt enrich mode=send requires an approved imagegen-send final script; "
            "run `python -m cyberppt prepare-imagegen-send` then stage/approve kind=imagegen-send"
        )

    enriched = apply_deterministic_enrich(source)
    block = build_deterministic_enrich_block(source)
    return SendEnrichResult(
        prompt=enriched,
        mode="deterministic" if mode == "deterministic" else "deterministic",
        source_prompt_sha256=source_hash,
        structure_cue=extract_structure_cue(source),
        used_send_script=False,
        send_script_path=None,
        enrich_block=block,
    )


def enrich_result_as_dict(result: SendEnrichResult) -> dict[str, Any]:
    return {
        "mode": result.mode,
        "source_prompt_sha256": result.source_prompt_sha256,
        "structure_cue": result.structure_cue,
        "used_send_script": result.used_send_script,
        "send_script_path": result.send_script_path,
        "enrich_block": result.enrich_block,
        "prompt_chars": len(result.prompt),
    }
