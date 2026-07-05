from scripts.dual_image_overlay.scene_graph.render_qa import build_render_qa


def test_render_qa_flags_text_outside_canvas():
    qa = build_render_qa(
        layout_plan={
            "items": [
                {"node_id": "text_1", "text": "审计留痕", "bbox": [1260, 100, 1310, 120]},
            ]
        },
        rendered_image_size={"width": 1280, "height": 720},
    )

    assert qa["valid"] is False
    assert qa["issues"][0]["code"] == "render_text_outside_canvas"


def test_render_qa_accepts_text_inside_canvas():
    qa = build_render_qa(
        layout_plan={
            "items": [
                {"node_id": "text_1", "text": "审计留痕", "bbox": [1160, 100, 1220, 120]},
            ]
        },
        rendered_image_size={"width": 1280, "height": 720},
    )

    assert qa["valid"] is True
