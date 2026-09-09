import pytest

from cyberppt.full_slide_context import (
    BODY_EXPORT_CANVAS,
    FULL_SLIDE_CANVAS,
    FullSlideDesignContextSpec,
    SlideRegionSpec,
    default_full_slide_design_context,
    validate_full_slide_design_context,
)


def test_default_context_is_full_16_9_with_external_title_and_2_1_body_mapping():
    context = default_full_slide_design_context()
    assert context.canvas == FULL_SLIDE_CANVAS == (1920, 1080, "16:9")
    assert context.body_export_canvas == BODY_EXPORT_CANVAS == (2048, 1024, "2:1")
    assert context.title_region.render_mode == "external_text_layer"
    assert context.body_region.render_mode == "body_image_export"
    assert context.body_region.w == context.body_region.h * 2
    assert context.title_region.y + context.title_region.h <= context.body_region.y


def test_context_round_trip_validation_preserves_geometry():
    context = default_full_slide_design_context()
    restored = validate_full_slide_design_context(context.to_dict())
    assert restored == context


def test_body_region_cannot_overlap_external_title_region():
    with pytest.raises(ValueError, match="must not overlap"):
        FullSlideDesignContextSpec(
            canvas=FULL_SLIDE_CANVAS,
            title_region=SlideRegionSpec(
                x=128, y=52, w=1664, h=200,
                role="external_title_region", render_mode="external_text_layer",
            ),
            body_region=SlideRegionSpec(
                x=128, y=216, w=1664, h=832,
                role="body_visual_region", render_mode="body_image_export",
            ),
        )


def test_body_export_contract_remains_2048x1024():
    with pytest.raises(ValueError, match="body export canvas must remain"):
        FullSlideDesignContextSpec(
            canvas=FULL_SLIDE_CANVAS,
            title_region=SlideRegionSpec(
                x=128, y=52, w=1664, h=120,
                role="external_title_region", render_mode="external_text_layer",
            ),
            body_region=SlideRegionSpec(
                x=128, y=216, w=1664, h=832,
                role="body_visual_region", render_mode="body_image_export",
            ),
            body_export_canvas=(1920, 960, "2:1"),
        )
