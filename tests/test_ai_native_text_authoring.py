from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image

from scripts.image_to_pptx_runtime.ai_native_text_authoring import (
    prepare_ai_authored_svgs,
    prepare_ai_graphic_text_policy,
)
from scripts.image_to_pptx_runtime.graphic_text_policy import validate_graphic_text_policy


def _manifest(image: Path, *, observations: list[dict[str, object]]) -> dict[str, object]:
    return {
        "pairs": [
            {
                "page_number": 1,
                "full": {
                    "path": str(image),
                    "debug_receipt": {"visible_text": ["标题", "第一行第二行"]},
                    "text_audit": {"ocr_items": observations},
                },
                "graphic_text_policy": {"status": "required"},
            }
        ]
    }


def _box(left: int, top: int, right: int, bottom: int) -> list[list[int]]:
    return [[left, top], [right, top], [right, bottom], [left, bottom]]


def test_ai_policy_uses_script_truth_and_ocr_boxes(tmp_path: Path) -> None:
    image = tmp_path / "full.png"
    Image.new("RGB", (400, 200), "white").save(image)
    manifest = _manifest(
        image,
        observations=[
            {"text": "标题", "confidence": 0.99, "bbox": _box(20, 15, 80, 40)},
            {"text": "第一行", "confidence": 0.99, "bbox": _box(30, 70, 100, 90)},
            {"text": "第二行", "confidence": 0.99, "bbox": _box(30, 98, 100, 118)},
            {"text": "★", "confidence": 0.99, "bbox": _box(300, 10, 315, 25)},
        ],
    )

    report = prepare_ai_graphic_text_policy(manifest, output_dir=tmp_path / "authoring")
    policy = manifest["pairs"][0]["graphic_text_policy"]  # type: ignore[index]

    assert report["status"] == "complete"
    assert policy["status"] == "complete"
    native = [item for item in policy["items"] if item["treatment"] == "native_text"]
    assert {item["text"] for item in native} == {"标题", "第一行第二行"}
    body = next(item for item in native if item["text"] == "第一行第二行")
    assert body["bbox"] == [30, 70, 100, 118]
    assert len(body["layout_lines"]) == 2


def test_ai_policy_fails_for_unbound_readable_ocr(tmp_path: Path) -> None:
    image = tmp_path / "full.png"
    Image.new("RGB", (400, 200), "white").save(image)
    manifest = _manifest(
        image,
        observations=[
            {"text": "标题", "confidence": 0.99, "bbox": _box(20, 15, 80, 40)},
            {"text": "未知文字", "confidence": 0.99, "bbox": _box(100, 80, 190, 105)},
        ],
    )

    report = prepare_ai_graphic_text_policy(manifest, output_dir=tmp_path / "authoring")

    assert report["status"] == "auto_failed"
    assert manifest["pairs"][0]["graphic_text_policy"]["status"] == "auto_failed"  # type: ignore[index]


def test_ai_policy_injects_a_missing_section_title_without_clearance_region(tmp_path: Path) -> None:
    image = tmp_path / "full.png"
    Image.new("RGB", (400, 200), "white").save(image)
    manifest = {
        "pairs": [
            {
                "page_number": 1,
                "full": {
                    "path": str(image),
                    "canvas": "200x100",
                    "debug_receipt": {"visible_text": ["【标题】", "正文"]},
                    "text_audit": {"ocr_items": [{"text": "正文", "confidence": 0.99, "bbox": _box(20, 30, 60, 45)}]},
                },
                "graphic_text_policy": {"status": "required"},
            }
        ]
    }

    report = prepare_ai_graphic_text_policy(manifest, output_dir=tmp_path / "authoring")
    native = manifest["pairs"][0]["graphic_text_policy"]["items"]  # type: ignore[index]
    title = next(item for item in native if item["text"] == "【标题】")
    body = next(item for item in native if item["text"] == "正文")

    assert report["status"] == "complete"
    assert title["source_visible"] is False
    assert title["locator"]["source"] == "ai_injected_safe_zone"
    assert body["bbox"] == [40, 60, 120, 90]


def test_ai_policy_replaces_legacy_complete_policy_without_native_bboxes(tmp_path: Path) -> None:
    image = tmp_path / "full.png"
    Image.new("RGB", (400, 200), "white").save(image)
    manifest = _manifest(
        image,
        observations=[
            {"text": "标题", "confidence": 0.99, "bbox": _box(20, 15, 80, 40)},
            {"text": "第一行", "confidence": 0.99, "bbox": _box(30, 70, 100, 90)},
            {"text": "第二行", "confidence": 0.99, "bbox": _box(30, 98, 100, 118)},
        ],
    )
    manifest["pairs"][0]["graphic_text_policy"] = {  # type: ignore[index]
        "status": "complete",
        "items": [{"id": "legacy", "text": "标题", "treatment": "native_text"}],
    }

    report = prepare_ai_graphic_text_policy(manifest, output_dir=tmp_path / "authoring")
    native = manifest["pairs"][0]["graphic_text_policy"]["items"]  # type: ignore[index]

    assert report["pages"][0]["status"] == "complete"
    assert all(item.get("bbox") for item in native if item["treatment"] == "native_text")


def test_ai_authored_svg_references_clean_base_and_policy_text(tmp_path: Path) -> None:
    image = tmp_path / "full.png"
    Image.new("RGB", (400, 200), "white").save(image)
    manifest = _manifest(
        image,
        observations=[
            {"text": "标题", "confidence": 0.99, "bbox": _box(20, 15, 80, 40)},
            {"text": "第一行", "confidence": 0.99, "bbox": _box(30, 70, 100, 90)},
            {"text": "第二行", "confidence": 0.99, "bbox": _box(30, 98, 100, 118)},
        ],
    )
    prepare_ai_graphic_text_policy(manifest, output_dir=tmp_path / "authoring")
    clean = tmp_path / "authoring" / "assets" / "page_001_clean_base.png"
    clean.parent.mkdir(parents=True)
    Image.new("RGB", (400, 200), "white").save(clean)
    pair = manifest["pairs"][0]  # type: ignore[index]
    pair["clean_base"] = {"status": "complete", "path": str(clean)}

    report = prepare_ai_authored_svgs(manifest, output_dir=tmp_path / "authoring")
    svg = Path(pair["authoring_svg"])
    policy = pair["graphic_text_policy"]

    assert report["status"] == "complete"
    assert svg.is_file()
    assert validate_graphic_text_policy(policy, authored_svg=svg, page_number=1)["valid"] is True
    root = ET.parse(svg).getroot()
    assert any(node.get("data-cyberppt-text-id") == "text-001" for node in root.iter())


def test_ai_authored_svg_fits_font_and_anchors_each_ocr_line(tmp_path: Path) -> None:
    image = tmp_path / "full.png"
    Image.new("RGB", (400, 200), "white").save(image)
    manifest = _manifest(
        image,
        observations=[
            {"text": "标签：正文", "confidence": 0.99, "bbox": _box(30, 70, 110, 90)},
            {"text": "第二行", "confidence": 0.99, "bbox": _box(50, 102, 110, 122)},
        ],
    )
    manifest["pairs"][0]["full"]["debug_receipt"]["visible_text"] = ["标签：正文第二行"]  # type: ignore[index]
    prepare_ai_graphic_text_policy(manifest, output_dir=tmp_path / "authoring")
    clean = tmp_path / "authoring" / "assets" / "page_001_clean_base.png"
    clean.parent.mkdir(parents=True)
    Image.new("RGB", (400, 200), "white").save(clean)
    pair = manifest["pairs"][0]  # type: ignore[index]
    pair["clean_base"] = {"status": "complete", "path": str(clean)}

    prepare_ai_authored_svgs(manifest, output_dir=tmp_path / "authoring")
    root = ET.parse(Path(pair["authoring_svg"])).getroot()
    node = next(node for node in root.iter() if node.get("data-cyberppt-text-id") == "text-001")
    tspans = list(node)

    assert float(node.get("font-size")) == 14.4
    assert tspans[0].get("x") == "30.00"
    assert tspans[0].get("y") == "81.23"
    assert tspans[-1].get("x") == "50.00"
    assert tspans[-1].get("y") == "113.23"
    assert tspans[0].get("fill") == "#12355B"
