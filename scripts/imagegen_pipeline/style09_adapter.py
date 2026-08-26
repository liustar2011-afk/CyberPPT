"""Translate Stage 02 page meaning into STYLE09's visual language.

This module deliberately has no prompt-string parsing or layout selection.
Stage 02 remains authoritative for the page's business objects and relation;
the adapter only makes that decision explicit in STYLE09's surface language.
"""

from __future__ import annotations

from dataclasses import dataclass

from cyberppt.visual_prompt_consumer import VisualDesignIR


@dataclass(frozen=True)
class Style09AdaptedDesign:
    """Style09-safe, non-rendered expression of a Stage 02 visual decision."""

    semantic_anchor: str
    business_objects: tuple[str, ...]
    scene_role: str
    scene_anchor: str
    relationship_expression: str
    text_attachment: str
    hierarchy: str
    avoid: tuple[str, ...]

    def render_non_onscreen(self) -> str:
        """Serialize one non-rendered block for the final prompt compiler."""

        lines = [
            "【STYLE09 页面语义适配｜不上屏】",
            f"- 语义锚点：{self.semantic_anchor}",
            f"- 业务对象：{'；'.join(self.business_objects)}",
            f"- 场景职责：{self.scene_role}",
            f"- 场景锚点：{self.scene_anchor}",
            f"- 关系表达：{self.relationship_expression}",
            f"- 文字附着：{self.text_attachment}",
            f"- 层级：{self.hierarchy}",
        ]
        lines.extend(f"- 避免：{item}" for item in self.avoid)
        lines.append("- 上述为模型理解上下文；不得将字段名或其中业务语句额外渲染为可见文字。")
        return "\n".join(lines)


def _unique(*values: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def adapt_style09(design: VisualDesignIR) -> Style09AdaptedDesign:
    """Adapt one structured Stage 02 decision without selecting a layout.

    A non-narrative page still gets a business relationship field: ``use_scene``
    only changes whether the scene itself is integrated, never whether the page
    has a semantic visual carrier.
    """

    objects = _unique(design.business_object, design.primary_focus)
    if not objects:
        objects = ("本页业务对象",)
    scene_role = "integrated_scene" if design.use_scene else "business_relationship_field"
    scene_anchor = design.scene_type or (
        "以业务对象、动作、接口、边界和结果共同构成关系承载场"
    )
    relation = design.relationship_encoding or design.spatial_organization
    if not relation:
        relation = "以对象之间的方向、层级和承接关系表达本页业务逻辑"
    text_attachment = design.text_integration_method or "锁定文字贴附于对应对象、动作、边界或结果"
    hierarchy = design.primary_focus or design.spatial_organization or objects[0]
    return Style09AdaptedDesign(
        semantic_anchor=design.visual_thesis or relation,
        business_objects=objects,
        scene_role=scene_role,
        scene_anchor=scene_anchor,
        relationship_expression=relation,
        text_attachment=text_attachment,
        hierarchy=hierarchy,
        avoid=design.avoid,
    )
