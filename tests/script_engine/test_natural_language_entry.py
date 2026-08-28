from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_root_entry_supports_one_sentence_usage() -> None:
    text = _read("SKILL.md")
    assert "根据这个 Word 生成 PPT 脚本" in text
    assert "继续" in text
    assert "第 8 页" in text or "第8页" in text
    assert "不得要求用户先选择" in text


def test_workflow_routes_common_intents_without_stage_selection() -> None:
    text = _read(".agents/skills/cyberppt-script-workflow/SKILL.md")
    for phrase in (
        "New source-to-script",
        "Continue",
        "Re-plan",
        "Targeted page edit",
        "Whole-deck review / rewrite",
    ):
        assert phrase in text
    assert "Do not reply by asking the user to choose an internal stage" in text


def test_user_facing_states_are_limited_to_plan_and_final() -> None:
    text = _read(".agents/skills/cyberppt-script-workflow/SKILL.md")
    assert "脚本规划待确认" in text
    assert "最终脚本已生成" in text
    assert "Critic self-dialogue" in text


def test_workflow_contract_keeps_stage02_on_the_formal_repository_entry() -> None:
    text = _read(".agents/skills/cyberppt-script-workflow/SKILL.md")
    assert "script/foundation.json" in text
    assert "script/deck-plan.json" in text
    assert "script/dist/final-script.md" in text
    assert ".venv/bin/python3 -m cyberppt final-script-pages --production-build" in text
    assert "one formal orchestration entry" in text
    assert "outside this repository" not in text


def test_quickstart_does_not_require_cli_or_skill_names() -> None:
    text = _read("docs/QUICKSTART.md")
    assert "根据这个 Word 生成 PPT 脚本" in text
    assert "不需要记住任何内部阶段名称" in text
    assert "不需要调用 Skill" in text
