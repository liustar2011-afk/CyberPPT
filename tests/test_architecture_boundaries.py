from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tree(relative: str) -> ast.Module:
    path = ROOT / relative
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imports(relative: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(_tree(relative)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _calls(relative: str) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(_tree(relative)):
        if isinstance(node, ast.Call):
            values.add(ast.unparse(node.func))
    return values


def test_final_script_pages_facade_does_not_reacquire_low_level_backends() -> None:
    imports = _imports("cyberppt/commands/final_script_pages.py")
    forbidden = (
        "scripts.imagegen_pipeline.providers",
        "cyberppt.image_text_gate",
        "scripts.image_to_pptx_runtime.stage02_adapter",
        "scripts.presentation_qa",
    )
    assert not any(name.startswith(forbidden) for name in imports)


def test_visual_structure_command_does_not_reacquire_compiler_or_ledger_rules() -> None:
    path = "cyberppt/commands/visual_structure_stage.py"
    source = (ROOT / path).read_text(encoding="utf-8")
    assert "ALLOWED_TOPOLOGY =" not in source
    assert "_FORBIDDEN_STRUCTURES_BY_TOPOLOGY =" not in source
    imports = _imports(path)
    assert "cyberppt.artifact_ledger" not in imports


def test_final_prompt_renderer_reads_only_ir_and_runtime_style_projection() -> None:
    path = "scripts/imagegen_pipeline/final_prompt_renderer.py"
    source = (ROOT / path).read_text(encoding="utf-8")
    imports = _imports(path)
    calls = _calls(path)
    assert "cyberppt.stage02_handoff" not in imports
    assert "cyberppt.visual_stage" not in imports
    assert "json.load" not in calls and "json.loads" not in calls
    assert ".md" not in source


def test_artifact_spec_and_final_prompt_ir_do_not_depend_on_cli() -> None:
    for path in (
        "cyberppt/page_artifact_spec.py",
        "scripts/imagegen_pipeline/final_prompt_ir.py",
    ):
        imports = _imports(path)
        assert not any(name.endswith(".cli") or name == "cyberppt.cli" for name in imports)


def test_runtime_style_contract_does_not_depend_on_prompt_renderer() -> None:
    imports = _imports("scripts/imagegen_pipeline/runtime_style_contract.py")
    assert "scripts.imagegen_pipeline.final_prompt_renderer" not in imports
    assert "scripts.imagegen_pipeline.artifact_prompt" not in imports
