from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"{label} not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def main() -> None:
    thesis = Path("cyberppt/visual_thesis.py")
    replace_once(
        thesis,
        '    re.compile(r"\\b(?:from|through|into|between|converge|connect|support|flow|feedback|return|map|depend|interface|boundary|exchange|transform|allocate)\\b", re.I),\n',
        '    re.compile(r"\\b(?:from|through|into|between|relationship|relational|peer|converge|connect|support|flow|feedback|return|map|depend|interface|boundary|exchange|transform|allocate)\\b", re.I),\n',
        "English relationship vocabulary",
    )

    regression = Path("tests/test_prompt_optimization_regressions.py")
    replace_once(
        regression,
        '''                "id": "c1",
                "semantic_focus": {"kind": "outcome", "evidence_key": "result"},
''',
        '''                "id": "c1",
                "visual_thesis": "Input flows through the approved relationship into the result.",
                "semantic_focus": {"kind": "outcome", "evidence_key": "result"},
''',
        "prompt optimization visual thesis fixture",
    )

    structure = Path("tests/test_visual_structure_stage.py")
    replace_once(
        structure,
        "from __future__ import annotations\n\nimport json\n",
        "from __future__ import annotations\n\nimport copy\nimport json\n",
        "visual structure copy import",
    )
    replace_once(
        structure,
        '''from cyberppt.onscreen_expression import expression_constraints
from cyberppt.onscreen_expression import expression_constraints_sha256


class VisualStructureStageTests(unittest.TestCase):
''',
        '''from cyberppt.onscreen_expression import expression_constraints
from cyberppt.onscreen_expression import expression_constraints_sha256


_RAW_BUILD_EXECUTABLE_PAGE = _build_executable_page


def _build_executable_page(source, decision):
    """Migrate legacy fixtures to the required visual-thesis contract.

    Missing-thesis rejection is covered separately by
    test_visual_thesis_compiler_contract.py. These older structure fixtures
    need an explicit relational thesis so they can reach the contract they
    were originally written to exercise.
    """
    migrated = copy.deepcopy(decision)
    for candidate in migrated.get("candidates", []):
        candidate.setdefault(
            "visual_thesis",
            "Approved evidence flows through the source-supported relationship.",
        )
    return _RAW_BUILD_EXECUTABLE_PAGE(source, migrated)


class VisualStructureStageTests(unittest.TestCase):
''',
        "legacy visual structure fixture migration",
    )


if __name__ == "__main__":
    main()
