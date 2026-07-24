"""Shared permissive visual-expression rules with semantic boundaries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisualGrammarContract:
    container_rule: str
    connector_rule: str
    image_text_rule: str
    hierarchy_rule: str

    def render(self) -> str:
        return "\n".join(
            (
                self.container_rule,
                self.connector_rule,
                self.image_text_rule,
                self.hierarchy_rule,
            )
        )


def default_visual_grammar() -> VisualGrammarContract:
    """Return open visual rules that preserve meaning and readability."""

    return VisualGrammarContract(
        container_rule=(
            "允许使用文字框、标签、卡片、侧栏、色块和分区，但每个容器必须承担明确的业务语义；"
            "不得为了版式整齐复制无语义容器。"
        ),
        connector_rule=(
            "箭头、路径和连接线可以采用细线、色带、渐变、光流、空间轨迹或轻微立体效果，"
            "但不得穿过、遮挡或托载正文文字；功能性连接方向必须清楚，装饰性路径不得制造虚假关系；"
            "同一页面只使用一套主要连接语言。"
        ),
        image_text_rule=(
            "文字可以与图片相邻、嵌套或局部叠加，但正文必须位于干净、稳定、对比充足的区域，"
            "不得压在复杂纹理或高对比图片上。"
        ),
        hierarchy_rule=(
            "容器数量、面积、对比度和视觉强弱服从内容层级；不同层级不得被处理成完全等权。"
        ),
    )
