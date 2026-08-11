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
        "page_job": question or message or title,
        "proof_points": [
            {"claim": message or title, "source_refs": refs or [], "consumption": "primary"}
        ] if refs else [{"claim": message or title, "source_refs": []}],
        "new_value_vs_previous": message or title,
        "reserved_for_later": "后续页面按各自职责展开。",
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
    def test_formal_semantic_outline_requires_atomic_page_content_units(self) -> None:
        payload = outline(
            page(1, "content", "建设基础", message="现有基础支撑首期试点"),
            semantic_argument_model_mode="required",
        )

        codes = {item.code for item in audit_outline(payload)}

        self.assertIn("PAGE_CONTENT_UNIT_COVERAGE_MODE_REQUIRED", codes)
        self.assertIn("PAGE_CONTENT_UNITS_MISSING", codes)

    def test_formal_v2_outline_defaults_to_plain_declarative_titles(self) -> None:
        payload = outline(
            page(1, "content", "为什么需要运营型数据基础设施", message="需要建设运营基础"),
            page(2, "content", "从资源能力到正式运营对象", message="资源能力形成运营对象"),
            schema="cyberppt.outline.v2",
        )

        issues = [item for item in audit_outline(payload) if item.code == "FORMAL_TITLE_NOT_PLAIN"]

        self.assertEqual({"p01", "p02"}, {item.pages[0] for item in issues})

    def test_expressive_title_style_requires_explicit_user_request(self) -> None:
        payload = outline(
            page(1, "content", "如何形成持续运营？", message="形成持续运营"),
            schema="cyberppt.outline.v2",
            title_style_mode="expressive",
        )
        self.assertIn(
            "TITLE_STYLE_OVERRIDE_UNCONFIRMED",
            [item.code for item in audit_outline(payload)],
        )

        payload["user_requested_title_style"] = True
        self.assertNotIn(
            "TITLE_STYLE_OVERRIDE_UNCONFIRMED",
            [item.code for item in audit_outline(payload)],
        )

    def test_required_editorial_controls_are_enforced(self) -> None:
        content = page(1, "content", "建设基础", message="现有条件支持启动", refs=["S001"])
        payload = outline(content, editorial_control_mode="required")
        codes = {item.code for item in audit_outline(payload)}
        self.assertIn("AUDIENCE_QUESTION_MISSING", codes)
        self.assertIn("MUST_NOT_INCLUDE_MISSING", codes)
        self.assertIn("SPLIT_RISK_INVALID", codes)

        content.update(
            {
                "audience_question": "现有条件是否足以支持项目启动？",
                "must_not_include": ["实施步骤", "投资承诺"],
                "split_risk": "low",
            }
        )
        codes = {item.code for item in audit_outline(payload)}
        self.assertFalse(
            {"AUDIENCE_QUESTION_MISSING", "MUST_NOT_INCLUDE_MISSING", "SPLIT_RISK_INVALID"}
            & codes
        )

    def test_editorial_question_cannot_repeat_mission_and_high_risk_blocks(self) -> None:
        content = page(1, "content", "建设基础", message="现有条件支持启动", refs=["S001"])
        content.update(
            {
                "page_mission": "说明现有条件是否足以支持项目启动",
                "audience_question": "说明现有条件是否足以支持项目启动",
                "must_not_include": ["实施步骤"],
                "split_risk": "high",
                "split_risk_reason": "同时承载基础判断和实施安排",
            }
        )
        codes = {item.code for item in audit_outline(outline(content, editorial_control_mode="required"))}
        self.assertIn("AUDIENCE_QUESTION_NOT_CONCRETE", codes)
        self.assertIn("HIGH_SPLIT_RISK_UNRESOLVED", codes)

    def test_medium_split_risk_requires_reason(self) -> None:
        content = page(1, "content", "建设基础", message="现有条件支持启动", refs=["S001"])
        content.update(
            {
                "audience_question": "现有条件是否足以支持项目启动？",
                "must_not_include": ["实施步骤"],
                "split_risk": "medium",
            }
        )
        codes = {item.code for item in audit_outline(outline(content, editorial_control_mode="required"))}
        self.assertIn("SPLIT_RISK_REASON_MISSING", codes)

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

    def test_strict_outline_requires_source_truth(self) -> None:
        payload = outline(
            page(1, "content", "工作基础", message="已有统计基础"),
            argument_contract_mode="strict",
        )

        self.assertIn(
            "SOURCE_TRUTH_REQUIRED",
            [item.code for item in audit_outline(payload)],
        )

    def test_strict_outline_includes_argument_flow_issues(self) -> None:
        content = page(
            1,
            "content",
            "工作基础",
            message="首期建议从全国总盘入手",
            refs=["S006R"],
        )
        content.update(
            {
                "argument_role": "foundation",
                "allowed_claim_roles": ["fact"],
                "forbidden_claim_roles": ["recommendation"],
                "prerequisite_pages": [],
                "main_claim_status": "confirmed",
                "page_job": "陈述既有工作事实基础",
                "proof_points": [
                    {"claim": "已有工作基础", "source_refs": ["S006R"], "consumption": "primary"}
                ],
                "new_value_vs_previous": "首次建立现状基础",
                "reserved_for_later": "首期建议留给范围页。",
            }
        )
        payload = outline(content, argument_contract_mode="strict")
        truth = {
            "argument_contract_mode": "strict",
            "records": [
                {
                    "id": "S006R",
                    "claim_role": "recommendation",
                    "page_refs": ["p01"],
                    "depends_on": [],
                    "status": "首期建议",
                }
            ],
        }

        self.assertIn(
            "PREMATURE_SOLUTION_CLAIM",
            [item.code for item in audit_outline(payload, truth)],
        )

    def test_content_page_requires_complete_core_message_without_forcing_judgment(self) -> None:
        content = page(
            1,
            "content",
            "建设目标与能力框架",
            message="总体建设框架由五个层次构成，各层分别承担相应职责",
            question="总体建设框架包含哪些内容",
            visual="五层能力框架",
            refs=["S021"],
        )
        payload = outline(
            content,
            core_message_derivation_mode="required",
            source_section_weights={},
        )
        truth = {"records": [{"id": "S021", "statement": "总体建设框架由五个层次构成。"}]}

        content["core_message_derivation"] = {
            "source_refs": ["S021"],
            "supporting_statements": ["总体建设框架由五个层次构成。"],
            "derivation": "保留原文的构成关系。",
            "introduced_relations": [],
            "introduced_modalities": [],
        }
        codes = [item.code for item in audit_outline(payload, truth)]
        self.assertNotIn("CORE_MESSAGE_DERIVATION_MISSING", codes)
        self.assertNotIn("ONSCREEN_CONCLUSION_WITHOUT_JUDGMENT", codes)

    def test_content_page_without_core_message_is_rejected(self) -> None:
        payload = outline(
            page(1, "content", "建设目标与能力框架", message="", refs=["S021"]),
            source_section_weights={},
        )
        self.assertIn("CORE_MESSAGE_MISSING", [item.code for item in audit_outline(payload)])

    def test_heading_or_table_label_is_not_a_complete_core_message(self) -> None:
        heading = page(1, "content", "研究边界", message="1. 研究对象", refs=["S021"])
        table = page(2, "content", "指标清单", message="指标类别 | 核心指标 | 主要用途", refs=["S022"])
        codes = [item.code for item in audit_outline(outline(heading, table))]
        self.assertIn("CORE_MESSAGE_NOT_COMPLETE", codes)

    def test_reused_page_necessity_is_rejected(self) -> None:
        pages = []
        for index in range(1, 4):
            item = page(index, "content", f"主题{index}", message=f"主题{index}包含完整的来源事实和边界说明。", refs=[f"S{index:03d}"])
            item["page_necessity"] = "该证据组具有独立对象，必须单独成页。"
            pages.append(item)
        codes = [item.code for item in audit_outline(outline(*pages))]
        self.assertIn("PAGE_NECESSITY_BOILERPLATE", codes)

    def test_similar_core_messages_across_different_sources_are_rejected(self) -> None:
        left = page(1, "content", "组织机制", message="建立领导统筹、处室牵头、专班推进、专家支撑和生态协同的组织机制。", refs=["S001"])
        right = page(2, "content", "组织条件", message="建议建立领导统筹、处室牵头、专班推进、专家支撑和生态协同的组织机制。", refs=["S002"])
        codes = [item.code for item in audit_outline(outline(left, right))]
        self.assertIn("CORE_MESSAGE_REDUNDANT", codes)

    def test_outline_must_inherit_document_subject_and_primary_thesis(self) -> None:
        semantics = {
            "document_role": "前期研究成果汇报",
            "subject_of_report": "电力供需预测预警能力建设",
            "primary_thesis": "需要推进能力建设",
            "decision_boundary": "完整范围与投资仍需论证",
            "source_refs": ["S001"],
        }
        truth = {
            "document_semantics_mode": "required",
            "document_semantics": semantics,
            "records": [{"id": "S001", "statement": "需要推进能力建设"}],
        }
        payload = outline(document_semantics=semantics, narrative_thesis="需要开展前期研究")
        codes = {item.code for item in audit_outline(payload, truth)}
        self.assertIn("NARRATIVE_THESIS_DRIFTED", codes)

        payload["narrative_thesis"] = "需要推进能力建设"
        self.assertNotIn("NARRATIVE_THESIS_DRIFTED", {item.code for item in audit_outline(payload, truth)})

    def test_v2_objective_composition_contract_passes_semantic_checks(self) -> None:
        content = page(
            1,
            "content",
            "建设目标与能力框架",
            message="",
            refs=["S021"],
        )
        content.update(
            {
                "page_mission": "说明总体能力框架的构成及各层职责",
                "core_message": "总体能力框架由五个层次构成，各层分别承担相应职责",
                "core_message_derivation": {
                    "source_refs": ["S021"],
                    "supporting_statements": ["总体能力框架由五个层次构成，各层分别承担相应职责。"],
                    "derivation": "保留原文组成关系和职责表述。",
                    "introduced_relations": [],
                    "introduced_modalities": [],
                },
                "content_relations": [
                    {
                        "relation": "composed_of",
                        "subject": "总体能力框架",
                        "objects": ["业务应用", "成果服务", "模型分析", "数据治理", "运行保障"],
                        "source_refs": ["S021"],
                    }
                ],
            }
        )
        payload = outline(
            content,
            schema="cyberppt.outline.v2",
            core_message_derivation_mode="required",
            source_section_weights={},
        )
        truth = {"records": [{"id": "S021", "statement": "总体能力框架由五个层次构成，各层分别承担相应职责。"}]}

        semantic_codes = {
            "CORE_MESSAGE_MISSING",
            "CORE_MESSAGE_DERIVATION_MISSING",
            "CONTENT_RELATIONS_MISSING",
            "RELATION_STRENGTH_UPGRADED",
            "MODALITY_STRENGTH_UPGRADED",
        }
        self.assertFalse(semantic_codes & {item.code for item in audit_outline(payload, truth)})

    def test_unsupported_necessity_and_relationship_are_rejected(self) -> None:
        content = page(
            1,
            "content",
            "建设目标与能力框架",
            message="五类能力协同，才能支撑多对象、多尺度、多层级研判",
            question="总体建设框架包含哪些内容",
            visual="五层能力框架",
            refs=["S021"],
        )
        content["onscreen_judgment"] = "五类能力协同，才能支撑研判"
        content["judgment_derivation"] = {
            "source_refs": ["S021"],
            "supporting_statements": ["总体建设框架由五个层次构成。"],
            "derivation": "压缩五层构成关系。",
            "introduced_relations": [],
            "introduced_modalities": [],
        }
        payload = outline(
            content,
            judgment_derivation_mode="required",
            source_section_weights={},
        )
        truth = {"records": [{"id": "S021", "statement": "总体建设框架由五个层次构成。"}]}

        codes = [item.code for item in audit_outline(payload, truth)]
        self.assertIn("RELATION_STRENGTH_UPGRADED", codes)
        self.assertIn("MODALITY_STRENGTH_UPGRADED", codes)


if __name__ == "__main__":
    unittest.main()
