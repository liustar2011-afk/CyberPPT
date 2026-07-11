from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path

from jsonschema import ValidationError, validate
import pytest


SCHEMA = Path(__file__).parents[1] / "assets/schemas/page.schema.json"
TEXT_LINE_SCHEMA = Path(__file__).parents[1] / "assets/schemas/text-line.schema.json"


def test_page_schema_rejects_newline_in_text():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    payload = {
        "schema_version": "1.0",
        "page": {"page_id": "page_004", "width_px": 1672, "height_px": 941},
        "images": {},
        "regions": [],
        "containers": [],
        "text_lines": [{"line_id": "L1", "text": "第一行\n第二行"}],
        "registration": {},
        "qa": {},
        "manual_corrections": [],
    }
    with pytest.raises(ValidationError):
        validate(payload, schema)


@pytest.mark.parametrize("schema_path", [SCHEMA, TEXT_LINE_SCHEMA])
@pytest.mark.parametrize("run_text", ["first\nsecond", "first\rsecond"])
def test_schemas_reject_newline_in_text_run(schema_path, run_text):
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    line = {
        "line_id": "L1",
        "text": "firstsecond",
        "runs": [{"text": run_text, "style": {}}],
    }
    payload = line
    if schema_path == SCHEMA:
        payload = {
            "schema_version": "1.0",
            "page": {"page_id": "page_004", "width_px": 1672, "height_px": 941},
            "images": {},
            "regions": [],
            "containers": [],
            "text_lines": [line],
            "registration": {},
            "qa": {},
            "manual_corrections": [],
        }

    with pytest.raises(ValidationError):
        validate(payload, schema)


def test_sample_page_is_schema_valid(sample_page):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    payload = sample_page.to_dict()

    validate(payload, schema)
    assert payload["registration"] == {
        "matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    }
    assert payload["regions"] == []
    assert payload["containers"] == []
    assert payload["manual_corrections"] == []
    assert payload["qa"]["status"] == "unverified"


@pytest.mark.parametrize("text", ["first\nsecond", "first\rsecond"])
def test_text_line_rejects_newline(text):
    from scripts.models import BBox, TextLine

    with pytest.raises(ValueError, match="visual line text must not contain newline"):
        TextLine(
            line_id="L1",
            group_id="G1",
            line_index=0,
            text=text,
            bbox=BBox(0, 0, 10, 10),
            polygon=((0, 0), (10, 0), (10, 10), (0, 10)),
            confidence=1.0,
        )


@pytest.mark.parametrize("text", ["first\nsecond", "first\rsecond"])
def test_text_run_rejects_newline(text):
    from scripts.models import TextRun

    with pytest.raises(ValueError, match="visual line text must not contain newline"):
        TextRun(text=text)


def test_models_are_frozen(sample_page):
    with pytest.raises(FrozenInstanceError):
        sample_page.page_id = "other"


def test_load_page_spec_round_trips(sample_page, sample_page_json):
    from scripts.models import load_page_spec

    assert load_page_spec(sample_page_json) == sample_page


def test_page_json_keeps_source_mapped_and_target_coordinates(tmp_path, sample_page):
    from scripts.build_page_json import build_page_spec, write_page_spec
    from scripts.map_text_coordinates import AffineTransform

    fixture_dir = Path(__file__).parent / "fixtures"
    spec = build_page_spec(
        sample_page.page_id,
        {
            "full": fixture_dir / "full.png",
            "text": fixture_dir / "text.png",
            "background": fixture_dir / "background.png",
        },
        sample_page.text_lines,
        AffineTransform(c=5, f=-2, transform_id="approved-global"),
        [
            {
                "container_id": "body",
                "safe_bbox": {"x": 0, "y": 0, "width": 1672, "height": 941},
                "corrections": {"font_scale": 0.98},
            }
        ],
    )

    out = write_page_spec(spec, tmp_path / "page.json")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["page"]["width_px"] == 8
    assert payload["page"]["height_px"] == 8
    line = payload["text_lines"][0]
    assert line["source"]["bbox"] == {
        "x": 181,
        "y": 111,
        "width": 373,
        "height": 59,
    }
    assert line["mapping"]["mapped_bbox"] == {
        "x": 186,
        "y": 109,
        "width": 373,
        "height": 59,
    }
    assert line["automatic_correction"] == {"font_scale": 0.98}
    assert set(line["target"]) >= {
        "bbox_px",
        "bbox_in",
        "bbox_pt",
        "inside_safe_area",
    }
    assert line["target"]["bbox_px"] == line["mapping"]["mapped_bbox"]
    assert line["target"]["bbox_in"]["x"] == pytest.approx(186 / 8 * 13.333333)
    assert line["target"]["bbox_in"]["y"] == pytest.approx(109 / 8 * 7.5)
    assert line["target"]["bbox_pt"]["x"] == pytest.approx(
        line["target"]["bbox_in"]["x"] * 72
    )
    assert line["target"]["inside_safe_area"] is True


def test_write_page_spec_validates_before_replacing_output(tmp_path, sample_page):
    from scripts.build_page_json import write_page_spec

    output = tmp_path / "page.json"
    output.write_text("existing", encoding="utf-8")

    with pytest.raises(ValidationError):
        write_page_spec(replace(sample_page, schema_version="invalid"), output)

    assert output.read_text(encoding="utf-8") == "existing"
