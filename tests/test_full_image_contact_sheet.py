from pathlib import Path

import pytest
from PIL import Image

from cyberppt.full_image_rhythm import (
    audited_full_image_entries,
    build_full_image_contact_sheet,
    build_manifest_contact_sheet,
)


def _image(path: Path, value: int) -> Path:
    Image.new("RGB", (200, 100), (value, value, value)).save(path)
    return path


def test_build_contact_sheet_is_page_ordered_and_hashed(tmp_path):
    p2 = _image(tmp_path / "p2.png", 230)
    p1 = _image(tmp_path / "p1.png", 200)
    result = build_full_image_contact_sheet(
        ((2, p2), (1, p1)),
        tmp_path / "qa" / "contact.png",
        thumbnail_size=(100, 50),
        columns=2,
        padding=4,
        label_height=16,
    )
    assert result["page_count"] == 2
    assert [item["page_number"] for item in result["pages"]] == [1, 2]
    assert len(result["sha256"]) == 64
    assert Path(result["path"]).is_file()
    with Image.open(result["path"]) as sheet:
        assert sheet.size == tuple(result["sheet_size"])


def test_manifest_contact_sheet_requires_text_audited_full_images(tmp_path):
    path = _image(tmp_path / "p1.png", 220)
    manifest = {"pairs": [{"page_number": 1, "full": {"path": str(path), "text_audit": {"valid": True}}}]}
    entries = audited_full_image_entries(manifest)
    assert entries == ((1, path),)
    result = build_manifest_contact_sheet(manifest, tmp_path / "contact.png")
    assert result["page_count"] == 1


def test_manifest_contact_sheet_rejects_unreviewed_page(tmp_path):
    path = _image(tmp_path / "p1.png", 220)
    manifest = {"pairs": [{"page_number": 1, "full": {"path": str(path), "text_audit": {"valid": False}}}]}
    with pytest.raises(ValueError, match="has not passed text audit"):
        audited_full_image_entries(manifest)
