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
        raise RuntimeError(f"{path}: expected one replacement target, found {count}: {old[:120]!r}")
    write(path, content.replace(old, new, 1))


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def apply_step_1_2() -> None:
    page_spec = "cyberppt/page_artifact_spec.py"
    if "from cyberppt.copy_contract import CopyContractSpec, build_copy_contract" not in read(page_spec):
        replace_once(
            page_spec,
            "from cyberppt.region_graph import RegionGraphSpec, validate_region_graph\n",
            "from cyberppt.copy_contract import CopyContractSpec, build_copy_contract\n"
            "from cyberppt.region_graph import RegionGraphSpec, validate_region_graph\n",
        )

    if "copy_contract: CopyContractSpec | None = None" not in read(page_spec):
        replace_once(
            page_spec,
            "    visual_medium_policy: VisualMediumPolicy | None = None\n",
            "    visual_medium_policy: VisualMediumPolicy | None = None\n"
            "    copy_contract: CopyContractSpec | None = None\n",
        )

    if "copy contract must cover every visible text binding exactly once" not in read(page_spec):
        replace_once(
            page_spec,
            "            if len(ids) != len(set(ids)):\n"
            "                raise ValueError(\"visible text binding text_id values must be unique\")\n",
            "            if len(ids) != len(set(ids)):\n"
            "                raise ValueError(\"visible text binding text_id values must be unique\")\n"
            "        if self.copy_contract is not None:\n"
            "            declared = {item.text_id: item.text for item in self.copy_contract.locked_copy}\n"
            "            declared.update({item.text_id: item.source_text for item in self.copy_contract.rewriteable_copy})\n"
            "            expected = {binding.text_id: binding.text for binding in self.visible_text_bindings}\n"
            "            if declared != expected:\n"
            "                raise ValueError(\"copy contract must cover every visible text binding exactly once\")\n",
        )

    if "visible_text_bindings = _visible_text_bindings(" not in read(page_spec):
        replace_once(
            page_spec,
            "    # Content-integrity nodes describe the authored script structure. They are\n"
            "    # useful for semantic grouping, but they do not bind the model to exact\n"
            "    # bitmap wording. Keep the prompt input as plain reference text.\n"
            "    visible_text_bindings = ()\n",
            "    # Authored content-integrity nodes are the authority for exact visible-copy\n"
            "    # ownership. Preserve that binding into the artifact contract; Stage2 may\n"
            "    # not silently downgrade authored copy to free source material.\n"
            "    visible_text_bindings = _visible_text_bindings(\n"
            "        visible_text=visible_text,\n"
            "        content_nodes=content_nodes,\n"
            "    )\n",
        )

    if "region_by_text_id: dict[str, str] = {}" not in read(page_spec):
        replace_once(
            page_spec,
            "    raw_medium_policy = visual_page.get(\"visual_medium_policy\")\n"
            "    visual_medium_policy = (\n"
            "        validate_visual_medium_policy(raw_medium_policy)\n"
            "        if isinstance(raw_medium_policy, Mapping)\n"
            "        else None\n"
            "    )\n"
            "    handoff_relationships = visual_input.get(\"business_relationships\")\n",
            "    raw_medium_policy = visual_page.get(\"visual_medium_policy\")\n"
            "    visual_medium_policy = (\n"
            "        validate_visual_medium_policy(raw_medium_policy)\n"
            "        if isinstance(raw_medium_policy, Mapping)\n"
            "        else None\n"
            "    )\n"
            "    region_by_text_id: dict[str, str] = {}\n"
            "    if region_graph is not None:\n"
            "        for region in region_graph.regions:\n"
            "            for text_id in region.text_ids:\n"
            "                existing = region_by_text_id.get(text_id)\n"
            "                if existing and existing != region.id:\n"
            "                    raise ValueError(f\"visible text {text_id!r} is owned by multiple macro regions\")\n"
            "                region_by_text_id[text_id] = region.id\n"
            "    copy_contract = (\n"
            "        build_copy_contract(visible_text_bindings, region_by_text_id=region_by_text_id)\n"
            "        if visible_text_bindings\n"
            "        else None\n"
            "    )\n"
            "    handoff_relationships = visual_input.get(\"business_relationships\")\n",
        )

    if "        copy_contract=copy_contract," not in read(page_spec):
        replace_once(
            page_spec,
            "        region_graph=region_graph,\n"
            "        visual_medium_policy=visual_medium_policy,\n"
            "    )\n",
            "        region_graph=region_graph,\n"
            "        visual_medium_policy=visual_medium_policy,\n"
            "        copy_contract=copy_contract,\n"
            "    )\n",
        )

    ir_path = "scripts/imagegen_pipeline/final_prompt_ir.py"
    if "from cyberppt.copy_contract import CopyContractSpec" not in read(ir_path):
        replace_once(
            ir_path,
            "from dataclasses import dataclass\n\n",
            "from dataclasses import dataclass\n\nfrom cyberppt.copy_contract import CopyContractSpec\n\n",
        )
    replace_once(ir_path, 'FINAL_PROMPT_IR_VERSION = "v4"', 'FINAL_PROMPT_IR_VERSION = "v5"') if 'FINAL_PROMPT_IR_VERSION = "v4"' in read(ir_path) else None
    if "    copy_contract: CopyContractSpec | None = None" not in read(ir_path):
        replace_once(
            ir_path,
            "    runtime_lock: RuntimeLockIR\n"
            "    page_title: str = \"\"\n",
            "    runtime_lock: RuntimeLockIR\n"
            "    copy_contract: CopyContractSpec | None = None\n"
            "    page_title: str = \"\"\n",
        )
    if "copy contract visible text must match the prompt IR" not in read(ir_path):
        replace_once(
            ir_path,
            "        if len(self.visible_text) != len(set(self.visible_text)):\n"
            "            raise PromptContractError(\"visible text entries must be unique\")\n",
            "        if len(self.visible_text) != len(set(self.visible_text)):\n"
            "            raise PromptContractError(\"visible text entries must be unique\")\n"
            "        if self.copy_contract is not None:\n"
            "            contract_text = tuple(\n"
            "                item.text for item in self.copy_contract.locked_copy\n"
            "            ) + tuple(\n"
            "                item.source_text for item in self.copy_contract.rewriteable_copy\n"
            "            )\n"
            "            if len(contract_text) != len(set(contract_text)):\n"
            "                raise PromptContractError(\"copy contract visible text entries must be unique\")\n"
            "            if set(contract_text) != set(self.visible_text):\n"
            "                raise PromptContractError(\"copy contract visible text must match the prompt IR\")\n",
        )

    artifact = "scripts/imagegen_pipeline/artifact_prompt.py"
    if "            copy_contract=spec.copy_contract," not in read(artifact):
        replace_once(
            artifact,
            "            runtime_lock=RuntimeLockIR(style_contract=spec.art_direction.contract),\n"
            "            page_title=spec.communication_goal.page_title,\n",
            "            runtime_lock=RuntimeLockIR(style_contract=spec.art_direction.contract),\n"
            "            copy_contract=spec.copy_contract,\n"
            "            page_title=spec.communication_goal.page_title,\n",
        )
    if "Keep each declared copy item within its assigned macro semantic region." not in read(artifact):
        replace_once(
            artifact,
            "            \"Keep each rewritten source item within its assigned macro semantic region.\",\n",
            "            \"Keep each declared copy item within its assigned macro semantic region.\",\n",
        )

    renderer = "scripts/imagegen_pipeline/final_prompt_renderer.py"
    if "def _copy_contract_lines(ir: FinalPromptIR)" not in read(renderer):
        replace_once(
            renderer,
            "def _micro_visual_freedom_lines(ir: FinalPromptIR) -> tuple[str, ...]:\n",
            "def _copy_contract_lines(ir: FinalPromptIR) -> tuple[str, ...]:\n"
            "    contract = ir.copy_contract\n"
            "    if contract is None:\n"
            "        return (\n"
            "            \"Use the supplied copy as source material for concise presentation text. You may rewrite, merge, shorten, reorder, split, select, or replace its wording to suit the visual composition.\",\n"
            "            *(f'- Source onscreen text: \\\"{text}\\\"' for text in ir.visible_text),\n"
            "        )\n"
            "    locked_by_text = {item.text: item for item in contract.locked_copy}\n"
            "    rewriteable_by_text = {item.source_text: item for item in contract.rewriteable_copy}\n"
            "    public_region = (\n"
            "        {region.id: index for index, region in enumerate(ir.region_graph.regions, start=1)}\n"
            "        if ir.region_graph is not None\n"
            "        else {}\n"
            "    )\n"
            "    lines: list[str] = [\n"
            "        \"Copy authority: only the copy declared below may become visible text. Locked copy is immutable; rewriteable copy may change only within its explicit rewrite goal and preservation boundary.\"\n"
            "    ]\n"
            "    for text in ir.visible_text:\n"
            "        locked = locked_by_text.get(text)\n"
            "        if locked is not None:\n"
            "            lines.append(f'- Exact visible text: \\\"{locked.text}\\\"')\n"
            "            if locked.region_id and locked.region_id in public_region:\n"
            "                lines.append(f\"  - assigned macro region: Region {public_region[locked.region_id]}\")\n"
            "            lines.append(f\"  - semantic role: {locked.semantic_role.replace('_', ' ')}; hierarchy {locked.hierarchy}; render exactly once.\")\n"
            "            continue\n"
            "        rewriteable = rewriteable_by_text[text]\n"
            "        lines.append(f'- Rewriteable visible source: \\\"{rewriteable.source_text}\\\"')\n"
            "        if rewriteable.region_id and rewriteable.region_id in public_region:\n"
            "            lines.append(f\"  - assigned macro region: Region {public_region[rewriteable.region_id]}\")\n"
            "        length = f\"; max length {rewriteable.max_length}\" if rewriteable.max_length else \"\"\n"
            "        lines.append(f\"  - rewrite goal: {rewriteable.rewrite_goal}{length}; preserve {', '.join(rewriteable.preserve)}.\")\n"
            "    if contract.extra_text.allowed:\n"
            "        lines.append(f\"Additional visible text is allowed only within the explicit extra-text budget: at most {contract.extra_text.max_count} item(s).\")\n"
            "    else:\n"
            "        lines.append(\"Do not add any visible text that is not declared in this copy contract.\")\n"
            "    return tuple(lines)\n"
            "\n\n"
            "def _micro_visual_freedom_lines(ir: FinalPromptIR) -> tuple[str, ...]:\n",
        )

    if "exact wording is declared once in Section 6" not in read(renderer):
        replace_once(
            renderer,
            "            lines.append(\"- source onscreen text assigned to this group:\")\n"
            "            lines.extend(f'- Source onscreen text: \"{text}\"' for text in binding.exact_text)\n"
            "            level_path = \" → \".join(str(level) for level in levels)\n",
            "            if ir.copy_contract is None:\n"
            "                lines.append(\"- source onscreen text assigned to this group:\")\n"
            "                lines.extend(f'- Source onscreen text: \\\"{text}\\\"' for text in binding.exact_text)\n"
            "            else:\n"
            "                ordinals = _public_text_ordinals(ir)\n"
            "                owned = [ordinals[text_id] for text_id in binding.text_ids if text_id in ordinals]\n"
            "                lines.append(\"- copy ownership: source onscreen item(s) \" + \", \".join(str(item) for item in owned) + \"; exact wording is declared once in Section 6.\")\n"
            "            level_path = \" → \".join(str(level) for level in levels)\n",
        )

    if "*_copy_contract_lines(ir)," not in read(renderer):
        replace_once(
            renderer,
            "        \"\\n\".join(\n"
            "            (\n"
            "                SECTION_HEADINGS[5],\n"
            "                (\n"
            "                    \"Use the supplied copy as source material for concise presentation text. \"\n"
            "                    \"You may rewrite, merge, shorten, reorder, split, select, or replace its \"\n"
            "                    \"wording to suit the visual composition.\"\n"
            "                ),\n"
            "                *(\n"
            "                    ()\n"
            "                    if ir.text_bindings\n"
            "                    else tuple(f'- Source onscreen text: \"{text}\"' for text in ir.visible_text)\n"
            "                ),\n"
            "            )\n"
            "        ),\n",
            "        \"\\n\".join((SECTION_HEADINGS[5], *_copy_contract_lines(ir))),\n",
        )

    if '"copy_contract": (' not in read(renderer):
        replace_once(
            renderer,
            "        \"visible_text\": list(ir.visible_text),\n"
            "        \"hard_constraints\": list(ir.hard_constraints),\n",
            "        \"visible_text\": list(ir.visible_text),\n"
            "        \"copy_contract\": (ir.copy_contract.as_dict() if ir.copy_contract is not None else None),\n"
            "        \"hard_constraints\": list(ir.hard_constraints),\n",
        )

    contract_path = "scripts/imagegen_pipeline/final_prompt_contract.py"
    if "if ir.copy_contract is not None:" not in read(contract_path):
        replace_once(
            contract_path,
            "    source_declarations = tuple(\n"
            "        re.findall(r'^- Source onscreen text: \"(.*)\"$', prompt, flags=re.MULTILINE)\n"
            "    )\n"
            "    if source_declarations != ir.visible_text:\n"
            "        raise PromptContractError(\n"
            "            \"final prompt source onscreen declarations must match the supplied source material\"\n"
            "        )\n",
            "    if ir.copy_contract is not None:\n"
            "        exact_declarations = tuple(\n"
            "            re.findall(r'^- Exact visible text: \\\"(.*)\\\"$', prompt, flags=re.MULTILINE)\n"
            "        )\n"
            "        rewriteable_declarations = tuple(\n"
            "            re.findall(r'^- Rewriteable visible source: \\\"(.*)\\\"$', prompt, flags=re.MULTILINE)\n"
            "        )\n"
            "        locked_text = {item.text for item in ir.copy_contract.locked_copy}\n"
            "        rewriteable_text = {item.source_text for item in ir.copy_contract.rewriteable_copy}\n"
            "        expected_exact = tuple(text for text in ir.visible_text if text in locked_text)\n"
            "        expected_rewriteable = tuple(text for text in ir.visible_text if text in rewriteable_text)\n"
            "        if exact_declarations != expected_exact:\n"
            "            raise PromptContractError(\"final prompt exact-copy declarations must match locked copy\")\n"
            "        if rewriteable_declarations != expected_rewriteable:\n"
            "            raise PromptContractError(\"final prompt rewriteable-copy declarations must match rewriteable copy\")\n"
            "        if \"You may rewrite, merge, shorten, reorder, split, select, or replace\" in prompt:\n"
            "            raise PromptContractError(\"copy-contract prompt cannot grant blanket rewrite authority\")\n"
            "        if (\n"
            "            not ir.copy_contract.extra_text.allowed\n"
            "            and \"Do not add any visible text that is not declared in this copy contract.\" not in prompt\n"
            "        ):\n"
            "            raise PromptContractError(\"copy-contract prompt must forbid undeclared extra visible text\")\n"
            "    else:\n"
            "        source_declarations = tuple(\n"
            "            re.findall(r'^- Source onscreen text: \\\"(.*)\\\"$', prompt, flags=re.MULTILINE)\n"
            "        )\n"
            "        if source_declarations != ir.visible_text:\n"
            "            raise PromptContractError(\n"
            "                \"final prompt source onscreen declarations must match the supplied source material\"\n"
            "            )\n",
        )

    test_path = ROOT / "tests/test_copy_contract_pipeline.py"
    test_path.write_text(
        '''from cyberppt.copy_contract import (\n    CopyContractSpec, ExtraTextPolicySpec, LockedCopySpec, RewriteableCopySpec,\n)\nfrom scripts.imagegen_pipeline.final_prompt_ir import (\n    CompositionIR, FinalPromptIR, PromptContractError, RegionGraphIR, RegionIR,\n    RuntimeLockIR, SemanticGroupIR, TextBindingIR,\n)\nfrom scripts.imagegen_pipeline.final_prompt_renderer import render_final_prompt\n\n\ndef _ir(contract):\n    return FinalPromptIR(\n        deliverable="Create one finished PowerPoint body visual.",\n        page_judgment="形成统一可信服务能力。",\n        dominant_relationship="数据能力支撑可信服务。",\n        reading_path=("input", "service"),\n        semantic_groups=(SemanticGroupIR(id="root-a", role="content", summary="可信服务", emphasis="primary"),),\n        composition=CompositionIR(\n            spatial_organization="one coherent field",\n            primary_focus="可信服务",\n            visual_responsibility=("Use one coherent business relationship field.",),\n        ),\n        visible_text=("统一接入", "可信使用"),\n        hard_constraints=("Do not render instructions.",),\n        runtime_lock=RuntimeLockIR(style_contract="Pure white editorial art direction."),\n        copy_contract=contract,\n        text_bindings=(TextBindingIR(\n            group_id="root-a", role="content", hierarchy_level=1,\n            exact_text=("统一接入", "可信使用"), text_ids=("T1", "T2"),\n            hierarchy_levels=(1, 2),\n        ),),\n        region_graph=RegionGraphIR(\n            primary_axis="left_to_right",\n            regions=(RegionIR(\n                id="R1", semantic_refs=("root-a",), role="content", anchor="center",\n                weight=1.0, span="full", priority="primary", text_ids=("T1", "T2"),\n            ),),\n            relations=(),\n        ),\n    )\n\n\ndef test_locked_copy_is_declared_exactly_once_without_blanket_rewrite_authority():\n    contract = CopyContractSpec(locked_copy=(\n        LockedCopySpec(text_id="T1", text="统一接入", region_id="R1", hierarchy=1),\n        LockedCopySpec(text_id="T2", text="可信使用", region_id="R1", hierarchy=2),\n    ))\n    prompt = render_final_prompt(_ir(contract))\n    assert prompt.count('- Exact visible text: "统一接入"') == 1\n    assert prompt.count('- Exact visible text: "可信使用"') == 1\n    assert "Source onscreen text" not in prompt\n    assert "You may rewrite, merge, shorten, reorder, split, select, or replace" not in prompt\n    assert "Do not add any visible text that is not declared in this copy contract." in prompt\n    assert "assigned macro region: Region 1" in prompt\n    assert "R1" not in prompt\n\n\ndef test_mixed_copy_contract_only_grants_rewrite_to_explicit_item():\n    contract = CopyContractSpec(\n        locked_copy=(LockedCopySpec(text_id="T1", text="统一接入", region_id="R1", hierarchy=1),),\n        rewriteable_copy=(RewriteableCopySpec(\n            text_id="T2", source_text="可信使用", region_id="R1", max_length=12,\n            rewrite_goal="shorten without changing business meaning",\n        ),),\n        extra_text=ExtraTextPolicySpec(),\n    )\n    prompt = render_final_prompt(_ir(contract))\n    assert prompt.count('- Exact visible text: "统一接入"') == 1\n    assert prompt.count('- Rewriteable visible source: "可信使用"') == 1\n    assert "rewrite goal: shorten without changing business meaning; max length 12" in prompt\n\n\ndef test_prompt_ir_rejects_copy_contract_coverage_drift():\n    contract = CopyContractSpec(locked_copy=(LockedCopySpec(text_id="T1", text="统一接入"),))\n    try:\n        _ir(contract)\n    except PromptContractError as exc:\n        assert "copy contract visible text must match" in str(exc)\n    else:\n        raise AssertionError("expected copy-contract coverage validation to fail")\n''',
        encoding="utf-8",
        newline="\n",
    )

    run("python", "-m", "pytest", "-q", "tests/test_copy_contract.py", "tests/test_copy_contract_pipeline.py")

    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "add", page_spec, ir_path, artifact, renderer, contract_path, "tests/test_copy_contract_pipeline.py")
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if diff.returncode == 0:
        print("Step 1.2 already applied; nothing to commit.")
        return
    run("git", "commit", "-m", "stage2-v3: close copy contract authority chain")
    run("git", "push", "origin", "HEAD:feature/stage2-artifact-contract-v3")


if __name__ == "__main__":
    apply_step_1_2()
