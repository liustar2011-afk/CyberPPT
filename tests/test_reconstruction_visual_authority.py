from hashlib import sha256
from pathlib import Path

import pytest

from cyberppt.reconstruction_visual_authority import validate_reconstruction_visual_authority


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _manifest(tmp_path: Path, *, include_clean: bool = True) -> dict:
    full = tmp_path / "full.png"
    full.write_bytes(b"audited-full-image")
    pair = {
        "page_number": 1,
        "full": {
            "path": str(full),
            "reconstruction_visual_source": {
                "authority": "audited_full_image",
                "path": str(full),
                "sha256": _sha(full),
                "immutable_visual_composition": True,
            },
        },
    }
    if include_clean:
        clean = tmp_path / "clean.png"
        clean.write_bytes(b"same-composition-clean-base")
        pair["clean_base"] = {
            "status": "complete",
            "path": str(clean),
            "source_sha256": _sha(full),
        }
    return {
        "visual_truth_policy": {
            "authority": "audited_full_image",
            "scope": "editable_reconstruction",
            "rule": "preserve accepted visual composition",
        },
        "pairs": [pair],
    }


def test_reconstruction_authority_accepts_exact_full_image_and_clean_base_source(tmp_path):
    result = validate_reconstruction_visual_authority(_manifest(tmp_path), require_clean_base=True)
    assert result["authority"] == "audited_full_image"
    assert result["immutable_visual_composition"] is True
    assert result["page_count"] == 1
    assert result["pages"][0]["authority_sha256"]
    assert result["pages"][0]["clean_base_sha256"]


def test_reconstruction_authority_rejects_full_image_mutation_after_freeze(tmp_path):
    manifest = _manifest(tmp_path, include_clean=False)
    full = Path(manifest["pairs"][0]["full"]["path"])
    full.write_bytes(b"mutated-after-authority-freeze")
    with pytest.raises(ValueError, match="sha256 drifted"):
        validate_reconstruction_visual_authority(manifest)


def test_reconstruction_authority_rejects_path_substitution(tmp_path):
    manifest = _manifest(tmp_path, include_clean=False)
    other = tmp_path / "other.png"
    other.write_bytes(b"other-image")
    manifest["pairs"][0]["full"]["reconstruction_visual_source"]["path"] = str(other)
    with pytest.raises(ValueError, match="path drifted"):
        validate_reconstruction_visual_authority(manifest)


def test_reconstruction_authority_rejects_clean_base_from_another_source(tmp_path):
    manifest = _manifest(tmp_path)
    manifest["pairs"][0]["clean_base"]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="clean base source_sha256 drifted"):
        validate_reconstruction_visual_authority(manifest, require_clean_base=True)


def test_reconstruction_authority_requires_immutable_flag(tmp_path):
    manifest = _manifest(tmp_path, include_clean=False)
    manifest["pairs"][0]["full"]["reconstruction_visual_source"]["immutable_visual_composition"] = False
    with pytest.raises(ValueError, match="immutable visual composition"):
        validate_reconstruction_visual_authority(manifest)
