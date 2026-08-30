from __future__ import annotations

from pathlib import Path

from cyberppt.stage02_production.manifest_stage import _retain_audited_prior_pairs, _reuse_prior_artifacts


def _pair(path: Path, *, prompt_sha: str) -> dict:
    return {
        "page_number": 4,
        "full": {
            "path": str(path),
            "prompt_sha256": prompt_sha,
        },
    }


def test_prior_audited_full_is_not_reused_when_input_fingerprint_changes(tmp_path: Path) -> None:
    image = tmp_path / "p4.png"
    image.write_bytes(b"image")
    current = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "new",
        "pairs": [_pair(image, prompt_sha="prompt")],
    }
    prior_pair = _pair(image, prompt_sha="prompt")
    prior_pair["full"].update({"generated_prompt_sha256": "prompt", "text_audit": {"valid": True}})
    prior = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "old",
        "pairs": [prior_pair],
    }
    _reuse_prior_artifacts(manifest=current, prior_manifest=prior, production_mode="image-to-editable-svg")
    assert "text_audit" not in current["pairs"][0]["full"]


def test_prior_audited_full_is_not_reused_when_prompt_changes(tmp_path: Path) -> None:
    image = tmp_path / "p4.png"
    image.write_bytes(b"image")
    current = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "same",
        "pairs": [_pair(image, prompt_sha="new-prompt")],
    }
    prior_pair = _pair(image, prompt_sha="old-prompt")
    prior_pair["full"].update({"generated_prompt_sha256": "old-prompt", "text_audit": {"valid": True}})
    prior = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "same",
        "pairs": [prior_pair],
    }
    _reuse_prior_artifacts(manifest=current, prior_manifest=prior, production_mode="image-to-editable-svg")
    assert "text_audit" not in current["pairs"][0]["full"]


def test_partial_recovery_retains_pages_only_for_same_input_identity(tmp_path: Path) -> None:
    image = tmp_path / "p5.png"
    image.write_bytes(b"image")
    prior = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "old",
        "pairs": [{"page_number": 5, "full": {"path": str(image), "text_audit": {"valid": True}}}],
    }
    current = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "new",
        "pairs": [{"page_number": 4, "full": {"path": str(tmp_path / 'p4.png')}}],
    }
    _retain_audited_prior_pairs(manifest=current, prior_manifest=prior)
    assert [pair["page_number"] for pair in current["pairs"]] == [4]


def test_historical_manifests_without_fingerprint_keep_legacy_recovery(tmp_path: Path) -> None:
    passed = tmp_path / "p4.png"
    passed.write_bytes(b"image")
    prior = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "pairs": [{"page_number": 4, "full": {"path": str(passed), "text_audit": {"valid": True}}}],
    }
    current = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "pairs": [{"page_number": 5, "full": {"path": str(tmp_path / 'p5.png')}}],
    }
    _retain_audited_prior_pairs(manifest=current, prior_manifest=prior)
    assert [pair["page_number"] for pair in current["pairs"]] == [4, 5]
