from __future__ import annotations

from pathlib import Path

from cyberppt.stage02_production.manifest_stage import (
    _retain_audited_prior_pairs,
    _reuse_prior_artifacts,
)


def _pair(page: int, image: Path, prompt_sha: str) -> dict[str, object]:
    return {
        "page_number": page,
        "full": {
            "path": str(image),
            "prompt_sha256": prompt_sha,
            "status": "Pending",
        },
    }


def _prior_pair(page: int, image: Path, generated_prompt_sha: str, authored: Path) -> dict[str, object]:
    return {
        "page_number": page,
        "authoring_svg": str(authored),
        "clean_base": {"status": "complete", "path": str(image.with_name("clean.png"))},
        "graphic_text_policy": {"status": "complete", "empty_container_check": "passed"},
        "quick_page_checkpoint": {"status": "passed"},
        "full": {
            "path": str(image),
            "status": "Generated",
            "generated_prompt_sha256": generated_prompt_sha,
            "text_audit": {"valid": True},
        },
    }


def test_reuse_prior_artifacts_requires_page_prompt_match(tmp_path: Path) -> None:
    image = tmp_path / "page.png"
    authored = tmp_path / "page.svg"
    image.write_bytes(b"png")
    authored.write_text("<svg/>", encoding="utf-8")
    manifest = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "resolved_style_contract_sha256": "style",
        "pairs": [_pair(1, image, "new-prompt")],
    }
    prior = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "resolved_style_contract_sha256": "style",
        "pairs": [_prior_pair(1, image, "old-prompt", authored)],
    }

    _reuse_prior_artifacts(
        manifest=manifest,
        prior_manifest=prior,
        production_mode="image-to-editable-svg",
    )

    current = manifest["pairs"][0]
    assert "authoring_svg" not in current
    assert "clean_base" not in current
    assert "quick_page_checkpoint" not in current
    assert "text_audit" not in current["full"]


def test_reuse_prior_artifacts_keeps_prompt_bound_page(tmp_path: Path) -> None:
    image = tmp_path / "page.png"
    authored = tmp_path / "page.svg"
    image.write_bytes(b"png")
    authored.write_text("<svg/>", encoding="utf-8")
    manifest = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "resolved_style_contract_sha256": "style",
        "pairs": [_pair(1, image, "same-prompt")],
    }
    prior = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "resolved_style_contract_sha256": "style",
        "pairs": [_prior_pair(1, image, "same-prompt", authored)],
    }

    _reuse_prior_artifacts(
        manifest=manifest,
        prior_manifest=prior,
        production_mode="image-to-editable-svg",
    )

    current = manifest["pairs"][0]
    assert current["authoring_svg"] == str(authored)
    assert current["quick_page_checkpoint"]["status"] == "passed"
    assert current["full"]["text_audit"]["valid"] is True
    assert current["full"]["generated_prompt_sha256"] == "same-prompt"


def test_partial_recovery_does_not_retain_pages_across_style_contract_change(tmp_path: Path) -> None:
    image1 = tmp_path / "p1.png"
    image2 = tmp_path / "p2.png"
    image1.write_bytes(b"1")
    image2.write_bytes(b"2")
    manifest = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "resolved_style_contract_sha256": "new-style",
        "pairs": [_pair(2, image2, "p2")],
    }
    prior = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "resolved_style_contract_sha256": "old-style",
        "pairs": [
            {
                "page_number": 1,
                "full": {
                    "path": str(image1),
                    "generated_prompt_sha256": "p1",
                    "text_audit": {"valid": True},
                },
            }
        ],
    }

    _retain_audited_prior_pairs(manifest=manifest, prior_manifest=prior)

    assert [pair["page_number"] for pair in manifest["pairs"]] == [2]
