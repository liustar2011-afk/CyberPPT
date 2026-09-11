from __future__ import annotations

import json
from pathlib import Path

from script_engine.contracts import (
    lint_final_script,
    validate_deck_plan,
    validate_final_script,
    validate_foundation,
)

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _source_provenance() -> dict:
    return {
        "packet_sha256": "1" * 64,
        "source_refs": ["F1"],
        "unit_ids": ["SU-001"],
    }


def test_examples_validate_and_default_faithful_example_is_source_closed() -> None:
    foundation = json.loads(_read("examples/foundation.example.json"))
    plan = json.loads(_read("examples/deck-plan.example.json"))
    final_script = json.loads(_read("examples/final-script.example.json"))

    assert validate_foundation(foundation) == []
    assert validate_deck_plan(plan) == []
    assert validate_final_script(final_script) == []
    assert lint_final_script(final_script) == []

    assert foundation["source_structure"]
    assert foundation["relations"][0]["basis"] == "explicit"
    assert foundation["relations"][0]["support"] == ["F3"]
    assert foundation["arguments"][0]["basis"] == "explicit"
    assert foundation["arguments"][0]["support"] == ["F3"]

    assert plan["authoring_mode"] == "faithful"
    assert plan["source_structure_mode"] == "preserve"
    assert plan["pages"][0]["source_refs"]
    assert plan["plan_contract_version"] == 2
    assert plan["planning_profile"] == "lean"
    assert "转化为可持续" not in plan["pages"][0]["question"]

    slide = final_script["slides"][0]
    assert slide["core_message"] == foundation["facts"][2]["statement"]
    assert slide["argument"]["pattern"] == "evidence synthesis"
    assert slide["visual_thesis"] == "资源治理与可信使用共同支撑服务输出。"
    assert slide["source_refs"] == ["F1", "F2", "F3", "F4"]

    full_copy = slide["full_copy"]
    for unsupported in (
        "血缘管理",
        "版本管理",
        "模型训练",
        "智能问答",
        "客户反馈",
        "续约",
        "增购",
        "场景复制",
        "缺一不可",
    ):
        assert unsupported not in full_copy


def test_understand_skill_preserves_only_explicit_relations() -> None:
    text = " ".join(
        _read(".agents/skills/cyberppt-script-understand/SKILL.md").split()
    )
    for token in (
        "Source structure",
        "Atomic facts",
        "Explicit relations",
        "basis: explicit",
        "Do not search for latent logic",
        "relations` may be empty",
    ):
        assert token in text


def test_understand_skill_bundles_its_analysis_references() -> None:
    skill_root = ROOT / ".agents/skills/cyberppt-script-understand"
    for relative in (
        "references/analysis-models.md",
        "references/evidence-architecture.md",
    ):
        assert (skill_root / relative).is_file()


def test_core_references_exist_without_new_content_authority() -> None:
    for relative in (
        "docs/SOURCE_FIDELITY_AND_ANALYSIS.md",
        "references/storyline-planning.md",
        "references/argument-patterns.md",
        "references/script-quality-rubric.md",
        "references/screen-copy-authoring.md",
        ".agents/skills/cyberppt-script-workflow/AGENTS.md",
        ".agents/skills/cyberppt-script-workflow/references/faithful-authoring-contract.md",
    ):
        assert (ROOT / relative).is_file()
    agents = _read("AGENTS.md")
    assert "Only these are authoritative content artifacts" in agents
    assert "foundation.json" in agents
    assert "deck-plan.json" in agents
    assert "dist/final-script.md" in agents
    assert ".cache" in agents


def test_workflow_routes_to_exactly_one_mode_specific_authoring_contract() -> None:
    workflow = _read(".agents/skills/cyberppt-script-workflow/SKILL.md")
    local_agents = _read(".agents/skills/cyberppt-script-workflow/AGENTS.md")

    assert "Mandatory mode-specific authoring reference" in workflow
    assert "references/faithful-authoring-contract.md" in workflow
    assert "references/authoring-contract.md" in workflow
    assert "Exactly one mode-specific contract is operational for each action" in workflow

    assert "Single active contract per action" in local_agents
    assert "`faithful` -> read `references/faithful-authoring-contract.md` completely" in local_agents
    assert "`analytical` -> read `references/authoring-contract.md` completely" in local_agents
    assert "Do not merge" in local_agents


def test_faithful_contract_is_source_native_not_judgment_first() -> None:
    contract = _read(
        ".agents/skills/cyberppt-script-workflow/references/faithful-authoring-contract.md"
    )
    for token in (
        "source-native editorial transduction",
        "no author-created page conclusion",
        "Classify the source-native page structure",
        "Write `full_copy` directly from source meaning",
        "Run Source Fidelity Critic on `full_copy`",
        "Create `onscreen` only from approved `full_copy`",
        "Every visible proposition must have a direct semantic parent in `full_copy`",
        "The faithful minimum content-page fields are",
        "The following fields are optional in faithful mode",
        "Parallel facts may remain peer facts",
        "Do not force",
    ):
        assert token in contract

    assert "Author the page conclusion" not in contract
    assert "judgment-first hierarchy" not in contract
    assert "one page, one conclusion" not in contract


def test_analytical_contract_retains_analytical_authoring_methods() -> None:
    contract = _read(
        ".agents/skills/cyberppt-script-workflow/references/authoring-contract.md"
    )
    assert "Author the page conclusion" in contract
    assert "judgment-first hierarchy" in contract
    assert "Argument-topology method" in contract


def test_faithful_minimum_content_page_validates_and_lints_without_argument() -> None:
    payload = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {
            "title": "忠实模式示例",
            "communication_goal": "呈现三项来源任务。",
            "authoring_mode": "faithful",
            "delivery_mode": "self_read",
        },
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "三项重点任务",
                "content_load": "light",
                "full_copy": "一是开展数据目录梳理。二是开展数据质量检查。三是开展接口联调。",
                "onscreen": [
                    {"heading": "数据目录梳理", "text": "开展数据目录梳理"},
                    {"heading": "数据质量检查", "text": "开展数据质量检查"},
                    {"heading": "接口联调", "text": "开展接口联调"},
                ],
                "source_refs": ["F1"],
                "source_provenance": _source_provenance(),
            }
        ],
    }

    assert validate_final_script(payload) == []
    assert lint_final_script(payload) == []


def test_analytical_mode_still_requires_analytical_supporting_fields() -> None:
    payload = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {
            "title": "分析模式示例",
            "communication_goal": "解释资源治理关系。",
            "authoring_mode": "analytical",
            "delivery_mode": "self_read",
        },
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "资源治理",
                "content_load": "light",
                "full_copy": "资源治理需要统一组织并形成清晰的分析结构。",
                "onscreen": [
                    {"heading": "资源治理需要统一组织", "text": "资源治理需要统一组织并形成清晰的分析结构"}
                ],
                "source_refs": ["F1"],
                "source_provenance": _source_provenance(),
            }
        ],
    }

    assert validate_final_script(payload) == []
    issues = lint_final_script(payload)
    assert any("AUTHOR_FIELD_REQUIRED" in issue and ".core_message" in issue for issue in issues)
    assert any("AUTHOR_ARGUMENT_REQUIRED" in issue for issue in issues)
    assert any("AUTHOR_FIELD_REQUIRED" in issue and ".visual_thesis" in issue for issue in issues)
