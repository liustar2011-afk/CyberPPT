#!/usr/bin/env python3
"""Run the unittest suite in isolated module subprocesses.

Document-processing libraries and subprocess-heavy tests can leave inherited
file descriptors or library shutdown hooks alive after a successful in-process
suite. Running each test module in its own short-lived process prevents one
module's runtime state from blocking the complete release check.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
import re
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_RAN_RE = re.compile(r"Ran\s+(\d+)\s+tests?\b")


@dataclass(frozen=True, slots=True)
class ModuleResult:
    module: str
    returncode: int
    output: str
    count: int
    timed_out: bool = False


def discover_test_modules(root: Path = ROOT) -> tuple[str, ...]:
    tests_dir = root / "tests"
    return tuple(
        f"tests.{path.stem}"
        for path in sorted(tests_dir.glob("test_*.py"))
        if path.is_file()
    )


def _run_single_module(module: str) -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.loadTestsFromName(module)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    code = 0 if result.wasSuccessful() else 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def _run_module_subprocess(module: str, timeout_seconds: int) -> ModuleResult:
    log_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as log:
            log_path = Path(log.name)
            try:
                completed = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()), "--single-module", module],
                    cwd=ROOT,
                    text=True,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=timeout_seconds,
                )
                returncode = completed.returncode
                timed_out = False
            except subprocess.TimeoutExpired:
                returncode = 124
                timed_out = True
        output = log_path.read_text(encoding="utf-8", errors="replace") if log_path else ""
        if timed_out:
            output += f"\nTIMEOUT after {timeout_seconds}s\n"
        matches = _RAN_RE.findall(output)
        count = int(matches[-1]) if matches else 0
        return ModuleResult(module, returncode, output.strip(), count, timed_out)
    finally:
        if log_path is not None:
            log_path.unlink(missing_ok=True)


def _run_isolated(modules: tuple[str, ...], jobs: int, timeout_seconds: int) -> int:
    if jobs <= 1:
        total = 0
        failures = 0
        for module in modules:
            result = _run_module_subprocess(module, timeout_seconds)
            print(f"\n=== {module} ===", flush=True)
            if result.output:
                print(result.output, flush=True)
            total += result.count
            if result.returncode != 0:
                failures += 1
        print("\n=== TEST SUITE SUMMARY ===", flush=True)
        print(f"Ran {total} tests across {len(modules)} isolated modules", flush=True)
        if failures:
            print(f"FAILED ({failures} module{'s' if failures != 1 else ''})", flush=True)
            return 1
        print("OK", flush=True)
        return 0

    results_by_module: dict[str, ModuleResult] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as executor:
        future_map = {
            executor.submit(_run_module_subprocess, module, timeout_seconds): module
            for module in modules
        }
        for future in concurrent.futures.as_completed(future_map):
            result = future.result()
            results_by_module[result.module] = result

    total = 0
    failures = 0
    for module in modules:
        result = results_by_module[module]
        print(f"\n=== {module} ===")
        if result.output:
            print(result.output)
        total += result.count
        if result.returncode != 0:
            failures += 1

    print("\n=== TEST SUITE SUMMARY ===")
    print(f"Ran {total} tests across {len(modules)} isolated modules")
    if failures:
        print(f"FAILED ({failures} module{'s' if failures != 1 else ''})")
        return 1
    print("OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ppt-script tests in isolated module subprocesses")
    parser.add_argument("--single-module", help=argparse.SUPPRESS)
    parser.add_argument("--list", action="store_true", help="list discovered test modules and exit")
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="parallel module processes; default 1 avoids CPU and document-library contention",
    )
    parser.add_argument("--timeout", type=int, default=180, help="timeout per test module in seconds")
    args = parser.parse_args(argv)

    if args.single_module:
        return _run_single_module(args.single_module)

    modules = discover_test_modules()
    if args.list:
        print("\n".join(modules))
        return 0
    return _run_isolated(modules, args.jobs, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
