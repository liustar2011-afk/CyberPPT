from __future__ import annotations

from cyberppt.cli import build_parser, _warn_deprecated_compatibility_flag


def test_deprecated_flag_help_is_compatibility_only() -> None:
    help_text = build_parser().format_help()
    parser = build_parser()
    sub = next(a for a in parser._actions if getattr(a, "choices", None))
    final = sub.choices["final-script-pages"].format_help()
    assert "compatibility-only" in final
    assert "selected style reference image" in final
    assert "Style 09 reference image" not in final


def test_deprecation_warning_is_explicit(capsys) -> None:
    _warn_deprecated_compatibility_flag("--allow-script-edit")
    err = capsys.readouterr().err
    assert "deprecated compatibility-only" in err
    assert "does not alter current gates" in err
