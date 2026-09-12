from __future__ import annotations

import sys

from .cli import main as advanced_main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "build":
        from .commands.build_cli import main as build_main

        return build_main(args[1:])
    return advanced_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
