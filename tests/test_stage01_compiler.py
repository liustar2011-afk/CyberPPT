from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.init_project import init_project
from cyberppt.outline_contract import audit_outline
from cyberppt.semantic_cross_audit import semantic_evidence_cross_issues
from cyberppt.semantic_understanding import (
    SEMANTIC_ARGUMENT_MODEL,
    SEMANTIC_ARTIFACT,
    run_semantic_understanding_audit,
)
from cyberppt.source_argument_model import SCHEMA
from cyberppt.source_document_map import (
    SOURCE_HEADING_TREE,
    SOURCE_UNITS,
    prepare_source_map,
)
from cyberppt.source_truth_contract import audit_source_truth, load_source_truth
from cyberppt.stage01_compiler import (
    _content_unit_anchors,
    _source_locator,
    _page_content_units,
    _onscreen_modules,
    compile_outline_draft,
    compile_source_truth,
    refresh_outline_content_units,
)


class Stage01CompilerTests(unittest.TestCase):
    def test_content_unit_anchors_keep_enumerated_facts_as_complete_clauses(self) -> None:
        cases = (
            (
                "ST0005",
                {
                    "statement": "复杂业务需要跨企业、跨领域、跨能力组织数据资源、模型算法、专家知识、技术实施和持续服务，单一主体难以完整支撑。",
                    "semantic_units": [
                        {
                            "text": "复杂业务需要跨企业、跨领域、跨能力组织数据资源、模型算法、专家知识、技术实施和持续服务，单一主体难以完整支撑。"
                        }
                    ],
                    "coverage_anchors": [
                        "复杂业务需要跨企业、跨领域、跨能力组织数据资源、模型算法、专家知识、技术实施和持续服务",
                        "单一主体难以完整支撑",
                    ],
                },
                ["单一主体难以完整支撑"],
            ),
            (
                "ST0006",
                {
                    "statement": "行业资源在法人主体、业务系统和安全域之间分布，目录、口径、接口、授权、质量、版本、责任、供需对接、计量和结算尚未统一，导致发现、适配、合规沟通和价值释放成本较高。",
                    "semantic_units": [
                        {
                            "text": "行业资源在法人主体、业务系统和安全域之间分布，目录、口径、接口、授权、质量、版本、责任、供需对接、计量和结算尚未统一，导致发现、适配、合规沟通和价值释放成本较高。"
                        }
                    ],
                    "coverage_anchors": [
                        "行业资源在法人主体、业务系统和安全域之间分布",
                        "目录、口径、接口、授权、质量、版本、责任、供需对接、计量和结算尚未统一",
                    ],
                },
                [
                    "行业资源在法人主体、业务系统和安全域之间分布",
                    "目录、口径、接口、授权、质量、版本、责任、供需对接、计量和结算尚未统一",
                ],
            ),
        )

        for source_id, record, expected in cases:
            with self.subTest(source_id=source_id):
                self.assertEqual(expected, _content_unit_anchors(record, "建设背景"))

    def test_content_unit_anchors_skip_section_framing_and_keep_source_conditions(self) -> None:
        record = {
            "statement": "首期方向筛选。",
            "semantic_units": [
                {"text": "本节从领域优先级角度，对前述服务在重点领域的组合应用进行排序，不构成与既有服务并列的新服务类型。"},
                {"text": "平台优先选择真实需求明确、资源权利清晰、交付成果可验证的方向。"},
            ],
        }

        self.assertEqual(
            ["真实需求明确", "资源权利清晰"],
            _content_unit_anchors(record, "重点服务方向"),
        )

    def test_source_locator_keeps_global_anchor_and_section_relative_ordinal(self) -> None:
        locator = _source_locator({
            "source_id": "SRC", "source_path": "source/material.docx",
            "heading_path": ["第一章", "建设背景"],
            "locator": {"paragraph": 23, "section_paragraph": 1},
        })
        self.assertEqual(23, locator["paragraph"])
        self.assertEqual(1, locator["section_paragraph"])
    def test_refresh_content_units_preserves_authored_page_judgment(self) -> None:
        outline_path = self.project / "workbench/stages/01-analysis/outline.json"
        truth_path = self.project / "workbench/stages/01-analysis/source-truth.json"
        outline_path.parent.mkdir(parents=True, exist_ok=True)
        outline_path.write_text(json.dumps({"pages": [{
            "page_id": "p04", "page_type": "content", "title": "背景", "topic_category": "背景",
            "core_message": "作者判断", "source_refs": ["ST0001"], "content_units": [],
        }]}, ensure_ascii=False), encoding="utf-8")
        truth_path.write_text(json.dumps({"records": [{
            "id": "ST0001", "statement": "来源事实。", "priority": "P0", "claim_role": "fact",
            "argument_duty": "detail", "semantic_units": [{"text": "来源事实需要保留。"}],
        }]}, ensure_ascii=False), encoding="utf-8")

        refresh_outline_content_units(self.project)

        refreshed = json.loads(outline_path.read_text(encoding="utf-8"))["pages"][0]
        self.assertEqual("作者判断", refreshed["core_message"])
        self.assertTrue(refreshed["content_units"])

    def test_refresh_content_units_projects_subtitle_policy_without_overwriting_authored_subtitle(self) -> None:
        outline_path = self.project / "workbench/stages/01-analysis/outline.json"
        truth_path = self.project / "workbench/stages/01-analysis/source-truth.json"
        outline_path.parent.mkdir(parents=True, exist_ok=True)
        core_message = "平台对产品和场景实行全过程阶段门控，产品和场景分别进入持续运营和标准化复制。"
        outline_path.write_text(json.dumps({"pages": [{
            "page_id": "p04", "page_type": "content", "title": "生命周期", "topic_category": "生命周期",
            "core_message": core_message, "source_refs": ["ST0001"], "content_units": [],
            "visual_intent_type": "phase",
        }, {
            "page_id": "p05", "page_type": "content", "title": "既有副标题", "topic_category": "既有副标题",
            "core_message": core_message, "source_refs": ["ST0001"], "content_units": [],
            "visual_intent_type": "phase", "subtitle": "既有作者层副标题",
        }]}, ensure_ascii=False), encoding="utf-8")
        truth_path.write_text(json.dumps({"records": [{
            "id": "ST0001", "statement": core_message, "priority": "P0", "claim_role": "fact",
            "argument_duty": "detail", "semantic_units": [{"text": core_message}],
        }]}, ensure_ascii=False), encoding="utf-8")

        refresh_outline_content_units(self.project)

        refreshed = json.loads(outline_path.read_text(encoding="utf-8"))["pages"]
        self.assertEqual("generated", refreshed[0]["subtitle_policy"]["mode"])
        self.assertEqual(
            "产品与场景分别在阶段门控下进入持续运营与标准化复制",
            refreshed[0]["subtitle"],
        )
        self.assertEqual("authored", refreshed[1]["subtitle_policy"]["mode"])
        self.assertEqual("既有作者层副标题", refreshed[1]["subtitle"])

    def test_content_units_split_large_primary_evidence_and_use_short_anchors(self) -> None:
        records = [
            {
                "id": f"ST000{index}", "priority": "P0", "claim_role": "fact", "argument_duty": "detail",
                "statement": f"来源事实{index}。", "coverage_anchors": ["这是一段超过三十六个字符且不应要求完整稿逐字复现的长来源锚点。"],
                "semantic_units": [{"text": f"业务对象{index}需要协同处理，形成明确服务结果。"}],
            }
            for index in range(1, 5)
        ]

        units, details = _page_content_units("p04", records, "建设背景")

        self.assertEqual([], details)
        self.assertEqual(2, len(units))
        self.assertEqual("primary", units[0]["role"])
        self.assertEqual("supporting", units[1]["role"])
        self.assertTrue(all(len(anchor) <= 36 for unit in units for anchor in unit["coverage_anchors"]))

    def test_semantic_argument_duties_keep_source_stages_onscreen(self) -> None:
        records = [
            {
                "id": f"ST000{index}", "priority": "P0", "claim_role": "fact",
                "argument_duty": ("premise", "driver", "gap", "response")[index - 1],
                "statement": f"来源论证阶段{index}。", "coverage_anchors": [f"阶段锚点{index}", "协同运营"],
            }
            for index in range(1, 5)
        ]

        units, details = _page_content_units(
            "p04", records, "建设背景",
        )

        self.assertEqual([], details)
        self.assertEqual([[f"ST000{index}"] for index in range(1, 5)], [unit["source_refs"] for unit in units])
        self.assertTrue(all(unit["onscreen_required"] for unit in units[1:]))

    def test_selected_scqa_groups_complication_and_keeps_answer_primary(self) -> None:
        records = [
            {
                "id": f"ST000{index}", "priority": "P0", "claim_role": "fact",
                "argument_duty": "detail", "statement": f"来源段落{index}。",
                "coverage_anchors": [f"锚点{index}", "数据服务"],
            }
            for index in range(1, 5)
        ]
        selection = {
            "model_id": "scqa", "fit": "selected",
            "source_mapping": [
                {"slot": "situation", "source_refs": ["ST0001"]},
                {"slot": "complication", "source_refs": ["ST0002", "ST0003"]},
                {"slot": "question", "source_refs": ["ST0002", "ST0003"], "implicit": True},
                {"slot": "answer", "source_refs": ["ST0004"]},
            ],
        }

        units, details = _page_content_units(
            "p04", records, "建设背景", expression_model_selection=selection,
        )

        self.assertEqual([], details)
        self.assertEqual(["situation", "complication", "answer"], [unit["model_slot"] for unit in units])
        self.assertEqual(["ST0002", "ST0003"], units[1]["source_refs"])
        self.assertEqual("primary", units[-1]["role"])
        self.assertTrue(all(unit["onscreen_required"] for unit in units))

    def test_onscreen_modules_keep_each_source_fact_separate(self) -> None:
        records = [
            {
                "id": "ST0001", "statement": "协同需求持续增长。",
                "semantic_units": [{"text": "协同需求持续增长"}],
            },
            {
                "id": "ST0002", "statement": "分散资源尚未形成稳定的行业服务供给。",
                "semantic_units": [{"text": "分散资源尚未形成稳定的行业服务供给"}],
            },
        ]
        modules = _onscreen_modules("p04", records, {
            "fit": "selected", "source_mapping": [
                {"slot": "complication", "source_refs": ["ST0001", "ST0002"]},
            ],
        })

        self.assertEqual([["ST0001"], ["ST0002"]], [item["source_refs"] for item in modules])
        self.assertEqual(["complication"], modules[1]["model_slots"])
        self.assertEqual("direct", modules[1]["derivation_mode"])
        self.assertEqual("分散资源尚未形成稳定的行业服务供给", modules[1]["display_title"])
        self.assertNotIn(
            "稳定的数据服务和场景服务供给",
            "\n".join(item["allowed_visible_claim"] for item in modules),
        )

    def test_source_native_architecture_promotes_overview_to_lead(self) -> None:
        records = [
            {
                "id": "ST0001",
                "statement": "平台按照五层两贯穿总体架构建设，并遵循统一控制原则。",
                "semantic_units": [{"text": "五层两贯穿总体架构"}],
            },
            {
                "id": "ST0002",
                "statement": "五层能力从主体接入到价值实现依次展开。",
                "semantic_units": [{"text": "五层能力"}],
            },
            {
                "id": "ST0003",
                "statement": "平台部署根据服务对象和安全要求分级配置。",
                "semantic_units": [{"text": "分级部署"}],
            },
        ]

        modules = _onscreen_modules(
            "p06", records,
            {"model_id": "source_native", "fit": "selected"},
            visual_intent_type="architecture",
        )

        self.assertEqual("lead", modules[0]["presentation_role"])
        self.assertEqual("semantic", modules[0]["visible_layer"])
        self.assertEqual("structure", modules[1]["presentation_role"])
        self.assertEqual("body", modules[1]["visible_layer"])
        self.assertEqual("boundary", modules[2]["presentation_role"])
        self.assertEqual("notes", modules[2]["visible_layer"])
    def test_fallback_primary_prefers_page_forming_gap_over_general_premise(self) -> None:
        records = [
            {
                "id": "ST0001",
                "priority": "P1",
                "claim_role": "fact",
                "argument_duty": "premise",
                "statement": "电力行业覆盖完整产业链。",
                "coverage_anchors": ["电力行业", "完整产业链"],
            },
            {
                "id": "ST0002",
                "priority": "P1",
                "claim_role": "problem",
                "argument_duty": "gap",
                "statement": "分散资源尚未形成稳定服务供给。",
                "coverage_anchors": ["分散资源", "稳定服务供给"],
            },
        ]
        units, _details = _page_content_units("p04", records, "建设必要性")
        primary = next(unit for unit in units if unit["role"] == "primary")
        premise = next(unit for unit in units if "premise" in unit["argument_duties"])
        self.assertEqual(["ST0002"], primary["source_refs"])
        self.assertTrue(primary["onscreen_required"])
        self.assertTrue(premise["onscreen_required"])

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name) / "project"
        init_project(self.project)
        (self.project / "source" / "material.md").write_text(
            "# 建设方案\n\n## 建设基础\n\n现有行业数据资源和专业能力构成首期建设基础。\n",
            encoding="utf-8",
        )
        prepare_source_map(self.project)
        headings = json.loads(
            (self.project / SOURCE_HEADING_TREE).read_text(encoding="utf-8")
        )["headings"]
        units = [
            json.loads(line)
            for line in (self.project / SOURCE_UNITS).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        paragraph = next(item for item in units if item["kind"] != "heading")
        top, child = headings
        evidence = paragraph["unit_id"]
        model = {
            "schema": SCHEMA,
            "version": 1,
            "interpretation_contract_mode": "strict",
            "source_truth_projection_mode": "required",
            "document_semantics": {
                "document_role": "建设方案",
                "subject_of_report": "行业数据资源与专业能力建设",
                "primary_thesis": "现有行业数据资源和专业能力构成首期建设基础。",
                "decision_boundary": "后续范围和责任仍需确认，不得写成既定承诺。",
                "author_purpose": "推动相关方理解现有基础并确认后续建设动作。",
                "argument_method": [{"statement": "先说明建设基础，再讨论后续动作。", "source_refs": [evidence]}],
                "supporting_basis": [{"statement": "正文列明行业数据资源和专业能力。", "source_refs": [evidence]}],
                "business_objects": ["行业数据资源", "专业能力"],
                "scope": "首期建设基础及其后续确认事项。",
                "decision_intent": "理解现有基础并确认后续动作。",
            },
            "document_thesis": {
                "statement": "现有行业数据资源和专业能力构成首期建设基础。",
                "argument_role": "thesis",
                "argument_weight": "core",
                "status": "existing",
                "evidence_refs": [evidence],
                "actor_refs": ["建设相关方"],
                "claim_origin": "source_explicit",
            },
            "heading_semantic_cards": [
                {
                    "heading_id": top["heading_id"],
                    "source_unit_id": top["unit_id"],
                    "source_heading": top["title"],
                    "level": top["level"],
                    "semantic_function": "提出建设方案总题",
                    "author_claim": "建设方案需要说明建设基础。",
                    "argument_role": "foundation",
                    "argument_weight": "core",
                    "claim_origin": "source_explicit",
                    "evidence_refs": [top["unit_id"]],
                },
                {
                    "heading_id": child["heading_id"],
                    "source_unit_id": child["unit_id"],
                    "source_heading": child["title"],
                    "level": child["level"],
                    "semantic_function": "说明建设基础",
                    "author_claim": "现有资源和能力构成建设基础。",
                    "argument_role": "foundation",
                    "argument_weight": "supporting",
                    "claim_origin": "source_explicit",
                    "evidence_refs": [child["unit_id"]],
                },
            ],
            "section_nodes": [
                {
                    "id": "c01",
                    "source_heading_id": top["heading_id"],
                    "source_heading": top["title"],
                    "section_thesis": "建设方案以现有资源和能力为基础。",
                    "argument_role": "foundation",
                    "argument_weight": "core",
                    "level": 1,
                    "status": "existing",
                    "evidence_refs": [evidence],
                    "actor_refs": ["建设相关方"],
                    "primary_consumer": "chapter-1",
                    "subsection_ids": ["c01-s01"],
                    "allowed_merges": [],
                    "claim_origin": "source_explicit",
                }
            ],
            "subsection_nodes": [
                {
                    "id": "c01-s01",
                    "parent_id": "c01",
                    "source_heading_id": child["heading_id"],
                    "source_heading": child["title"],
                    "section_thesis": "现有行业数据资源和专业能力构成首期建设基础。",
                    "argument_role": "foundation",
                    "argument_weight": "supporting",
                    "level": 2,
                    "status": "existing",
                    "evidence_refs": [evidence],
                    "actor_refs": ["建设相关方"],
                    "primary_consumer": "建设基础",
                    "allowed_merges": [],
                    "claim_origin": "source_explicit",
                }
            ],
            "argument_relations": [
                {
                    "id": "r01",
                    "from": "c01-s01",
                    "to": "c01",
                    "relation": "supports",
                    "weight_effect": "none",
                    "explanation": "建设基础支撑方案总题。",
                    "evidence_refs": [evidence],
                    "claim_origin": "source_explicit",
                }
            ],
            "argument_weighting": {
                "definition": "core保留总题，supporting保留展开事项。",
                "core_node_ids": ["c01"],
                "supporting_node_ids": ["c01-s01"],
                "detail_node_ids": [],
                "constraint_node_ids": [],
                "review_notes": [],
            },
            "mece_rules": {
                "partition_basis": "按来源标题层级划分。",
                "exhaustive_scope": "覆盖建设方案和建设基础。",
                "overlap_policy": "父子节点通过支持关系连接。",
                "groups": [
                    {
                        "parent_id": "c01",
                        "node_ids": ["c01-s01", "c01"],
                        "partition_basis": "按来源子标题划分。",
                        "exhaustive_scope": "覆盖建设基础正文。",
                        "overlap_policy": "一个来源事项只保留一个主要语义归属。",
                    }
                ],
                "review_notes": [],
            },
            "inference_register": [],
            "concept_occurrence_graph": {"concepts": [], "relations": [], "review_notes": []},
            "semantic_content_unit_coverage_mode": "required",
            "source_coverage": {
                "assignments": [
                    {
                        "source_unit_refs": [evidence],
                        "semantic_node_ids": ["c01", "c01-s01"],
                        "summary": "正文说明首期建设基础。",
                        "atomic_items": [
                            {
                                "item_id": "AI-001",
                                "statement": "现有行业数据资源和专业能力构成首期建设基础。",
                                "source_unit_refs": [evidence],
                                "claim_role": "foundation",
                                "evidence_role": "fact",
                                "evidence_priority": "P0",
                                "argument_duty": "premise",
                                "importance": "core",
                                "status": "existing",
                                "claim_origin": "source_explicit",
                                "coverage_anchors": ["行业数据资源", "专业能力"],
                                "actors": ["建设相关方"],
                                "conditions": ["首期建设"],
                                "numeric_facts": [],
                            },
                            {
                                "item_id": "AI-002",
                                "statement": "现有专业能力构成首期建设基础。",
                                "source_unit_refs": [evidence],
                                "claim_role": "foundation",
                                "evidence_role": "fact",
                                "evidence_priority": "P1",
                                "argument_duty": "support",
                                "importance": "constraint",
                                "status": "existing",
                                "claim_origin": "source_explicit",
                                "coverage_anchors": ["专业能力", "首期建设基础"],
                                "actors": ["建设相关方"],
                                "conditions": ["首期建设"],
                                "numeric_facts": [],
                            },
                            {
                                "item_id": "AI-003",
                                "statement": "行业数据资源用于首期建设基础。",
                                "source_unit_refs": [evidence],
                                "claim_role": "foundation",
                                "evidence_role": "fact",
                                "evidence_priority": "P2",
                                "argument_duty": "detail",
                                "importance": "detail",
                                "status": "existing",
                                "claim_origin": "source_explicit",
                                "coverage_anchors": ["行业数据资源", "首期建设基础"],
                                "actors": ["建设相关方"],
                                "conditions": ["首期建设"],
                                "numeric_facts": [],
                            },
                            {
                                "item_id": "AI-004",
                                "statement": "建设方案封面日期",
                                "source_unit_refs": [evidence],
                                "claim_role": "foundation",
                                "evidence_role": "fact",
                                "evidence_priority": "P2",
                                "argument_duty": "metadata",
                                "importance": "detail",
                                "status": "existing",
                                "claim_origin": "source_explicit",
                                "coverage_anchors": ["建设方案", "封面日期"],
                                "actors": [],
                                "conditions": [],
                                "numeric_facts": [],
                            }
                        ],
                    }
                ],
                "intentional_omissions": [],
                "review_notes": [],
            },
            "source_gaps": [],
        }
        model_path = self.project / SEMANTIC_ARGUMENT_MODEL
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
        self.model = model
        self.unit_ids = {item["unit_id"] for item in units}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_lightweight_semantic_check_renders_review_from_canonical_model(self) -> None:
        self.assertFalse((self.project / SEMANTIC_ARTIFACT).exists())

        code, report = run_semantic_understanding_audit(self.project)

        self.assertEqual(0, code, report["issues"])
        review = (self.project / SEMANTIC_ARTIFACT).read_text(encoding="utf-8")
        self.assertIn("本文由 semantic-argument-model.json 确定性渲染", review)
        self.assertIn("行业数据资源", review)
        self.assertFalse((self.project / "workbench/stages/00-semantic-understanding/semantic-understanding-audit.json").exists())

    def test_source_truth_compiles_but_outline_requires_professional_authoring(self) -> None:
        truth_path = compile_source_truth(self.project)
        truth = load_source_truth(truth_path)

        self.assertEqual([], audit_source_truth(truth))
        self.assertEqual(
            [],
            semantic_evidence_cross_issues(self.model, truth, source_unit_ids=self.unit_ids),
        )
        self.assertEqual("AI-001", truth["records"][0]["atomic_item_id"])
        self.assertEqual("fact", truth["records"][0]["claim_role"])
        self.assertEqual(
            truth["records"][0]["statement"],
            truth["records"][0]["semantic_units"][0]["text"],
        )
        self.assertEqual(4, len(truth["records"]))
        self.assertNotIn("retry", truth)
        self.assertTrue(all(record["page_refs"] == [] for record in truth["records"]))

        outline_path = compile_outline_draft(
            self.project,
            communication_goal="面向建设相关方说明现有基础并确认后续动作。",
        )
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
        issues = audit_outline(outline, truth, self.model)

        self.assertEqual(
            {"OUTLINE_AUTHOR_EDIT_REQUIRED"},
            {item.code for item in issues},
        )
        self.assertEqual("mechanical_draft", outline["editorial_authoring_status"])
        self.assertEqual("frozen", outline["source_truth_mapping_mode"])
        self.assertNotIn("retry", outline)
        self.assertEqual("ending", outline["pages"][-1]["page_type"])
        self.assertEqual(
            ["cover", "agenda", "chapter", "content", "ending"],
            [page["page_type"] for page in outline["pages"]],
        )
        content_page = next(page for page in outline["pages"] if page["page_type"] == "content")
        content_page["non_substitutable_value"] = "删除本页后，受众无法判断现有基础是否支持后续建设。"
        content_page["argument_chain"] = "现有资源与能力 → 首期建设基础 → 后续建设判断"
        content_page["evidence_roles"] = {
            "claim": content_page["core_message_derivation"]["source_refs"],
            "boundary": content_page["boundary_refs"],
            "trace_only": content_page["detail_refs"],
        }
        content_page["excluded_from_onscreen"] = list(content_page["detail_refs"])
        chapter_page = next(page for page in outline["pages"] if page["page_type"] == "chapter")
        chapter_page.update(
            {
                "source_section_node_id": "c01",
                "source_section_title": "建设方案",
                "title": "建设方案",
                "editorial_chapter_label": "建设基础",
            }
        )
        outline["editorial_authoring_status"] = "author_edited"
        self.assertEqual([], audit_outline(outline, truth, self.model))
        self.assertEqual("c01-s01", content_page["primary_argument_node_id"])
        self.assertEqual(["c01-s01"], content_page["source_argument_node_ids"])
        metadata_refs = {
            record["id"] for record in truth["records"]
            if record["argument_duty"] == "metadata"
        }
        self.assertEqual(
            {record["id"] for record in truth["records"]} - metadata_refs,
            set(content_page["source_refs"]),
        )
        self.assertTrue(metadata_refs.isdisjoint(content_page["detail_refs"]))
        consumed_refs = {
            source_ref
            for unit in content_page["content_units"]
            for source_ref in unit["source_refs"]
        } | set(content_page["detail_refs"])
        self.assertEqual(set(content_page["source_refs"]), consumed_refs)
        self.assertLess(len(content_page["content_units"]), len(content_page["source_refs"]))
        premise_unit = next(
            unit for unit in content_page["content_units"]
            if "premise" in unit["argument_duties"]
        )
        self.assertTrue(premise_unit["onscreen_required"])
        self.assertGreaterEqual(len(premise_unit["onscreen_anchors"]), 2)
        self.assertNotIn("建设相关方", premise_unit["coverage_anchors"])
        self.assertFalse(
            set(content_page["core_message_derivation"]["source_refs"])
            & set(content_page["boundary_refs"])
        )
        self.assertEqual(
            {
                "node_id": "c01-s01",
                "disposition": "standalone_page",
                "page_id": content_page["page_id"],
                "rationale": "建设基础具有独立来源标题、语义命题和证据责任，先编译为独立候选页；仅在后续规划判断确认共享主题与主关系后才可合并。",
            },
            outline["argument_node_dispositions"][0],
        )

    def test_strict_atomic_item_requires_semantic_argument_duty(self) -> None:
        # Evidence role and claim role remain derived from the target node,
        # while argument duty belongs to the source-faithful atomic claim.
        atomic = self.model["source_coverage"]["assignments"][0]["atomic_items"][0]
        del atomic["evidence_role"]
        del atomic["claim_role"]
        del atomic["argument_duty"]
        model_path = self.project / SEMANTIC_ARGUMENT_MODEL
        model_path.write_text(json.dumps(self.model, ensure_ascii=False, indent=2), encoding="utf-8")

        code, report = run_semantic_understanding_audit(self.project)
        self.assertNotEqual(0, code)
        self.assertIn(
            "SEMANTIC_ATOMIC_ARGUMENT_DUTY_MISSING",
            {item["code"] for item in report["issues"]},
        )

    def test_official_cli_executes_new_lightweight_path_without_control_artifacts(self) -> None:
        goal = "面向建设相关方说明现有基础并确认后续动作。"

        commands = (
            ["compile-source-truth", str(self.project)],
            [
                "source-truth-audit",
                str(self.project),
                "--input",
                str(self.project / "workbench/stages/01-analysis/source-truth.json"),
            ],
            [
                "compile-outline-draft",
                str(self.project),
                "--communication-goal",
                goal,
            ],
        )
        for argv in commands:
            completed = subprocess.run(
                [sys.executable, "-m", "cyberppt", *argv],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr or completed.stdout)
            self.assertEqual("", completed.stderr)
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "cyberppt",
                "outline-audit",
                str(self.project),
                "--input",
                str(self.project / "workbench/stages/01-analysis/outline.json"),
            ],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(4, completed.returncode)
        self.assertIn("OUTLINE_AUTHOR_EDIT_REQUIRED", completed.stdout)
        forbidden = (
            "workbench/artifact-ledger.json",
            "workbench/approvals",
            "workbench/decisions",
            "workbench/runs",
            "workbench/stages/00-semantic-understanding/semantic-generation-receipt.json",
            "workbench/stages/00-semantic-understanding/semantic-understanding-audit.json",
            "workbench/stages/01-analysis/source-truth-audit.json",
            "workbench/stages/01-analysis/source-truth-attempts",
            "workbench/stages/01-analysis/source-truth-escalation.json",
            "workbench/stages/01-analysis/outline-attempts",
            "workbench/stages/01-analysis/outline-escalation.json",
        )
        self.assertEqual(
            [],
            [relative for relative in forbidden if (self.project / relative).exists()],
        )
        self.assertTrue((self.project / "workbench/stages/01-analysis/outline-audit.json").is_file())
        self.assertTrue((self.project / "workbench/stages/01-analysis/outline-audit.md").is_file())
        self.assertTrue((self.project / "workbench/stages/01-analysis/outline-human-review.md").is_file())

    def test_outline_recompile_changes_only_the_outline_artifact(self) -> None:
        model_path = self.project / SEMANTIC_ARGUMENT_MODEL
        truth_path = compile_source_truth(self.project)
        model_before = model_path.read_bytes()
        truth_before = truth_path.read_bytes()

        compile_outline_draft(
            self.project,
            communication_goal="先说明现有基础。",
        )
        outline_path = compile_outline_draft(
            self.project,
            communication_goal="说明现有基础并确认后续动作。",
        )

        self.assertEqual(model_before, model_path.read_bytes())
        self.assertEqual(truth_before, truth_path.read_bytes())
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
        self.assertEqual("说明现有基础并确认后续动作。", outline["communication_goal"])


if __name__ == "__main__":
    unittest.main()
