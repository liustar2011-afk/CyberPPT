from pathlib import Path

from PIL import Image

from scripts.image_to_editable_svg.roster import build_roster, normalize_full_page, sha256_file


def _image(path: Path) -> Path:
    Image.new("RGB", (80, 40), "white").save(path)
    return path


def test_normalize_frame_preserves_order_hash_and_canvas(tmp_path):
    source = _image(tmp_path / "source.png")
    frame = normalize_full_page(page_number=4, source=source, output_dir=tmp_path / "frames")
    assert frame.page_number == 4
    assert Path(frame.normalized_path).is_file()
    assert frame.source_sha256 == sha256_file(source)
    assert frame.pixel_size == (80, 40)


def test_roster_rejects_ambiguous_page_mapping(tmp_path):
    source = _image(tmp_path / "source.png")
    try:
        build_roster(pages=[(1, source), (1, source)], output_dir=tmp_path / "frames")
    except ValueError as exc:
        assert "ambiguous" in str(exc)
    else:
        raise AssertionError("duplicate page mapping must be rejected")
