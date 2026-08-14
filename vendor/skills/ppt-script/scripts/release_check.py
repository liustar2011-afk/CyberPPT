#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ppt_script.version import get_version  # noqa: E402
from repository_consistency import check_repository  # noqa: E402


@dataclass(frozen=True, slots=True)
class ReleaseStep:
    name: str
    passed: bool
    command: str
    output: str


@dataclass(frozen=True, slots=True)
class ReleaseReport:
    version: str
    quick: bool
    steps: tuple[ReleaseStep, ...]

    @property
    def passed(self) -> bool:
        return all(step.passed for step in self.steps)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "quick": self.quick,
            "passed": self.passed,
            "steps": [asdict(step) for step in self.steps],
        }


def _run(
    name: str,
    command: Sequence[str],
    *,
    cwd: Path = ROOT,
    timeout_seconds: int = 180,
) -> ReleaseStep:
    # Use a named regular file instead of PIPE or an anonymous temporary file.
    # Subprocess-heavy document tests may pass descriptors to grandchildren; a
    # regular file keeps completion independent of descriptor closure order.
    log_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as log:
            log_path = Path(log.name)
            try:
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    text=True,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=timeout_seconds,
                )
                passed = result.returncode == 0
                timeout_note = ""
            except subprocess.TimeoutExpired:
                passed = False
                timeout_note = f"TIMEOUT after {timeout_seconds}s\n"
        output = timeout_note + (log_path.read_text(encoding="utf-8", errors="replace").strip() if log_path else "")
        return ReleaseStep(name, passed, " ".join(command), output.strip())
    finally:
        if log_path is not None:
            log_path.unlink(missing_ok=True)



def run_release_check(repo_root: Path, *, quick: bool = False) -> ReleaseReport:
    root = repo_root.resolve()
    steps: list[ReleaseStep] = []

    consistency = check_repository(root)
    issues = "\n".join(f"[{item.code}] {item.path}: {item.message}" for item in consistency.issues)
    steps.append(
        ReleaseStep(
            "repository-consistency",
            consistency.passed,
            "python3 scripts/repository_consistency.py",
            issues or "PASS",
        )
    )
    steps.append(
        _run(
            "compileall",
            [sys.executable, "-m", "compileall", "-q", "scripts"],
            cwd=root,
        )
    )

    if not quick:
        steps.append(
            _run(
                "editorial-semantic-regression",
                [
                    sys.executable,
                    "-m",
                    "unittest",
                    "tests.test_v39_editorial.CecEditorialRegressionTests",
                    "-v",
                ],
                cwd=root,
            )
        )

        def verify_install() -> tuple[ReleaseStep, ReleaseStep]:
            with tempfile.TemporaryDirectory() as tmp:
                destination = Path(tmp) / "ppt-script"
                install = _run(
                    "temporary-install",
                    ["bash", "install.sh", "--target", "codex", "--codex-dir", str(destination)],
                    cwd=root,
                )
                if not install.passed:
                    return install, ReleaseStep("installed-doctor", False, "skipped", "temporary install failed")
                doctor = _run(
                    "installed-doctor",
                    [sys.executable, "scripts/project_manager.py", "doctor"],
                    cwd=destination,
                )
                return install, doctor

        def verify_tests() -> ReleaseStep:
            return _run(
                "unit-tests",
                [sys.executable, "scripts/run_tests.py"],
                cwd=root,
                timeout_seconds=300,
            )

        # Run the clean-install verification and the repository test suite in
        # independent subprocess branches. This avoids order-dependent stalls
        # observed in some sandboxed document-processing environments.
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            install_future = executor.submit(verify_install)
            tests_future = executor.submit(verify_tests)
            install_step, doctor_step = install_future.result()
            tests_step = tests_future.result()
        steps.extend((install_step, doctor_step, tests_step))

    return ReleaseReport(get_version(root), quick, tuple(steps))


def render_release_report(report: ReleaseReport) -> str:
    lines = [
        "# PPT Script Release Check",
        "",
        f"- Version: {report.version}",
        f"- Mode: {'quick' if report.quick else 'full'}",
        f"- Result: {'PASS' if report.passed else 'FAIL'}",
        "",
        "## Steps",
        "",
    ]
    for step in report.steps:
        lines.append(f"### {step.name} — {'PASS' if step.passed else 'FAIL'}")
        lines.append("")
        lines.append(f"Command: `{step.command}`")
        lines.append("")
        lines.append("```text")
        lines.append(step.output or "(no output)")
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ppt-script release verification")
    parser.add_argument("--quick", action="store_true", help="run consistency and compile checks only")
    parser.add_argument("--output-dir", default=str(ROOT / "docs"), help="directory for release-check reports")
    args = parser.parse_args(argv)

    report = run_release_check(ROOT, quick=args.quick)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "release-check.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "release-check.md").write_text(render_release_report(report), encoding="utf-8")
    print(f"ppt-script {report.version} release-check: {'PASS' if report.passed else 'FAIL'}")
    for step in report.steps:
        print(f"[{'PASS' if step.passed else 'FAIL'}] {step.name}")
    print(f"Reports: {output_dir / 'release-check.md'}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
