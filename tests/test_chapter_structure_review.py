from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from cyberppt.commands.chapter_structure_review import (
    prepare_chapter_review_input,
    run_chapter_review_audit,
)
from cyberppt.stage01_controls import write_confirmation_request


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class ChapterStructureReviewTests(unittest.TestCase):
    def make_project(self, root: Path) -> Path:
        project = root / "project"
        outline = project / "workbench/stages/01-analysis/outline.json"
        write_json(outline, {
            "document_semantics": {"document_role": "成果汇报"},
            "narrative_thesis": "建设能力",
            "pages": [
                {"page_id": "p01", "page_type": "chapter", "chapter_id": "c1", "title": "第一章"},
                {"page_id": "p02", "page_type": "content", "chapter_id": "c1", "title": "现状", "page_mission": "说明现状", "core_message": "现状存在短板", "content_units": [], "content_relations": [], "source_refs": ["S1"], "page_necessity": "独立说明现状"},
            ],
        })
        return project

    def complete_review(self, project: Path) -> None:
        review = project / "review/c01-outline-structure-review.md"
        review.write_text("# 审阅\n\n## 总判\n通过\n\n## 章内推进链\n清晰\n\n## 跨页优化\n无\n\n## 建议落地顺序\n无\n\n## 消费状态\n- [x] 已消费\n", encoding="utf-8")
        outline = project / "workbench/stages/01-analysis/outline.json"
        write_json(project / "review/chapter-review-manifest.json", {
            "schema": "cyberppt.chapter_review_manifest.v1",
            "level": "outline",
            "input_sha256": hashlib.sha256(outline.read_bytes()).hexdigest(),
            "reviews": [{"path": "review/c01-outline-structure-review.md", "chapter_ids": ["c1"], "page_ids": ["p02"], "status": "passed", "high_priority_open": []}],
        })

    def test_prepare_contains_semantics_and_all_reviewable_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(Path(tmp))
            path = prepare_chapter_review_input(project)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("成果汇报", payload["document_semantics"]["document_role"])
            self.assertEqual("p02", payload["chapters"][0]["pages"][0]["page_id"])

    def test_audit_passes_and_stale_outline_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(Path(tmp))
            prepare_chapter_review_input(project)
            self.complete_review(project)
            code, report = run_chapter_review_audit(project)
            self.assertEqual(0, code)
            self.assertEqual("passed", report["status"])
            outline = project / "workbench/stages/01-analysis/outline.json"
            outline.write_text(outline.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            code, report = run_chapter_review_audit(project)
            self.assertEqual(4, code)
            self.assertTrue(any(issue["code"] == "REVIEW_INPUT_STALE" for issue in report["issues"]))

    def test_missing_heading_and_page_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(Path(tmp))
            prepare_chapter_review_input(project)
            self.complete_review(project)
            review = project / "review/c01-outline-structure-review.md"
            review.write_text("## 总判\n不完整\n", encoding="utf-8")
            manifest = json.loads((project / "review/chapter-review-manifest.json").read_text(encoding="utf-8"))
            manifest["reviews"][0]["page_ids"] = []
            write_json(project / "review/chapter-review-manifest.json", manifest)
            code, report = run_chapter_review_audit(project)
            self.assertEqual(4, code)
            codes = {issue["code"] for issue in report["issues"]}
            self.assertIn("REVIEW_SECTION_MISSING", codes)
            self.assertIn("PAGE_COVERAGE_INCOMPLETE", codes)

    def test_required_review_does_not_block_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(Path(tmp))
            (project / "manifest.yml").write_text("chapter_review:\n  outline: required\n", encoding="utf-8")
            request = write_confirmation_request(project, "outline")
            self.assertTrue(request.is_file())
            prepare_chapter_review_input(project)
            self.complete_review(project)
            run_chapter_review_audit(project)
            request = write_confirmation_request(project, "outline")
            self.assertTrue(request.is_file())
            text = request.read_text(encoding="utf-8")
            self.assertIn("**总提纲**", text)
            self.assertIn("### 分章审阅稿", text)
            self.assertIn("第1章：", text)
            self.assertIn("c01-outline-structure-review.md", text)

    def test_combined_multi_chapter_review_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(Path(tmp))
            outline = project / "workbench/stages/01-analysis/outline.json"
            payload = json.loads(outline.read_text(encoding="utf-8"))
            payload["pages"].extend([
                {"page_id": "p03", "page_type": "chapter", "chapter_id": "c2", "title": "第二章"},
                {"page_id": "p04", "page_type": "content", "chapter_id": "c2", "title": "目标", "page_mission": "说明目标", "core_message": "形成能力", "content_units": [], "content_relations": [], "source_refs": ["S2"], "page_necessity": "独立说明目标"},
            ])
            write_json(outline, payload)
            prepare_chapter_review_input(project)
            review = project / "review/combined.md"
            review.write_text("## 总判\n通过\n## 章内推进链\n清晰\n## 跨页优化\n无\n## 建议落地顺序\n无\n## 消费状态\n已消费\n", encoding="utf-8")
            write_json(project / "review/chapter-review-manifest.json", {
                "schema": "cyberppt.chapter_review_manifest.v1",
                "level": "outline",
                "input_sha256": hashlib.sha256(outline.read_bytes()).hexdigest(),
                "reviews": [{"path": "review/combined.md", "chapter_ids": ["c1", "c2"], "page_ids": ["p02", "p04"], "status": "passed", "high_priority_open": []}],
            })
            code, report = run_chapter_review_audit(project)
            self.assertEqual(4, code)
            self.assertTrue(any(issue["code"] == "CHAPTER_REVIEW_NOT_INDIVIDUAL" for issue in report["issues"]))


if __name__ == "__main__":
    unittest.main()
