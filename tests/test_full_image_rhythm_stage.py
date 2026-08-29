import json
from pathlib import Path

from PIL import Image, ImageDraw

from cyberppt.stage02_production.rhythm_stage import run_full_image_rhythm_stage


def _image(path: Path, side: str) -> Path:
    image = Image.new("RGB", (300, 150), "white")
    draw = ImageDraw.Draw(image)
    if side == "left":
        draw.rectangle((10, 20, 95, 130), fill="black")
    elif side == "right":
        draw.rectangle((205, 20, 290, 130), fill="black")
    else:
        draw.rectangle((105, 20, 195, 130), fill="black")
    image.save(path)
    return path


def _pair(page: int, path: Path, medium: str = "mixed") -> dict:
    return {
        "page_number": page,
        "full": {
            "path": str(path),
            "text_audit": {"valid": True},
            "debug_receipt": {"visual_medium_policy": {"preferred": medium}},
        },
    }


def test_rhythm_stage_writes_contact_sheet_receipt_and_manifest_summary(tmp_path):
    manifest = {
        "pairs": [
            _pair(1, _image(tmp_path / "p1.png", "left")),
            _pair(2, _image(tmp_path / "p2.png", "right")),
        ]
    }
    summary = run_full_image_rhythm_stage(manifest, build_dir=tmp_path / "build")
    assert summary["status"] in {"passed", "passed_with_warnings"}
    assert summary["authority_gate"] == "before_reconstruction_visual_source_binding"
    assert Path(summary["receipt_path"]).is_file()
    assert Path(summary["contact_sheet_path"]).is_file()
    assert len(summary["receipt_sha256"]) == 64
    assert manifest["full_image_deck_rhythm_qa"] == summary
    assert manifest["pairs"][0]["full"]["visual_signature"]["page_number"] == 1
    receipt = json.loads(Path(summary["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["schema"] == "cyberppt.full_image_deck_rhythm_receipt.v1"
    assert len(receipt["signatures"]) == 2


def test_rhythm_stage_persists_blocked_status_before_authority_binding(tmp_path):
    source = _image(tmp_path / "same.png", "center")
    manifest = {"pairs": [_pair(page, source, "business_scene") for page in (1, 2, 3)]}
    summary = run_full_image_rhythm_stage(manifest, build_dir=tmp_path / "build")
    assert summary["status"] == "blocked"
    assert summary["blocker_count"] >= 1
    receipt = json.loads(Path(summary["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["audit"]["status"] == "blocked"
    assert any(item["code"] == "TRIPLE_RHYTHM_REPEAT" for item in receipt["audit"]["findings"])
