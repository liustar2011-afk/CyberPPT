from pathlib import Path

from PIL import Image, ImageDraw

from cyberppt.full_image_signature import (
    build_manifest_visual_signatures,
    build_page_visual_signature,
)


def _canvas(path: Path, side: str) -> Path:
    image = Image.new("RGB", (300, 150), "white")
    draw = ImageDraw.Draw(image)
    if side == "left":
        draw.rectangle((15, 25, 95, 125), fill="black")
    elif side == "right":
        draw.rectangle((205, 25, 285, 125), fill="black")
    elif side == "dense":
        for x in range(10, 290, 20):
            for y in range(10, 140, 20):
                draw.rectangle((x, y, x + 8, y + 8), fill="black")
    image.save(path)
    return path


def test_signature_distinguishes_left_and_right_visual_gravity(tmp_path):
    left = build_page_visual_signature(_canvas(tmp_path / "left.png", "left"), page_number=1)
    right = build_page_visual_signature(_canvas(tmp_path / "right.png", "right"), page_number=2)
    assert left["gravity"]["horizontal"] == "left"
    assert right["gravity"]["horizontal"] == "right"
    assert left["structure_hash"] != right["structure_hash"]
    assert len(left["skeleton_3x3"]) == 9


def test_signature_density_responds_to_actual_edge_activity(tmp_path):
    sparse = build_page_visual_signature(_canvas(tmp_path / "sparse.png", "left"), page_number=1)
    dense = build_page_visual_signature(_canvas(tmp_path / "dense.png", "dense"), page_number=2)
    assert dense["density_score"] > sparse["density_score"]
    assert dense["density"] in {"medium", "dense"}


def test_manifest_signature_uses_audited_visual_medium_metadata(tmp_path):
    image = _canvas(tmp_path / "page.png", "left")
    manifest = {
        "pairs": [{
            "page_number": 1,
            "full": {
                "path": str(image),
                "text_audit": {"valid": True},
                "debug_receipt": {
                    "visual_medium_policy": {"preferred": "business_scene"}
                },
            },
        }]
    }
    signatures = build_manifest_visual_signatures(manifest)
    assert signatures[0]["visual_medium"] == "business_scene"
    assert signatures[0]["source_sha256"]
