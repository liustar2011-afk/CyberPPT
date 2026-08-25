from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class SRResult:
    path: Path
    backend: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    cleanup_dir: Path | None = None

    def cleanup(self) -> None:
        if self.cleanup_dir and self.cleanup_dir.exists():
            shutil.rmtree(self.cleanup_dir, ignore_errors=True)


def _repo_path(value: str | Path) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (ROOT / p).resolve()


def _python_executable(value: str | None) -> str:
    value = (value or "").strip()
    return value or sys.executable


def _run(command: List[str], *, cwd: Path | None = None) -> None:
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    subprocess.run(command, cwd=str(cwd) if cwd else None, env=env, check=True)


def run_external_sr(input_path: Path, config: Dict[str, Any]) -> SRResult:
    sr = config.get("super_resolution", {})
    ext = sr.get("external", {})
    if not ext.get("enabled", False):
        raise RuntimeError("External super-resolution is not enabled.")

    executable = str(ext.get("executable", "")).strip()
    if not executable:
        raise RuntimeError("External super-resolution executable is not configured.")
    resolved = shutil.which(executable) or (executable if Path(executable).exists() else None)
    if not resolved:
        raise RuntimeError(f"External super-resolution executable not found: {executable}")

    command: List[str] = ext.get("command", [])
    if not command:
        raise RuntimeError("External super-resolution command template is empty.")

    scale = float(ext.get("scale", sr.get("requested_scale", 2.0)))
    tmp_dir = Path(tempfile.mkdtemp(prefix="ppt_image_enhancer_sr_"))
    output_path = tmp_dir / f"{input_path.stem}_sr.png"

    variables = {
        "executable": str(resolved),
        "input": str(input_path.resolve()),
        "output": str(output_path),
        "scale": str(scale),
    }
    rendered = [str(token).format(**variables) for token in command]
    _run(rendered)
    if not output_path.exists():
        raise RuntimeError("External super-resolution command completed but no output file was created.")
    return SRResult(output_path, "external", {"scale": scale, "command": rendered}, tmp_dir)


def run_realesrgan(input_path: Path, config: Dict[str, Any]) -> SRResult:
    sr = config.get("super_resolution", {})
    rcfg = sr.get("realesrgan", {})
    repo = _repo_path(rcfg.get("repo_dir", "third_party/Real-ESRGAN"))
    script = repo / "inference_realesrgan.py"
    if not script.exists():
        raise RuntimeError(
            f"Real-ESRGAN not found at {repo}. Run: python scripts/setup_ai_backends.py --backend realesrgan"
        )

    py = _python_executable(rcfg.get("python"))
    model = str(rcfg.get("model_name", "RealESRGAN_x4plus"))
    outscale = float(rcfg.get("outscale", sr.get("requested_scale", 2.0)))
    tile = int(rcfg.get("tile", 0))
    tile_pad = int(rcfg.get("tile_pad", 10))
    pre_pad = int(rcfg.get("pre_pad", 0))
    denoise = float(rcfg.get("denoise_strength", 0.35))

    tmp_dir = Path(tempfile.mkdtemp(prefix="ppt_image_enhancer_realesrgan_"))
    out_dir = tmp_dir / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    command = [
        py,
        str(script),
        "-i", str(input_path.resolve()),
        "-o", str(out_dir),
        "-n", model,
        "--outscale", str(outscale),
        "--suffix", "pptsr",
        "--ext", "png",
        "--tile", str(tile),
        "--tile_pad", str(tile_pad),
        "--pre_pad", str(pre_pad),
        "--denoise_strength", str(denoise),
    ]
    if bool(rcfg.get("fp32", False)):
        command.append("--fp32")
    gpu_id = rcfg.get("gpu_id", None)
    if gpu_id is not None:
        command += ["--gpu-id", str(int(gpu_id))]

    _run(command, cwd=repo)
    output = out_dir / f"{input_path.stem}_pptsr.png"
    if not output.exists():
        candidates = sorted(out_dir.glob(f"{input_path.stem}_pptsr.*"))
        if candidates:
            output = candidates[0]
    if not output.exists():
        raise RuntimeError(f"Real-ESRGAN completed but output was not found in {out_dir}")

    return SRResult(
        output,
        "realesrgan",
        {"model": model, "native_or_outscale": outscale, "tile": tile, "repo": str(repo)},
        tmp_dir,
    )


def run_swinir(input_path: Path, config: Dict[str, Any]) -> SRResult:
    sr = config.get("super_resolution", {})
    scfg = sr.get("swinir", {})
    repo = _repo_path(scfg.get("repo_dir", "third_party/SwinIR"))
    script = repo / "main_test_swinir.py"
    if not script.exists():
        raise RuntimeError(
            f"SwinIR not found at {repo}. Run: python scripts/setup_ai_backends.py --backend swinir"
        )

    py = _python_executable(scfg.get("python"))
    scale = int(scfg.get("scale", 4))
    if scale != 4:
        raise ValueError("SwinIR real-world SR backend is configured for the official x4 real_sr model; scale must be 4.")

    model_path = Path(str(scfg.get(
        "model_path",
        "model_zoo/swinir/003_realSR_BSRGAN_DFO_s64w8_SwinIR-M_x4_GAN.pth",
    )))
    if not model_path.is_absolute():
        model_path = repo / model_path

    tile = int(scfg.get("tile", 400))
    tile_overlap = int(scfg.get("tile_overlap", 32))
    large_model = bool(scfg.get("large_model", False))

    tmp_dir = Path(tempfile.mkdtemp(prefix="ppt_image_enhancer_swinir_"))
    input_dir = tmp_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    staged_input = input_dir / input_path.name
    shutil.copy2(input_path, staged_input)

    command = [
        py,
        str(script),
        "--task", "real_sr",
        "--scale", str(scale),
        "--model_path", str(model_path),
        "--folder_lq", str(input_dir),
        "--tile_overlap", str(tile_overlap),
    ]
    if tile > 0:
        if tile % 8 != 0:
            raise ValueError("SwinIR tile size must be a multiple of 8.")
        command += ["--tile", str(tile)]
    if large_model:
        command.append("--large_model")

    # The upstream script writes to ./results, so use an isolated temporary cwd.
    _run(command, cwd=tmp_dir)
    result_dir = tmp_dir / "results" / f"swinir_real_sr_x{scale}"
    if large_model:
        result_dir = Path(str(result_dir) + "_large")
    output = result_dir / f"{input_path.stem}_SwinIR.png"
    if not output.exists():
        candidates = sorted((tmp_dir / "results").rglob(f"{input_path.stem}_SwinIR.png"))
        if candidates:
            output = candidates[0]
    if not output.exists():
        raise RuntimeError(f"SwinIR completed but output was not found under {tmp_dir / 'results'}")

    return SRResult(
        output,
        "swinir",
        {
            "model": str(model_path),
            "native_scale": scale,
            "tile": tile,
            "large_model": large_model,
            "repo": str(repo),
        },
        tmp_dir,
    )


def run_realesrgan_ncnn(input_path: Path, config: Dict[str, Any]) -> SRResult:
    sr = config.get("super_resolution", {})
    ncfg = sr.get("realesrgan_ncnn", {})
    executable = str(ncfg.get("executable", "")).strip()
    if not executable:
        executable = "realesrgan-ncnn-vulkan"
    resolved = shutil.which(executable) or (executable if Path(executable).exists() else None)
    if not resolved:
        raise RuntimeError(
            "Real-ESRGAN NCNN Vulkan executable not found. Configure super_resolution.realesrgan_ncnn.executable."
        )

    scale = int(ncfg.get("scale", 2))
    model = str(ncfg.get("model_name", "realesrgan-x4plus"))
    tile = int(ncfg.get("tile", 0))
    model_dir = str(ncfg.get("model_dir", "")).strip()

    tmp_dir = Path(tempfile.mkdtemp(prefix="ppt_image_enhancer_realesrgan_ncnn_"))
    output = tmp_dir / f"{input_path.stem}_ncnn.png"
    command = [str(resolved), "-i", str(input_path.resolve()), "-o", str(output), "-n", model, "-s", str(scale), "-t", str(tile)]
    if model_dir:
        command += ["-m", model_dir]
    _run(command)
    if not output.exists():
        raise RuntimeError("Real-ESRGAN NCNN Vulkan completed but no output file was created.")
    return SRResult(output, "realesrgan_ncnn", {"model": model, "scale": scale, "tile": tile}, tmp_dir)


def run_super_resolution(input_path: Path, config: Dict[str, Any]) -> SRResult | None:
    backend = str(config.get("super_resolution", {}).get("backend", "builtin")).lower().strip()
    if backend in ("", "builtin", "none", "off"):
        return None
    if backend == "realesrgan":
        return run_realesrgan(input_path, config)
    if backend == "swinir":
        return run_swinir(input_path, config)
    if backend in ("realesrgan_ncnn", "ncnn"):
        return run_realesrgan_ncnn(input_path, config)
    if backend == "external":
        return run_external_sr(input_path, config)
    raise ValueError(
        f"Unknown super-resolution backend '{backend}'. Supported: builtin, realesrgan, swinir, realesrgan_ncnn, external"
    )
