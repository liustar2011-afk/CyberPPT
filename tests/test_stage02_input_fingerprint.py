from __future__ import annotations

from pathlib import Path

from cyberppt.stage02_production.preflight import build_id_for, input_fingerprint_for


def _inputs() -> dict[str, object]:
    return {
        "source_script_sha256": "script",
        "script_input_sha256": "intake",
        "visual_spec_sha256": "visual",
        "style_lock_sha256": "style-lock",
        "resolved_style_contract_sha256": "style-contract-a",
        "selected_pages": (1, 2, 3),
        "production_mode": "image-to-editable-svg",
        "assembly_mode": "editable",
        "image_model": "gpt-image-2",
        "image_quality": "high",
        "prompt_enrich": "off",
        "no_style_reference": False,
        "skip_image_text_audit": False,
        "allow_prompt_edit": False,
        "prompt_overrides_sha256": "",
        "autonomous_contract_sha256": "",
    }


def test_input_fingerprint_is_deterministic() -> None:
    first = input_fingerprint_for(**_inputs())
    second = input_fingerprint_for(**_inputs())

    assert first == second
    assert len(first) == 64


def test_input_fingerprint_changes_with_frozen_style_contract() -> None:
    first_inputs = _inputs()
    second_inputs = _inputs()
    second_inputs["resolved_style_contract_sha256"] = "style-contract-b"

    assert input_fingerprint_for(**first_inputs) != input_fingerprint_for(**second_inputs)


def test_input_fingerprint_changes_with_output_semantics() -> None:
    first_inputs = _inputs()
    second_inputs = _inputs()
    second_inputs["assembly_mode"] = "image"

    assert input_fingerprint_for(**first_inputs) != input_fingerprint_for(**second_inputs)


def test_default_build_id_uses_input_fingerprint_digest(tmp_path: Path) -> None:
    script = tmp_path / "final-script.md"
    style_lock = tmp_path / "style.json"
    script.write_text("script", encoding="utf-8")
    style_lock.write_text("{}", encoding="utf-8")
    fingerprint = "abcdef0123456789" * 4

    build_id = build_id_for(
        script=script,
        pages_raw="1-3",
        production_mode="image-to-editable-svg",
        style_lock=style_lock,
        input_fingerprint=fingerprint,
    )

    assert build_id.endswith("-" + fingerprint[:10])


def test_requested_build_id_is_preserved(tmp_path: Path) -> None:
    script = tmp_path / "final-script.md"
    style_lock = tmp_path / "style.json"
    script.write_text("script", encoding="utf-8")
    style_lock.write_text("{}", encoding="utf-8")

    assert build_id_for(
        script=script,
        pages_raw="1",
        production_mode="image-to-editable-svg",
        style_lock=style_lock,
        requested="resume-me",
        input_fingerprint="f" * 64,
    ) == "resume-me"
