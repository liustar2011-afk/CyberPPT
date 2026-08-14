"""Load immutable Stage 02 visual-design IR for production prompt consumers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


VISUAL_STRUCTURE_HEADER = "【视觉结构设计模块｜不上屏】"
VISUAL_STRUCTURE_END = "【视觉结构设计模块结束】"


@dataclass(frozen=True)
class VisualDesignIR:
    """The complete, immutable visual decision for a single page.

    ``governed_json`` comes only from the audited deck spec.  Markdown is an
    explicitly requested compatibility input and must never silently replace a
    present governed artifact.
    """

    page_number: int
    visual_thesis: str
    business_object: str
    primary_focus: str
    spatial_organization: str
    relationship_encoding: str
    text_integration_method: str
    semantic_role: str
    use_scene: bool
    scene_type: str
    spatial_grammar: tuple[str, ...]
    avoid: tuple[str, ...]
    source_path: Path
    source_sha256: str
    page_block_sha256: str
    source_mode: str


@dataclass(frozen=True)
class VisualPromptModule:
    """Compatibility wrapper for callers that still append a prompt string."""

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
        if line.strip().lstrip("-").strip().startswith(prefix) and ":" in line
    ]


def _spec_page(payload: object, page_number: int) -> dict[str, object] | None:
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


def _required_text(value: object, field: str, *, path: Path) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"VisualDesignIR field {field} is required: {path}")
    return text


def _required_strings(value: object, field: str, *, path: Path) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"VisualDesignIR field {field} must be a list: {path}")
    values = tuple(str(item).strip() for item in value if str(item).strip())
    if not values:
        raise ValueError(f"VisualDesignIR field {field} must not be empty: {path}")
    return values


def _governed_ir(spec: dict[str, object], *, source_path: Path, source: str) -> VisualDesignIR:
    decision = spec.get("visual_decision")
    image_plan = spec.get("image_plan")
    structural = spec.get("structural_decision")
    if not isinstance(decision, dict) or not isinstance(image_plan, dict) or not isinstance(structural, dict):
        raise ValueError(f"VisualDesignIR requires visual_decision, image_plan, and structural_decision: {source_path}")
    hierarchy = decision.get("visual_hierarchy")
    if not isinstance(hierarchy, dict):
        raise ValueError(f"VisualDesignIR field visual_decision.visual_hierarchy is required: {source_path}")
    use_scene = image_plan.get("use_scene")
    if not isinstance(use_scene, bool):
        raise ValueError(f"VisualDesignIR field image_plan.use_scene must be boolean: {source_path}")
    return VisualDesignIR(
        page_number=int(spec["page_number"]),
        visual_thesis=_required_text(decision.get("visual_thesis"), "visual_thesis", path=source_path),
        business_object=_required_text(image_plan.get("business_object"), "business_object", path=source_path),
        primary_focus=_required_text(hierarchy.get("primary"), "primary_focus", path=source_path),
        spatial_organization=_required_text(decision.get("spatial_organization"), "spatial_organization", path=source_path),
        relationship_encoding=_required_text(decision.get("relationship_encoding"), "relationship_encoding", path=source_path),
        text_integration_method=_required_text(decision.get("text_integration_method"), "text_integration_method", path=source_path),
        semantic_role=_required_text(image_plan.get("semantic_role"), "semantic_role", path=source_path),
        use_scene=use_scene,
        scene_type=_required_text(image_plan.get("scene_type"), "scene_type", path=source_path),
        spatial_grammar=_required_strings(structural.get("spatial_grammar"), "spatial_grammar", path=source_path),
        avoid=_required_strings(spec.get("avoid"), "avoid", path=source_path),
        source_path=source_path,
        source_sha256=_sha256_text(source),
        page_block_sha256=_sha256_text(json.dumps(spec, ensure_ascii=False, sort_keys=True)),
        source_mode="governed_json",
    )


def _legacy_ir(page_number: int, page_block: str, *, source_path: Path, source: str) -> VisualDesignIR:
    # Older handoffs used several headings (including "Mandatory composition
    # guidance") for the same structural facts.  Legacy is compatibility-only,
    # but when explicitly selected it must preserve those facts rather than
    # silently collapse them to generic placeholders.
    structural = page_block
    placement = _section(page_block, "[Text placement]")
    negative = _section(page_block, "[Negative constraints]")
    thesis = next(iter(_field_values(structural, "Visual thesis:")), "legacy visual structure")
    grammar = tuple(item.strip() for item in next(iter(_field_values(structural, "Spatial grammar:")), "legacy").split(",") if item.strip())
    placement_method = next(iter(_field_values(placement, "Placement strategy:")), "attach locked text to its related object")
    return VisualDesignIR(
        page_number=page_number, visual_thesis=thesis, business_object="legacy visual carrier",
        primary_focus="legacy primary focus", spatial_organization="legacy spatial organization",
        relationship_encoding="legacy relationship encoding", text_integration_method=placement_method,
        semantic_role="legacy semantic role", use_scene=False, scene_type="no scene",
        spatial_grammar=grammar or ("legacy",),
        avoid=tuple(line.strip().lstrip("-").strip() for line in negative.splitlines() if line.strip()) or ("no equal card wall",),
        source_path=source_path, source_sha256=_sha256_text(source),
        page_block_sha256=_sha256_text(page_block), source_mode="legacy_markdown",
    )


def load_visual_design(project: Path, page_number: int, allow_legacy: bool = False) -> VisualDesignIR | None:
    """Load governed JSON strictly; parse Markdown only after an explicit opt-in."""

    project = project.expanduser().resolve()
    spec_path = project / "visual" / "deck-visual-spec.json"
    if spec_path.is_file():
        source = spec_path.read_text(encoding="utf-8-sig")
        try:
            payload = json.loads(source)
        except json.JSONDecodeError as exc:
            raise ValueError(f"VisualDesignIR JSON is invalid: {spec_path}") from exc
        spec = _spec_page(payload, page_number)
        if spec is None:
            raise ValueError(f"VisualDesignIR missing requested page {page_number}: {spec_path}")
        return _governed_ir(spec, source_path=spec_path, source=source)

    if not allow_legacy:
        from cyberppt.commands.visual_structure_stage import visual_structure_required

        if visual_structure_required(project):
            raise FileNotFoundError(f"required VisualDesignIR is missing: {spec_path}")
        return None

    source_path = project / "visual" / "generation-prompts.md"
    if not source_path.is_file():
        return None
    source = source_path.read_text(encoding="utf-8-sig")
    match = re.search(rf"^# Page {page_number}:.*?\n(.*?)(?=^---\s*$|^# Page \d+:|\Z)", source, flags=re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"visual generation module missing page {page_number}: {source_path}")
    return _legacy_ir(page_number, match.group(1).strip(), source_path=source_path, source=source)


def _compile_visual_design(ir: VisualDesignIR) -> str:
    """Render all IR semantics as non-on-screen prompt context for old consumers."""

    scene = "使用场景" if ir.use_scene else "不使用场景"
    return "\n".join([
        "【页面视觉设计语义｜不上屏，不得作为可读文字渲染】",
        f"- 视觉论题：{ir.visual_thesis}", f"- 业务对象：{ir.business_object}",
        f"- 主焦点：{ir.primary_focus}", f"- 空间组织：{ir.spatial_organization}",
        f"- 关系编码：{ir.relationship_encoding}", f"- 文字融合：{ir.text_integration_method}",
        f"- 语义角色：{ir.semantic_role}", f"- 场景策略：{scene}；{ir.scene_type}",
        f"- 空间语法：{'、'.join(ir.spatial_grammar)}", f"- 避免：{'、'.join(ir.avoid)}",
    ])


def load_visual_prompt_module(
    project: Path, page_number: int, *, allow_legacy: bool = False
) -> VisualPromptModule | None:
    """Compatibility wrapper over ``load_visual_design`` for string consumers."""

    project = project.expanduser().resolve()
    ir = load_visual_design(project, page_number, allow_legacy=allow_legacy)
    if ir is None:
        return None
    return VisualPromptModule(ir.page_number, ir.source_path, ir.source_sha256, ir.page_block_sha256, _compile_visual_design(ir))


def strip_visual_prompt_module(prompt: str) -> str:
    pattern = re.compile(rf"\n*{re.escape(VISUAL_STRUCTURE_HEADER)}.*?{re.escape(VISUAL_STRUCTURE_END)}\n*", flags=re.DOTALL)
    return pattern.sub("\n\n", prompt).strip()


def append_visual_prompt_module(prompt: str, module: VisualPromptModule | None) -> str:
    base = strip_visual_prompt_module(prompt)
    if module is None:
        return base
    return f"{base.rstrip()}\n\n{VISUAL_STRUCTURE_HEADER}\n{module.prompt_text}\n{VISUAL_STRUCTURE_END}\n"


def visual_module_metadata(module: VisualPromptModule | None) -> dict[str, object]:
    if module is None:
        return {"consumed": False}
    return {"consumed": True, "page_number": module.page_number, "source_path": str(module.source_path), "source_sha256": module.source_sha256, "page_block_sha256": module.page_block_sha256}
