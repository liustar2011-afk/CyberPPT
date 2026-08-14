"""Prepare deterministic ImageGen send drafts (+ optional LLM briefs)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cyberppt.commands.script_gate import assert_approved_final_script, stage_script
from scripts.dual_image_overlay.prompt_send_enrich import (
    build_deterministic_enrich_block,
    llm_enrich_brief,
)


def _parse_pages(pages_raw: str) -> list[int]:
    pages: list[int] = []
    for part in pages_raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s), int(end_s)
            if end < start:
                raise ValueError(f"invalid page range: {part}")
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    if not pages:
        raise ValueError("no pages specified")
    return pages


def prepare_imagegen_send(
    *,
    project: Path,
    pages_raw: str,
    write_llm_brief: bool = True,
    stage_draft: bool = True,
    note: str = "",
) -> dict[str, Any]:
    """Build per-page deterministic send drafts from approved imagegen finals."""

    project = project.expanduser().resolve()
    pages = _parse_pages(pages_raw)
    send_dir = project / "workbench" / "prompts" / "imagegen" / "send"
    send_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []

    for page in pages:
        approved = assert_approved_final_script(project, page, "imagegen")
        source = approved.read_text(encoding="utf-8-sig")
        # The send reviewer edits an enrichment block only.  The final prompt
        # compiler owns the page semantics, STYLE09 contract and terminal lock;
        # this command must never append a second visual module to an approved
        # prompt and then pass that altered body downstream.
        enriched = build_deterministic_enrich_block(source)
        draft_path = send_dir / f"slide-{page:02d}-imagegen-send-draft.md"
        draft_path.write_text(enriched, encoding="utf-8")
        brief_path: Path | None = None
        if write_llm_brief:
            brief_path = send_dir / f"slide-{page:02d}-imagegen-send-llm-brief.md"
            brief_path.write_text(
                llm_enrich_brief(page_number=page, approved_prompt=source),
                encoding="utf-8",
            )
        staged: Path | None = None
        if stage_draft:
            staged = stage_script(
                project,
                page,
                "imagegen-send",
                "draft",
                draft_path,
                note=note or "deterministic send enrich draft",
            )
        items.append(
            {
                "page": page,
                "approved_imagegen": str(approved),
                "send_draft": str(draft_path),
                "llm_brief": str(brief_path) if brief_path else None,
                "staged_draft": str(staged) if staged else None,
            }
        )

    summary = {
        "schema": "cyberppt.imagegen_send_prepare.v1",
        "project": str(project),
        "pages": pages,
        "items": items,
        "next_steps": [
            "Optional: edit send draft using the llm-brief (keep locked Chinese verbatim).",
            "python -m cyberppt stage-script <project> --slide N --kind imagegen-send --phase final --source <send draft or edited file>",
            "python -m cyberppt approve-script <project> --slide N --kind imagegen-send",
            "python -m cyberppt final-script-pages ... --generate-images --prompt-enrich send",
        ],
    }
    summary_path = send_dir / "prepare-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary
