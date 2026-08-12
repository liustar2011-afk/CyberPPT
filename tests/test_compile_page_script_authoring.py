from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.compile_page_script_authoring import (
    compile_page_script_authoring,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CompilePageScriptAuthoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name) / "demo"
        self.stage = self.project / "workbench/stages/01-analysis"
        self.scripts = self.project / "workbench/scripts"
        self.stage.mkdir(parents=True)
        self.scripts.mkdir(parents=True)
        self.outline_path = self.stage / "outline.json"
        self.outline = {
            "pages": [
                {"page_id": "p01", "page_type": "cover", "title": "封面"},
                {
                    "page_id": "p02",
                    "page_type": "chapter",
                    "chapter_id": "CH01",
                    "title": "第一章",
                },
                {
                    "page_id": "p03",
                    "page_type": "content",
                    "chapter_id": "CH01",
                    "title": "内容页",
                    "subtitle": "模板层副标题",
                    "core_message": "事实支持判断",
                    "source_refs": ["ST001"],
                    "detail_refs": [],
                    "visual_intent_type": "judgment_evidence",
                    "page_mission": "回答问题",
                    "audience_question": "为什么？",
                    "business_question": None,
                    "must_not_include": [],
                    "split_risk": "low",
                    "split_risk_reason": "单一命题",
                    "core_message_derivation": {},
                    "content_relations": [
                        {
                            "subject": "事实",
                            "relation": "supports",
                            "objects": ["判断"],
                            "source_refs": ["ST001"],
                        }
                    ],
                    "onscreen_conclusion": None,
                    "new_value_vs_previous": "新增判断",
                    "reserved_for_later": [],
                    "visual_proof": None,
                    "content_units": [
                        {
                            "unit_id": "CU-p03-01",
                            "statement": "事实支持判断",
                            "source_refs": ["ST001"],
                            "role": "primary",
                        }
                    ],
                    "boundary_refs": [],
                },
                {"page_id": "p04", "page_type": "ending", "title": "结束"},
            ]
        }
        self.outline_path.write_text(
            json.dumps(self.outline, ensure_ascii=False), encoding="utf-8"
        )
        self.authoring_path = self.scripts / "page-script-authoring.json"
        self.authoring = {
            "schema": "cyberppt.page_script_authoring.v1",
            "project": "demo",
            "outline_sha256": _sha256(self.outline_path),
            "pages": {
                "p03": {
                    "subtitle": "作者确认的精简副标题",
                    "prose": "事实材料形成完整说明，并支持本页判断。",
                    "selection": [
                        "必留上屏：事实与判断。",
                        "仅讲解：解释细节。",
                        "仅追溯：ST001。",
                    ],
                    "onscreen": "事实：原文事实。\n判断：事实支持判断。",
                    "visual": "核心判断：事实支持判断。主要关系与方向：事实支持判断。",
                    "notes": "先说明事实，再得出判断。",
                    "consumes": ["CU-p03-01"],
                }
            },
        }
        self.authoring_path.write_text(
            json.dumps(self.authoring, ensure_ascii=False), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_compiles_chapter_drafts_with_receipt(self) -> None:
        output = self.scripts / "drafts/run-01"
        report = compile_page_script_authoring(self.project, output_dir=output)

        self.assertEqual(4, report["page_count"])
        self.assertEqual(1, report["content_page_count"])
        chapter = (output / "ch01.md").read_text(encoding="utf-8")
        self.assertIn("## 第2页：第一章", chapter)
        self.assertIn("## 第3页：内容页", chapter)
        self.assertIn("- 副标题：作者确认的精简副标题", chapter)
        onscreen = chapter.split("### 上屏文字（严格锁定）", 1)[1].split(
            "### 逻辑骨架", 1
        )[0]
        self.assertNotIn("作者确认的精简副标题", onscreen)
        self.assertIn("### 完整文字稿", chapter)
        self.assertIn('"consumed_content_unit_ids":["CU-p03-01"]', chapter)
        self.assertIn("事实：原文事实。\n    判断：事实支持判断", chapter)
        self.assertNotIn("左侧", chapter)

    def test_rejects_stale_outline_binding(self) -> None:
        self.authoring["outline_sha256"] = "0" * 64
        self.authoring_path.write_text(
            json.dumps(self.authoring, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "stale"):
            compile_page_script_authoring(
                self.project, output_dir=self.scripts / "drafts/run-02"
            )

    def test_onscreen_detail_items_have_no_terminal_punctuation(self) -> None:
        self.authoring["pages"]["p03"]["onscreen"] = (
            "现状判断\n\n明细项\n- 稳定供给仍有缺口。\n- 服务运营需要统一支撑！"
        )
        self.authoring_path.write_text(
            json.dumps(self.authoring, ensure_ascii=False), encoding="utf-8"
        )
        output = self.scripts / "drafts/run-punctuation"
        compile_page_script_authoring(self.project, output_dir=output)
        chapter = (output / "ch01.md").read_text(encoding="utf-8")
        onscreen = chapter.split("### 上屏文字（严格锁定）", 1)[1].split(
            "### 逻辑骨架", 1
        )[0]
        self.assertIn("- 稳定供给仍有缺口", onscreen)
        self.assertIn("- 服务运营需要统一支撑", onscreen)
        self.assertNotIn("缺口。", onscreen)
        self.assertNotIn("支撑！", onscreen)

    def test_rejects_consumption_mismatch(self) -> None:
        self.authoring["pages"]["p03"]["consumes"] = []
        self.authoring_path.write_text(
            json.dumps(self.authoring, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "consumes mismatch"):
            compile_page_script_authoring(
                self.project, output_dir=self.scripts / "drafts/run-03"
            )


if __name__ == "__main__":
    unittest.main()
