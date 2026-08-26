from __future__ import annotations

import ast
from pathlib import Path
import tempfile
import unittest

from cyberppt.commands.init_project import init_project


REPO_ROOT = Path(__file__).resolve().parents[1]
TEXT_ARTIFACT_ROOTS = (
    REPO_ROOT / "cyberppt",
    REPO_ROOT / "scripts" / "imagegen_pipeline",
    REPO_ROOT / "scripts" / "image_to_editable_svg",
    REPO_ROOT / "scripts" / "image_to_pptx_runtime",
    REPO_ROOT / "scripts" / "presentation_qa",
)


def _write_text_calls_without_newline_translation(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders: list[int] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "write_text"
        ):
            continue
        newline = next(
            (keyword for keyword in node.keywords if keyword.arg == "newline"),
            None,
        )
        if not (
            newline is not None
            and isinstance(newline.value, ast.Constant)
            and newline.value.value in {"", "\n"}
        ):
            offenders.append(node.lineno)
    return offenders


class TextOutputContractTests(unittest.TestCase):
    def test_project_initialization_writes_lf_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            init_project(project)
            for path in (project / "manifest.yml", project / "README.md"):
                self.assertNotIn(b"\r\n", path.read_bytes(), path.name)

    def test_production_text_artifact_writers_disable_newline_translation(self) -> None:
        offenders: list[str] = []
        for root in TEXT_ARTIFACT_ROOTS:
            for path in sorted(root.rglob("*.py")):
                for line in _write_text_calls_without_newline_translation(path):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{line}")
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
