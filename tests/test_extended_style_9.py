from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.cli import build_parser
from scripts.imagegen_pipeline.page_manifest import main as pair_manifest_main
from scripts.imagegen_pipeline.deliverable_prompt import (
    PageBlock,
    _style09_page_semantic_tags,
    enforce_style09_terminal_lock,
)
from scripts.imagegen_pipeline.imagegen_handoff import render_content_first_style_contract
from scripts.imagegen_pipeline.runtime_style_contract import (
    TERMINAL_EXECUTION_HEADING,
    load_runtime_style_contract,
)
from scripts.imagegen_pipeline.style_library import (
    default_style_choices,
    load_style_lock,
    load_style_library,
    resolve_default_style,
    write_project_style_lock,
)


STYLE_FOUR_CONTRACT = {
    "id": 4,
    "slug": "ivory_deep_blue",
    "colors": {
        "background": "#F7F6F0",
        "title": "#101820",
        "body": "#303030",
        "secondary": "#6F7275",
        "divider": "#C9CDD1",
        "accent": "#12355B",
    },
}


def test_style_nine_is_the_explicit_pure_white_extension_and_style_four_is_unchanged() -> None:
    library = load_style_library()
    styles = library["styles"]

    assert [style["id"] for style in styles] == list(range(1, 10))
    assert library["default_style_id"] == 9

    style_four = next(style for style in styles if style["id"] == 4)
    assert style_four["id"] == STYLE_FOUR_CONTRACT["id"]
    assert style_four["slug"] == STYLE_FOUR_CONTRACT["slug"]
    assert style_four["colors"] == STYLE_FOUR_CONTRACT["colors"]

    style_nine = resolve_default_style(style_id=9)
    assert style_nine["slug"] == "ivory_deep_blue_scene"
    assert style_nine["extension_only"] is True
    assert style_nine["name"] == "纯白 + 深蓝领导汇报"
    assert resolve_default_style(style_name="ivory_deep_blue_scene")["id"] == 9
    assert style_nine["colors"] == {
        **STYLE_FOUR_CONTRACT["colors"],
        "background": "#FFFFFF",
    }
    assert style_nine["prompt_contract_source"].endswith(
        "scripts/imagegen_pipeline/style_presets/cyberppt_default_styles.json"
    )


def test_style_nine_registry_contract_carries_current_visual_invariants() -> None:
    style = resolve_default_style(style_id=9)
    contract = style["prompt_contract"]

    assert "pure white background #FFFFFF" in contract
    assert "deep blue #12355B" in contract
    assert "### 1. Style identity and semantic principle — hard" in contract
    assert "### 2. Semantic anchor and composition — hard" in contract
    assert "### 3. Content fidelity and presentation expression — hard" in contract
    assert "### 6. Depth, material and icon discipline — hard" in contract
    assert "### 7. Semantic economy and final priority — hard" in contract
    assert "Represent each source-supported concept once" in contract
    assert "Keep connection lines absent by default" in contract
    assert "Icons are not a default visual language" in contract
    assert "glossy or decorative 3D rendering" in contract
    assert "#F7F6F0" not in contract
    assert 4_000 < len(contract) < 20_000


def test_default_style_choices_still_show_only_original_eight() -> None:
    choices = default_style_choices()
    assert choices.count("\n") == 7
    assert "8. 冷白灰 + 深紫" in choices
    assert "9." not in choices
    assert "10." not in choices


def test_style_nine_lock_records_registry_snapshot_and_reference_image() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        payload = json.loads(lock.read_text(encoding="utf-8"))

    contract = payload["style"]["prompt_contract"]
    assert payload["style"]["id"] == 9
    assert payload["style"]["name"] == "纯白 + 深蓝领导汇报"
    assert payload["policy"]["selected_from_default_8"] is False
    assert payload["policy"]["selected_from_extension"] is True
    assert payload["policy"]["resolved_contract_is_immutable"] is True
    assert payload["policy"]["executable_style_authority"] == "style_registry_snapshot"
    assert payload["resolved_contract"]["mode"] == "snapshot"
    assert payload["resolved_contract"]["source"].endswith(
        "scripts/imagegen_pipeline/style_presets/cyberppt_default_styles.json"
    )
    assert payload["resolved_contract"]["sha256"] == sha256(
        contract.encode("utf-8")
    ).hexdigest().upper()
    assert payload["reference_image"]["required_for_every_page"] is True
    assert payload["reference_image"]["path"].endswith("palette-09.png")


def test_legacy_style_nine_lock_ignores_caller_controlled_documentation_source() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        reference = root / "visual-system.md"
        reference.write_text(
            "## 扩展风格9：测试\n\ncaller-controlled stale contract\n",
            encoding="utf-8",
        )
        lock = root / "visual_style_lock.json"
        lock.write_text(
            json.dumps(
                {
                    "style_source": str(root / "styles.json"),
                    "source_reference": str(reference),
                    "style": {"id": 9, "prompt_contract": "stale"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        payload = load_style_lock(lock)

    contract = payload["style"]["prompt_contract"]
    assert "caller-controlled stale contract" not in contract
    assert "pure white background #FFFFFF" in contract
    assert payload["migration"]["from"] == "legacy_live_refresh"
    assert payload["migration"]["to"] == "style_registry_snapshot"
    assert payload["style"]["prompt_contract_source"].endswith(
        "scripts/imagegen_pipeline/style_presets/cyberppt_default_styles.json"
    )


def test_style_nine_contract_reaches_content_first_prompt_compiler() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        contract = render_content_first_style_contract(lock)

    assert "【视觉风格｜不上屏】" in contract
    assert "pure white background #FFFFFF" in contract
    assert "### 1. Style identity and semantic principle — hard" in contract
    assert "### 2. Semantic anchor and composition — hard" in contract
    assert "### 6. Depth, material and icon discipline — hard" in contract
    assert "semantic_tags:" not in contract
    assert "style09:scope" not in contract


def test_style_nine_is_a_global_contract_not_a_page_clause_selector() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        base = render_content_first_style_contract(lock)
        tagged = render_content_first_style_contract(
            lock,
            semantic_tags=frozenset({"flow", "feedback"}),
        )

    assert tagged == base
    assert "### 4. Reusable composition grammars" in tagged
    assert "#### A. Continuous object transformation" in tagged
    assert "#### D. Multi-source convergence" in tagged
    assert "semantic_tags:" not in tagged


def test_style_nine_infers_multiple_page_semantic_tags_without_incidental_boundary() -> None:
    page = PageBlock(
        10,
        "总体业务主线",
        "\n".join(
            (
                "产品形成链：需求论证与五类审核共同形成产品设计。",
                "订单履行链：可信交付形成计量、验收、账单与结算依据。",
                "运营反馈环：跟踪订购并回流至产品形成链。",
            )
        ),
    )
    tags = _style09_page_semantic_tags(page, page.text.splitlines())

    assert {"flow", "sequence", "feedback", "loop"}.issubset(tags)
    assert "boundary" not in tags


def test_style_nine_terminal_lock_is_reasserted_once_at_absolute_end() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        runtime = load_runtime_style_contract(lock)
        assert runtime.terminal_lock
        duplicated_line = next(
            line.strip()
            for line in runtime.terminal_lock.splitlines()
            if line.strip()
        )
        prompt = enforce_style09_terminal_lock(
            f"Page-specific constraint.\n{duplicated_line}\nNo invented facts.",
            lock,
        )

    assert prompt.count(TERMINAL_EXECUTION_HEADING) == 1
    assert prompt.count(duplicated_line) == 1
    assert "No invented facts." in prompt
    assert prompt.rstrip().endswith(runtime.terminal_lock.strip())


def test_final_script_pages_cli_accepts_explicit_style_nine() -> None:
    args = build_parser().parse_args(
        [
            "final-script-pages",
            "project",
            "--script",
            "script.md",
            "--pages",
            "1",
            "--style-id",
            "9",
        ]
    )
    assert args.style_id == 9


def test_pair_manifest_accepts_explicit_style_nine() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        script = root / "script.md"
        output = root / "output"
        script.write_text("## 第1页：扩展风格\n组件A：业务内容\n", encoding="utf-8")
        code = pair_manifest_main(
            [
                "--script",
                str(script),
                "--pages",
                "1",
                "--output-dir",
                str(output),
                "--project-path",
                str(root / "project"),
                "--style-id",
                "9",
            ]
        )
    assert code == 0


def test_style_nine_contract_uses_page_specific_evidence_without_generic_dashboard_fallback() -> None:
    contract = resolve_default_style(style_id=9)["prompt_contract"]

    assert "Suitable visual material includes:" in contract
    assert "never a generic control room, dashboard wall or stock BI screen" in contract
    assert "prefer the flat structured relationship field over a generic technology scene" in contract
    assert "Never assign one icon to each bullet, module, stage, actor, capability or message" in contract
