"""UTF-8 console helper for the vendored image-to-PPTX runtime."""

from __future__ import annotations

import sys


def configure_utf8_stdio() -> None:
    """Use UTF-8 when the host stream supports dynamic reconfiguration."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")
