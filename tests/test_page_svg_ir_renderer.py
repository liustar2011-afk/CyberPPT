from pathlib import Path

from scripts.dual_image_overlay.scene_graph.svg_renderer import render_page_svg_ir


def _ir(tmp_path: Path) -> dict:
    image = tmp_path / "background.png"
    image.write_bytes(b"not-decoded-by-renderer")
    return {
        "canvas": {"width": 100, "height": 50},
        "image_assets": {
            "assets": [
                {
                    "asset_id": "asset_bg",
                    "source": str(image),
                }
            ]
        },
        "layers": [
            {
                "id": "background",
                "z_index": 0,
                "elements": [
                    {
                        "id": "page_background",
                        "kind": "image",
                        "asset_id": "asset_bg",
                        "bbox": {"x": 0, "y": 0, "width": 100, "height": 50},
                    }
                ],
            },
            {
                "id": "editable_information",
                "z_index": 20,
                "elements": [
                    {
                        "id": "text_1",
                        "kind": "text",
                        "text": "可编辑文字",
                        "bbox": {"x": 10, "y": 10, "width": 40, "height": 15},
                        "style": {"font_size": 10, "font_size_space": "ppt_svg_px", "fill": "#123456"},
                        "metrics": {"text": "可编辑文字", "font_size": 10},
                    }
                ],
            },
        ],
    }


def test_page_svg_ir_renderer_consumes_asset_registry_and_text_metrics(tmp_path):
    svg = render_page_svg_ir(
        _ir(tmp_path),
        canvas={"width": 1280, "height": 720},
        content_region={"x": 20, "y": 100, "width": 1240, "height": 600},
        slide_title="标题",
    )
    assert 'data-export-source="page_svg_ir"' in svg
    assert 'data-ir-asset-id="asset_bg"' in svg
    assert str(tmp_path / "background.png") in svg
    assert 'data-ir-editable="1"' in svg
    assert '<g id="ir_' not in svg
    assert 'font-size="10.00"' in svg
    assert "可编辑文字" in svg
