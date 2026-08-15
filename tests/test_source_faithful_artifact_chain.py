from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HANDOFF_SKILL = ROOT / ".agents" / "skills" / "cyberppt-handoff"
from cyberppt.commands.visual_structure_stage import _build_executable_page
from cyberppt.page_artifact_spec import build_page_artifact_spec
from cyberppt.script_quality_contract import ScriptPage
from cyberppt.stage02_handoff import _page_record
from scripts.imagegen_pipeline.artifact_prompt import (
    SECTION_HEADINGS,
    render_artifact_prompt,
)

if str(HANDOFF_SKILL) not in sys.path:
    sys.path.append(str(HANDOFF_SKILL))

from cyberppt_handoff.project import build_projection


class SourceFaithfulArtifactChainTests(unittest.TestCase):
    def test_government_source_authority_reaches_the_nine_part_prompt(self) -> None:
        fixtures = HANDOFF_SKILL / "tests" / "fixtures"
        projection = build_projection(
            fixtures / "foundation",
            fixtures / "semantic",
            fixtures / "outline",
        )
        outline = projection["outline"]
        page_plan = json.loads(
            (fixtures / "outline" / "page-plan.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            [page["title_intent"] for page in page_plan["pages"]],
            [page["title"] for page in outline["pages"]],
        )
        self.assertEqual(
            [page["order"] for page in page_plan["pages"]],
            [page["sequence"] for page in outline["pages"]],
        )
        self.assertEqual("government_official", outline["planning_policy"]["writing_style_mode"])
        self.assertEqual("locked", outline["planning_policy"]["source_structure_mode"])
        self.assertEqual("locked", outline["planning_policy"]["source_title_mode"])
        self.assertEqual("locked", outline["planning_policy"]["source_order_mode"])
        self.assertEqual("preserve", outline["planning_policy"]["source_content_mode"])

        outline_page = next(
            page for page in outline["pages"] if page.get("page_type") == "content"
        )
        source_statements = tuple(
            str(unit["statement"]) for unit in outline_page["content_units"]
        )
        script_page = ScriptPage(
            page_id=outline_page["page_id"],
            sequence=outline_page["sequence"],
            heading=f"第{outline_page['sequence']}页：{outline_page['title']}",
            page_type="content",
            title=outline_page["title"],
            main_message=outline_page["core_message"],
            full_prose="\n".join(source_statements),
            selection_notes="按源材料原文编制。",
            evidence_map="；".join(outline_page["source_refs"]),
            evidence_map_refs=tuple(outline_page["source_refs"]),
            source_refs=tuple(outline_page["source_refs"]),
            boundary_source_refs=(),
            boundary="不得纳入本页未授权内容。",
            visual_structure="仅表达源材料明确的项目目标关系。",
            onscreen_text="\n".join(source_statements),
            module_titles=(),
            contract_receipt={
                "page_mission": outline_page["page_mission"],
                "content_relations": outline_page["content_relations"],
                "consumed_content_unit_ids": [
                    unit["unit_id"] for unit in outline_page["content_units"]
                ],
                "must_not_include": outline_page["must_not_include"],
            },
        )
        handoff_page = _page_record(script_page, outline_page)

        self.assertEqual(outline_page["title"], handoff_page["title"])
        self.assertEqual(
            outline_page["content_relations"],
            handoff_page["stage02_visual_input"]["business_relationships"],
        )
        self.assertEqual(["sec-0001"], handoff_page["source_heading_ids"])

        visual_source = {
            **handoff_page["stage02_visual_input"],
            "page_id": handoff_page["page_id"],
            "page_number": handoff_page["page_number"],
            "page_title": handoff_page["title"],
            "argument_role": handoff_page["argument_role"],
            "page_mission": handoff_page["page_mission"],
            "core_judgment": handoff_page["core_message"],
            "trace_refs": handoff_page["source_refs"],
        }
        locked = visual_source["locked_text_items"]
        form = visual_source["expression_constraints"]["form"]
        candidates = [
            {
                "id": f"c{index}",
                "visual_thesis": "项目由实施准备阶段面向统一服务入口建设目标推进。",
                "semantic_focus": {"kind": "goal", "evidence_key": "goal"},
                "reading_sequence": ["stage", "goal"],
                "spatial_grammar": ["path"],
                "direction": "left_to_right",
                "visual_intent_type": "goal_relationship",
                "expression_fit": {
                    "form": form,
                    "constraint_status": "default_profile",
                    "satisfied_constraints": ["source_relationship_preserved"],
                    "reading_relation": "从当前阶段到建设目标",
                    "balance_strategy": "建设目标为唯一主焦点",
                    "changed_constraints": [],
                    "deviation_reason": "",
                },
            }
            for index in range(1, 4)
        ]
        visual_page = _build_executable_page(
            visual_source,
            {
                "page_id": handoff_page["page_id"],
                "evidence_units": [
                    {
                        "key": "stage",
                        "summary": source_statements[0],
                        "text_ids": [locked[0]["text_id"]],
                    },
                    {
                        "key": "goal",
                        "summary": source_statements[1],
                        "text_ids": [locked[1]["text_id"]],
                    },
                ],
                "candidates": candidates,
                "selected_candidate": "c1",
                "execution_design": {
                    "business_object": "项目建设目标关系场",
                    "visual_focus": "统一服务入口",
                    "text_integration_method": "将原文分别贴附于当前阶段与建设目标对象",
                    "spatial_organization": "由实施准备阶段指向统一服务入口建设目标",
                    "relationship_encoding": "以项目主体和目标对象的有向关系表达建设目标",
                    "semantic_role": "准确呈现项目与统一服务入口之间的目标关系",
                    "use_scene": False,
                    "scene_type": "非实景业务关系场",
                },
            },
        )

        self.assertEqual(
            outline_page["content_relations"],
            visual_page["semantic_graph"]["business_relationships"],
        )
        self.assertNotEqual(
            visual_page["semantic_graph"]["business_relationships"],
            visual_page["connectors"],
        )

        with tempfile.TemporaryDirectory() as directory:
            style_lock = Path(directory) / "style10.json"
            style_lock.write_text(
                json.dumps(
                    {
                        "style": {
                            "id": 10,
                            "name": "政企白底编辑风",
                            "slug": "government_white_editorial",
                            "style_prompt_v2": "纯白底、克制、正式的政企汇报视觉语言。",
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            spec = build_page_artifact_spec(
                handoff_page=handoff_page,
                visual_page=visual_page,
                style_lock=style_lock,
                handoff_sha256="a" * 64,
                visual_source_sha256="b" * 64,
                planning_policy=outline["planning_policy"],
            )
            first = render_artifact_prompt(spec)
            second = render_artifact_prompt(spec)

        self.assertEqual(source_statements, spec.typography.visible_text)
        relationship = spec.relationships[0]
        self.assertEqual("项目", relationship.subject)
        self.assertEqual("has_goal", relationship.relation)
        self.assertEqual(("统一服务入口",), relationship.objects)
        positions = [first.index(heading) for heading in SECTION_HEADINGS]
        self.assertEqual(sorted(positions), positions)
        self.assertIn(
            "- 项目 --has_goal--> 统一服务入口 | direction=subject_to_objects | basis=explicit | confidence=high",
            first,
        )
        for backend_id in (
            "ST0001",
            "ST0002",
            "rel-0001",
            locked[0]["text_id"],
            locked[1]["text_id"],
        ):
            self.assertNotIn(backend_id, first)
        self.assertEqual(first, second)
        self.assertEqual(
            hashlib.sha256(first.encode("utf-8")).hexdigest(),
            hashlib.sha256(second.encode("utf-8")).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
