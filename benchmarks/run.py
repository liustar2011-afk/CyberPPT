"""Run the Task 6 Stage 01 graduation benchmark.

Shape fixtures prove routing and contract boundaries. Real-project rows prove
only the stages actually present in the repository; synthetic cases never count
toward the three-project graduation requirement.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cyberppt.source_document_map import prepare_source_context
from cyberppt.stage02_handoff import prepare_stage02_handoff
from script_engine.analysis_audits.deck_plan import audit_deck_plan
from script_engine.contracts import load_json, validate_deck_plan, validate_foundation
from script_engine.source_index import estimate_reading_load, recommend_reading_mode


DEFAULT_FIXTURE = ROOT / "tests/script_engine/fixtures/projects/task6-validation.json"
DEFAULT_REPORT = ROOT / "benchmarks/stage01_content_quality/task6-default-switch.md"
QUALITY_CASE = ROOT / "benchmarks/stage01_content_quality/cases/power-p03-p04.json"


def _shape_result(case: dict[str, Any]) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    for index, count in enumerate(case["source_char_counts"], start=1):
        source_id = f"SRC-{index:02d}"
        sources.append({"source_id": source_id, "path": f"source-{index}.md"})
        units.append({"source_id": source_id, "text": "据" * int(count), "locator": {}})
    load = estimate_reading_load(units, sources)
    strategy = recommend_reading_mode(load)
    expected = case["expected_reading_mode"]
    deep_fraction = case.get("deep_read_char_fraction")
    deep_fraction_ok = deep_fraction is None or 0.15 <= float(deep_fraction) <= 0.30
    return {
        "id": case["id"],
        "kind": case["kind"],
        "evidence_scope": case["evidence_scope"],
        "reading_load": load,
        "reading_mode": strategy["mode"],
        "expected_reading_mode": expected,
        "required_capabilities": case.get("required_capabilities", []),
        "deep_read_char_fraction": deep_fraction,
        "passed": strategy["mode"] == expected and deep_fraction_ok,
    }


def _source_artifact_boundary() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        project = Path(directory) / "project"
        source = project / "source"
        source.mkdir(parents=True)
        (source / "brief.md").write_text("# 结论\n来源事实。\n", encoding="utf-8")
        payload = prepare_source_context(project)
        files = sorted(
            str(path.relative_to(project))
            for path in project.rglob("*")
            if path.is_file() and not str(path.relative_to(project)).startswith("source/")
        )
    return {
        "status": payload.get("status"),
        "created_files": files,
        "passed": files == ["script/.cache/source-index.json"],
        "foundation_target": "script/foundation.json",
    }


def _stage02_result(project: Path) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / project.name
        (target / "script/dist").mkdir(parents=True)
        for relative in (
            "script/foundation.json",
            "script/deck-plan.json",
            "script/dist/final-script.md",
        ):
            source = project / relative
            if not source.is_file():
                return False, f"missing {relative}"
            shutil.copy2(source, target / relative)
        try:
            report = prepare_stage02_handoff(
                target, script=target / "script/dist/final-script.md"
            )
        except (OSError, ValueError) as exc:
            return False, str(exc)
    return report.get("status") == "passed", "; ".join(
        item.get("code", "unknown") for item in report.get("blocking", [])
    )


def _real_project_result(name: str) -> dict[str, Any]:
    project = ROOT / "projects" / name
    foundation_path = project / "script/foundation.json"
    plan_path = project / "script/deck-plan.json"
    script_path = project / "script/dist/final-script.md"
    missing = [
        str(path.relative_to(project))
        for path in (foundation_path, plan_path, script_path)
        if not path.is_file()
    ]
    if missing:
        return {"id": name, "missing": missing, "stage02_handoff": False}
    foundation = load_json(foundation_path)
    plan = load_json(plan_path)
    foundation_issues = validate_foundation(foundation)
    plan_issues = validate_deck_plan(plan)
    audit_issues, audit_warnings = audit_deck_plan(plan, foundation)
    handoff_ok, handoff_detail = _stage02_result(project)
    return {
        "id": name,
        "foundation_valid": not foundation_issues,
        "plan_valid": not plan_issues and not audit_issues,
        "author_present": script_path.stat().st_size > 0,
        "stage02_handoff": handoff_ok,
        "handoff_detail": handoff_detail,
        "foundation_issues": foundation_issues,
        "plan_issues": plan_issues + audit_issues,
        "plan_warnings": audit_warnings,
        "plan_contract_version": plan.get("plan_contract_version", 2),
    }


def _field_reduction() -> dict[str, Any]:
    case = load_json(QUALITY_CASE)
    inventory = case["authoring_field_inventory"]
    before = len(inventory["before_v1_p03"])
    after = len(inventory["after_v2_presented"])
    reduction = (before - after) / before
    return {"before": before, "after": after, "reduction": round(reduction, 4)}


def run_benchmark(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load_json(path)
    shape_results = [_shape_result(case) for case in fixture["shape_cases"]]
    real_results = [_real_project_result(name) for name in fixture["real_projects"]]
    requirements = fixture["graduation_requirements"]
    reached_handoff = sum(
        bool(item.get("foundation_valid"))
        and bool(item.get("plan_valid"))
        and bool(item.get("author_present"))
        and bool(item.get("stage02_handoff"))
        for item in real_results
    )
    fields = _field_reduction()
    conditions = {
        "five_shape_cases_pass": all(item["passed"] for item in shape_results),
        "three_real_projects_reach_handoff": reached_handoff
        >= requirements["real_projects_reaching_stage02_handoff"],
        "script_source_artifact_boundary": _source_artifact_boundary()["passed"],
        "script_to_strict_size_ratio_at_most_40_percent": None,
        "foundation_human_review_complete": None,
        "dual_profile_recall_non_regression": None,
        "independent_blind_review_wins_three_of_four": None,
        "authoring_fields_reduced_at_least_40_percent": fields["reduction"]
        >= requirements["minimum_field_reduction"],
        "long_selection_reviewed_at_15_to_30_percent": None,
    }
    graduated = all(value is True for value in conditions.values())
    return {
        "schema": "cyberppt.task6_benchmark.v1",
        "fixture": str(path),
        "shape_results": shape_results,
        "real_project_results": real_results,
        "real_projects_reaching_stage02_handoff": reached_handoff,
        "source_artifact_boundary": _source_artifact_boundary(),
        "field_reduction": fields,
        "conditions": conditions,
        "graduated": graduated,
        "technical_judgment": "SUPPORT WITH CONDITIONS",
        "default_plan_contract": 1 if not graduated else 2,
    }


def render_markdown(report: dict[str, Any]) -> str:
    status = "已毕业" if report["graduated"] else "尚未毕业"
    lines = [
        "# Task 6 默认切换验证",
        "",
        f"- 技术判断：`{report['technical_judgment']}`",
        f"- 结论：{status}",
        f"- 当前默认 Deck Plan 合同：v{report['default_plan_contract']}",
        "- 证据边界：合成样本只验证尺寸路由和合同能力，不计入真实项目数量或内容质量结论。",
        "",
        "## 五类验证样本",
        "",
        "| 样本 | 证据范围 | 页等价 | 阅读模式 | 结果 |",
        "|---|---|---:|---|---|",
    ]
    for item in report["shape_results"]:
        lines.append(
            f"| {item['id']} | {item['evidence_scope']} | "
            f"{item['reading_load']['page_equivalent']} | {item['reading_mode']} | "
            f"{'通过' if item['passed'] else '失败'} |"
        )
    lines.extend([
        "",
        "## 真实项目链路",
        "",
        "| 项目 | Foundation | Plan | Author | Stage 02 handoff | 说明 |",
        "|---|---|---|---|---|---|",
    ])
    for item in report["real_project_results"]:
        yes = lambda value: "通过" if value else "未通过"
        lines.append(
            f"| {item['id']} | {yes(item.get('foundation_valid'))} | "
            f"{yes(item.get('plan_valid'))} | {yes(item.get('author_present'))} | "
            f"{yes(item.get('stage02_handoff'))} | {item.get('handoff_detail') or '—'} |"
        )
    lines.extend([
        "",
        f"达到 Stage 02 handoff 的真实项目为 "
        f"{report['real_projects_reaching_stage02_handoff']}/3。",
        "",
        "## 毕业条件",
        "",
        "| 条件 | 状态 |",
        "|---|---|",
    ])
    labels = {True: "通过", False: "未通过", None: "待补证据"}
    for key, value in report["conditions"].items():
        lines.append(f"| `{key}` | {labels[value]} |")
    boundary = report["source_artifact_boundary"]
    fields = report["field_reduction"]
    lines.extend([
        "",
        "## 已验证的机械边界",
        "",
        f"- script 来源准备仅创建：`{', '.join(boundary['created_files'])}`。",
        f"- 人工计划字段由 {fields['before']} 降至 {fields['after']}，减少 "
        f"{fields['reduction']:.0%}。",
        "",
        "## 待补的内容质量证据",
        "",
        "- 增加至少两个能通过当前 Stage 02 handoff 的独立真实项目，其中一个用于补足三项目门槛。",
        "- 对同一批材料运行 script/strict 双 profile，记录结构化产物体积、关键数字、责任、条件、边界召回和来源错误。",
        "- 交付 Foundation 人工审核稿，并由独立审阅者确认 long 选区与排除理由。",
        "- 完成 v1/v2 四维盲评；现有 P03/P04 Agent 盲评保留为前置证据，不代替独立人工评审。",
        "",
        "当前生产路径统一采用 v2 lean；历史 v1 计划必须先完成迁移。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    report = run_benchmark(args.fixture)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(item["passed"] for item in report["shape_results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
