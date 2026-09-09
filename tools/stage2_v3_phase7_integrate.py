from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one patch target, found {count}: {old[:160]!r}")
    write(path, content.replace(old, new, 1))


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


# 1. CompositionStrategy gets an audited mapping validator for PageArtifactSpec.
strategy = "cyberppt/composition_strategy.py"
if "from typing import Iterable, Mapping" not in read(strategy):
    replace_once(strategy, "from typing import Iterable\n", "from typing import Iterable, Mapping\n")
if "def validate_composition_strategy(" not in read(strategy):
    marker = "\ndef resolve_composition_strategy(\n"
    helper = '''\ndef validate_composition_strategy(value: Mapping[str, object]) -> CompositionStrategySpec:\n    if not isinstance(value, Mapping):\n        raise ValueError("composition_strategy must be an object")\n    topology = str(value.get("topology") or "").strip()\n    strategy_id = str(value.get("strategy_id") or "").strip()\n    if not topology or not strategy_id:\n        raise ValueError("composition_strategy requires topology and strategy_id")\n    expected = materialize_composition_strategy(topology=topology, strategy_id=strategy_id)\n    rationale_raw = value.get("rationale")\n    if not isinstance(rationale_raw, (list, tuple)) or not rationale_raw:\n        raise ValueError("composition_strategy rationale must be a non-empty array")\n    try:\n        score = float(value.get("score", 1.0))\n    except (TypeError, ValueError) as exc:\n        raise ValueError("composition_strategy score must be numeric") from exc\n    spec = CompositionStrategySpec(\n        strategy_id=strategy_id,\n        topology=topology,\n        primary_axis=str(value.get("primary_axis") or "").strip(),\n        geometry=str(value.get("geometry") or "").strip(),\n        anchor_policy=str(value.get("anchor_policy") or "").strip(),\n        weight_policy=str(value.get("weight_policy") or "").strip(),\n        span_policy=str(value.get("span_policy") or "").strip(),\n        score=score,\n        rationale=tuple(str(item).strip() for item in rationale_raw if str(item).strip()),\n        version=str(value.get("version") or COMPOSITION_STRATEGY_VERSION),\n    )\n    for field in ("primary_axis", "geometry", "anchor_policy", "weight_policy", "span_policy"):\n        if getattr(spec, field) != getattr(expected, field):\n            raise ValueError(f"composition_strategy {field} drifted from the declared strategy blueprint")\n    return spec\n\n'''
    replace_once(strategy, marker, helper + marker)
if '    "validate_composition_strategy",\n' not in read(strategy):
    replace_once(
        strategy,
        '    "resolve_composition_strategy",\n',
        '    "resolve_composition_strategy",\n    "validate_composition_strategy",\n',
    )

# 2. PageArtifactSpec carries Acceptance + CompositionStrategy as v3 authorities.
page = "cyberppt/page_artifact_spec.py"
if "from cyberppt.acceptance_contract import AcceptanceSpec, build_acceptance_spec" not in read(page):
    replace_once(
        page,
        "from cyberppt.copy_contract import CopyContractSpec, build_copy_contract\n",
        "from cyberppt.acceptance_contract import AcceptanceSpec, build_acceptance_spec\n"
        "from cyberppt.copy_contract import CopyContractSpec, build_copy_contract\n"
        "from cyberppt.composition_strategy import CompositionStrategySpec, validate_composition_strategy\n",
    )
if "    composition_strategy: CompositionStrategySpec | None = None" not in read(page):
    replace_once(
        page,
        "    full_slide_design_context: FullSlideDesignContextSpec | None = None\n",
        "    full_slide_design_context: FullSlideDesignContextSpec | None = None\n"
        "    composition_strategy: CompositionStrategySpec | None = None\n"
        "    acceptance: AcceptanceSpec | None = None\n",
    )
if "    raw_composition_strategy = visual_page.get(\"composition_strategy\")" not in read(page):
    marker = "    raw_region_graph = visual_page.get(\"region_graph\")\n"
    block = '''    raw_composition_strategy = visual_page.get("composition_strategy")\n    composition_strategy = (\n        validate_composition_strategy(raw_composition_strategy)\n        if isinstance(raw_composition_strategy, Mapping)\n        else None\n    )\n'''
    replace_once(page, marker, block + marker)
if "    acceptance = build_acceptance_spec(" not in read(page):
    target = '''    copy_contract = (\n        build_copy_contract(visible_text_bindings, region_by_text_id=region_by_text_id)\n        if visible_text_bindings\n        else None\n    )\n    handoff_relationships = visual_input.get("business_relationships")\n'''
    replacement = '''    copy_contract = (\n        build_copy_contract(visible_text_bindings, region_by_text_id=region_by_text_id)\n        if visible_text_bindings\n        else None\n    )\n    acceptance = build_acceptance_spec(\n        allowed_extra_text_count=(\n            copy_contract.extra_text.max_count\n            if copy_contract is not None and copy_contract.extra_text.allowed\n            else 0\n        )\n    )\n    handoff_relationships = visual_input.get("business_relationships")\n'''
    replace_once(page, target, replacement)
if "        composition_strategy=composition_strategy," not in read(page):
    replace_once(
        page,
        "        full_slide_design_context=full_slide_design_context,\n"
        "    )\n",
        "        full_slide_design_context=full_slide_design_context,\n"
        "        composition_strategy=composition_strategy,\n"
        "        acceptance=acceptance,\n"
        "    )\n",
    )

# 3. FinalPromptIR carries AcceptanceIR and bumps contract version.
ir = "scripts/imagegen_pipeline/final_prompt_ir.py"
if 'FINAL_PROMPT_IR_VERSION = "v5"' in read(ir):
    replace_once(ir, 'FINAL_PROMPT_IR_VERSION = "v5"', 'FINAL_PROMPT_IR_VERSION = "v6"')
if "class AcceptanceIR:" not in read(ir):
    marker = "\n@dataclass(frozen=True)\nclass FullSlideDesignContextIR:\n"
    block = '''\n@dataclass(frozen=True)\nclass AcceptanceIR:\n    exact_copy_coverage: float\n    extra_text_count: int\n    region_ownership: str\n    relationship_accuracy: str\n    hierarchy_preservation: str\n    minimum_readability: str\n    forbidden_structure_absence: bool\n    style_lock_conformance: bool\n\n    def __post_init__(self) -> None:\n        if self.exact_copy_coverage != 1.0:\n            raise PromptContractError("acceptance exact copy coverage must be 100%")\n        if self.extra_text_count < 0:\n            raise PromptContractError("acceptance extra text count cannot be negative")\n        if not all((\n            self.region_ownership.strip(), self.relationship_accuracy.strip(),\n            self.hierarchy_preservation.strip(), self.minimum_readability.strip(),\n        )):\n            raise PromptContractError("acceptance IR is incomplete")\n        if not self.forbidden_structure_absence or not self.style_lock_conformance:\n            raise PromptContractError("acceptance requires forbidden-structure absence and style-lock conformance")\n\n'''
    replace_once(ir, marker, block + marker)
if "    acceptance: AcceptanceIR | None = None" not in read(ir):
    replace_once(
        ir,
        "    full_slide_design_context: FullSlideDesignContextIR | None = None\n",
        "    full_slide_design_context: FullSlideDesignContextIR | None = None\n"
        "    acceptance: AcceptanceIR | None = None\n",
    )
if '    "AcceptanceIR",\n' not in read(ir):
    replace_once(ir, '    "CompositionIR",\n', '    "AcceptanceIR",\n    "CompositionIR",\n')

# 4. Artifact projection of acceptance.
artifact = "scripts/imagegen_pipeline/artifact_prompt.py"
if "    AcceptanceIR," not in read(artifact):
    replace_once(
        artifact,
        "from scripts.imagegen_pipeline.final_prompt_ir import (\n",
        "from scripts.imagegen_pipeline.final_prompt_ir import (\n    AcceptanceIR,\n",
    )
if "def _acceptance_ir(spec: PageArtifactSpec)" not in read(artifact):
    marker = "\ndef _full_slide_design_context_ir(spec: PageArtifactSpec) -> FullSlideDesignContextIR | None:\n"
    helper = '''\ndef _acceptance_ir(spec: PageArtifactSpec) -> AcceptanceIR | None:\n    acceptance = spec.acceptance\n    if acceptance is None:\n        return None\n    return AcceptanceIR(\n        exact_copy_coverage=acceptance.exact_copy_coverage,\n        extra_text_count=acceptance.extra_text_count,\n        region_ownership=acceptance.region_ownership,\n        relationship_accuracy=acceptance.relationship_accuracy,\n        hierarchy_preservation=acceptance.hierarchy_preservation,\n        minimum_readability=acceptance.minimum_readability,\n        forbidden_structure_absence=acceptance.forbidden_structure_absence,\n        style_lock_conformance=acceptance.style_lock_conformance,\n    )\n\n'''
    replace_once(artifact, marker, helper + marker)
if "            acceptance=_acceptance_ir(spec)," not in read(artifact):
    replace_once(
        artifact,
        "            full_slide_design_context=_full_slide_design_context_ir(spec),\n"
        "        )\n",
        "            full_slide_design_context=_full_slide_design_context_ir(spec),\n"
        "            acceptance=_acceptance_ir(spec),\n"
        "        )\n",
    )

# 5. Renderer: one conditional [Acceptance criteria] section before hard constraints.
renderer = "scripts/imagegen_pipeline/final_prompt_renderer.py"
if 'ACCEPTANCE_HEADING = "[Acceptance criteria]"' not in read(renderer):
    replace_once(
        renderer,
        'HARD_CONSTRAINTS_HEADING = "[Hard constraints]"\n',
        'ACCEPTANCE_HEADING = "[Acceptance criteria]"\nHARD_CONSTRAINTS_HEADING = "[Hard constraints]"\n',
    )
if "def _acceptance_lines(ir: FinalPromptIR)" not in read(renderer):
    marker = "\ndef _full_slide_context_lines(ir: FinalPromptIR) -> tuple[str, ...]:\n"
    helper = '''\ndef _acceptance_lines(ir: FinalPromptIR) -> tuple[str, ...]:\n    acceptance = ir.acceptance\n    if acceptance is None:\n        return ()\n    return (\n        f"Exact copy coverage: {round(acceptance.exact_copy_coverage * 100)}% of locked copy must be present exactly once.",\n        f"Maximum extra visible text count: {acceptance.extra_text_count}.",\n        "Region ownership: " + acceptance.region_ownership.replace("_", " ") + ".",\n        "Relationship accuracy: " + acceptance.relationship_accuracy.replace("_", " ") + ".",\n        "Hierarchy preservation: " + acceptance.hierarchy_preservation.replace("_", " ") + ".",\n        "Minimum readability: " + acceptance.minimum_readability.replace("_", " ") + ".",\n        "Forbidden structure absence: required." if acceptance.forbidden_structure_absence else "Forbidden structure absence: not required.",\n        "Style lock conformance: required." if acceptance.style_lock_conformance else "Style lock conformance: not required.",\n    )\n\n'''
    replace_once(renderer, marker, helper + marker)
if "    acceptance_section = (" not in read(renderer):
    replace_once(
        renderer,
        "    hard_constraints_section = \"\\n\".join((HARD_CONSTRAINTS_HEADING, *ir.hard_constraints))\n",
        "    hard_constraints_section = \"\\n\".join((HARD_CONSTRAINTS_HEADING, *ir.hard_constraints))\n"
        "    acceptance_section = (\n"
        "        \"\\n\".join((ACCEPTANCE_HEADING, *_acceptance_lines(ir)))\n"
        "        if ir.acceptance is not None\n"
        "        else \"\"\n"
        "    )\n",
    )
    replace_once(
        renderer,
        "    sections = (*sections_before_runtime, hard_constraints_section, runtime_section)\n",
        "    sections = (*sections_before_runtime, acceptance_section, hard_constraints_section, runtime_section)\n",
    )
if '        "acceptance": (' not in read(renderer):
    replace_once(
        renderer,
        '        "full_slide_design_context": (\n',
        '        "acceptance": (\n'
        '            {\n'
        '                "exact_copy_coverage": ir.acceptance.exact_copy_coverage,\n'
        '                "extra_text_count": ir.acceptance.extra_text_count,\n'
        '                "region_ownership": ir.acceptance.region_ownership,\n'
        '                "relationship_accuracy": ir.acceptance.relationship_accuracy,\n'
        '                "hierarchy_preservation": ir.acceptance.hierarchy_preservation,\n'
        '                "minimum_readability": ir.acceptance.minimum_readability,\n'
        '                "forbidden_structure_absence": ir.acceptance.forbidden_structure_absence,\n'
        '                "style_lock_conformance": ir.acceptance.style_lock_conformance,\n'
        '            } if ir.acceptance is not None else None\n'
        '        ),\n'
        '        "full_slide_design_context": (\n',
    )
if '    "ACCEPTANCE_HEADING",\n' not in read(renderer):
    replace_once(
        renderer,
        '    "HARD_CONSTRAINTS_HEADING",\n',
        '    "ACCEPTANCE_HEADING",\n    "HARD_CONSTRAINTS_HEADING",\n',
    )

# 6. Validator: Acceptance section is machine-checked and ordered before hard constraints/runtime.
contract = "scripts/imagegen_pipeline/final_prompt_contract.py"
if "acceptance criteria section" not in read(contract):
    replace_once(
        contract,
        "    from scripts.imagegen_pipeline.final_prompt_renderer import SECTION_HEADINGS\n",
        "    from scripts.imagegen_pipeline.final_prompt_renderer import ACCEPTANCE_HEADING, HARD_CONSTRAINTS_HEADING, SECTION_HEADINGS\n",
    )
    insert = '''\n    if ir.acceptance is not None:\n        if prompt.count(ACCEPTANCE_HEADING) != 1:\n            raise PromptContractError("acceptance criteria section must appear exactly once")\n        if not (\n            prompt.index(ACCEPTANCE_HEADING) < prompt.index(HARD_CONSTRAINTS_HEADING)\n            < prompt.index(SECTION_HEADINGS[-1])\n        ):\n            raise PromptContractError("acceptance criteria must precede hard constraints and runtime lock")\n        acceptance = ir.acceptance\n        expected_lines = (\n            f"Exact copy coverage: {round(acceptance.exact_copy_coverage * 100)}% of locked copy must be present exactly once.",\n            f"Maximum extra visible text count: {acceptance.extra_text_count}.",\n            "Forbidden structure absence: required.",\n            "Style lock conformance: required.",\n        )\n        if any(prompt.count(line) != 1 for line in expected_lines):\n            raise PromptContractError("acceptance criteria values differ from the prompt IR")\n    elif ACCEPTANCE_HEADING in prompt:\n        raise PromptContractError("legacy prompt without acceptance IR cannot contain acceptance criteria")\n\n'''
    replace_once(
        contract,
        "    reading_path_declarations = re.findall",
        insert + "    reading_path_declarations = re.findall",
    )

# 7. artifact-spec-v3 compiler path while retaining v2.
compiler_contract = "scripts/imagegen_pipeline/prompt_compiler.py"
if 'ARTIFACT_PROMPT_COMPILER_V3 = "artifact-spec-v3"' not in read(compiler_contract):
    replace_once(
        compiler_contract,
        'ARTIFACT_PROMPT_COMPILER = "artifact-spec-v2"\n',
        'ARTIFACT_PROMPT_COMPILER = "artifact-spec-v2"\nARTIFACT_PROMPT_COMPILER_V3 = "artifact-spec-v3"\n',
    )
    replace_once(
        compiler_contract,
        "    ARTIFACT_PROMPT_COMPILER,\n)",
        "    ARTIFACT_PROMPT_COMPILER,\n    ARTIFACT_PROMPT_COMPILER_V3,\n)",
    )
    replace_once(
        compiler_contract,
        '    "ARTIFACT_PROMPT_COMPILER",\n',
        '    "ARTIFACT_PROMPT_COMPILER",\n    "ARTIFACT_PROMPT_COMPILER_V3",\n',
    )

prompt = "scripts/imagegen_pipeline/handoff/prompt.py"
if "    ARTIFACT_PROMPT_COMPILER_V3," not in read(prompt):
    replace_once(
        prompt,
        "    ARTIFACT_PROMPT_COMPILER,\n",
        "    ARTIFACT_PROMPT_COMPILER,\n    ARTIFACT_PROMPT_COMPILER_V3,\n",
    )
if "if prompt_compiler in {ARTIFACT_PROMPT_COMPILER, ARTIFACT_PROMPT_COMPILER_V3}:" not in read(prompt):
    old = '''    if prompt_compiler == ARTIFACT_PROMPT_COMPILER:\n        if artifact_spec is None:\n            raise ValueError("artifact-spec-v2 requires artifact_spec")\n        if visual_design is not None or enrichment_block.strip():\n            raise ValueError(\n                "artifact-spec-v2 accepts only artifact_spec; visual_design and enrichment are separate prompt authorities"\n            )\n'''
    new = '''    if prompt_compiler in {ARTIFACT_PROMPT_COMPILER, ARTIFACT_PROMPT_COMPILER_V3}:\n        if artifact_spec is None:\n            raise ValueError(f"{prompt_compiler} requires artifact_spec")\n        if visual_design is not None or enrichment_block.strip():\n            raise ValueError(\n                f"{prompt_compiler} accepts only artifact_spec; visual_design and enrichment are separate prompt authorities"\n            )\n        if prompt_compiler == ARTIFACT_PROMPT_COMPILER_V3:\n            missing: list[str] = []\n            if artifact_spec.copy_contract is None:\n                missing.append("copy_contract")\n            if artifact_spec.composition_strategy is None:\n                missing.append("composition_strategy")\n            if artifact_spec.region_graph is None:\n                missing.append("region_graph")\n            if artifact_spec.visual_medium_policy is None:\n                missing.append("visual_medium_policy")\n            if artifact_spec.acceptance is None:\n                missing.append("acceptance")\n            if artifact_spec.full_slide_design_context is None:\n                missing.append("full_slide_design_context")\n            if artifact_spec.text_capacity is None or artifact_spec.text_capacity.status != "passed":\n                missing.append("passed_text_capacity")\n            if missing:\n                raise ValueError(\n                    "artifact-spec-v3 requires the complete Stage2 v3 authority chain: "\n                    + ", ".join(missing)\n                )\n'''
    replace_once(prompt, old, new)

facade = "scripts/imagegen_pipeline/imagegen_handoff.py"
if "    ARTIFACT_PROMPT_COMPILER_V3," not in read(facade):
    replace_once(
        facade,
        "    ARTIFACT_PROMPT_COMPILER,\n",
        "    ARTIFACT_PROMPT_COMPILER,\n    ARTIFACT_PROMPT_COMPILER_V3,\n",
    )
    replace_once(
        facade,
        '    "ARTIFACT_PROMPT_COMPILER", "Any",',
        '    "ARTIFACT_PROMPT_COMPILER", "ARTIFACT_PROMPT_COMPILER_V3", "Any",',
    )

# 8. Tests for prompt section, receipt parity, composition validation and compiler v3 selection.
test = ROOT / "tests/test_acceptance_prompt_contract.py"
test.write_text(
    '''import pytest\n\nfrom cyberppt.acceptance_contract import build_acceptance_spec\nfrom cyberppt.composition_strategy import resolve_composition_strategy, validate_composition_strategy\nfrom scripts.imagegen_pipeline.final_prompt_ir import (\n    AcceptanceIR, CompositionIR, FinalPromptIR, RuntimeLockIR, SemanticGroupIR,\n)\nfrom scripts.imagegen_pipeline.final_prompt_renderer import (\n    ACCEPTANCE_HEADING, render_debug_receipt, render_final_prompt,\n)\nfrom scripts.imagegen_pipeline.prompt_compiler import (\n    ARTIFACT_PROMPT_COMPILER, ARTIFACT_PROMPT_COMPILER_V3, PROMPT_COMPILERS,\n    validate_prompt_compiler,\n)\n\n\ndef _ir():\n    return FinalPromptIR(\n        deliverable="Create one finished PowerPoint body visual.",\n        page_judgment="形成可信协同能力。",\n        dominant_relationship="多主体通过受控接口连接并汇聚形成协同结果。",\n        reading_path=("主体", "接口", "结果"),\n        semantic_groups=(SemanticGroupIR(id="g1", role="content", summary="可信协同", emphasis="primary"),),\n        composition=CompositionIR(\n            spatial_organization="one coherent relationship field",\n            primary_focus="可信协同",\n            visual_responsibility=("Use one relationship-bearing field.",),\n        ),\n        visible_text=("可信协同",),\n        hard_constraints=("Do not render instructions.",),\n        runtime_lock=RuntimeLockIR(style_contract="Pure white editorial art direction."),\n        acceptance=AcceptanceIR(\n            exact_copy_coverage=1.0, extra_text_count=0,\n            region_ownership="all_declared_copy_stays_in_assigned_macro_region",\n            relationship_accuracy="source_supported_relationships_only",\n            hierarchy_preservation="preserve_declared_hierarchy",\n            minimum_readability="readable_at_normal_slide_view",\n            forbidden_structure_absence=True, style_lock_conformance=True,\n        ),\n    )\n\n\ndef test_final_prompt_contains_machine_readable_acceptance_section():\n    prompt = render_final_prompt(_ir())\n    assert prompt.count(ACCEPTANCE_HEADING) == 1\n    assert "Exact copy coverage: 100% of locked copy must be present exactly once." in prompt\n    assert "Maximum extra visible text count: 0." in prompt\n    assert "Region ownership: all declared copy stays in assigned macro region." in prompt\n    assert "Relationship accuracy: source supported relationships only." in prompt\n    assert "Hierarchy preservation: preserve declared hierarchy." in prompt\n    assert "Minimum readability: readable at normal slide view." in prompt\n    assert "Forbidden structure absence: required." in prompt\n    assert "Style lock conformance: required." in prompt\n    assert prompt.index(ACCEPTANCE_HEADING) < prompt.index("[Hard constraints]") < prompt.index("[7. Runtime lock]")\n\n\ndef test_debug_receipt_acceptance_matches_prompt_ir():\n    receipt = render_debug_receipt(_ir(), page_id="P03", compiler="artifact-spec-v3", prompt_ir_version="v6")\n    acceptance = receipt["acceptance"]\n    assert acceptance["exact_copy_coverage"] == 1.0\n    assert acceptance["extra_text_count"] == 0\n    assert acceptance["style_lock_conformance"] is True\n\n\ndef test_acceptance_domain_projects_to_ir_values():\n    domain = build_acceptance_spec()\n    assert domain.to_dict()["exact_copy_coverage"] == 1.0\n\n\ndef test_composition_strategy_mapping_validator_preserves_blueprint():\n    strategy = resolve_composition_strategy(\n        topology="directed_flow", focus_policy="sequence_focus", evidence_count=3,\n        medium="business_scene", page_index=1,\n    )\n    restored = validate_composition_strategy(strategy.to_dict())\n    assert restored.strategy_id == strategy.strategy_id\n    drift = strategy.to_dict(); drift["primary_axis"] = "radial"\n    with pytest.raises(ValueError, match="drifted"):\n        validate_composition_strategy(drift)\n\n\ndef test_artifact_spec_v3_is_additive_and_v2_remains_valid():\n    assert ARTIFACT_PROMPT_COMPILER in PROMPT_COMPILERS\n    assert ARTIFACT_PROMPT_COMPILER_V3 in PROMPT_COMPILERS\n    assert validate_prompt_compiler("artifact-spec-v2") == "artifact-spec-v2"\n    assert validate_prompt_compiler("artifact-spec-v3") == "artifact-spec-v3"\n''',
    encoding="utf-8", newline="\n",
)

run(
    "python", "-m", "pytest", "-q",
    "tests/test_acceptance_contract.py",
    "tests/test_acceptance_prompt_contract.py",
    "tests/test_full_slide_prompt_context.py",
    "tests/test_copy_contract_pipeline.py",
    "tests/test_region_graph_composition_strategy.py",
    "tests/test_visual_medium_prompt_v2.py",
    "tests/test_text_capacity_v2.py",
    "tests/test_visual_thesis_compiler_contract.py",
)

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run(
    "git", "add", strategy, page, ir, artifact, renderer, contract,
    compiler_contract, prompt, facade, "tests/test_acceptance_prompt_contract.py",
)
if run("git", "diff", "--cached", "--quiet", check=False).returncode != 0:
    run("git", "commit", "-m", "stage2-v3: add production acceptance contract")
    run("git", "push", "origin", "HEAD:feature/stage2-artifact-contract-v3")
