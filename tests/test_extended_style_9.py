from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from scripts.imagegen_pipeline.deliverable_prompt import enforce_style09_terminal_lock
from scripts.imagegen_pipeline.handoff.presentation import (
    PresentationDecision,
    render_presentation_contract,
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

    assert [style["id"] for style in styles] == list(range(1, 11))
    assert style_four["colors"] == STYLE_FOUR_COLORS
    assert style_nine["slug"] == "ivory_deep_blue_scene"
    assert style_nine["name"] == "纯白 + 深蓝领导汇报"
    assert style_nine["extension_only"] is True
    assert style_nine["colors"] == {
        **STYLE_FOUR_COLORS,
        "background": "#FFFFFF",
        "secondary_accent": "#D9772B",
    }
    assert style_nine["prompt_contract_source"].endswith("references/visual-system.md")


def test_style_nine_registry_contract_carries_current_visual_invariants() -> None:
    contract = resolve_default_style(style_id=9)["prompt_contract"]

    assert "视觉风格09：纯白 + 深蓝领导汇报｜GPT Image 2.5 Artifact Spec 执行版" in contract
    assert "配色：纯白 `#FFFFFF`" in contract
    assert "深蓝 `#12355B`" in contract
    assert "低饱和琥珀色 `#D9772B`" in contract
    assert "琥珀色只用于来源明确的风险、约束、例外、待定或决策重点" in contract
    assert "第一眼必须识别正文主焦点" in contract
    assert "来源存在主次时，可采用非对称与不等视觉权重；来源等权时保持同层均衡" in contract
    assert "卡片只在业务信息本身具有明确独立边界时使用" in contract
    assert "场景按需使用，可以为零" in contract
    assert "图标只用于提高必要对象的识别效率" in contract
    assert "每页采用一个主构图机制" in contract
    assert "## 12｜最终风格收口｜最高视觉优先级" in contract
    assert "strong visual hierarchy" in contract
    assert len(contract) > 2_000


def test_style_nine_fallback_contract_allows_requested_structures() -> None:
    style_nine = next(
        style for style in load_style_library()["styles"] if style["id"] == 9
    )
    contract = style_nine["prompt_contract"].lower()

    assert "timelines" not in contract
    assert "step cards" not in contract
    assert "architecture diagrams" not in contract


def test_style_nine_presentation_routes_allow_requested_structures() -> None:
    page = SimpleNamespace(scene_role="", layout_motif="")
    for visual_medium in ("editorial_typographic", "editorial_dense", "spatial_system"):
        contract = render_presentation_contract(
            page,
            PresentationDecision("", "no_scene", "script", "test", visual_medium),
            style_id=9,
        )
        assert "流程" not in contract
        assert "连续节点" not in contract
        assert "架构层" not in contract
        assert "架构图" not in contract

    default_contract = render_presentation_contract(
        page,
        PresentationDecision("", "no_scene", "script", "test", "editorial_dense"),
    )
    assert "流程图和软件架构图" in default_contract


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
    assert payload["policy"]["resolved_contract_is_immutable"] is False
    assert payload["policy"]["executable_style_authority"].endswith(
        "references/visual-system.md"
    )
    assert payload["resolved_contract"]["mode"] == "snapshot"
    assert payload["resolved_contract"]["source"].endswith(
        "references/visual-system.md"
    )
    assert payload["resolved_contract"]["sha256"] == sha256(
        contract.encode("utf-8")
    ).hexdigest().upper()
    assert payload["reference_image"]["required_for_every_page"] is True
    assert payload["reference_image"]["path"].endswith("palette-09.png")


def test_legacy_style_nine_lock_refreshes_to_current_contract() -> None:
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

        refreshed = load_style_lock(lock)
        second_read = load_style_lock(lock)

    assert "caller-controlled stale contract" not in refreshed["style"]["prompt_contract"]
    assert "配色：纯白 `#FFFFFF`" in refreshed["style"]["prompt_contract"]
    assert refreshed["style_source"].endswith("references/visual-system.md")
    assert second_read["style"] == refreshed["style"]


def test_explicitly_immutable_style_nine_lock_preserves_frozen_contract() -> None:
    with TemporaryDirectory() as directory:
        lock = Path(directory) / "visual_style_lock.json"
        lock.write_text(
            json.dumps(
                {
                    "style_source": "/tmp/frozen-visual-system.md",
                    "style": {"id": 9, "prompt_contract": "frozen test contract"},
                    "policy": {"resolved_contract_is_immutable": True},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        loaded = load_style_lock(lock)

    assert loaded["style"]["prompt_contract"] == "frozen test contract"
    assert loaded["style_source"] == "/tmp/frozen-visual-system.md"


def test_style_nine_contract_reaches_content_first_compiler_without_routing_metadata() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        contract = render_content_first_style_contract(lock)

    assert "【视觉风格｜不上屏】" in contract
    assert "配色：纯白 `#FFFFFF`" in contract
    assert "每页采用一个主构图机制" in contract
    assert "semantic_tags:" not in contract
    assert "style09:scope" not in contract


def test_style_nine_terminal_lock_reasserts_the_visual_focus_requirement() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        runtime = load_runtime_style_contract(lock)
        duplicated_line = next(
            line.strip() for line in runtime.terminal_lock.splitlines() if line.strip()
        )
        prompt_source = f"Page-specific constraint.\n{duplicated_line}\nNo invented facts."
        prompt = enforce_style09_terminal_lock(
            prompt_source,
            lock,
        )

    assert "strong visual hierarchy" in runtime.terminal_lock
    assert "构图由当前页面语义决定" in runtime.terminal_lock
    assert prompt.count(TERMINAL_EXECUTION_HEADING) == 1
    assert prompt.count(duplicated_line) == 1
    assert "No invented facts." in prompt
    assert prompt.rstrip().endswith(runtime.terminal_lock.strip())
