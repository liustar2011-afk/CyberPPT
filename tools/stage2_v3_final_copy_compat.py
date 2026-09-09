from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"{label} not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def main() -> None:
    contract = Path("scripts/imagegen_pipeline/final_prompt_contract.py")
    replace_once(
        contract,
        '''    for text in ir.visible_text:
        if text.strip().lower() in _FORBIDDEN_CHROME_TEXT:
            raise PromptContractError(
                f"final prompt visible text contains excluded chrome content: {text!r}"
            )
    if ir.copy_contract is not None:
''',
        '''    for text in ir.visible_text:
        if text.strip().lower() in _FORBIDDEN_CHROME_TEXT:
            raise PromptContractError(
                f"final prompt visible text contains excluded chrome content: {text!r}"
            )
    legacy_source_declarations = tuple(
        re.findall(r'^- Source onscreen text: \\"(.*)\\"$', prompt, flags=re.MULTILINE)
    )
    if legacy_source_declarations:
        raise PromptContractError(
            "supplied source material declarations are retired; use exact or explicitly rewriteable copy declarations"
        )
    if ir.copy_contract is not None:
''',
        "retired source-material declaration gate",
    )

    artifact_prompt = Path("tests/test_artifact_prompt.py")
    replace_once(
        artifact_prompt,
        '''    def test_final_prompt_uses_onscreen_as_free_source_and_hides_full_copy(self) -> None:
        unique_context = "This complete explanation is semantic context only."
        spec = replace(
            _spec(),
            semantic_context=SemanticContextSpec(
                text=unique_context,
                source_sha256="d" * 64,
                source_kind="full_prose",
            ),
        )

        prompt = render_final_prompt(build_final_prompt_ir(spec))

        self.assertIn(unique_context, prompt)
        self.assertIn("never render or paraphrase this passage as extra copy", prompt)
        self.assertIn("Use the supplied copy as source material", prompt)
        self.assertIn("rewrite, merge, shorten, reorder, split, select, or replace", prompt)
''',
        '''    def test_final_prompt_locks_authored_onscreen_copy_and_hides_full_copy(self) -> None:
        unique_context = "This complete explanation is semantic context only."
        spec = replace(
            _spec(),
            semantic_context=SemanticContextSpec(
                text=unique_context,
                source_sha256="d" * 64,
                source_kind="full_prose",
            ),
        )

        prompt = render_final_prompt(build_final_prompt_ir(spec))

        self.assertIn(unique_context, prompt)
        self.assertIn("never render or paraphrase this passage as extra copy", prompt)
        self.assertEqual(1, prompt.count('- Exact visible text: "Governed input"'))
        self.assertEqual(1, prompt.count('- Exact visible text: "Traceable result"'))
        self.assertIn("Locked copy may not be rewritten, merged, shortened, reordered, split, selected, or replaced", prompt)
        self.assertIn("Do not add any visible text that is not declared in this copy contract.", prompt)
        self.assertNotIn("Use the supplied copy as source material", prompt)
''',
        "legacy free-source assertion migration",
    )


if __name__ == "__main__":
    main()
