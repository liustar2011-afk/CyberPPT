from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from .version import get_version


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    passed: bool
    message: str


@dataclass(frozen=True, slots=True)
class DoctorReport:
    version: str
    python: str
    checks: tuple[DoctorCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "python": self.python,
            "passed": self.passed,
            "checks": [asdict(check) for check in self.checks],
        }


def _dependency_check(module: str, label: str) -> DoctorCheck:
    available = importlib.util.find_spec(module) is not None
    return DoctorCheck(
        f"dependency:{label}",
        available,
        f"{label} {'available' if available else 'missing'}",
    )


def _yaml_check(path: Path) -> DoctorCheck:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        passed = isinstance(data, dict) and bool(data)
        message = "valid YAML mapping" if passed else "YAML must contain a non-empty mapping"
    except Exception as exc:  # pragma: no cover - exercised through result
        passed = False
        message = f"invalid YAML: {exc}"
    return DoctorCheck(f"config:{path.name}", passed, message)


def run_doctor(repo_root: str | Path) -> DoctorReport:
    root = Path(repo_root).resolve()
    checks: list[DoctorCheck] = []

    version = get_version(root)
    checks.append(
        DoctorCheck(
            "python-version",
            sys.version_info >= (3, 11),
            f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )

    for relative in (
        "SKILL.md",
        "scripts/project_manager.py",
        "config/rules.yaml",
        "config/reporting-modes.yaml",
        "config/workflow-routes.yaml",
        "config/prompt-modules.yaml",
        "system-prompt/stage1.md",
        "system-prompt/stage1/05-deep-reading-kernel.md",
        "system-prompt/stage1/12-faithful-reading.md",
        "system-prompt/stage1/13-decision-reading.md",
        "system-prompt/stage1/14-reconciliation.md",
        "system-prompt/stage1/15-evidence-graph.md",
        "system-prompt/stage1/16-experience-retrieval.md",
        "scripts/ppt_script/experience.py",
        "knowledge/schemas/experience-case.schema.json",
        "templates/experience-feedback.json",
        "evaluations/cognition/complex-material-scorecard.yaml",
        "evaluations/experience/retrieval-scorecard.yaml",
        "system-prompt/stage2.md",
        "scripts/ppt_script/understanding.py",
        "scripts/ppt_script/cognition.py",
        "scripts/ppt_script/evidence_graph.py",
        "templates/source-analysis.md",
        "templates/understanding-gate.md",
        "templates/faithful-reading.md",
        "templates/decision-reading.md",
        "templates/reconciliation.md",
    ):
        path = root / relative
        checks.append(DoctorCheck(f"file:{relative}", path.is_file(), "present" if path.is_file() else "missing"))

    for relative in ("config/rules.yaml", "config/reporting-modes.yaml", "config/workflow-routes.yaml", "config/prompt-modules.yaml"):
        path = root / relative
        if path.is_file():
            checks.append(_yaml_check(path))

    for module, label in (
        ("yaml", "PyYAML"),
        ("docx", "python-docx"),
        ("pptx", "python-pptx"),
        ("pypdf", "pypdf"),
        ("sklearn", "scikit-learn"),
    ):
        checks.append(_dependency_check(module, label))

    try:
        from repository_consistency import check_repository

        consistency = check_repository(root)
        checks.append(
            DoctorCheck(
                "repository-consistency",
                consistency.passed,
                "PASS" if consistency.passed else "; ".join(issue.message for issue in consistency.issues),
            )
        )
    except Exception as exc:  # pragma: no cover - defensive path
        checks.append(DoctorCheck("repository-consistency", False, f"check failed: {exc}"))

    return DoctorReport(
        version=version,
        python=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        checks=tuple(checks),
    )


def render_doctor_report(report: DoctorReport) -> str:
    lines = [
        f"ppt-script {report.version} doctor: {'PASS' if report.passed else 'FAIL'}",
        f"Python: {report.python}",
    ]
    for check in report.checks:
        lines.append(f"[{'PASS' if check.passed else 'FAIL'}] {check.name}: {check.message}")
    return "\n".join(lines) + "\n"


def write_doctor_report(report: DoctorReport, output_dir: str | Path) -> tuple[Path, Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "doctor.json"
    md_path = directory / "doctor.md"
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_doctor_report(report), encoding="utf-8")
    return md_path, json_path
