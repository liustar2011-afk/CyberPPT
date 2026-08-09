"""Bridge to the registered vendored PPT image enhancer skill."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    command = [
        str(_runtime_python()), str(ENTRYPOINT), str(source), "--output", str(output),
        "--report", str(report), "--backend", backend, "--scale", str(scale),
    ]
    if target_size is not None:
        command.extend(["--target-size", f"{target_size[0]}x{target_size[1]}"])
    if mode is not None:
        command.extend(["--mode", mode])
    completed = subprocess.run(command, cwd=SKILL_ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"ppt-image-enhancer failed with exit code {completed.returncode}: {' '.join(command)}"
        )
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
