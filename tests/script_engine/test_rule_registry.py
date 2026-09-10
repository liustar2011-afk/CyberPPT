from __future__ import annotations

import json
from pathlib import Path

from script_engine.quality_policy import ADVISORY_CODES
from script_engine.rule_registry import (
    load_rule_registry,
    validate_default_rule_registry,
)


ROOT = Path(__file__).resolve().parents[2]
BANNED = ROOT / "contracts" / "banned-phrasing.json"
LEGACY_RULES = ROOT / "cyberppt" / "script_quality" / "rules.yaml"


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


def test_deterministic_heuristic_findings_are_registered_as_warnings() -> None:
    registry = load_rule_registry()
    findings = registry["deterministic_findings"]
    assert findings
    for finding in findings:
        assert finding["kind"] in {"semantic_heuristic", "style_heuristic"}
        assert finding["severity"] == "warning"
        assert finding["scope"]
        assert finding["confidence"] in {"high", "medium", "low"}
        assert finding["owner"]
        assert finding["severity_rationale"]


def test_runtime_advisory_codes_are_derived_from_registry_and_phrasing_rules() -> None:
    registry = load_rule_registry()
    expected = {
        finding["code"]
        for finding in registry["deterministic_findings"]
        if finding["severity"] == "warning"
    }
    banned = json.loads(BANNED.read_text(encoding="utf-8"))
    expected.update(
        rule["id"] for rule in banned["rules"] if rule["severity"] == "warning"
    )
    assert ADVISORY_CODES == frozenset(expected)


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


def test_legacy_rule_file_no_longer_contains_project_content_fingerprints() -> None:
    text = LEGACY_RULES.read_text(encoding="utf-8")
    for phrase in (
        "同意摸底≠",
        "不锁投资",
        "追溯五问",
        "哪版数据",
        "数据接入与质量治理",
        "供需模型预测",
    ):
        assert phrase not in text
    assert "cross_page_fingerprints:\n    enabled: false" in text
    assert "slogan_ban_patterns: []" in text
