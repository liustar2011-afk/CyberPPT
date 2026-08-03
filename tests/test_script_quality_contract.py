from __future__ import annotations

import json
from pathlib import Path
import unittest

from cyberppt.script_quality_contract import (
    ScriptPage,
    _issue,
    _source_consumption_issues,
    _visual_structure_judgment_issues,
    audit_script_quality,
    build_communication_review,
    extract_speaker_notes,
    meaningful_char_count,
    onscreen_effective_char_target,
    onscreen_story_roles,
    parse_script_markdown,
    parse_selection_notes,
    selection_notes_are_structured,
    text_similarity,
)

ROOT = Path(__file__).resolve().parents[1]
POWER_PROJECT = ROOT / "projects" / "power-supply-demand-forecast-early-warning"
SCRIPT_AUDIT_FIXTURES = ROOT / "tests" / "fixtures" / "script_audit"


SCRIPT = """# 第8—9页脚本审稿稿

## 第8页：第二章：定位、目标与研究边界

- 页面类型：章节过渡页
- 上屏文字：第二章：定位、目标与研究边界

## 第9页：总体定位

- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 完整文字稿：在现状、变化和能力断点已经建立的前提下，建设方向初步定位为面向行业的公共能力。该定位明确研究方向和服务对象，同时保留专业运行系统的职责边界。正式判断仍需由数据、模型、业务分析和专家会商共同形成。
- 文字稿取舍说明：
  - 必留上屏：行业公共能力；专业系统边界
  - 仅讲解：正式判断仍需数据、模型、业务分析和专家会商共同形成
  - 仅追溯：S015、S026、S059
- 证据映射：公共能力定位→S015；专业系统边界→S026；正式范围待定→S059
- 上屏文字：

  **行业公共能力**

  - 服务行业研判。

  **专业系统边界**

  - 保留专业职责边界。

- 证据：S015、S026、S059
- 边界：正式范围待后续确定。
- 视觉结构：判断证据支撑——中央公共能力定位，两侧职责边界托举。
- 讲解提示：先说定位再说边界。

【演讲者备注】

建设定位是面向行业的公共能力，服务履职与行业共用；同时明确与专业系统的职责分工，不替代调度、出清和企业计划。正式范围仍需结合资源摸底和原型验证进一步确定，当前阶段不提前锁定实施参数。
"""


def strict_outline(*pages: dict[str, object]) -> dict[str, object]:
    return {"argument_contract_mode": "strict", "pages": list(pages)}


def source_truth(*records: dict[str, object]) -> dict[str, object]:
    return {"argument_contract_mode": "strict", "records": list(records)}


def _consumption_fixture(receipt: dict[str, object] | None) -> tuple[ScriptPage, dict[str, object]]:
    units = [
        {
            "unit_id": "CU-P01-01",
            "role": "primary",
            "statement": "统一目录支撑行业数据服务",
            "source_refs": ["S001"],
            "source_statements": ["统一目录支撑行业数据服务"],
        },
        {
            "unit_id": "CU-P01-02",
            "role": "boundary",
            "statement": "价格与责任待后续确认",
            "source_refs": ["S002"],
            "source_statements": ["价格与责任待后续确认"],
        },
    ]
    page = ScriptPage(
        page_id="p01",
        sequence=1,
        heading="",
        page_type="content",
        title="",
        main_message="统一目录支撑行业数据服务",
        full_prose="统一目录支撑行业数据服务",
        selection_notes="",
        evidence_map="",
        evidence_map_refs=(),
        source_refs=("S001",),
        boundary_source_refs=("S002",),
        boundary="",
        visual_structure="闭环",
        onscreen_text="统一目录支撑行业数据服务",
        module_titles=(),
        contract_receipt=receipt,
    )
    contract = {
        "source_evidence_contract": {"mode": "required", "units": units},
        "content_units": units,
    }
    return page, contract


class ContentUnitConsumptionTests(unittest.TestCase):
    def test_missing_declaration_is_blocked(self) -> None:
        page, contract = _consumption_fixture({})
        issues = _source_consumption_issues(page, contract)
        self.assertEqual(
            ["CONTENT_UNIT_CONSUMPTION_DECLARATION_MISSING"],
            [issue.code for issue in issues],
        )

    def test_mismatched_declaration_is_blocked(self) -> None:
        page, contract = _consumption_fixture(
            {"consumed_content_unit_ids": ["CU-P01-02"]}
        )
        issues = _source_consumption_issues(page, contract)
        self.assertEqual(
            ["CONTENT_UNIT_CONSUMPTION_DECLARATION_MISMATCH"],
            [issue.code for issue in issues],
        )

    def test_boundary_unit_is_traceability_only(self) -> None:
        page, contract = _consumption_fixture(
            {"consumed_content_unit_ids": ["CU-P01-01"]}
        )
        self.assertEqual([], _source_consumption_issues(page, contract))


class ScriptMarkdownParserTests(unittest.TestCase):
    def test_four_digit_source_ids_are_parsed_as_complete_refs(self) -> None:
        document = parse_script_markdown(
            """## 第23页：四位证据引用
- 页面类型：内容页
- 页面标题：四位证据引用
- 主判断：四位证据引用应保持完整。
- 证据：S0410、S0420
- 证据映射：组织→S0410；原型→S0420
- 完整文字稿：这是足够长的完整文字稿，用于证明解析器保留四位来源标识，而不是把它截断为三位。这里继续补充若干业务事实、关系和结果，确保该字段具备短文章形态并可供质量合同检查。
- 文字稿取舍说明：必留上屏：组织和原型；仅讲解：细节；仅追溯：S0410、S0420
- 上屏文字：

  **组织**
  - 组织机制与责任清单形成可追溯的启动基础

  **原型**
  - 原型验证数据导入、质量检查和报告生成流程

【视觉结构，不上屏】
采用阶段推进主链呈现组织到原型的关系。

【演讲者备注】

组织与原型按同一启动链路推进。
"""
        )
        self.assertEqual(("S0410", "S0420"), document.pages[0].source_refs)
        self.assertEqual(("S0410", "S0420"), document.pages[0].evidence_map_refs)

    def test_source_id_ranges_expand_to_atomic_refs(self) -> None:
        page = parse_script_markdown(
            """## 第23页：范围证据引用
- 页面类型：内容页
- 页面标题：范围证据引用
- 主判断：范围引用在审计时展开为原子来源。
- 证据：S0410—S0412
- 证据映射：组织与原型→S0410—S0412
- 完整文字稿：范围引用仍然对应明确的业务事实、关系和结果，脚本解析器应当展开每一个原子来源并保留来源顺序。
- 文字稿取舍说明：必留上屏：组织与原型；仅讲解：细节；仅追溯：S0410—S0412
- 上屏文字：

  **组织与原型**
  - 组织、数据和原型按同一启动链路推进

【视觉结构，不上屏】
采用阶段推进主链呈现组织到原型的关系。

【演讲者备注】

组织与原型按同一启动链路推进。
"""
        ).pages[0]
        self.assertEqual(("S0410", "S0411", "S0412"), page.source_refs)
        self.assertEqual(("S0410", "S0411", "S0412"), page.evidence_map_refs)

    def test_inline_module_titles_are_retained_as_modules(self) -> None:
        page = parse_script_markdown(
            """## 第16页：共性能力底座
- 页面类型：内容页
- 上屏文字：
  **业务标准**｜目录、对象、尺度和口径统一
  **分层数据**｜必需数据先成稳定链路
  **模型体系**｜分步建设并滚动回测
"""
        ).pages[0]

        self.assertEqual(
            ("业务标准", "分层数据", "模型体系"),
            page.module_titles,
        )
        self.assertIn("口径统一", page.onscreen_text)

    def test_non_onscreen_visual_structure_block_is_parsed_separately(self) -> None:
        page = parse_script_markdown(
            """## 第11页：五层总体能力框架
- 页面类型：内容页
- 页面标题：五层总体能力框架
- 上屏文字：

  **运行闭环**
  - 数据治理 → 模型计算 → 审核发布

【视觉结构，不上屏】
五层纵向架构与一条横向运行闭环同构呈现。

【演讲者备注】
说明五层框架。
"""
        ).pages[0]
        self.assertIn("运行闭环", page.onscreen_text)
        self.assertNotIn("视觉结构", page.onscreen_text)
        self.assertEqual(
            "五层纵向架构与一条横向运行闭环同构呈现。",
            page.visual_structure,
        )

    def test_parser_accepts_core_message_human_label(self) -> None:
        document = parse_script_markdown(
            """## 第1页：建设目标与能力框架
- 页面类型：内容页
- 页面标题：建设目标与能力框架
- 核心结论：总体能力框架由五个层次构成，各层分别承担相应职责。
- 证据：S021
- 完整文字稿：总体能力框架由五个层次构成，各层分别承担相应职责，并分别展开业务应用、成果服务、模型分析、数据治理和运行保障等内容。
- 文字稿取舍说明：必留上屏：五层名称；仅讲解：职责说明；仅追溯：S021。
- 证据映射：S021
- 视觉结构：五层结构
- 上屏文字：五层总体能力框架
"""
        )
        self.assertEqual(
            "总体能力框架由五个层次构成，各层分别承担相应职责。",
            document.pages[0].core_message,
        )

    def test_extracts_pages_and_fields(self) -> None:
        document = parse_script_markdown(SCRIPT)

        self.assertEqual(["p08", "p09"], [page.page_id for page in document.pages])
        self.assertEqual("chapter", document.pages[0].page_type)
        self.assertEqual("总体定位", document.pages[1].title)
        self.assertEqual(("S015", "S026", "S059"), document.pages[1].source_refs)
        self.assertEqual(("行业公共能力", "专业系统边界"), document.pages[1].module_titles)
        self.assertEqual("先说定位再说边界。", document.pages[1].coaching_tip)
        self.assertTrue(selection_notes_are_structured(document.pages[1].selection_notes))
        parsed = parse_selection_notes(document.pages[1].selection_notes)
        self.assertIn("行业公共能力", parsed["必留上屏"])
        self.assertIn("S015", parsed["仅追溯"])

    def test_rejects_document_without_pages(self) -> None:
        with self.assertRaisesRegex(ValueError, "no page headings"):
            parse_script_markdown("# empty")

    def test_onscreen_block_stops_at_next_backend_field(self) -> None:
        page = parse_script_markdown(SCRIPT).pages[1]

        self.assertNotIn("- 证据：", page.onscreen_text)
        self.assertNotIn("S015", page.onscreen_text)

    def test_extracts_optional_presentation_fields_and_keeps_legacy_defaults(self) -> None:
        page = parse_script_markdown(
            """## 第1页：示例
- 页面类型：内容页
- 上屏结论：结论
- 上屏文字：正文
- 版式母题：process_atlas
- 场景角色：no_scene
- 生图锁定文字：短标签
- 视觉证明：供需信息经过数据治理、模型推演和专家会商形成行业研判成果
"""
        ).pages[0]
        self.assertEqual("process_atlas", page.layout_motif)
        self.assertEqual("no_scene", page.scene_role)
        self.assertEqual("短标签", page.image_locked_text)
        self.assertEqual(
            "供需信息经过数据治理、模型推演和专家会商形成行业研判成果",
            page.visual_proof,
        )

        legacy = parse_script_markdown(
            """## 第2页：旧页
- 页面类型：内容页
- 上屏结论：结论
- 上屏文字：正文
"""
        ).pages[0]
        self.assertEqual("", legacy.layout_motif)
        self.assertEqual("", legacy.scene_role)
        self.assertEqual("", legacy.image_locked_text)
        self.assertEqual("", legacy.visual_proof)


class ScriptContractAuditTests(unittest.TestCase):
    def test_trailing_boundary_caveat_cannot_become_peer_module(self) -> None:
        outline = strict_outline(
            {
                "page_id": "p12",
                "sequence": 12,
                "page_type": "content",
                "title": "建设范围与研究边界",
                "page_mission": "说明首期范围并保留研究边界。",
                "core_message": "首期聚焦两项业务；完整系统范围仍待论证。",
                "source_refs": ["S015"],
                "content_units": [
                    {"statement": "首期聚焦两项业务。", "source_refs": ["S015"], "role": "primary"}
                ],
            }
        )
        truth = source_truth(
            {"id": "S015", "type": "J", "status": "原文陈述", "statement": "首期聚焦两项业务。"},
        )
        script = """## 第12页：建设范围与研究边界
- 页面类型：内容页
- 页面标题：建设范围与研究边界
- 主判断：首期聚焦两项业务；完整系统范围仍待论证。
- 完整文字稿：首期聚焦两项业务，并保留后续论证事项。首期业务形成可运行闭环，并按数据条件逐步扩展。
- 文字稿取舍说明：
  - 必留上屏：首期两项业务
  - 仅讲解：后续论证事项
  - 仅追溯：S015
- 证据映射：首期范围→S015
- 上屏文字：
  **首期两项业务**
  - 月度季度分析和年度报告自动化
  **研究边界**
  - 完整系统范围仍待论证
- 证据：S015
【视觉结构，不上屏】
突出首期两项业务。
【演讲者备注】
首期聚焦两项业务，并根据验证结果逐步扩展。
"""
        codes = {issue.code for issue in audit_script_quality(parse_script_markdown(script), outline, truth)}
        self.assertIn("OFF_TOPIC_CONSTRAINT_MODULE", codes)

    def test_required_page_contract_receipt_must_be_present(self) -> None:
        outline = strict_outline(
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "总体定位",
                "argument_role": "positioning",
                "source_refs": ["S015", "S026", "S059"],
                "prerequisite_pages": [],
            }
        )
        outline["page_contract_receipt_mode"] = "required"
        truth = source_truth(
            {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
            {"id": "S026", "type": "B", "status": "研究边界", "statement": "专业边界。"},
            {"id": "S059", "type": "B", "status": "研究边界", "statement": "正式范围待定。"},
        )

        codes = {
            issue.code
            for issue in audit_script_quality(parse_script_markdown(SCRIPT), outline, truth)
        }

        self.assertIn("PAGE_CONTRACT_RECEIPT_MISSING", codes)

    def test_matching_page_contract_receipt_passes(self) -> None:
        outline = strict_outline(
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "总体定位",
                "argument_role": "positioning",
                "source_refs": ["S015", "S026", "S059"],
                "prerequisite_pages": [],
                "main_message": "初步定位为面向行业的公共能力。",
            }
        )
        outline["page_contract_receipt_mode"] = "required"
        receipt = (
            '<!-- cyberppt-page-contract {"schema":"cyberppt.page_contract_receipt.v1",'
            '"page_id":"p09","main_message":"初步定位为面向行业的公共能力。",'
            '"new_value_realized":true,"reserved_for_later_respected":true} -->\n'
        )
        script = SCRIPT.replace("【演讲者备注】", receipt + "【演讲者备注】")
        truth = source_truth(
            {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
            {"id": "S026", "type": "B", "status": "研究边界", "statement": "专业边界。"},
            {"id": "S059", "type": "B", "status": "研究边界", "statement": "正式范围待定。"},
        )

        codes = {
            issue.code
            for issue in audit_script_quality(parse_script_markdown(script), outline, truth)
        }

        self.assertFalse(any(code.startswith("PAGE_CONTRACT_") for code in codes))

    def test_communication_review_tracks_mission_and_lead(self) -> None:
        script = parse_script_markdown(
            """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：公共能力定位支撑行业研判。
- 上屏文字：

  公共能力定位支撑行业研判。

  **服务对象**

  - 服务行业公共研判。

- 视觉结构：判断证据支撑。

【演讲者备注】

建设定位、服务对象和职责边界共同构成本阶段的基本判断。
"""
        )
        review = build_communication_review(
            script,
            {
                "pages": [
                    {
                        "page_id": "p09",
                        "business_question": "拟建什么性质的能力",
                    }
                ]
            },
        )

        self.assertEqual(1, review["content_pages"])
        self.assertEqual(1, review["mission_coverage"])
        self.assertEqual(1, review["lead_match_count"])
        page = review["pages"][0]
        self.assertEqual("拟建什么性质的能力", page["mission"])
        self.assertTrue(page["lead_matches_main_message"])
        self.assertIn("semantic_coverage", page)
        self.assertEqual("high", review["reading_density_default"])
        self.assertEqual(1, review["reading_density_low_count"])
        self.assertEqual("low", page["reading_density_status"])
        self.assertEqual(
            {"conclusion", "evidence", "relation", "closure"},
            set(page["story_roles"]),
        )
        self.assertEqual("manual_review", page["review_questions"]["single_mission"])

    def test_effective_density_ignores_markdown_and_uses_adaptive_target(self) -> None:
        page = parse_script_markdown(
            """## 第9页：密度测试
- 页面类型：内容页
- 主判断：形成完整判断。
- 上屏结论：形成完整判断
- 完整文字稿：这是用于测试动态密度目标的完整文字稿，持续补充业务事实、证据关系和页面结论，使正文长度足以触发最低有效字符门槛。
- 上屏文字：
  **证据模块**
  - 事实一支撑判断。
  - 事实二解释关系。
"""
        ).pages[0]

        self.assertEqual(
            len("形成完整判断证据模块事实一支撑判断事实二解释关系"),
            meaningful_char_count(page.onscreen_judgment + page.onscreen_text),
        )
        self.assertEqual(220, onscreen_effective_char_target(page))
        self.assertTrue(onscreen_story_roles(page)["relation"])

    def test_all_content_pages_require_density_without_forcing_visible_conclusion(self) -> None:
        script = """## 第10页：供需研判底座
- 页面类型：内容页
- 页面标题：供需研判底座
- 主判断：供需研判由数据、模型和成果流程共同承载。
- 完整文字稿：供需研判需要统一数据口径，形成稳定的数据接入和治理链路，再按业务对象和时间尺度组织模型计算。模型结果还要经过业务解释、报告生产、审核发布和版本留痕，实际数据形成后再回到误差复盘，支持下一轮研判。
- 文字稿取舍说明：
  - 必留上屏：数据、模型、成果流程和复盘关系
  - 仅讲解：字段级治理方式
  - 仅追溯：S001
- 证据映射：底座关系→S001
- 上屏文字：
  **数据**
  - 统一数据。
  **模型**
  - 形成预测。
- 证据：S001
【视觉结构，不上屏】
以数据、模型和成果流程构成连续主链。
【演讲者备注】
说明数据、模型和成果流程的业务关系。
"""
        outline = strict_outline(
            {
                "page_id": "p10",
                "sequence": 10,
                "page_type": "content",
                "title": "供需研判底座",
                "argument_role": "solution",
                "source_refs": ["S001"],
                "prerequisite_pages": [],
            }
        )
        issues = audit_script_quality(
            parse_script_markdown(script),
            outline,
            source_truth(
                {
                    "id": "S001",
                    "type": "R",
                    "status": "原文陈述",
                    "statement": "数据、模型和成果流程构成研判底座。",
                }
            ),
        )
        codes = {issue.code for issue in issues}

        self.assertIn("ONSCREEN_STORY_DENSITY_LOW", codes)
        self.assertNotIn("ONSCREEN_JUDGMENT_MISSING", codes)
        self.assertNotIn("SCRIPT_JUDGMENT_INTRODUCED", codes)
        self.assertNotIn("ONSCREEN_STORY_NOT_CLOSED", codes)

    def test_communication_review_warns_when_lead_is_not_main_message(self) -> None:
        script = parse_script_markdown(
            """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：公共能力定位支撑行业研判。
- 上屏文字：

  **服务对象**

  - 服务行业公共研判。
"""
        )
        review = build_communication_review(
            script,
            {"pages": [{"page_id": "p09", "business_question": "拟建什么能力"}]},
        )

        codes = {item["code"] for item in review["pages"][0]["findings"]}
        self.assertIn("MAIN_MESSAGE_NOT_FIRST_ONSCREEN_LINE", codes)

    def test_legacy_global_mode_does_not_force_a_judgment(self) -> None:
        outline = strict_outline(
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "总体定位",
                "argument_role": "positioning",
                "source_refs": ["S015", "S026", "S059"],
                "prerequisite_pages": [],
            }
        )
        outline["visible_judgment_mode"] = "required"
        truth = source_truth(
            {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
            {"id": "S026", "type": "B", "status": "研究边界", "statement": "专业边界。"},
            {"id": "S059", "type": "B", "status": "研究边界", "statement": "正式范围待定。"},
        )

        missing_codes = {
            issue.code
            for issue in audit_script_quality(
                parse_script_markdown(SCRIPT),
                outline,
                truth,
            )
        }
        self.assertNotIn("ONSCREEN_JUDGMENT_MISSING", missing_codes)

        revised = SCRIPT.replace(
            "- 主判断：初步定位为面向行业的公共能力。\n",
            "- 主判断：初步定位为面向行业的公共能力。\n"
            "- 上屏结论：面向行业的公共能力定位支撑行业研判\n",
            1,
        )
        revised_codes = {
            issue.code
            for issue in audit_script_quality(
                parse_script_markdown(revised),
                outline,
                truth,
            )
        }
        self.assertIn("SCRIPT_JUDGMENT_INTRODUCED", revised_codes)

        punctuated = revised.replace(
            "- 上屏结论：面向行业的公共能力定位支撑行业研判\n",
            "- 上屏结论：面向行业的公共能力定位支撑行业研判。\n",
        )
        punctuated_codes = {
            issue.code
            for issue in audit_script_quality(
                parse_script_markdown(punctuated),
                outline,
                truth,
            )
        }
        self.assertIn("SCRIPT_JUDGMENT_INTRODUCED", punctuated_codes)

    @unittest.skipUnless(
        (POWER_PROJECT / "workbench/stages/01-analysis/outline.json").is_file(),
        "power-supply-demand project artifacts not present",
    )
    def test_power_foundation_regression_is_blocked(self) -> None:
        script = parse_script_markdown(
            (SCRIPT_AUDIT_FIXTURES / "power_foundation_premature_scope.md").read_text(
                encoding="utf-8"
            )
        )
        outline = json.loads(
            (POWER_PROJECT / "workbench/stages/01-analysis/outline.json").read_text(
                encoding="utf-8"
            )
        )
        truth = json.loads(
            (
                POWER_PROJECT / "workbench/stages/01-analysis/source-truth.json"
            ).read_text(encoding="utf-8")
        )

        codes = {issue.code for issue in audit_script_quality(script, outline, truth)}

        self.assertIn("PREMATURE_SCOPE_CLAIM", codes)

    @unittest.skipUnless(
        (POWER_PROJECT / "workbench/stages/01-analysis/outline.json").is_file(),
        "power-supply-demand project artifacts not present",
    )
    def test_power_scene_matrix_is_not_treated_as_isolated_method_page(self) -> None:
        script = parse_script_markdown(
            (SCRIPT_AUDIT_FIXTURES / "power_scene_matrix.md").read_text(
                encoding="utf-8"
            )
        )
        outline = json.loads(
            (POWER_PROJECT / "workbench/stages/01-analysis/outline.json").read_text(
                encoding="utf-8"
            )
        )
        truth = json.loads(
            (
                POWER_PROJECT / "workbench/stages/01-analysis/source-truth.json"
            ).read_text(encoding="utf-8")
        )

        codes = {issue.code for issue in audit_script_quality(script, outline, truth)}

        self.assertNotIn("MATRIX_AXES_MISSING", codes)
        self.assertNotIn("MULTIPLE_PAGE_MISSIONS", codes)

    def test_partial_batch_does_not_require_absent_outline_pages(self) -> None:
        outline = strict_outline(
            {
                "page_id": "p08",
                "sequence": 8,
                "page_type": "chapter",
                "title": "第二章：定位、目标与研究边界",
            },
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "总体定位",
                "argument_role": "positioning",
                "source_refs": ["S015", "S026", "S059"],
                "prerequisite_pages": ["p07"],
                "main_claim_status": "proposed",
            },
            {
                "page_id": "p10",
                "sequence": 10,
                "page_type": "content",
                "title": "能力框架",
                "argument_role": "solution",
                "source_refs": ["S017"],
                "prerequisite_pages": ["p09"],
            },
        )
        truth = source_truth(
            {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
            {"id": "S026", "type": "B", "status": "研究边界", "statement": "专业边界。"},
            {"id": "S059", "type": "B", "status": "研究边界", "statement": "正式范围待定。"},
        )

        issues = audit_script_quality(parse_script_markdown(SCRIPT), outline, truth)

        # Reading-page density is now checked for the supplied content page;
        # the partial batch must still not invent requirements for absent p10.
        self.assertTrue(issues)
        self.assertTrue(all("p10" not in issue.pages for issue in issues))

    def test_chapter_page_with_main_message_is_rejected(self) -> None:
        bad = SCRIPT.replace(
            "- 上屏文字：第二章：定位、目标与研究边界",
            "- 主判断：本章明确完整建设方案。\n- 上屏文字：第二章：定位、目标与研究边界",
        )

        issues = audit_script_quality(
            parse_script_markdown(bad),
            strict_outline(
                {
                    "page_id": "p08",
                    "sequence": 8,
                    "page_type": "chapter",
                    "title": "第二章：定位、目标与研究边界",
                }
            ),
            source_truth(),
        )

        self.assertIn("CHAPTER_PAGE_HAS_CONTENT", {issue.code for issue in issues})

    def test_foundation_page_cannot_claim_first_phase_scope(self) -> None:
        script = parse_script_markdown(
            """## 第4页：工作基础
- 页面类型：内容页
- 页面标题：工作基础
- 主判断：现有基础能够直接支撑首期建设全国总盘和定期报告。
- 完整文字稿：本页应以既有统计、研判和协调工作事实为主。若把现有基础能够直接支撑首期建设全国总盘和定期报告写成工作基础页的核心判断，就把尚未进入范围论证的首期建设安排提前固化了。正确写法应先陈述已形成的工作依托，再在范围页讨论首期是否从全国总盘和定期报告入手。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S006
- 上屏文字：
  **既有基础**
  - 已具备统计和报告工作。
- 证据：S006
- 边界：本页陈述既有事实。
- 视觉结构：工作基础链。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p04",
                "sequence": 4,
                "page_type": "content",
                "title": "工作基础",
                "argument_role": "foundation",
                "source_refs": ["S006"],
                "prerequisite_pages": [],
                "main_claim_status": "confirmed",
            }
        )
        truth = source_truth(
            {
                "id": "S006",
                "type": "F",
                "status": "已形成",
                "statement": "具备行业协调基础。",
            }
        )

        codes = {issue.code for issue in audit_script_quality(script, outline, truth)}

        self.assertIn("PREMATURE_SCOPE_CLAIM", codes)

    def test_foundation_page_rejects_off_topic_quality_module(self) -> None:
        script = parse_script_markdown(
            """## 第4页：知识资产基础
- 页面类型：内容页
- 页面标题：知识资产基础
- 主判断：三类存量知识资产共同构成智能应用基础。
- 完整文字稿：现有学科、题目和行业数据共同构成知识资产基础，并可支撑后续学习、教学和分析应用。
- 文字稿取舍说明：本页只说明既有知识资产。
- 证据映射：资产规模→S001
- 上屏文字：
  **资产规模**
  - 已形成30个学科、约30万条题目和40年行业数据。
  **质量要求**
  - 原题不得开放，数据必须隔离，并防止模型幻觉和内容泄露。
- 证据：S001
- 边界：应用能力和治理机制留待后续页面。
- 视觉结构：三类资产共同支撑知识底座。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p04",
                "sequence": 4,
                "page_type": "content",
                "title": "知识资产基础",
                "argument_role": "foundation",
                "page_job": "说明已经具备哪些知识资产",
                "business_question": "已经形成哪些知识资产",
                "main_message": "三类存量知识资产共同构成智能应用基础",
                "source_refs": ["S001"],
                "prerequisite_pages": [],
            }
        )
        truth = source_truth(
            {
                "id": "S001",
                "type": "F",
                "status": "原文陈述",
                "statement": "已形成学科、题目和行业数据资产。",
            }
        )

        issues = audit_script_quality(script, outline, truth)
        matching = [
            issue for issue in issues
            if issue.code == "OFF_TOPIC_CONSTRAINT_MODULE"
        ]

        self.assertEqual(1, len(matching))
        self.assertEqual("error", matching[0].severity)

    def test_safety_page_allows_quality_and_security_boundary_modules(self) -> None:
        script = parse_script_markdown(
            """## 第17页：数据安全与题源保护
- 页面类型：内容页
- 页面标题：数据安全与题源保护
- 主判断：分层防护保护题源和业务数据。
- 完整文字稿：本页说明题源保护、权限隔离、人工审核和审计处置如何共同形成数据安全机制。
- 文字稿取舍说明：本页聚焦安全治理。
- 证据映射：安全机制→S001
- 上屏文字：
  **安全边界**
  - 原题不得开放，通过权限隔离降低泄露风险。
  **质量要求**
  - 生成内容经人工审核后进入业务服务。
- 证据：S001
- 边界：具体产品选型留待实施阶段。
- 视觉结构：分层安全防护。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p17",
                "sequence": 17,
                "page_type": "content",
                "title": "数据安全与题源保护",
                "argument_role": "assurance",
                "page_job": "说明如何保护题源和业务数据",
                "business_question": "如何形成数据安全防护",
                "main_message": "分层防护保护题源和业务数据",
                "source_refs": ["S001"],
                "prerequisite_pages": [],
            }
        )
        truth = source_truth(
            {
                "id": "S001",
                "type": "F",
                "status": "原文陈述",
                "statement": "题源和业务数据需要分层防护。",
            }
        )

        codes = {
            issue.code
            for issue in audit_script_quality(script, outline, truth)
        }

        self.assertNotIn("OFF_TOPIC_CONSTRAINT_MODULE", codes)

    def test_incidental_constraint_phrase_is_not_treated_as_a_module(self) -> None:
        script = parse_script_markdown(
            """## 第10页：学校学科智能分析
- 页面类型：内容页
- 页面标题：学校学科智能分析
- 主判断：多源数据形成可比较的学科规划建议。
- 完整文字稿：管理者选择目标年度、区域、专业和资源条件后，平台组织行业、招聘、培养和就业数据，形成可比较的情景方案。
- 文字稿取舍说明：本页聚焦规划分析流程。
- 证据映射：规划分析→S001
- 上屏文字：
  **情景分析**
  - 管理者选择目标年度、区域范围、专业和约束条件后开展情景比较。
  **规划建议**
  - 输出招生、培养和就业建议。
- 证据：S001
- 边界：重大调整由学校审议。
- 视觉结构：规划分析闭环。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p10",
                "sequence": 10,
                "page_type": "content",
                "title": "学校学科智能分析",
                "argument_role": "solution",
                "page_job": "说明学校如何形成学科规划建议",
                "business_question": "如何利用多源数据优化学科规划",
                "main_message": "多源数据形成可比较的学科规划建议",
                "source_refs": ["S001"],
                "prerequisite_pages": [],
            }
        )
        truth = source_truth(
            {
                "id": "S001",
                "type": "F",
                "status": "原文陈述",
                "statement": "管理者可设置分析条件并比较情景。",
            }
        )

        codes = {
            issue.code
            for issue in audit_script_quality(script, outline, truth)
        }

        self.assertNotIn("OFF_TOPIC_CONSTRAINT_MODULE", codes)

    def test_proposed_source_cannot_be_upgraded_to_completed(self) -> None:
        script = parse_script_markdown(
            """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：已经建成面向行业的公共能力。
- 完整文字稿：源材料对公共能力只给出拟建议定位，正式项目范围尚未确定。本稿却写成已经建成面向行业的公共能力，并把已完成建设作为上屏表述，属于把条件性建议升级为完成态结论。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S015
- 上屏文字：
  **公共能力**
  - 已完成建设。
- 证据：S015
- 边界：正式范围待确定。
- 视觉结构：定位图。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p09",
                "sequence": 9,
                "page_type": "content",
                "title": "总体定位",
                "argument_role": "positioning",
                "source_refs": ["S015"],
                "prerequisite_pages": ["p07"],
                "main_claim_status": "proposed",
            }
        )
        truth = source_truth(
            {
                "id": "S015",
                "type": "B",
                "status": "拟建议",
                "statement": "初步考虑将本项建设定位为公共能力。",
            }
        )

        codes = {issue.code for issue in audit_script_quality(script, outline, truth)}

        self.assertIn("SOURCE_STATE_UPGRADED", codes)

    def test_adjacent_pages_with_same_main_message_are_rejected(self) -> None:
        duplicate = """## 第14页：业务体系
- 页面类型：内容页
- 页面标题：业务体系
- 主判断：统一数据和模型支撑报告生产与审核发布。
- 完整文字稿：业务体系页强调预测对象、流程与成果出口必须共用统一数据和模型底座，使报告生产与审核发布建立在同一输入之上。本页回答的是业务对象如何组织，而不是单独展开产品闭环细节。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S017
- 上屏文字：
  **业务对象**
  - 覆盖供需研判与成果生产。
  **运行关系**
  - 数据、模型与报告相互衔接。
- 证据：S017
- 边界：拟建议。
- 视觉结构：业务关系图。

## 第15页：成果闭环
- 页面类型：内容页
- 页面标题：成果闭环
- 主判断：统一数据和模型支撑报告生产与审核发布。
- 完整文字稿：成果闭环页本应推进生产、审校、发布、归档和复盘的运行机制，但本稿主判断仍重复写成统一数据和模型支撑报告生产与审核发布，没有形成新的业务问题推进。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S020
- 上屏文字：
  **成果生产**
  - 覆盖报告生产与审核发布。
  **运行关系**
  - 数据、模型与报告相互衔接。
- 证据：S020
- 边界：拟建议。
- 视觉结构：成果关系图。
"""
        issues = audit_script_quality(
            parse_script_markdown(duplicate),
            strict_outline(
                {
                    "page_id": "p14",
                    "sequence": 14,
                    "page_type": "content",
                    "title": "业务体系",
                    "argument_role": "solution",
                    "source_refs": ["S017"],
                    "prerequisite_pages": [],
                },
                {
                    "page_id": "p15",
                    "sequence": 15,
                    "page_type": "content",
                    "title": "成果闭环",
                    "argument_role": "solution",
                    "source_refs": ["S020"],
                    "prerequisite_pages": ["p14"],
                },
            ),
            source_truth(
                {"id": "S017", "type": "R", "status": "拟建议", "statement": "业务体系。"},
                {"id": "S020", "type": "R", "status": "拟建议", "statement": "成果产品。"},
            ),
        )

        self.assertIn(
            "ADJACENT_MAIN_MESSAGE_DUPLICATE",
            {issue.code for issue in issues},
        )

    def test_short_bridge_does_not_trigger_full_text_duplicate(self) -> None:
        self.assertLess(
            text_similarity("承接前页的数据治理基础", "数据治理提供可信输入"),
            0.72,
        )

    def test_path_visual_requires_order_signal(self) -> None:
        script = parse_script_markdown(
            """## 第12页：研究任务
- 页面类型：内容页
- 页面标题：研究任务
- 主判断：四项任务形成研究证据。
- 完整文字稿：本阶段研究通过资源摸底、问题量化、首期设计和原型验证四项任务形成立项前证据。四项任务应串成完整路径：先摸清资源和责任，再量化现状与缺口，再设计首期业务与技术方案，最后用原型验证形成测算与风险依据。本页不提前决定投资规模或采购方式。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S014
- 上屏文字：
  **资源摸底**
  - 形成资源清单和责任清单。
  **问题量化**
  - 形成现状基线和问题清单。
  **首期设计**
  - 形成首期业务与技术方案。
  **原型验证**
  - 形成验证结果和测算依据。
- 证据：S014
- 边界：不决定投资。
- 视觉结构：四步任务路径图。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p12",
                    "sequence": 12,
                    "page_type": "content",
                    "title": "研究任务",
                    "argument_role": "decision",
                    "source_refs": ["S014"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {
                    "id": "S014",
                    "type": "U",
                    "status": "待确认",
                    "statement": "四项研究任务。",
                }
            ),
        )

        self.assertIn("PATH_ORDER_SIGNAL_MISSING", {issue.code for issue in issues})

    def test_declared_count_must_match_modules(self) -> None:
        text = SCRIPT.replace(
            "初步定位为面向行业的公共能力。",
            "形成五类能力。",
        )
        issues = audit_script_quality(
            parse_script_markdown(text),
            strict_outline(
                {
                    "page_id": "p08",
                    "sequence": 8,
                    "page_type": "chapter",
                    "title": "第二章：定位、目标与研究边界",
                },
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "solution",
                    "source_refs": ["S015", "S026", "S059"],
                    "prerequisite_pages": [],
                },
            ),
            source_truth(
                {"id": "S015", "type": "R", "status": "拟建议", "statement": "能力。"},
                {"id": "S026", "type": "B", "status": "研究边界", "statement": "边界。"},
                {"id": "S059", "type": "B", "status": "研究边界", "statement": "边界。"},
            ),
        )

        self.assertIn("DECLARED_COUNT_MISMATCH", {issue.code for issue in issues})

    def test_content_page_with_one_short_module_is_too_sparse(self) -> None:
        sparse = """## 第10页：能力框架
- 页面类型：内容页
- 页面标题：能力框架
- 主判断：形成能力。
- 完整文字稿：能力框架页需要说明业务、数据、模型、产品和运行机制如何共同支撑研判，而不是只留下一句形成能力。本稿文字稿虽给出方向，但上屏仅保留单一短模块，无法承载完整论证结构。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S017
- 上屏文字：
  **能力**
  - 提升研判。
- 证据：S017
- 边界：拟建议。
- 视觉结构：能力图。
"""
        outline = strict_outline(
            {
                "page_id": "p10",
                "sequence": 10,
                "page_type": "content",
                "title": "能力框架",
                "argument_role": "solution",
                "source_refs": ["S017"],
                "prerequisite_pages": [],
            }
        )
        outline["visible_judgment_mode"] = "required"
        issues = audit_script_quality(
            parse_script_markdown(sparse),
            outline,
            source_truth(
                {"id": "S017", "type": "R", "status": "拟建议", "statement": "能力。"}
            ),
        )

        codes = {issue.code for issue in issues}
        self.assertIn("CONTENT_PAGE_TOO_SPARSE", codes)

    def test_onscreen_layer_must_preserve_full_prose_semantics(self) -> None:
        script = parse_script_markdown(
            """## 第10页：数据断点
- 页面类型：内容页
- 页面标题：数据断点
- 主判断：数据接入与治理尚未贯通。
- 上屏结论：数据接入与治理尚未贯通
- 完整文字稿：供需预测依赖统一指标口径、稳定数据来源、版本留痕、授权边界和发布审核。当前数据分散在统计报表、业务系统、外部公开来源与合作单位，不同数据在统计范围、时间粒度、更新周期和历史修订方式上存在差异。高频负荷、气象、市场交易和新型主体数据仍需建立稳定接入渠道。数据不可控会削弱模型可信，进一步放大发布风险，因此数据治理是端到端研判能力的前置条件。
- 文字稿取舍说明：只讨论数据断点；模型细节和建设安排留后页。
- 证据映射：数据断点→S017
- 上屏文字：
  **组织保障**
  - 建立专项工作组并完善会议安排。
  **实施节奏**
  - 分阶段推进培训、宣传、考核和日常协调。
- 证据：S017
- 边界：不提前给出建设方案。
- 视觉结构：判断证据支撑。
"""
        )
        outline = strict_outline(
            {
                "page_id": "p10",
                "sequence": 10,
                "page_type": "content",
                "title": "数据断点",
                "argument_role": "diagnosis",
                "source_refs": ["S017"],
                "prerequisite_pages": [],
                "main_message": "数据接入与治理尚未贯通。",
                "onscreen_judgment": "数据接入与治理尚未贯通",
            }
        )
        outline["visible_judgment_mode"] = "required"
        issues = audit_script_quality(
            script,
            outline,
            source_truth(
                {
                    "id": "S017",
                    "type": "F",
                    "status": "现状",
                    "statement": "数据接入与治理尚未贯通。",
                }
            ),
        )

        self.assertIn(
            "ONSCREEN_SEMANTIC_COVERAGE_LOW",
            {issue.code for issue in issues},
        )

    def test_content_page_requires_full_prose_before_onscreen(self) -> None:
        missing = """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留专业职责边界。
- 证据：S015
- 边界：正式范围待后续确定。
- 视觉结构：公共能力定位与职责边界图。
"""
        issues = audit_script_quality(
            parse_script_markdown(missing),
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                    "main_claim_status": "proposed",
                }
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"}
            ),
        )
        self.assertIn("CONTENT_PROSE_MISSING", {issue.code for issue in issues})

    def test_full_prose_must_precede_onscreen_field(self) -> None:
        wrong_order = """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 文字稿取舍说明：本页只写本页业务问题主体；邻页议题不展开；建议与边界保持拟/待状态。
- 证据映射：支撑点1→S015
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留专业职责边界。
- 完整文字稿：在现状与能力断点已经建立后，本页将建设方向初步定位为面向行业的公共能力，同时保留专业系统边界。该定位用于明确研究方向，不等于正式项目范围已经确定；正式判断仍需由数据、模型、业务分析与专家会商共同形成，不能把拟建议写成已审定结论。
- 证据：S015
- 边界：正式范围待后续确定。
- 视觉结构：公共能力定位与职责边界图。
"""
        issues = audit_script_quality(
            parse_script_markdown(wrong_order),
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                    "main_claim_status": "proposed",
                }
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"}
            ),
        )
        self.assertIn("CONTENT_PROSE_AFTER_ONSCREEN", {issue.code for issue in issues})

    def test_analytical_meta_narration_in_prose_is_blocked(self) -> None:
        script = parse_script_markdown(
            """# 第9页脚本

## 第9页：总体定位

- 页面类型：内容页
- 页面标题：总体定位
- 主判断：拟初步定位为面向行业的公共能力。
- 完整文字稿：讨论能力建设，首先需要确认拟建对象的公共能力定位，而不是直接讨论完整方案。从现有材料看，本页只确认研究方向属性，本页不评价正式范围是否已定。
- 文字稿取舍说明：不展开五类能力与首期场景；定位保持拟建议。
- 证据映射：公共能力定位→S015
- 上屏文字：

  **行业公共能力**

  - 拟定位为面向行业的公共能力。
  - 该定位不等于正式项目范围已定。

  **职责边界**

  - 不替代专业运行系统。

- 证据：S015
- 边界：正式范围待后续确定。
- 视觉结构：公共能力定位与职责边界图。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                    "main_claim_status": "proposed",
                }
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"}
            ),
        )
        self.assertIn(
            "CONTENT_PROSE_ANALYTICAL_VOICE",
            {issue.code for issue in issues},
        )

    def test_issue_helper_accepts_warning_severity(self) -> None:
        page = ScriptPage(
            page_id="p01",
            sequence=1,
            heading="示例",
            page_type="content",
            title="示例",
            main_message="判断",
            full_prose="x" * 100,
            selection_notes="取舍说明足够长",
            evidence_map="点→S001",
            evidence_map_refs=("S001",),
            source_refs=("S001",),
            boundary_source_refs=(),
            boundary="",
            visual_structure="业务关系图。",
            onscreen_text="**模块A**\n- a\n**模块B**\n- b",
            module_titles=("模块A", "模块B"),
            speaker_notes="建设方向应与专业系统的职责分工同时明确，避免能力边界交叉。",
        )
        issue = _issue(
            "VISUAL_STRUCTURE_TOO_THIN",
            page,
            "thin",
            "expand",
            severity="warning",
        )
        self.assertEqual("warning", issue.severity)

    def test_visual_structure_style_only_is_error(self) -> None:
        prose = "建设方向定位为面向行业的公共能力，明确研究对象与服务边界。" * 4
        script = parse_script_markdown(
            f"""## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：定位为行业公共能力。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开邻页。
- 证据映射：定位→S015
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留职责边界。
- 证据：S015
- 边界：范围待定。
- 视觉结构：简洁现代科技感。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {
                    "id": "S015",
                    "type": "J",
                    "status": "拟建议",
                    "statement": "公共能力定位。",
                }
            ),
        )
        style_issues = [
            issue for issue in issues if issue.code == "VISUAL_STRUCTURE_STYLE_ONLY"
        ]
        self.assertTrue(style_issues)
        self.assertEqual("error", style_issues[0].severity)

    def test_visual_structure_too_thin_is_warning(self) -> None:
        prose = "建设方向定位为面向行业的公共能力，明确研究对象与服务边界。" * 4
        script = parse_script_markdown(
            f"""## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：定位为行业公共能力。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开邻页。
- 证据映射：定位→S015
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留职责边界。
- 证据：S015
- 边界：范围待定。
- 视觉结构：业务关系图。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {
                    "id": "S015",
                    "type": "J",
                    "status": "拟建议",
                    "statement": "公共能力定位。",
                }
            ),
        )
        thin_issues = [
            issue for issue in issues if issue.code == "VISUAL_STRUCTURE_TOO_THIN"
        ]
        self.assertTrue(thin_issues)
        self.assertEqual("warning", thin_issues[0].severity)

    def test_onscreen_anti_pattern_warns_on_card_wall_phrase(self) -> None:
        prose = "建设方向定位为面向行业的公共能力，明确研究对象与服务边界。" * 4
        script = parse_script_markdown(
            f"""## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：定位为行业公共能力。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开邻页。
- 证据映射：定位→S015
- 上屏文字：
  **行业公共能力**
  - 用六宫格展示能力项。
  **专业系统边界**
  - 保留职责边界。
- 证据：S015
- 边界：范围待定。
- 视觉结构：判断证据支撑——中央判断，两侧证据托举。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {
                    "id": "S015",
                    "type": "J",
                    "status": "拟建议",
                    "statement": "公共能力定位。",
                }
            ),
        )
        anti = [issue for issue in issues if issue.code == "ONSCREEN_ANTI_PATTERN"]
        self.assertTrue(anti)
        self.assertEqual("warning", anti[0].severity)

    def test_onscreen_relation_meta_labels_are_errors(self) -> None:
        prose = "统一底座使三类应用共享知识标准，同时保留各自权限与解释口径。" * 3
        script = parse_script_markdown(
            f"""## 第6页：平台定位
- 页面类型：内容页
- 页面标题：平台定位
- 主判断：平台以统一知识治理为底座连接三类应用。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开邻页。
- 证据映射：底座→S009
- 上屏文字：
  **01｜数据资产层**
  - 统一接入数据资产。
  **02｜三类应用层**
  - 连接三类业务。
  - 业务含义：统一底座使三类应用共享知识标准。
  - 纵向关系：数据资产 → 三类应用。
- 证据：S009
- 边界：不替代既有系统。
- 视觉结构：分层剖面——自下而上呈现支撑关系。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p06",
                    "page_type": "content",
                    "title": "平台定位",
                    "main_message": "平台以统一知识治理为底座连接三类应用。",
                    "source_refs": ["S009"],
                }
            ),
            source_truth(
                {
                    "id": "S009",
                    "type": "F",
                    "status": "已确认",
                    "statement": "平台范围包括知识资产治理与三类应用。",
                }
            ),
        )
        meta = [
            issue for issue in issues if issue.code == "ONSCREEN_RELATION_META_LABEL"
        ]
        self.assertTrue(meta)
        self.assertEqual("error", meta[0].severity)
        self.assertIn("业务含义", meta[0].evidence)
        self.assertIn("纵向关系", meta[0].evidence)

    def test_primitive_matrix_mismatch_warns(self) -> None:
        prose = "场景筛选需要按业务必要与数据可得综合权衡后分期安排。" * 4
        script = parse_script_markdown(
            f"""## 第19页：场景布局
- 页面类型：内容页
- 页面标题：场景布局
- 主判断：首期双场景是综合权衡后的阶段安排。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开技术方案。
- 证据映射：场景范围→S022
- 上屏文字：
  **首期取舍**
  - 两个场景共同验证能力。
  **后续准入**
  - 条件成熟后再纳入高频场景。
- 证据：S022
- 边界：排序需摸底后校核。
- 视觉结构：矩阵筛选——场景与准入条件对照。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p19",
                    "sequence": 19,
                    "page_type": "content",
                    "title": "场景布局",
                    "argument_role": "scope",
                    "source_refs": ["S022"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {
                    "id": "S022",
                    "type": "J",
                    "status": "拟建议",
                    "statement": "首期双场景。",
                }
            ),
        )
        mismatch = [
            issue
            for issue in issues
            if issue.code == "PRIMITIVE_ONSCREEN_MISMATCH"
        ]
        self.assertTrue(mismatch)
        self.assertEqual("warning", mismatch[0].severity)


class SpeakerNotesContractTests(unittest.TestCase):
    def test_extracts_bracket_speaker_notes(self) -> None:
        body = (
            "- 讲解提示：短提醒。\n\n"
            "【演讲者备注】\n\n"
            "建设方向与职责分工需要同步明确。\n"
        )
        self.assertIn("建设方向", extract_speaker_notes(body))

    def test_rejects_defensive_boundary_coaching(self) -> None:
        script = parse_script_markdown(
            SCRIPT.replace(
                "先说定位再说边界。",
                "反复区分方向和首期，避免听众把完整蓝图听成一期承诺。",
            )
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p08",
                    "sequence": 8,
                    "page_type": "chapter",
                    "title": "第二章：定位、目标与研究边界",
                },
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "page_job": "说明总体定位",
                    "business_question": "拟建什么能力",
                    "main_message": "定位为行业公共能力",
                    "source_refs": ["S015", "S026", "S059"],
                    "prerequisite_pages": [],
                },
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
                {"id": "S026", "type": "B", "status": "边界", "statement": "专业边界。"},
                {"id": "S059", "type": "B", "status": "边界", "statement": "正式范围待定。"},
            ),
        )

        self.assertIn(
            "NARRATION_BOUNDARY_COACHING",
            {issue.code for issue in issues},
        )

    def test_rejects_internal_boundary_repeated_in_ordinary_speaker_notes(self) -> None:
        script = parse_script_markdown(
            SCRIPT.replace(
                "建设定位是面向行业的公共能力，服务履职与行业共用；同时明确与专业系统的职责分工，不替代调度、出清和企业计划。正式范围仍需结合资源摸底和原型验证进一步确定，当前阶段不提前锁定实施参数。",
                "建设定位是面向行业的公共能力，服务履职与行业共用。正式范围待后续确定，当前阶段不提前锁定实施参数。相关能力建设由业务体系持续支撑。",
            )
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p08",
                    "sequence": 8,
                    "page_type": "chapter",
                    "title": "第二章：定位、目标与研究边界",
                },
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "能力定位",
                    "argument_role": "solution",
                    "page_job": "说明能力组成",
                    "business_question": "形成哪些业务能力",
                    "main_message": "形成行业公共预测能力",
                    "source_refs": ["S015", "S026", "S059"],
                    "prerequisite_pages": [],
                },
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
                {"id": "S026", "type": "B", "status": "边界", "statement": "专业边界。"},
                {"id": "S059", "type": "B", "status": "边界", "statement": "正式范围待定。"},
            ),
        )

        self.assertIn(
            "NARRATION_INTERNAL_BOUNDARY_LEAK",
            {issue.code for issue in issues},
        )

    def test_scope_page_may_state_substantive_scope_without_defensive_coaching(self) -> None:
        script = parse_script_markdown(
            SCRIPT.replace(
                "先说定位再说边界。",
                "先说明首期业务，再说明数据和模型安排。",
            ).replace(
                "建设定位是面向行业的公共能力，服务履职与行业共用；同时明确与专业系统的职责分工，不替代调度、出清和企业计划。正式范围仍需结合资源摸底和原型验证进一步确定，当前阶段不提前锁定实施参数。",
                "首期聚焦月度季度分析和年度报告自动化，数据采用现有统计与稳定来源，模型采用可解释基线和滚动回测，形成能够验证的业务闭环。",
            )
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p08",
                    "sequence": 8,
                    "page_type": "chapter",
                    "title": "第二章：定位、目标与研究边界",
                },
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "首期范围",
                    "argument_role": "scope",
                    "page_job": "明确首期范围",
                    "business_question": "首期聚焦哪些业务",
                    "main_message": "首期聚焦月季分析和年报自动化",
                    "source_refs": ["S015", "S026", "S059"],
                    "prerequisite_pages": [],
                },
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
                {"id": "S026", "type": "B", "status": "边界", "statement": "专业边界。"},
                {"id": "S059", "type": "B", "status": "边界", "statement": "正式范围待定。"},
            ),
        )

        narration_codes = {
            "NARRATION_BOUNDARY_COACHING",
            "NARRATION_INTERNAL_BOUNDARY_LEAK",
        }
        self.assertFalse(narration_codes & {issue.code for issue in issues})

    def test_rejects_slide_meta_speech(self) -> None:
        prose = "建设方向定位为面向行业的公共能力，明确研究对象与服务边界。" * 4
        script = parse_script_markdown(
            f"""## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开邻页细节。
- 证据映射：定位→S015
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留专业边界。
- 证据：S015
- 边界：正式范围待定。
- 视觉结构：双侧协同——左右对照。
- 讲解提示：短提醒。

【演讲者备注】

各位同事，这一页我们先说定位，下一页再谈范围。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"}
            ),
        )
        codes = {issue.code for issue in issues}
        self.assertIn("SPEAKER_NOTES_SLIDE_META", codes)
        self.assertIn("SPEAKER_NOTES_HOST_META", codes)

    def test_requires_speaker_notes_on_content_pages(self) -> None:
        prose = "建设方向定位为面向行业的公共能力，明确研究对象与服务边界。" * 4
        script = parse_script_markdown(
            f"""## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 完整文字稿：{prose}
- 文字稿取舍说明：不展开邻页细节。
- 证据映射：定位→S015
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留专业边界。
- 证据：S015
- 边界：正式范围待定。
- 视觉结构：双侧协同——左右对照。
"""
        )
        issues = audit_script_quality(
            script,
            strict_outline(
                {
                    "page_id": "p09",
                    "sequence": 9,
                    "page_type": "content",
                    "title": "总体定位",
                    "argument_role": "positioning",
                    "source_refs": ["S015"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"}
            ),
        )
        self.assertIn(
            "CONTENT_SPEAKER_NOTES_MISSING",
            {issue.code for issue in issues},
        )


def _judgment_page(**overrides: object) -> ScriptPage:
    base = dict(
        page_id="p15",
        sequence=15,
        heading="知识与数据底座",
        page_type="content",
        title="知识与数据底座",
        main_message="通用、专业和行业知识先归一为标准知识对象，再由分层数据服务支撑应用",
        full_prose="从业务关系看，三类知识来源先归一为统一知识对象。" * 4,
        selection_notes="必留上屏：三类来源；仅讲解：细节；仅追溯：S001",
        evidence_map="点→S001",
        evidence_map_refs=("S001",),
        source_refs=("S001",),
        boundary_source_refs=(),
        boundary="",
        visual_structure="",
        onscreen_text="**01｜三类知识来源**\n- a\n**02｜统一知识对象**\n- b",
        module_titles=("01｜三类知识来源", "02｜统一知识对象"),
        speaker_notes="围绕判断展开。",
        onscreen_judgment="通用、专业和行业知识先归一为标准知识对象，再由分层数据服务支撑应用",
    )
    base.update(overrides)
    return ScriptPage(**base)  # type: ignore[arg-type]


class VisualStructureJudgmentAccuracyTests(unittest.TestCase):
    def test_flags_crosscut_module_peer_staged_on_path(self) -> None:
        page = _judgment_page(
            visual_structure=(
                "贯穿主链——三类知识来源 → 统一知识对象 → 分层数据服务 → 质量与生命周期；"
                "一级模块与上屏文字一致。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertIn("VISUAL_STRUCTURE_CROSSCUT_AS_PEER", codes)

    def test_allows_crosscut_as_second_clause_not_on_arrow_chain(self) -> None:
        page = _judgment_page(
            visual_structure=(
                "贯穿主链——三类知识来源 → 统一知识对象 → 分层数据服务；"
                "质量与生命周期贯穿主链。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertNotIn("VISUAL_STRUCTURE_CROSSCUT_AS_PEER", codes)

    def test_flags_horizontal_governance_as_stacked_layer(self) -> None:
        page = _judgment_page(
            main_message="平台以统一知识治理为底座，并由权限审核贯穿全链",
            full_prose="从业务关系看，数据资产经过知识加工形成智能能力，横向治理贯穿每一层。" * 2,
            visual_structure=(
                "分层剖面——自下而上依次呈现数据资产层、知识加工层、智能能力层、"
                "三类应用层、横向治理层；一级模块与上屏文字一致。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertIn("VISUAL_STRUCTURE_CROSSCUT_AS_PEER", codes)

    def test_flags_gateway_center_mismatch(self) -> None:
        page = _judgment_page(
            main_message="统一网关连接身份组织、知识题库、学习教学和分析报告接口",
            onscreen_judgment="统一网关连接身份组织、知识题库、学习教学和分析报告接口",
            visual_structure=(
                "双侧协同——以身份组织接口为视觉中心，其余模块按支撑关系连接；"
                "一级模块与上屏文字一致。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertIn("VISUAL_CENTER_JUDGMENT_MISMATCH", codes)

    def test_flags_depth_defense_with_boundary_primitive(self) -> None:
        page = _judgment_page(
            main_message="安全体系以五层纵深防护构成内容到审计的防护链",
            onscreen_judgment="安全体系以五层纵深防护构成内容到审计的防护链",
            visual_structure=(
                "受控边界——由外向内设置内容输出控制、风险行为识别、身份与网络隔离、"
                "数据保护、审计与应急，中心为受控业务输出；一级模块与上屏文字一致。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertIn("VISUAL_STRUCTURE_PRIMITIVE_MISMATCH", codes)

    def test_flags_mechanism_peer_lanes(self) -> None:
        page = _judgment_page(
            main_message="学生实时链路与教师异步任务采用隔离资源和差异化降级策略",
            visual_structure=(
                "主体泳道——横向并列学生实时链路、教师异步队列、资源隔离、弹性降级，"
                "底部设置统一支撑关系；一级模块与上屏文字一致。"
            ),
        )
        codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
        self.assertIn("VISUAL_STRUCTURE_MECHANISM_AS_LANE", codes)


if __name__ == "__main__":
    unittest.main()
