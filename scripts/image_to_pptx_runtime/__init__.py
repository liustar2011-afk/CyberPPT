"""CyberPPT-owned Image-to-PPTX Quick reconstruction runtime.

This package is a namespaced import of the PPT-Master reconstruction toolchain.
It deliberately has no runtime dependency on an external PPT-Master checkout.
"""

from __future__ import annotations

from pathlib import Path


def runtime_root() -> Path:
    return Path(__file__).resolve().parent


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
