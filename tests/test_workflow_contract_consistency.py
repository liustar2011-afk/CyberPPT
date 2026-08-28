from pathlib import Path

from cyberppt.workflow_contract import (
    AUTHORITATIVE_STAGE01_CONTENT_ARTIFACTS,
    SCRIPT_PHASES,
    STAGE01_ROUTE,
    STAGE02_ENTRY,
    workflow_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def test_machine_readable_workflow_contract_is_stable():
    assert STAGE01_ROUTE == (
        "cyberppt-source-foundation",
        "business-semantic-understanding",
        "project-foundation",
        "cyberppt-script-workflow",
    )
    assert SCRIPT_PHASES == (
        "UNDERSTAND",
        "PLAN",
        "AUTHOR",
        "CRITIQUE",
        "REWRITE",
        "DELIVER",
    )
    assert AUTHORITATIVE_STAGE01_CONTENT_ARTIFACTS == (
        "foundation.json",
        "deck-plan.json",
        "dist/final-script.md",
    )
    assert STAGE02_ENTRY == "final-script-pages"
    assert workflow_contract()["stage02_entry"] == STAGE02_ENTRY


def test_script_workflow_skill_matches_repository_stage02_contract():
    skill = (ROOT / ".agents/skills/cyberppt-script-workflow/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert STAGE02_ENTRY in skill
    assert "remain outside this repository" not in skill
    for artifact in AUTHORITATIVE_STAGE01_CONTENT_ARTIFACTS:
        assert artifact in skill


def test_repository_entry_docs_expose_the_formal_stage02_entry():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    workflow = (ROOT / "docs/CYBERPPT_WORKFLOW.md").read_text(encoding="utf-8")
    assert STAGE02_ENTRY in agents
    assert STAGE02_ENTRY in workflow
