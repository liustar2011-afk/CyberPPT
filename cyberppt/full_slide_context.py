"""Full-slide 16:9 design context for Stage 02.

The production ImageGen asset remains the 2048x1024 body image.  This contract
adds the complete 16:9 slide coordinate system so composition decisions know
where the external title region sits and how the body export maps back into the
finished slide.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


FULL_SLIDE_CONTEXT_VERSION = "full-slide-context-v1"
FULL_SLIDE_CANVAS = (1920, 1080, "16:9")
BODY_EXPORT_CANVAS = (2048, 1024, "2:1")


@dataclass(frozen=True)
class SlideRegionSpec:
    x: int
    y: int
    w: int
    h: int
    role: str
    render_mode: str

    def __post_init__(self) -> None:
        if min(self.x, self.y, self.w, self.h) < 0 or self.w <= 0 or self.h <= 0:
            raise ValueError("full-slide region geometry must be positive")
        if not self.role.strip() or not self.render_mode.strip():
            raise ValueError("full-slide region requires role and render_mode")


@dataclass(frozen=True)
class FullSlideDesignContextSpec:
    canvas: tuple[int, int, str]
    title_region: SlideRegionSpec
    body_region: SlideRegionSpec
    body_export_canvas: tuple[int, int, str] = BODY_EXPORT_CANVAS
    subtitle_render_mode: str = "external_text_layer"
    version: str = FULL_SLIDE_CONTEXT_VERSION

    def __post_init__(self) -> None:
        if self.canvas != FULL_SLIDE_CANVAS:
            raise ValueError("full-slide design canvas must be 1920x1080 (16:9)")
        if self.body_export_canvas != BODY_EXPORT_CANVAS:
            raise ValueError("body export canvas must remain 2048x1024 (2:1)")
        width, height, _ = self.canvas
        for region in (self.title_region, self.body_region):
            if region.x + region.w > width or region.y + region.h > height:
                raise ValueError(f"full-slide {region.role} region exceeds the 16:9 canvas")
        if self.title_region.render_mode != "external_text_layer":
            raise ValueError("title region must remain an external text layer")
        if self.body_region.render_mode != "body_image_export":
            raise ValueError("body region must map to the body image export")
        title_bottom = self.title_region.y + self.title_region.h
        if title_bottom > self.body_region.y:
            raise ValueError("external title region must not overlap the body image region")
        if self.body_region.w * 1 != self.body_region.h * 2:
            raise ValueError("full-slide body region must preserve the 2:1 body-image aspect ratio")
        if self.subtitle_render_mode != "external_text_layer":
            raise ValueError("subtitle must remain an external text layer")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_full_slide_design_context() -> FullSlideDesignContextSpec:
    return FullSlideDesignContextSpec(
        canvas=FULL_SLIDE_CANVAS,
        title_region=SlideRegionSpec(
            x=128,
            y=52,
            w=1664,
            h=120,
            role="external_title_region",
            render_mode="external_text_layer",
        ),
        body_region=SlideRegionSpec(
            x=128,
            y=216,
            w=1664,
            h=832,
            role="body_visual_region",
            render_mode="body_image_export",
        ),
    )


def _canvas(value: object, *, field: str) -> tuple[int, int, str]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"full-slide context {field} must be [width, height, ratio]")
    return int(value[0]), int(value[1]), str(value[2])


def _region(value: object, *, field: str) -> SlideRegionSpec:
    if not isinstance(value, Mapping):
        raise ValueError(f"full-slide context {field} must be an object")
    return SlideRegionSpec(
        x=int(value.get("x") or 0),
        y=int(value.get("y") or 0),
        w=int(value.get("w") or 0),
        h=int(value.get("h") or 0),
        role=str(value.get("role") or "").strip(),
        render_mode=str(value.get("render_mode") or "").strip(),
    )


def validate_full_slide_design_context(value: Mapping[str, object]) -> FullSlideDesignContextSpec:
    if not isinstance(value, Mapping):
        raise ValueError("full_slide_design_context must be an object")
    return FullSlideDesignContextSpec(
        canvas=_canvas(value.get("canvas"), field="canvas"),
        title_region=_region(value.get("title_region"), field="title_region"),
        body_region=_region(value.get("body_region"), field="body_region"),
        body_export_canvas=_canvas(value.get("body_export_canvas"), field="body_export_canvas"),
        subtitle_render_mode=str(value.get("subtitle_render_mode") or "external_text_layer"),
        version=str(value.get("version") or FULL_SLIDE_CONTEXT_VERSION),
    )


__all__ = [
    "BODY_EXPORT_CANVAS",
    "FULL_SLIDE_CANVAS",
    "FULL_SLIDE_CONTEXT_VERSION",
    "FullSlideDesignContextSpec",
    "SlideRegionSpec",
    "default_full_slide_design_context",
    "validate_full_slide_design_context",
]
