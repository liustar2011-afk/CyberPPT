from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from cyberppt.stage02_production.page_reuse import (
    PAGE_INPUT_SHA256_FIELD,
    recover_page_local_artifacts,
)


def _pair(page_number: int, path: Path, *, page_sha: str, prompt_sha: str) -> dict:
    return {
        "page_number": page_number,
        PAGE_INPUT_SHA256_FIELD: page_sha,
        "full": {
            "path": str(path),
            "prompt_sha256": prompt_sha,
        },
    }


def _prior_pair(page_number: int, path: Path, *, page_sha: str, prompt_sha: str) -> dict:
    pair = _pair(page_number, path, page_sha=page_sha, prompt_sha=prompt_sha)
    pair["full"].update(
        {
            "status": "Generated",
            "sha256": sha256(path.read_bytes()).hexdigest(),
            "generated_prompt_sha256": prompt_sha,
            "text_audit": {"valid": True, "receipt": f"p{page_number}"},
        }
    )
    return pair


def _manifest(*, script_sha: str, fingerprint: str, pairs: list[dict]) -> dict:
    return {
        "source_script_sha256": script_sha,
        "source_mode": "script_file",
        "production_mode": "image-to-editable-svg",
        "prompt_contract": {"compiler": "content-first-v1"},
        "input_fingerprint": fingerprint,
        "pairs": pairs,
    }


def test_only_changed_page_is_invalidated_when_fidelity_changes_other_page(tmp_path: Path) -> None:
    p1 = tmp_path / "p1.png"
    p2 = tmp_path / "p2.png"
    p1.write_bytes(b"page-one")
    p2.write_bytes(b"page-two")

    prior = _manifest(
        script_sha="old-script",
        fingerprint="old-deck",
        pairs=[
            _prior_pair(1, p1, page_sha="page-1-same", prompt_sha="prompt-1"),
            _prior_pair(2, p2, page_sha="page-2-old-fidelity", prompt_sha="prompt-2-old"),
        ],
    )
    current = _manifest(
        script_sha="new-script",
        fingerprint="new-deck",
        pairs=[
            _pair(1, p1, page_sha="page-1-same", prompt_sha="prompt-1"),
            _pair(2, p2, page_sha="page-2-new-fidelity", prompt_sha="prompt-2-new"),
        ],
    )

    recovered = recover_page_local_artifacts(
        manifest=current,
        prior_manifest=prior,
        production_mode="image-to-editable-svg",
    )

    assert recovered == (1,)
    assert current["pairs"][0]["full"]["status"] == "Generated"
    assert current["pairs"][0]["full"]["text_audit"] == {
        "valid": True,
        "receipt": "p1",
    }
    assert "text_audit" not in current["pairs"][1]["full"]
    assert "generated_prompt_sha256" not in current["pairs"][1]["full"]


def test_matching_page_hash_does_not_override_prompt_change(tmp_path: Path) -> None:
    image = tmp_path / "p1.png"
    image.write_bytes(b"page-one")
    prior = _manifest(
        script_sha="old-script",
        fingerprint="old-deck",
        pairs=[_prior_pair(1, image, page_sha="same-page", prompt_sha="old-prompt")],
    )
    current = _manifest(
        script_sha="new-script",
        fingerprint="new-deck",
        pairs=[_pair(1, image, page_sha="same-page", prompt_sha="new-prompt")],
    )

    recovered = recover_page_local_artifacts(
        manifest=current,
        prior_manifest=prior,
        production_mode="image-to-editable-svg",
    )

    assert recovered == ()
    assert "text_audit" not in current["pairs"][0]["full"]


def test_historical_pair_without_page_hash_does_not_use_cross_script_reuse(tmp_path: Path) -> None:
    image = tmp_path / "p1.png"
    image.write_bytes(b"page-one")
    prior_pair = _prior_pair(1, image, page_sha="legacy-placeholder", prompt_sha="prompt")
    prior_pair.pop(PAGE_INPUT_SHA256_FIELD)
    prior = _manifest(
        script_sha="old-script",
        fingerprint="old-deck",
        pairs=[prior_pair],
    )
    current = _manifest(
        script_sha="new-script",
        fingerprint="new-deck",
        pairs=[_pair(1, image, page_sha="current-page", prompt_sha="prompt")],
    )

    recovered = recover_page_local_artifacts(
        manifest=current,
        prior_manifest=prior,
        production_mode="image-to-editable-svg",
    )

    assert recovered == ()
    assert "text_audit" not in current["pairs"][0]["full"]
