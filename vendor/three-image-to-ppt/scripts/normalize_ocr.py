"""Normalize supported OCR responses into independent visual text lines."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from scripts.models import BBox, TextLine, TextRun


_PROVIDERS = {"canonical", "paddleocr-vl", "baidu"}


def normalize_ocr(
    payload: Mapping[str, Any],
    provider: str,
    image_width: int,
    image_height: int,
) -> list[TextLine]:
    """Return one ``TextLine`` for every provider-reported visual line.

    ``image_width`` and ``image_height`` are part of the stable normalization
    interface. Coordinates remain in provider image pixels and are not scaled.
    """
    if provider not in _PROVIDERS:
        raise ValueError(f"unsupported OCR provider: {provider}")
    if image_width <= 0 or image_height <= 0:
        raise ValueError("image dimensions must be positive")

    adapters = {
        "canonical": _canonical_lines,
        "paddleocr-vl": _paddle_lines,
        "baidu": _baidu_lines,
    }
    raw_lines = list(adapters[provider](payload))
    raw_lines.sort(key=lambda line: _center_sort_key(line[1]))

    result: list[TextLine] = []
    for index, (text, polygon, confidence, runs) in enumerate(raw_lines):
        _validate_visual_line(text)
        bbox = _bbox_from_polygon(polygon)
        _validate_geometry(bbox, polygon, image_width, image_height)
        number = index + 1
        result.append(
            TextLine(
                line_id=f"L{number:03d}",
                group_id=f"G{number:03d}",
                line_index=index,
                text=text,
                polygon=polygon,
                bbox=bbox,
                confidence=confidence,
                runs=runs,
            )
        )
    return result


RawLine = tuple[str, tuple[tuple[int, int], ...], float, tuple[TextRun, ...]]


def _canonical_lines(payload: Mapping[str, Any]) -> Iterable[RawLine]:
    for line in payload.get("lines", ()):
        bbox = line.get("bbox")
        polygon = (
            _polygon(line.get("polygon"))
            if line.get("polygon")
            else _polygon_from_bbox(bbox)
        )
        confidence = line.get("score", line.get("confidence", 1.0))
        text = str(line["text"])
        runs = _canonical_runs(line.get("runs", ()), text)
        yield text, polygon, _confidence(confidence), runs


def _paddle_lines(payload: Mapping[str, Any]) -> Iterable[RawLine]:
    data = payload.get("res", payload)
    if "parsing_res_list" in data:
        for line in data["parsing_res_list"]:
            bbox = line.get("block_bbox", line.get("bbox"))
            polygon = (
                _polygon(line.get("polygon"))
                if line.get("polygon")
                else _polygon_from_xyxy(bbox)
            )
            text = line.get("block_content", line.get("text", ""))
            yield str(text), polygon, _confidence(line.get("score", 1.0)), ()
        return

    texts = data.get("rec_texts", ())
    polygons = data.get("rec_polys")
    boxes = data.get("rec_boxes")
    scores = data.get("rec_scores", [1.0] * len(texts))
    for index, text in enumerate(texts):
        polygon = (
            _polygon(polygons[index])
            if polygons is not None
            else _polygon_from_xyxy(boxes[index])
        )
        yield str(text), polygon, _confidence(scores[index]), ()


def _baidu_lines(payload: Mapping[str, Any]) -> Iterable[RawLine]:
    for line in payload.get("words_result", ()):
        location = line["location"]
        polygon = _polygon_from_bbox(location)
        probability = line.get("probability", {})
        confidence = probability.get("average", line.get("confidence", 1.0))
        yield str(line["words"]), polygon, _confidence(confidence), ()


def _canonical_runs(values: Sequence[Mapping[str, Any]], line_text: str) -> tuple[TextRun, ...]:
    runs = tuple(
        TextRun(
            text=str(value["text"]),
            style={key: item for key, item in value.items() if key != "text"},
        )
        for value in values
    )
    if runs and "".join(run.text for run in runs) != line_text:
        raise ValueError("concatenated runs must equal line text")
    return runs


def _polygon(value: Sequence[Sequence[Any]]) -> tuple[tuple[int, int], ...]:
    return tuple((int(point[0]), int(point[1])) for point in value)


def _polygon_from_bbox(
    value: Mapping[str, Any] | Sequence[Any],
) -> tuple[tuple[int, int], ...]:
    if isinstance(value, Mapping):
        x, y = value.get("x", value.get("left")), value.get("y", value.get("top"))
        width, height = value["width"], value["height"]
    else:
        x, y, width, height = value
    x, y, width, height = int(x), int(y), int(width), int(height)
    if width <= 0 or height <= 0:
        raise ValueError("OCR bbox width and height must be positive")
    return ((x, y), (x + width, y), (x + width, y + height), (x, y + height))


def _polygon_from_xyxy(value: Sequence[Any]) -> tuple[tuple[int, int], ...]:
    x1, y1, x2, y2 = (int(coordinate) for coordinate in value)
    if x2 <= x1 or y2 <= y1:
        raise ValueError("OCR bbox width and height must be positive")
    return ((x1, y1), (x2, y1), (x2, y2), (x1, y2))


def _bbox_from_polygon(polygon: tuple[tuple[int, int], ...]) -> BBox:
    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]
    return BBox(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _center_sort_key(polygon: tuple[tuple[int, int], ...]) -> tuple[float, float]:
    bbox = _bbox_from_polygon(polygon)
    return (bbox.y + bbox.height / 2, bbox.x + bbox.width / 2)


def _confidence(value: Any) -> float:
    return float(value)


def _validate_visual_line(text: str) -> None:
    if "\n" in text or "\r" in text:
        raise ValueError("visual line text must not contain CR or LF")


def _validate_geometry(
    bbox: BBox,
    polygon: tuple[tuple[int, int], ...],
    image_width: int,
    image_height: int,
) -> None:
    if any(
        x < 0 or y < 0 or x > image_width or y > image_height
        for x, y in polygon
    ):
        raise ValueError("OCR polygon must be within image bounds")
    if bbox.width <= 0 or bbox.height <= 0:
        raise ValueError("OCR bbox width and height must be positive")
    if (
        bbox.x < 0
        or bbox.y < 0
        or bbox.x + bbox.width > image_width
        or bbox.y + bbox.height > image_height
    ):
        raise ValueError("OCR bbox must be within image bounds")
