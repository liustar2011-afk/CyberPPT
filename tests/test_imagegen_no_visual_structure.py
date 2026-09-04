from __future__ import annotations

from tests._imagegen_no_visual_structure_base import *
from tests import _imagegen_no_visual_structure_base as _base


# Imported unittest classes can otherwise be collected alongside the wrappers.
_base.ImageGenNoVisualStructureTests.__test__ = False
_base.StructureStyleDecouplingTests.__test__ = False


class ImageGenNoVisualStructureTests(_base.ImageGenNoVisualStructureTests):
    __test__ = True

    def test_page_prompt_places_visual_intent_after_global_style_as_final_priority(self) -> None:
        page = _base.parse_script_markdown(_base.SCRIPT_WITH_VISUAL_STRUCTURE).pages[0]
        with _base.TemporaryDirectory() as directory:
            lock = _base.write_project_style_lock(project=_base.Path(directory), style_id=9)
            prompt = _base.build_page_prompt(
                page,
                lock,
                page_mission="首期场景如何选择",
                visual_intent_override={
                    "visual_thesis": "Explain the approved page-specific decision."
                },
                prompt_compiler="legacy",
            )

        self.assertLess(prompt.index("Page-specific visual intent"), prompt.index("上屏文字"))
        self.assertLess(
            prompt.index("Page-specific visual intent"),
            prompt.index("### 2. Semantic anchor and composition — hard"),
        )
        self.assertNotIn("扩展风格9：", prompt)
        self.assertNotIn("不进入默认候选", prompt)
        self.assertIn("【本页业务关系与视觉表达意图｜不上屏】", prompt)
        self.assertIn("不锁定分栏、卡片、框体或文字区", prompt)
        self.assertIn("将锁定文字就近附着于同一连续业务场", prompt)
        self.assertNotIn("Apply this layout guidance", prompt)
        self.assertIn("Explain the approved page-specific decision.", prompt)
        self.assertIn("do not render field names or instruction text", prompt)


class StructureStyleDecouplingTests(_base.StructureStyleDecouplingTests):
    __test__ = True

    def test_style09_and_style10_project_identical_structure(self) -> None:
        from cyberppt.page_artifact_spec import build_page_artifact_spec

        handoff_page = self._handoff_page()
        with _base.TemporaryDirectory() as directory9, _base.TemporaryDirectory() as directory10:
            lock9 = _base.write_project_style_lock(project=_base.Path(directory9), style_id=9)
            lock10 = _base.write_project_style_lock(project=_base.Path(directory10), style_id=10)
            spec9 = build_page_artifact_spec(
                handoff_page=handoff_page,
                visual_page=self._visual_page(),
                style_lock=lock9,
                script_input_sha256="a" * 64,
                visual_source_sha256="b" * 64,
            )
            spec10 = build_page_artifact_spec(
                handoff_page=handoff_page,
                visual_page=self._visual_page(),
                style_lock=lock10,
                script_input_sha256="a" * 64,
                visual_source_sha256="b" * 64,
            )

        # Style10 is independently selectable while retaining Style09's
        # source-derived visual grammar.
        self.assertEqual(spec9.art_direction.style_id, 9)
        self.assertEqual(spec10.art_direction.style_id, 10)
        self.assertIn(
            "Palette: ivory #F7F6F0, deep blue #12355B",
            spec10.art_direction.contract,
        )
        self.assertNotIn(
            "Keep all locked Chinese text complete.",
            spec10.art_direction.contract,
        )
        self.assertEqual(spec9.deliverable, spec10.deliverable)
        self.assertEqual(spec9.communication_goal, spec10.communication_goal)
        self.assertEqual(spec9.visual_thesis, spec10.visual_thesis)
        self.assertEqual(spec9.evidence, spec10.evidence)
        self.assertEqual(spec9.relationships, spec10.relationships)
        self.assertEqual(spec9.visual_carrier, spec10.visual_carrier)
        self.assertEqual(spec9.composition, spec10.composition)
        self.assertEqual(spec9.typography, spec10.typography)
        self.assertEqual(spec9.hard_constraints, spec10.hard_constraints)

        hashes9 = {key: value for key, value in spec9.source_hashes if key != "style_lock"}
        hashes10 = {key: value for key, value in spec10.source_hashes if key != "style_lock"}
        self.assertEqual(hashes9, hashes10)
