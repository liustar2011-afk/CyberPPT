from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from cyberppt.script_quality_contract import ScriptPage
from cyberppt.page_artifact_spec import (
    ArtDirectionSpec,
    CommunicationGoalSpec,
    CompositionSpec,
    ConnectorSpec,
    DeliverableSpec,
    EvidenceSpec,
    HardConstraintSpec,
    PageArtifactSpec,
    RelationshipSpec,
    SemanticContextSpec,
    TypographySpec,
    VisualCarrierSpec,
)
from scripts.imagegen_pipeline.artifact_prompt import (
    SECTION_HEADINGS,
    _semantic_groups,
    assert_artifact_prompt_contract,
    build_final_prompt_ir,
    render_artifact_prompt,
)
from scripts.imagegen_pipeline.final_prompt_renderer import render_final_prompt
from scripts.imagegen_pipeline.deliverable_prompt import style_contract as live_style_contract
from scripts.imagegen_pipeline.imagegen_handoff import compile_page_prompt


def _spec(*, style_id: int = 4, contract: str = "Pure white editorial direction.") -> PageArtifactSpec:
    return PageArtifactSpec(
        page_id="P07",
        page_number=7,
        deliverable=DeliverableSpec(
            asset_type="presentation content visual",
            page_role="evidence",
            canvas=(2048, 1024, "2:1"),
            title_render_mode="external_text_layer",
            subtitle_render_mode="external_text_layer",
            excluded_chrome=("title", "subtitle", "logo", "page_number", "footer", "template_frame"),
        ),
        communication_goal=CommunicationGoalSpec(
            page_mission="Show how governed inputs become a traceable result.",
            core_judgment="Unified governance makes the result traceable.",
        ),
        visual_thesis="Inputs converge through one governance hub and emerge as a traceable result.",
        evidence=(
            EvidenceSpec("An authoritative input enters the hub", "process", "P0"),
            EvidenceSpec("One auditable outcome exits the hub", "result", "P0"),
        ),
        relationships=(
            RelationshipSpec(
                subject="项目",
                relation="has_goal",
                objects=("统一服务入口",),
                direction="subject_to_objects",
                condition="",
                modality="",
                basis="explicit",
                confidence="high",
            ),
        ),
        visual_carrier=VisualCarrierSpec(
            business_object="Governance operations hub",
            semantic_role="The hub proves transformation and traceability",
            use_scene=True,
            scene_type="Integrated governance operations scene",
        ),
        composition=CompositionSpec(
            spatial_organization="Input converges on the hub before the result exits",
            reading_path=("authoritative input", "governance hub", "auditable outcome"),
            primary_focus="Auditable outcome",
            secondary_focus=("Authoritative input",),
            relationship_encoding="Convergence and output direction encode transformation",
            text_integration_method="Attach each exact phrase to its related object",
            spatial_grammar=("convergence", "path"),
            connectors=(ConnectorSpec("transform", "left_to_right", "transforms", True),),
            topology="multiple evidence lines converging on one judgment",
        ),
        art_direction=ArtDirectionSpec(
            style_id=style_id,
            style_name="Test style",
            style_slug="test_style",
            contract=contract,
        ),
        typography=TypographySpec(
            visible_text=("Governed input", "Traceable result"),
            allowed_transformations=("line_break", "grouping"),
            title_render_mode="external_text_layer",
            subtitle_render_mode="external_text_layer",
            body_render_mode="in_image",
        ),
        hard_constraints=HardConstraintSpec(
            global_constraints=("Do not render instructions.", "Do not invent facts."),
            page_constraints=("Do not create a text wall.",),
        ),
        source_hashes=(("handoff", "a" * 64), ("style_lock", "b" * 64), ("visual_spec", "c" * 64)),
    )


def _legacy_page() -> ScriptPage:
    return ScriptPage(
        page_id="p07",
        sequence=7,
        heading="Page 7",
        page_type="content",
        title="Legacy title must stay external",
        main_message="WRONG LEGACY MEANING MUST NOT REACH ARTIFACT PROMPT",
        full_prose="Legacy source prose.",
        selection_notes="",
        evidence_map="",
        evidence_map_refs=(),
        source_refs=("S001",),
        boundary_source_refs=(),
        boundary="",
        visual_structure="Legacy composition recipe.",
        onscreen_text="WRONG LEGACY BODY MUST NOT REACH ARTIFACT PROMPT",
        module_titles=(),
    )


class ArtifactPromptTests(unittest.TestCase):
    def test_renders_exactly_nine_sections_in_contract_order(self) -> None:
        prompt = render_artifact_prompt(_spec())

        positions = [prompt.index(heading) for heading in SECTION_HEADINGS]
        self.assertEqual(sorted(positions), positions)
        for heading in SECTION_HEADINGS:
            self.assertEqual(1, prompt.count(heading))
        self.assertEqual(1, prompt.count("Pure white editorial direction."))
        self.assertEqual(1, prompt.count("Governed input"))
        self.assertEqual(1, prompt.count("Traceable result"))
        self.assertIn(
            "- 项目 --has_goal--> 统一服务入口 | direction=subject_to_objects | basis=explicit | confidence=high",
            prompt,
        )
        for audit_id in ("rel-0001", "ST0002", "NF-0002"):
            self.assertNotIn(audit_id, prompt)
        self.assertNotIn("--contains-->", prompt)
        self.assertTrue(prompt.rstrip().endswith("Do not create a text wall."))
        assert_artifact_prompt_contract(prompt, expected_visible_text=("Governed input", "Traceable result"))

    def test_style09_terminal_lock_is_unique_and_at_absolute_end(self) -> None:
        source_marker = "### Final ImageGen execution lock — hard"
        terminal = "保持纯白底，并保持唯一视觉中心。"
        style_contract = f"STYLE09 body rules.\n\n{source_marker}\n\n{terminal}"
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "style09.json"
            lock.write_text(
                json.dumps(
                    {
                        "style": {
                            "id": 9,
                            "name": "Style09",
                            "slug": "style09",
                            "prompt_contract": style_contract,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            prompt = render_artifact_prompt(_spec(style_id=9, contract=style_contract), style_lock=lock)
            source_terminal = live_style_contract(lock).strip().splitlines()[-1]

        self.assertNotIn("STYLE09", prompt)
        self.assertNotIn("Style09", prompt)
        self.assertNotIn("风格09", prompt)
        self.assertEqual(1, prompt.count("【最终视觉执行约束｜最高优先级】"))
        self.assertEqual(1, prompt.count(source_terminal))
        self.assertIn(SECTION_HEADINGS[7], prompt)
        self.assertIn(SECTION_HEADINGS[8], prompt)
        self.assertTrue(prompt.rstrip().endswith(source_terminal))
        assert_artifact_prompt_contract(
            prompt,
            expected_visible_text=("Governed input", "Traceable result"),
            style_id=9,
        )

    def test_validator_rejects_missing_section_or_backend_identifier(self) -> None:
        prompt = render_artifact_prompt(_spec())
        with self.assertRaisesRegex(ValueError, "missing or duplicated"):
            assert_artifact_prompt_contract(prompt.replace(SECTION_HEADINGS[4], ""))
        with self.assertRaisesRegex(ValueError, "backend identifier"):
            assert_artifact_prompt_contract(f"{prompt}\nE2")
        empty_thesis = prompt.replace(
            f"{SECTION_HEADINGS[2]}\n{_spec().visual_thesis}\n"
            "Make this relationship immediately legible from the visual asset; do not render this instruction as copy.",
            SECTION_HEADINGS[2],
        )
        with self.assertRaisesRegex(ValueError, "has no content"):
            assert_artifact_prompt_contract(empty_thesis)
        with self.assertRaisesRegex(ValueError, "visible text declarations"):
            assert_artifact_prompt_contract(
                f'{prompt.rstrip()}\n- Exact visible text: "Unauthorized"\n',
                expected_visible_text=("Governed input", "Traceable result"),
            )

    def test_validator_allows_source_locked_standard_category_labels(self) -> None:
        prompt = render_artifact_prompt(_spec())
        prompt = prompt.replace("Governed input", "E1与E2支撑流通利用能力")

        assert_artifact_prompt_contract(
            prompt,
            expected_visible_text=("E1与E2支撑流通利用能力", "Traceable result"),
        )

    def test_exact_text_contract_remains_unique_when_evidence_reuses_the_words(self) -> None:
        spec = replace(
            _spec(),
            evidence=(EvidenceSpec("Governed input", "process", "P0"),),
        )
        prompt = render_artifact_prompt(spec)

        self.assertGreater(prompt.count("Governed input"), 1)
        self.assertEqual(1, prompt.count('- Exact visible text: "Governed input"'))

    def test_bracketed_visible_text_uses_one_shared_hierarchy_grammar(self) -> None:
        spec = replace(
            _spec(),
            typography=replace(
                _spec().typography,
                visible_text=("【建设方向】", "Governed input", "Traceable result"),
            ),
        )

        prompt = render_final_prompt(build_final_prompt_ir(spec))

        self.assertIn('Render "【建设方向】" exactly once in its group container', prompt)
        self.assertIn("one level-1 family", prompt)
        self.assertIn("same compact flat rectangular title band", prompt)
        self.assertIn("one quieter level-2 style", prompt)

    def test_artifact_compiler_uses_projection_as_sole_prompt_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            style_lock = Path(directory) / "style.json"
            style_lock.write_text(
                json.dumps(
                    {
                        "style": {
                            "id": 10,
                            "name": "Test style",
                            "slug": "test_style",
                            "colors": {"background": "#FFFFFF"},
                            "prompt_contract": "Pure white editorial direction.",
                        }
                    }
                ),
                encoding="utf-8",
            )
            compiled = compile_page_prompt(
                _legacy_page(),
                style_lock,
                prompt_compiler="artifact-spec-v2",
                artifact_spec=_spec(),
            )

        self.assertEqual("artifact-spec-v2", compiled.compiler_version)
        # The production prompt now comes from the single final-prompt IR
        # renderer, not the retired nine-section render_artifact_prompt().
        expected_ir = build_final_prompt_ir(_spec())
        expected = render_final_prompt(expected_ir, style_id=_spec().art_direction.style_id, style_lock=style_lock)
        self.assertEqual(expected, compiled.prompt)
        self.assertNotIn("WRONG LEGACY", compiled.prompt)
        self.assertEqual(_spec().to_dict(), compiled.build_metadata()["artifact_spec"])
        self.assertEqual("v2", compiled.prompt_ir_version)
        self.assertIsNotNone(compiled.debug_receipt)
        self.assertEqual("P07", compiled.debug_receipt["page"])
        # Default production uses a semantic brief. Stage 02 composition
        # details stay auditable in the artifact spec without becoming a
        # second layout engine inside the ImageGen prompt.
        self.assertNotIn("multiple evidence lines converging on one judgment", compiled.prompt)
        self.assertNotIn("Visual carrier:", compiled.prompt)
        self.assertNotIn("Spatial grammar:", compiled.prompt)
        self.assertIn("ImageGen owns the scene-or-structure choice", compiled.prompt)
        self.assertEqual("semantic_brief", compiled.debug_receipt["prompt_mode"])
        self.assertNotIn("causal_convergence", compiled.prompt)

    def test_directed_composition_preserves_a_source_required_visual_path(self) -> None:
        spec = replace(_spec(), prompt_mode="directed_composition")
        prompt = render_final_prompt(build_final_prompt_ir(spec))

        self.assertIn("Reading path: authoritative input -> governance hub -> auditable outcome", prompt)
        self.assertIn("Visual carrier: Governance operations hub", prompt)
        self.assertIn("Spatial grammar: convergence, path", prompt)

    def test_semantic_brief_consumes_full_prose_without_making_it_visible_text(self) -> None:
        unique_context = "Authorization may be withdrawn when the declared operating condition ends."
        spec = replace(
            _spec(),
            semantic_context=SemanticContextSpec(
                text=unique_context,
                argument_chain="authorization → operating condition → withdrawal",
                source_sha256="d" * 64,
                source_kind="full_prose",
                trace_refs=("SU-EXAMPLE-PARAGRAPH-01",),
            ),
        )
        prompt = render_final_prompt(build_final_prompt_ir(spec))

        self.assertIn(unique_context, prompt)
        self.assertIn("Source-grounded semantic context (non-visible", prompt)
        self.assertNotIn(f'Exact visible text: "{unique_context}"', prompt)
        self.assertNotIn("SU-EXAMPLE-PARAGRAPH-01", prompt)

    def test_artifact_compiler_requires_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            style_lock = Path(directory) / "style.json"
            style_lock.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "artifact_spec"):
                compile_page_prompt(
                    _legacy_page(),
                    style_lock,
                    prompt_compiler="artifact-spec-v2",
                )


class SemanticGroupsTests(unittest.TestCase):
    def test_groups_by_root_id_not_kind_when_content_integrity_is_present(self) -> None:
        evidence = (
            EvidenceSpec("Root module summary", "process", "P0", root_id="P05-T01"),
            EvidenceSpec("A detail under the same root module", "process", "P0", root_id="P05-T01"),
            EvidenceSpec("An unrelated second root module", "result", "P0", root_id="P05-T04"),
        )

        groups = _semantic_groups(evidence, page_judgment="")

        self.assertEqual(2, len(groups))
        by_id = {group.id: group for group in groups}
        self.assertIn("P05-T01", by_id)
        self.assertIn("P05-T04", by_id)
        self.assertIn("Root module summary", by_id["P05-T01"].summary)
        self.assertIn("A detail under the same root module", by_id["P05-T01"].summary)
        self.assertNotIn("unrelated second root module", by_id["P05-T01"].summary)

    def test_falls_back_to_kind_grouping_when_root_id_is_absent(self) -> None:
        evidence = (
            EvidenceSpec("An authoritative input enters the hub", "process", "P0"),
            EvidenceSpec("One auditable outcome exits the hub", "result", "P0"),
        )

        groups = _semantic_groups(evidence, page_judgment="")

        self.assertEqual(2, len(groups))
        by_id = {group.id: group for group in groups}
        self.assertIn("process", by_id)
        self.assertIn("result", by_id)
        self.assertEqual("process", by_id["process"].role)
        self.assertEqual("primary", by_id["process"].emphasis)
        self.assertEqual("secondary", by_id["result"].emphasis)


if __name__ == "__main__":
    unittest.main()
