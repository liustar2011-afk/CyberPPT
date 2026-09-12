from __future__ import annotations

import sys

from .cli import main as advanced_main


def _print_root_help() -> None:
    print(
        "CyberPPT\n\n"
        "Primary command:\n"
        "  cyberppt build SCRIPT [--mode image|editable|both] [--pages RANGE]\n\n"
        "Examples:\n"
        "  cyberppt build ./script.md\n"
        "  cyberppt build ./script.md --mode editable\n"
        "  cyberppt build ./script.md --mode both --pages 3-6\n\n"
        "Run 'cyberppt build --help' for build options.\n"
        "Run 'cyberppt --advanced-help' for development and compatibility commands."
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        _print_root_help()
        return 0
    if args[0] == "--advanced-help":
        return advanced_main(["--help"])
    if args[0] == "build":
        from .commands.build_cli import main as build_main

        return build_main(args[1:])
    return advanced_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
