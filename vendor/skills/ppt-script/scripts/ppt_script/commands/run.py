from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..cli import audit_command, notes_check_command, plan_check_command, quality_check_command, source_inventory_command
from ..cognition import initialize_cognition, write_cognitive_audit
from ..editorial import write_editorial_audit
from ..experience import build_experience_pack
from ..pages_index import active_page_files
from ..planning import parse_plan
from ..source_truth import parse_source_truth_map
from ..semantics import write_semantic_audit
from ..understanding import write_understanding_audit
from .style import style_check_command
from ..workflow import (
    assert_assembly_allowed,
    assert_page_authoring_allowed,
    cognitive_gate_required,
    editorial_gate_required,
    recommended_rework_state,
    semantic_gate_required,
    understanding_gate_required,
    write_project_state,
)


@dataclass(frozen=True, slots=True)
class RunResult:
    status: str
    stage: str
    message: str
    outputs: tuple[Path, ...] = field(default_factory=tuple)


def _pages(project: Path) -> list[Path]:
    return active_page_files(project)


def _next_missing_page(project: Path, outline: Path) -> tuple[int, str, Path] | None:
    plan = parse_plan(outline.read_text(encoding="utf-8"))
    slides = [slide for chapter in plan.chapters for slide in chapter.slides]
    slides.extend(plan.orphan_slides)
    for slide in sorted(slides, key=lambda item: item.number):
        target = project / "pages" / f"p{slide.number:02d}-{slide.title}.md"
        if not target.is_file():
            return slide.number, slide.title, target
    return None


def run_project(
    project: Path,
    repo_root: Path,
    *,
    assemble: Callable[[str], None] | None = None,
    evidence_usage: Callable[[str], None] | None = None,
) -> RunResult:
    def done(status: str, stage: str, message: str, outputs: tuple[Path, ...] = ()) -> RunResult:
        write_project_state(project)
        return RunResult(status, stage, message, outputs)

    source_dir = project / "source"
    source_files = [path for path in source_dir.glob("**/*") if path.is_file()]
    if not source_files:
        command = f'python scripts/project_manager.py run "{project}"'
        return done("paused", "source", f"请将源材料写入目标 {source_dir}，然后运行 {command}。")

    (project / "analysis").mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = [source_inventory_command(project)]
    if semantic_gate_required(project):
        semantic_path = project / "analysis/00-semantic-understanding.md"
        semantic_text = semantic_path.read_text(encoding="utf-8", errors="ignore") if semantic_path.is_file() else ""
        if not semantic_text.strip() or "待生成" in semantic_text:
            command = f'python scripts/project_manager.py semantic-check "{project}"'
            output = project / "analysis/01-semantic-gate.json"
            return done(
                "paused",
                "semantic-understanding",
                f"请完成目标文件 {semantic_path}，运行 {command}，并生成通过的 {output}。",
                tuple(outputs),
            )
        semantic = write_semantic_audit(project)
        semantic_report = project / "analysis/01-semantic-gate.md"
        outputs.append(semantic_report)
        if not semantic.passed:
            command = f'python scripts/project_manager.py semantic-check "{project}"'
            return done(
                "paused",
                "semantic-check",
                f"请修订目标文件 {semantic_path}，运行 {command}，并使 {semantic_report.with_suffix('.json')} 通过。",
                tuple(outputs),
            )

    truth_path = project / "analysis/01-source-truth-map.md"
    if not truth_path.exists():
        command = f'python scripts/project_manager.py run "{project}"'
        return done(
            "paused",
            "source-truth",
            f"请完成目标文件 {truth_path}，然后运行 {command}。",
            tuple(outputs),
        )
    truth = parse_source_truth_map(truth_path.read_text(encoding="utf-8"))
    if not truth.items or truth.issues:
        detail = "；".join(truth.issues) if truth.issues else "没有有效的 S### 条目"
        command = f'python scripts/project_manager.py run "{project}"'
        return done(
            "paused",
            "source-truth",
            f"请修订目标文件 {truth_path}（{detail}），然后运行 {command}。",
            tuple(outputs),
        )

    if understanding_gate_required(project):
        understanding = write_understanding_audit(project)
        understanding_path = project / "analysis/02-understanding-gate.md"
        outputs.append(understanding_path)
        if not understanding.passed:
            command = f'python scripts/project_manager.py understanding-check "{project}"'
            return done(
                "paused",
                "understanding-check",
                f"请修订 analysis/00-analysis.md 与 {truth_path}，运行 {command}，并使 {understanding_path.with_suffix('.json')} 通过。",
                tuple(outputs),
            )

    if cognitive_gate_required(project):
        initialize_cognition(project, repo_root)
        cognition = write_cognitive_audit(project)
        cognitive_path = project / "review/10-cognitive-audit.md"
        outputs.append(cognitive_path)
        if not cognition.passed:
            command = f'python scripts/project_manager.py cognitive-check "{project}"'
            return done(
                "paused",
                "cognitive-check",
                f"请完成 analysis/readings/03-reconciliation.md 与 contracts/evidence-graph.json，运行 {command}，并使 {cognitive_path.with_suffix('.json')} 通过。",
                tuple(outputs),
            )

    editorial_required = editorial_gate_required(project)

    def check_editorial(phase: str, required_file: str, author_mode: str) -> RunResult | None:
        report = write_editorial_audit(project, phase)  # type: ignore[arg-type]
        report_markdown = project / f"analysis/editorial/99-{phase}-audit.md"
        outputs.append(report_markdown)
        if report.passed:
            return None
        report_json = project / f"analysis/editorial/99-{phase}-audit.json"
        pack_command = f'python scripts/project_manager.py editorial-pack "{project}" {author_mode}'
        check_command = f'python scripts/project_manager.py editorial-check "{project}" {phase}'
        business_codes = report.metrics.get("business_issue_codes", [])
        rework = recommended_rework_state(business_codes or (issue.code for issue in report.issues))
        return done(
            "paused",
            f"editorial-{author_mode}-authoring",
            f"请运行 {pack_command} 获取独立作者上下文，完成 {required_file}；随后运行 {check_command}，并使 {report_json} 通过。建议定向返工状态：{rework}。仓库未配置模型执行器，返工须由人工或外部执行器完成。",
            tuple(outputs),
        )

    if editorial_required:
        paused = check_editorial(
            "semantic-planning",
            "contracts/semantic-core.json、contracts/content-role-map.json 和 contracts/solution-model.json",
            "semantic-planning",
        )
        if paused is not None:
            return paused
        paused = check_editorial("independent", "analysis/editorial/01-independent-judgment.json", "independent")
        if paused is not None:
            return paused
        paused = check_editorial(
            "storyline-candidates",
            "analysis/editorial/storyline-candidates.json",
            "storyline-candidates",
        )
        if paused is not None:
            return paused
        paused = check_editorial(
            "storyline",
            "decision/01-decision.md、contracts/deck-decision.json 和 analysis/editorial/02-storyline-verdict.json",
            "storyline",
        )
        if paused is not None:
            return paused

    meta_path = project / "project.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    if str(meta.get("experience_mode", "enabled")) == "enabled":
        experience_pack = build_experience_pack(
            project,
            repo_root,
            limit=int(meta.get("experience_case_limit", 5) or 5),
        )
        outputs.append(experience_pack.markdown_path)

    outline = project / "outline/02-outline.md"
    if not outline.exists() or "待生成" in outline.read_text(encoding="utf-8"):
        command = f'python scripts/project_manager.py plan-check "{project}"'
        plan_output = project / "outline/02-plan-audit.json"
        return done(
            "paused",
            "outline",
            f"请先完成 outline/02-outline.md，运行 {command}，并使 {plan_output} 通过。",
            tuple(outputs),
        )
    plan_report = plan_check_command(project)
    outputs.append(plan_report)
    plan_data = json.loads(plan_report.with_suffix(".json").read_text(encoding="utf-8"))
    if not plan_data.get("passed"):
        command = f'python scripts/project_manager.py plan-check "{project}"'
        return done(
            "paused",
            "plan-check",
            f"规划检查未通过；请修订 outline/02-outline.md，运行 {command}，并使 {plan_report.with_suffix('.json')} 通过。",
            tuple(outputs),
        )

    if editorial_required:
        paused = check_editorial("outline", "analysis/editorial/03-outline-review.json", "outline")
        if paused is not None:
            return paused
        paused = check_editorial(
            "red-team-review",
            "analysis/editorial/04-red-team-review.json",
            "red-team",
        )
        if paused is not None:
            return paused
        paused = check_editorial(
            "red-team",
            "analysis/editorial/05-red-team-response.json",
            "red-team-response",
        )
        if paused is not None:
            return paused

    if editorial_required:
        try:
            assert_page_authoring_allowed(project)
        except ValueError as exc:
            return done(
                "paused",
                "authoring-approvals",
                (
                    f"{exc} "
                    f'请先完成 decision、outline、expression 人审批准，并运行 '
                    f'python scripts/project_manager.py authoring-check "{project}"。'
                ),
                tuple(outputs),
            )
    missing_page = _next_missing_page(project, outline)
    if missing_page is not None:
        number, title, target = missing_page
        command = f'python scripts/project_manager.py new-page "{project}" {number:02d} "{title}"'
        return done(
            "paused",
            "pages",
            f"请按已批准提纲运行 {command}，并完成精确目标文件 {target}。",
            tuple(outputs),
        )
    quality_report = quality_check_command(project, repo_root)
    outputs.append(quality_report)
    quality_data = json.loads(quality_report.with_suffix(".json").read_text(encoding="utf-8"))
    if not quality_data.get("passed"):
        command = f'python scripts/project_manager.py quality-check "{project}"'
        return done(
            "paused",
            "quality-check",
            f"请修订 pages/ 页面，运行 {command}，并使 {quality_report.with_suffix('.json')} 通过。",
            tuple(outputs),
        )
    audit_report = audit_command(project, repo_root)
    outputs.append(audit_report)
    audit_data = json.loads(audit_report.with_suffix(".json").read_text(encoding="utf-8"))
    blockers = any(
        audit_data.get(key)
        for key in (
            "unmapped_required_source_ids",
            "unverified_numbers",
            "missing_titles",
            "missing_missions",
            "missing_key_messages",
            "missing_source_ids",
        )
    )
    if blockers:
        command = f'python scripts/project_manager.py audit "{project}"'
        return done(
            "paused",
            "audit",
            f"请修订 pages/ 页面，运行 {command}，并使 {audit_report.with_suffix('.json')} 无阻断项。",
            tuple(outputs),
        )

    notes_report = notes_check_command(project, repo_root)
    outputs.append(notes_report)
    notes_data = json.loads(notes_report.with_suffix(".json").read_text(encoding="utf-8"))
    if not notes_data.get("passed"):
        command = f'python scripts/project_manager.py notes-check "{project}"'
        return done(
            "paused",
            "notes-check",
            f"请修订 pages/ 讲解词，运行 {command}，并使 {notes_report.with_suffix('.json')} 通过。",
            tuple(outputs),
        )

    style_report = style_check_command(project, repo_root)
    outputs.append(style_report)
    style_data = json.loads(style_report.with_suffix(".json").read_text(encoding="utf-8"))
    if not style_data.get("passed"):
        command = f'python scripts/project_manager.py style-check "{project}"'
        return done(
            "paused",
            "style-check",
            f"请修订正式文体问题，运行 {command}，并使 {style_report.with_suffix('.json')} 通过。",
            tuple(outputs),
        )

    if evidence_usage is not None:
        evidence_usage(str(project))
    if assemble is None:
        command = f'python scripts/project_manager.py assemble "{project}"'
        target = project / "output/script-final.md"
        return done("paused", "assemble", f"请运行 {command} 并生成目标文件 {target}。", tuple(outputs))
    assert_assembly_allowed(project)
    assemble(str(project))
    final_outputs = tuple(
        project / "output" / name
        for name in (
            "script-final.md",
            "script-imagegen.md",
            "outline-index.json",
            "script-speaker-notes.md",
            "speaker-notes.json",
        )
    )
    return done("completed", "assembled", "全部检查通过并完成组装。", tuple(outputs) + final_outputs)
