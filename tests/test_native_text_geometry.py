import json
from pathlib import Path

from scripts.image_to_pptx_runtime.native_text_geometry import (
    analyze_native_text_geometry,
    write_native_text_geometry_receipt,
)


def _policy(items: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": "cyberppt.image_to_pptx.graphic_text_policy.v1",
        "status": "complete",
        "empty_container_check": "passed",
        "items": items,
    }


def _svg(tmp_path: Path, body: str, *, locked: bool = False) -> Path:
    path = tmp_path / "page.svg"
    lock = ' data-cyberppt-native-text-style="locked"' if locked else ""
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200"{lock}>{body}</svg>',
        encoding="utf-8",
    )
    return path


def test_unique_text_match_reports_geometry_without_editing_svg(tmp_path: Path) -> None:
    svg = _svg(tmp_path, '<text x="40" y="74" font-size="20">标题</text>')
    original = svg.read_bytes()
    report = analyze_native_text_geometry(
        _policy([{"id": "title", "text": "标题", "treatment": "native_text", "bbox": [40, 50, 140, 80]}]),
        authored_svg=svg,
        page_number=1,
    )

    item = report["items"][0]
    assert report["status"] == "complete"
    assert item["match_method"] == "unique_text"
    assert item["svg_x"] == 40.0
    assert item["font_size"] == 20.0
    assert item["action"] == "pass"
    assert svg.read_bytes() == original


def test_explicit_id_wins_when_text_is_duplicated(tmp_path: Path) -> None:
    svg = _svg(
        tmp_path,
        '<text data-cyberppt-text-id="second" x="100" y="80" font-size="20">重复</text>'
        '<text data-cyberppt-text-id="first" x="20" y="80" font-size="20">重复</text>',
    )
    report = analyze_native_text_geometry(
        _policy(
            [
                {"id": "first", "text": "重复", "treatment": "native_text", "bbox": [20, 55, 60, 85]},
                {"id": "second", "text": "重复", "treatment": "native_text", "bbox": [100, 55, 140, 85]},
            ]
        ),
        authored_svg=svg,
        page_number=1,
    )
    assert [item["match_method"] for item in report["items"]] == ["explicit_id", "explicit_id"]
    assert [item["svg_x"] for item in report["items"]] == [20.0, 100.0]


def test_missing_bbox_blocks_geometry(tmp_path: Path) -> None:
    svg = _svg(tmp_path, '<text x="10" y="30" font-size="16">缺少框</text>')
    report = analyze_native_text_geometry(
        _policy([{"id": "missing", "text": "缺少框", "treatment": "native_text"}]),
        authored_svg=svg,
        page_number=1,
    )
    assert report["valid"] is False
    assert report["review_required"] is True
    assert report["items"][0]["action"] == "missing_bbox"


def test_duplicate_text_without_id_is_ambiguous(tmp_path: Path) -> None:
    svg = _svg(
        tmp_path,
        '<text x="10" y="30">重复</text><text x="100" y="30">重复</text>',
    )
    report = analyze_native_text_geometry(
        _policy([{"id": "ambiguous", "text": "重复", "treatment": "native_text", "bbox": [10, 10, 50, 35]}]),
        authored_svg=svg,
        page_number=1,
    )
    assert report["items"][0]["match_method"] == "none"
    assert any("ambiguous" in warning for warning in report["warnings"])


def test_multiline_text_reports_line_metrics(tmp_path: Path) -> None:
    svg = _svg(
        tmp_path,
        '<text x="20" y="60" font-size="20"><tspan>第一行</tspan><tspan x="20" dy="28">第二行</tspan></text>',
    )
    report = analyze_native_text_geometry(
        _policy([{"id": "body", "text": "第一行 第二行", "treatment": "native_text", "bbox": [20, 40, 180, 100]}]),
        authored_svg=svg,
        page_number=1,
    )
    item = report["items"][0]
    assert item["line_count"] == 2
    assert item["line_step"] == 28.0


def test_multiline_text_reports_absolute_tspan_baselines(tmp_path: Path) -> None:
    svg = _svg(
        tmp_path,
        '<text x="20" y="60" font-size="20"><tspan x="20" y="60">第一行</tspan><tspan x="30" y="88">第二行</tspan></text>',
    )
    report = analyze_native_text_geometry(
        _policy([{"id": "body", "text": "第一行 第二行", "treatment": "native_text", "bbox": [20, 40, 180, 100]}]),
        authored_svg=svg,
        page_number=1,
    )
    item = report["items"][0]

    assert item["line_count"] == 2
    assert item["line_step"] == 28.0


def test_tspan_horizontal_region_jump_blocks_geometry(tmp_path: Path) -> None:
    svg = _svg(
        tmp_path,
        '<text x="20" y="60" font-size="20"><tspan x="20" y="60">第一行</tspan>'
        '<tspan x="300" y="88">错误跳列</tspan></text>',
    )
    report = analyze_native_text_geometry(
        _policy([{"id": "body", "text": "第一行 错误跳列", "treatment": "native_text", "bbox": [20, 40, 380, 100]}]),
        authored_svg=svg,
        page_number=1,
    )
    assert report["valid"] is False
    assert report["items"][0]["intra_text_x_span"] == 280.0
    assert "tspan x positions jump across visual regions" in report["items"][0]["structural_issues"]


def test_tspan_vertical_region_jump_blocks_geometry(tmp_path: Path) -> None:
    svg = _svg(
        tmp_path,
        '<text x="20" y="60" font-size="20"><tspan x="20" y="60">正文</tspan>'
        '<tspan x="20" y="180">错误跳区</tspan></text>',
    )
    report = analyze_native_text_geometry(
        _policy([{"id": "body", "text": "正文 错误跳区", "treatment": "native_text", "bbox": [20, 40, 180, 195]}]),
        authored_svg=svg,
        page_number=1,
    )
    assert report["valid"] is False
    assert report["items"][0]["max_baseline_step"] == 120.0
    assert "tspan baselines jump across visual regions" in report["items"][0]["structural_issues"]


def test_locked_svg_is_fully_checked(tmp_path: Path) -> None:
    svg = _svg(tmp_path, '<text x="10" y="30" font-size="16">锁定</text>', locked=True)
    report = analyze_native_text_geometry(
        _policy([{"id": "locked", "text": "锁定", "treatment": "native_text", "bbox": [10, 10, 50, 35]}]),
        authored_svg=svg,
        page_number=1,
    )
    assert report["status"] == "checked_locked"
    assert len(report["items"]) == 1
    assert report["items"][0]["final_font_pt"] == 12.0


def test_template_scale_enforces_final_font_floor(tmp_path: Path) -> None:
    svg = _svg(tmp_path, '<text x="10" y="30" font-size="12">过小</text>', locked=True)
    report = analyze_native_text_geometry(
        _policy([{"id": "small", "text": "过小", "treatment": "native_text", "bbox": [10, 15, 50, 35]}]),
        authored_svg=svg,
        page_number=1,
        body_scale=0.5,
    )
    assert report["valid"] is False
    assert report["items"][0]["final_font_pt"] == 4.5
    assert "below 12.00pt floor" in report["warnings"][0]


def test_exact_source_mode_preserves_source_sized_multiline_type(tmp_path: Path) -> None:
    svg = _svg(
        tmp_path,
        '<text data-cyberppt-text-id="body" x="40" y="77" font-size="17">'
        '<tspan x="40" y="77">第一行</tspan><tspan x="40" y="100">第二行</tspan></text>',
        locked=True,
    )
    policy = _policy([
        {"id": "body", "text": "第一行第二行", "role": "body", "treatment": "native_text", "bbox": [40, 60, 120, 105]}
    ])
    policy["fidelity_mode"] = "exact_source_image"

    report = analyze_native_text_geometry(
        policy,
        authored_svg=svg,
        page_number=1,
        body_scale=0.5,
    )

    assert report["valid"] is True
    assert report["items"][0]["exact_source_fidelity"] is True


def test_geometry_receipt_is_machine_readable(tmp_path: Path) -> None:
    svg = _svg(tmp_path, '<text x="10" y="30">回执</text>')
    report = analyze_native_text_geometry(
        _policy([{"id": "receipt", "text": "回执", "treatment": "native_text", "bbox": [10, 10, 50, 35]}]),
        authored_svg=svg,
        page_number=1,
    )
    output = write_native_text_geometry_receipt([report], tmp_path / "analysis" / "native_text_geometry_qa.json")
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "cyberppt.native_text_geometry_qa.v1"
    assert payload["qa_only"] is True
