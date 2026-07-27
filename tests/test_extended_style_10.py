from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.cli import build_parser
from scripts.dual_image_overlay.cyberppt_pair_manifest import main as pair_manifest_main
from scripts.dual_image_overlay.deliverable_prompt import style_contract
from scripts.dual_image_overlay.style_library import (
    default_style_choices,
    load_style_library,
    resolve_default_style,
    write_project_style_lock,
)


ROOT = Path(__file__).resolve().parents[1]


def test_style_ten_is_two_layer_explicit_extension() -> None:
    styles = load_style_library()["styles"]
    assert [style["id"] for style in styles] == list(range(1, 11))

    style_ten = resolve_default_style(style_id=10)
    assert style_ten["slug"] == "ivory_deep_blue_semantic_scene"
    assert style_ten["extension_only"] is True
    assert resolve_default_style(style_name=style_ten["slug"])["id"] == 10
    assert style_ten["colors"] == resolve_default_style(style_id=9)["colors"]
    assert "第一层是页面语义结构" in style_ten["scope_rule"]
    assert "semantic structure is mandatory" in style_ten["semantic_structure_rule"]
    assert "normally within about one third" in style_ten["scene_layer_rule"]
    assert "场景不得替代结构" in style_ten["prompt_contract"]


def test_style_ten_contract_reaches_imagegen_prompt() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=10)
        contract = style_contract(lock)
        payload = json.loads(lock.read_text(encoding="utf-8"))

    assert payload["style"]["id"] == 10
    assert "第一层是页面语义结构" in contract
    assert "semantic structure is mandatory" in contract
    assert "normally within about one third" in contract


def test_style_ten_is_not_added_to_default_eight() -> None:
    choices = default_style_choices()
    assert choices.count("\n") == 7
    assert "9." not in choices
    assert "10." not in choices


def test_final_script_pages_cli_accepts_style_ten() -> None:
    args = build_parser().parse_args(
        [
            "final-script-pages",
            "project",
            "--script",
            "script.md",
            "--pages",
            "1",
            "--style-id",
            "10",
        ]
    )
    assert args.style_id == 10


def test_pair_manifest_accepts_style_ten() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        script = root / "script.md"
        script.write_text("## 第1页：双层风格\n组件A：业务内容\n", encoding="utf-8")
        code = pair_manifest_main(
            [
                "--script",
                str(script),
                "--pages",
                "1",
                "--output-dir",
                str(root / "output"),
                "--project-path",
                str(root / "project"),
                "--style-id",
                "10",
            ]
        )
    assert code == 0


def test_style_ten_sample_and_reference_exist() -> None:
    assert (ROOT / "assets" / "palette-samples" / "palette-10.png").exists()
    reference = (ROOT / "references" / "visual-system.md").read_text(encoding="utf-8")
    assert "扩展风格10：象牙白 + 深蓝双层语义汇报" in reference
    assert "以语义结构为骨架，以行业场景为有限视觉锚点" in reference
