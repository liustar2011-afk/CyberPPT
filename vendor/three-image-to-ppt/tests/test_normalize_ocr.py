import json
from pathlib import Path

import pytest

from scripts.models import BBox, TextLine
from scripts.normalize_ocr import normalize_ocr


FIXTURE = Path(__file__).parent / "fixtures" / "ocr.json"


def test_preserves_two_visual_lines_as_two_elements():
    payload = {
        "lines": [
            {"text": "全国统一电力市场", "bbox": [200, 392, 169, 26], "score": 0.99},
            {"text": "建设加快推进", "bbox": [218, 424, 133, 26], "score": 0.98},
        ]
    }

    lines = normalize_ocr(payload, "canonical", 1672, 941)

    assert [line.text for line in lines] == ["全国统一电力市场", "建设加快推进"]
    assert len(lines) == 2
    assert all(isinstance(line, TextLine) for line in lines)
    assert lines[0].bbox == BBox(200, 392, 169, 26)
    assert lines[0].polygon == ((200, 392), (369, 392), (369, 418), (200, 418))
    assert lines[0].runs == ()


@pytest.mark.parametrize("separator", ["\n", "\r"])
def test_rejects_provider_line_containing_newline(separator):
    payload = {
        "lines": [
            {"text": f"第一行{separator}第二行", "bbox": [0, 0, 100, 40], "score": 0.9}
        ]
    }

    with pytest.raises(ValueError, match="visual line"):
        normalize_ocr(payload, "canonical", 1280, 720)


def test_normalizes_all_supported_providers_without_joining_boxes():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    expected = [
        {
            "line_id": "L001",
            "group_id": "G001",
            "line_index": 0,
            "text": "top-left",
            "bbox": BBox(10, 10, 80, 20),
            "polygon": ((10, 10), (90, 10), (90, 30), (10, 30)),
            "confidence": 0.93,
            "runs": (),
        },
        {
            "line_id": "L002",
            "group_id": "G002",
            "line_index": 1,
            "text": "top-right",
            "bbox": BBox(200, 10, 80, 20),
            "polygon": ((200, 10), (280, 10), (280, 30), (200, 30)),
            "confidence": 0.92,
            "runs": (),
        },
        {
            "line_id": "L003",
            "group_id": "G003",
            "line_index": 2,
            "text": "bottom",
            "bbox": BBox(30, 80, 90, 20),
            "polygon": ((30, 80), (120, 80), (120, 100), (30, 100)),
            "confidence": 0.91,
            "runs": (),
        },
    ]

    for provider in ("canonical", "paddleocr-vl", "baidu"):
        lines = normalize_ocr(fixture[provider], provider, 1280, 720)
        assert len(lines) == 3
        for line, fields in zip(lines, expected, strict=True):
            for field, value in fields.items():
                assert getattr(line, field) == value, (provider, field)


@pytest.mark.parametrize(
    ("bbox", "match"),
    [
        ([-1, 10, 20, 20], "bounds"),
        ([10, -1, 20, 20], "bounds"),
        ([10, 10, 0, 20], "positive"),
        ([10, 10, 20, 0], "positive"),
        ([10, 10, -1, 20], "positive"),
        ([10, 10, 20, -1], "positive"),
        ([90, 10, 20, 20], "bounds"),
        ([10, 90, 20, 20], "bounds"),
    ],
)
def test_rejects_bbox_outside_image_or_without_positive_size(bbox, match):
    payload = {"lines": [{"text": "line", "bbox": bbox, "score": 0.9}]}

    with pytest.raises(ValueError, match=match):
        normalize_ocr(payload, "canonical", 100, 100)


def test_rejects_polygon_point_outside_image_even_when_bbox_would_fit():
    payload = {
        "lines": [
            {
                "text": "line",
                "bbox": [10, 10, 20, 20],
                "polygon": [[10, 10], [101, 10], [30, 30], [10, 30]],
                "score": 0.9,
            }
        ]
    }

    with pytest.raises(ValueError, match="polygon.*bounds"):
        normalize_ocr(payload, "canonical", 100, 100)


def test_rejects_unknown_provider():
    with pytest.raises(ValueError, match="provider"):
        normalize_ocr({}, "unknown", 1280, 720)


def test_canonical_preserves_mixed_runs_and_validates_their_text():
    payload = {
        "lines": [{
            "text": "Bold color",
            "bbox": [10, 10, 100, 20],
            "runs": [
                {"text": "Bold", "font_family": "Arial", "font_size": 18,
                 "weight": "bold", "color": "#112233"},
                {"text": " color", "font_family": "Calibri", "font_size": 16,
                 "weight": 400, "color": "#445566"},
            ],
        }]
    }

    line = normalize_ocr(payload, "canonical", 200, 100)[0]

    assert [run.text for run in line.runs] == ["Bold", " color"]
    assert line.runs[0].style == {
        "font_family": "Arial", "font_size": 18,
        "weight": "bold", "color": "#112233",
    }


@pytest.mark.parametrize(
    "runs",
    [
        [{"text": "first\nsecond"}],
        [{"text": "does not match"}],
    ],
)
def test_canonical_rejects_invalid_run_text(runs):
    payload = {"lines": [{"text": "firstsecond", "bbox": [0, 0, 50, 10], "runs": runs}]}

    with pytest.raises(ValueError, match="runs|visual line"):
        normalize_ocr(payload, "canonical", 100, 100)
