from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple
import importlib.util
import os
import platform
import shutil

from .config import PROJECT_ROOT, deep_merge, load_config, load_yaml
from .inspect import inspect_image


def _module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _find_ncnn_executable() -> Path | None:
    env = os.environ.get("PPT_IMAGE_ENHANCER_NCNN", "").strip()
    candidates = []
    if env:
        candidates.append(Path(env))
    runtime = PROJECT_ROOT / "runtime" / "realesrgan-ncnn-vulkan"
    names = ["realesrgan-ncnn-vulkan.exe", "realesrgan-ncnn-vulkan"]
    for name in names:
        which = shutil.which(name)
        if which:
            candidates.append(Path(which))
    if runtime.exists():
        for name in names:
            candidates.extend(runtime.rglob(name))
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return None


def backend_status() -> Dict[str, Any]:
    real_repo = PROJECT_ROOT / "third_party" / "Real-ESRGAN"
    swin_repo = PROJECT_ROOT / "third_party" / "SwinIR"
    ncnn = _find_ncnn_executable()
    return {
        "ncnn": str(ncnn) if ncnn else None,
        "realesrgan_python": (real_repo / "inference_realesrgan.py").exists() and _module("torch"),
        "swinir_python": (swin_repo / "main_test_swinir.py").exists() and _module("torch"),
        "torch": _module("torch"),
    }


def choose_mode(image_path: str | Path) -> Tuple[str, Dict[str, Any]]:
    # Use only non-semantic image statistics; this is intentionally conservative.
    probe_cfg = load_config("ppt_page")
    stats = inspect_image(image_path, probe_cfg)
    edges = float(stats.get("edge_density", 0.0))
    white = float(stats.get("near_white_ratio", 0.0))

    if edges >= 0.13:
        mode = "chart_heavy"
    elif white >= 0.28 and edges >= 0.055:
        mode = "ppt_page"
    else:
        mode = "scene_plus_text"
    return mode, stats


def choose_backend(mode: str) -> str:
    status = backend_status()
    # Text/diagram dense pages default to conservative processing even when AI is available.
    if mode == "chart_heavy":
        return "builtin"
    if status["ncnn"]:
        return "realesrgan_ncnn"
    if status["realesrgan_python"]:
        return "realesrgan"
    if status["swinir_python"]:
        return "swinir"
    return "builtin"


def build_auto_config(image_path: str | Path, mode: str | None = None, backend: str = "auto", scale: float = 2.0) -> tuple[Dict[str, Any], Dict[str, Any]]:
    detected_mode, stats = choose_mode(image_path)
    mode = mode or detected_mode
    cfg = load_config(mode)
    chosen = choose_backend(mode) if backend == "auto" else backend

    if chosen == "realesrgan":
        cfg = deep_merge(cfg, load_yaml(PROJECT_ROOT / "config" / "ai" / "realesrgan-ppt.yaml"))
    elif chosen == "swinir":
        cfg = deep_merge(cfg, load_yaml(PROJECT_ROOT / "config" / "ai" / "swinir-ppt.yaml"))
    elif chosen == "realesrgan_ncnn":
        exe = _find_ncnn_executable()
        if not exe:
            chosen = "builtin"
        else:
            model_dir = exe.parent / "models"
            cfg = deep_merge(cfg, {
                "super_resolution": {
                    "backend": "realesrgan_ncnn",
                    "requested_scale": float(scale),
                    "realesrgan_ncnn": {
                        "executable": str(exe),
                        "model_name": "realesrgan-x4plus",
                        "scale": 2 if scale <= 2 else 4,
                        "tile": 0,
                        "model_dir": str(model_dir) if model_dir.exists() else "",
                    },
                }
            })
    if chosen == "builtin":
        cfg = deep_merge(cfg, {"super_resolution": {"backend": "builtin"}})

    # The final output target can be 2x even when an upstream model is natively 4x.
    cfg.setdefault("output", {})["upscale_factor"] = float(scale)
    cfg.setdefault("super_resolution", {})["requested_scale"] = float(scale)
    meta = {"detected_mode": detected_mode, "selected_mode": mode, "selected_backend": chosen, "probe": stats, "backend_status": backend_status()}
    return cfg, meta
