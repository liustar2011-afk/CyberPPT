from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple
import json
import cv2
import numpy as np

from .inspect import inspect_image
from .sr_backend import run_super_resolution


def _read_with_alpha(path: Path) -> Tuple[np.ndarray, np.ndarray | None]:
    raw = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise ValueError(f"Unable to read image: {path}")
    if raw.ndim == 2:
        bgr = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
        return bgr, None
    if raw.shape[2] == 4:
        return raw[:, :, :3], raw[:, :, 3]
    return raw[:, :, :3], None


def _save_image(path: Path, bgr: np.ndarray, alpha: np.ndarray | None, cfg: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out_cfg = cfg.get("output", {})
    fmt = str(out_cfg.get("format", "png")).lower()
    if alpha is not None:
        if alpha.shape[:2] != bgr.shape[:2]:
            alpha = cv2.resize(alpha, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_LANCZOS4)
        image = np.dstack([bgr, alpha])
    else:
        image = bgr

    if fmt in ("jpg", "jpeg") or path.suffix.lower() in (".jpg", ".jpeg"):
        if image.shape[2] == 4:
            image = image[:, :, :3]
        quality = int(out_cfg.get("jpeg_quality", 96))
        ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    else:
        compression = int(out_cfg.get("png_compression", 6))
        ok, encoded = cv2.imencode(".png", image, [cv2.IMWRITE_PNG_COMPRESSION, compression])
    if not ok:
        raise ValueError(f"Unable to encode image: {path}")
    encoded.tofile(str(path))


def _target_size(w: int, h: int, cfg: Dict[str, Any]) -> Tuple[int, int]:
    out = cfg.get("output", {})
    target_width = out.get("target_width")
    target_height = out.get("target_height")
    if target_width is not None and target_height is not None:
        return max(1, int(target_width)), max(1, int(target_height))
    if not out.get("upscale_enabled", True):
        return w, h
    factor = float(out.get("upscale_factor", 1.5))
    factor = max(factor, 1.0 if out.get("never_downscale", True) else 0.01)
    nw, nh = int(round(w * factor)), int(round(h * factor))
    max_w = int(out.get("max_width", nw))
    max_h = int(out.get("max_height", nh))
    scale = min(max_w / nw if nw > max_w else 1.0, max_h / nh if nh > max_h else 1.0)
    if scale < 1.0:
        nw, nh = int(round(nw * scale)), int(round(nh * scale))
    if out.get("never_downscale", True):
        nw, nh = max(nw, w), max(nh, h)
    return max(1, nw), max(1, nh)


def _fine_structure_mask(bgr: np.ndarray, cfg: Dict[str, Any]) -> np.ndarray:
    analysis = cfg.get("analysis", {})
    protect = cfg.get("protection", {}).get("fine_structure", {})
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, int(analysis.get("canny_low", 80)), int(analysis.get("canny_high", 180)))
    dilation = int(protect.get("dilation", 1))
    if dilation > 0:
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=dilation)
    mask = cv2.GaussianBlur(edges.astype(np.float32) / 255.0, (0, 0), 0.7)
    return np.clip(mask, 0.0, 1.0)


def _white_mask(bgr: np.ndarray, cfg: Dict[str, Any]) -> np.ndarray:
    analysis = cfg.get("analysis", {})
    threshold = int(analysis.get("white_threshold", 244))
    tol = int(analysis.get("white_chroma_tolerance", 12))
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.int16)
    minc = rgb.min(axis=2)
    maxc = rgb.max(axis=2)
    mask = ((minc >= threshold) & ((maxc - minc) <= tol)).astype(np.float32)
    return cv2.GaussianBlur(mask, (0, 0), 1.0)


def _bilateral_denoise(bgr: np.ndarray, strength: float) -> np.ndarray:
    strength = float(np.clip(strength, 0.0, 1.0))
    if strength <= 0:
        return bgr
    sigma_color = 8 + 30 * strength
    sigma_space = 4 + 12 * strength
    return cv2.bilateralFilter(bgr, d=5, sigmaColor=sigma_color, sigmaSpace=sigma_space)


def _local_contrast(bgr: np.ndarray, clip_limit: float, grid: int) -> np.ndarray:
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=max(1.0, clip_limit), tileGridSize=(grid, grid))
    l2 = clahe.apply(l)
    merged = cv2.merge([l2, a, b])
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def _unsharp(bgr: np.ndarray, amount: float, radius: float, threshold: int) -> np.ndarray:
    sigma = max(0.1, float(radius))
    blur = cv2.GaussianBlur(bgr, (0, 0), sigma)
    sharp = cv2.addWeighted(bgr, 1.0 + amount, blur, -amount, 0)
    if threshold <= 0:
        return sharp
    diff = cv2.absdiff(bgr, blur)
    mask = (cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY) >= threshold).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (0, 0), 0.5)[:, :, None]
    return np.clip(bgr.astype(np.float32) * (1 - mask) + sharp.astype(np.float32) * mask, 0, 255).astype(np.uint8)


def _scale_color(bgr: np.ndarray, saturation: float, brightness: float) -> np.ndarray:
    out = bgr
    if abs(saturation - 1.0) > 1e-6:
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] *= saturation
        hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
        out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    if abs(brightness - 1.0) > 1e-6:
        out = np.clip(out.astype(np.float32) * brightness, 0, 255).astype(np.uint8)
    return out


def _blend_text_guard(ai_result: np.ndarray, reference: np.ndarray, cfg: Dict[str, Any]) -> np.ndarray:
    guard = cfg.get("super_resolution", {}).get("text_guard", {})
    if not guard.get("enabled", True):
        return ai_result

    # Fine/high-contrast structures are where text strokes, arrows and diagram lines usually live.
    fine_mask = _fine_structure_mask(reference, cfg)
    strength = float(np.clip(guard.get("fine_structure_blend", 0.72), 0.0, 1.0))
    m = (fine_mask * strength)[:, :, None]
    blended = np.clip(
        ai_result.astype(np.float32) * (1.0 - m) + reference.astype(np.float32) * m,
        0,
        255,
    ).astype(np.uint8)

    # Near-white regions are also protected so AI SR cannot dirty a clean slide background.
    if guard.get("protect_white_background", True):
        white_mask = _white_mask(reference, cfg)
        white_strength = float(np.clip(guard.get("white_background_blend", 0.90), 0.0, 1.0))
        wm = (white_mask * white_strength)[:, :, None]
        blended = np.clip(
            blended.astype(np.float32) * (1.0 - wm) + reference.astype(np.float32) * wm,
            0,
            255,
        ).astype(np.uint8)
    return blended


def _validate(before: Dict[str, Any], after: Dict[str, Any], cfg: Dict[str, Any]) -> list[str]:
    gates = cfg.get("gates", {})
    warnings = []
    if before.get("aspect_ratio") and after.get("aspect_ratio"):
        if abs(before["aspect_ratio"] - after["aspect_ratio"]) > float(gates.get("max_aspect_ratio_delta", 0.001)):
            warnings.append("Aspect ratio changed beyond configured tolerance.")
    drop = float(gates.get("warn_white_ratio_drop", 0.10))
    if before.get("near_white_ratio", 0) > 0.20:
        if after.get("near_white_ratio", 0) < before["near_white_ratio"] * (1.0 - drop):
            warnings.append("Near-white background ratio dropped noticeably; inspect background neutrality.")
    block_ratio = float(gates.get("warn_blockiness_increase_ratio", 1.35))
    if after.get("blockiness_score", 1) > max(1e-6, before.get("blockiness_score", 1)) * block_ratio:
        warnings.append("Approximate blockiness score increased substantially.")
    sharp_ratio = float(gates.get("warn_sharpness_increase_ratio", 8.0))
    if after.get("sharpness_laplacian_variance", 0) > max(1e-6, before.get("sharpness_laplacian_variance", 1)) * sharp_ratio:
        warnings.append("Sharpness score increased extremely; inspect for halos or jagged edges.")
    return warnings


def _structural_fidelity(reference: np.ndarray, result: np.ndarray, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Detect model hallucination that moves or invents text/diagram edges."""
    if result.shape[:2] != reference.shape[:2]:
        result = cv2.resize(result, (reference.shape[1], reference.shape[0]), interpolation=cv2.INTER_AREA)
    ref_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    out_gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    ref_edges = cv2.Canny(ref_gray, 80, 180) > 0
    out_edges = cv2.Canny(out_gray, 80, 180) > 0
    kernel = np.ones((3, 3), np.uint8)
    ref_near = cv2.dilate(ref_edges.astype(np.uint8), kernel) > 0
    out_near = cv2.dilate(out_edges.astype(np.uint8), kernel) > 0
    edge_recall = float((ref_edges & out_near).sum() / max(1, int(ref_edges.sum())))
    edge_precision = float((out_edges & ref_near).sum() / max(1, int(out_edges.sum())))
    mean_abs_delta = float(
        np.mean(np.abs(ref_gray.astype(np.float32) - out_gray.astype(np.float32))) / 255.0
    )
    if float(ref_gray.std()) < 1e-6 or float(out_gray.std()) < 1e-6:
        correlation = 1.0 if mean_abs_delta <= 0.01 else 0.0
    else:
        correlation = float(np.corrcoef(ref_gray.ravel(), out_gray.ravel())[0, 1])
    gates = cfg.get("gates", {})
    valid = (
        correlation >= float(gates.get("min_structural_correlation", 0.92))
        and mean_abs_delta <= float(gates.get("max_normalized_mean_abs_delta", 0.08))
        and edge_recall >= float(gates.get("min_edge_recall", 0.75))
        and edge_precision >= float(gates.get("min_edge_precision", 0.75))
    )
    return {
        "valid": bool(valid),
        "correlation": round(correlation, 6),
        "normalized_mean_abs_delta": round(mean_abs_delta, 6),
        "edge_recall": round(edge_recall, 6),
        "edge_precision": round(edge_precision, 6),
    }


def enhance(input_path: str | Path, output_path: str | Path, cfg: Dict[str, Any], report_path: str | Path | None = None) -> Dict[str, Any]:
    input_path = Path(input_path)
    output_path = Path(output_path)
    before = inspect_image(input_path, cfg)

    # Final dimensions are always derived from the original input, not from an AI backend's native x4 output.
    input_bgr, input_alpha = _read_with_alpha(input_path)
    in_h, in_w = input_bgr.shape[:2]
    target_w, target_h = _target_size(in_w, in_h, cfg)
    lanczos_reference = cv2.resize(input_bgr, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4) \
        if (target_w, target_h) != (in_w, in_h) else input_bgr.copy()
    alpha = input_alpha
    if alpha is not None and alpha.shape[:2] != (target_h, target_w):
        alpha = cv2.resize(alpha, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

    sr_result = None
    backend = str(cfg.get("super_resolution", {}).get("backend", "builtin")).lower()
    try:
        sr_result = run_super_resolution(input_path, cfg)
        if sr_result is not None:
            ai_bgr, _ = _read_with_alpha(sr_result.path)
            if ai_bgr.shape[:2] != (target_h, target_w):
                interpolation = cv2.INTER_AREA if ai_bgr.shape[0] >= target_h and ai_bgr.shape[1] >= target_w else cv2.INTER_LANCZOS4
                ai_bgr = cv2.resize(ai_bgr, (target_w, target_h), interpolation=interpolation)
            original = _blend_text_guard(ai_bgr, lanczos_reference, cfg)
            backend = sr_result.backend
        else:
            original = lanczos_reference.copy()
            backend = "builtin"

        protected_reference = lanczos_reference.copy()
        fine_mask = _fine_structure_mask(protected_reference, cfg)
        white_mask = _white_mask(protected_reference, cfg)

        proc = cfg.get("processing", {})
        result = original.copy()

        denoise_cfg = proc.get("denoise", {})
        if denoise_cfg.get("enabled", True):
            result = _bilateral_denoise(result, float(denoise_cfg.get("strength", 0.18)))

        lc = proc.get("local_contrast", {})
        if lc.get("enabled", False):
            result = _local_contrast(result, float(lc.get("clip_limit", 1.15)), int(lc.get("tile_grid_size", 8)))

        fine_cfg = cfg.get("protection", {}).get("fine_structure", {})
        if fine_cfg.get("enabled", True):
            blend = float(np.clip(fine_cfg.get("original_blend", 0.18), 0.0, 1.0))
            m = (fine_mask * blend)[:, :, None]
            result = np.clip(result.astype(np.float32) * (1 - m) + protected_reference.astype(np.float32) * m, 0, 255).astype(np.uint8)

        sharpen = proc.get("sharpen", {})
        if sharpen.get("enabled", True):
            result = _unsharp(
                result,
                float(sharpen.get("amount", 0.58)),
                float(sharpen.get("radius", 1.05)),
                int(sharpen.get("threshold", 3)),
            )

        result = _scale_color(
            result,
            float(proc.get("saturation", {}).get("factor", proc.get("saturation", 1.0)) if isinstance(proc.get("saturation"), dict) else proc.get("saturation", 1.0)),
            float(proc.get("brightness", {}).get("factor", proc.get("brightness", 1.0)) if isinstance(proc.get("brightness"), dict) else proc.get("brightness", 1.0)),
        )

        white_cfg = cfg.get("protection", {}).get("white_background", {})
        if white_cfg.get("enabled", True):
            blend = float(np.clip(white_cfg.get("original_blend", 0.78), 0.0, 1.0))
            m = (white_mask * blend)[:, :, None]
            result = np.clip(result.astype(np.float32) * (1 - m) + protected_reference.astype(np.float32) * m, 0, 255).astype(np.uint8)
            if white_cfg.get("clean_extreme_white", False):
                threshold = int(white_cfg.get("clean_threshold", 252))
                grayish = np.max(result, axis=2) - np.min(result, axis=2) <= 5
                bright = np.min(result, axis=2) >= threshold
                result[grayish & bright] = 255

        _save_image(output_path, result, alpha, cfg)
        after = inspect_image(output_path, cfg)
        warnings = _validate(before, after, cfg)
        structural_fidelity = _structural_fidelity(lanczos_reference, result, cfg)
        if sr_result is not None and not structural_fidelity["valid"]:
            warnings.append("STRUCTURAL_FIDELITY_FAILED: model output changed text/diagram geometry.")

        report = {
            "mode": cfg.get("mode", "ppt_page"),
            "input": str(input_path),
            "output": str(output_path),
            "super_resolution_backend": backend,
            "ai_super_resolution_used": sr_result is not None,
            "super_resolution_metadata": sr_result.metadata if sr_result else {},
            "text_guard_enabled": bool(cfg.get("super_resolution", {}).get("text_guard", {}).get("enabled", True)) if sr_result else False,
            "upscale_applied": [before["width"], before["height"]] != [after["width"], after["height"]],
            "before": before,
            "after": after,
            "warnings": warnings,
            "structural_fidelity": structural_fidelity,
            "quality_gate_valid": not (sr_result is not None and not structural_fidelity["valid"]),
        }
        # Backward-compatible report key.
        report["external_super_resolution_used"] = sr_result is not None and backend == "external"
        if report_path:
            rp = Path(report_path)
            rp.parent.mkdir(parents=True, exist_ok=True)
            rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    finally:
        if sr_result is not None:
            sr_result.cleanup()
