#!/usr/bin/env python3
"""
Verify Cairo / CairoSVG availability for preview, similarity checks, and PNG fallback.

Usage:
    python3 scripts/check_cairo_backend.py
    python3 scripts/check_cairo_backend.py --render <project_path>

macOS (Homebrew): if import fails with "no library called cairo", install libcairo and
expose it to the venv:
    brew install cairo pango gdk-pixbuf libffi
    export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def _brew_prefix() -> str | None:
    brew = shutil.which("brew")
    if not brew:
        return None
    try:
        out = subprocess.check_output([brew, "--prefix"], text=True, timeout=10).strip()
        return out or None
    except (subprocess.SubprocessError, OSError):
        return None


def _ensure_macos_dyld() -> list[str]:
    hints: list[str] = []
    if platform.system() != "Darwin":
        return hints
    prefix = _brew_prefix()
    if not prefix:
        hints.append("Install Homebrew cairo: brew install cairo pango gdk-pixbuf libffi")
        return hints
    lib_dir = f"{prefix}/lib"
    if not Path(lib_dir, "libcairo.2.dylib").exists() and not Path(lib_dir, "libcairo.dylib").exists():
        hints.append(f"Run: brew install cairo  (expected libs under {lib_dir})")
        return hints
    current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if lib_dir not in current.split(":"):
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
            f"{lib_dir}:{current}" if current else lib_dir
        )
        hints.append(
            "Set for Cursor shells / .venv: "
            f'export DYLD_FALLBACK_LIBRARY_PATH="{lib_dir}:$DYLD_FALLBACK_LIBRARY_PATH"'
        )
    return hints


def check_import() -> dict:
    result: dict = {
        "python": sys.executable,
        "platform": platform.platform(),
        "cairosvg": None,
        "cairo_native": None,
        "png_renderer": None,
        "errors": [],
        "warnings": [],
        "hints": [],
    }
    result["hints"].extend(_ensure_macos_dyld())

    try:
        import cairosvg  # noqa: F401

        import cairosvg as mod

        result["cairosvg"] = getattr(mod, "__version__", "unknown")
    except Exception as exc:  # pragma: no cover - diagnostic
        result["errors"].append(f"cairosvg import failed: {exc}")
        return result

    try:
        import cairocffi

        result["cairo_native"] = cairocffi.cairo_version()
    except Exception as exc:
        result["errors"].append(f"libcairo link failed: {exc}")
        return result

    try:
        scripts_dir = Path(__file__).resolve().parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from svg_to_pptx.pptx_media import get_png_renderer_info

        name, status, hint = get_png_renderer_info()
        result["png_renderer"] = {"name": name, "status": status, "hint": hint}
        if hint:
            result["warnings"].append(hint)
    except Exception as exc:
        result["warnings"].append(f"pptx_media probe skipped: {exc}")

    try:
        import cairosvg

        probe = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="40">'
            '<text x="10" y="28" font-family="Microsoft YaHei, PingFang SC, sans-serif" '
            'font-size="18" fill="#003088">Cairo</text></svg>'
        )
        png = cairosvg.svg2png(bytestring=probe.encode())
        if not png or len(png) < 100:
            result["warnings"].append("Cairo render probe returned empty PNG")
        else:
            result["render_probe_bytes"] = len(png)
    except Exception as exc:
        result["errors"].append(f"Cairo render probe failed: {exc}")

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Cairo/CairoSVG backend for PPT Master.")
    parser.add_argument("--render", type=Path, help="Optional project path to run verify_svg_preview --render")
    args = parser.parse_args(argv)

    payload = check_import()
    payload["valid"] = not payload["errors"]

    if args.render and payload["valid"]:
        project = args.render.resolve()
        script = Path(__file__).resolve().parent / "verify_svg_preview.py"
        proc = subprocess.run(
            [sys.executable, str(script), str(project), "--render"],
            capture_output=True,
            text=True,
        )
        payload["verify_svg_preview_exit"] = proc.returncode
        if proc.returncode != 0:
            payload["errors"].append(proc.stderr.strip() or proc.stdout.strip() or "verify_svg_preview failed")
            payload["valid"] = False

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
