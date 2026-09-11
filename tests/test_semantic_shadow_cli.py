from __future__ import annotations

import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cyberppt.commands.script_runner import SCRIPT_ALIASES, script_path
from cyberppt.commands.semantic_shadow import (
    _load_source_units,
    main,
    run_semantic_shadow,
    semantic_shadow_exit_code,
)


def _report(*, legacy_blocked: bool, semantic_blocked: bool = True) -> dict:
    legacy_blockers = (
        [{"code": "LEGACY_BLOCKER", "severity": "error"}]
        if legacy_blocked
        else []
    )
    semantic_blockers = (
        ["[FINAL_NUMBER_OUTSIDE_FOUNDATION] p01/full_copy: unsupported number"]
        if semantic_blocked
        else []
    )
    return {
        "schema": "cyberppt.script_quality_semantic_shadow.v1",
        "mode": "shadow",
        "effective_gate": "legacy",
        "status": "blocked" if legacy_blocked else "passed",
        "legacy": {
            "blockers": legacy_blockers,
            "warnings": [],
            "blocker_codes": ["LEGACY_BLOCKER"] if legacy_blocked else [],
            "warning_codes": [],
        },
        "semantic_shadow": {
            "blockers": semantic_blockers,
            "reviews": [],
            "diagnostics": [],
            "blocker_codes": (
                ["FINAL_NUMBER_OUTSIDE_FOUNDATION"] if semantic_blocked else []
            ),
            "review_codes": [],
        },
        "diff": {
            "blocker_codes_only_legacy": ["LEGACY_BLOCKER"] if legacy_blocked else [],
            "blocker_codes_only_semantic": (
                ["FINAL_NUMBER_OUTSIDE_FOUNDATION"] if semantic_blocked else []
            ),
            "common_blocker_codes": [],
        },
    }


def test_semantic_shadow_is_registered_as_product_cli_alias() -> None:
    assert SCRIPT_ALIASES["semantic-shadow"] == "semantic_shadow.py"
    assert script_path("semantic-shadow").name == "semantic_shadow.py"


def test_semantic_shadow_exit_code_uses_only_legacy_gate() -> None:
    assert semantic_shadow_exit_code(
        _report(legacy_blocked=False, semantic_blocked=True)
    ) == 0
    assert semantic_shadow_exit_code(
        _report(legacy_blocked=True, semantic_blocked=False)
    ) == 1


def test_source_units_loader_accepts_jsonl() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "source-units.jsonl"
        path.write_text(
            '{"id":"SU-001","text":"A"}\n{"id":"SU-002","text":"B"}\n',
            encoding="utf-8",
        )
        units = _load_source_units(path)

    assert [unit["id"] for unit in units] == ["SU-001", "SU-002"]


def test_run_semantic_shadow_parses_existing_markdown_outline_and_source_truth() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        script_path_value = root / "script-final.md"
        outline_path = root / "outline.json"
        source_truth_path = root / "source-truth.json"
        script_path_value.write_text(
            "\n".join(
                [
                    "## 第1页：服务输出",
                    "- 页面类型：内容页",
                    "- 页面标题：服务输出",
                    "- 核心结论：来源事实用于说明服务输出。",
                    "- 完整文字稿：来源事实用于说明服务输出。",
                    "- 证据：ST001",
                    "- 上屏文字：来源事实用于说明服务输出。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        outline_path.write_text(
            json.dumps(
                {
                    "authoring_mode": "faithful",
                    "pages": [
                        {
                            "page_id": "p01",
                            "page_type": "content",
                            "source_refs": ["ST001"],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        source_truth_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "id": "ST001",
                            "statement": "来源事实用于说明服务输出。",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        report = run_semantic_shadow(
            script_path=script_path_value,
            outline_path=outline_path,
            source_truth_path=source_truth_path,
        )

    assert report["schema"] == "cyberppt.script_quality_semantic_shadow.v1"
    assert report["mode"] == "shadow"
    assert report["effective_gate"] == "legacy"
    assert isinstance(report["semantic_shadow"]["diagnostics"], list)


def test_cli_json_output_does_not_gate_on_semantic_only_blocker() -> None:
    report = _report(legacy_blocked=False, semantic_blocked=True)
    stdout = io.StringIO()
    with (
        patch(
            "cyberppt.commands.semantic_shadow.run_semantic_shadow",
            return_value=report,
        ),
        redirect_stdout(stdout),
    ):
        code = main(
            [
                "--script",
                "script-final.md",
                "--outline",
                "outline.json",
                "--source-truth",
                "source-truth.json",
                "--json",
            ]
        )

    payload = json.loads(stdout.getvalue())
    assert code == 0
    assert payload["effective_gate"] == "legacy"
    assert payload["semantic_shadow"]["blockers"]
    assert payload["legacy"]["blockers"] == []


def test_cli_persists_full_shadow_report() -> None:
    report = _report(legacy_blocked=True, semantic_blocked=False)
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "reports" / "semantic-shadow.json"
        with patch(
            "cyberppt.commands.semantic_shadow.run_semantic_shadow",
            return_value=report,
        ):
            code = main(
                [
                    "--script",
                    "script-final.md",
                    "--outline",
                    "outline.json",
                    "--source-truth",
                    "source-truth.json",
                    "--output",
                    str(output),
                ]
            )
        persisted = json.loads(output.read_text(encoding="utf-8"))

    assert code == 1
    assert persisted == report
