"""Build and write schema-validated, traceable page JSON."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import validate
from PIL import Image

from scripts.map_text_coordinates import AffineTransform, MappedTextLine, map_lines
from scripts.models import BBox, ImageInfo, PageSpec, TextLine, TextRun


SLIDE_WIDTH_IN = 13.333333
SLIDE_HEIGHT_IN = 7.5
POINTS_PER_INCH = 72
SCHEMA_PATH = Path(__file__).parents[1] / "assets/schemas/page.schema.json"


@dataclass(frozen=True)
class TraceableTextLine:
    """A visual line plus every coordinate stage used to place it."""

    mapped: MappedTextLine
    image_width: int
    image_height: int

    def to_dict(self) -> dict[str, Any]:
        result = self.mapped.line.to_dict()
        source_bbox = self.mapped.source_bbox.to_dict()
        mapped_bbox = self.mapped.mapped_bbox.to_dict()
        bbox_in = _convert_bbox(
            self.mapped.mapped_bbox,
            self.image_width,
            self.image_height,
            SLIDE_WIDTH_IN,
            SLIDE_HEIGHT_IN,
        )
        result.update(
            {
                "source": {"bbox": source_bbox},
                "mapping": {
                    "transform_id": self.mapped.transform_id,
                    "mapped_bbox": mapped_bbox,
                },
                "automatic_correction": dict(self.mapped.corrections),
                "manual_correction": dict(self.mapped.manual_correction),
                "target": {
                    "bbox_px": mapped_bbox,
                    "bbox_in": bbox_in,
                    "bbox_pt": {
                        key: value * POINTS_PER_INCH for key, value in bbox_in.items()
                    },
                    "inside_safe_area": self.mapped.within_safe_area,
                },
            }
        )
        if self.mapped.container_id is not None:
            result["mapping"]["container_id"] = self.mapped.container_id
        return result


def build_page_spec(
    page_id: str,
    images: Mapping[str, str | Path | ImageInfo],
    lines: Sequence[TextLine],
    transform: AffineTransform,
    containers: Sequence[Mapping[str, Any]],
    line_corrections: Mapping[str, Mapping[str, Any]] | None = None,
) -> PageSpec:
    """Build a page spec using the background's actual pixel dimensions."""

    image_info = {name: _image_info(value) for name, value in images.items()}
    if "background" not in image_info:
        raise ValueError("images must include a background image")
    background = image_info["background"]
    normalized_containers = tuple(_normalize_container(item) for item in containers)
    mapped = map_lines(lines, transform, normalized_containers, line_corrections)
    mapped = [_apply_font_corrections(item) for item in mapped]
    traceable_lines = tuple(
        TraceableTextLine(item, background.width_px, background.height_px)
        for item in mapped
    )
    return PageSpec(
        page_id=page_id,
        width_px=background.width_px,
        height_px=background.height_px,
        images=image_info,
        containers=normalized_containers,
        text_lines=traceable_lines,  # type: ignore[arg-type]
        registration={
            "transform_id": transform.transform_id,
            "matrix": [
                [transform.a, transform.b, transform.c],
                [transform.d, transform.e, transform.f],
                [0.0, 0.0, 1.0],
            ],
        },
        qa={"status": "unverified"},
        manual_corrections=tuple(
            {"line_id": line_id, **dict(correction)}
            for line_id, correction in (line_corrections or {}).items()
            if correction.get("source") in {"manual", "powerpoint"}
        ),
    )


def _apply_font_corrections(mapped: MappedTextLine) -> MappedTextLine:
    scales = [
        correction.get("font_scale", 1.0)
        for correction in (mapped.corrections, mapped.manual_correction)
    ]
    if any(abs(scale - 1.0) > 0.0300001 for scale in scales):
        raise ValueError("font correction exceeds the 3% single-step limit")
    scale = scales[0] * scales[1]
    cumulative = mapped.manual_correction.get("cumulative_font_scale", scale)
    if abs(cumulative - 1.0) > 0.0800001:
        raise ValueError("font correction exceeds the 8% cumulative limit")
    if scale == 1 or not mapped.line.runs:
        return mapped
    runs = tuple(TextRun(run.text, _scaled_style(run.style, scale)) for run in mapped.line.runs)
    return replace(mapped, line=replace(mapped.line, runs=runs))


def _scaled_style(style: Mapping[str, Any], scale: float) -> dict[str, Any]:
    result = dict(style)
    for key in ("font_size", "fontSize", "fontSizePt"):
        if isinstance(result.get(key), (int, float)):
            result[key] = result[key] * scale
    return result


def write_page_spec(spec: PageSpec, output_path: str | Path) -> Path:
    """Validate the complete payload before creating or replacing a JSON file."""

    output = Path(output_path)
    payload = spec.to_dict()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validate(payload, schema)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return output


def _image_info(value: str | Path | ImageInfo) -> ImageInfo:
    if isinstance(value, ImageInfo):
        path = Path(value.path)
    else:
        path = Path(value)
    with Image.open(path) as image:
        width, height = image.size
    return ImageInfo(
        path=str(path),
        width_px=width,
        height_px=height,
        sha256=value.sha256 if isinstance(value, ImageInfo) else None,
    )


def _normalize_container(container: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(container)
    safe_bbox = result.get("safe_bbox")
    if isinstance(safe_bbox, BBox):
        result["safe_bbox"] = safe_bbox.to_dict()
    return result


def _convert_bbox(
    bbox: BBox,
    image_width: int,
    image_height: int,
    target_width: float,
    target_height: float,
) -> dict[str, float]:
    return {
        "x": bbox.x / image_width * target_width,
        "y": bbox.y / image_height * target_height,
        "width": bbox.width / image_width * target_width,
        "height": bbox.height / image_height * target_height,
    }
