from pathlib import Path
from unittest.mock import Mock, patch


def test_resolve_yahei_faces_selects_distinct_regular_and_bold_files():
    from scripts.font_resolver import resolve_font_face

    regular = resolve_font_face("Microsoft YaHei", "regular")
    bold = resolve_font_face("Microsoft YaHei", "bold")

    assert regular.is_file()
    assert bold.is_file()
    assert regular != bold


def test_resolver_passes_weight_to_fontconfig(tmp_path):
    from scripts.font_resolver import resolve_font_face

    font = tmp_path / "msyhl.ttc"
    font.write_bytes(b"font")
    completed = Mock(stdout=f"{font}\n")
    resolve_font_face.cache_clear()

    with patch("scripts.font_resolver.subprocess.run", return_value=completed) as run:
        resolved = resolve_font_face("Microsoft YaHei", "light")

    assert resolved == font.resolve()
    assert run.call_args.args[0][-1] == "Microsoft YaHei:weight=light"


def test_resolver_rejects_missing_font_file(tmp_path):
    from scripts.font_resolver import resolve_font_face

    missing = tmp_path / "missing.ttf"
    resolve_font_face.cache_clear()

    with patch(
        "scripts.font_resolver.subprocess.run",
        return_value=Mock(stdout=f"{missing}\n"),
    ):
        try:
            resolve_font_face("Microsoft YaHei", "bold")
        except FileNotFoundError as error:
            assert "Microsoft YaHei bold" in str(error)
        else:
            raise AssertionError("missing font file must be rejected")
