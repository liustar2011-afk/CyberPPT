#!/usr/bin/env python3
"""
PPT Master - SVG Preview Render Backend (Cairo)

Unified SVG → PNG rendering for verify_reference_similarity and verify_svg_preview.

Usage:
    python3 scripts/render_preview_backend.py probe --json
    python3 scripts/render_preview_backend.py render <project> --svg svg_output/01.svg

Dependencies:
    cairosvg + libcairo
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from prepare_svg_for_render import PrepareResult, default_render_ready_path, prepare_svg_for_render
except ImportError:  # pragma: no cover
    from scripts.prepare_svg_for_render import (  # type: ignore
        PrepareResult,
        default_render_ready_path,
        prepare_svg_for_render,
    )

BACKEND_CODE_VERSION = "0.1.0"
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
VALID_BACKENDS = frozenset({"auto", "cairo", "none"})
CJK_RE = __import__("re").compile(r"[㐀-鿿]")


class RenderBackendError(Exception):
    def __init__(self, code: str, message: str, *, hints: list[str] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hints = hints or []


@dataclass(frozen=True)
class RenderRequest:
    project: Path
    svg_path: Path
    out_path: Path
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    backend: str = "cairo"
    server_url: str | None = None
    force: bool = False
    hard_gate: bool = False


@dataclass(frozen=True)
class RenderResult:
    ok: bool
    backend: str
    out_path: Path
    meta_path: Path
    render_input_path: Path | None
    render_input_hash: str | None
    icon_manifest_hash: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    duration_ms: int
    skipped: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "backend": self.backend,
            "out_path": str(self.out_path),
            "meta_path": str(self.meta_path),
            "render_input_path": str(self.render_input_path) if self.render_input_path else None,
            "render_input_hash": self.render_input_hash,
            "icon_manifest_hash": self.icon_manifest_hash,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "duration_ms": self.duration_ms,
            "skipped": self.skipped,
        }


def meta_path_for(preview_png: Path) -> Path:
    return preview_png.with_suffix(".meta.json")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def cairo_available() -> bool:
    try:
        import cairosvg  # noqa: F401
    except (ImportError, OSError):
        return False
    return True


def _svg_has_cjk(svg_path: Path) -> bool:
    try:
        text = svg_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(CJK_RE.search(text))


def resolve_render_backend(
    requested: str,
    *,
    project: Path,
    svg_path: Path,
    hard_gate: bool = False,
) -> str:
    backend = requested.strip().lower() or "cairo"
    if backend not in VALID_BACKENDS:
        raise RenderBackendError(
            "invalid_render_backend",
            f"Unknown render backend `{requested}`; expected one of: {', '.join(sorted(VALID_BACKENDS))}",
        )
    if hard_gate and backend == "auto":
        raise RenderBackendError(
            "hard_gate_requires_explicit_backend",
            "CI and pre-export gates must use cairo or none, not auto.",
        )
    if backend != "auto":
        return backend

    env = os.environ.get("PPT_MASTER_RENDER_BACKEND", "").strip().lower()
    if env in VALID_BACKENDS - {"auto"}:
        return env

    if cairo_available():
        return "cairo"
    raise RenderBackendError(
        "no_backend_available",
        "No preview render backend available (install cairosvg).",
        hints=[
            "macOS: brew install cairo",
            "Linux: apt-get install libcairo2 && pip install cairosvg",
        ],
    )


def _needs_rerender(
    *,
    preview_png: Path,
    meta_path: Path,
    prepare: PrepareResult,
    backend: str,
    force: bool,
) -> bool:
    if force or not preview_png.is_file():
        return True
    if backend == "none":
        return preview_png.stat().st_mtime < prepare.svg_path.stat().st_mtime
    meta = _load_json(meta_path)
    if not meta:
        return True
    if meta.get("backend") != backend:
        return True
    if meta.get("backend_code_version") != BACKEND_CODE_VERSION:
        return True
    if meta.get("svg_sha256") and meta.get("svg_sha256") != prepare.svg_sha256:
        return True
    if meta.get("render_input_hash") and meta.get("render_input_hash") != prepare.render_input_hash:
        return True
    imh = prepare.icon_manifest_hash
    if imh and meta.get("icon_manifest_hash") not in {None, imh}:
        return True
    if preview_png.stat().st_mtime < prepare.svg_path.stat().st_mtime:
        return True
    return False


def _write_meta(
    meta_path: Path,
    *,
    backend: str,
    prepare: PrepareResult,
    preview_png: Path,
    width: int,
    height: int,
    duration_ms: int,
    warnings: list[str],
) -> None:
    payload = {
        "version": "1.0",
        "backend": backend,
        "backend_version": "cairosvg",
        "backend_code_version": BACKEND_CODE_VERSION,
        "svg": str(prepare.svg_path),
        "svg_sha256": prepare.svg_sha256,
        "render_input_path": str(prepare.render_ready_path),
        "render_input_hash": prepare.render_input_hash,
        "icon_manifest_hash": prepare.icon_manifest_hash,
        "svg_mtime": prepare.svg_path.stat().st_mtime,
        "preview": str(preview_png),
        "preview_mtime": preview_png.stat().st_mtime if preview_png.is_file() else 0,
        "width": width,
        "height": height,
        "duration_ms": duration_ms,
        "warnings": warnings,
    }
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = meta_path.with_suffix(".meta.json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(meta_path)


def _render_cairo(render_ready: Path, out_path: Path, width: int, height: int) -> None:
    import cairosvg

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(
        url=str(render_ready),
        write_to=str(out_path),
        output_width=width,
        output_height=height,
        # cairosvg defaults to unsafe=False, which silently drops any local
        # <image href="..."> raster reference (decorative crops, footer line
        # art, text-editable-snapshot backgrounds) -- the image renders fully
        # transparent with no error. We only ever render SVGs this pipeline
        # generated itself, so local file access is an acceptable trust
        # boundary here.
        unsafe=True,
    )


def _is_all_background(png_path: Path) -> bool:
    try:
        from PIL import Image
    except ImportError:
        return False
    image = Image.open(png_path).convert("RGB")
    pixels = list(image.getdata())
    if not pixels:
        return True
    counts: dict[tuple[int, int, int], int] = {}
    for pixel in pixels:
        key = (pixel[0] >> 4, pixel[1] >> 4, pixel[2] >> 4)
        counts[key] = counts.get(key, 0) + 1
    return max(counts.values()) / len(pixels) >= 0.99


def render_preview(req: RenderRequest) -> RenderResult:
    started = time.monotonic()
    warnings: list[str] = []
    backend = resolve_render_backend(
        req.backend,
        project=req.project,
        svg_path=req.svg_path,
        hard_gate=req.hard_gate,
    )
    meta = meta_path_for(req.out_path)

    if backend == "none":
        errors: list[str] = []
        if not req.out_path.is_file():
            errors.append(f"Preview PNG missing: {req.out_path}")
        elif _needs_rerender(
            preview_png=req.out_path,
            meta_path=meta,
            prepare=prepare_svg_for_render(req.project, req.svg_path, write=False),
            backend=backend,
            force=req.force,
        ):
            errors.append(f"Preview PNG stale: {req.out_path}; re-render with --render-backend cairo.")
        duration = int((time.monotonic() - started) * 1000)
        return RenderResult(
            ok=not errors,
            backend=backend,
            out_path=req.out_path,
            meta_path=meta,
            render_input_path=None,
            render_input_hash=None,
            icon_manifest_hash=None,
            errors=tuple(errors),
            warnings=tuple(warnings),
            duration_ms=duration,
            skipped=True,
        )

    prepare = prepare_svg_for_render(req.project, req.svg_path)
    if not prepare.ok:
        duration = int((time.monotonic() - started) * 1000)
        return RenderResult(
            ok=False,
            backend=backend,
            out_path=req.out_path,
            meta_path=meta,
            render_input_path=None,
            render_input_hash=None,
            icon_manifest_hash=None,
            errors=prepare.errors,
            warnings=tuple(str(item) for item in prepare.warnings),
            duration_ms=duration,
        )
    warnings.extend(f"icon:{item.get('icon','')}: {item.get('reason','')}" for item in prepare.warnings)

    if not _needs_rerender(
        preview_png=req.out_path,
        meta_path=meta,
        prepare=prepare,
        backend=backend,
        force=req.force,
    ):
        duration = int((time.monotonic() - started) * 1000)
        return RenderResult(
            ok=True,
            backend=backend,
            out_path=req.out_path,
            meta_path=meta,
            render_input_path=prepare.render_ready_path,
            render_input_hash=prepare.render_input_hash,
            icon_manifest_hash=prepare.icon_manifest_hash,
            errors=(),
            warnings=tuple(warnings),
            duration_ms=duration,
            skipped=True,
        )

    errors_list: list[str] = []
    try:
        if not cairo_available():
            raise RenderBackendError(
                "render_backend_cairo_unavailable",
                "cairosvg/libcairo is not available.",
                hints=[
                    "macOS: brew install cairo",
                    "Linux: apt-get install libcairo2 && pip install cairosvg",
                ],
            )
        _render_cairo(prepare.render_ready_path, req.out_path, req.width, req.height)
    except RenderBackendError as exc:
        duration = int((time.monotonic() - started) * 1000)
        return RenderResult(
            ok=False,
            backend=backend,
            out_path=req.out_path,
            meta_path=meta,
            render_input_path=prepare.render_ready_path,
            render_input_hash=prepare.render_input_hash,
            icon_manifest_hash=prepare.icon_manifest_hash,
            errors=(exc.message,),
            warnings=tuple(warnings),
            duration_ms=duration,
        )

    if errors_list:
        duration = int((time.monotonic() - started) * 1000)
        return RenderResult(
            ok=False,
            backend=backend,
            out_path=req.out_path,
            meta_path=meta,
            render_input_path=prepare.render_ready_path,
            render_input_hash=prepare.render_input_hash,
            icon_manifest_hash=prepare.icon_manifest_hash,
            errors=tuple(errors_list),
            warnings=tuple(warnings),
            duration_ms=duration,
        )

    if _is_all_background(req.out_path):
        if _svg_has_cjk(req.svg_path):
            warnings.append(
                "cairo_cjk_preview_blank_or_uniform — ensure CJK fonts are installed "
                "(macOS: system fonts; Linux: apt install fonts-noto-cjk)"
            )
        else:
            duration = int((time.monotonic() - started) * 1000)
            return RenderResult(
                ok=False,
                backend=backend,
                out_path=req.out_path,
                meta_path=meta,
                render_input_path=prepare.render_ready_path,
                render_input_hash=prepare.render_input_hash,
                icon_manifest_hash=prepare.icon_manifest_hash,
                errors=("Rendered preview appears blank.",),
                warnings=tuple(warnings),
                duration_ms=duration,
            )

    duration = int((time.monotonic() - started) * 1000)
    _write_meta(
        meta,
        backend=backend,
        prepare=prepare,
        preview_png=req.out_path,
        width=req.width,
        height=req.height,
        duration_ms=duration,
        warnings=warnings,
    )
    return RenderResult(
        ok=True,
        backend=backend,
        out_path=req.out_path,
        meta_path=meta,
        render_input_path=prepare.render_ready_path,
        render_input_hash=prepare.render_input_hash,
        icon_manifest_hash=prepare.icon_manifest_hash,
        errors=(),
        warnings=tuple(warnings),
        duration_ms=duration,
    )


def probe_backends() -> dict[str, Any]:
    return {
        "backend_code_version": BACKEND_CODE_VERSION,
        "cairo": {"available": cairo_available()},
        "valid_backends": sorted(VALID_BACKENDS),
    }


def ensure_preview_for_svg(
    project: Path,
    svg: Path,
    preview: Path,
    *,
    render: bool,
    render_backend: str = "cairo",
    hard_gate: bool = False,
    force_render: bool = False,
    server_url: str | None = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> RenderResult:
    if not render and render_backend == "none":
        render = True
    if not render:
        if not preview.is_file():
            return RenderResult(
                ok=False,
                backend=render_backend,
                out_path=preview,
                meta_path=meta_path_for(preview),
                render_input_path=None,
                render_input_hash=None,
                icon_manifest_hash=None,
                errors=(
                    f"Preview PNG missing: {preview}. Run with --render or --render --render-backend none.",
                ),
                warnings=(),
                duration_ms=0,
                skipped=True,
            )
        stale = preview.stat().st_mtime < svg.stat().st_mtime
        if stale:
            return RenderResult(
                ok=False,
                backend=render_backend,
                out_path=preview,
                meta_path=meta_path_for(preview),
                render_input_path=None,
                render_input_hash=None,
                icon_manifest_hash=None,
                errors=(
                    f"Preview PNG is older than {svg.name}; re-run with --render to refresh {preview.name}.",
                ),
                warnings=(),
                duration_ms=0,
                skipped=True,
            )
        return RenderResult(
            ok=True,
            backend=render_backend,
            out_path=preview,
            meta_path=meta_path_for(preview),
            render_input_path=None,
            render_input_hash=None,
            icon_manifest_hash=None,
            errors=(),
            warnings=(),
            duration_ms=0,
            skipped=True,
        )

    return render_preview(
        RenderRequest(
            project=project,
            svg_path=svg,
            out_path=preview,
            width=width,
            height=height,
            backend=render_backend,
            force=force_render,
            hard_gate=hard_gate,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SVG preview render backend (Cairo).")
    sub = parser.add_subparsers(dest="command")

    probe = sub.add_parser("probe", help="Probe backend availability")
    probe.add_argument("--json", action="store_true")

    render = sub.add_parser("render", help="Render one SVG to preview PNG")
    render.add_argument("project_path", type=Path)
    render.add_argument("--svg", type=Path, required=True)
    render.add_argument("--out", type=Path)
    render.add_argument("--render-backend", default="cairo", choices=["cairo", "none", "auto"])
    render.add_argument("--force-render", action="store_true")
    render.add_argument("--hard-gate", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "probe":
        payload = probe_backends()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.command == "render":
        project = args.project_path.resolve()
        svg = args.svg if args.svg.is_absolute() else project / args.svg
        out = args.out or project / "exports" / "preview_qa" / f"{svg.stem}.preview.png"
        if not out.is_absolute():
            out = project / out
        result = render_preview(
            RenderRequest(
                project=project,
                svg_path=svg,
                out_path=out,
                backend=args.render_backend,
                force=args.force_render,
                hard_gate=args.hard_gate,
            )
        )
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        return 0 if result.ok else 1
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
