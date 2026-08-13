from __future__ import annotations

import unittest

from cyberppt.semantic_understanding import semantic_authoring_contract, semantic_template
from cyberppt.commands.prepare_stage01_input import storyline_director_authoring_contract


class GenericSemanticPromptTests(unittest.TestCase):
    def test_generic_prompts_do_not_embed_current_project_answers(self) -> None:
        combined = "\n".join(
            [
                semantic_template(),
                semantic_authoring_contract(),
                storyline_director_authoring_contract(),
            ]
        )

        for project_specific_answer in (
            "行业优势与合作价值",
            "依托→运营→合作→推进",
            "从依托 to运营、合作 and推进",
            "合作依托、业务运营、合作机制和推进安排",
        ):
            self.assertNotIn(project_specific_answer, combined)

    def test_generic_prompts_still_enforce_the_method(self) -> None:
        semantic = semantic_authoring_contract()
        director = storyline_director_authoring_contract()

        self.assertIn("interpreted by exactly one section/subsection node", semantic)
        self.assertIn("claim_origin", semantic)
        self.assertIn("concept_occurrence_graph", semantic)
        self.assertIn("independent source proposition", director)
        self.assertIn("editorial_hypothesis", director)

    def test_storyline_contract_includes_source_logic_focused_route(self) -> None:
        director = storyline_director_authoring_contract()

        self.assertIn("`source_logic_focused`", director)
        self.assertIn("preserves the source-native thesis and major section progression", director)
        self.assertIn("first introductions", director)
        self.assertIn("must not replace the source progression", director)
        self.assertIn("Do not select `source_logic_focused` automatically", director)


if __name__ == "__main__":
    unittest.main()
