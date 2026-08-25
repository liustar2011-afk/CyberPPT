"""Public CLI boundary for the standalone CyberPPT Stage 02 product.

The first standalone release intentionally keeps the mature ``cyberppt``
internal package namespace so the existing ImageGen / Quick / QA production
chain can move without a risky import rewrite.  This module is the public
boundary: Stage 01 authoring, source analysis and outline commands are not
exposed by the standalone product.
"""
from __future__ import annotations

import sys


STAGE02_COMMANDS = frozenset(
    {
        "doctor",
        "officecli",
        "enhance-image",
        "prepare-stage02-handoff",
        "stage02-handoff-check",
        "prepare-visual-structure",
        "execute-visual-structure",
        "record-visual-structure-execution",
        "visual-structure-audit",
        "stage-script",
        "approve-script",
        "script-status",
        "prepare-imagegen-send",
        "final-script-pages",
        "review-quick-page",
    }
)


def _usage() -> str:
    commands = "\n".join(f"  {name}" for name in sorted(STAGE02_COMMANDS))
    return (
        "CyberPPT-Stage02 — semantic script to visual/editable PPTX production\n\n"
        "Usage: cyberppt-stage02 <command> [args]\n\n"
        "Stage 02 commands:\n"
        f"{commands}\n"
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        print(_usage())
        return 0
    command = args[0]
    if command not in STAGE02_COMMANDS:
        print(
            f"CyberPPT-Stage02 does not expose command {command!r}. "
            "Use CyberPPT-Script for source/authoring work and CyberPPT-Stage02 "
            "for visual production.",
            file=sys.stderr,
        )
        return 2
    from cyberppt.cli import main as compatibility_main

    return int(compatibility_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
