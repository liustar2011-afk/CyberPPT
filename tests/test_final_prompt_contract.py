from __future__ import annotations

import unittest

from scripts.imagegen_pipeline.final_prompt_contract import (
    MAX_PROMPT_CHARACTERS,
    validate_final_prompt,
)
from scripts.imagegen_pipeline.final_prompt_ir import (
    CompositionIR,
    FinalPromptIR,
    PromptContractError,
    RuntimeLockIR,
    SemanticGroupIR,
)
from scripts.imagegen_pipeline.final_prompt_renderer import render_final_prompt


def _ir(**overrides: object) -> FinalPromptIR:
    fields: dict[str, object] = dict(
        deliverable="Create one finished presentation content visual for a PowerPoint content page.",
        page_judgment="Unified governance makes the result traceable.",
        dominant_relationship="Inputs converge through one governance hub and emerge as a traceable result.",
        reading_path=("authoritative input", "governance hub", "auditable outcome"),
        semantic_groups=(SemanticGroupIR(id="process", role="process", summary="An authoritative input enters the hub", emphasis="primary"),),
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


class ValidateFinalPromptTests(unittest.TestCase):
    def test_valid_prompt_passes(self) -> None:
        ir = _ir()
        prompt = render_final_prompt(ir)
        validate_final_prompt(prompt, ir)  # must not raise

    def test_rejects_two_reading_paths(self) -> None:
        ir = _ir(prompt_mode="directed_composition")
        prompt = render_final_prompt(ir)
        corrupted = prompt.replace(
            "Reading path: authoritative input -> governance hub -> auditable outcome",
            "Reading path: authoritative input -> governance hub -> auditable outcome\n"
            "Reading path: alternate -> path",
        )
        with self.assertRaisesRegex(PromptContractError, "exactly one reading path"):
            validate_final_prompt(corrupted, ir)

    def test_rejects_truncated_page_judgment(self) -> None:
        ir = _ir()
        prompt = render_final_prompt(ir)
        corrupted = prompt.replace(ir.page_judgment, ir.page_judgment[:5])
        with self.assertRaisesRegex(PromptContractError, "page judgment"):
            validate_final_prompt(corrupted, ir)

    def test_rejects_unresolved_placeholder(self) -> None:
        ir = _ir(visible_text=("<one-sentence business judgment>",))
        with self.assertRaisesRegex(PromptContractError, "placeholder"):
            render_final_prompt(ir)

    def test_rejects_snake_case_token_glued_to_cjk_text(self) -> None:
        # Python's \w matches CJK characters, so a naive \w-based boundary
        # check misses a snake_case token directly adjacent to Chinese
        # prose with no separating space - exactly the shape real Stage 02
        # output produces (e.g. "方向为outside_to_anchor，"). Confirmed by
        # rendering this against real production PageArtifactSpec data.
        ir = _ir()
        prompt = render_final_prompt(ir)
        corrupted = prompt.replace(
            "[7. Runtime lock]", "[7. Runtime lock]\n方向为outside_to_anchor，不以逐条文字代替", 1
        )
        with self.assertRaisesRegex(PromptContractError, "internal/backend field"):
            validate_final_prompt(corrupted, ir)

    def test_rejects_known_backend_leaks(self) -> None:
        ir = _ir()
        prompt = render_final_prompt(ir)
        for leak in (
            "P0 process: something happened",
            "direction=subject_to_object",
            "confidence=high",
            "the main chain connector",
            "outside_to_center",
        ):
            corrupted = prompt.replace(
                "[7. Runtime lock]", f"[7. Runtime lock]\n{leak}", 1
            )
            with self.assertRaisesRegex(PromptContractError, "internal/backend field"):
                validate_final_prompt(corrupted, ir)

    def test_allows_source_locked_standard_category_labels(self) -> None:
        ir = _ir(visible_text=("E1与E2支撑流通利用能力",))
        prompt = render_final_prompt(ir)

        validate_final_prompt(prompt, ir)

    def test_rejects_duplicate_visible_text_declaration(self) -> None:
        ir = _ir()
        prompt = render_final_prompt(ir)
        corrupted = prompt.rstrip() + '\n- Exact visible text: "Unauthorized"\n'
        with self.assertRaisesRegex(PromptContractError, "exactly match"):
            validate_final_prompt(corrupted, ir)

    def test_rejects_missing_section(self) -> None:
        ir = _ir()
        prompt = render_final_prompt(ir)
        corrupted = prompt.replace("[4. Semantic groups]", "")
        with self.assertRaisesRegex(PromptContractError, "missing or duplicated"):
            validate_final_prompt(corrupted, ir)

    def test_rejects_duplicate_runtime_lock(self) -> None:
        ir = _ir()
        prompt = render_final_prompt(ir)
        corrupted = prompt.rstrip() + f"\n\n{ir.runtime_lock.style_contract}\n"
        with self.assertRaisesRegex(PromptContractError, "runtime style contract exactly once"):
            validate_final_prompt(corrupted, ir)

    def test_rejects_prompt_over_length_budget(self) -> None:
        ir = _ir()
        prompt = render_final_prompt(ir)
        padded = prompt.replace(
            "Input converges on the hub before the result exits.",
            "Input converges on the hub before the result exits. " + "x" * (MAX_PROMPT_CHARACTERS + 1),
        )
        with self.assertRaisesRegex(PromptContractError, "character budget"):
            validate_final_prompt(padded, ir)

    def test_rejects_excluded_chrome_as_visible_text(self) -> None:
        ir = _ir(visible_text=("标题", "Traceable result"))
        with self.assertRaisesRegex(PromptContractError, "excluded chrome"):
            render_final_prompt(ir)

    def test_style09_requires_exactly_one_terminal_lock(self) -> None:
        ir = _ir()
        prompt = render_final_prompt(ir)
        with self.assertRaisesRegex(PromptContractError, "live runtime style prompt requires one terminal"):
            validate_final_prompt(prompt, ir, style_id=9)

    def test_non_style09_rejects_style09_terminal_marker(self) -> None:
        ir = _ir()
        prompt = render_final_prompt(ir)
        corrupted = prompt.rstrip() + "\n\n【最终视觉执行约束｜最高优先级】\nsomething\n"
        with self.assertRaisesRegex(PromptContractError, "internal style routing token"):
            validate_final_prompt(corrupted, ir)


if __name__ == "__main__":
    unittest.main()
