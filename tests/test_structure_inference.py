from __future__ import annotations

from scripts.dual_image_overlay.structure_inference import infer_structure_containers


def test_infers_reusable_containers_from_text_geometry() -> None:
    text_items = [
        _text("top_summary", 150, 140, 900, 24),
        _text("top_detail", 150, 176, 760, 24),
        _text("1", 70, 250, 14, 22),
        _text("A title", 114, 250, 130, 20),
        _text("A body 1", 110, 316, 180, 18),
        _text("A body 2", 110, 386, 180, 18),
        _text("2", 390, 250, 14, 22),
        _text("B title", 432, 250, 130, 20),
        _text("B body 1", 424, 316, 180, 18),
        _text("B body 2", 424, 386, 180, 18),
        _text("3", 696, 250, 14, 22),
        _text("C title", 730, 250, 130, 20),
        _text("C body 1", 728, 316, 180, 18),
        _text("C body 2", 728, 386, 180, 18),
        _text("4", 990, 250, 14, 22),
        _text("D title", 1034, 250, 130, 20),
        _text("D body 1", 1028, 316, 180, 18),
        _text("D body 2", 1028, 386, 180, 18),
        _text("bottom 1", 194, 620, 162, 31),
        _text("bottom 2", 451, 620, 162, 31),
        _text("bottom 3", 714, 620, 162, 31),
        _text("bottom 4", 969, 620, 162, 31),
    ]

    result = infer_structure_containers(page_number=3, text_items=text_items)

    assert result["schema"] == "cyberppt.dual_image.structure_inference.v1"
    assert result["valid"] is True
    assert result["container_count"] == 6
    roles = [item["role"] for item in result["containers"]]
    assert roles.count("row_band") == 2
    assert roles.count("repeated_panel") == 4
    assert all(item.get("container_id") for item in result["text_items"])
    assert len({item["container_id"] for item in result["text_items"] if item["text"].startswith(("A", "B", "C", "D", "1", "2", "3", "4"))}) == 4


def _text(text: str, x: float, y: float, w: float, h: float) -> dict[str, object]:
    return {
        "text": text,
        "bbox": {"x": x, "y": y, "w": w, "h": h},
        "role": "body",
    }
