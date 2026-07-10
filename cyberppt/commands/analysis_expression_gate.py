"""Project-level scaffold and status for analysis-expression gates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


GATE_ORDER = (
    "reporting_direction",
    "report_structure",
    "page_design",
    "business_script",
    "drawing_script",
)


@dataclass(frozen=True)
class AnalysisExpressionStatus:
    adopted: bool
    next_gate: str | None


def _contract_path(project: Path) -> Path:
    return project.expanduser().resolve() / "workbench" / "analysis_expression" / "contract.json"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def adopt_analysis_expression_contract(project: Path) -> Path:
    contract = _contract_path(project)
    if not contract.exists():
        _write_json(
            contract,
            {
                "schema": "cyberppt.analysis_expression.v1",
                "adopted": True,
                "gates": {},
            },
        )
    return contract


def get_analysis_expression_status(project: Path) -> AnalysisExpressionStatus:
    contract = _contract_path(project)
    if not contract.exists():
        return AnalysisExpressionStatus(adopted=False, next_gate=None)
    return AnalysisExpressionStatus(adopted=True, next_gate=GATE_ORDER[0])
