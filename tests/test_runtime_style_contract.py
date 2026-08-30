from __future__ import annotations

from scripts.imagegen_pipeline.runtime_style_contract import (
    RuntimeStyleContract,
    TERMINAL_EXECUTION_HEADING,
    enforce_terminal_execution_lock,
    internal_style_token_leaks,
)


def test_generic_terminal_lock_is_absolute_end_and_not_numbered() -> None:
    runtime = RuntimeStyleContract(
        contract="Use a clean editorial field.",
        terminal_lock="Keep locked text exact.",
        source="references/visual-system.md",
        sha256="abc",
    )
    prompt = enforce_terminal_execution_lock(
        "[7. Runtime lock]\nUse a clean editorial field.\n\n[Hard constraints]\nNo invented facts.",
        runtime,
    )
    assert prompt.count(TERMINAL_EXECUTION_HEADING) == 1
    assert prompt.rstrip().endswith("Keep locked text exact.")
    assert internal_style_token_leaks(prompt) == ()


def test_terminal_lock_removes_exact_duplicate_instruction_from_body() -> None:
    runtime = RuntimeStyleContract(
        contract="Use a clean editorial field.",
        terminal_lock="Keep locked text exact.\nPeople stay absent by default.",
        source="style-registry",
        sha256="abc",
    )
    prompt = enforce_terminal_execution_lock(
        "Page-specific constraint.\nPeople stay absent by default.\nNo invented facts.",
        runtime,
    )

    assert prompt.count("People stay absent by default.") == 1
    assert "Page-specific constraint." in prompt
    assert "No invented facts." in prompt
    assert prompt.rstrip().endswith("People stay absent by default.")


def test_terminal_lock_does_not_remove_partial_or_page_specific_text() -> None:
    runtime = RuntimeStyleContract(
        contract="Use a clean editorial field.",
        terminal_lock="Keep locked text exact.",
        source="style-registry",
        sha256="abc",
    )
    prompt = enforce_terminal_execution_lock(
        "Page rule: Keep locked text exact. This sentence carries extra context.",
        runtime,
    )

    assert "Page rule: Keep locked text exact. This sentence carries extra context." in prompt
    assert prompt.count("Keep locked text exact.") == 2


def test_internal_style_token_detector_catches_routing_labels() -> None:
    leaks = internal_style_token_leaks(
        "Style 09 and 风格10 are internal routing names; normal prose follows."
    )
    assert len(leaks) == 2
