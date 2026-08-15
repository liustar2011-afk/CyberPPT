from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from cyberppt.commands.preview_page_anchors import preview_page_anchors


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _build_project(root: Path) -> Path:
    project = root / "project"
    outline_path = project / "workbench" / "stages" / "01-analysis" / "outline.json"
    _write_json(
        outline_path,
        {
            "schema": "cyberppt.outline.v1",
            "material_type": "solution",
            "audience": "project_team",
            "architecture_mode": "solution",
            "architecture_reason": "formal solution workflow",
            "source_section_weights": {},
            "argument_contract_mode": "strict",
            "pages": [
                {
                    "page_id": "p04",
                    "sequence": 4,
                    "page_type": "content",
                    "title": "一、建设背景",
                    "argument_role": "foundation",
                    "expression_model_selection": None,
                    "content_units": [
                        {
                            "unit_id": "p04-U01",
                            "role": "primary",
                            "onscreen_required": True,
                            "source_refs": ["ST0042", "ST0043"],
                            "coverage_anchors": ["电力行业是国民经济基础性、战略性行业"],
                            "onscreen_anchors": [
                                "电力行业是国民经济基础性、战略性行业",
                                "这是一个刻意超过三十个字符长度上限的极长锚点示例文本用于测试内容",
                            ],
                        },
                    ],
                },
            ],
            "retry": {"attempt": 1, "max_attempts": 3, "strategy": ""},
        },
    )
    return project


class PreviewPageAnchorsCommandTests(unittest.TestCase):
    def test_reports_anchor_lengths_and_source_refs_for_the_requested_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = _build_project(Path(temp_dir))

            report = preview_page_anchors(project, "p04")

            self.assertEqual("p04", report["page_id"])
            self.assertEqual("foundation", report["argument_role"])
            units = report["content_units"]
            self.assertEqual(1, len(units))
            self.assertEqual(["ST0042", "ST0043"], units[0]["source_refs"])
            anchors = units[0]["onscreen_anchors"]
            self.assertEqual(2, len(anchors))
            self.assertFalse(anchors[0]["over_detail_phrase_limit"])
            self.assertTrue(anchors[1]["over_detail_phrase_limit"])

    def test_unknown_page_id_reports_the_known_page_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = _build_project(Path(temp_dir))

            with self.assertRaises(ValueError) as ctx:
                preview_page_anchors(project, "p999")

            self.assertIn("p04", str(ctx.exception))

    def test_missing_outline_raises_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir(parents=True)

            with self.assertRaises(FileNotFoundError):
                preview_page_anchors(project, "p04")


if __name__ == "__main__":
    unittest.main()
