"""Consume ppt-visual-structure-designer generation modules in production prompts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


VISUAL_STRUCTURE_HEADER = "【视觉结构设计模块｜不上屏】"
VISUAL_STRUCTURE_END = "【视觉结构设计模块结束】"


@dataclass(frozen=True)
class VisualPromptModule:
    page_number: int
    source_path: Path
    source_sha256: str
    page_block_sha256: str
    prompt_text: str


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().lower()


def _section(block: str, heading: str) -> str:
    match = re.search(
        rf"^{re.escape(heading)}\s*\n(.*?)(?=^\[[^\n]+\]\s*$|\Z)",
        block,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _field_values(text: str, prefix: str) -> list[str]:
    return [
        line.split(":", 1)[1].strip()
        for line in text.splitlines()
        if line.strip().lstrip("-").strip().startswith(prefix)
        and ":" in line
    ]


def _compile_execution_summary(page_block: str) -> str:
    """Compile Stage 02 review IR into a short, ImageGen-executable layout brief.

    The Stage 02 module intentionally contains IDs, evidence bindings and audit
    fields.  Those are authoritative for traceability, not visual instructions;
    only the actual visual thesis, spatial relation and placement constraints
    cross the production boundary.
    """

    structural = _section(page_block, "[Structural guidance]")
    if not structural:
        structural = _section(
            page_block,
            "[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.",
        )
    placement = _section(page_block, "[Text placement]")
    negative = _section(page_block, "[Negative constraints]")
    thesis = next(iter(_field_values(structural, "Visual thesis:")), "")
    grammar = next(iter(_field_values(structural, "Spatial grammar:")), "")
    reading = next(iter(_field_values(structural, "Reading sequence:")), "")
    constraints = _field_values(structural, "Additional structural constraint:")
    placement_strategy = next(iter(_field_values(placement, "Placement strategy:")), "")

    directions: list[str] = []
    if thesis:
        directions.append(f"本页只围绕这一主论断组织画面：{thesis}")
    if grammar:
        grammar_terms = {item.strip() for item in grammar.split(",") if item.strip()}
        if "path" in grammar_terms:
            directions.append("按一条连续主路径组织业务环节，保持清晰的前后推进")
        if "divergence" in grammar_terms:
            directions.append("允许局部展开或分支，但必须从属于同一主路径，不另起第二套结构")
        if "convergence" in grammar_terms:
            directions.append("将相关信息收束到同一主判断，不按条目均分为孤立模块")
        if "feedback" in grammar_terms:
            directions.append("用一处从属回接表达反馈，不形成完整环形图或第二条主链")
    if reading:
        step_count = len([item for item in reading.split("->") if item.strip()])
        if step_count > 1:
            directions.append(f"按已锁定文字对应的 {step_count} 个业务环节顺序阅读")
    if placement_strategy:
        directions.append(placement_strategy.rstrip("。") + "，不形成独立文字墙")
    for constraint in constraints:
        if constraint and constraint not in directions:
            directions.append(constraint)
    directions.extend(
        item.strip().lstrip("-").strip()
        for item in negative.splitlines()
        if item.strip()
    )
    if not directions and structural:
        directions.append("以一个连续、非等权的业务关系场组织已锁定文字")
    if not directions:
        raise ValueError("Stage 02 visual module has no executable layout guidance")
    return "\n".join(["【页面版式执行摘要｜不上屏】", *(f"- {item}" for item in directions)])


def _spec_page(payload: object, page_number: int) -> dict[str, object] | None:
    """Find a page spec in either a one-page or a deck-level Skill artifact."""

    if isinstance(payload, dict):
        if int(payload.get("page_number") or 0) == page_number:
            return payload
        pages = payload.get("pages")
        if isinstance(pages, list):
            for page in pages:
                found = _spec_page(page, page_number)
                if found is not None:
                    return found
    return None


def _strings(values: object) -> list[str]:
    return [str(value).strip() for value in values or [] if str(value).strip()]


def _compile_visual_spec(spec: dict[str, object]) -> str:
    """Translate the approved visual-design decision into an ImageGen brief.

    The spec is the Stage 02 design authority.  Unlike the former
    ``generation-prompts.md`` summary, this keeps the chosen carrier, focal
    relationship, scene decision, text-integration method and relationship
    encoding.  It deliberately omits internal IDs, copied locked text and
    pixel geometry: those either leak audit IR or turn a design into a brittle
    drawing recipe.
    """

    decision = spec.get("visual_decision") if isinstance(spec.get("visual_decision"), dict) else {}
    image_plan = spec.get("image_plan") if isinstance(spec.get("image_plan"), dict) else {}
    integration = spec.get("text_integration") if isinstance(spec.get("text_integration"), dict) else {}
    structural = spec.get("structural_decision") if isinstance(spec.get("structural_decision"), dict) else {}
    hierarchy = decision.get("visual_hierarchy") if isinstance(decision.get("visual_hierarchy"), dict) else {}
    focus = hierarchy.get("primary") or image_plan.get("business_object")
    thesis = str(decision.get("visual_thesis") or "").strip()
    carrier = str(image_plan.get("business_object") or "").strip()
    organization = str(decision.get("spatial_organization") or "").strip()
    integration_method = str(decision.get("text_integration_method") or integration.get("placement_strategy") or "").strip()
    encoding = str(decision.get("relationship_encoding") or "").strip()
    semantic_role = str(image_plan.get("semantic_role") or "").strip()
    scene_type = str(image_plan.get("scene_type") or "").strip()
    use_scene = image_plan.get("use_scene") is True
    grammar = _strings(structural.get("spatial_grammar"))
    avoid = _strings(spec.get("avoid"))

    directions: list[str] = []
    if thesis:
        directions.append(f"画面要清晰表达：{thesis}")
    if carrier:
        directions.append(f"以“{carrier}”作为承载业务关系的主视觉对象，不把它替换为泛科技装饰")
    if focus:
        directions.append(f"唯一视觉焦点是“{focus}”；其他对象、信息和局部场景都服务于该焦点")
    if organization:
        directions.append(f"构图组织：{organization}")
    if integration_method:
        directions.append(f"图文融合方式：{integration_method}")
    if encoding:
        directions.append(f"关系表达：{encoding}")
    if semantic_role:
        directions.append(f"业务语义要求：{semantic_role}")
    if use_scene:
        directions.append(f"场景仅作为业务关系的组成部分呈现（{scene_type or '按页面语义确定'}），不得脱离文字另作装饰")
    else:
        directions.append("不另设装饰性场景；由业务对象、动作、接口、边界和关系本身承担画面表达")
    if grammar:
        directions.append(f"空间语法服务于既定关系：{'、'.join(grammar)}")
    directions.extend(f"避免：{item}" for item in avoid)
    if not directions:
        raise ValueError("Stage 02 visual spec has no consumable visual decision")
    return "\n".join(["【页面视觉设计｜不上屏】", *(f"- {item}" for item in directions)])


def load_visual_prompt_module(project: Path, page_number: int) -> VisualPromptModule | None:
    """Load the approved visual-structure handoff for one page, when present.

    The visible Chinese body remains owned by the approved per-page ImageGen
    prompt.  This consumer deliberately imports only page-expression guidance
    from generation-prompts.md.  The selected CyberPPT style is owned by the
    production prompt compiler and is never imported from the visual-structure
    handoff's legacy ``[Style]`` section or its v1.1 ``[Style source]`` reference.
    """

    project = project.expanduser().resolve()
    spec_path = project / "visual" / "deck-visual-spec.json"
    if spec_path.is_file():
        source = spec_path.read_text(encoding="utf-8-sig")
        spec = _spec_page(json.loads(source), page_number)
        if spec is not None:
            prompt_text = _compile_visual_spec(spec)
            return VisualPromptModule(
                page_number=page_number,
                source_path=spec_path,
                source_sha256=_sha256_text(source),
                page_block_sha256=_sha256_text(json.dumps(spec, ensure_ascii=False, sort_keys=True)),
                prompt_text=prompt_text,
            )

    # Compatibility fallback for pre-v1.1 projects.  New Stage 02 production
    # is required to provide and consume the audited visual spec above.
    source_path = project / "visual" / "generation-prompts.md"
    if not source_path.is_file():
        return None
    source = source_path.read_text(encoding="utf-8-sig")
    match = re.search(
        rf"^# Page {page_number}:.*?\n(.*?)(?=^---\s*$|^# Page \d+:|\Z)",
        source,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise ValueError(
            f"visual generation module missing page {page_number}: {source_path}"
        )
    page_block = match.group(1).strip()
    prompt_text = _compile_execution_summary(page_block)
    return VisualPromptModule(
        page_number=page_number,
        source_path=source_path,
        source_sha256=_sha256_text(source),
        page_block_sha256=_sha256_text(page_block),
        prompt_text=prompt_text,
    )


def strip_visual_prompt_module(prompt: str) -> str:
    pattern = re.compile(
        rf"\n*{re.escape(VISUAL_STRUCTURE_HEADER)}.*?{re.escape(VISUAL_STRUCTURE_END)}\n*",
        flags=re.DOTALL,
    )
    return pattern.sub("\n\n", prompt).strip()


def append_visual_prompt_module(prompt: str, module: VisualPromptModule | None) -> str:
    base = strip_visual_prompt_module(prompt)
    if module is None:
        return base
    block = "\n".join(
        [
            VISUAL_STRUCTURE_HEADER,
            module.prompt_text,
            VISUAL_STRUCTURE_END,
        ]
    )
    return f"{base.rstrip()}\n\n{block}\n"


def visual_module_metadata(module: VisualPromptModule | None) -> dict[str, object]:
    if module is None:
        return {"consumed": False}
    return {
        "consumed": True,
        "page_number": module.page_number,
        "source_path": str(module.source_path),
        "source_sha256": module.source_sha256,
        "page_block_sha256": module.page_block_sha256,
    }
