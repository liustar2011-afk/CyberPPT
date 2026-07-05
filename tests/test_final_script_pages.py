from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.commands.init_project import init_project


class FinalScriptPagesTests(unittest.TestCase):
    def test_compiles_pages_7_8_from_final_script_with_traceable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text(
                """# 终稿脚本

## 第7页：态势感知能力
本页结论标题为“态势感知能力要从工具堆叠转向风险闭环”
组件A（左侧主图）——三层能力链：
数据接入、模型研判、处置反馈

## 第8页：运营保障机制
本页结论标题为“运营保障机制需要责任、流程和审计同时落地”
组件A（中部流程）——责任闭环：
授权、执行、复盘、追踪
""",
                encoding="utf-8",
            )

            summary = run_final_script_pages(project=project, script=script, pages_raw="7-8")

            manifest = json.loads(Path(summary["artifacts"]["page_image_pairs"]).read_text(encoding="utf-8"))
            lock = json.loads(Path(summary["artifacts"]["template_text_lock"]).read_text(encoding="utf-8"))
            ledger = json.loads((project / "workbench/artifact-ledger.json").read_text(encoding="utf-8"))

            self.assertEqual([7, 8], summary["pages"])
            self.assertEqual([7, 8], [pair["page_number"] for pair in manifest["pairs"]])
            self.assertEqual("态势感知能力要从工具堆叠转向风险闭环", lock["records"][0]["title"])
            self.assertEqual("运营保障机制需要责任、流程和审计同时落地", lock["records"][1]["title"])
            self.assertTrue(Path(summary["artifacts"]["compiled_deliverable_prompt"]).exists())
            self.assertTrue(Path(summary["artifacts"]["page_image_pairs"]).exists())
            self.assertTrue(Path(summary["artifacts"]["template_text_lock"]).exists())
            self.assertIn("--pages 7-8", summary["resume_command"])
            ledger_paths = {item["path"] for item in ledger["artifacts"]}
            self.assertIn(summary["artifacts"]["page_image_pairs"], ledger_paths)
            self.assertIn(summary["artifacts"]["template_text_lock"], ledger_paths)


if __name__ == "__main__":
    unittest.main()
