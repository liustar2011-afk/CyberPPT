from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


TOLERANCE = 0.002


def _rect_delta(a: dict[str, Any], b: dict[str, Any]) -> dict[str, float]:
    return {key: round(abs(float(a[key]) - float(b[key])), 4) for key in ("x", "y", "w", "h")}


def _rect_matches(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return all(delta <= TOLERANCE for delta in _rect_delta(a, b).values())


def lint_plan_layout(plan_path: Path, context_path: Path | None = None) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    layout_ref = plan.get("blueprint_layout_context") or {}
    resolved_context_path = context_path or Path(str(layout_ref.get("source", "")))
    if not resolved_context_path.is_absolute():
        resolved_context_path = Path.cwd() / resolved_context_path
    issues: list[dict[str, Any]] = []
    if not resolved_context_path.exists():
        issues.append({"code": "layout_context_missing", "path": str(resolved_context_path)})
        return _report(plan_path, resolved_context_path, issues)

    context = json.loads(resolved_context_path.read_text(encoding="utf-8"))
    checks = [
        ("safe_body_zone_in", "safe_body_zone"),
        ("so_what_band_in", "so_what_band"),
    ]
    for plan_key, context_key in checks:
        if plan_key not in layout_ref:
            issues.append({"code": "plan_layout_region_missing", "field": plan_key})
            continue
        if context_key not in context:
            issues.append({"code": "context_layout_region_missing", "field": context_key})
            continue
        if not _rect_matches(layout_ref[plan_key], context[context_key]):
            issues.append(
                {
                    "code": "plan_layout_region_drift",
                    "plan_field": plan_key,
                    "context_field": context_key,
                    "delta": _rect_delta(layout_ref[plan_key], context[context_key]),
                }
            )
    if layout_ref.get("final_text_source") != "content-lock":
        issues.append({"code": "final_text_source_not_content_lock"})
    return _report(plan_path, resolved_context_path, issues)


def _report(plan_path: Path, context_path: Path, issues: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "cyberppt.blueprint_layout_lint.v1",
        "plan": str(plan_path),
        "context": str(context_path),
        "valid": not issues,
        "issues": issues,
        "error_count": len(issues),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint a CyberPPT reconstruction plan against blueprint layout context.")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = lint_plan_layout(args.plan, args.context)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
