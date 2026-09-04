from __future__ import annotations

from pathlib import Path
from hashlib import sha256

from PIL import Image, ImageDraw

from cyberppt.stage02_production.manifest_stage import _retain_audited_prior_pairs, _reuse_prior_artifacts
from scripts.image_to_pptx_runtime.clean_base_policy import (
    ALGORITHM_VERSION,
    SCHEMA,
    compute_visual_diff_report,
    graphic_text_policy_sha256,
)


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


def test_same_run_does_not_reuse_across_external_source_mode(tmp_path: Path) -> None:
    image = tmp_path / "p4.png"
    image.write_bytes(b"image")
    current = {
        "run_id": "same-run",
        "source_mode": "external_script",
        "prompt_contract": {"compiler": "content-first-v1"},
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "external",
        "pairs": [_pair(image, prompt_sha="verbatim")],
    }
    prior_pair = _pair(image, prompt_sha="content-first")
    prior_pair["full"].update({"generated_prompt_sha256": "content-first", "text_audit": {"valid": True}})
    prior = {
        "run_id": "same-run",
        "source_mode": "script_file",
        "prompt_contract": {"compiler": "content-first-v1"},
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "local",
        "pairs": [prior_pair],
    }

    _reuse_prior_artifacts(manifest=current, prior_manifest=prior, production_mode="image-to-editable-svg")

    assert "text_audit" not in current["pairs"][0]["full"]


def test_prior_audited_full_is_not_reused_when_bound_image_bytes_change(tmp_path: Path) -> None:
    image = tmp_path / "p4.png"
    image.write_bytes(b"new-image-bytes")
    current = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "same",
        "pairs": [_pair(image, prompt_sha="prompt")],
    }
    prior_pair = _pair(image, prompt_sha="prompt")
    prior_pair["full"].update({
        "sha256": sha256(b"old-image-bytes").hexdigest(),
        "generated_prompt_sha256": "prompt",
        "text_audit": {"valid": True},
    })
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


def test_bad_complete_clean_base_does_not_reuse_but_audited_full_does(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (160, 90), "#173C63")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 36, 42), fill="white")
    image.save(full)
    clean = tmp_path / "clean.png"
    Image.new("RGB", (160, 90), "white").save(clean)
    policy = {
        "schema": "cyberppt.image_to_pptx.graphic_text_policy.v1",
        "status": "complete",
        "empty_container_check": "passed",
        "items": [{"id": "label-1", "text": "登记编目", "bbox": [20, 20, 70, 50], "treatment": "native_text"}],
    }
    file_hash = lambda path: sha256(path.read_bytes()).hexdigest()
    policy_hash = graphic_text_policy_sha256(policy)
    bad_clean = {
        "schema": SCHEMA,
        "status": "complete",
        "path": str(clean),
        "source_sha256": file_hash(full),
        "sha256": file_hash(clean),
        "algorithm_version": ALGORITHM_VERSION,
        "graphic_text_policy_sha256": policy_hash,
        "removal_scope": "native_text_only",
        "clearance_padding_px": 0,
        "max_outside_mask_changed_fraction": 0.0,
        "cleaned_text_regions": [{
            "policy_id": "label-1",
            "text": "登记编目",
            "bbox": [20, 20, 70, 50],
            "clearance_bbox": [20, 20, 70, 50],
            "method": "flat-surface-rebuild",
        }],
        "visual_diff_report": {
            "schema": "cyberppt.stage02.clean_base.visual_diff.v2",
            "qa_origin": "computed",
            "status": "passed",
            "algorithm_version": ALGORITHM_VERSION,
            "source_sha256": file_hash(full),
            "clean_base_sha256": file_hash(clean),
            "graphic_text_policy_sha256": policy_hash,
            "checks": {
                "text_removal": "passed",
                "background_continuity": "passed",
                "outside_mask_preserved": "passed",
                "no_abnormal_solid_blocks": "passed",
            },
            "post_clean_ocr": {"executed": True, "status": "passed", "residual": []},
        },
    }
    prior_pair = _pair(full, prompt_sha="prompt")
    prior_pair.update({
        "graphic_text_policy": policy,
        "clean_base": bad_clean,
        "authoring_svg": str(tmp_path / "old.svg"),
        "quick_page_checkpoint": {"status": "passed"},
    })
    prior_pair["full"].update({"generated_prompt_sha256": "prompt", "text_audit": {"valid": True}})
    current = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "same",
        "pairs": [_pair(full, prompt_sha="prompt")],
    }
    prior = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "same",
        "pairs": [prior_pair],
    }

    _reuse_prior_artifacts(manifest=current, prior_manifest=prior, production_mode="image-to-editable-svg")

    pair = current["pairs"][0]
    assert pair["full"]["text_audit"]["valid"] is True
    assert pair["clean_base"]["status"] == "required"
    assert "authoring_svg" not in pair
    assert "quick_page_checkpoint" not in pair


def test_legacy_v2_complete_clean_base_is_not_reused(tmp_path: Path) -> None:
    image = tmp_path / "full.png"
    image.write_bytes(b"image")
    prior_pair = _pair(image, prompt_sha="prompt")
    prior_pair["full"].update({"generated_prompt_sha256": "prompt", "text_audit": {"valid": True}})
    prior_pair["clean_base"] = {"schema": "cyberppt.stage02.clean_base.v2", "status": "complete", "path": str(image)}
    prior = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "same",
        "pairs": [prior_pair],
    }
    current = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "same",
        "pairs": [_pair(image, prompt_sha="prompt")],
    }

    _reuse_prior_artifacts(manifest=current, prior_manifest=prior, production_mode="image-to-editable-svg")

    assert current["pairs"][0]["full"]["text_audit"]["valid"] is True
    assert current["pairs"][0]["clean_base"]["status"] == "required"


def test_self_reported_visual_receipt_is_not_reused_when_pixels_are_valid(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    full_image = Image.new("RGB", (160, 90), "#173C63")
    draw = ImageDraw.Draw(full_image)
    for offset in (0, 11, 22, 33):
        draw.rectangle((30 + offset, 28, 35 + offset, 43), fill="#FFFFFF")
    full_image.save(full)
    clean = tmp_path / "clean.png"
    clean_image = full_image.copy()
    clean_draw = ImageDraw.Draw(clean_image)
    for offset in (0, 11, 22, 33):
        clean_draw.rectangle((30 + offset, 28, 35 + offset, 43), fill="#173C63")
    clean_image.save(clean)
    policy = {
        "schema": "cyberppt.image_to_pptx.graphic_text_policy.v1",
        "status": "complete",
        "empty_container_check": "passed",
        "items": [{"id": "label-1", "text": "登记编目", "bbox": [20, 20, 80, 50], "treatment": "native_text"}],
    }
    file_hash = lambda path: sha256(path.read_bytes()).hexdigest()
    policy_hash = graphic_text_policy_sha256(policy)
    regions = [{
        "policy_id": "label-1",
        "text": "登记编目",
        "bbox": [20, 20, 80, 50],
        "clearance_bbox": [20, 20, 80, 50],
        "method": "flat-surface-rebuild",
    }]
    visual = compute_visual_diff_report(
        full,
        clean,
        regions,
        source_sha256=file_hash(full),
        clean_base_sha256=file_hash(clean),
        policy_sha256=policy_hash,
    )
    visual["post_clean_ocr"] = {"executed": True, "status": "passed", "residual": []}
    visual["qa_origin"] = "self-reported"
    bad_clean = {
        "schema": SCHEMA,
        "status": "complete",
        "path": str(clean),
        "source_sha256": file_hash(full),
        "sha256": file_hash(clean),
        "algorithm_version": ALGORITHM_VERSION,
        "graphic_text_policy_sha256": policy_hash,
        "removal_scope": "native_text_only",
        "clearance_padding_px": 0,
        "max_outside_mask_changed_fraction": 0.0,
        "cleaned_text_regions": regions,
        "visual_diff_report": visual,
    }
    prior_pair = _pair(full, prompt_sha="prompt")
    prior_pair.update({
        "graphic_text_policy": policy,
        "clean_base": bad_clean,
    })
    prior_pair["full"].update({"generated_prompt_sha256": "prompt", "text_audit": {"valid": True}})
    current = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "same",
        "pairs": [_pair(full, prompt_sha="prompt")],
    }
    prior = {
        "source_script_sha256": "script",
        "production_mode": "image-to-editable-svg",
        "input_fingerprint": "same",
        "pairs": [prior_pair],
    }

    _reuse_prior_artifacts(manifest=current, prior_manifest=prior, production_mode="image-to-editable-svg")

    assert current["pairs"][0]["clean_base"]["status"] == "required"
