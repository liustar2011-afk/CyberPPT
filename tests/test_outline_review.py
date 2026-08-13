from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.outline_review import (
    render_outline_audit_markdown,
    render_outline_audit_report,
    render_outline_review,
    render_outline_review_markdown,
)


class OutlineReviewTests(unittest.TestCase):
    def test_markdown_carries_page_judgment_evidence_and_directory_exception(self) -> None:
        markdown = render_outline_review_markdown(
            {
                "communication_goal": "形成合作共识",
                "narrative_thesis": "先验证再运营",
                "pages": [
                    {"page_type": "chapter", "chapter_id": "C1", "title": "合作推进"},
                    {
                        "page_type": "content", "page_id": "p04", "chapter_id": "C1", "title": "事项梳理",
                        "audience_question": "先确认什么？", "page_mission": "形成筛选口径。",
                        "core_message": "先核验资源、客户与权利条件。", "non_substitutable_value": "避免无条件启动。",
                        "source_refs": ["ST0001", "ST0002"],
                        "evidence_roles": [{"role": "claim", "source_refs": ["ST0001", "ST0002"]}],
                        "argument_chain": [{"statement": "资源、客户与权利条件需要同步核验。", "source_refs": ["ST0001"]}],
                        "excluded_from_onscreen": ["不展示登记字段"], "reserved_for_later": "后页进入试点。",
                        "source_heading_preserved": True, "source_heading_preservation_rationale": "原文单列筛选动作。",
                    },
                ],
            },
            {"status": "passed", "mode": "lightweight", "argument_contract_mode": "strict", "issues": []},
        )

        self.assertIn("### p04｜事项梳理", markdown)
        self.assertIn("ST0001、ST0002", markdown)
        self.assertIn("原文目录保留：原文单列筛选动作。", markdown)
        self.assertIn("严格 Outline 审计通过", markdown)

    def test_renderer_writes_default_project_review_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            outline = root / "outline.json"
            audit = root / "audit.json"
            outline.write_text(json.dumps({"pages": []}), encoding="utf-8")
            audit.write_text(json.dumps({"issues": []}), encoding="utf-8")

            output = render_outline_review(project, outline, audit)

            self.assertEqual(
                (project / "workbench/stages/01-analysis/outline-human-review.md").resolve(),
                output,
            )
            self.assertTrue(output.is_file())

    def test_markdown_exposes_selected_expression_model_and_implicit_slot(self) -> None:
        markdown = render_outline_review_markdown(
            {
                "pages": [
                    {"page_type": "chapter", "chapter_id": "C1", "title": "第一章"},
                    {
                        "page_type": "content", "page_id": "p01", "chapter_id": "C1", "title": "背景",
                        "expression_model_selection": {
                            "model_id": "scqa", "fit": "selected", "fit_reason": "有前提、矛盾和回应",
                            "source_mapping": [
                                {"slot": "situation", "source_refs": ["ST0001"]},
                                {"slot": "question", "source_refs": ["ST0002"], "implicit": True, "statement": "如何回应？"},
                            ],
                        },
                    },
                ],
            },
            {"status": "passed", "issues": []},
        )

        self.assertIn("表达模型：scqa", markdown)
        self.assertIn("question＝ST0002（隐含问题）：如何回应？", markdown)

    def test_audit_renderer_exposes_status_and_issue_table(self) -> None:
        markdown = render_outline_audit_markdown({
            "status": "rewrite_required",
            "issues": [{"code": "TEST", "pages": ["p04"], "retry_strategy": "rewrite", "message": "需要重写"}],
            "argument_graph": {"nodes": [], "edges": [], "source_record_count": 3},
        })

        self.assertIn("**rewrite_required**", markdown)
        self.assertIn("`TEST`", markdown)
        self.assertIn("Source Truth 记录：3", markdown)

        with tempfile.TemporaryDirectory() as tmp:
            output = render_outline_audit_report(Path(tmp), {"status": "passed", "issues": []})
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
