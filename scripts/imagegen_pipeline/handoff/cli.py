"""Build reviewable ImageGen handoff prompts from approved final scripts.

Before any ImageGen call, CyberPPT must:
1. preserve the approved page meaning and drawable layer;
2. compile plaintext prompts with a tone-only visual contract;
3. save them under workbench/prompts/imagegen/;
4. wait for user modify-or-approve.

Page mission, core meaning, and source-supported content relations are passed before 上屏文字
so the model can understand the page responsibility without inventing an argument.
They are context fields, not extra labels to render; the drawable text layer remains 上屏文字.
The default content-first compiler projects the locked final script and selected Style 09
lock directly into the ImageGen handoff. The artifact-spec-v2 compiler remains explicitly
available for legacy compatibility and migration callers.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.imagegen_pipeline.prompt_compiler import (
    DEFAULT_PROMPT_COMPILER,
    PROMPT_COMPILERS,
    TEXT_RENDER_MODES,
)
from scripts.imagegen_pipeline.handoff.delivery import write_chapter_handoff


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--style-lock", type=Path, required=True)
    parser.add_argument("--pages", required=True, help="e.g. 1-7")
    parser.add_argument("--batch-name", default="chapter01")
    parser.add_argument(
        "--prompt-compiler",
        choices=PROMPT_COMPILERS,
        default=DEFAULT_PROMPT_COMPILER,
    )
    parser.add_argument(
        "--compare-with",
        choices=PROMPT_COMPILERS,
    )
    parser.add_argument(
        "--visual-structure-mode",
        choices=("off", "review"),
        default="off",
        help="Opt-in semantic composition guidance; review never bypasses approval.",
    )
    parser.add_argument(
        "--text-render-mode",
        choices=TEXT_RENDER_MODES,
        default=None,
        help="Override style default: full_image or semantic_visual.",
    )
    args = parser.parse_args(argv)

    raw = args.pages.strip()
    if "-" in raw and "," not in raw:
        start, end = raw.split("-", 1)
        pages = list(range(int(start), int(end) + 1))
    else:
        pages = [int(part) for part in raw.split(",") if part.strip()]

    outputs = write_chapter_handoff(
        project=args.project.resolve(),
        script=args.script.resolve(),
        style_lock=args.style_lock.resolve(),
        pages=pages,
        batch_name=args.batch_name,
        prompt_compiler=args.prompt_compiler,
        compare_with=args.compare_with,
        visual_structure_mode=args.visual_structure_mode,
        text_render_mode=args.text_render_mode,
    )
    print(f"batch_review={outputs['batch']}")
    print(f"diagnostics={outputs['diagnostics']}")
    if "comparison" in outputs:
        print(f"comparison={outputs['comparison']}")
    print(f"gate={outputs['gate']}")
    for key, path in sorted(outputs.items()):
        if key.startswith("p"):
            print(f"{key}={path}")
    return 0


__all__ = ("main",)
