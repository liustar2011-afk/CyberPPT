from __future__ import annotations

import json
from pathlib import Path
import unittest

from cyberppt.script_quality_contract import (
    audit_script_quality,
    parse_script_markdown,
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
- 上屏文字：

  **行业公共能力**

  - 服务行业研判。

  **专业系统边界**

  - 保留专业职责边界。

- 证据：S015、S026、S059
- 边界：正式范围待后续确定。
- 视觉结构：公共能力定位与职责边界图。
"""


def strict_outline(*pages: dict[str, object]) -> dict[str, object]:
    return {"argument_contract_mode": "strict", "pages": list(pages)}


def source_truth(*records: dict[str, object]) -> dict[str, object]:
    return {"argument_contract_mode": "strict", "records": list(records)}


class ScriptMarkdownParserTests(unittest.TestCase):
    def test_extracts_pages_and_fields(self) -> None:
        document = parse_script_markdown(SCRIPT)

        self.assertEqual(["p08", "p09"], [page.page_id for page in document.pages])
        self.assertEqual("chapter", document.pages[0].page_type)
        self.assertEqual("总体定位", document.pages[1].title)
        self.assertEqual(("S015", "S026", "S059"), document.pages[1].source_refs)
        self.assertEqual(("行业公共能力", "专业系统边界"), document.pages[1].module_titles)

    def test_rejects_document_without_pages(self) -> None:
        with self.assertRaisesRegex(ValueError, "no page headings"):
            parse_script_markdown("# empty")

    def test_onscreen_block_stops_at_next_backend_field(self) -> None:
        page = parse_script_markdown(SCRIPT).pages[1]

        self.assertNotIn("- 证据：", page.onscreen_text)
        self.assertNotIn("S015", page.onscreen_text)


class ScriptContractAuditTests(unittest.TestCase):
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

        self.assertEqual(
            [],
            audit_script_quality(parse_script_markdown(SCRIPT), outline, truth),
        )

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

    def test_proposed_source_cannot_be_upgraded_to_completed(self) -> None:
        script = parse_script_markdown(
            """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：已经建成面向行业的公共能力。
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
- 上屏文字：
  **能力**
  - 提升研判。
- 证据：S017
- 边界：拟建议。
- 视觉结构：能力图。
"""
        issues = audit_script_quality(
            parse_script_markdown(sparse),
            strict_outline(
                {
                    "page_id": "p10",
                    "sequence": 10,
                    "page_type": "content",
                    "title": "能力框架",
                    "argument_role": "solution",
                    "source_refs": ["S017"],
                    "prerequisite_pages": [],
                }
            ),
            source_truth(
                {"id": "S017", "type": "R", "status": "拟建议", "statement": "能力。"}
            ),
        )

        self.assertIn("CONTENT_PAGE_TOO_SPARSE", {issue.code for issue in issues})


if __name__ == "__main__":
    unittest.main()
