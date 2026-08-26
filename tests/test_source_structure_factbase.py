from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "source-structure-factbase"
if str(SKILL) not in sys.path:
    sys.path.insert(0, str(SKILL))

from source_structure_factbase.factbase import build_fact_base
from source_structure_factbase.parser import parse_document


class SourceStructureFactBaseTests(unittest.TestCase):
    def test_empty_markdown_header_records_p10_shape_without_promoting_it(self) -> None:
        structure = parse_document(
            "|  |  |  |  |\n"
            "| --- | --- | --- | --- |\n"
            "| 课程/产品 | 核心训练内容 | 建议价格 | 首期优先级 |\n"
            "| 新能源电力市场交易与AI决策实训 | 信息研判→预测输入 | 15—20万元/企业班 | A |\n",
            "p10.md",
        )

        table = structure["blocks"][0]
        self.assertEqual("empty", table["header_status"])
        self.assertEqual(
            {
                "status": "unconfirmed",
                "row_index": 1,
                "line_start": 3,
                "line_end": 3,
                "cells": ["课程/产品", "核心训练内容", "建议价格", "首期优先级"],
                "reason": "first_body_row_after_empty_markdown_header",
            },
            table["candidate_header"],
        )
        self.assertEqual("课程/产品", table["rows"][0][0])

        payload = build_fact_base(structure)
        candidate = next(
            entry for entry in payload["entries"]
            if entry["fact_type"] == "table_record"
        )
        price = next(
            entry for entry in payload["entries"]
            if entry["fact_type"] == "table_cell_statement"
            and entry["table_cell"]["cell_index"] == 3
            and entry["table_cell"]["row_index"] == 2
        )
        self.assertEqual("candidate_header", candidate["table"]["row_role"])
        self.assertEqual(3, candidate["source_ref"]["line_start"])
        self.assertEqual("", price["table_cell"]["header"])
        self.assertEqual(
            "新能源电力市场交易与AI决策实训：15—20万元/企业班",
            price["text"],
        )

    def test_empty_header_first_data_row_stays_data_bearing_candidate(self) -> None:
        structure = parse_document(
            "|  |  |\n"
            "| --- | --- |\n"
            "| 课程A | 交易申报实训 |\n"
            "| 课程B | 功率预测实训 |\n",
            "data-table.md",
        )
        payload = build_fact_base(structure)

        self.assertEqual(["", ""], structure["blocks"][0]["headers"])
        self.assertEqual(
            ["课程A", "交易申报实训"],
            structure["blocks"][0]["rows"][0],
        )
        first_row = next(
            entry for entry in payload["entries"]
            if entry["fact_type"] == "table_record"
        )
        first_detail = next(
            entry for entry in payload["entries"]
            if entry["fact_type"] == "table_cell_statement"
            and entry["table_cell"]["row_index"] == 1
            and entry["table_cell"]["cell_index"] == 2
        )
        self.assertEqual("candidate_header", first_row["table"]["row_role"])
        self.assertEqual("课程A：交易申报实训", first_detail["text"])
        self.assertEqual("", first_detail["table_cell"]["header"])

    def test_table_rows_keep_trace_parent_and_emit_atomic_cell_children(self) -> None:
        payload = build_fact_base({
            "blocks": [{
                "block_id": "block-0001",
                "type": "table",
                "line_start": 10,
                "line_end": 13,
                "heading_path": ["市场测算"],
                "headers": ["市场", "长期空间", "触发条件"],
                "rows": [["企业培训", "0.5—1.7亿元/年", "完成付费交付；再研究投入"]],
                "raw_rows": ["| 企业培训 | 0.5—1.7亿元/年 | 完成付费交付；再研究投入 |"],
            }],
        })

        entries = payload["entries"]
        parent = entries[0]
        children = entries[1:]
        self.assertEqual("fact-0001", parent["fact_id"])
        self.assertEqual("table_record", parent["fact_type"])
        self.assertEqual(
            [
                "fact-0001-c01-s01",
                "fact-0001-c02-s01",
                "fact-0001-c03-s01",
                "fact-0001-c03-s02",
            ],
            [entry["fact_id"] for entry in children],
        )
        self.assertEqual(
            "企业培训｜长期空间：0.5—1.7亿元/年",
            children[1]["text"],
        )
        self.assertTrue(all(entry["parent_fact_id"] == "fact-0001" for entry in children))
        self.assertTrue(all("|" not in entry["text"] for entry in children))

    def test_child_entries_do_not_shift_later_parent_ids(self) -> None:
        payload = build_fact_base({
            "blocks": [
                {
                    "block_id": "block-0001", "type": "table", "line_start": 1,
                    "line_end": 3, "heading_path": [], "headers": ["项目", "值"],
                    "rows": [["甲", "1"]], "raw_rows": ["| 甲 | 1 |"],
                },
                {
                    "block_id": "block-0002", "type": "paragraph", "line_start": 4,
                    "line_end": 4, "heading_path": [], "text": "后续事实。",
                },
            ],
        })

        statement = next(entry for entry in payload["entries"] if entry["fact_type"] == "statement")
        self.assertEqual("fact-0002", statement["fact_id"])


if __name__ == "__main__":
    unittest.main()
