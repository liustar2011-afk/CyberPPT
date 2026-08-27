from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "cyberppt" / "stage02_production"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_orchestrator_does_not_import_low_level_production_backends() -> None:
    imports = _imports(PACKAGE / "orchestrator.py")
    forbidden_prefixes = (
        "scripts.imagegen_pipeline.providers",
        "cyberppt.image_text_gate",
        "scripts.image_to_pptx_runtime.stage02_adapter",
        "cyberppt.commands.production_qa",
    )
    assert not any(name.startswith(forbidden_prefixes) for name in imports)


def test_image_stage_does_not_depend_on_reconstruction_or_delivery() -> None:
    imports = _imports(PACKAGE / "image_stage.py")
    assert "cyberppt.stage02_production.reconstruction_stage" not in imports
    assert "cyberppt.stage02_production.delivery_stage" not in imports


def test_command_facade_has_no_stage_business_implementation() -> None:
    path = ROOT / "cyberppt" / "commands" / "final_script_pages.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert functions == {
        "_sync_legacy_patch_points",
        "_generate_manifest_images",
        "_normalize_audited_manifest_images",
        "run_final_script_pages",
    }


def test_stage_models_are_frozen_dataclasses() -> None:
    source = (PACKAGE / "models.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    dataclasses = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert dataclasses
    for node in dataclasses:
        decorators = [ast.unparse(item) for item in node.decorator_list]
        assert "dataclass(frozen=True)" in decorators
