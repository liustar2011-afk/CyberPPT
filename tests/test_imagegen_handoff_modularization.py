"""Freeze the pre-modularization ImageGen handoff interface and behavior."""

from __future__ import annotations

import ast
from contextlib import redirect_stderr, redirect_stdout
import importlib
import importlib.util
from io import StringIO
import json
import os
import subprocess
import sys
from dataclasses import MISSING, asdict, dataclass, fields, is_dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cyberppt.script_quality_contract import ScriptPage
from scripts.imagegen_pipeline.style_library import write_project_style_lock


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "tests" / "fixtures" / "imagegen_handoff_baseline.json"
HANDOFF_DIR = ROOT / "scripts" / "imagegen_pipeline" / "handoff"
HANDOFF_MODULE = "scripts.imagegen_pipeline.imagegen_handoff"
HANDOFF_PACKAGE = "scripts.imagegen_pipeline.handoff"
PROMPT_MODULE = "scripts.imagegen_pipeline.handoff.prompt"

BASELINE_HANDOFF_SCRIPT = """## 第1页：统一治理

- 页面类型：内容页
- 页面标题：统一治理
- 主判断：统一治理形成可追溯结果。
- 上屏结论：统一治理形成可追溯结果。
- 上屏文字：

  **统一治理**
  - 可追溯结果
"""

BASELINE_OUTPUTS = [
    "workbench",
    "workbench/prompts",
    "workbench/prompts/imagegen",
    "workbench/prompts/imagegen/baseline-imagegen-diagnostics.json",
    "workbench/prompts/imagegen/baseline-imagegen-review.md",
    "workbench/prompts/imagegen/slide-01-imagegen-draft.md",
    "workbench/scripts",
    "workbench/scripts/script-manifest.json",
    "workbench/stages",
    "workbench/stages/02-imagegen",
    "workbench/stages/02-imagegen/baseline-imagegen-script-gate.md",
]

BASELINE_HANDOFF_RESULT = {
    "p01": "workbench/prompts/imagegen/slide-01-imagegen-draft.md",
    "batch": "workbench/prompts/imagegen/baseline-imagegen-review.md",
    "diagnostics": "workbench/prompts/imagegen/baseline-imagegen-diagnostics.json",
    "gate": "workbench/stages/02-imagegen/baseline-imagegen-script-gate.md",
}

BASELINE_HELP_EXIT_CODE = 0
BASELINE_INVALID_EXIT_CODE = 2

# The migration baseline comes from the old handoff module, not from a future
# facade.  Keep this literal list intentionally small and explicit.
COMPAT_SYMBOLS = (
    "ScriptPage",
    "PresentationDecision",
    "build_page_prompt",
    "compile_page_prompt",
    "audit_page_semantic_intent",
    "render_content_first_style_contract",
    "render_page_logic_contract",
    "select_image_locked_text",
    "_page_semantic_relations",
    "write_chapter_handoff",
    "main",
)

# Literal snapshot of every non-private top-level definition/assignment in the
# pre-modularization module at commit 4b0fd6ae.  Do not derive this from the
# current facade or package: removing one legacy export must change this list
# intentionally and fail the compatibility test below.
BASE_PUBLIC_SYMBOLS = (
    "EVIDENCE_ID_RE",
    "IMAGEGEN_CANVAS_CONTRACT",
    "IMAGEGEN_CHROME_BAN_CONTRACT",
    "SEMANTIC_VISUAL_CHROME_CONTRACT",
    "CONTENT_FIRST_ONSCREEN_STORY_CONTRACT",
    "CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT",
    "CONTENT_FIRST_SEMANTIC_ONLY_WITH_LOCKED_STORY_CONTRACT",
    "CONTENT_FIRST_SHARED_PREDICATE_CONTRACT",
    "CONTENT_FIRST_VISIBLE_TEXT_WHITELIST_CONTRACT",
    "CONTENT_FIRST_PAGE_MISSION_LABEL",
    "CONTENT_FIRST_CORE_MEANING_LABEL",
    "CONTENT_FIRST_CORE_JUDGMENT_LABEL",
    "SEMANTIC_VISUAL_TEXT_CONTRACT",
    "SEMANTIC_VISUAL_FACTS_HEADER",
    "SEMANTIC_VISUAL_BRIEF_HEADER",
    "ONSCREEN_ASIDE_RE",
    "VISUAL_INTENT_SIGNALS",
    "VISUAL_INTENT_PRIORITY",
    "VISUAL_STRUCTURE_HARD_HINTS",
    "TEXT_IN_COMPOSITION_RULE",
    "DETACHED_TEXT_RAIL_AVOID",
    "VISUAL_INTENT_TEMPLATES",
    "VISUAL_PROOF_FALLBACKS",
    "NON_RENDERING_RELATION_LABELS",
    "PAGE_SEMANTIC_LEAD_PHRASE_MARKERS",
    "PAGE_SEMANTIC_STRUCTURE_LABEL_MARKERS",
    "PAGE_SEMANTIC_PHRASE_MARKERS",
    "PAGE_SEMANTIC_LABEL_MARKERS",
    "PAGE_SEMANTIC_MARKERS",
    "BUSINESS_RELATION_MARKERS",
    "MODULE_CHAIN_MARKERS",
    "resolve_page_visual_intent",
    "select_page_visual_intent_type",
    "resolve_page_semantic_intent",
    "audit_page_semantic_intent",
    "build_page_visual_intent",
    "build_page_creative_brief",
    "content_lock_text",
    "diagnostic_onscreen_text",
    "ONSCREEN_JUDGMENT_MODES",
    "resolve_onscreen_judgment_mode",
    "locked_onscreen_text",
    "MAX_IMAGE_LOCKED_LINES",
    "MAX_IMAGE_LOCKED_LINE_CHARS",
    "MAX_IMAGE_LOCKED_CHARS",
    "select_image_locked_text",
    "render_semantic_visual_brief",
    "resolve_text_render_mode",
    "render_presentation_contract",
    "STYLE_COLOR_LABELS",
    "CONTENT_FIRST_STYLE_RULE_FIELDS",
    "STYLE10_SEMANTIC_RULE_FIELDS",
    "LAYOUT_MOTIFS",
    "SCENE_ROLES",
    "VISUAL_MEDIA",
    "MOTIF_CANDIDATES",
    "DEFAULT_SCENE_ROLE_BY_MOTIF",
    "DEFAULT_SCENE_ROLE_BY_RELATION",
    "PresentationDecision",
    "resolve_visual_medium",
    "select_dense_supporting_facts",
    "resolve_presentation_decision",
    "render_content_first_style_contract",
    "resolve_visual_center",
    "render_visual_center_contract",
    "resolve_visual_carrier",
    "render_visual_carrier_contract",
    "compact_visual_structure_for_logic",
    "render_page_logic_contract",
    "render_content_first_prompt",
    "compile_page_prompt",
    "build_page_prompt",
    "write_chapter_handoff",
    "main",
)

# Literal snapshot of every non-private name visible from the module before
# modularization.  This intentionally includes imported compatibility names:
# legacy callers could access them from this module even when they were not
# defined by its business logic.
LEGACY_PUBLIC_SYMBOLS = (
    "ARTIFACT_PROMPT_COMPILER",
    "Any",
    "BUSINESS_RELATION_MARKERS",
    "CONTENT_FIRST_CORE_JUDGMENT_LABEL",
    "CONTENT_FIRST_CORE_MEANING_LABEL",
    "CONTENT_FIRST_ONSCREEN_STORY_CONTRACT",
    "CONTENT_FIRST_PAGE_MISSION_LABEL",
    "CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT",
    "CONTENT_FIRST_SEMANTIC_ONLY_WITH_LOCKED_STORY_CONTRACT",
    "CONTENT_FIRST_SHARED_PREDICATE_CONTRACT",
    "CONTENT_FIRST_STYLE_RULE_FIELDS",
    "CONTENT_FIRST_VISIBLE_TEXT_WHITELIST_CONTRACT",
    "CompiledPagePrompt",
    "CreativeBrief",
    "DEFAULT_PROMPT_COMPILER",
    "DEFAULT_SCENE_ROLE_BY_MOTIF",
    "DEFAULT_SCENE_ROLE_BY_RELATION",
    "DEFAULT_TEXT_RENDER_MODE",
    "DETACHED_TEXT_RAIL_AVOID",
    "EVIDENCE_ID_RE",
    "IMAGEGEN_CANVAS_CONTRACT",
    "IMAGEGEN_CHROME_BAN_CONTRACT",
    "LAYOUT_MOTIFS",
    "MAX_IMAGE_LOCKED_CHARS",
    "MAX_IMAGE_LOCKED_LINES",
    "MAX_IMAGE_LOCKED_LINE_CHARS",
    "MODULE_CHAIN_MARKERS",
    "MOTIF_CANDIDATES",
    "NON_RENDERING_RELATION_LABELS",
    "ONSCREEN_ASIDE_RE",
    "ONSCREEN_JUDGMENT_MODES",
    "PAGE_SEMANTIC_LABEL_MARKERS",
    "PAGE_SEMANTIC_LEAD_PHRASE_MARKERS",
    "PAGE_SEMANTIC_MARKERS",
    "PAGE_SEMANTIC_PHRASE_MARKERS",
    "PAGE_SEMANTIC_STRUCTURE_LABEL_MARKERS",
    "PROMPT_COMPILERS",
    "PageArtifactSpec",
    "PageBlock",
    "PagePromptDiagnostics",
    "PageSemanticContext",
    "Path",
    "PresentationDecision",
    "SCENE_ROLES",
    "SEMANTIC_VISUAL_BRIEF_HEADER",
    "SEMANTIC_VISUAL_CHROME_CONTRACT",
    "SEMANTIC_VISUAL_FACTS_HEADER",
    "SEMANTIC_VISUAL_TEXT_CONTRACT",
    "STYLE10_SEMANTIC_RULE_FIELDS",
    "STYLE_COLOR_LABELS",
    "ScriptPage",
    "SemanticIntentDecision",
    "TEXT_IN_COMPOSITION_RULE",
    "TEXT_RENDER_MODES",
    "VISUAL_INTENT_PRIORITY",
    "VISUAL_INTENT_SIGNALS",
    "VISUAL_INTENT_TEMPLATES",
    "VISUAL_MEDIA",
    "VISUAL_PROOF_FALLBACKS",
    "VISUAL_STRUCTURE_HARD_HINTS",
    "analyze_prompt",
    "annotations",
    "argparse",
    "assert_deliverable_prompt",
    "atomic_write_text",
    "audit_page_semantic_intent",
    "build_creative_brief",
    "build_lock",
    "build_page_creative_brief",
    "build_page_prompt",
    "build_page_visual_intent",
    "canonicalize_intent",
    "compact_visual_structure_for_logic",
    "compile_page_prompt",
    "content_lock_text",
    "dataclass",
    "derive_page_semantics",
    "diagnostic_onscreen_text",
    "json",
    "load_page_missions",
    "load_page_visual_contexts",
    "load_page_visual_intent_overrides",
    "load_project_page_artifact_specs",
    "load_style_lock",
    "locked_onscreen_text",
    "main",
    "parse_script_markdown",
    "re",
    "render_artifact_prompt",
    "render_content_first_prompt",
    "render_content_first_style_contract",
    "render_creative_brief",
    "render_page_logic_contract",
    "render_presentation_contract",
    "render_prompt",
    "render_semantic_visual_brief",
    "render_visual_carrier_contract",
    "render_visual_center_contract",
    "resolve_composition",
    "resolve_default_style",
    "resolve_judgment_mode",
    "resolve_onscreen_judgment_mode",
    "resolve_page_semantic_intent",
    "resolve_page_visual_intent",
    "resolve_presentation_decision",
    "resolve_semantic_intent",
    "resolve_text_render_mode",
    "resolve_visual_carrier",
    "resolve_visual_center",
    "resolve_visual_medium",
    "select_dense_supporting_facts",
    "select_image_locked_text",
    "select_page_visual_intent_type",
    "select_visual_carrier",
    "stage_script",
    "strip_authoring_group_marker",
    "sys",
    "validate_composition",
    "validate_prompt_compiler",
    "validate_semantic_structure",
    "validate_text_render_mode",
    "validate_visual_carrier",
    "write_batch_diagnostics",
    "write_chapter_handoff",
    "write_compiler_comparison",
)

# These are the remaining literal imports found in repository consumers before
# modularization.  They are kept separate so COMPAT_SYMBOLS remains the precise
# legacy contract above, while every real import still joins the frozen set.
REPOSITORY_IMPORT_SYMBOLS = (
    "IMAGEGEN_CANVAS_CONTRACT",
    "VISUAL_INTENT_TEMPLATES",
    "CONTENT_FIRST_ONSCREEN_STORY_CONTRACT",
    "CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT",
    "CONTENT_FIRST_SEMANTIC_ONLY_WITH_LOCKED_STORY_CONTRACT",
    "_page_missions",
    "_page_visual_contexts",
    "_page_visual_intent_overrides",
    "build_page_creative_brief",
    "build_page_visual_intent",
    "content_lock_text",
    "diagnostic_onscreen_text",
    "locked_onscreen_text",
    "resolve_presentation_decision",
    "resolve_onscreen_judgment_mode",
    "resolve_visual_medium",
    "select_dense_supporting_facts",
    "select_page_visual_intent_type",
)

FROZEN_COMPAT_SYMBOLS = BASE_PUBLIC_SYMBOLS + tuple(
    name
    for name in COMPAT_SYMBOLS + REPOSITORY_IMPORT_SYMBOLS
    if name.startswith("_")
)

PROMPT_FUNCTIONS = (
    "render_content_first_prompt",
    "compile_page_prompt",
    "build_page_prompt",
)

CONTENT_FIRST_SECTION_ORDER = (
    "【锁定关键文字】",
    "【完整上屏内容】",
    "【核心意思表达要求｜不上屏】",
    "【可读文字白名单｜硬约束】",
    "【并列语义防发散｜不上屏】",
    "【页面逻辑｜不上屏】",
    "【输出尺寸｜不上屏】",
    "【模板层禁绘｜不上屏】",
    "【视觉风格｜不上屏】",
)

TEXT_ALLOWLIST_CONTRACT = (
    "图中所有可读文字只能来自【锁定关键文字】或【完整上屏内容】中的原文字符串。"
    "页面任务、核心意思、页面逻辑、视觉结构、语义关系、演讲备注及所有“不上屏”"
    "区块只决定构图和对象关系；其中任何词句只要未在上屏白名单中逐字出现，就不得"
    "渲染、摘录、改写、缩写或组合成标题、中心结论、标签、按钮、图例、流程节点或"
    "总结框。允许用场景、对象、位置、连线、色调和视觉焦点表达这些非上屏语义。"
)

CANVAS_CONTRACT = (
    "最高优先级画布约束：输出必须严格为 2048×1024 像素（2:1）的正文内容区图片；"
    "不得输出16:9完整幻灯片。输入参考图只用于视觉风格与构图语言，不得继承参考图"
    "的画布比例。不得绘制页面标题、副标题、页码、页面序号、Logo 或页脚；标题/副"
    "标题由 PPT 模板文字层承载。"
)

TEMPLATE_BAN_CONTRACT = (
    "正文区图只画业务内容，不绘制页面标题、副标题、页码、页面序号（第N页 / Pxx / "
    "Slide N）、Logo、页脚或母版装饰线。\n"
    "标题与副标题由 PPT 模板文字层承载，不得在图内另起通栏标题区。\n"
    "【锁定关键文字】【完整上屏内容】中的业务编号与模块名（如 01｜）必须保留；"
    "禁止新增与锁定文案无关的序号条、页码章或装饰编号。"
)


@dataclass(frozen=True)
class BaselineCase:
    name: str
    page: ScriptPage
    page_mission: str
    visual_context: dict[str, str]
    visual_intent_override: dict[str, str]
    style_id: int
    text_render_mode: str


def normalize_prompt(text: str) -> str:
    return text.replace("\r\n", "\n").rstrip() + "\n"


def serialize_result(value: object) -> object:
    if hasattr(value, "to_dict"):
        return serialize_result(value.to_dict())
    if is_dataclass(value):
        return serialize_result(asdict(value))
    if isinstance(value, dict):
        return {str(key): serialize_result(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_result(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _page(
    *,
    page_id: str,
    title: str,
    main_message: str,
    onscreen_text: str,
    visual_structure: str,
    speaker_notes: str,
    visual_intent_type: str = "",
    image_locked_text: str = "",
) -> ScriptPage:
    return ScriptPage(
        page_id=page_id,
        sequence=int(page_id.removeprefix("p")),
        heading=f"第{int(page_id.removeprefix('p'))}页：{title}",
        page_type="content",
        title=title,
        main_message=main_message,
        full_prose=(
            f"{main_message}。业务关系：输入经过统一治理后形成可追溯输出，"
            "并由权限边界持续约束。"
        ),
        selection_notes="冻结模块化前的 ImageGen handoff 行为。",
        evidence_map="统一治理→S001；权限边界→S002",
        evidence_map_refs=("S001", "S002"),
        source_refs=("S001", "S002"),
        boundary_source_refs=("S002",),
        boundary="不新增输入中不存在的业务结论。",
        visual_structure=visual_structure,
        onscreen_text=onscreen_text,
        module_titles=("统一治理", "可追溯输出", "权限边界"),
        visual_intent_type=visual_intent_type,
        image_locked_text=image_locked_text,
        speaker_notes=speaker_notes,
    )


def fixed_page_inputs() -> tuple[BaselineCase, ...]:
    return (
        BaselineCase(
            name="semantic_visual",
            page=_page(
                page_id="p01",
                title="统一治理形成可追溯结果",
                main_message="统一治理把分散输入转化为可追溯业务结果。",
                onscreen_text="统一治理\n可追溯结果\n权限边界",
                visual_structure="路径转化：分散输入汇聚至治理中枢，再输出可追溯结果。",
                speaker_notes="先解释输入为何需要汇聚，再说明结果如何回溯。",
                visual_intent_type="path_chain",
            ),
            page_mission="说明统一治理如何完成输入到结果的转化。",
            visual_context={"argument_role": "solution", "page_job": "说明转化路径"},
            visual_intent_override={},
            style_id=10,
            text_render_mode="semantic_visual",
        ),
        BaselineCase(
            name="content_first",
            page=_page(
                page_id="p02",
                title="能力共同支撑业务运行",
                main_message="数据、模型、产品和安全能力共同支撑稳定业务运行。",
                onscreen_text="数据治理｜质量与授权\n模型生产｜验证与复盘\n安全运行｜权限与日志",
                visual_structure="分层支撑：数据、模型、产品与安全能力共同托底业务运行。",
                speaker_notes="强调每一层都有明确职责，不能把安全作为装饰项。",
                visual_intent_type="hierarchy_support",
            ),
            page_mission="说明支撑能力如何共同托底业务运行。",
            visual_context={"argument_role": "foundation", "page_job": "说明共同支撑"},
            visual_intent_override={},
            style_id=10,
            text_render_mode="full_image",
        ),
        BaselineCase(
            name="locked_text_style09",
            page=_page(
                page_id="p03",
                title="关键判断必须完整保留",
                main_message="受控授权让共享范围可核验、可撤销。",
                onscreen_text="受控授权\n共享范围\n可核验、可撤销",
                visual_structure="边界护栏：授权范围、有效期和撤销机制共同约束共享。",
                speaker_notes="锁定结论要靠近授权边界和撤销机制，不得另造页面标题。",
                visual_intent_type="boundary_guardrail",
                image_locked_text="受控授权\n共享范围可核验、可撤销",
            ),
            page_mission="说明受控授权如何建立共享边界。",
            visual_context={"argument_role": "governance", "page_job": "说明授权边界"},
            visual_intent_override={},
            style_id=9,
            text_render_mode="full_image",
        ),
        BaselineCase(
            name="style10_logic_and_notes",
            page=_page(
                page_id="p04",
                title="闭环运营持续校正结果",
                main_message="业务结果回流后持续校正模型与服务策略。",
                onscreen_text="业务输入\n治理与服务\n结果回流\n持续校正",
                visual_structure="闭环：业务输入进入治理与服务，结果回流后持续校正策略。",
                speaker_notes="按输入、治理、结果、回流的顺序讲解，最后落到持续校正。",
                visual_intent_type="closed_loop",
            ),
            page_mission="说明业务结果如何形成持续校正的运营闭环。",
            visual_context={"argument_role": "implementation", "page_job": "说明运营闭环"},
            visual_intent_override={},
            style_id=10,
            text_render_mode="full_image",
        ),
    )


def render_fixed_prompt(module: object, case_name: str) -> str:
    case = next(case for case in fixed_page_inputs() if case.name == case_name)
    with TemporaryDirectory() as directory:
        style_lock = write_project_style_lock(
            project=Path(directory) / f"style-{case.style_id}",
            style_id=case.style_id,
        )
        return module.build_page_prompt(
            case.page,
            style_lock,
            page_mission=case.page_mission,
            visual_context=case.visual_context,
            visual_intent_override=case.visual_intent_override,
            text_render_mode=case.text_render_mode,
        )


def _repository_handoff_imports() -> set[str]:
    imported: set[str] = set()
    for path in ROOT.rglob("*.py"):
        if any(part in {".git", "__pycache__"} for part in path.relative_to(ROOT).parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == HANDOFF_MODULE:
                imported.update(alias.name for alias in node.names)
    return imported


def _module_name(path: Path) -> str:
    if path.name == "__init__.py":
        return HANDOFF_PACKAGE
    return f"{HANDOFF_PACKAGE}.{path.stem}"


def _internal_import_targets(path: Path) -> set[str]:
    module_name = _module_name(path)
    package_name = (
        module_name if path.name == "__init__.py" else module_name.rpartition(".")[0]
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_module = node.module or ""
            if node.level:
                imported_module = importlib.util.resolve_name(
                    f"{'.' * node.level}{imported_module}",
                    package_name,
                )
            targets.add(imported_module)
            if imported_module == HANDOFF_PACKAGE:
                targets.update(
                    f"{HANDOFF_PACKAGE}.{alias.name}" for alias in node.names
                )
    return targets


def build_internal_dependency_graph(directory: Path) -> dict[str, set[str]]:
    paths = sorted(directory.glob("*.py"))
    modules = {_module_name(path): path for path in paths}
    return {
        module_name: {
            target for target in _internal_import_targets(path) if target in modules
        }
        for module_name, path in modules.items()
    }


def strongly_connected_components(
    graph: dict[str, set[str]],
) -> list[tuple[str, ...]]:
    index = 0
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal index
        indexes[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for dependency in sorted(graph[node]):
            if dependency not in indexes:
                visit(dependency)
                lowlinks[node] = min(lowlinks[node], lowlinks[dependency])
            elif dependency in on_stack:
                lowlinks[node] = min(lowlinks[node], indexes[dependency])

        if lowlinks[node] == indexes[node]:
            component: list[str] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            components.append(tuple(sorted(component)))

    for node in sorted(graph):
        if node not in indexes:
            visit(node)
    return components


def scan_for_text(directory: Path, needle: str) -> list[str]:
    return [
        path.relative_to(directory).as_posix()
        for path in sorted(directory.rglob("*.py"))
        if needle in path.read_text(encoding="utf-8")
    ]


def capture_baseline() -> dict[str, object]:
    handoff = importlib.import_module(HANDOFF_MODULE)
    cases: dict[str, object] = {}
    with TemporaryDirectory() as directory:
        root = Path(directory)
        locks = {
            style_id: write_project_style_lock(project=root / f"style-{style_id}", style_id=style_id)
            for style_id in {case.style_id for case in fixed_page_inputs()}
        }
        for case in fixed_page_inputs():
            relation, relation_source = handoff.resolve_page_visual_intent(
                case.page,
                case.page_mission,
                context=case.visual_context,
                override=case.visual_intent_override,
            )
            cases[case.name] = serialize_result(
                {
                    "input": {
                        "page": case.page,
                        "page_mission": case.page_mission,
                        "visual_context": case.visual_context,
                        "visual_intent_override": case.visual_intent_override,
                        "style_id": case.style_id,
                        "text_render_mode": case.text_render_mode,
                    },
                    "resolve_page_visual_intent": [relation, relation_source],
                    "audit_page_semantic_intent": handoff.audit_page_semantic_intent(
                        case.page,
                        case.page_mission,
                        context=case.visual_context,
                        override=case.visual_intent_override,
                    ),
                    "select_image_locked_text": handoff.select_image_locked_text(
                        case.page,
                        case.visual_context,
                    ),
                    "resolve_presentation_decision": handoff.resolve_presentation_decision(
                        case.page,
                        relation,
                    ),
                    "render_page_logic_contract": handoff.render_page_logic_contract(
                        case.page,
                        page_mission=case.page_mission,
                        visual_context=case.visual_context,
                        visual_intent_override=case.visual_intent_override,
                    ),
                    "build_page_prompt": normalize_prompt(
                        handoff.build_page_prompt(
                            case.page,
                            locks[case.style_id],
                            page_mission=case.page_mission,
                            visual_context=case.visual_context,
                            visual_intent_override=case.visual_intent_override,
                            text_render_mode=case.text_render_mode,
                        )
                    ),
                }
            )
    return {"schema": 1, "cases": cases}


class ImageGenHandoffModularizationTests(unittest.TestCase):
    def test_handoff_dependency_graph_has_no_nontrivial_scc(self) -> None:
        graph = build_internal_dependency_graph(HANDOFF_DIR)
        components = strongly_connected_components(graph)
        self.assertEqual(
            [],
            [component for component in components if len(component) > 1],
        )

    def test_internal_modules_do_not_import_legacy_facade(self) -> None:
        offenders = scan_for_text(HANDOFF_DIR, "imagegen_handoff")
        self.assertEqual([], offenders)

    def test_facade_is_small_and_contains_no_implementation(self) -> None:
        module = importlib.import_module(HANDOFF_MODULE)
        source = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertLessEqual(len(source.splitlines()), 190)

        forbidden_nodes = (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.ClassDef,
            ast.Lambda,
        )
        self.assertFalse(
            any(isinstance(node, forbidden_nodes) for node in ast.walk(tree))
        )
        self.assertFalse(
            any(
                isinstance(node, ast.ImportFrom)
                and any(alias.name == "*" for alias in node.names)
                for node in ast.walk(tree)
            )
        )

        docstrings = [
            node
            for node in tree.body
            if isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ]
        self.assertEqual([tree.body[0]], docstrings)

        assignments = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr))
        ]
        self.assertEqual(1, len(assignments))
        all_assignment = assignments[0]
        self.assertIsInstance(all_assignment, ast.Assign)
        self.assertEqual(1, len(all_assignment.targets))
        self.assertIsInstance(all_assignment.targets[0], ast.Name)
        self.assertEqual("__all__", all_assignment.targets[0].id)
        self.assertIsInstance(all_assignment.value, ast.Tuple)
        self.assertTrue(
            all(
                isinstance(item, ast.Constant) and isinstance(item.value, str)
                for item in all_assignment.value.elts
            )
        )
        exported_names = [item.value for item in all_assignment.value.elts]
        self.assertEqual(len(exported_names), len(set(exported_names)))

        expected_compatibility_ifs = ast.parse(
            """
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

if __name__ == "__main__":
    raise SystemExit(main())
"""
        ).body
        compatibility_ifs = [node for node in tree.body if isinstance(node, ast.If)]
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in expected_compatibility_ifs],
            [ast.dump(node, include_attributes=False) for node in compatibility_ifs],
        )

        allowed_top_level = (
            ast.Expr,
            ast.Import,
            ast.ImportFrom,
            ast.Assign,
            ast.If,
        )
        self.assertTrue(all(isinstance(node, allowed_top_level) for node in tree.body))
        self.assertEqual(1, sum(isinstance(node, ast.Expr) for node in tree.body))

        allowed_call_ids = {
            id(node)
            for compatibility_if in compatibility_ifs
            for node in ast.walk(compatibility_if)
            if isinstance(node, ast.Call)
        }
        actual_call_ids = {
            id(node) for node in ast.walk(tree) if isinstance(node, ast.Call)
        }
        self.assertEqual(allowed_call_ids, actual_call_ids)

    def test_legacy_facade_exports_complete_base_public_surface(self) -> None:
        legacy = importlib.import_module(HANDOFF_MODULE)
        exported = set(getattr(legacy, "__all__", ()))
        self.assertEqual(74, len(BASE_PUBLIC_SYMBOLS))
        self.assertEqual(set(), set(BASE_PUBLIC_SYMBOLS) - exported)
        self.assertTrue(all(hasattr(legacy, name) for name in BASE_PUBLIC_SYMBOLS))

        star_namespace: dict[str, object] = {}
        exec(f"from {HANDOFF_MODULE} import *", {}, star_namespace)
        self.assertEqual(set(), set(BASE_PUBLIC_SYMBOLS) - set(star_namespace))

    def test_legacy_facade_preserves_complete_pre_modularization_public_surface(self) -> None:
        legacy = importlib.import_module(HANDOFF_MODULE)
        self.assertEqual(125, len(LEGACY_PUBLIC_SYMBOLS))
        self.assertEqual(len(LEGACY_PUBLIC_SYMBOLS), len(set(LEGACY_PUBLIC_SYMBOLS)))
        self.assertEqual(set(LEGACY_PUBLIC_SYMBOLS), set(getattr(legacy, "__all__", ())))
        self.assertTrue(all(hasattr(legacy, name) for name in LEGACY_PUBLIC_SYMBOLS))

        star_namespace: dict[str, object] = {}
        exec(f"from {HANDOFF_MODULE} import *", {}, star_namespace)
        self.assertEqual(set(LEGACY_PUBLIC_SYMBOLS), set(star_namespace))

    def test_delivery_and_cli_are_direct_reexports(self) -> None:
        legacy = importlib.import_module(HANDOFF_MODULE)
        delivery = importlib.import_module("scripts.imagegen_pipeline.handoff.delivery")
        cli = importlib.import_module("scripts.imagegen_pipeline.handoff.cli")
        self.assertIs(legacy.write_chapter_handoff, delivery.write_chapter_handoff)
        self.assertIs(legacy.main, cli.main)

    def test_write_chapter_handoff_preserves_relative_outputs(self) -> None:
        delivery = importlib.import_module("scripts.imagegen_pipeline.handoff.delivery")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            script = root / "script.md"
            script.write_text(BASELINE_HANDOFF_SCRIPT, encoding="utf-8")
            style_lock = write_project_style_lock(
                project=root / "style",
                style_id=10,
            )

            result = delivery.write_chapter_handoff(
                project=project,
                script=script,
                style_lock=style_lock,
                pages=[1],
                batch_name="baseline",
                prompt_compiler="content-first-v1",
            )

            self.assertEqual(
                BASELINE_OUTPUTS,
                sorted(path.relative_to(project).as_posix() for path in project.rglob("*")),
            )
            self.assertEqual(
                BASELINE_HANDOFF_RESULT,
                {key: path.relative_to(project).as_posix() for key, path in result.items()},
            )

            draft = (project / "workbench/prompts/imagegen/slide-01-imagegen-draft.md").read_text(
                encoding="utf-8"
            )
            self.assertTrue(draft.startswith("【锁定关键文字】\n统一治理\n可追溯结果\n"))
            self.assertIn("【完整上屏内容】", draft)
            self.assertIn("【输出尺寸｜不上屏】", draft)
            self.assertIn("最高优先级画布约束：输出必须严格为 2048×1024 像素（2:1）", draft)

            review = (project / "workbench/prompts/imagegen/baseline-imagegen-review.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("# ImageGen 送图脚本审阅稿 · baseline", review)
            self.assertIn("## 第1页：统一治理", review)
            self.assertIn("Prompt compiler: `content-first-v1`", review)
            self.assertIn("Visual structure mode: `off`", review)

            diagnostics = json.loads(
                (project / "workbench/prompts/imagegen/baseline-imagegen-diagnostics.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual("cyberppt.imagegen_prompt_diagnostics.v2", diagnostics["schema"])
            self.assertEqual("baseline", diagnostics["batch_name"])
            self.assertEqual(1, diagnostics["summary"]["page_count"])
            self.assertEqual("p01", diagnostics["pages"][0]["page_id"])
            self.assertEqual("统一治理", diagnostics["pages"][0]["title"])
            self.assertTrue(diagnostics["pages"][0]["locked_text_preserved"])

            manifest = json.loads(
                (project / "workbench/scripts/script-manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual("cyberppt.script_manifest.v1", manifest["schema"])
            self.assertEqual(
                {
                    "slide": 1,
                    "kind": "imagegen",
                    "phase": "draft",
                    "note": "baseline imagegen handoff draft for review",
                    "requires_user_review_before_generation": True,
                },
                {
                    key: manifest["entries"][0][key]
                    for key in (
                        "slide",
                        "kind",
                        "phase",
                        "note",
                        "requires_user_review_before_generation",
                    )
                },
            )
            self.assertTrue(manifest["entries"][0]["source"].endswith("_tmp_slide-01-imagegen.md"))
            self.assertTrue(manifest["entries"][0]["saved_path"].endswith("slide-01-imagegen-draft.md"))

            gate = (project / "workbench/stages/02-imagegen/baseline-imagegen-script-gate.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("# ImageGen 送图脚本门禁 · baseline", gate)
            self.assertIn("status: waiting_for_user_modify_or_approve", gate)
            self.assertIn("用户批准前不得调用 ImageGen / final-script-pages --production-build", gate)

    def test_main_help_and_invalid_input_keep_exit_contract(self) -> None:
        cli = importlib.import_module("scripts.imagegen_pipeline.handoff.cli")
        help_stdout = StringIO()
        with redirect_stdout(help_stdout), self.assertRaises(SystemExit) as help_exit:
            cli.main(["--help"])
        self.assertEqual(BASELINE_HELP_EXIT_CODE, help_exit.exception.code)
        self.assertIn("usage:", help_stdout.getvalue())
        self.assertIn("--prompt-compiler", help_stdout.getvalue())

        invalid_stderr = StringIO()
        with redirect_stderr(invalid_stderr), self.assertRaises(SystemExit) as invalid_exit:
            cli.main(["--missing-input"])
        self.assertEqual(BASELINE_INVALID_EXIT_CODE, invalid_exit.exception.code)
        self.assertIn("usage:", invalid_stderr.getvalue())
        self.assertIn("the following arguments are required", invalid_stderr.getvalue())

    def test_main_success_preserves_output_lines(self) -> None:
        cli = importlib.import_module("scripts.imagegen_pipeline.handoff.cli")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            script = root / "script.md"
            script.write_text(BASELINE_HANDOFF_SCRIPT, encoding="utf-8")
            style_lock = write_project_style_lock(project=root / "style", style_id=10)
            stdout = StringIO()

            with redirect_stdout(stdout):
                result = cli.main(
                    [
                        str(project),
                        "--script",
                        str(script),
                        "--style-lock",
                        str(style_lock),
                        "--pages",
                        "1",
                        "--batch-name",
                        "baseline",
                        "--prompt-compiler",
                        "content-first-v1",
                    ]
                )

            self.assertEqual(0, result)
            output = stdout.getvalue()
            self.assertIn("batch_review=", output)
            self.assertIn("diagnostics=", output)
            self.assertIn("gate=", output)
            self.assertIn("p01=", output)
            self.assertIn("baseline-imagegen-review.md", output)
            self.assertIn("baseline-imagegen-diagnostics.json", output)
            self.assertIn("baseline-imagegen-script-gate.md", output)
            self.assertIn("slide-01-imagegen-draft.md", output)

    def test_legacy_script_help_keeps_direct_execution_compatibility(self) -> None:
        completed = subprocess.run(
            [sys.executable, ROOT / "scripts" / "imagegen_pipeline" / "imagegen_handoff.py", "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(BASELINE_HELP_EXIT_CODE, completed.returncode)
        self.assertIn("usage:", completed.stdout)

    def test_prompt_functions_are_direct_reexports(self) -> None:
        legacy = importlib.import_module(HANDOFF_MODULE)
        prompt = importlib.import_module(PROMPT_MODULE)
        for name in PROMPT_FUNCTIONS:
            with self.subTest(name=name):
                self.assertIs(getattr(legacy, name), getattr(prompt, name))

    def test_page_prompts_match_frozen_baseline_verbatim(self) -> None:
        prompt = importlib.import_module(PROMPT_MODULE)
        expected = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["cases"]
        for case in fixed_page_inputs():
            with self.subTest(case=case.name):
                actual = normalize_prompt(render_fixed_prompt(prompt, case.name))
                self.assertEqual(expected[case.name]["build_page_prompt"], actual)

    def test_content_first_prompt_keeps_nine_sections_in_order(self) -> None:
        prompt = importlib.import_module(PROMPT_MODULE)
        result = render_fixed_prompt(prompt, "content_first")
        actual = tuple(
            line
            for line in result.splitlines()
            if line.startswith("【") and line.endswith("】")
        )
        self.assertEqual(CONTENT_FIRST_SECTION_ORDER, actual)

    def test_content_first_prompt_keeps_text_allowlist_contract(self) -> None:
        prompt = importlib.import_module(PROMPT_MODULE)
        result = render_fixed_prompt(prompt, "content_first")
        self.assertIn(TEXT_ALLOWLIST_CONTRACT, result)

    def test_content_first_prompt_keeps_canvas_contract(self) -> None:
        prompt = importlib.import_module(PROMPT_MODULE)
        result = render_fixed_prompt(prompt, "content_first")
        self.assertIn(CANVAS_CONTRACT, result)

    def test_content_first_prompt_keeps_template_ban_contract(self) -> None:
        prompt = importlib.import_module(PROMPT_MODULE)
        result = render_fixed_prompt(prompt, "content_first")
        self.assertIn(TEMPLATE_BAN_CONTRACT, result)

    def test_presentation_decision_is_not_wrapped(self) -> None:
        legacy = importlib.import_module(
            "scripts.imagegen_pipeline.imagegen_handoff"
        )
        presentation = importlib.import_module(
            "scripts.imagegen_pipeline.handoff.presentation"
        )
        self.assertIs(legacy.PresentationDecision, presentation.PresentationDecision)
        self.assertIs(
            legacy.resolve_presentation_decision,
            presentation.resolve_presentation_decision,
        )
        self.assertIs(
            legacy.render_presentation_contract,
            presentation.render_presentation_contract,
        )

    def test_presentation_decision_fields_keep_the_frozen_order_and_defaults(self) -> None:
        presentation = importlib.import_module(
            "scripts.imagegen_pipeline.handoff.presentation"
        )
        snapshot = tuple(
            (
                field.name,
                field.default is MISSING,
                None if field.default is MISSING else field.default,
            )
            for field in fields(presentation.PresentationDecision)
        )
        self.assertEqual(
            (
                ("layout_motif", True, None),
                ("scene_role", True, None),
                ("source", True, None),
                ("reason", True, None),
                ("visual_medium", False, "editorial_typographic"),
            ),
            snapshot,
        )

    def test_semantic_and_text_functions_are_direct_reexports(self) -> None:
        legacy = importlib.import_module(
            "scripts.imagegen_pipeline.imagegen_handoff"
        )
        semantics = importlib.import_module(
            "scripts.imagegen_pipeline.handoff.semantics"
        )
        text = importlib.import_module("scripts.imagegen_pipeline.handoff.text")
        self.assertIs(
            legacy.audit_page_semantic_intent,
            semantics.audit_page_semantic_intent,
        )
        self.assertIs(
            legacy.build_page_visual_intent,
            semantics.build_page_visual_intent,
        )
        self.assertIs(
            legacy.select_image_locked_text,
            text.select_image_locked_text,
        )
        self.assertIs(legacy.content_lock_text, text.content_lock_text)

    def test_contract_constants_are_direct_reexports(self) -> None:
        legacy = importlib.import_module(HANDOFF_MODULE)
        contracts = importlib.import_module(
            "scripts.imagegen_pipeline.handoff.contracts"
        )
        self.assertEqual(
            legacy.IMAGEGEN_CANVAS_CONTRACT,
            contracts.IMAGEGEN_CANVAS_CONTRACT,
        )
        self.assertIs(
            legacy.IMAGEGEN_CHROME_BAN_CONTRACT,
            contracts.IMAGEGEN_CHROME_BAN_CONTRACT,
        )

    def test_lightweight_modules_have_no_import_time_business_io(self) -> None:
        audit_script = r'''
import importlib
import json
import os
import sys

events = []

def audit(event, args):
    if event != "open":
        return
    path = args[0]
    try:
        normalized = os.fspath(path).replace("\\", "/")
    except TypeError:
        normalized = repr(path)
    mode = args[1] if len(args) > 1 else None
    flags = args[2] if len(args) > 2 else 0
    mode_writes = isinstance(mode, str) and any(marker in mode for marker in "wax+")
    flag_writes = isinstance(flags, int) and bool(
        flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
    )
    reads_rules = normalized.endswith("vendor/skills/ppt-script/config/rules.yaml")
    writes_output = (mode_writes or flag_writes) and any(
        marker in f"/{normalized.lstrip('/')}"
        for marker in ("/workbench/prompts/", "/workbench/stages/")
    )
    if reads_rules or writes_output:
        events.append([normalized, mode, flags])

sys.addaudithook(audit)
target = sys.argv[1]
importlib.import_module(target)
loaded = sorted(
    name for name in sys.modules
    if name.startswith("scripts.imagegen_pipeline.handoff.")
)
print(json.dumps({"events": events, "loaded": loaded}))
'''
        targets = {
            "scripts.imagegen_pipeline.handoff.contracts": {
                "scripts.imagegen_pipeline.handoff.contracts",
            },
            "scripts.imagegen_pipeline.handoff.common": {
                "scripts.imagegen_pipeline.handoff.common",
                "scripts.imagegen_pipeline.handoff.contracts",
            },
        }
        for module_name, allowed_modules in targets.items():
            with self.subTest(module=module_name):
                environment = os.environ.copy()
                environment["PYTHONDONTWRITEBYTECODE"] = "1"
                completed = subprocess.run(
                    [sys.executable, "-c", audit_script, module_name],
                    cwd=ROOT,
                    env=environment,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                payload = json.loads(completed.stdout)
                self.assertEqual([], payload["events"])
                self.assertEqual(allowed_modules, set(payload["loaded"]))

    def test_legacy_symbols_exist(self) -> None:
        module = importlib.import_module(HANDOFF_MODULE)
        missing = [name for name in COMPAT_SYMBOLS if not hasattr(module, name)]
        self.assertEqual([], missing)

    def test_repository_import_symbols_exist(self) -> None:
        module = importlib.import_module(HANDOFF_MODULE)
        missing = [name for name in REPOSITORY_IMPORT_SYMBOLS if not hasattr(module, name)]
        self.assertEqual([], missing)

    def test_repository_imports_are_covered_by_frozen_compatibility_symbols(self) -> None:
        imported = _repository_handoff_imports()
        self.assertTrue(imported)
        self.assertEqual(set(), imported - set(FROZEN_COMPAT_SYMBOLS))

    def test_behavior_matches_frozen_baseline(self) -> None:
        actual = capture_baseline()
        if os.environ.get("UPDATE_IMAGEGEN_HANDOFF_BASELINE") == "1":
            BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
            BASELINE_PATH.write_text(
                json.dumps(actual, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        expected = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(expected, actual)
