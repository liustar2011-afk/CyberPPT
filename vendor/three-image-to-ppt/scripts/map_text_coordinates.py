"""Map OCR visual-line coordinates with an approved global transform."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from scripts.models import BBox, TextLine


@dataclass(frozen=True)
class AffineTransform:
    """A caller-supplied global affine transform.

    V1 deliberately contains no transform estimation or per-region transform
    selection.  ``transform_id`` records the approved registration used.
    """

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 0.0
    e: float = 1.0
    f: float = 0.0
    transform_id: str = "global"

    def apply_bbox(self, bbox: BBox) -> BBox:
        corners = (
            (bbox.x, bbox.y),
            (bbox.x + bbox.width, bbox.y),
            (bbox.x, bbox.y + bbox.height),
            (bbox.x + bbox.width, bbox.y + bbox.height),
        )
        mapped = tuple(
            (self.a * x + self.b * y + self.c, self.d * x + self.e * y + self.f)
            for x, y in corners
        )
        left = round(min(x for x, _ in mapped))
        top = round(min(y for _, y in mapped))
        right = round(max(x for x, _ in mapped))
        bottom = round(max(y for _, y in mapped))
        return BBox(left, top, right - left, bottom - top)


@dataclass(frozen=True)
class MappedTextLine:
    line: TextLine
    source_bbox: BBox
    mapped_bbox: BBox
    transform_id: str
    corrected_bbox: BBox | None = None
    corrections: Mapping[str, Any] = field(default_factory=dict)
    manual_correction: Mapping[str, Any] = field(default_factory=dict)
    container_id: str | None = None
    within_safe_area: bool = False


def check_safe_area(mapped_bbox: BBox, safe_bbox: BBox) -> bool:
    """Return whether ``mapped_bbox`` is fully contained by ``safe_bbox``."""

    return (
        mapped_bbox.x >= safe_bbox.x
        and mapped_bbox.y >= safe_bbox.y
        and mapped_bbox.x + mapped_bbox.width <= safe_bbox.x + safe_bbox.width
        and mapped_bbox.y + mapped_bbox.height <= safe_bbox.y + safe_bbox.height
    )


def map_lines(
    lines: Sequence[TextLine],
    transform: AffineTransform,
    containers: Sequence[Mapping[str, Any]],
    line_corrections: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[MappedTextLine]:
    """Apply one approved global transform and annotate safe-area membership."""

    result: list[MappedTextLine] = []
    line_corrections = line_corrections or {}
    for line in lines:
        correction = dict(line_corrections.get(line.line_id, {}))
        is_manual = correction.get("source") in {"manual", "powerpoint"}
        corrected_bbox = BBox(
            line.bbox.x + correction.get("dx", 0),
            line.bbox.y + correction.get("dy", 0),
            line.bbox.width + correction.get("width_delta", 0),
            line.bbox.height + correction.get("height_delta", 0),
        )
        if corrected_bbox.width <= 0 or corrected_bbox.height <= 0:
            raise ValueError(f"line correction creates invalid geometry for {line.line_id}")
        mapped_bbox = transform.apply_bbox(corrected_bbox)
        container = next(
            (
                candidate
                for candidate in containers
                if check_safe_area(mapped_bbox, _bbox(candidate["safe_bbox"]))
            ),
            None,
        )
        result.append(
            MappedTextLine(
                line=line,
                source_bbox=line.bbox,
                mapped_bbox=mapped_bbox,
                transform_id=transform.transform_id,
                corrected_bbox=corrected_bbox,
                corrections={
                    **(dict(container.get("corrections", {})) if container else {}),
                    **({} if is_manual else correction),
                },
                manual_correction=correction if is_manual else {},
                container_id=_container_id(container) if container else None,
                within_safe_area=container is not None,
            )
        )
    return result


def _bbox(value: BBox | Mapping[str, int]) -> BBox:
    if isinstance(value, BBox):
        return value
    return BBox(value["x"], value["y"], value["width"], value["height"])


def _container_id(container: Mapping[str, Any]) -> str | None:
    value = container.get("container_id", container.get("id"))
    return str(value) if value is not None else None
