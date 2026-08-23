from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.imagegen_pipeline.final_prompt_ir import (
    CompositionIR,
    FinalPromptIR,
    RuntimeLockIR,
    SemanticGroupIR,
)
from scripts.imagegen_pipeline.final_prompt_ir import PromptContractError
from scripts.imagegen_pipeline.final_prompt_renderer import (
    SECTION_HEADINGS,
    render_debug_receipt,
    render_final_prompt,
)


def _sample_ir(**overrides: object) -> FinalPromptIR:
    fields: dict[str, object] = dict(
        deliverable="Create one finished presentation content visual for a PowerPoint content page.",
        page_judgment="Unified governance makes the result traceable.",
        dominant_relationship="Inputs converge through one governance hub and emerge as a traceable result.",
        reading_path=("authoritative input", "governance hub", "auditable outcome"),
        semantic_groups=(
            SemanticGroupIR(id="process", role="process", summary="An authoritative input enters the hub", emphasis="primary"),
            SemanticGroupIR(id="result", role="result", summary="One auditable outcome exits the hub", emphasis="secondary"),
        ),
        composition=CompositionIR(
            spatial_organization="Input converges on the hub before the result exits.",
            primary_focus="governance hub",
            visual_responsibility=("Primary focus carries: governance hub",),
        ),
        visible_text=("①需求侧变化", "Traceable result"),
        hard_constraints=("Do not invent facts.",),
        runtime_lock=RuntimeLockIR(style_contract="Pure white editorial direction."),
    )
    fields.update(overrides)
    return FinalPromptIR(**fields)


class RenderFinalPromptTests(unittest.TestCase):
    def test_emits_fixed_compact_sections_in_order(self) -> None:
        ir = _sample_ir()
        prompt = render_final_prompt(ir)

        self.assertLess(prompt.index(SECTION_HEADINGS[0]), prompt.index(SECTION_HEADINGS[-1]))
        for heading in SECTION_HEADINGS:
            self.assertEqual(1, prompt.count(heading))
        self.assertEqual(1, prompt.count("①需求侧变化"))

    def test_does_not_emit_backend_fields(self) -> None:
        prompt = render_final_prompt(_sample_ir())
        for leak in ("outside_to_center", "main chain", "P0 process", "direction=", "confidence="):
            self.assertNotIn(leak, prompt)

    def test_visible_text_declarations_match_ir_exactly(self) -> None:
        ir = _sample_ir()
        prompt = render_final_prompt(ir)
        for text in ir.visible_text:
            self.assertEqual(1, prompt.count(f'- Exact visible text: "{text}"'))

    def test_style09_terminal_lock_ends_up_at_absolute_end(self) -> None:
        source_marker = "### Final ImageGen execution lock — hard"
        terminal = "formal enterprise-report typography."
        style_contract = f"STYLE09 body rules.\n\n{source_marker}\n\n{terminal}"
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "style09.json"
            lock.write_text(
                json.dumps(
                    {"style": {"id": 9, "name": "Style09", "slug": "style09", "prompt_contract": style_contract}}
                ),
                encoding="utf-8",
            )
            ir = _sample_ir(runtime_lock=RuntimeLockIR(style_contract=style_contract))
            prompt = render_final_prompt(ir, style_id=9, style_lock=lock)

        self.assertEqual(1, prompt.count("【风格09最终执行锁｜最高优先级】"))
        self.assertEqual(1, prompt.count(terminal))
        self.assertTrue(prompt.rstrip().endswith(terminal))
        # enforce_style09_terminal_lock slices the prompt at marker
        # positions to reassert the lock at the true end; without a
        # findable heading in front of them, every hard constraint
        # (including this IR's default "Do not invent facts.") landed
        # after the source marker and was silently discarded by that
        # slicing, for every Style09 page.
        self.assertIn("Do not invent facts.", prompt)

    def test_style09_terminal_lock_preserves_hard_constraints(self) -> None:
        source_marker = "### Final ImageGen execution lock — hard"
        terminal = "formal enterprise-report typography."
        style_contract = f"STYLE09 body rules.\n\n{source_marker}\n\n{terminal}"
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "style09.json"
            lock.write_text(
                json.dumps(
                    {"style": {"id": 9, "name": "Style09", "slug": "style09", "prompt_contract": style_contract}}
                ),
                encoding="utf-8",
            )
            ir = _sample_ir(
                runtime_lock=RuntimeLockIR(style_contract=style_contract),
                hard_constraints=(
                    "Do not render instructions, field labels, source references, evidence ids, or text ids.",
                    "Do not invent a center hub or radial mechanism the declared relationship does not describe.",
                ),
            )
            prompt = render_final_prompt(ir, style_id=9, style_lock=lock)

        self.assertIn(
            "Do not render instructions, field labels, source references, evidence ids, or text ids.",
            prompt,
        )
        self.assertIn(
            "Do not invent a center hub or radial mechanism the declared relationship does not describe.",
            prompt,
        )
        # The terminal lock must still end up as the true final content,
        # after the preserved hard constraints -- not the other way round.
        self.assertTrue(prompt.rstrip().endswith(terminal))
        self.assertLess(prompt.index("Do not invent a center hub"), prompt.rindex(terminal))

    def test_style09_current_chinese_terminal_lock_is_reasserted(self) -> None:
        terminal = "formal enterprise-report typography."
        style_contract = f"STYLE09 body rules.\n\n【风格09最终执行锁｜最高优先级】\n\n{terminal}"
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "style09.json"
            lock.write_text(
                json.dumps(
                    {"style": {"id": 9, "name": "Style09", "slug": "style09", "prompt_contract": style_contract}}
                ),
                encoding="utf-8",
            )
            prompt = render_final_prompt(_sample_ir(runtime_lock=RuntimeLockIR(style_contract=style_contract)), style_id=9, style_lock=lock)

        self.assertEqual(1, prompt.count("【风格09最终执行锁｜最高优先级】"))
        self.assertEqual(1, prompt.count(terminal))
        self.assertTrue(prompt.rstrip().endswith(terminal))

    def test_style09_requires_style_lock(self) -> None:
        with self.assertRaisesRegex(ValueError, "style lock"):
            render_final_prompt(_sample_ir(), style_id=9, style_lock=None)

    def test_contract_violation_blocks_render(self) -> None:
        # An unresolved placeholder passes IR construction (it is not a
        # dangling-phrase judgment) but must still be caught at render time
        # by the final prompt contract gate.
        ir = _sample_ir(visible_text=("<one-sentence business judgment>",))
        with self.assertRaises(PromptContractError):
            render_final_prompt(ir)


class RenderDebugReceiptTests(unittest.TestCase):
    def test_receipt_carries_ir_content_and_identity(self) -> None:
        ir = _sample_ir()
        receipt = render_debug_receipt(
            ir,
            page_id="p04",
            compiler="artifact-spec-v2",
            prompt_ir_version="v1",
            source_hashes=(("handoff", "a" * 64),),
        )

        self.assertEqual("cyberppt.final_prompt_debug.v1", receipt["schema"])
        self.assertEqual("p04", receipt["page"])
        self.assertEqual(list(ir.reading_path), receipt["reading_path"])
        self.assertEqual(2, len(receipt["semantic_groups"]))
        self.assertEqual({"handoff": "a" * 64}, receipt["source_hashes"])


if __name__ == "__main__":
    unittest.main()
