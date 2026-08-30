from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.imagegen_pipeline.deliverable_prompt import enforce_style09_terminal_lock
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


STYLE_FOUR_COLORS = {
    "background": "#F7F6F0",
    "title": "#101820",
    "body": "#303030",
    "secondary": "#6F7275",
    "divider": "#C9CDD1",
    "accent": "#12355B",
}


def test_style_nine_is_pure_white_extension_and_style_four_stays_unchanged() -> None:
    styles = load_style_library()["styles"]
    style_four = next(style for style in styles if style["id"] == 4)
    style_nine = resolve_default_style(style_id=9)

    assert [style["id"] for style in styles] == list(range(1, 10))
    assert style_four["colors"] == STYLE_FOUR_COLORS
    assert style_nine["slug"] == "ivory_deep_blue_scene"
    assert style_nine["name"] == "纯白 + 深蓝领导汇报"
    assert style_nine["extension_only"] is True
    assert style_nine["colors"] == {**STYLE_FOUR_COLORS, "background": "#FFFFFF"}
    assert style_nine["prompt_contract_source"].endswith(
        "scripts/imagegen_pipeline/style_presets/cyberppt_default_styles.json"
    )


def test_style_nine_registry_contract_carries_current_visual_invariants() -> None:
    contract = resolve_default_style(style_id=9)["prompt_contract"]

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
    assert "#F7F6F0" not in contract
    # Protect against an accidentally truncated/compact replacement without
    # turning one historical prompt length into an API contract.
    assert len(contract) > 10_000


def test_default_style_choices_still_advertise_only_original_eight() -> None:
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


def test_legacy_style_nine_lock_ignores_caller_documentation_and_migrates_once() -> None:
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

        migrated = load_style_lock(lock)
        second_read = load_style_lock(lock)

    assert "caller-controlled stale contract" not in migrated["style"]["prompt_contract"]
    assert "pure white background #FFFFFF" in migrated["style"]["prompt_contract"]
    assert migrated["migration"]["from"] == "legacy_live_refresh"
    assert migrated["migration"]["to"] == "style_registry_snapshot"
    assert second_read["style"]["prompt_contract"] == migrated["style"]["prompt_contract"]


def test_style_nine_contract_reaches_content_first_compiler_without_routing_metadata() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        contract = render_content_first_style_contract(lock)

    assert "【视觉风格｜不上屏】" in contract
    assert "pure white background #FFFFFF" in contract
    assert "### 2. Semantic anchor and composition — hard" in contract
    assert "semantic_tags:" not in contract
    assert "style09:scope" not in contract


def test_style_nine_terminal_lock_is_reasserted_once_at_absolute_end() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        runtime = load_runtime_style_contract(lock)
        duplicated_line = next(
            line.strip() for line in runtime.terminal_lock.splitlines() if line.strip()
        )
        prompt = enforce_style09_terminal_lock(
            f"Page-specific constraint.\n{duplicated_line}\nNo invented facts.",
            lock,
        )

    assert prompt.count(TERMINAL_EXECUTION_HEADING) == 1
    assert prompt.count(duplicated_line) == 1
    assert "No invented facts." in prompt
    assert prompt.rstrip().endswith(runtime.terminal_lock.strip())
