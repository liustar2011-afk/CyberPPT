"""Shared immutable models for the three-image page representation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class BBox:
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class TextRun:
    text: str
    style: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if "\n" in self.text or "\r" in self.text:
            raise ValueError("visual line text must not contain newline")

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "style": dict(self.style)}


@dataclass(frozen=True)
class TextLine:
    line_id: str
    group_id: str
    line_index: int
    text: str
    bbox: BBox
    polygon: tuple[tuple[int, int], ...]
    confidence: float
    runs: tuple[TextRun, ...] = ()
    layout: Mapping[str, Any] = field(default_factory=dict)
    style_evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if "\n" in self.text or "\r" in self.text:
            raise ValueError("visual line text must not contain newline")
        if self.runs and "".join(run.text for run in self.runs) != self.text:
            raise ValueError("concatenated run texts must equal visual line text")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "line_id": self.line_id,
            "group_id": self.group_id,
            "line_index": self.line_index,
            "text": self.text,
            "bbox": self.bbox.to_dict(),
            "polygon": [list(point) for point in self.polygon],
            "confidence": self.confidence,
        }
        if self.runs:
            result["runs"] = [run.to_dict() for run in self.runs]
        if self.layout:
            result["layout"] = dict(self.layout)
        if self.style_evidence:
            result["style_evidence"] = dict(self.style_evidence)
        return result


@dataclass(frozen=True)
class ImageInfo:
    path: str
    width_px: int
    height_px: int
    sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "path": self.path,
            "width_px": self.width_px,
            "height_px": self.height_px,
        }
        if self.sha256 is not None:
            result["sha256"] = self.sha256
        return result


@dataclass(frozen=True)
class PageSpec:
    page_id: str
    width_px: int
    height_px: int
    images: Mapping[str, ImageInfo] = field(default_factory=dict)
    regions: tuple[Mapping[str, Any], ...] = ()
    containers: tuple[Mapping[str, Any], ...] = ()
    text_lines: tuple[TextLine, ...] = ()
    registration: Mapping[str, Any] = field(default_factory=dict)
    qa: Mapping[str, Any] = field(default_factory=dict)
    manual_corrections: tuple[Mapping[str, Any], ...] = ()
    schema_version: str = "1.0"

    @classmethod
    def sample(
        cls,
        page_id: str,
        width_px: int,
        height_px: int,
        lines: Sequence[TextLine],
    ) -> PageSpec:
        return cls(
            page_id=page_id,
            width_px=width_px,
            height_px=height_px,
            text_lines=tuple(lines),
            registration={
                "matrix": [
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0],
                ]
            },
            qa={"status": "unverified"},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "page": {
                "page_id": self.page_id,
                "width_px": self.width_px,
                "height_px": self.height_px,
            },
            "images": {key: value.to_dict() for key, value in self.images.items()},
            "regions": [dict(region) for region in self.regions],
            "containers": [dict(container) for container in self.containers],
            "text_lines": [line.to_dict() for line in self.text_lines],
            "registration": dict(self.registration),
            "qa": dict(self.qa),
            "manual_corrections": [dict(item) for item in self.manual_corrections],
        }


def load_page_spec(path: str | Path) -> PageSpec:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    page = payload["page"]
    images = {
        key: ImageInfo(
            path=value["path"],
            width_px=value["width_px"],
            height_px=value["height_px"],
            sha256=value.get("sha256"),
        )
        for key, value in payload["images"].items()
    }
    lines = tuple(_text_line_from_dict(line) for line in payload["text_lines"])
    return PageSpec(
        page_id=page["page_id"],
        width_px=page["width_px"],
        height_px=page["height_px"],
        images=images,
        regions=tuple(payload["regions"]),
        containers=tuple(payload["containers"]),
        text_lines=lines,
        registration=payload["registration"],
        qa=payload["qa"],
        manual_corrections=tuple(payload["manual_corrections"]),
        schema_version=payload["schema_version"],
    )


def _text_line_from_dict(value: Mapping[str, Any]) -> TextLine:
    bbox = value["bbox"]
    return TextLine(
        line_id=value["line_id"],
        group_id=value["group_id"],
        line_index=value["line_index"],
        text=value["text"],
        bbox=BBox(bbox["x"], bbox["y"], bbox["width"], bbox["height"]),
        polygon=tuple(tuple(point) for point in value["polygon"]),
        confidence=value["confidence"],
        runs=tuple(
            TextRun(text=run["text"], style=run.get("style", {}))
            for run in value.get("runs", ())
        ),
        layout=value.get("layout", {}),
        style_evidence=value.get("style_evidence", {}),
    )
