from __future__ import annotations

import unittest

from cyberppt.outline_contract import audit_outline, resolve_architecture_mode


def page(
    sequence: int,
    page_type: str,
    title: str,
    *,
    chapter_id: str = "c1",
    message: str = "",
    question: str = "",
    visual: str = "",
    modules: list[dict[str, str]] | None = None,
    refs: list[str] | None = None,
    source_weight: float = 0.0,
) -> dict[str, object]:
    return {
        "page_id": f"p{sequence:02d}",
        "sequence": sequence,
        "page_type": page_type,
        "chapter_id": chapter_id,
        "title": title,
        "main_message": message,
        "source_refs": refs or [],
        "business_question": question,
        "visual_center": visual,
        "modules": modules or [],
        "source_weight": source_weight,
    }


def outline(*pages: dict[str, object], **overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "schema": "cyberppt.outline.v1",
        "material_type": "建设方案",
        "audience": "项目组内部讨论",
        "architecture_mode": "solution",
        "architecture_reason": "正式方案材料默认使用方案型架构",
        "user_requested_architecture": False,
        "source_section_weights": {"c1": 1.0},
        "pages": list(pages),
        "retry": {"attempt": 1, "max_attempts": 3, "strategy": "source_native"},
    }
    result.update(overrides)
    return result


class OutlineContractTests(unittest.TestCase):
    def test_solution_material_rejects_implicit_consulting_route(self) -> None:
        payload = outline(architecture_mode="consulting")
        self.assertIn("SOLUTION_ARCHITECTURE_REQUIRED", [item.code for item in audit_outline(payload)])

    def test_explicit_consulting_request_is_allowed(self) -> None:
        payload = outline(architecture_mode="consulting", user_requested_architecture=True)
        self.assertEqual("consulting", resolve_architecture_mode(payload))
        self.assertNotIn("SOLUTION_ARCHITECTURE_REQUIRED", [item.code for item in audit_outline(payload)])

    def test_chapter_page_cannot_carry_content(self) -> None:
        payload = outline(page(1, "chapter", "第一章：现状", message="正文判断"))
        self.assertIn("CHAPTER_PAGE_HAS_CONTENT", [item.code for item in audit_outline(payload)])

    def test_template_pages_must_be_in_continuous_sequence(self) -> None:
        payload = outline(
            page(1, "cover", "封面"),
            page(3, "chapter", "第一章：现状"),
            page(4, "content", "现状基础", message="基础较好", question="基础如何", visual="对照矩阵"),
        )
        self.assertIn("TEMPLATE_PAGES_DETACHED", [item.code for item in audit_outline(payload)])

    def test_title_and_main_message_must_be_distinct(self) -> None:
        payload = outline(page(1, "content", "现有能力存在四类问题", message="现有能力存在四类问题"))
        self.assertIn("TITLE_CLAIM_COLLAPSED", [item.code for item in audit_outline(payload)])

    def test_same_business_question_is_not_mechanically_split(self) -> None:
        pages = [
            page(index, "content", f"建设内容{index}", message=f"内容{index}", question="建设什么", visual="能力架构", modules=[{"title": f"模块{index}"}], refs=[f"S{index:03d}"])
            for index in range(1, 4)
        ]
        self.assertIn("ATOMIC_SECTION_SPLIT", [item.code for item in audit_outline(outline(*pages))])

    def test_source_weight_distortion_is_rejected(self) -> None:
        payload = outline(
            page(1, "content", "主体建设", message="建设体系", question="建设什么", visual="架构", source_weight=0.15),
            source_section_weights={"c1": 0.55, "c2": 0.45},
        )
        self.assertIn("SOURCE_WEIGHT_DISTORTED", [item.code for item in audit_outline(payload)])

    def test_method_only_page_without_evidence_is_overpromoted(self) -> None:
        payload = outline(
            page(1, "content", "场景选择原则", message="满足五项原则", question="如何选择场景", visual="筛选矩阵", modules=[{"role": "method", "title": "选择原则"}])
        )
        self.assertIn("METHOD_PAGE_OVERPROMOTED", [item.code for item in audit_outline(payload)])


if __name__ == "__main__":
    unittest.main()
