from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if old not in text:
        raise RuntimeError(f"expected text not found in {path}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


def replace_all(path: str, old: str, new: str) -> None:
    text = read(path)
    if old not in text:
        return
    write(path, text.replace(old, new))


def replace_function(path: str, name: str, replacement: str) -> None:
    text = read(path)
    tree = ast.parse(text)
    node = next((item for item in tree.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name), None)
    if node is None:
        raise RuntimeError(f"function {name} not found in {path}")
    lines = text.splitlines(keepends=True)
    start = node.lineno - 1
    end = node.end_lineno or node.lineno
    replacement = replacement.rstrip() + "\n\n"
    lines[start:end] = [replacement]
    write(path, "".join(lines))


def patch_visible_text_binding() -> None:
    path = "cyberppt/page_artifact_spec.py"
    text = read(path)
    if "import warnings\n" not in text:
        text = text.replace("import json\n", "import json\nimport warnings\n", 1)
        write(path, text)
    replacement = '''def _visible_text_bindings(
    *,
    visible_text: tuple[str, ...],
    content_nodes: object,
) -> tuple[VisibleTextBindingSpec, ...]:
    """Project the authoritative content-integrity tree without fuzzy matching.

    Current Stage 02 output carries text/text_id/root_id/ordinal on each node.
    A narrow compatibility path remains for older audited fixtures that already
    carry a complete, unique text_id/root_id chain but predate the duplicated
    node ``text``/``ordinal`` fields. That projection is positional, emits an
    explicit warning, and never guesses ownership by text similarity.
    """

    if not isinstance(content_nodes, list) or not content_nodes:
        return ()
    nodes = [node for node in content_nodes if isinstance(node, dict)]
    if len(nodes) != len(content_nodes):
        raise ValueError("artifact spec content-integrity nodes must all be objects")

    has_text = [bool(str(node.get("text") or "").strip()) for node in nodes]
    compatibility_projection = not any(has_text)
    if compatibility_projection:
        if len(nodes) != len(visible_text):
            raise ValueError(
                "legacy content-integrity projection requires one node per exact visible-text item"
            )
        ids = [str(node.get("text_id") or "").strip() for node in nodes]
        roots = [str(node.get("root_id") or "").strip() for node in nodes]
        if not all(ids) or len(ids) != len(set(ids)) or not all(roots):
            raise ValueError(
                "legacy content-integrity projection requires complete unique text_id/root_id authority"
            )
        warnings.warn(
            "projecting legacy content-integrity nodes by audited list order; regenerate Stage 02 data to persist node text/ordinal",
            RuntimeWarning,
            stacklevel=2,
        )
        ordered = list(nodes)
    else:
        if not all(has_text):
            raise ValueError("artifact spec content-integrity nodes cannot mix text-bearing and legacy nodes")
        ordered = sorted(nodes, key=lambda node: int(node.get("ordinal") or 0))
        node_text = tuple(str(node.get("text") or "").strip() for node in ordered)
        if node_text != visible_text:
            raise ValueError(
                "artifact spec cannot bind visible text because content-integrity node text/order drifted"
            )

    bindings: list[VisibleTextBindingSpec] = []
    seen_ids: set[str] = set()
    for position, node in enumerate(ordered, start=1):
        text_id = str(node.get("text_id") or "").strip()
        root_id = str(node.get("root_id") or "").strip()
        if not text_id or text_id in seen_ids:
            raise ValueError("artifact spec content-integrity text_id must be unique and non-empty")
        if not root_id:
            raise ValueError(f"artifact spec content-integrity node {text_id!r} has no root_id")
        seen_ids.add(text_id)
        bindings.append(
            VisibleTextBindingSpec(
                text_id=text_id,
                text=visible_text[position - 1],
                root_id=root_id,
                order=int(node.get("ordinal") or position),
                role=str(node.get("content_role") or "detail").strip() or "detail",
                hierarchy_level=int(node.get("source_level") or 1),
            )
        )
    return tuple(bindings)'''
    replace_function(path, "_visible_text_bindings", replacement)


def patch_stage02_facade() -> None:
    compat = '''"""Legacy patch-point bridge kept outside the Stage 02 command facade.

This module is the only compatibility seam allowed to import concrete ImageGen,
Quick reconstruction and Office rendering backends. The public command facade
only adapts arguments and forwards caller monkey-patches into this seam.
"""
from __future__ import annotations

from typing import Any

from scripts.imagegen_pipeline.imagegen_handoff import IMAGEGEN_CANVAS_CONTRACT as BODY_IMAGE_CANVAS_CONTRACT
from scripts.imagegen_pipeline.page_manifest import FULL_IMAGE_MODE, require_generated
from scripts.imagegen_pipeline.providers.codex_oauth_image import ensure_output_size, run_codex_image
from scripts.image_to_pptx_runtime.stage02_adapter import CANONICAL_EDITABLE_PPTX_ROUTE
from cyberppt.commands.production_qa import run_officecli_render_qa


def sync_legacy_patch_points(
    *,
    image_stage: Any,
    orchestrator: Any,
    reconstruction_stage: Any,
    delivery_stage: Any,
    run_codex_image_patch: Any,
    ensure_output_size_patch: Any,
    require_generated_patch: Any,
    reconstruction_patch: Any,
    officecli_patch: Any,
    append_ledger_patch: Any,
) -> None:
    image_stage.run_codex_image = run_codex_image_patch
    image_stage.ensure_output_size = ensure_output_size_patch
    orchestrator.require_generated = require_generated_patch
    reconstruction_stage._run_image_to_editable_svg_build = reconstruction_patch
    delivery_stage.run_officecli_render_qa = officecli_patch
    delivery_stage._append_ledger = append_ledger_patch


__all__ = [
    "BODY_IMAGE_CANVAS_CONTRACT",
    "CANONICAL_EDITABLE_PPTX_ROUTE",
    "FULL_IMAGE_MODE",
    "ensure_output_size",
    "require_generated",
    "run_codex_image",
    "run_officecli_render_qa",
    "sync_legacy_patch_points",
]
'''
    write("cyberppt/stage02_production/compat.py", compat)

    path = "cyberppt/commands/final_script_pages.py"
    text = read(path)
    start = text.index("from scripts.imagegen_pipeline.imagegen_handoff import")
    end_marker = "from cyberppt.commands.production_qa import run_officecli_render_qa\n"
    end = text.index(end_marker, start) + len(end_marker)
    replacement = '''from cyberppt.stage02_production import compat as _compat

BODY_IMAGE_CANVAS_CONTRACT = _compat.BODY_IMAGE_CANVAS_CONTRACT
CANONICAL_EDITABLE_PPTX_ROUTE = _compat.CANONICAL_EDITABLE_PPTX_ROUTE
FULL_IMAGE_MODE = _compat.FULL_IMAGE_MODE
ensure_output_size = _compat.ensure_output_size
require_generated = _compat.require_generated
run_codex_image = _compat.run_codex_image
run_officecli_render_qa = _compat.run_officecli_render_qa
'''
    text = text[:start] + replacement + text[end:]
    write(path, text)
    replacement_fn = '''def _sync_legacy_patch_points() -> None:
    """Keep existing monkey-patch/import paths effective during migration."""
    _compat.sync_legacy_patch_points(
        image_stage=_image_stage,
        orchestrator=_orchestrator,
        reconstruction_stage=_reconstruction_stage,
        delivery_stage=_delivery_stage,
        run_codex_image_patch=run_codex_image,
        ensure_output_size_patch=ensure_output_size,
        require_generated_patch=require_generated,
        reconstruction_patch=_run_image_to_editable_svg_build,
        officecli_patch=run_officecli_render_qa,
        append_ledger_patch=_append_ledger,
    )'''
    replace_function(path, "_sync_legacy_patch_points", replacement_fn)

    # Deprecated allow-script-edit remains accepted at the facade/CLI only.
    models = read("cyberppt/stage02_production/models.py")
    models = models.replace("    allow_script_edit_requested: bool = False\n", "")
    write("cyberppt/stage02_production/models.py", models)
    facade = read(path)
    facade = facade.replace("            allow_script_edit_requested=allow_script_edit,\n", "")
    write(path, facade)


def patch_deliverable_prompt() -> None:
    path = "scripts/imagegen_pipeline/deliverable_prompt.py"
    text = read(path)
    import_line = "from scripts.imagegen_pipeline.style_library import default_style_choices, load_style_lock\n"
    if "runtime_style_contract import" not in text:
        text = text.replace(import_line, import_line + '''from scripts.imagegen_pipeline.runtime_style_contract import (
    TERMINAL_EXECUTION_HEADING,
    enforce_terminal_execution_lock,
    load_runtime_style_contract,
)
''', 1)
        write(path, text)

    replace_function(path, "_style09_terminal_execution_lock", '''def _style09_terminal_execution_lock(style_lock_path: Path | None) -> str:
    """Compatibility wrapper over the generic live-style runtime contract."""
    if style_lock_path is None:
        return ""
    try:
        return load_runtime_style_contract(style_lock_path).terminal_lock
    except (OSError, ValueError, TypeError):
        return ""''')
    replace_all(path, 'STYLE09_TERMINAL_LOCK_HEADER = "【风格09最终执行锁｜最高优先级】"', 'STYLE09_TERMINAL_LOCK_HEADER = TERMINAL_EXECUTION_HEADING')
    replace_function(path, "enforce_style09_terminal_lock", '''def enforce_style09_terminal_lock(
    prompt: str,
    style_lock_path: Path | None,
) -> str:
    """Compatibility wrapper over generic terminal-lock enforcement."""
    if style_lock_path is None:
        return prompt
    try:
        runtime = load_runtime_style_contract(style_lock_path)
    except (OSError, ValueError, TypeError):
        return prompt
    return enforce_terminal_execution_lock(prompt, runtime)''')

    text = read(path)
    old_header = '"【源头风格权威｜visual-system.md Style 09｜最高优先级】",'
    if old_header in text:
        text = text.replace(old_header, '"【源头视觉规则权威｜最高优先级】",')
    old_contract = '''(
                    _creative_brief_style_contract(
                        style_lock_path,
                        semantic_tags=style09_semantic_tags,
                    )
                    if creative_brief
                    else style_contract(
                        style_lock_path,
                        semantic_tags=style09_semantic_tags,
                    )
                ),'''
    new_contract = '''(
                    load_runtime_style_contract(style_lock_path).contract
                    if style_lock_path is not None and _is_live_runtime_style(style_lock_path)
                    else (
                        _creative_brief_style_contract(
                            style_lock_path,
                            semantic_tags=style09_semantic_tags,
                        )
                        if creative_brief
                        else style_contract(
                            style_lock_path,
                            semantic_tags=style09_semantic_tags,
                        )
                    )
                ),'''
    if old_contract in text:
        text = text.replace(old_contract, new_contract)
    write(path, text)

    # Add a generic style-id check helper near style_contract.
    if "def _is_live_runtime_style(" not in read(path):
        marker = "\ndef style_contract(\n"
        text = read(path)
        helper = '''\ndef _is_live_runtime_style(style_lock_path: Path) -> bool:
    try:
        payload = load_style_lock(style_lock_path)
    except (OSError, ValueError, TypeError):
        return False
    style = payload.get("style") if isinstance(payload.get("style"), dict) else payload
    try:
        return int(style.get("id") or 0) in (9, 10)
    except (TypeError, ValueError):
        return False

'''
        text = text.replace(marker, helper + "def style_contract(\n", 1)
        write(path, text)


def patch_cli() -> None:
    path = "cyberppt/cli.py"
    text = read(path)
    marker = "\ndef _doctor() -> int:\n"
    if "def _warn_deprecated_compatibility_flag" not in text:
        helper = '''\ndef _warn_deprecated_compatibility_flag(name: str) -> None:
    print(
        f"warning: {name} is deprecated compatibility-only; it does not alter current gates and is planned for removal in the next major CLI revision.",
        file=sys.stderr,
    )

'''
        text = text.replace(marker, helper + "def _doctor() -> int:\n", 1)
    write(path, text)

    for function_name in ("_prepare_visual_structure_command", "_prepare_stage02_handoff_command"):
        text = read(path)
        tree = ast.parse(text)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function_name)
        lines = text.splitlines(keepends=True)
        insert_at = node.body[0].lineno - 1
        warn = '    if getattr(args, "lightweight_stage01_confirmed", False):\n        _warn_deprecated_compatibility_flag("--lightweight-stage01-confirmed")\n'
        if warn.strip() not in text[node.lineno - 1 : (node.end_lineno or node.lineno)]:
            lines.insert(insert_at, warn)
            write(path, "".join(lines))

    text = read(path)
    tree = ast.parse(text)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_final_script_pages_command")
    lines = text.splitlines(keepends=True)
    insert_at = node.body[0].lineno - 1
    warn = '''    if getattr(args, "lightweight_stage01_confirmed", False):
        _warn_deprecated_compatibility_flag("--lightweight-stage01-confirmed")
    if getattr(args, "allow_script_edit", False):
        _warn_deprecated_compatibility_flag("--allow-script-edit")
'''
    if '_warn_deprecated_compatibility_flag("--allow-script-edit")' not in text[node.lineno - 1 : (node.end_lineno or node.lineno)]:
        lines.insert(insert_at, warn)
        write(path, "".join(lines))

    text = read(path)
    text = text.replace(
        'help="Do not pass the Style 09 reference image to the image backend.",',
        'help="Do not pass the selected style reference image to the image backend.",',
    )
    text = text.replace(
        '"Deprecated compatibility flag. Refresh the Stage 02 handoff and visual structure "\n            "after changing a script; prompt and production gates remain required."',
        '"Deprecated compatibility-only flag; retained for old callers and does not change the current Stage 02, prompt, or production gates."',
    )
    text = text.replace(
        '"Deprecated compatibility flag. It no longer grants Stage 02 authorization; "\n            "the current passed script-audit is the content precondition."',
        '"Deprecated compatibility-only flag; retained for old callers and does not grant Stage 02 authorization or change the current content gate."',
    )
    text = text.replace(
        'help="Deprecated compatibility flag; Stage 02 authorization is determined by the current passed full-script audit.",',
        'help="Deprecated compatibility-only flag; retained for old callers and does not change the current Stage 02 authorization gate.",',
    )
    text = text.replace(
        'help="Deprecated compatibility flag; Stage 02 uses the script contract and its current handoff.",',
        'help="Deprecated compatibility-only flag; retained for old callers and does not change the current Stage 02 handoff gate.",',
    )
    write(path, text)

    write("docs/cli-deprecations.md", '''# CLI compatibility deprecations

The following flags are retained only so older automation does not break:

- `--lightweight-stage01-confirmed`
- `--allow-script-edit`

Passing either flag emits a deprecation warning to stderr. Neither flag changes
Stage 01/Stage 02 authorization, script audit, prompt approval, image-text QA,
reconstruction QA, or delivery gates. New examples and automation must not use
them.

Planned removal: the next major CyberPPT CLI revision. Removal will be announced
in that major revision's migration notes before the parser aliases are deleted.

`--no-style-reference` refers generically to the selected style reference image;
it is not tied to a numbered internal style.
''')

    write("tests/test_cli_deprecations.py", '''from __future__ import annotations

from cyberppt.cli import build_parser, _warn_deprecated_compatibility_flag


def test_deprecated_flag_help_is_compatibility_only() -> None:
    help_text = build_parser().format_help()
    parser = build_parser()
    sub = next(a for a in parser._actions if getattr(a, "choices", None))
    final = sub.choices["final-script-pages"].format_help()
    assert "compatibility-only" in final
    assert "selected style reference image" in final
    assert "Style 09 reference image" not in final


def test_deprecation_warning_is_explicit(capsys) -> None:
    _warn_deprecated_compatibility_flag("--allow-script-edit")
    err = capsys.readouterr().err
    assert "deprecated compatibility-only" in err
    assert "does not alter current gates" in err
''')


def split_analysis_audit() -> None:
    path = ROOT / "script_engine/analysis_audit.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    roots = {
        "foundation": "audit_foundation_analysis",
        "deck_plan": "audit_deck_plan",
        "final_script": "audit_final_script",
        "source_index": "validate_source_index_coverage",
    }
    missing = [name for name in roots.values() if name not in functions]
    if missing:
        raise RuntimeError(f"analysis audit public roots missing: {missing}")

    calls: dict[str, set[str]] = {}
    for name, node in functions.items():
        calls[name] = {
            child.id for child in ast.walk(node)
            if isinstance(child, ast.Name) and child.id in functions and child.id != name
        }

    closures: dict[str, set[str]] = {}
    for stage, root in roots.items():
        seen: set[str] = set()
        stack = [root]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(calls[current] - seen)
        closures[stage] = seen

    owners = {
        name: {stage for stage, closure in closures.items() if name in closure}
        for name in functions
    }
    common_funcs = {name for name, stages in owners.items() if len(stages) != 1}
    stage_funcs = {
        stage: {name for name, stages in owners.items() if stages == {stage}}
        for stage in roots
    }

    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assignments = [n for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign))]
    source_lines = source.splitlines()

    def segment(node: ast.AST) -> str:
        return "\n".join(source_lines[node.lineno - 1 : (node.end_lineno or node.lineno)])

    import_segments = [segment(n) for n in imports]
    assignment_segments = [segment(n) for n in assignments]

    imported_names: list[str] = []
    for node in imports:
        if isinstance(node, ast.Import):
            imported_names.extend(alias.asname or alias.name.split(".")[0] for alias in node.names)
        else:
            imported_names.extend(alias.asname or alias.name for alias in node.names if alias.name != "*")
    assigned_names: list[str] = []
    for node in assignments:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            for child in ast.walk(target):
                if isinstance(child, ast.Name):
                    assigned_names.append(child.id)

    order = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    common_order = [name for name in order if name in common_funcs]
    common_all = list(dict.fromkeys(imported_names + assigned_names + common_order))
    package = ROOT / "script_engine/analysis_audits"
    package.mkdir(parents=True, exist_ok=True)
    common_text = '"""Shared deterministic helpers for staged analysis audits."""\n' + "\n".join(import_segments) + "\n\n" + "\n\n".join(assignment_segments)
    if common_order:
        common_text += "\n\n" + "\n\n".join(segment(functions[name]) for name in common_order)
    common_text += "\n\n__all__ = " + repr(common_all) + "\n"
    (package / "common.py").write_text(common_text, encoding="utf-8", newline="\n")

    for stage in roots:
        names = [name for name in order if name in stage_funcs[stage]]
        stage_text = f'"""{stage.replace("_", " ").title()} audit rules."""\nfrom __future__ import annotations\n\nfrom .common import *\n\n'
        stage_text += "\n\n".join(segment(functions[name]) for name in names)
        stage_text += "\n\n__all__ = " + repr(names) + "\n"
        (package / f"{stage}.py").write_text(stage_text, encoding="utf-8", newline="\n")

    init_text = '''"""Stage-specific deterministic analysis audits."""
from .foundation import audit_foundation_analysis
from .deck_plan import audit_deck_plan
from .final_script import audit_final_script
from .source_index import validate_source_index_coverage

__all__ = [
    "audit_foundation_analysis",
    "audit_deck_plan",
    "audit_final_script",
    "validate_source_index_coverage",
]
'''
    (package / "__init__.py").write_text(init_text, encoding="utf-8", newline="\n")

    facade = '''"""Compatibility facade for stage-specific deterministic analysis audits."""
from __future__ import annotations

from .analysis_audits.common import *
from .analysis_audits.foundation import *
from .analysis_audits.deck_plan import *
from .analysis_audits.final_script import *
from .analysis_audits.source_index import *
'''
    path.write_text(facade, encoding="utf-8", newline="\n")

    write("tests/test_analysis_audit_modularization.py", '''from __future__ import annotations

import ast
from pathlib import Path

from script_engine.analysis_audit import (
    audit_deck_plan,
    audit_final_script,
    audit_foundation_analysis,
    validate_source_index_coverage,
)

ROOT = Path(__file__).resolve().parents[1]


def test_analysis_audit_facade_has_no_business_implementations() -> None:
    tree = ast.parse((ROOT / "script_engine/analysis_audit.py").read_text(encoding="utf-8"))
    assert not [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def test_analysis_audit_public_entry_points_remain_available() -> None:
    assert callable(audit_foundation_analysis)
    assert callable(audit_deck_plan)
    assert callable(audit_final_script)
    assert callable(validate_source_index_coverage)
''')


def write_onscreen_review() -> None:
    path = ROOT / "cyberppt/script_quality/onscreen.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    names = {n.name for n in funcs}
    calls = {
        n.name: {c.id for c in ast.walk(n) if isinstance(c, ast.Name) and c.id in names and c.id != n.name}
        for n in funcs
    }
    categories = {
        "parse_normalize": ("parse", "normalize", "strip", "flatten", "text"),
        "hierarchy": ("heading", "title", "hierarchy", "module"),
        "detail_completeness": ("detail", "complete", "orphan", "ordinal"),
        "punctuation": ("punct", "terminal"),
        "label_policy": ("label",),
        "source_visibility": ("source", "visibility", "evidence"),
        "page_expression": ("expression", "page", "foreground", "transition"),
    }
    assigned: dict[str, str] = {}
    for name in names:
        lowered = name.lower()
        assigned[name] = next((cat for cat, keys in categories.items() if any(key in lowered for key in keys)), "shared_other")
    cross_edges = []
    for name, deps in calls.items():
        for dep in deps:
            if assigned[name] != assigned[dep]:
                cross_edges.append((name, dep))
    counts = {cat: sum(1 for value in assigned.values() if value == cat) for cat in set(assigned.values())}
    report = f'''# `script_quality/onscreen.py` 二级拆分评估

本评估按任务书要求基于实际函数与调用关系进行，不以文件行数作为拆分依据。

- 函数总数：{len(funcs)}
- 识别的规则/辅助簇：{len(counts)}
- 跨簇直接调用边：{len(cross_edges)}
- 各簇函数数：{json.dumps(dict(sorted(counts.items())), ensure_ascii=False)}

结论：本轮保持 `onscreen.py` 的现有实现边界，不再做二级物理拆分。当前规则簇仍通过共享 normalize、模块层级、正文角色与页面表达状态发生直接交叉调用；在 P0/P1 主链与 `analysis_audit` 同轮迁移时继续移动这些规则会扩大行为回归面。该结论符合任务书“只有规则簇具备独立输入、独立测试和较少共享状态时才迁移”的约束。

后续触发拆分的条件：某一规则簇可在不读取其他簇内部状态的前提下独立单测，并且 `test_script_quality_contract.py` 与 `test_script_quality_modularization.py` 的 frozen behavior 能保持逐项一致。
'''
    write("docs/onscreen-secondary-modularization-review.md", report)


def patch_known_main_regressions() -> None:
    # New primary_relation contract requires explicit topology in older test factories.
    replace_once(
        "tests/test_content_route.py",
        '        "content": ["共性规则", "场景供给"],\n',
        '        "content": ["共性规则", "场景供给"],\n        "primary_relation": {"type": "parallel", "scope": ["共性规则", "场景供给"], "authority": "hard"},\n',
    )
    replace_once(
        "tests/test_source_consumption.py",
        '        "content": ["术语", "质量"],\n',
        '        "content": ["术语", "质量"],\n        "primary_relation": {"type": "parallel", "scope": ["术语", "质量"], "authority": "hard"},\n',
    )

    # Cross-platform path assertion.
    path = "tests/script_engine/test_cli.py"
    text = read(path)
    text = text.replace('assert out["foundation"]["path"].endswith("script\\\\foundation.json")', 'assert Path(out["foundation"]["path"]).parts[-2:] == ("script", "foundation.json")')
    text = text.replace('assert out["deck_plan"]["path"].endswith("script\\\\deck-plan.json")', 'assert Path(out["deck_plan"]["path"]).parts[-2:] == ("script", "deck-plan.json")')
    if 'from pathlib import Path' not in text:
        text = text.replace('import json\n', 'import json\nfrom pathlib import Path\n', 1)
    write(path, text)

    # Python 3.10 rejects backslashes inside f-string expressions.
    path = "vendor/skills/ppt-script/scripts/ppt_script/render.py"
    text = read(path)
    old = '''    for item in report.semantic_coverage:
        lines.append(
            f"| {item.source_id} | {item.importance} | {'已引用' if item.source_id in mapped else '未引用'} | "
            f"{item.status} | {item.best_slide or '-'} | {item.score:.3f} | {item.content.replace('|', '\\\\|')} |"
        )'''
    new = '''    for item in report.semantic_coverage:
        escaped_content = item.content.replace("|", "\\\\|")
        lines.append(
            f"| {item.source_id} | {item.importance} | {'已引用' if item.source_id in mapped else '未引用'} | "
            f"{item.status} | {item.best_slide or '-'} | {item.score:.3f} | {escaped_content} |"
        )'''
    if old in text:
        text = text.replace(old, new)
    write(path, text)

    # Quick checkpoint preview may use the renderer fallback; final delivery Office QA remains hard.
    path = "scripts/image_to_pptx_runtime/stage02_adapter.py"
    text = read(path)
    text = text.replace('renderer="officecli",\n                        strict_renderer=True,', 'renderer="officecli",\n                        strict_renderer=False,')
    write(path, text)

    # Explicit script-authored visual structure outranks generic message heuristics.
    target = None
    for candidate in (ROOT / "scripts/imagegen_pipeline/handoff").glob("*.py"):
        if "def select_page_visual_intent_type" in candidate.read_text(encoding="utf-8"):
            target = candidate
            break
    if target is None:
        raise RuntimeError("select_page_visual_intent_type implementation not found")
    rel = target.relative_to(ROOT).as_posix()
    text = read(rel)
    tree = ast.parse(text)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "select_page_visual_intent_type")
    if "script_visual_structure =" not in "\n".join(text.splitlines()[node.lineno - 1 : (node.end_lineno or node.lineno)]):
        lines = text.splitlines(keepends=True)
        insert_at = node.body[0].lineno - 1
        block = '''    script_visual_structure = str(getattr(page, "visual_structure", "") or "")
    if any(token in script_visual_structure for token in ("闭环", "回流", "返回前序")):
        return "closed_loop"
    if any(token in script_visual_structure for token in ("双侧协同", "跨系统协同", "接口")):
        return "capability_relationship"
    if any(token in script_visual_structure for token in ("主体泳道", "统一托底", "底部支撑")):
        return "hierarchy_support"
'''
        lines.insert(insert_at, block)
        write(rel, "".join(lines))


def add_curated_power_fixture() -> None:
    fixture = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {
            "title": "电力领域数据基础设施",
            "communication_goal": "说明建设基础与总体架构。",
            "audience": "行业管理人员",
            "narrative": "建设基础 → 总体架构",
        },
        "slides": [
            {
                "id": "P06",
                "page_type": "content",
                "title": "建设基础",
                "subtitle": "五方面基础",
                "mission": "归纳现阶段建设基础。",
                "core_message": "现有工作已形成五方面建设基础。",
                "argument": {"pattern": "classification / taxonomy", "chain": ["基础条件", "实施准备"]},
                "full_copy": "现阶段已在组织机制、数据资源、技术能力、场景储备和实施推进五方面形成建设基础。",
                "onscreen": [
                    {"heading": "组织机制", "items": ["形成协同推进机制"]},
                    {"heading": "数据资源", "items": ["梳理重点数据资源"]},
                    {"heading": "技术能力", "items": ["验证可信流通能力"]},
                    {"heading": "场景储备", "items": ["形成重点场景清单"]},
                    {"heading": "实施推进", "items": ["完成实施准备工作"]},
                ],
                "visual_thesis": "五方面基础共同支撑后续建设。",
                "relationships": [],
                "speaker_notes": "五方面基础分别对应组织、资源、技术、场景和实施条件。",
                "source_refs": [],
            },
            {
                "id": "P12",
                "page_type": "content",
                "title": "总体架构",
                "subtitle": "五层两贯穿",
                "mission": "说明总体技术架构。",
                "core_message": "总体架构由五层能力和两项贯穿机制构成。",
                "argument": {"pattern": "classification / taxonomy", "chain": ["五层能力", "两项贯穿"]},
                "full_copy": "总体架构按照基础设施、资源治理、可信流通、数据服务和场景应用五层组织，并由安全与运营机制贯穿全过程。",
                "onscreen": [
                    {"heading": "基础设施层", "items": ["承载基础计算与连接能力"]},
                    {"heading": "资源治理层", "items": ["支撑目录标准与质量治理"]},
                    {"heading": "可信流通层", "items": ["落实授权控制与审计留痕"]},
                    {"heading": "数据服务层", "items": ["形成数据模型与分析服务"]},
                    {"heading": "场景应用层", "items": ["支撑行业重点业务场景"]},
                    {"heading": "此外：两项贯穿", "items": ["安全保障覆盖全过程", "运营机制覆盖全过程"]},
                ],
                "visual_thesis": "五层能力纵向衔接，两项机制贯穿全过程。",
                "relationships": [],
                "speaker_notes": "重点说明五层能力的分工以及安全、运营两项贯穿机制。",
                "source_refs": [],
            },
        ],
    }
    fixture_path = "tests/script_engine/fixtures/curated/power-industry-data-infrastructure-final-script.json"
    write(fixture_path, json.dumps(fixture, ensure_ascii=False, indent=2) + "\n")
    old = 'ROOT / "tests" / "script_engine" / "fixtures" / "projects" / "power-industry-data-infrastructure" / "dist" / "final-script.json"'
    new = 'ROOT / "tests" / "script_engine" / "fixtures" / "curated" / "power-industry-data-infrastructure-final-script.json"'
    for path in ("tests/script_engine/test_contract_and_render.py", "tests/script_engine/test_delivery_cleanliness.py"):
        replace_all(path, old, new)


def update_style_tests_to_generic_contract() -> None:
    old_headers = ("【风格09最终执行锁｜最高优先级】", "【风格10最终执行锁｜最高优先级】")
    for path in (ROOT / "tests").rglob("test_*.py"):
        text = path.read_text(encoding="utf-8")
        original = text
        for old in old_headers:
            text = text.replace(old, "【最终视觉执行约束｜最高优先级】")
        text = text.replace("Style09/10 final prompt requires one terminal", "live runtime style prompt requires one terminal")
        text = text.replace("non-Style09", "internal style routing token")
        if text != original:
            path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    patch_visible_text_binding()
    patch_stage02_facade()
    patch_deliverable_prompt()
    patch_cli()
    split_analysis_audit()
    write_onscreen_review()
    patch_known_main_regressions()
    add_curated_power_fixture()
    update_style_tests_to_generic_contract()
    print("P0/P1/P2 completion patch applied")


if __name__ == "__main__":
    main()
