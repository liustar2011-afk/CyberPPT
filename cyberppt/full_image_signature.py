"""Image-level visual signatures for audited Stage 02 full images.

The signature deliberately avoids OCR and semantic guessing. It measures only
coarse edge activity from the finished image and combines that with the already
audited visual-medium metadata carried by the Stage 02 manifest.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image, ImageFilter

from cyberppt.full_image_rhythm import audited_full_image_entries


VISUAL_SIGNATURE_SCHEMA = "cyberppt.full_image_visual_signature.v1"


def _gravity_label(value: float, negative: str, neutral: str, positive: str) -> str:
    if value < 0.42:
        return negative
    if value > 0.58:
        return positive
    return neutral


def _edge_activity(path: Path, *, size: tuple[int, int] = (96, 48)) -> tuple[list[int], int, int]:
    with Image.open(path) as source:
        gray = source.convert("L").resize(size, Image.Resampling.LANCZOS)
    edge = gray.filter(ImageFilter.FIND_EDGES)
    width, height = edge.size
    pixels = list(edge.getdata())
    clean: list[int] = []
    for y in range(height):
        for x in range(width):
            value = pixels[y * width + x]
            clean.append(0 if x in {0, width - 1} or y in {0, height - 1} else int(value))
    return clean, width, height


def _structure_hash(activity: Sequence[int], width: int, height: int) -> str:
    image = Image.new("L", (width, height))
    image.putdata(activity)
    small = image.resize((8, 8), Image.Resampling.BILINEAR)
    values = list(small.getdata())
    mean = sum(values) / len(values)
    bits = "".join("1" if value >= mean else "0" for value in values)
    return f"{int(bits, 2):016x}"


def build_page_visual_signature(
    path: Path,
    *,
    page_number: int,
    visual_medium: str = "unspecified",
) -> dict[str, Any]:
    """Measure coarse composition from one finished full image without OCR."""

    path = Path(path)
    if page_number <= 0:
        raise ValueError("visual signature requires a positive page number")
    if not path.is_file():
        raise FileNotFoundError(path)

    activity, width, height = _edge_activity(path)
    total = float(sum(activity))
    if total <= 0:
        gx = gy = 0.5
    else:
        gx = (
            sum((index % width) * value for index, value in enumerate(activity))
            / total
            / max(1, width - 1)
        )
        gy = (
            sum((index // width) * value for index, value in enumerate(activity))
            / total
            / max(1, height - 1)
        )

    bin_mass = [0.0] * 9
    for index, value in enumerate(activity):
        x = index % width
        y = index // width
        col = min(2, int(x * 3 / width))
        row = min(2, int(y * 3 / height))
        bin_mass[row * 3 + col] += value
    shares = [mass / total if total else 0.0 for mass in bin_mass]
    skeleton = "".join("1" if share >= 0.08 else "0" for share in shares)

    density_score = total / max(1, width * height)
    density = "sparse" if density_score < 12 else ("medium" if density_score < 28 else "dense")

    return {
        "schema": VISUAL_SIGNATURE_SCHEMA,
        "page_number": int(page_number),
        "source_path": str(path),
        "source_sha256": sha256(path.read_bytes()).hexdigest(),
        "visual_medium": str(visual_medium or "unspecified"),
        "gravity": {
            "x": round(gx, 4),
            "y": round(gy, 4),
            "horizontal": _gravity_label(gx, "left", "center", "right"),
            "vertical": _gravity_label(gy, "top", "middle", "bottom"),
        },
        "density": density,
        "density_score": round(density_score, 4),
        "skeleton_3x3": skeleton,
        "skeleton_shares": [round(value, 4) for value in shares],
        "structure_hash": _structure_hash(activity, width, height),
    }


def pair_visual_medium(pair: Mapping[str, object]) -> str:
    """Read visual medium from audited Stage 02 metadata; never infer it from pixels."""

    full = pair.get("full")
    full = full if isinstance(full, Mapping) else {}
    debug = full.get("debug_receipt")
    debug = debug if isinstance(debug, Mapping) else {}
    policy = debug.get("visual_medium_policy")
    policy = policy if isinstance(policy, Mapping) else {}
    preferred = str(policy.get("preferred") or "").strip()
    if preferred:
        return preferred
    for owner in (pair, full):
        candidate = owner.get("visual_medium_policy") if isinstance(owner, Mapping) else None
        if isinstance(candidate, Mapping):
            preferred = str(candidate.get("preferred") or "").strip()
            if preferred:
                return preferred
    return "unspecified"


def build_manifest_visual_signatures(manifest: Mapping[str, object]) -> list[dict[str, Any]]:
    entries = audited_full_image_entries(manifest)
    pairs = manifest.get("pairs")
    pair_by_page = {
        int(pair.get("page_number") or 0): pair
        for pair in pairs
        if isinstance(pair, Mapping)
    } if isinstance(pairs, list) else {}
    return [
        build_page_visual_signature(
            path,
            page_number=page_number,
            visual_medium=pair_visual_medium(pair_by_page.get(page_number, {})),
        )
        for page_number, path in entries
    ]


__all__ = [
    "VISUAL_SIGNATURE_SCHEMA",
    "build_manifest_visual_signatures",
    "build_page_visual_signature",
    "pair_visual_medium",
]
