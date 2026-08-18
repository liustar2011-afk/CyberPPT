from __future__ import annotations

from dataclasses import replace
import unittest

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
    TypographySpec,
    VisualCarrierSpec,
)
from scripts.imagegen_pipeline.artifact_prompt import build_final_prompt_ir
from scripts.imagegen_pipeline.final_prompt_ir import (
    MAX_SEMANTIC_GROUPS,
    CompositionIR,
    FinalPromptIR,
    PromptContractError,
    RuntimeLockIR,
    SemanticGroupIR,
)


def _composition(*, primary_focus: str = "hub") -> CompositionIR:
    return CompositionIR(
        spatial_organization="Inputs converge on the hub before the result exits.",
        primary_focus=primary_focus,
        visual_responsibility=("Primary focus carries: hub",),
    )


def _group(id_: str = "process", emphasis: str = "primary") -> SemanticGroupIR:
    return SemanticGroupIR(id=id_, role=id_, summary="An authoritative input enters the hub", emphasis=emphasis)


def _ir(**overrides: object) -> FinalPromptIR:
    fields: dict[str, object] = dict(
        deliverable="Create one finished powerpoint_body_visual_asset.",
        page_judgment="Unified governance makes the result traceable.",
        dominant_relationship="Inputs converge through one governance hub and emerge as a traceable result.",
        reading_path=("input", "hub", "result"),
        semantic_groups=(_group(),),
        composition=_composition(primary_focus="hub"),
        visible_text=("Governed input", "Traceable result"),
        hard_constraints=("Do not invent facts.",),
        runtime_lock=RuntimeLockIR(style_contract="Pure white editorial direction."),
    )
    fields.update(overrides)
    return FinalPromptIR(**fields)


class FinalPromptIRTests(unittest.TestCase):
    def test_requires_one_reading_path(self) -> None:
        ir = _ir(reading_path=("①", "②", "③"), composition=_composition(primary_focus="①"))
        self.assertEqual(("①", "②", "③"), ir.reading_path)

    def test_semantic_group_preserves_summary(self) -> None:
        group = SemanticGroupIR(id="demand", role="input", summary="①需求侧变化", emphasis="primary")
        self.assertEqual("①需求侧变化", group.summary)

    def test_rejects_more_than_four_semantic_groups(self) -> None:
        groups = tuple(_group(id_=f"kind{i}", emphasis="primary" if i == 0 else "secondary") for i in range(MAX_SEMANTIC_GROUPS + 1))
        with self.assertRaisesRegex(PromptContractError, "at most 4 semantic groups"):
            _ir(semantic_groups=groups)

    def test_accepts_exactly_four_semantic_groups(self) -> None:
        groups = tuple(_group(id_=f"kind{i}", emphasis="primary" if i == 0 else "secondary") for i in range(MAX_SEMANTIC_GROUPS))
        ir = _ir(semantic_groups=groups)
        self.assertEqual(MAX_SEMANTIC_GROUPS, len(ir.semantic_groups))

    def test_rejects_duplicate_semantic_group_ids(self) -> None:
        with self.assertRaisesRegex(PromptContractError, "unique"):
            _ir(semantic_groups=(_group("process"), _group("process")))

    def test_rejects_empty_semantic_groups(self) -> None:
        with self.assertRaisesRegex(PromptContractError, "at least one semantic group"):
            _ir(semantic_groups=())

    def test_primary_focus_is_independent_free_text(self) -> None:
        # Real Stage 02 `reading_path` entries are full prose blocks, not
        # discrete waypoint labels equal to `primary_focus` — confirmed
        # against 23 real production pages, all of which fail an exact
        # membership check. The IR does not force that shape.
        ir = _ir(composition=_composition(primary_focus="a sentence not literally in the reading path"))
        self.assertEqual("a sentence not literally in the reading path", ir.composition.primary_focus)

    def test_rejects_dangling_judgment_phrase(self) -> None:
        with self.assertRaisesRegex(PromptContractError, "dangling phrase"):
            _ir(page_judgment="治理体系高度可信")

    def test_rejects_empty_judgment(self) -> None:
        with self.assertRaisesRegex(PromptContractError, "page judgment"):
            _ir(page_judgment="   ")

    def test_rejects_empty_visible_text(self) -> None:
        with self.assertRaisesRegex(PromptContractError, "visible text"):
            _ir(visible_text=())

    def test_rejects_duplicate_visible_text(self) -> None:
        with self.assertRaisesRegex(PromptContractError, "unique"):
            _ir(visible_text=("Governed input", "Governed input"))

    def test_semantic_group_rejects_invalid_emphasis(self) -> None:
        with self.assertRaisesRegex(PromptContractError, "primary or secondary"):
            SemanticGroupIR(id="x", role="x", summary="text", emphasis="tertiary")

    def test_semantic_group_rejects_empty_summary(self) -> None:
        with self.assertRaisesRegex(PromptContractError, "requires a summary"):
            SemanticGroupIR(id="x", role="x", summary="   ")

    def test_runtime_lock_requires_style_contract(self) -> None:
        with self.assertRaisesRegex(PromptContractError, "style contract"):
            RuntimeLockIR(style_contract="   ")

    def test_ir_is_frozen(self) -> None:
        ir = _ir()
        with self.assertRaises(Exception):
            ir.deliverable = "changed"  # type: ignore[misc]


def _artifact_spec(*, evidence_kinds: tuple[str, ...] = ("process", "result")) -> PageArtifactSpec:
    """A P05-shaped fixture carrying the exact leak patterns seen in production.

    ``P0 process:`` prefixes, ``direction=``/``basis=``/``confidence=``
    relationship qualifiers, and a ``main_chain=True`` connector are the
    literal leaks confirmed in a real generated manifest
    (pages_005_031_22p_.../page_image_pairs.json, page P05). Normalization
    must consume these fields without echoing their raw form into the IR.
    """

    evidence = tuple(
        EvidenceSpec(summary=f"Evidence summary for {kind}", kind=kind, priority="P0")
        for kind in evidence_kinds
    )
    return PageArtifactSpec(
        page_id="P05",
        page_number=5,
        deliverable=DeliverableSpec(
            asset_type="powerpoint_body_visual_asset",
            page_role="solution",
            canvas=(2048, 1024, "2:1"),
            title_render_mode="external_text_layer",
            subtitle_render_mode="external_text_layer",
            excluded_chrome=("title", "subtitle", "logo", "page_number", "footer", "template_frame"),
        ),
        communication_goal=CommunicationGoalSpec(
            page_mission="Explain the platform's positioning.",
            core_judgment="The platform is the industry hub for power data circulation.",
        ),
        visual_thesis="The operating-platform direction proves the hub positioning together with the other two directions.",
        evidence=evidence,
        relationships=(
            RelationshipSpec(
                subject="二、总体定位",
                relation="contains",
                objects=("（一）建设国家数据基础设施电力行业节点",),
                direction="subject_to_object",
                condition="",
                modality="",
                basis="explicit",
                confidence="high",
            ),
        ),
        visual_carrier=VisualCarrierSpec(
            business_object="Governance operations hub",
            semantic_role="Proves the hub positioning",
            use_scene=True,
            scene_type="Integrated governance operations scene",
        ),
        composition=CompositionSpec(
            spatial_organization="Three directions converge on one central hub icon.",
            reading_path=("national node direction", "operating platform direction", "collaboration carrier direction"),
            primary_focus="operating platform direction",
            secondary_focus=("national node direction",),
            relationship_encoding="Convergence encodes the three supporting directions.",
            text_integration_method="Attach each exact phrase to its business object.",
            spatial_grammar=("convergence",),
            connectors=(ConnectorSpec(relationship="contains", direction="subject_to_object", label="", main_chain=True),),
        ),
        art_direction=ArtDirectionSpec(style_id=10, style_name="Style10", style_slug="style10", contract="Pure white editorial direction."),
        typography=TypographySpec(
            visible_text=("①国家节点方向", "②运营平台方向", "③协同载体方向"),
            allowed_transformations=("line_break",),
            title_render_mode="external_text_layer",
            subtitle_render_mode="external_text_layer",
            body_render_mode="in_image",
        ),
        hard_constraints=HardConstraintSpec(
            global_constraints=("Do not render instructions.",),
            page_constraints=("Do not invent partners.",),
        ),
        source_hashes=(("handoff", "a" * 64), ("style_lock", "b" * 64), ("visual_spec", "c" * 64)),
    )


class BuildFinalPromptIRTests(unittest.TestCase):
    def test_projects_facts_without_backend_qualifiers(self) -> None:
        ir = build_final_prompt_ir(_artifact_spec())

        rendered_debug = repr(ir)
        for leak in ("P0 process", "direction=", "basis=", "confidence=", "main_chain", "main chain"):
            self.assertNotIn(leak, rendered_debug)

    def test_groups_evidence_deterministically_by_kind(self) -> None:
        ir = build_final_prompt_ir(_artifact_spec(evidence_kinds=("process", "result", "process")))

        self.assertEqual(2, len(ir.semantic_groups))
        by_id = {group.id: group for group in ir.semantic_groups}
        self.assertIn("Evidence summary for process", by_id["process"].summary)
        self.assertEqual("primary", by_id["process"].emphasis)
        self.assertEqual("secondary", by_id["result"].emphasis)

    def test_more_than_four_evidence_kinds_raises_with_page_id(self) -> None:
        kinds = tuple(f"kind{i}" for i in range(5))
        with self.assertRaisesRegex(PromptContractError, r"P05:.*at most 4 semantic groups"):
            build_final_prompt_ir(_artifact_spec(evidence_kinds=kinds))

    def test_visible_text_matches_typography_exactly(self) -> None:
        spec = _artifact_spec()
        ir = build_final_prompt_ir(spec)
        self.assertEqual(spec.typography.visible_text, ir.visible_text)

    def test_reading_path_matches_composition_exactly(self) -> None:
        spec = _artifact_spec()
        ir = build_final_prompt_ir(spec)
        self.assertEqual(spec.composition.reading_path, ir.reading_path)

    def test_dominant_relationship_uses_visual_thesis(self) -> None:
        spec = _artifact_spec()
        ir = build_final_prompt_ir(spec)
        self.assertEqual(spec.visual_thesis, ir.dominant_relationship)

    def test_carries_visual_carrier_and_anti_generic_scene_constraint(self) -> None:
        ir = build_final_prompt_ir(_artifact_spec())
        responsibility = " | ".join(ir.composition.visual_responsibility)

        self.assertIn("Governance operations hub", responsibility)
        self.assertIn("Proves the hub positioning", responsibility)
        self.assertIn(
            "Do not substitute a generic dashboard, icon collection, card wall, or unrelated decorative scene.",
            responsibility,
        )

    def test_does_not_carry_relationship_encoding_with_raw_direction_tokens(self) -> None:
        # Real Stage 02 output embeds raw tokens like "outside_to_anchor"
        # directly inside relationship_encoding prose (confirmed against
        # projects/power-data-infrastructure-cooperation-v16-20260815-foundation).
        # Until Stage 02 stops doing that, this field must not reach the
        # final prompt, or final_prompt_contract's snake_case leak check
        # would rightly block real production pages.
        spec = replace(
            _artifact_spec(),
            composition=replace(
                _artifact_spec().composition,
                relationship_encoding="通过关系表达业务判断，方向为outside_to_anchor，不以逐条文字代替业务关系",
            ),
        )
        ir = build_final_prompt_ir(spec)
        self.assertNotIn("outside_to_anchor", " ".join(ir.composition.visual_responsibility))


if __name__ == "__main__":
    unittest.main()
