from hashlib import sha256
from pathlib import Path

from scripts.image_to_pptx_runtime.stage02_adapter import _quick_page_binding


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_quick_page_checkpoint_binds_reconstruction_visual_authority_sha(tmp_path):
    full = tmp_path / "full.png"
    clean = tmp_path / "clean.png"
    authored = tmp_path / "page.svg"
    full.write_bytes(b"full-authority")
    clean.write_bytes(b"clean-base")
    authored.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    pair = {
        "full": {
            "path": str(full),
            "text_audit": {"valid": True},
            "reconstruction_visual_source": {
                "authority": "audited_full_image",
                "path": str(full),
                "sha256": _sha(full),
                "immutable_visual_composition": True,
            },
        },
        "clean_base": {"path": str(clean)},
        "graphic_text_policy": {},
    }
    binding = _quick_page_binding(
        pair,
        authored,
        template_contract={"rules": {}},
        style_lock=None,
    )
    assert binding["full_image_sha256"] == _sha(full)
    assert binding["reconstruction_visual_source_sha256"] == _sha(full)
