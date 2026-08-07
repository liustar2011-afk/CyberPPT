from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from .source_truth import parse_source_truth_map
from .cognition import audit_cognition
from .editorial import audit_editorial
from .pages_index import active_page_files
from .semantics import audit_semantic_understanding
from .understanding import audit_source_understanding

LEGACY_WORKFLOW_STATES = (
    "INITIALIZED",
    "SOURCE_READY",
    "SEMANTIC_READY",
    "SOURCE_TRUTH_READY",
    "COGNITIVE_READY",
    "STORYLINE_READY",
    "PAGE_PLAN_READY",
    "SCRIPT_READY",
    "SCRIPT_VALIDATED",
    "VISUAL_READY",
    "DELIVERED",
)

WORKFLOW_STATES = (
    "INITIALIZED",
    "SOURCE_READY",
    "SEMANTIC_READY",
    "SOURCE_TRUTH_READY",
    "COGNITIVE_READY",
    "SEMANTIC_PLANNING_READY",
    "EDITORIAL_JUDGMENT_READY",
    "STORYLINE_CANDIDATES_READY",
    "STORYLINE_READY",
    "EDITORIAL_STORYLINE_APPROVED",
    "PAGE_PLAN_READY",
    "OUTLINE_EDITORIAL_APPROVED",
    "RED_TEAM_REVIEW_READY",
    "EDITORIAL_APPROVED",
    "SCRIPT_READY",
    "SCRIPT_VALIDATED",
    "VISUAL_READY",
    "DELIVERED",
)

REWORK_PRECEDENCE = (
    ("SEMANTIC_REWORK_REQUIRED", {"business-subject-shift", "existing-new-confusion"}),
    ("CONTENT_ROLE_REWORK_REQUIRED", {"background-overweight", "core-content-demoted"}),
    ("SOLUTION_MODEL_REWORK_REQUIRED", {"missing-solution-object", "support-over-business"}),
    ("STORYLINE_REWORK_REQUIRED", {"framework-hard-fit", "chapter-weight-distortion"}),
    ("PAGE_PLAN_REWORK_REQUIRED", {"duplicate-page", "mergeable-page", "sequence-break"}),
    ("TITLE_REWORK_REQUIRED", {"generic-title", "title-content-mismatch"}),
)


def recommended_rework_state(issue_codes: Iterable[str]) -> str:
    codes = set(issue_codes)
    if not codes:
        return "EDITORIAL_APPROVED"
    for state, routed_codes in REWORK_PRECEDENCE:
        if codes & routed_codes:
            return state
    return "EDITORIAL_REVIEW_PENDING"


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    label: str
    default_source_state: str
    default_primary_goal: str
    stages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkflowRegistry:
    source_states: dict[str, str]
    primary_goals: dict[str, str]
    task_types: dict[str, WorkflowDefinition]


@dataclass(frozen=True, slots=True)
class WorkflowRoute:
    task_type: str
    label: str
    source_state: str
    primary_goal: str
    stages: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProjectState:
    current: str
    achieved: tuple[str, ...]
    next_state: str | None
    missing_for_next: tuple[str, ...]
    evidence: dict[str, tuple[str, ...]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "current": self.current,
            "achieved": list(self.achieved),
            "next_state": self.next_state,
            "missing_for_next": list(self.missing_for_next),
            "evidence": {key: list(value) for key, value in self.evidence.items()},
        }


def _mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{key} must be a non-empty mapping")
    return value


def load_workflow_registry(path: str | Path) -> WorkflowRegistry:
    source = Path(path)
    if not source.is_file():
        raise ValueError(f"workflow registry not found: {source}")
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    source_states = {str(key): str(value) for key, value in _mapping(data, "source_states").items()}
    primary_goals = {str(key): str(value) for key, value in _mapping(data, "primary_goals").items()}
    task_types: dict[str, WorkflowDefinition] = {}
    for key, raw in _mapping(data, "task_types").items():
        if not isinstance(raw, dict):
            raise ValueError(f"task_types.{key} must be a mapping")
        stages = raw.get("stages")
        if not isinstance(stages, list) or not stages:
            raise ValueError(f"task_types.{key}.stages must be a non-empty list")
        source_state = str(raw.get("default_source_state", ""))
        goal = str(raw.get("default_primary_goal", ""))
        if source_state not in source_states:
            raise ValueError(f"task_types.{key} has unknown default_source_state: {source_state}")
        if goal not in primary_goals:
            raise ValueError(f"task_types.{key} has unknown default_primary_goal: {goal}")
        task_types[str(key)] = WorkflowDefinition(
            label=str(raw.get("label", key)),
            default_source_state=source_state,
            default_primary_goal=goal,
            stages=tuple(str(item) for item in stages),
        )
    return WorkflowRegistry(source_states, primary_goals, task_types)


def _resolve_value(value: str, mapping: dict[str, Any], field: str) -> str:
    if value not in mapping:
        supported = ", ".join(sorted(mapping))
        raise ValueError(f"unknown {field}: {value}; supported {field} values: {supported}")
    return value


def route_workflow(
    registry: WorkflowRegistry,
    *,
    task_type: str,
    source_state: str | None = None,
    primary_goal: str | None = None,
) -> WorkflowRoute:
    if task_type not in registry.task_types:
        supported = ", ".join(sorted(registry.task_types))
        raise ValueError(f"unknown task_type: {task_type}; supported task_type values: {supported}")
    definition = registry.task_types[task_type]
    resolved_source = _resolve_value(
        source_state or definition.default_source_state, registry.source_states, "source_state"
    )
    resolved_goal = _resolve_value(
        primary_goal or definition.default_primary_goal, registry.primary_goals, "primary_goal"
    )
    return WorkflowRoute(task_type, definition.label, resolved_source, resolved_goal, definition.stages)


def render_route(route: WorkflowRoute) -> str:
    lines = [
        "# PPT Script 工作流路由",
        "",
        f"- 任务类型：{route.task_type}（{route.label}）",
        f"- 材料状态：{route.source_state}",
        f"- 主要目标：{route.primary_goal}",
        "- 执行阶段：",
    ]
    lines.extend(f"  {index}. {stage}" for index, stage in enumerate(route.stages, 1))
    return "\n".join(lines) + "\n"


def update_project_route(
    project: str | Path,
    repo_root: str | Path,
    *,
    task_type: str,
    source_state: str | None = None,
    primary_goal: str | None = None,
) -> WorkflowRoute:
    project_path = Path(project)
    meta_path = project_path / "project.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"project metadata not found: {meta_path}")
    registry = load_workflow_registry(Path(repo_root) / "config/workflow-routes.yaml")
    route = route_workflow(
        registry,
        task_type=task_type,
        source_state=source_state,
        primary_goal=primary_goal,
    )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update(
        {
            "task_type": route.task_type,
            "source_state": route.source_state,
            "primary_goal": route.primary_goal,
            "workflow": list(route.stages),
        }
    )
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    analysis = project_path / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    (analysis / "00-workflow-route.json").write_text(
        json.dumps(route.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (analysis / "00-workflow-route.md").write_text(render_route(route), encoding="utf-8")
    return route


def _meaningful(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return False
    return not any(marker in text for marker in ("> 待生成", "> 待组装", "待运行（", "待运行。"))


def _source_truth_ready(project: Path) -> bool:
    path = project / "analysis/01-source-truth-map.md"
    if not _meaningful(path):
        return False
    truth = parse_source_truth_map(path.read_text(encoding="utf-8"))
    return bool(truth.items) and not truth.issues



def understanding_gate_required(project: Path) -> bool:
    meta_path = project / "project.json"
    if not meta_path.is_file():
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if "understanding_gate_required" in meta:
        return bool(meta.get("understanding_gate_required"))
    workflow = meta.get("workflow", [])
    return isinstance(workflow, list) and "source-understanding" in workflow


def semantic_gate_required(project: Path) -> bool:
    meta_path = project / "project.json"
    if not meta_path.is_file():
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(meta.get("semantic_gate_required", False))


_SIMPLE_MATERIAL_CHAR_LIMIT = 6000


def _material_is_simple(project: Path) -> bool:
    from .extractors import extract_project_sources
    from .source_truth import build_source_inventory

    try:
        bundle = extract_project_sources(project)
    except (FileNotFoundError, ImportError, OSError, ValueError):
        return False
    if not bundle.text.strip():
        return False
    inventory = build_source_inventory(bundle.text, bundle.file_names)
    if inventory.file_count != 1:
        return False
    if inventory.char_count > _SIMPLE_MATERIAL_CHAR_LIMIT:
        return False
    if inventory.state_terms or inventory.boundary_terms:
        return False
    return True


def cognitive_gate_required(project: Path) -> bool:
    meta_path = project / "project.json"
    if not meta_path.is_file():
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if "cognitive_gate_required" in meta:
        return bool(meta.get("cognitive_gate_required"))
    if "cognitive_mode" in meta:
        return str(meta.get("cognitive_mode", "legacy")) == "enhanced"
    return not _material_is_simple(project)


def editorial_gate_required(project: Path) -> bool:
    return editorial_gate_mode(project) == "required"


def editorial_gate_mode(project: Path) -> str:
    meta_path = project / "project.json"
    if not meta_path.is_file():
        return "legacy"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "migration-required"
    if not isinstance(meta, dict):
        return "migration-required"
    formal = meta.get("writing_profile") == "government-soe-formal"
    legacy_exempt = (
        meta.get("legacy_mode") is True
        or meta.get("editorial_migration_status") == "legacy-exempt"
    )
    if "editorial_gate_required" not in meta:
        return "legacy" if legacy_exempt or not formal else "migration-required"
    value = meta.get("editorial_gate_required")
    if not isinstance(value, bool):
        return "migration-required"
    if value:
        return "required"
    if formal and not legacy_exempt:
        return "migration-required"
    return "legacy"


def assert_page_authoring_allowed(project: str | Path) -> None:
    path = Path(project)
    mode = editorial_gate_mode(path)
    if mode == "legacy":
        return
    if mode == "migration-required":
        raise ValueError(
            "正式项目缺少有效 editorial_gate_required；请迁移或显式声明 legacy-exempt。"
        )
    state = evaluate_project_state(path)
    allowed = {
        "EDITORIAL_APPROVED",
        "SCRIPT_READY",
        "SCRIPT_VALIDATED",
        "VISUAL_READY",
        "DELIVERED",
    }
    if state.current not in allowed:
        detail = "；".join(state.missing_for_next[:3])
        raise ValueError(f"汇报总编闸门未批准页面写作：当前 {state.current}。{detail}")
    from .commands.approval import assert_authoring_approvals
    from .context import assert_context_fresh, assert_methodology_loaded

    assert_authoring_approvals(path)
    assert_context_fresh(path)
    assert_methodology_loaded(path)


def assert_page_approval_allowed(project: str | Path, step: str) -> None:
    normalized = step.strip().lower()
    if normalized.startswith("p") or normalized in {"evaluation", "review"}:
        assert_page_authoring_allowed(project)


def assert_assembly_allowed(project: str | Path) -> None:
    path = Path(project)
    mode = editorial_gate_mode(path)
    if mode == "legacy":
        return
    if mode == "migration-required":
        raise ValueError(
            "正式项目缺少有效 editorial_gate_required；不得组装，请先完成迁移。"
        )
    state = evaluate_project_state(path)
    if state.current not in {"SCRIPT_VALIDATED", "VISUAL_READY", "DELIVERED"}:
        detail = "；".join(state.missing_for_next[:3])
        raise ValueError(
            f"汇报总编项目尚未达到完整脚本验证状态：当前 {state.current}。{detail}"
        )


def _source_understanding_ready(project: Path) -> tuple[bool, tuple[str, ...]]:
    if not _source_truth_ready(project):
        return False, ("有效的 analysis/01-source-truth-map.md",)
    if not understanding_gate_required(project):
        return True, ()
    report = audit_source_understanding(project)
    if report.passed:
        return True, ()
    messages = tuple(issue.message for issue in report.issues[:3])
    return False, ("源材料理解闸门未通过（运行 understanding-check）", *messages)


def _semantic_ready(project: Path) -> tuple[bool, tuple[str, ...]]:
    report = audit_semantic_understanding(project)
    if report.passed:
        return True, ()
    messages = tuple(issue.message for issue in report.issues[:3])
    return False, ("全文语义理解闸门未通过（运行 semantic-check）", *messages)


def _cognition_ready(project: Path) -> tuple[bool, tuple[str, ...]]:
    if not cognitive_gate_required(project):
        return True, ()
    report = audit_cognition(project)
    if report.passed:
        return True, ()
    messages = tuple(issue.message for issue in report.issues[:3])
    return False, ("认知增强闸门未通过（运行 cognitive-check）", *messages)


def _editorial_ready(project: Path, phase: str) -> tuple[bool, tuple[str, ...]]:
    report = audit_editorial(project, phase)  # type: ignore[arg-type]
    if report.passed:
        return True, ()
    output = f"analysis/editorial/99-{phase}-audit.json"
    command = f'python scripts/project_manager.py editorial-check "{project}" {phase}'
    messages = (
        f"汇报总编阶段未通过：运行 {command}，并使 {output} 通过。",
        *(issue.message for issue in report.issues[:3]),
    )
    rework = recommended_rework_state(issue.code for issue in report.issues)
    messages = (*messages, f"建议定向返工状态：{rework}")
    return False, messages


def _page_plan_ready(project: Path) -> tuple[bool, tuple[str, ...]]:
    from .planning import audit_plan_text

    command = f'python scripts/project_manager.py plan-check "{project}"'
    plan_path = project / "outline/02-outline.md"
    if not plan_path.is_file():
        return False, (f"缺少 outline/02-outline.md",)
    try:
        truth = parse_source_truth_map(
            (project / "analysis/01-source-truth-map.md").read_text(encoding="utf-8")
        )
        formal = False
        meta_path = project / "project.json"
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            formal = (
                meta.get("writing_profile") == "government-soe-formal"
                or editorial_gate_required(project)
            )
        report = audit_plan_text(
            plan_path.read_text(encoding="utf-8"),
            truth.required_ids,
            formal_internal_reporting=formal,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return False, (f"plan-check 无法完成：运行 {command}。{exc}",)
    if report.passed:
        return True, ()
    details = tuple(issue.message for issue in report.issues[:3])
    return False, (f"plan-check 未通过：运行 {command}。", *details)


def _json_pass(path: Path, *, audit: bool = False) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if "passed" in data:
        return bool(data["passed"])
    if audit:
        blockers = (
            "unmapped_required_source_ids",
            "unverified_numbers",
            "missing_titles",
            "missing_missions",
            "missing_key_messages",
            "missing_source_ids",
            "polarity_mismatches",
        )
        return not any(data.get(key) for key in blockers)
    return False


def _script_validated(project: Path) -> bool:
    reports = (
        (project / "review/05-machine-audit.json", True),
        (project / "review/06-speaker-notes-audit.json", False),
        (project / "review/07-quality-gate.json", False),
        (project / "review/07-government-soe-style-audit.json", False),
    )
    return all(_json_pass(path, audit=audit) for path, audit in reports)


def evaluate_project_state(project: str | Path) -> ProjectState:
    path = Path(project)
    gate_mode = editorial_gate_mode(path)
    if gate_mode == "migration-required":
        return ProjectState(
            current="EDITORIAL_MIGRATION_REQUIRED",
            achieved=("INITIALIZED",) if (path / "project.json").is_file() else (),
            next_state=None,
            missing_for_next=(
                "正式项目必须声明 JSON boolean editorial_gate_required；旧项目如确需兼容须显式 legacy_mode=true 与 editorial_migration_status=legacy-exempt。",
            ),
            evidence={"EDITORIAL_MIGRATION_REQUIRED": ("project.json",)},
        )
    editorial_required = gate_mode == "required"
    workflow_states = WORKFLOW_STATES if editorial_required else LEGACY_WORKFLOW_STATES
    evidence: dict[str, tuple[str, ...]] = {"INITIALIZED": ("project.json",)}
    current_index = workflow_states.index("INITIALIZED")

    def result(
        missing: tuple[str, ...],
        *,
        next_state: str | None = None,
    ) -> ProjectState:
        return _state_result(
            current_index,
            evidence,
            missing,
            next_state=next_state,
            workflow_states=workflow_states,
        )

    source_files = tuple(
        str(item.relative_to(path)) for item in (path / "source").glob("**/*") if item.is_file()
    )
    if source_files:
        current_index = workflow_states.index("SOURCE_READY")
        evidence["SOURCE_READY"] = source_files
    else:
        return result(("source/ 中至少一份源材料",))

    semantic_required = semantic_gate_required(path)
    if semantic_required:
        semantic_ready, semantic_missing = _semantic_ready(path)
        if semantic_ready:
            current_index = workflow_states.index("SEMANTIC_READY")
            evidence["SEMANTIC_READY"] = (
                "analysis/00-semantic-understanding.md",
                "analysis/01-semantic-gate.json",
            )
        else:
            return result(semantic_missing)

    source_understanding_ready, source_missing = _source_understanding_ready(path)
    if source_understanding_ready:
        current_index = workflow_states.index("SOURCE_TRUTH_READY")
        gate_evidence = ("analysis/02-understanding-gate.json",) if understanding_gate_required(path) else ()
        evidence["SOURCE_TRUTH_READY"] = ("analysis/01-source-truth-map.md", *gate_evidence)
    else:
        return result(
            source_missing,
            next_state="SOURCE_TRUTH_READY" if not semantic_required else None,
        )

    cognition_ready, cognition_missing = _cognition_ready(path)
    if cognition_ready:
        current_index = workflow_states.index("COGNITIVE_READY")
        gate_evidence = ("review/10-cognitive-audit.json",) if cognitive_gate_required(path) else ()
        evidence["COGNITIVE_READY"] = gate_evidence or ("兼容模式：未启用认知增强闸门",)
    else:
        return result(cognition_missing)

    if editorial_required:
        semantic_planning_ready, editorial_missing = _editorial_ready(path, "semantic-planning")
        if semantic_planning_ready:
            current_index = workflow_states.index("SEMANTIC_PLANNING_READY")
            evidence["SEMANTIC_PLANNING_READY"] = (
                "analysis/editorial/99-semantic-planning-audit.json",
            )
        else:
            return result(editorial_missing)

        judgment_ready, editorial_missing = _editorial_ready(path, "independent")
        if judgment_ready:
            current_index = workflow_states.index("EDITORIAL_JUDGMENT_READY")
            evidence["EDITORIAL_JUDGMENT_READY"] = (
                "analysis/editorial/99-independent-audit.json",
            )
        else:
            return result(editorial_missing)

        candidates_ready, editorial_missing = _editorial_ready(path, "storyline-candidates")
        if candidates_ready:
            current_index = workflow_states.index("STORYLINE_CANDIDATES_READY")
            evidence["STORYLINE_CANDIDATES_READY"] = (
                "analysis/editorial/99-storyline-candidates-audit.json",
            )
        else:
            return result(editorial_missing)

    if _meaningful(path / "decision/01-decision.md"):
        current_index = workflow_states.index("STORYLINE_READY")
        evidence["STORYLINE_READY"] = ("decision/01-decision.md",)
    else:
        return result(("已完成的 decision/01-decision.md",))

    if editorial_required:
        storyline_ready, editorial_missing = _editorial_ready(path, "storyline")
        if storyline_ready:
            current_index = workflow_states.index("EDITORIAL_STORYLINE_APPROVED")
            evidence["EDITORIAL_STORYLINE_APPROVED"] = (
                "analysis/editorial/99-storyline-audit.json",
            )
        else:
            return result(editorial_missing)

    if not _meaningful(path / "outline/02-outline.md"):
        return result(("已完成的 outline/02-outline.md",))

    page_plan_evidence = ["outline/02-outline.md"]
    if editorial_required:
        plan_ready, plan_missing = _page_plan_ready(path)
        if not plan_ready:
            return result(plan_missing)
        page_plan_evidence.append("outline/02-plan-audit.json")
    current_index = workflow_states.index("PAGE_PLAN_READY")
    evidence["PAGE_PLAN_READY"] = tuple(page_plan_evidence)

    if editorial_required:
        outline_ready, editorial_missing = _editorial_ready(path, "outline")
        if outline_ready:
            current_index = workflow_states.index("OUTLINE_EDITORIAL_APPROVED")
            evidence["OUTLINE_EDITORIAL_APPROVED"] = (
                "analysis/editorial/99-outline-audit.json",
            )
        else:
            return result(editorial_missing)
        red_team_review_ready, editorial_missing = _editorial_ready(path, "red-team-review")
        if red_team_review_ready:
            current_index = workflow_states.index("RED_TEAM_REVIEW_READY")
            evidence["RED_TEAM_REVIEW_READY"] = (
                "analysis/editorial/99-red-team-review-audit.json",
            )
        else:
            return result(editorial_missing)
        red_team_ready, editorial_missing = _editorial_ready(path, "red-team")
        if red_team_ready:
            current_index = workflow_states.index("EDITORIAL_APPROVED")
            evidence["EDITORIAL_APPROVED"] = (
                "analysis/editorial/99-outline-audit.json",
                "analysis/editorial/99-red-team-review-audit.json",
                "analysis/editorial/99-red-team-audit.json",
            )
        else:
            return result(editorial_missing)

    pages = tuple(
        str(item.relative_to(path))
        for item in active_page_files(path)
        if item.name.lower().startswith("p")
    )
    if pages:
        current_index = workflow_states.index("SCRIPT_READY")
        evidence["SCRIPT_READY"] = pages
    else:
        return result(("pages/ 中至少一页脚本",))

    if _script_validated(path):
        current_index = workflow_states.index("SCRIPT_VALIDATED")
        evidence["SCRIPT_VALIDATED"] = (
            "review/05-machine-audit.json",
            "review/06-speaker-notes-audit.json",
            "review/07-quality-gate.json",
            "review/07-government-soe-style-audit.json",
        )
    else:
        return result(("四项脚本质量报告均通过",))

    if _meaningful(path / "output/script-imagegen.md"):
        current_index = workflow_states.index("VISUAL_READY")
        evidence["VISUAL_READY"] = ("output/script-imagegen.md",)
    else:
        return result(("已组装的 output/script-imagegen.md",))

    if _meaningful(path / "output/script-final.md"):
        current_index = workflow_states.index("DELIVERED")
        evidence["DELIVERED"] = ("output/script-final.md",)
        return result(())
    return result(("已组装的 output/script-final.md",))


def _state_result(
    current_index: int,
    evidence: dict[str, tuple[str, ...]],
    missing: tuple[str, ...],
    *,
    next_state: str | None = None,
    workflow_states: tuple[str, ...] = WORKFLOW_STATES,
) -> ProjectState:
    resolved_next = next_state
    if resolved_next is None and current_index + 1 < len(workflow_states):
        resolved_next = workflow_states[current_index + 1]
    return ProjectState(
        current=workflow_states[current_index],
        achieved=tuple(state for state in workflow_states[: current_index + 1] if state in evidence),
        next_state=resolved_next,
        missing_for_next=missing,
        evidence=evidence,
    )


def render_project_state(state: ProjectState) -> str:
    lines = [
        "# PPT Script 项目状态",
        "",
        f"- 当前状态：{state.current}",
        f"- 下一状态：{state.next_state or '无'}",
        "- 已达到：" + " → ".join(state.achieved),
        "",
        "## 下一步缺口",
        "",
    ]
    lines.extend(f"- {item}" for item in state.missing_for_next or ("无",))
    lines.extend(("", "## 状态依据", ""))
    for name, items in state.evidence.items():
        lines.append(f"- {name}：{', '.join(items)}")
    return "\n".join(lines) + "\n"


def write_project_state(project: str | Path) -> ProjectState:
    path = Path(project)
    state = evaluate_project_state(path)
    analysis = path / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    (analysis / "00-workflow-state.json").write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (analysis / "00-workflow-state.md").write_text(render_project_state(state), encoding="utf-8")
    meta_path = path / "project.json"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["workflow_state"] = state.current
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return state
