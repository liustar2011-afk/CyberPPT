import json
from pathlib import Path
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).parents[1]
RENDERER = PROJECT_ROOT / "scripts" / "render_ppt.mjs"
BACKGROUND = PROJECT_ROOT / "tests" / "fixtures" / "background.png"
FULL = PROJECT_ROOT / "tests" / "fixtures" / "full.png"
TEXT = PROJECT_ROOT / "tests" / "fixtures" / "text.png"
OCR = PROJECT_ROOT / "tests" / "fixtures" / "ocr.json"
PIPELINE = PROJECT_ROOT / "scripts" / "run_pipeline.py"


def test_renderer_uses_pptxgenjs_instead_of_artifact_tool():
    source = RENDERER.read_text(encoding="utf-8")
    assert 'from "pptxgenjs"' in source
    assert "artifact-tool" not in source


def test_presentation_tools_honor_environment_override(tmp_path, monkeypatch):
    import scripts.run_pipeline as pipeline

    monkeypatch.setenv("THREE_IMAGE_TO_PPT_PRESENTATIONS_TOOLS", str(tmp_path))

    assert pipeline._presentation_tool("render_slides.py") == tmp_path / "render_slides.py"


def test_presentation_python_honors_environment_override(tmp_path, monkeypatch):
    import scripts.run_pipeline as pipeline

    interpreter = tmp_path / "python3"
    monkeypatch.setenv("THREE_IMAGE_TO_PPT_PRESENTATIONS_PYTHON", str(interpreter))

    assert pipeline._presentations_python() == str(interpreter)


def test_pipeline_fails_empty_ocr_with_qa(tmp_path):
    import scripts.run_pipeline as pipeline

    ocr = tmp_path / "ocr.json"
    ocr.write_text('{"lines":[]}', encoding="utf-8")
    registration = tmp_path / "registration.json"
    registration.write_text(
        '{"transform_id":"TF-GLOBAL","matrix":[[1,0,0],[0,1,0]]}',
        encoding="utf-8",
    )
    args = type(
        "Args",
        (),
        {
            "mode": "review",
            "full": FULL,
            "background": BACKGROUND,
            "text": TEXT,
            "ocr": ocr,
            "registration": registration,
            "output_dir": tmp_path,
            "page_id": "page",
        },
    )()

    assert pipeline.run(args) == 1
    qa = json.loads((tmp_path / "qa.json").read_text(encoding="utf-8"))
    assert qa["status"] == "failed"
    assert qa["failed_items"][0]["rule"] == "ocr_line_count"
    assert not (tmp_path / "page.pptx").exists()


def test_pipeline_removes_page_and_writes_standalone_qa_after_overflow(
    tmp_path, monkeypatch
):
    import scripts.run_pipeline as pipeline

    ocr = tmp_path / "ocr.json"
    ocr.write_text(
        '{"lines":[{"text":"Page 004","bbox":[1,1,6,2],"score":0.99}]}',
        encoding="utf-8",
    )
    registration = tmp_path / "registration.json"
    registration.write_text(
        '{"transform_id":"TF-GLOBAL","matrix":[[1,0,0],[0,1,0]]}',
        encoding="utf-8",
    )
    args = type(
        "Args",
        (),
        {
            "mode": "review",
            "full": FULL,
            "background": BACKGROUND,
            "text": TEXT,
            "ocr": ocr,
            "registration": registration,
            "output_dir": tmp_path,
            "page_id": "page",
        },
    )()
    calls = 0

    def fake_run(*unused_args, **unused_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            (tmp_path / "page.pptx").write_bytes(b"pptx")
        elif calls == 2:
            (tmp_path / "slide-1.png").write_bytes(b"png")
        return subprocess.CompletedProcess([], 1 if calls == 3 else 0, "overflow", "")

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)

    assert pipeline.run(args) == 1
    standalone = json.loads((tmp_path / "qa.json").read_text(encoding="utf-8"))
    assert standalone["status"] == "failed"
    assert not (tmp_path / "page.json").exists()
    assert not (tmp_path / "page.pptx").exists()


def test_review_pipeline_produces_json_pptx_render_and_qa(tmp_path):
    ocr = tmp_path / "ocr.json"
    ocr.write_text(
        '{"lines":[{"text":"Page 004","bbox":[1,1,6,2],"score":0.99}]}',
        encoding="utf-8",
    )
    registration = tmp_path / "registration.json"
    registration.write_text(
        '{"transform_id":"TF-GLOBAL","matrix":[[1,0,0],[0,1,0]]}',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(PIPELINE),
            "--mode",
            "review",
            "--full",
            str(FULL),
            "--background",
            str(BACKGROUND),
            "--text",
            str(TEXT),
            "--ocr",
            str(ocr),
            "--registration",
            str(registration),
            "--output-dir",
            str(tmp_path),
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "page.json").exists()
    assert (tmp_path / "page.pptx").exists()
    assert (tmp_path / "slide-1.png").exists()
    assert (tmp_path / "qa.json").exists()
    qa = json.loads((tmp_path / "qa.json").read_text(encoding="utf-8"))
    assert [item["checkpoint"] for item in qa["manual_review_items"]] == [
        "full_image",
        "background_geometry",
        "text_image_and_ocr",
        "ppt_render",
    ]


def test_renderer_creates_one_textbox_per_visual_line(tmp_path, sample_page_json):
    payload = json.loads(sample_page_json.read_text(encoding="utf-8"))
    payload["text_lines"][0]["runs"] = [
        {"text": "103682", "style": {"bold": True, "fontSize": "24pt"}},
        {"text": " 亿千瓦时，", "style": {"color": "#123456", "fontSizePt": 20}},
    ]
    payload["text_lines"][0]["target"] = {
        "bbox_px": {"x": 181, "y": 111, "width": 373, "height": 59},
        "bbox_in": {"x": 1.45, "y": 0.89, "width": 2.98, "height": 0.47},
        "bbox_pt": {"x": 104.4, "y": 64.1, "width": 214.6, "height": 33.9},
        "inside_safe_area": True,
    }
    sample_page_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    expected_line_count = len(payload["text_lines"])
    out = tmp_path / "page.pptx"

    subprocess.run(
        [
            "node",
            str(RENDERER),
            "--json",
            str(sample_page_json),
            "--background",
            str(BACKGROUND),
            "--out",
            str(out),
        ],
        check=True,
    )

    assert out.exists()
    with zipfile.ZipFile(out) as zf:
        slide_xml = zf.read("ppt/slides/slide1.xml").decode("utf-8")
        relationships = zf.read("ppt/slides/_rels/slide1.xml.rels").decode("utf-8")
    assert slide_xml.count("text-page_004-") == expected_line_count
    assert slide_xml.index("<p:pic>") < slide_xml.index("text-page_004-T02-L01")
    assert "103682" in slide_xml and "亿千瓦时" in slide_xml
    assert "Microsoft YaHei" in slide_xml
    assert 'sz="2000"' in slide_xml
    assert "<a:br" not in slide_xml
    assert slide_xml.count("<a:r>") == 2
    assert 'wrap="none"' in slide_xml
    assert 'lIns="0"' in slide_xml and 'tIns="0"' in slide_xml
    assert 'rIns="0"' in slide_xml and 'bIns="0"' in slide_xml
    assert "spAutoFit" not in slide_xml and "normAutofit" not in slide_xml
    assert "image" in relationships


def test_renderer_stretches_non_widescreen_background_without_cropping(
    tmp_path, sample_page_json, image_factory
):
    background = image_factory(tmp_path / "square.png", (8, 8))
    payload = json.loads(sample_page_json.read_text(encoding="utf-8"))
    payload["page"] = {"page_id": "square", "width_px": 8, "height_px": 8}
    payload["text_lines"][0]["bbox"] = {"x": 2, "y": 3, "width": 4, "height": 2}
    sample_page_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "square.pptx"

    subprocess.run(
        [
            "node",
            str(RENDERER),
            "--json",
            str(sample_page_json),
            "--background",
            str(background),
            "--out",
            str(out),
        ],
        check=True,
    )

    with zipfile.ZipFile(out) as zf:
        slide_xml = zf.read("ppt/slides/slide1.xml")
    root = ET.fromstring(slide_xml)
    ns = {
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    }
    assert root.find(".//p:pic/p:blipFill/a:srcRect", ns) is None
    textbox = next(
        shape
        for shape in root.findall(".//p:sp", ns)
        if shape.find("./p:nvSpPr/p:cNvPr", ns).get("name") == "text-square-T02-L01"
    )
    offset = textbox.find("./p:spPr/a:xfrm/a:off", ns)
    extent = textbox.find("./p:spPr/a:xfrm/a:ext", ns)
    emu_per_px = 9525
    assert int(offset.get("x")) == round(2 / 8 * 1280 * emu_per_px)
    assert int(offset.get("y")) == round(3 / 8 * 720 * emu_per_px)
    assert int(extent.get("cx")) == round(4 / 8 * 1280 * emu_per_px)
    assert int(extent.get("cy")) == round(2 / 8 * 720 * emu_per_px)


def _pipeline_args(tmp_path, ocr_payload, registration_payload):
    import scripts.run_pipeline as pipeline
    ocr = tmp_path / "ocr.json"
    ocr.write_text(json.dumps(ocr_payload), encoding="utf-8")
    registration = tmp_path / "registration.json"
    registration.write_text(json.dumps(registration_payload), encoding="utf-8")
    return pipeline, type("Args", (), {
        "mode": "batch", "full": FULL, "background": BACKGROUND, "text": TEXT,
        "ocr": ocr, "registration": registration, "output_dir": tmp_path,
        "page_id": "page",
    })()


def test_pipeline_applies_manual_bbox_and_font_correction_with_traceability(tmp_path, monkeypatch):
    pipeline, args = _pipeline_args(
        tmp_path,
        {"lines": [{"text": "Styled", "bbox": [1, 1, 4, 2], "score": 0.99,
                    "runs": [{"text": "Styled", "font_size": 20, "weight": "bold"}]}]},
        {"transform_id": "TF", "matrix": [[1, 0, 0], [0, 1, 0]],
         "line_corrections": {"L001": {"dx": 1, "dy": 1, "width_delta": 1,
             "height_delta": 1, "font_scale": 0.98, "reason": "fit", "source": "powerpoint"}}},
    )
    calls = 0
    def fake_run(*unused_args, **unused_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1: (tmp_path / "page.pptx").write_bytes(b"pptx")
        elif calls == 2: (tmp_path / "slide-1.png").write_bytes(b"png")
        return subprocess.CompletedProcess([], 0, "ok", "")
    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)

    assert pipeline.run(args) == 0
    page = json.loads((tmp_path / "page.json").read_text(encoding="utf-8"))
    line = page["text_lines"][0]
    assert line["target"]["bbox_px"] == {"x": 2, "y": 2, "width": 5, "height": 3}
    assert line["runs"][0]["style"]["font_size"] == 19.6
    assert line["manual_correction"]["source"] == "powerpoint"
    assert page["manual_corrections"][0]["line_id"] == "L001"


def test_inside_safe_area_false_prevents_pass_and_classifies_geometry():
    import scripts.run_pipeline as pipeline
    from scripts.models import BBox, TextLine
    from scripts.map_text_coordinates import MappedTextLine
    line = TextLine("L1", "G1", 0, "line", BBox(0, 0, 10, 10),
                    ((0, 0), (10, 0), (10, 10), (0, 10)), 0.99)
    bounded = MappedTextLine(line, line.bbox, line.bbox, "TF", within_safe_area=False)
    outside = MappedTextLine(line, line.bbox, BBox(-1, 0, 10, 10), "TF", within_safe_area=False)

    assert pipeline._qa_for_lines([line], [bounded], 100, 100)["status"] == "review"
    failed = pipeline._qa_for_lines([line], [outside], 100, 100)
    assert failed["status"] == "failed"
    assert failed["failed_items"][0]["rule"] == "inside_safe_area"


def test_failed_rerun_removes_only_stale_generated_artifacts(tmp_path):
    pipeline, args = _pipeline_args(
        tmp_path, {"lines": []},
        {"transform_id": "TF", "matrix": [[1, 0, 0], [0, 1, 0]]},
    )
    for name in ("page.json", "page.pptx", "slide-1.png", "rendered-extra.png"):
        (tmp_path / name).write_text("stale", encoding="utf-8")
    unrelated = tmp_path / "notes.png"
    unrelated.write_text("keep", encoding="utf-8")

    assert pipeline.run(args) == 1
    assert not any((tmp_path / name).exists() for name in
                   ("page.json", "page.pptx", "slide-1.png", "rendered-extra.png"))
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_pipeline_rejects_font_correction_over_single_step_limit(tmp_path):
    pipeline, args = _pipeline_args(
        tmp_path, {"lines": [{"text": "line", "bbox": [1, 1, 4, 2]}]},
        {"transform_id": "TF", "matrix": [[1, 0, 0], [0, 1, 0]],
         "line_corrections": {"L001": {"font_scale": 1.04, "source": "manual"}}},
    )

    assert pipeline.run(args) == 1
    qa = json.loads((tmp_path / "qa.json").read_text(encoding="utf-8"))
    assert qa["failed_items"][0]["rule"] == "font_correction_limit"


def test_pipeline_preserves_mixed_runs_through_json_and_pptx(tmp_path):
    ocr = tmp_path / "ocr.json"
    ocr.write_text(json.dumps({"lines": [{
        "text": "Mixed style", "bbox": [1, 1, 6, 2], "score": 0.99,
        "runs": [
            {"text": "Mixed", "font_family": "Arial", "font_size": 16,
             "weight": "bold", "color": "#112233"},
            {"text": " style", "font_family": "Calibri", "font_size": 14,
             "weight": 400, "color": "#445566"},
        ],
    }]}), encoding="utf-8")
    registration = tmp_path / "registration.json"
    registration.write_text(
        '{"transform_id":"TF","matrix":[[1,0,0],[0,1,0]]}', encoding="utf-8"
    )

    result = subprocess.run([
        sys.executable, str(PIPELINE), "--mode", "batch",
        "--full", str(FULL), "--background", str(BACKGROUND), "--text", str(TEXT),
        "--ocr", str(ocr), "--registration", str(registration),
        "--output-dir", str(tmp_path),
    ], text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    page = json.loads((tmp_path / "page.json").read_text(encoding="utf-8"))
    assert [run["text"] for run in page["text_lines"][0]["runs"]] == ["Mixed", " style"]
    with zipfile.ZipFile(tmp_path / "page.pptx") as zf:
        slide_xml = zf.read("ppt/slides/slide1.xml").decode("utf-8")
    assert slide_xml.count("<a:r>") == 2
    assert "Arial" in slide_xml and "Calibri" in slide_xml
    assert "Mixed" in slide_xml and " style" in slide_xml


def test_three_image_pipeline_enriches_page_json_with_style_and_layout(tmp_path, monkeypatch):
    import scripts.run_pipeline as pipeline
    from scripts.font_resolver import resolve_font_face

    size = (320, 100)
    full = Image.new("RGB", size, "#12355B")
    background = Image.new("RGB", size, "#12355B")
    text = Image.new("RGB", size, "#FFFFFF")
    for weight in ("light", "regular", "bold"):
        resolve_font_face("Microsoft YaHei", weight)
    font = ImageFont.truetype(str(resolve_font_face("Microsoft YaHei", "bold")), 34)
    ImageDraw.Draw(full).text((24, 20), "103682", font=font, fill="#FFFFFF")
    ImageDraw.Draw(text).text((24, 20), "103682", font=font, fill="#101010")
    full_path = tmp_path / "full.png"
    background_path = tmp_path / "background.png"
    text_path = tmp_path / "text.png"
    full.save(full_path)
    background.save(background_path)
    text.save(text_path)
    ocr = tmp_path / "ocr.json"
    ocr.write_text(
        json.dumps({"lines": [{"text": "103682", "bbox": [20, 12, 180, 58], "score": 0.99}]}),
        encoding="utf-8",
    )
    registration = tmp_path / "registration.json"
    registration.write_text(
        '{"transform_id":"TF","matrix":[[1,0,0],[0,1,0]]}',
        encoding="utf-8",
    )
    args = type(
        "Args",
        (),
        {
            "mode": "batch",
            "input_mode": "three-image",
            "full": full_path,
            "background": background_path,
            "text": text_path,
            "ocr": ocr,
            "registration": registration,
            "output_dir": tmp_path,
            "page_id": "page-004",
        },
    )()
    calls = 0

    def fake_run(*unused_args, **unused_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            (tmp_path / "page.pptx").write_bytes(b"pptx")
        elif calls == 2:
            (tmp_path / "slide-1.png").write_bytes(b"png")
        return subprocess.CompletedProcess([], 0, "ok", "")

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)

    assert pipeline.run(args) == 0
    page = json.loads((tmp_path / "page.json").read_text(encoding="utf-8"))
    line = page["text_lines"][0]
    assert page["schema_version"] == "1.1"
    assert line["layout"]["align"] in {"left", "center", "right"}
    assert line["runs"][0]["style"]["color"] == "#FFFFFF"
    assert line["runs"][0]["style"]["weight"] == "bold"
    assert line["style_evidence"]["runs"][0]["color"]["method"] == "full_background_delta"
