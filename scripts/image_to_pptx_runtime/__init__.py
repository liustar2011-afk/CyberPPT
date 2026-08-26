"""CyberPPT-owned Image-to-PPTX Quick reconstruction runtime.

This package is a namespaced import of the PPT-Master reconstruction toolchain.
It deliberately has no runtime dependency on an external PPT-Master checkout.
"""

from __future__ import annotations

import sys
from pathlib import Path


# The vendored files below this package are kept byte-identical to ppt-master.
# Upstream executes them with its scripts directory on sys.path and therefore
# uses top-level imports such as ``pptx_shapes`` and ``svg_to_pptx``.  Expose
# this internal directory in the same way, while keeping the external checkout
# completely out of the runtime dependency graph.
_RUNTIME_ROOT = Path(__file__).resolve().parent
if str(_RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(_RUNTIME_ROOT))


def runtime_root() -> Path:
    return _RUNTIME_ROOT


def assert_internal_runtime() -> None:
    """Fail if copied Python sources retain an external checkout dependency."""
    forbidden = "/Volumes/DOC/ppt-master"
    offenders = [
        source for source in runtime_root().rglob("*.py")
        if source.name != "__init__.py" and forbidden in source.read_text(encoding="utf-8")
    ]
    if offenders:
        names = ", ".join(str(source.relative_to(runtime_root())) for source in offenders)
        raise RuntimeError(f"external PPT-Master dependency: {names}")


__all__ = ["assert_internal_runtime", "runtime_root"]
