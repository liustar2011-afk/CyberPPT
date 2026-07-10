from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.speaker_notes import build_manifest, parse_llm_notes


class SpeakerNotesTests(unittest.TestCase):
    def test_builds_speech_like_notes_from_business_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            business = root / "business_script.md"
            business.write_text(
                "\n".join(
                    [
                        "## 第4页：形势变化和工作要求",
                        "### 页面内容脚本",
                        "- 全国全社会用电量103682亿千瓦时，同比增长5.0%",
                        "- 市场交易电量66394亿千瓦时，占比64.0%",
                        "- 可再生能源装机23.4亿千瓦，占比约60%",
                        "### 非上屏：证据链",
                        "- E01，E02，E03",
                        "### 非上屏：完整性校核",
                        "- 本页不新增预算、人力等既定事实。",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = build_manifest(business_script=business, pages_raw="4", output_dir=root / "notes")
            prompt_exists = (root / "notes" / "speaker_notes_llm_prompt.md").exists()

        note = manifest["notes"][0]["notes_text"]
        self.assertIn("这一页汇报形势变化和工作要求", note)
        self.assertIn("全国全社会用电量103682亿千瓦时", note)
        self.assertNotIn("证据链", note)
        self.assertNotIn("E01", note)
        self.assertNotIn("完整性校核", note)
        self.assertNotIn("汇报要点：", note)
        self.assertTrue(prompt_exists)

    def test_filters_provenance_language_from_reviewed_llm_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            business = root / "business_script.md"
            business.write_text("## 第4页：形势变化\n### 页面内容脚本\n- 用电量增长。\n", encoding="utf-8")
            llm = root / "llm.json"
            llm.write_text(
                json.dumps(
                    {
                        "notes": [
                            {
                                "page_number": 4,
                                "notes_text": "这一页说明用电量增长。相关判断有业务稿证据链支撑，重点对应E01、E02。",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            manifest = build_manifest(business_script=business, pages_raw="4", output_dir=root / "notes", llm_output=llm)

        note = manifest["notes"][0]["notes_text"]
        self.assertEqual("这一页说明用电量增长。", note)

    def test_accepts_reviewed_llm_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            business = root / "business_script.md"
            business.write_text("## 第1页：封面\n- 项目汇报\n- 单位\n- 2026 年 7 月\n", encoding="utf-8")
            llm = root / "llm.json"
            llm.write_text(
                json.dumps({"notes": [{"page_number": 1, "notes_text": "各位领导，下面汇报项目情况。"}]}, ensure_ascii=False),
                encoding="utf-8",
            )

            manifest = build_manifest(business_script=business, pages_raw="1", output_dir=root / "notes", llm_output=llm)

        self.assertEqual("llm_optimized", manifest["notes"][0]["source"])
        self.assertEqual("各位领导，下面汇报项目情况。", manifest["notes"][0]["notes_text"])

    def test_parses_spaced_page_heading_from_page_content_design(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            business = root / "page_content.md"
            business.write_text("## 第 4 页 形势变化和工作要求\n### 上屏文字\n- 供需研判对象扩展\n", encoding="utf-8")

            manifest = build_manifest(business_script=business, pages_raw="4", output_dir=root / "notes")

        self.assertEqual([4], manifest["pages"])
        self.assertIn("供需研判对象扩展", manifest["notes"][0]["notes_text"])

    def test_section_break_notes_do_not_add_filler(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            business = root / "business_script.md"
            business.write_text(
                "## 第3页：第一章 建设背景与基础\n### 上屏文字\n- 第一章\n- 建设背景与基础\n",
                encoding="utf-8",
            )

            manifest = build_manifest(business_script=business, pages_raw="3", output_dir=root / "notes")

        self.assertEqual("section", manifest["notes"][0]["page_role"])
        self.assertEqual("", manifest["notes"][0]["notes_text"])

    def test_filters_section_filler_from_reviewed_llm_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            business = root / "business_script.md"
            business.write_text("## 第3页：第一章 建设背景与基础\n### 上屏文字\n- 第一章\n", encoding="utf-8")
            llm = root / "llm.json"
            llm.write_text(
                json.dumps(
                    {
                        "notes": [
                            {
                                "page_number": 3,
                                "notes_text": "下面进入建设背景与基础部分。围绕本章内容开展汇报。",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            manifest = build_manifest(business_script=business, pages_raw="3", output_dir=root / "notes", llm_output=llm)

        self.assertEqual("", manifest["notes"][0]["notes_text"])

    def test_filters_page_design_meta_language_from_reviewed_llm_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            business = root / "business_script.md"
            business.write_text("## 第4页：形势变化\n### 页面内容脚本\n- 用电量增长。\n", encoding="utf-8")
            llm = root / "llm.json"
            llm.write_text(
                json.dumps(
                    {
                        "notes": [
                            {
                                "page_number": 4,
                                "notes_text": "本页围绕形势变化展开。各位领导，当前用电量保持增长。",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            manifest = build_manifest(business_script=business, pages_raw="4", output_dir=root / "notes", llm_output=llm)

        self.assertEqual("各位领导，当前用电量保持增长。", manifest["notes"][0]["notes_text"])

    def test_parse_llm_notes_accepts_fenced_json(self) -> None:
        notes = parse_llm_notes('```json\n{"notes":[{"page_number":2,"notes_text":"进入目录。"}]}\n```')

        self.assertEqual({2: "进入目录。"}, notes)


if __name__ == "__main__":
    unittest.main()
