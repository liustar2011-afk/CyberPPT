from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"{label} not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def main() -> None:
    renderer = Path("scripts/imagegen_pipeline/final_prompt_renderer.py")
    replace_once(
        renderer,
        '''            if ir.copy_contract is None:
                lines.append("- source onscreen text assigned to this group:")
                lines.extend(f'- Source onscreen text: \\"{text}\\"' for text in binding.exact_text)
            else:
                ordinals = _public_text_ordinals(ir)
                owned = [ordinals[text_id] for text_id in binding.text_ids if text_id in ordinals]
                lines.append("- copy ownership: source onscreen item(s) " + ", ".join(str(item) for item in owned) + "; exact wording is declared once in Section 6.")
''',
        '''            ordinals = _public_text_ordinals(ir)
            owned = [ordinals[text_id] for text_id in binding.text_ids if text_id in ordinals]
            lines.append("- copy ownership: source onscreen item(s) " + ", ".join(str(item) for item in owned) + "; exact wording is declared once in Section 6.")
''',
        "renderer group fallback block",
    )
    replace_once(
        renderer,
        '''    if contract is None:
        return (
            "Use the supplied copy as source material for concise presentation text. You may rewrite, merge, shorten, reorder, split, select, or replace its wording to suit the visual composition.",
            *(f'- Source onscreen text: \\"{text}\\"' for text in ir.visible_text),
        )
''',
        '''    if contract is None:
        lines: list[str] = [
            "Copy authority: supplied visible copy is locked by default when no explicit copy contract is attached."
        ]
        for text in ir.visible_text:
            lines.append(f'- Exact visible text: \\"{text}\\"')
            lines.append("  - semantic role: content; render exactly once.")
        if not ir.visible_text:
            lines.append("- No visible copy is declared.")
        lines.extend(
            (
                "Locked copy may not be rewritten, merged, shortened, reordered, split, selected, or replaced; line breaks, grouping and position changes may be used only to preserve readability and meaning.",
                "Do not add any visible text that is not declared in this copy contract.",
            )
        )
        return tuple(lines)
''',
        "renderer copy fallback block",
    )

    contract = Path("scripts/imagegen_pipeline/final_prompt_contract.py")
    replace_once(
        contract,
        '''    else:
        source_declarations = tuple(
            re.findall(r'^- Source onscreen text: \\"(.*)\\"$', prompt, flags=re.MULTILINE)
        )
        if source_declarations != ir.visible_text:
            raise PromptContractError(
                "final prompt source onscreen declarations must match the supplied source material"
            )
''',
        '''    else:
        exact_declarations = tuple(
            re.findall(r'^- Exact visible text: \\"(.*)\\"$', prompt, flags=re.MULTILINE)
        )
        if exact_declarations != ir.visible_text:
            raise PromptContractError(
                "final prompt exact-copy declarations must match the supplied visible copy"
            )
        if "You may rewrite, merge, shorten, reorder, split, select, or replace" in prompt:
            raise PromptContractError("legacy fallback cannot grant blanket rewrite authority")
        if "Do not add any visible text that is not declared in this copy contract." not in prompt:
            raise PromptContractError("legacy fallback must forbid undeclared extra visible text")
''',
        "prompt contract legacy fallback block",
    )


if __name__ == "__main__":
    main()
