from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import cv2
import numpy as np


def _read_bgr(path: str | Path) -> np.ndarray:
    # ``cv2.imread`` is not Unicode-safe on some Windows OpenCV builds.
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to read image: {path}")
    return image


def laplacian_variance(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def edge_density(gray: np.ndarray, low: int = 80, high: int = 180) -> float:
    edges = cv2.Canny(gray, low, high)
    return float(np.mean(edges > 0))


def near_white_ratio(bgr: np.ndarray, threshold: int = 244, chroma_tolerance: int = 12) -> float:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.int16)
    minc = rgb.min(axis=2)
    maxc = rgb.max(axis=2)
    neutral = (maxc - minc) <= chroma_tolerance
    bright = minc >= threshold
    return float(np.mean(neutral & bright))


def noise_estimate(gray: np.ndarray) -> float:
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    residual = gray.astype(np.float32) - blur.astype(np.float32)
    mad = np.median(np.abs(residual - np.median(residual)))
    return float(1.4826 * mad)


def blockiness_score(gray: np.ndarray, block: int = 8) -> float:
    g = gray.astype(np.float32)
    h, w = g.shape
    scores = []
    if w > block + 2:
        boundaries = np.arange(block, w, block)
        if boundaries.size:
            boundary_diff = np.abs(g[:, boundaries] - g[:, boundaries - 1]).mean()
            normal_idx = np.setdiff1d(np.arange(1, w), boundaries)
            if normal_idx.size:
                normal_diff = np.abs(g[:, normal_idx] - g[:, normal_idx - 1]).mean()
                scores.append(boundary_diff / max(normal_diff, 1e-6))
    if h > block + 2:
        boundaries = np.arange(block, h, block)
        if boundaries.size:
            boundary_diff = np.abs(g[boundaries, :] - g[boundaries - 1, :]).mean()
            normal_idx = np.setdiff1d(np.arange(1, h), boundaries)
            if normal_idx.size:
                normal_diff = np.abs(g[normal_idx, :] - g[normal_idx - 1, :]).mean()
                scores.append(boundary_diff / max(normal_diff, 1e-6))
    return float(np.mean(scores)) if scores else 1.0


def inspect_image(path: str | Path, config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    config = config or {}
    analysis = config.get("analysis", {})
    bgr = _read_bgr(path)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    white_threshold = int(analysis.get("white_threshold", 244))
    chroma_tol = int(analysis.get("white_chroma_tolerance", 12))
    low = int(analysis.get("canny_low", 80))
    high = int(analysis.get("canny_high", 180))

    sharpness = laplacian_variance(gray)
    edges = edge_density(gray, low, high)
    whites = near_white_ratio(bgr, white_threshold, chroma_tol)
    noise = noise_estimate(gray)
    blockiness = blockiness_score(gray)

    notes = []
    if w < 1800 or h < 1000:
        notes.append("Resolution is relatively small for presentation use; moderate upscaling may help.")
    if whites > 0.35:
        notes.append("Large near-white area detected; white-background protection is recommended.")
    if sharpness < 80:
        notes.append("Low Laplacian sharpness score; the image may be visually soft or blurred.")
    if edges > 0.12:
        notes.append("High edge density detected; use conservative denoise to protect text/lines.")
    if blockiness > 1.22:
        notes.append("Possible block/compression artifacts detected.")

    return {
        "file": str(path),
        "width": int(w),
        "height": int(h),
        "aspect_ratio": round(w / h, 6) if h else None,
        "sharpness_laplacian_variance": round(sharpness, 4),
        "edge_density": round(edges, 6),
        "near_white_ratio": round(whites, 6),
        "noise_estimate": round(noise, 4),
        "blockiness_score": round(blockiness, 4),
        "notes": notes,
    }
