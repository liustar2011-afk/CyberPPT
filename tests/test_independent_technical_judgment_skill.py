from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "independent-technical-judgment" / "SKILL.md"
AGENTS = ROOT / "AGENTS.md"


def test_skill_contract_is_present_and_explicit():
    text = SKILL.read_text(encoding="utf-8")
    assert "name: independent-technical-judgment" in text
    for token in (
        "SUPPORT",
        "SUPPORT WITH CONDITIONS",
        "OPPOSE",
        "INSUFFICIENT EVIDENCE",
        "User intent",
        "User proposal",
        "Counter-evidence",
        "Alternatives",
        "Reversal test",
    ):
        assert token in text


def test_repo_agents_wires_skill_before_disputable_technical_decisions():
    text = AGENTS.read_text(encoding="utf-8")
    assert "independent-technical-judgment" in text
    assert "先调用" in text
    assert "机械性修改" in text
