"""Bridge to the registered vendored PPT image enhancer skill."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from cyberppt.paths import REPO_ROOT


SKILL_ROOT = REPO_ROOT / "vendor" / "ppt-image-enhancer-skill-v1.0.0"
SKILL_FILE = SKILL_ROOT / "SKILL.md"
ENTRYPOINT = SKILL_ROOT / "enhance.py"
REGISTRY_FILE = REPO_ROOT / "vendor" / "skills.json"


def assert_registered() -> None:
    if not SKILL_FILE.is_file() or not ENTRYPOINT.is_file():
        raise FileNotFoundError(
            f"registered ppt-image-enhancer skill is incomplete: {SKILL_ROOT}"
        )
    if not REGISTRY_FILE.is_file():
        raise FileNotFoundError(f"vendor skill registry is missing: {REGISTRY_FILE}")
    registry = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    skills = registry.get("skills") if isinstance(registry, dict) else None
    entry = next(
        (item for item in (skills or []) if item.get("name") == "ppt-image-enhancer"),
        None,
    )
    if not entry or (REPO_ROOT / str(entry.get("path", ""))).resolve() != SKILL_ROOT.resolve():
        raise ValueError("ppt-image-enhancer is not correctly registered in vendor/skills.json")


def _runtime_python() -> Path:
    candidate = SKILL_ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    return candidate if candidate.is_file() else Path(sys.executable)


def _needs_ascii_staging(*paths: Path) -> bool:
    return sys.platform == "win32" and any(
        not str(path).isascii() for path in paths
    )


def enhance_image(
    source: Path,
    *,
    output: Path | None = None,
    backend: str = "auto",
    scale: float = 1.0,
    target_size: tuple[int, int] | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Run the registered skill and return its machine-readable report."""
    assert_registered()
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"image to enhance not found: {source}")
    output = (output or source.with_name(f"{source.stem}_enhanced.png")).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = output.with_suffix(output.suffix + ".report.json")

    def pillow_fallback(run_source: Path, run_output: Path, run_report: Path) -> list[str]:
        """Keep ingest normalization available when the optional cv2 skill dependency is absent."""
        with Image.open(run_source) as image:
            destination = target_size or image.size
            normalized = image.convert("RGB").resize(destination, Image.Resampling.LANCZOS)
            normalized.save(run_output)
        run_report.write_text(
            json.dumps(
                {
                    "super_resolution_backend": "pillow_resize_fallback",
                    "warnings": [
                        "ppt-image-enhancer cv2 dependency unavailable; used deterministic Pillow resize"
                    ],
                    "target_size": list(destination),
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        return ["pillow_resize_fallback", str(run_source), str(run_output)]

    def run_skill(run_source: Path, run_output: Path, run_report: Path) -> list[str]:
        command = [
            str(_runtime_python()), str(ENTRYPOINT), str(run_source),
            "--output", str(run_output), "--report", str(run_report),
            "--backend", backend, "--scale", str(scale),
        ]
        if target_size is not None:
            command.extend(["--target-size", f"{target_size[0]}x{target_size[1]}"])
        if mode is not None:
            command.extend(["--mode", mode])
        completed = subprocess.run(command, cwd=SKILL_ROOT, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            if "No module named 'cv2'" in (completed.stderr or ""):
                return pillow_fallback(run_source, run_output, run_report)
            raise RuntimeError(
                "ppt-image-enhancer failed with exit code "
                f"{completed.returncode}: {' '.join(command)}"
            )
        return command

    if _needs_ascii_staging(source, output, report):
        with tempfile.TemporaryDirectory(prefix="cyberppt-enhance-") as temp_dir:
            stage = Path(temp_dir)
            staged_source = stage / f"input{source.suffix or '.png'}"
            staged_output = stage / f"output{output.suffix or '.png'}"
            staged_report = stage / "output.report.json"
            shutil.copy2(source, staged_source)
            command = run_skill(staged_source, staged_output, staged_report)
            if not staged_output.is_file() or not staged_report.is_file():
                raise RuntimeError(
                    "ppt-image-enhancer completed without its declared output/report"
                )
            shutil.copy2(staged_output, output)
            shutil.copy2(staged_report, report)
    else:
        command = run_skill(source, output, report)
    if not output.is_file() or not report.is_file():
        raise RuntimeError("ppt-image-enhancer completed without its declared output/report")
    payload = json.loads(report.read_text(encoding="utf-8"))
    return {
        "source": str(source), "output": str(output), "report": str(report),
        "backend": payload.get("super_resolution_backend"),
        "warnings": payload.get("warnings", []), "command": command,
    }


def enhance_manifest_images(
    manifest: dict[str, Any], *, backend: str = "auto", scale: float = 1.0
) -> dict[str, Any]:
    """Enhance generated manifest images and promote outputs as manifest authority."""
    rows: list[dict[str, Any]] = []
    for pair in manifest.get("pairs", []):
        for variant in ("full", "background"):
            item = pair.get(variant)
            if not isinstance(item, dict) or str(item.get("status", "")).lower() != "generated":
                continue
            source = Path(str(item.get("path", "")))
            if not source.is_file():
                raise FileNotFoundError(
                    f"page {pair.get('page_number')} generated {variant} image is missing: {source}"
                )
            output = source.parent / "enhanced" / f"{source.stem}_enhanced.png"
            result = enhance_image(source, output=output, backend=backend, scale=scale)
            item["enhancement"] = {
                "skill": "ppt-image-enhancer", "source_path": str(source),
                "report": result["report"], "backend": result["backend"],
                "scale": scale, "warnings": result["warnings"],
            }
            item["path"] = result["output"]
            item["filename"] = output.name
            rows.append({"page_number": pair.get("page_number"), "variant": variant, **result})
    if not rows:
        raise ValueError("no Generated full/background images are available for enhancement")
    return {
        "schema": "cyberppt.image_enhancement_run.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "skill": "ppt-image-enhancer", "backend": backend, "scale": scale,
        "images": rows,
    }
