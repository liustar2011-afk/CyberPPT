from __future__ import annotations

import json
from pathlib import Path

from script_engine.advisory_lint import advisory_findings, main
from script_engine.contracts import lint_final_script, load_banned_phrasing


def _final_script() -> dict:
    return {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {"title": "测试", "communication_goal": "说明测试内容"},
        "slides": [
            {
                "id": "P1",
                "page_type": "content",
                "title": "测试页面",
                "mission": "让受众意识到这项工作的重要性",
                "core_message": "形成明确的业务判断",
                "argument": {"pattern": "并列", "chain": ["事实A", "事实B"]},
                "full_copy": "事实A和事实B共同支撑结论。",
                "onscreen": [{"heading": "业务判断", "text": "事实A和事实B共同支撑结论"}],
                "visual_thesis": "事实A与事实B共同形成结论",
                "speaker_notes": "接下来看具体内容。",
            }
        ],
    }


def test_advisory_rule_is_not_a_hard_banned_rule() -> None:
    hard_ids = {str(rule.get("id")) for rule in load_banned_phrasing()}

    assert "authoring-intent-description" not in hard_ids
    assert "speaker-notes-host-meta" not in hard_ids
    assert "contrastive-reveal" in hard_ids
    assert "audience-facing-meta" in hard_ids


def test_advisory_findings_do_not_enter_hard_lint() -> None:
    payload = _final_script()
    warnings = advisory_findings(payload)
    hard = lint_final_script(payload)

    warning_ids = {item["rule_id"] for item in warnings}
    assert "authoring-intent-description" in warning_ids
    assert "speaker-notes-host-meta" in warning_ids
    assert not any("authoring-intent-description" in item for item in hard)
    assert not any("speaker-notes-host-meta" in item for item in hard)


def test_advisory_cli_returns_zero_with_warnings(tmp_path: Path, capsys) -> None:
    path = tmp_path / "final.json"
    path.write_text(json.dumps(_final_script(), ensure_ascii=False), encoding="utf-8")

    code = main([str(path)])
    report = json.loads(capsys.readouterr().out)

    assert code == 0
    assert report["blocking"] is False
    assert report["status"] == "warnings"
    assert report["warnings"]
