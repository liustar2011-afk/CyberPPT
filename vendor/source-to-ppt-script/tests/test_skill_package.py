from __future__ import annotations

import re
from pathlib import Path

import yaml


def test_skill_frontmatter(skill_root: Path) -> None:
    text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    assert match, "SKILL.md must start with YAML frontmatter"
    metadata = yaml.safe_load(match.group(1))
    assert metadata["name"] == "source-to-ppt-script"
    assert 1 <= len(metadata["description"]) <= 1024
    assert "DOCX" in metadata["description"]


def test_required_skill_files(skill_root: Path) -> None:
    required = [
        "SKILL.md",
        "agents/openai.yaml",
        "scripts/ppt_skill.py",
        "references/schemas/information_assets.schema.json",
        "assets/profiles/cec_leadership.yaml",
    ]
    for relative in required:
        assert (skill_root / relative).exists(), relative


def test_agent_metadata(skill_root: Path) -> None:
    payload = yaml.safe_load((skill_root / "agents/openai.yaml").read_text(encoding="utf-8"))
    assert payload["interface"]["display_name"]
    assert payload["policy"]["allow_implicit_invocation"] is True
