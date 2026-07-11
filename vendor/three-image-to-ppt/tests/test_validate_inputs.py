from hashlib import sha256

from PIL import Image

from scripts.validate_inputs import validate_images


def test_rejects_mismatched_dimensions(tmp_path, image_factory):
    full = image_factory(tmp_path / "full.png", (1672, 941))
    bg = image_factory(tmp_path / "background.png", (1280, 720))
    text = image_factory(tmp_path / "text.png", (1672, 941), mode="RGBA")
    report = validate_images(full, bg, text)
    assert report.valid is False
    assert "image dimensions must be identical" in report.errors


def test_accepts_opaque_generated_text_image(tmp_path, image_factory):
    full = image_factory(tmp_path / "full.png", (1672, 941))
    bg = image_factory(tmp_path / "background.png", (1672, 941))
    text = image_factory(tmp_path / "text.png", (1672, 941), mode="RGB")
    report = validate_images(full, bg, text)
    assert report.valid is True
    assert report.errors == ()


def test_accepts_redrawn_text_pixels_without_provenance_check(tmp_path):
    full = tmp_path / "full.png"
    bg = tmp_path / "background.png"
    text = tmp_path / "text.png"
    Image.new("RGB", (100, 60), "white").save(full)
    Image.new("RGB", (100, 60), "white").save(bg)
    layer = Image.new("RGBA", (100, 60), (0, 0, 0, 0))
    layer.putpixel((20, 20), (12, 53, 91, 255))
    layer.save(text)
    report = validate_images(full, bg, text)
    assert report.valid is True
    assert report.errors == ()


def test_accepts_original_pixels_at_same_coordinates_and_reports_hashes(tmp_path):
    full = tmp_path / "full.png"
    bg = tmp_path / "background.png"
    text = tmp_path / "text.png"
    full_image = Image.new("RGB", (20, 20), (240, 240, 240))
    layer = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    for x in range(10):
        color = (10 + x, 50 + x, 90 + x)
        full_image.putpixel((x, 5), color)
        layer.putpixel((x, 5), (*color, 16 if x == 0 else 255))
    full_image.save(full)
    Image.new("RGB", (20, 20), "white").save(bg)
    layer.save(text)

    report = validate_images(full, bg, text)

    assert report.valid is True
    assert (report.width_px, report.height_px) == (20, 20)
    assert report.errors == ()
    assert report.warnings == ()
    assert report.sha256 == {
        "full": sha256(full.read_bytes()).hexdigest(),
        "background": sha256(bg.read_bytes()).hexdigest(),
        "text": sha256(text.read_bytes()).hexdigest(),
    }


def test_accepts_fully_opaque_rgba_text_image(tmp_path):
    full = tmp_path / "full.png"
    bg = tmp_path / "background.png"
    text = tmp_path / "text.png"
    Image.new("RGB", (10, 10), "white").save(full)
    Image.new("RGB", (10, 10), "white").save(bg)
    layer = Image.new("RGBA", (10, 10), (255, 255, 255, 255))
    for x in range(49):
        layer.putpixel((x % 10, x // 10), (0, 0, 0, 0))
    layer.save(text)
    report = validate_images(full, bg, text)
    assert report.valid is True
    assert report.errors == ()


def test_reports_unreadable_image_instead_of_crashing(tmp_path, image_factory):
    full = image_factory(tmp_path / "full.png", (10, 10))
    bg = image_factory(tmp_path / "background.png", (10, 10))
    text = tmp_path / "text.png"
    text.write_text("not an image", encoding="utf-8")

    report = validate_images(full, bg, text)

    assert report.valid is False
    assert "text image is not readable" in report.errors
