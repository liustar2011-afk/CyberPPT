from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .extractors import extract_project_sources
from .provenance_bindings import CONTEXT_FRESHNESS_TARGETS
from .workflow import evaluate_project_state

_CONTEXT_SCHEMA = "ppt-script.active-context.v2"
_CONTEXT_MODES = {"deep", "compact"}
_DEFAULT_SOURCE_CHAR_LIMIT = 120_000
_DEFAULT_ARTIFACT_CHAR_LIMIT = 120_000
_EDITORIAL_MODULE_IDS = (
    "editorial-semantic-planning",
    "editorial-independent",
    "editorial-storyline-candidates",
    "editorial-storyline",
    "editorial-outline",
    "editorial-red-team",
    "editorial-red-team-response",
)
_EDITORIAL_REVIEW_ARTIFACTS = (
    "analysis/editorial/01-independent-judgment.json",
    "analysis/editorial/storyline-candidates.json",
    "analysis/editorial/02-storyline-verdict.json",
    "analysis/editorial/03-outline-review.json",
    "analysis/editorial/04-red-team-review.json",
    "analysis/editorial/05-red-team-response.json",
)
_EDITORIAL_BASE_ARTIFACTS = frozenset(
    {
        "analysis/00-source-inventory.md",
        "analysis/00-semantic-understanding.md",
        "analysis/01-semantic-gate.md",
        "analysis/00-analysis.md",
        "analysis/01-source-truth-map.md",
        "analysis/02-understanding-gate.md",
        "contracts/semantic-core.json",
        "contracts/content-role-map.json",
        "contracts/solution-model.json",
        "contracts/source-truth.json",
    }
)
_EDITORIAL_ARTIFACT_ALLOWLISTS = {
    "editorial-semantic-planning": _EDITORIAL_BASE_ARTIFACTS,
    "editorial-independent": _EDITORIAL_BASE_ARTIFACTS,
    "editorial-storyline-candidates": _EDITORIAL_BASE_ARTIFACTS
    | {
        "analysis/editorial/01-independent-judgment.json",
    },
    "editorial-storyline": _EDITORIAL_BASE_ARTIFACTS
    | {
        "analysis/editorial/01-independent-judgment.json",
        "analysis/editorial/storyline-candidates.json",
    },
    "editorial-outline": _EDITORIAL_BASE_ARTIFACTS
    | {
        "analysis/editorial/02-storyline-verdict.json",
        "decision/01-decision.md",
        "outline/02-outline.md",
        "contracts/deck-decision.json",
        "contracts/chapter-contracts.json",
        "contracts/page-contracts.json",
    },
    "editorial-red-team": _EDITORIAL_BASE_ARTIFACTS
    | {
        "analysis/editorial/02-storyline-verdict.json",
        "outline/02-outline.md",
    },
    "editorial-red-team-response": _EDITORIAL_BASE_ARTIFACTS
    | {
        "analysis/editorial/02-storyline-verdict.json",
        "analysis/editorial/04-red-team-review.json",
        "outline/02-outline.md",
    },
}
_EDITORIAL_FRAMEWORK_REFERENCE = "knowledge/editorial-frameworks/README.md"
_EDITORIAL_CASE_REFERENCE = "analysis/editorial/00-approved-method-cases.md"
_EDITORIAL_VERDICTS = {"ACCEPT", "MERGE", "REJECT"}


@dataclass(frozen=True)
class PromptModule:
    module_id: str
    path: Path
    stage: str


@dataclass(frozen=True)
class MethodologyReferenceRegistry:
    persistent: tuple[str, ...] = ()
    by_writing_profile: dict[str, tuple[str, ...]] = field(default_factory=dict)
    by_workflow_stage: dict[str, tuple[str, ...]] = field(default_factory=dict)
    when_pages_present: tuple[str, ...] = ()


@dataclass(frozen=True)
class PromptRegistry:
    modules: dict[str, PromptModule]
    workflow_stage_modules: dict[str, tuple[str, ...]]
    state_focus: dict[str, tuple[str, ...]]
    persistent_stage1_modules: tuple[str, ...] = ()
    methodology_references: MethodologyReferenceRegistry = MethodologyReferenceRegistry()


@dataclass(frozen=True)
class ContextPack:
    schema: str
    mode: str
    state: str
    task_type: str
    workflow: tuple[str, ...]
    module_ids: tuple[str, ...]
    included_artifacts: tuple[str, ...]
    source_files: tuple[str, ...]
    source_truncated: bool
    source_characters: int
    markdown: str
    artifact_digests: dict[str, str]
    methodology_references: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "mode": self.mode,
            "state": self.state,
            "task_type": self.task_type,
            "workflow": list(self.workflow),
            "modules": list(self.module_ids),
            "methodology_references": list(self.methodology_references),
            "included_artifacts": list(self.included_artifacts),
            "source_files": list(self.source_files),
            "source_truncated": self.source_truncated,
            "source_characters": self.source_characters,
            "artifact_digests": dict(self.artifact_digests),
        }


def collect_artifact_digests(project: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for relative in CONTEXT_FRESHNESS_TARGETS:
        path = project / relative
        if path.is_file() and path.stat().st_size > 0:
            digests[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def stale_context_artifacts(project: Path) -> list[str]:
    """Return authority files that changed after the last context-pack."""
    meta_path = project / "analysis/00-active-context.json"
    if not meta_path.is_file():
        return list(CONTEXT_FRESHNESS_TARGETS)
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(CONTEXT_FRESHNESS_TARGETS)
    if not isinstance(payload, dict):
        return list(CONTEXT_FRESHNESS_TARGETS)
    recorded = payload.get("artifact_digests")
    if not isinstance(recorded, dict) or not recorded:
        # Legacy packs without digests are treated as stale once authority files exist.
        existing = [rel for rel in CONTEXT_FRESHNESS_TARGETS if (project / rel).is_file()]
        return existing
    stale: list[str] = []
    current = collect_artifact_digests(project)
    for relative, digest in current.items():
        expected = recorded.get(relative)
        if expected != digest:
            stale.append(relative)
    for relative in recorded:
        if relative in CONTEXT_FRESHNESS_TARGETS and relative not in current:
            stale.append(relative)
    return sorted(set(stale))


def assert_context_fresh(project: Path) -> None:
    if not any((project / relative).is_file() for relative in CONTEXT_FRESHNESS_TARGETS):
        return
    stale = stale_context_artifacts(project)
    if not stale:
        return
    raise ValueError(
        "活动上下文已过期（权威文本已变更，仍在使用旧的 00-active-context）。"
        "过期文件："
        + "、".join(stale)
        + '。请运行：python scripts/project_manager.py context-pack "<项目>" deep'
        "（或运行 provenance-sync，默认会自动刷新 context-pack）。"
    )


def _parse_path_list(raw: Any, *, field_name: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(f"{field_name} must be a list of relative paths")
    paths = tuple(str(item).strip().replace("\\", "/") for item in raw if str(item).strip())
    return paths


def _load_methodology_registry(payload: dict[str, Any], repo_root: Path) -> MethodologyReferenceRegistry:
    raw = payload.get("methodology_references") or {}
    if raw in ({}, None):
        return MethodologyReferenceRegistry()
    if not isinstance(raw, dict):
        raise ValueError("methodology_references must be a mapping")

    persistent = _parse_path_list(raw.get("persistent"), field_name="methodology_references.persistent")
    when_pages = _parse_path_list(
        raw.get("when_pages_present"),
        field_name="methodology_references.when_pages_present",
    )

    by_profile_raw = raw.get("by_writing_profile") or {}
    if not isinstance(by_profile_raw, dict):
        raise ValueError("methodology_references.by_writing_profile must be a mapping")
    by_profile = {
        str(profile): _parse_path_list(items, field_name=f"methodology_references.by_writing_profile.{profile}")
        for profile, items in by_profile_raw.items()
    }

    by_stage_raw = raw.get("by_workflow_stage") or {}
    if not isinstance(by_stage_raw, dict):
        raise ValueError("methodology_references.by_workflow_stage must be a mapping")
    by_stage = {
        str(stage): _parse_path_list(items, field_name=f"methodology_references.by_workflow_stage.{stage}")
        for stage, items in by_stage_raw.items()
    }

    all_paths = list(persistent) + list(when_pages)
    for paths in by_profile.values():
        all_paths.extend(paths)
    for paths in by_stage.values():
        all_paths.extend(paths)
    missing = [relative for relative in sorted(set(all_paths)) if not (repo_root / relative).is_file()]
    if missing:
        raise FileNotFoundError(
            "methodology_references path missing: " + "、".join(missing)
        )

    return MethodologyReferenceRegistry(
        persistent=persistent,
        by_writing_profile=by_profile,
        by_workflow_stage=by_stage,
        when_pages_present=when_pages,
    )


def load_prompt_registry(path: Path, repo_root: Path) -> PromptRegistry:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw_modules = payload.get("modules", {})
    if not isinstance(raw_modules, dict):
        raise ValueError("prompt module registry requires a modules mapping")
    modules: dict[str, PromptModule] = {}
    for module_id, raw in raw_modules.items():
        if not isinstance(raw, dict) or not raw.get("path") or not raw.get("stage"):
            raise ValueError(f"invalid prompt module definition: {module_id}")
        module_path = (repo_root / str(raw["path"])).resolve()
        if not module_path.is_file():
            raise FileNotFoundError(f"prompt module does not exist: {module_id} -> {module_path}")
        modules[str(module_id)] = PromptModule(str(module_id), module_path, str(raw["stage"]))

    workflow_stage_modules = {
        str(stage): tuple(str(item) for item in items)
        for stage, items in (payload.get("workflow_stage_modules", {}) or {}).items()
    }
    state_focus = {
        str(state): tuple(str(item) for item in items)
        for state, items in (payload.get("state_focus", {}) or {}).items()
    }
    persistent = tuple(str(item) for item in (payload.get("persistent_stage1_modules", []) or []))
    methodology = _load_methodology_registry(payload, repo_root)

    for mapping_name, mapping in (("workflow_stage_modules", workflow_stage_modules),):
        for key, module_ids in mapping.items():
            unknown = [module_id for module_id in module_ids if module_id not in modules]
            if unknown:
                raise ValueError(f"{mapping_name}.{key} references unknown modules: {unknown}")
    unknown_persistent = [module_id for module_id in persistent if module_id not in modules]
    if unknown_persistent:
        raise ValueError(f"persistent_stage1_modules references unknown modules: {unknown_persistent}")
    wrong_stage = [module_id for module_id in persistent if modules[module_id].stage != "stage1"]
    if wrong_stage:
        raise ValueError(f"persistent_stage1_modules must contain only stage1 modules: {wrong_stage}")
    unknown_stage_refs = [
        stage
        for stage in methodology.by_workflow_stage
        if stage not in workflow_stage_modules and stage not in _EDITORIAL_MODULE_IDS
    ]
    if unknown_stage_refs:
        raise ValueError(
            "methodology_references.by_workflow_stage references unknown stages: "
            + ", ".join(sorted(unknown_stage_refs))
        )

    return PromptRegistry(modules, workflow_stage_modules, state_focus, persistent, methodology)


def _load_meta(project: Path) -> dict[str, Any]:
    path = project / "project.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing project metadata: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("project.json must be an object")
    return payload


def _select_workflow_stages(
    registry: PromptRegistry,
    state: str,
    workflow: tuple[str, ...],
    *,
    editorial_enabled: bool,
) -> tuple[str, ...]:
    focused = registry.state_focus.get(state, ())
    editorial_focus = tuple(stage for stage in focused if stage in _EDITORIAL_MODULE_IDS)
    if editorial_enabled and editorial_focus:
        return editorial_focus
    selected = tuple(stage for stage in focused if stage in workflow)
    if selected:
        return selected
    visual_aliases = tuple(stage for stage in focused if stage.startswith("visual-"))
    if visual_aliases and any(stage.startswith("visual-") for stage in workflow):
        return tuple(stage for stage in visual_aliases if stage in workflow or stage == "visual-handoff")
    if workflow:
        return workflow[:2]
    return ()


def _resolve_mode(meta: dict[str, Any], explicit: str | None) -> str:
    mode = str(explicit or meta.get("context_mode") or "deep").lower()
    if mode not in _CONTEXT_MODES:
        raise ValueError(f"unknown context mode: {mode}; supported: deep, compact")
    return mode


def _select_modules(
    registry: PromptRegistry,
    *,
    state: str,
    workflow: tuple[str, ...],
    editorial_enabled: bool,
) -> tuple[str, ...]:
    focus_stages = _select_workflow_stages(
        registry,
        state,
        workflow,
        editorial_enabled=editorial_enabled,
    )
    selected: list[str] = []
    for workflow_stage in focus_stages:
        for module_id in registry.workflow_stage_modules.get(workflow_stage, ()):
            if module_id not in selected:
                selected.append(module_id)

    if state == "SCRIPT_VALIDATED" and any(stage.startswith("visual-") for stage in workflow):
        selected = []
        for workflow_stage in workflow:
            for module_id in registry.workflow_stage_modules.get(workflow_stage, ()):
                if module_id not in selected:
                    selected.append(module_id)

    has_stage1 = any(registry.modules[module_id].stage == "stage1" for module_id in selected)
    if has_stage1:
        selected = [*registry.persistent_stage1_modules, *selected]

    deduped: list[str] = []
    for module_id in selected:
        if module_id not in deduped:
            deduped.append(module_id)
    return tuple(deduped)


def _source_manifest(project: Path) -> tuple[str, ...]:
    source_dir = project / "source"
    if not source_dir.is_dir():
        return ()
    return tuple(
        f"source/{path.relative_to(source_dir).as_posix()}"
        for path in sorted(item for item in source_dir.rglob("*") if item.is_file())
    )


def _is_substantive_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    markers = ("> 待生成", "> 待组装", "待运行（", "待运行。")
    return not any(marker in stripped for marker in markers)


def _read_artifact(project: Path, relative: str) -> str | None:
    path = project / relative
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return text if _is_substantive_text(text) else None
        if relative in _EDITORIAL_REVIEW_ARTIFACTS and "verdict" in payload:
            verdict = str(payload.get("verdict", "")).strip().upper()
            if verdict not in _EDITORIAL_VERDICTS:
                return None
        # Empty contract scaffolds are not project facts.
        collections = (
            payload.get("sources"),
            payload.get("chapters"),
            payload.get("pages"),
            payload.get("items"),
            payload.get("judgments"),
            payload.get("candidates"),
        )
        if any(isinstance(value, list) and value for value in collections):
            return text
        if any(
            isinstance(payload.get(field), str) and payload.get(field, "").strip()
            for field in (
                "audience",
                "objective",
                "decision_request",
                "core_conclusion",
                "core_proposition",
                "solution",
                "verdict",
            )
        ):
            return text
        if relative.endswith(("understanding-gate.json", "semantic-gate.json")):
            return text
        return None
    return text if _is_substantive_text(text) else None


def _collect_artifacts(project: Path, char_limit: int) -> tuple[list[tuple[str, str]], bool]:
    candidates = [
        "analysis/00-source-inventory.md",
        "analysis/00-semantic-understanding.md",
        "analysis/01-semantic-gate.md",
        "analysis/00-analysis.md",
        "analysis/01-source-truth-map.md",
        "analysis/02-understanding-gate.md",
        "contracts/semantic-core.json",
        "contracts/content-role-map.json",
        "contracts/solution-model.json",
        "analysis/readings/03-reconciliation.md",
        "analysis/00-experience-context.md",
        "analysis/editorial/00-approved-method-cases.md",
        "contracts/evidence-graph.json",
        "review/10-cognitive-audit.md",
        "decision/01-decision.md",
        "outline/02-outline.md",
        "contracts/source-truth.json",
        "contracts/deck-decision.json",
        "contracts/chapter-contracts.json",
        "contracts/page-contracts.json",
        "analysis/editorial/01-independent-judgment.json",
        "analysis/editorial/storyline-candidates.json",
        "analysis/editorial/02-storyline-verdict.json",
        "analysis/editorial/03-outline-review.json",
        "analysis/editorial/04-red-team-review.json",
        "analysis/editorial/05-red-team-response.json",
        "review/04-review.md",
        "review/05-evaluation.md",
        "review/05-machine-audit.md",
        "review/07-quality-gate.md",
    ]
    collected: list[tuple[str, str]] = []
    used = 0
    truncated = False
    for relative in candidates:
        text = _read_artifact(project, relative)
        if text is None:
            continue
        remaining = char_limit - used
        if remaining <= 0:
            truncated = True
            break
        if len(text) > remaining:
            collected.append((relative, text[:remaining] + "\n\n[项目成果内容因上下文上限截断]"))
            truncated = True
            break
        collected.append((relative, text))
        used += len(text)
    return collected, truncated


def _selected_editorial_module(module_ids: tuple[str, ...]) -> str | None:
    selected = [module_id for module_id in module_ids if module_id in _EDITORIAL_MODULE_IDS]
    if len(selected) > 1:
        raise ValueError(f"editorial prompt stages must be isolated: {selected}")
    return selected[0] if selected else None


def _filter_editorial_artifacts(
    artifacts: list[tuple[str, str]],
    *,
    state: str,
    module_ids: tuple[str, ...],
) -> list[tuple[str, str]]:
    editorial_module = _selected_editorial_module(module_ids)
    if editorial_module is not None:
        allowed = _EDITORIAL_ARTIFACT_ALLOWLISTS[editorial_module]
        return [(relative, text) for relative, text in artifacts if relative in allowed]

    allowed_reviews: set[str] = set()
    if state == "EDITORIAL_STORYLINE_APPROVED":
        allowed_reviews.update(_EDITORIAL_REVIEW_ARTIFACTS[:3])
    elif state in {"EDITORIAL_APPROVED", "SCRIPT_READY", "SCRIPT_VALIDATED", "VISUAL_READY", "DELIVERED"}:
        allowed_reviews.update(_EDITORIAL_REVIEW_ARTIFACTS)

    return [
        (relative, text)
        for relative, text in artifacts
        if relative not in _EDITORIAL_REVIEW_ARTIFACTS or relative in allowed_reviews
    ]


def _project_has_pages(project: Path) -> bool:
    pages_dir = project / "pages"
    if not pages_dir.is_dir():
        return False
    return any(path.is_file() and path.name.startswith("p") and path.suffix.lower() == ".md" for path in pages_dir.iterdir())


def _resolve_methodology_paths(
    registry: PromptRegistry,
    *,
    writing_profile: str,
    focus_stages: tuple[str, ...],
    pages_present: bool,
    module_ids: tuple[str, ...],
) -> tuple[str, ...]:
    if not module_ids:
        return ()
    selected: list[str] = []

    def _add(paths: tuple[str, ...]) -> None:
        for relative in paths:
            if relative not in selected:
                selected.append(relative)

    has_stage1 = any(registry.modules[module_id].stage == "stage1" for module_id in module_ids)
    if has_stage1:
        _add(registry.methodology_references.persistent)
        _add(registry.methodology_references.by_writing_profile.get(writing_profile, ()))
        if pages_present:
            _add(registry.methodology_references.when_pages_present)
            # Keep full page-writing methodology available while revising existing pages,
            # even if workflow focus has returned to outline/editorial stages.
            _add(registry.methodology_references.by_workflow_stage.get("page-script", ()))
            _add(registry.methodology_references.by_workflow_stage.get("speaker-notes", ()))
    for stage in focus_stages:
        _add(registry.methodology_references.by_workflow_stage.get(stage, ()))
    return tuple(selected)


def _collect_method_references(
    artifacts: list[tuple[str, str]],
    *,
    repo_root: Path,
    registry: PromptRegistry,
    module_ids: tuple[str, ...],
    writing_profile: str,
    focus_stages: tuple[str, ...],
    pages_present: bool,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], tuple[str, ...]]:
    """Split project artifacts from methodology refs; return (artifacts, refs, ref_paths)."""
    editorial_module = _selected_editorial_module(module_ids)

    project_artifacts: list[tuple[str, str]] = []
    case_content: str | None = None
    for relative, content in artifacts:
        if relative == _EDITORIAL_CASE_REFERENCE:
            case_content = content
        else:
            project_artifacts.append((relative, content))

    references: list[tuple[str, str]] = []
    ref_paths = _resolve_methodology_paths(
        registry,
        writing_profile=writing_profile,
        focus_stages=focus_stages,
        pages_present=pages_present,
        module_ids=module_ids,
    )
    for relative in ref_paths:
        path = repo_root / relative
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            references.append((relative, text))

    if editorial_module is not None:
        framework = repo_root / _EDITORIAL_FRAMEWORK_REFERENCE
        if framework.is_file():
            text = framework.read_text(encoding="utf-8", errors="ignore").strip()
            if text and _EDITORIAL_FRAMEWORK_REFERENCE not in {item[0] for item in references}:
                references.append((_EDITORIAL_FRAMEWORK_REFERENCE, text))
        if case_content and case_content.strip():
            references.append((_EDITORIAL_CASE_REFERENCE, case_content))

    return project_artifacts, references, tuple(relative for relative, _ in references)


def _append_modules(sections: list[str], registry: PromptRegistry, module_ids: tuple[str, ...], repo_root: Path) -> None:
    sections.extend(["# 当前阶段方法", ""])
    for module_id in module_ids:
        module = registry.modules[module_id]
        relative = module.path.relative_to(repo_root)
        sections.extend(
            [
                f"---\n\n## {module_id}\n",
                f"来源：`{relative.as_posix()}`\n",
                module.path.read_text(encoding="utf-8").strip(),
                "",
            ]
        )


def _append_method_references(sections: list[str], references: list[tuple[str, str]]) -> None:
    if not references:
        return
    sections.extend(
        [
            "",
            "# 仓库方法论",
            "",
            "> 以下内容只提供写作纪律、阶段方法、编辑判断框架与反模式，不是当前项目事实，不得生成 Source ID，也不得覆盖源材料和 Source Truth Map。",
            "",
        ]
    )
    for relative, content in references:
        sections.extend([f"---\n\n## `{relative}`\n", content.strip(), ""])


def required_methodology_references(
    project: Path,
    repo_root: Path,
    *,
    state_override: str | None = None,
) -> tuple[str, ...]:
    """Return methodology paths that context-pack must embed for the current project state."""
    project = Path(project)
    repo_root = Path(repo_root)
    meta = _load_meta(project)
    registry = load_prompt_registry(repo_root / "config/prompt-modules.yaml", repo_root)
    state = state_override or evaluate_project_state(project).current
    workflow = tuple(str(value) for value in meta.get("workflow", []))
    editorial_enabled = bool(meta.get("editorial_gate_required", False))
    focus_stages = _select_workflow_stages(
        registry,
        state,
        workflow,
        editorial_enabled=editorial_enabled,
    )
    module_ids = _select_modules(
        registry,
        state=state,
        workflow=workflow,
        editorial_enabled=editorial_enabled,
    )
    return _resolve_methodology_paths(
        registry,
        writing_profile=str(meta.get("writing_profile") or ""),
        focus_stages=focus_stages,
        pages_present=_project_has_pages(project),
        module_ids=module_ids,
    )


def required_methodology_for_gate(
    project: Path,
    repo_root: Path,
) -> tuple[str, ...]:
    """Core methodology that must be present before page authoring / new-page."""
    project = Path(project)
    repo_root = Path(repo_root)
    meta = _load_meta(project)
    registry = load_prompt_registry(repo_root / "config/prompt-modules.yaml", repo_root)
    state = evaluate_project_state(project).current
    authoring_states = {
        "EDITORIAL_APPROVED",
        "SCRIPT_READY",
        "SCRIPT_VALIDATED",
        "VISUAL_READY",
        "DELIVERED",
    }
    pages_present = _project_has_pages(project)
    focus_stages: tuple[str, ...] = ()
    if state in authoring_states or pages_present:
        # Gate checks writing-profile + page-script rules, not every focus-stage expansion
        # (e.g. quality-review refs appear only after SCRIPT_READY and must not block new-page).
        focus_stages = ("page-script", "speaker-notes")
    return _resolve_methodology_paths(
        registry,
        writing_profile=str(meta.get("writing_profile") or ""),
        focus_stages=focus_stages,
        pages_present=pages_present,
        module_ids=("stage1-deep-reading-kernel", "stage1-page-script", "stage1-speaker-notes"),
    )


def default_repo_root() -> Path:
    """Repository root for the running ppt_script package (…/scripts/ppt_script → repo)."""
    return Path(__file__).resolve().parents[2]


def assert_methodology_loaded(project: Path, repo_root: Path | None = None) -> None:
    """Fail when active context omitted required repository methodology references."""
    project = Path(project)
    root = Path(repo_root) if repo_root is not None else default_repo_root()
    if not (root / "config/prompt-modules.yaml").is_file():
        raise FileNotFoundError(f"无法定位仓库根目录（缺少 config/prompt-modules.yaml）：{root}")
    required = required_methodology_for_gate(project, root)
    if not required:
        return
    meta_path = project / "analysis/00-active-context.json"
    if not meta_path.is_file():
        raise ValueError(
            "缺少活动上下文，无法确认仓库方法论已加载。"
            '请运行：python scripts/project_manager.py context-pack "<项目>" deep'
        )
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取活动上下文元数据：{exc}") from exc
    recorded = payload.get("methodology_references")
    if not isinstance(recorded, list):
        raise ValueError(
            "活动上下文未记录 methodology_references（旧版 context-pack）。"
            '请重新运行：python scripts/project_manager.py context-pack "<项目>" deep'
        )
    recorded_set = {str(item).replace("\\", "/") for item in recorded}
    missing = [relative for relative in required if relative not in recorded_set]
    if missing:
        raise ValueError(
            "活动上下文未加载完整仓库方法论："
            + "、".join(missing)
            + '。请运行：python scripts/project_manager.py context-pack "<项目>" deep'
        )


def build_context_pack(
    project: Path,
    repo_root: Path,
    *,
    state_override: str | None = None,
    mode: str | None = None,
) -> ContextPack:
    project = Path(project)
    repo_root = Path(repo_root)
    meta = _load_meta(project)
    registry = load_prompt_registry(repo_root / "config/prompt-modules.yaml", repo_root)
    state = state_override or evaluate_project_state(project).current
    workflow = tuple(str(value) for value in meta.get("workflow", []))
    context_mode = _resolve_mode(meta, mode)
    editorial_enabled = bool(meta.get("editorial_gate_required", False))
    focus_stages = _select_workflow_stages(
        registry,
        state,
        workflow,
        editorial_enabled=editorial_enabled,
    )
    module_ids = _select_modules(
        registry,
        state=state,
        workflow=workflow,
        editorial_enabled=editorial_enabled,
    )

    if _selected_editorial_module(module_ids) is not None:
        from .editorial import build_editorial_case_context

        build_editorial_case_context(project, repo_root)

    source_files = _source_manifest(project)
    source_limit = int(meta.get("context_source_char_limit") or _DEFAULT_SOURCE_CHAR_LIMIT)
    artifact_limit = int(meta.get("context_artifact_char_limit") or _DEFAULT_ARTIFACT_CHAR_LIMIT)
    source_text = ""
    source_truncated = False
    source_characters = 0
    unsupported: tuple[str, ...] = ()
    if context_mode == "deep" and source_files:
        bundle = extract_project_sources(project)
        source_characters = len(bundle.text)
        unsupported = tuple(bundle.unsupported_files)
        if len(bundle.text) > source_limit:
            source_text = bundle.text[:source_limit] + "\n\n[源材料正文因上下文上限截断；必须继续直接读取 source/ 中未覆盖部分]"
            source_truncated = True
        else:
            source_text = bundle.text

    artifacts, artifacts_truncated = _collect_artifacts(project, artifact_limit)
    experience_allowed = state not in {"INITIALIZED", "SOURCE_READY", "SEMANTIC_READY", "SOURCE_TRUTH_READY"} and str(meta.get("experience_mode", "enabled")) == "enabled"
    if not experience_allowed:
        artifacts = [(relative, text) for relative, text in artifacts if relative != "analysis/00-experience-context.md"]
    artifacts = _filter_editorial_artifacts(artifacts, state=state, module_ids=module_ids)
    writing_profile = str(meta.get("writing_profile") or "")
    pages_present = _project_has_pages(project)
    artifacts, method_references, methodology_paths = _collect_method_references(
        artifacts,
        repo_root=repo_root,
        registry=registry,
        module_ids=module_ids,
        writing_profile=writing_profile,
        focus_stages=focus_stages,
        pages_present=pages_present,
    )
    included_artifacts = list(source_files if context_mode == "deep" and source_text else ())
    included_artifacts.extend(relative for relative, _ in artifacts)
    included_artifacts.extend(methodology_paths)

    sections = [
        "# 当前活动上下文",
        "",
        f"- 上下文模式：`{context_mode}`",
        f"- 工作流状态：`{state}`",
        f"- 任务类型：`{meta.get('task_type', 'unknown')}`",
        f"- 材料状态：`{meta.get('source_state', 'unknown')}`",
        f"- 主要目标：`{meta.get('primary_goal', 'unknown')}`",
        f"- 汇报子类型：`{meta.get('report_subtype', 'unknown')}`",
        f"- 决策意图：`{meta.get('decision_intent', 'unknown')}`",
        f"- 受众层级：`{meta.get('audience_level', 'unknown')}`",
        f"- 项目阶段：`{meta.get('project_phase', 'unknown')}`",
        f"- 写作配置：`{writing_profile or '未设置'}`",
        f"- 当前工作流：{', '.join(workflow) or '未设置'}",
        f"- 本轮加载模块：{', '.join(module_ids) or '无'}",
        f"- 本轮方法论：{', '.join(methodology_paths) or '无'}",
        "",
        "> 本文件是当前工作的活动工作集，不替代源材料、Source Truth Map 或完整方法。任何结论均须回溯到 `source/` 和项目事实；权威文本变更后必须重新运行 context-pack（过期检测见 00-active-context.json 的 artifact_digests）。",
        "",
        "## 源材料清单",
        "",
    ]
    sections.extend(f"- `{name}`" for name in source_files)
    if not source_files:
        sections.append("- 暂无源材料")
    if unsupported:
        sections.extend(["", "无法自动提取正文的文件：" + "、".join(f"`{name}`" for name in unsupported)])

    if context_mode == "deep":
        sections.extend(["", "# 源材料正文", ""])
        if source_text:
            sections.append(source_text.strip())
        else:
            sections.append("当前未发现可自动提取的源材料正文。必须直接检查 `source/` 中的文件，不得仅依据文件名推断。")
    else:
        sections.extend(
            [
                "",
                "# 源材料读取要求",
                "",
                "> 本上下文未嵌入源材料正文。必须逐一读取 `source/` 中的全部文件后再作判断；compact 模式不得用于替代正式材料深度解读。",
            ]
        )

    sections.extend(["", "# 当前项目事实与阶段成果", ""])
    if artifacts:
        for relative, text in artifacts:
            sections.extend([f"---\n\n## `{relative}`\n", text.strip(), ""])
    else:
        sections.append("尚无可用的分析、事实底稿、决策稿或提纲成果。")
    if artifacts_truncated:
        sections.extend(["", "> 项目成果因上下文上限截断，必须直接读取对应文件。"])

    _append_method_references(sections, method_references)

    sections.extend(["", "# 执行约束", ""])
    sections.extend(
        [
            "1. 先核对源材料，再使用已有分析和合同；已有成果与源材料冲突时不得沿用错误成果。",
            "2. 材料理解贯穿故事线、章节、页面和优化阶段，不得在 Source Truth Map 生成后停止回查原文。",
            "3. 对状态、主体、数字、条件、边界和冲突保持逐项可追溯。",
            "4. deep 模式为正式材料默认；compact 模式仅用于已经完成事实核验后的轻量操作。",
            "5. 必须遵守本上下文「仓库方法论」与「当前阶段方法」；不得跳过已加载的正式文体与阶段规则。",
            "",
        ]
    )
    _append_modules(sections, registry, module_ids, repo_root)

    markdown = "\n".join(sections).rstrip() + "\n"
    artifact_digests = collect_artifact_digests(project)
    pack = ContextPack(
        schema=_CONTEXT_SCHEMA,
        mode=context_mode,
        state=state,
        task_type=str(meta.get("task_type", "unknown")),
        workflow=workflow,
        module_ids=module_ids,
        included_artifacts=tuple(included_artifacts),
        source_files=source_files,
        source_truncated=source_truncated,
        source_characters=source_characters,
        markdown=markdown,
        artifact_digests=artifact_digests,
        methodology_references=methodology_paths,
    )
    analysis_dir = project / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    (analysis_dir / "00-active-context.md").write_text(markdown, encoding="utf-8")
    (analysis_dir / "00-active-context.json").write_text(
        json.dumps(pack.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return pack
