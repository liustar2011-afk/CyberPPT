from __future__ import annotations

import json
from pathlib import Path

from script_engine.rule_registry import (
    load_rule_registry,
    validate_default_rule_registry,
)


ROOT = Path(__file__).resolve().parents[2]
BANNED = ROOT / "contracts" / "banned-phrasing.json"


def test_default_rule_registry_is_policy_valid() -> None:
    assert validate_default_rule_registry() == []


def test_default_banned_rules_have_required_governance_metadata() -> None:
    payload = json.loads(BANNED.read_text(encoding="utf-8"))
    for rule in payload["rules"]:
        assert rule["kind"] != "project_specific"
        assert rule["severity"] in {"blocking", "warning"}
        assert rule["scope"]
        assert rule["confidence"] in {"high", "medium", "low"}
        assert rule["owner"]
        assert rule["severity_rationale"]


def test_semantic_and_style_heuristics_cannot_be_blocking() -> None:
    payload = json.loads(BANNED.read_text(encoding="utf-8"))
    heuristic = {
        rule["id"]: rule["severity"]
        for rule in payload["rules"]
        if rule["kind"] in {"semantic_heuristic", "style_heuristic"}
    }
    assert heuristic
    assert set(heuristic.values()) == {"warning"}


def test_legacy_script_quality_rules_are_not_default_enabled() -> None:
    registry = load_rule_registry()
    legacy = next(
        source for source in registry["sources"]
        if source["id"] == "legacy-script-quality"
    )
    assert legacy["profile"] == "legacy"
    assert legacy["default_enabled"] is False


def test_known_project_specific_phrases_are_absent_from_default_banned_rules() -> None:
    text = BANNED.read_text(encoding="utf-8")
    for phrase in (
        "电力行业能力建设",
        "中电联",
        "数据接入与质量治理",
        "供需模型预测",
        "课程包",
        "场景包",
    ):
        assert phrase not in text
