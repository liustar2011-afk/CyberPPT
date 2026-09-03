from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_repository_uses_local_workflow_router_instead_of_a_root_skill() -> None:
    assert not (ROOT / "SKILL.md").exists()
    router = _read(".agents/skills/cyberppt-workflow/SKILL.md")
    workflow = _read(".agents/skills/cyberppt-script-workflow/SKILL.md")
    assert "load and execute `cyberppt-script-workflow`" in router
    assert "Do not reply by asking the user to choose an internal stage" in workflow


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


def test_current_main_agent_executes_author_instead_of_delegating_to_dead_code() -> None:
    workflow = _read(".agents/skills/cyberppt-script-workflow/SKILL.md")
    router = _read(".agents/skills/cyberppt-workflow/SKILL.md")
    agents = _read("AGENTS.md")

    assert "The current main agent is the AUTHOR executor" in workflow
    assert "There is no separate AUTHOR" in workflow
    assert "load and execute `cyberppt-script-workflow`" in router
    assert "PLAN 和 AUTHOR 的唯一执行者是当前主 Agent" in agents
    assert not (ROOT / "scripts" / "author_v16_outline.py").exists()


def test_workflow_requires_full_copy_structure_pass_before_onscreen_selection() -> None:
    workflow = _read(".agents/skills/cyberppt-script-workflow/SKILL.md")

    assert "semantic-preserving editorial projection" in workflow
    assert "conclusion-first, reader-facing expression" in workflow
    assert "complete paragraphs" in workflow


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
