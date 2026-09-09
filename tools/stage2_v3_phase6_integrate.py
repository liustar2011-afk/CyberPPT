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
        raise RuntimeError(f"{path}: expected one patch target, found {count}: {old[:140]!r}")
    write(path, content.replace(old, new, 1))


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


# 1. Stage02 handoff exposes full-slide design context while retaining body canvas.
handoff = "cyberppt/stage02_handoff.py"
if "from cyberppt.full_slide_context import default_full_slide_design_context" not in read(handoff):
    replace_once(
        handoff,
        "from cyberppt.script_quality_contract import ScriptPage, parse_script_path\n",
        "from cyberppt.script_quality_contract import ScriptPage, parse_script_path\n"
        "from cyberppt.full_slide_context import default_full_slide_design_context\n",
    )
if '        "full_slide_design_context": default_full_slide_design_context().to_dict(),\n' not in read(handoff):
    replace_once(
        handoff,
        '        "body_image_canvas": dict(BODY_CANVAS),\n'
        '        "title_render_mode": "external_text_layer",\n',
        '        "body_image_canvas": dict(BODY_CANVAS),\n'
        '        "full_slide_design_context": default_full_slide_design_context().to_dict(),\n'
        '        "title_render_mode": "external_text_layer",\n',
    )

# 2. PageArtifactSpec validates/provides compatibility projection.
page = "cyberppt/page_artifact_spec.py"
if "FullSlideDesignContextSpec" not in read(page):
    replace_once(
        page,
        "from cyberppt.copy_contract import CopyContractSpec, build_copy_contract\n",
        "from cyberppt.copy_contract import CopyContractSpec, build_copy_contract\n"
        "from cyberppt.full_slide_context import (\n"
        "    FullSlideDesignContextSpec, default_full_slide_design_context,\n"
        "    validate_full_slide_design_context,\n"
        ")\n",
    )
if "    full_slide_design_context: FullSlideDesignContextSpec | None = None" not in read(page):
    replace_once(
        page,
        "    text_capacity: TextCapacityAssessment | None = None\n",
        "    text_capacity: TextCapacityAssessment | None = None\n"
        "    full_slide_design_context: FullSlideDesignContextSpec | None = None\n",
    )
if "    raw_full_slide_context = visual_input.get(\"full_slide_design_context\")" not in read(page):
    replace_once(
        page,
        "    if handoff_canvas != visual_canvas:\n"
        "        raise ValueError(\"artifact spec canvas drifted between handoff and visual spec\")\n\n",
        "    if handoff_canvas != visual_canvas:\n"
        "        raise ValueError(\"artifact spec canvas drifted between handoff and visual spec\")\n"
        "    raw_full_slide_context = visual_input.get(\"full_slide_design_context\")\n"
        "    if isinstance(raw_full_slide_context, Mapping):\n"
        "        full_slide_design_context = validate_full_slide_design_context(raw_full_slide_context)\n"
        "    else:\n"
        "        warnings.warn(\n"
        "            \"legacy_stage02_prompt_contract: projecting default 16:9 full-slide design context\",\n"
        "            RuntimeWarning, stacklevel=2,\n"
        "        )\n"
        "        full_slide_design_context = default_full_slide_design_context()\n"
        "    if full_slide_design_context.body_export_canvas != handoff_canvas:\n"
        "        raise ValueError(\"full-slide context body export canvas drifted from Stage02 body canvas\")\n\n",
    )
if "        full_slide_design_context=full_slide_design_context," not in read(page):
    replace_once(
        page,
        "        text_capacity=capacity,\n"
        "    )\n",
        "        text_capacity=capacity,\n"
        "        full_slide_design_context=full_slide_design_context,\n"
        "    )\n",
    )

# 3. FinalPromptIR carries a public geometry-only slide context.
ir = "scripts/imagegen_pipeline/final_prompt_ir.py"
if "class FullSlideDesignContextIR:" not in read(ir):
    marker = "\n@dataclass(frozen=True)\nclass RuntimeLockIR:\n"
    block = '''\n@dataclass(frozen=True)\nclass FullSlideDesignContextIR:\n    canvas: tuple[int, int, str]\n    title_region: tuple[int, int, int, int]\n    body_region: tuple[int, int, int, int]\n    body_export_canvas: tuple[int, int, str]\n    title_render_mode: str = "external_text_layer"\n    subtitle_render_mode: str = "external_text_layer"\n\n    def __post_init__(self) -> None:\n        if self.canvas != (1920, 1080, "16:9"):\n            raise PromptContractError("full-slide prompt context must use 1920x1080 (16:9)")\n        if self.body_export_canvas != (2048, 1024, "2:1"):\n            raise PromptContractError("full-slide prompt context must preserve 2048x1024 body export")\n        if self.title_render_mode != "external_text_layer" or self.subtitle_render_mode != "external_text_layer":\n            raise PromptContractError("title and subtitle must remain external text layers")\n        tx, ty, tw, th = self.title_region\n        bx, by, bw, bh = self.body_region\n        if min(tx, ty, tw, th, bx, by, bw, bh) < 0 or tw <= 0 or th <= 0 or bw <= 0 or bh <= 0:\n            raise PromptContractError("full-slide prompt regions must have valid geometry")\n        if ty + th > by:\n            raise PromptContractError("full-slide title region must not overlap body region")\n\n'''
    replace_once(ir, marker, block + marker)
if "    full_slide_design_context: FullSlideDesignContextIR | None = None" not in read(ir):
    replace_once(
        ir,
        "    micro_visual_freedom: MicroVisualFreedomIR | None = None\n",
        "    micro_visual_freedom: MicroVisualFreedomIR | None = None\n"
        "    full_slide_design_context: FullSlideDesignContextIR | None = None\n",
    )
if '    "FullSlideDesignContextIR",\n' not in read(ir):
    replace_once(
        ir,
        '    "FinalPromptIR",\n',
        '    "FinalPromptIR",\n    "FullSlideDesignContextIR",\n',
    )

# 4. Artifact projection.
artifact = "scripts/imagegen_pipeline/artifact_prompt.py"
if "    FullSlideDesignContextIR," not in read(artifact):
    replace_once(
        artifact,
        "    FinalPromptIR,\n",
        "    FinalPromptIR,\n    FullSlideDesignContextIR,\n",
    )
if "def _full_slide_design_context_ir(" not in read(artifact):
    marker = "\ndef _visual_medium_policy_ir(spec: PageArtifactSpec) -> VisualMediumPolicyIR | None:\n"
    helper = '''\ndef _full_slide_design_context_ir(spec: PageArtifactSpec) -> FullSlideDesignContextIR | None:\n    context = spec.full_slide_design_context\n    if context is None:\n        return None\n    title = context.title_region\n    body = context.body_region\n    return FullSlideDesignContextIR(\n        canvas=context.canvas,\n        title_region=(title.x, title.y, title.w, title.h),\n        body_region=(body.x, body.y, body.w, body.h),\n        body_export_canvas=context.body_export_canvas,\n        title_render_mode=title.render_mode,\n        subtitle_render_mode=context.subtitle_render_mode,\n    )\n\n'''
    replace_once(artifact, marker, helper + marker)
if "            full_slide_design_context=_full_slide_design_context_ir(spec)," not in read(artifact):
    replace_once(
        artifact,
        "            micro_visual_freedom=_micro_visual_freedom_ir(spec),\n"
        "        )\n",
        "            micro_visual_freedom=_micro_visual_freedom_ir(spec),\n"
        "            full_slide_design_context=_full_slide_design_context_ir(spec),\n"
        "        )\n",
    )

# 5. Renderer knows full slide/title region without rendering title into body asset.
renderer = "scripts/imagegen_pipeline/final_prompt_renderer.py"
if "def _full_slide_context_lines(ir: FinalPromptIR)" not in read(renderer):
    marker = "\ndef _copy_contract_lines(ir: FinalPromptIR) -> tuple[str, ...]:\n"
    helper = '''\ndef _full_slide_context_lines(ir: FinalPromptIR) -> tuple[str, ...]:\n    context = ir.full_slide_design_context\n    if context is None:\n        return ()\n    tx, ty, tw, th = context.title_region\n    bx, by, bw, bh = context.body_region\n    ew, eh, er = context.body_export_canvas\n    return (\n        f"Full-slide design context: {context.canvas[0]}x{context.canvas[1]} ({context.canvas[2]}).",\n        f"External title region: x={tx}, y={ty}, w={tw}, h={th}; reserve this region in the full-slide hierarchy but do not render title or subtitle into the body image.",\n        f"Body visual region in the finished slide: x={bx}, y={by}, w={bw}, h={bh}; compose the body as the visual continuation below the external title region.",\n        f"Body image export remains independent at {ew}x{eh} ({er}); map the full-slide body-region composition into this export without adding title, subtitle, logo, footer or page chrome.",\n    )\n\n'''
    replace_once(renderer, marker, helper + marker)
if "                *_full_slide_context_lines(ir)," not in read(renderer):
    replace_once(
        renderer,
        "        \"\\n\".join((SECTION_HEADINGS[0], ir.deliverable)),\n",
        "        \"\\n\".join((SECTION_HEADINGS[0], ir.deliverable, *_full_slide_context_lines(ir))),\n",
    )
if '        "full_slide_design_context": (' not in read(renderer):
    replace_once(
        renderer,
        '        "visible_text": list(ir.visible_text),\n',
        '        "full_slide_design_context": (\n'
        '            {\n'
        '                "canvas": list(ir.full_slide_design_context.canvas),\n'
        '                "title_region": list(ir.full_slide_design_context.title_region),\n'
        '                "body_region": list(ir.full_slide_design_context.body_region),\n'
        '                "body_export_canvas": list(ir.full_slide_design_context.body_export_canvas),\n'
        '                "title_render_mode": ir.full_slide_design_context.title_render_mode,\n'
        '                "subtitle_render_mode": ir.full_slide_design_context.subtitle_render_mode,\n'
        '            } if ir.full_slide_design_context is not None else None\n'
        '        ),\n'
        '        "visible_text": list(ir.visible_text),\n',
    )

# 6. Validator requires the public context lines when context exists.
contract = "scripts/imagegen_pipeline/final_prompt_contract.py"
if "full-slide design context must be declared" not in read(contract):
    insert = '''\n    if ir.full_slide_design_context is not None:\n        context = ir.full_slide_design_context\n        expected = f"Full-slide design context: {context.canvas[0]}x{context.canvas[1]} ({context.canvas[2]})."\n        if prompt.count(expected) != 1:\n            raise PromptContractError("full-slide design context must be declared exactly once")\n        if "External title region:" not in prompt or "Body image export remains independent" not in prompt:\n            raise PromptContractError("full-slide prompt must declare external title and body-export mapping")\n\n'''
    replace_once(
        contract,
        "    _validate_text_bindings(prompt, ir)\n\n    reading_path_declarations",
        "    _validate_text_bindings(prompt, ir)\n" + insert + "    reading_path_declarations",
    )

# 7. Focused integration tests.
test = ROOT / "tests/test_full_slide_prompt_context.py"
test.write_text(
    '''from pathlib import Path\n\nfrom cyberppt.full_slide_context import default_full_slide_design_context\nfrom scripts.imagegen_pipeline.final_prompt_ir import (\n    CompositionIR, FinalPromptIR, FullSlideDesignContextIR, RuntimeLockIR, SemanticGroupIR,\n)\nfrom scripts.imagegen_pipeline.final_prompt_renderer import render_debug_receipt, render_final_prompt\n\n\nROOT = Path(__file__).resolve().parents[1]\n\n\ndef _ir():\n    context = default_full_slide_design_context()\n    title = context.title_region\n    body = context.body_region\n    return FinalPromptIR(\n        deliverable="Create one finished PowerPoint body visual on a 2048x1024 canvas.",\n        page_judgment="形成可信协同能力。",\n        dominant_relationship="多主体通过受控接口连接并汇聚形成协同结果。",\n        reading_path=("主体", "接口", "结果"),\n        semantic_groups=(SemanticGroupIR(id="g1", role="content", summary="可信协同", emphasis="primary"),),\n        composition=CompositionIR(\n            spatial_organization="one coherent relationship field",\n            primary_focus="可信协同",\n            visual_responsibility=("Use one relationship-bearing field.",),\n        ),\n        visible_text=("可信协同",),\n        hard_constraints=("Do not render instructions.",),\n        runtime_lock=RuntimeLockIR(style_contract="Pure white editorial art direction."),\n        page_title="外置页面标题",\n        full_slide_design_context=FullSlideDesignContextIR(\n            canvas=context.canvas,\n            title_region=(title.x, title.y, title.w, title.h),\n            body_region=(body.x, body.y, body.w, body.h),\n            body_export_canvas=context.body_export_canvas,\n        ),\n    )\n\n\ndef test_prompt_knows_16_9_title_region_but_keeps_2_1_body_export():\n    prompt = render_final_prompt(_ir())\n    assert "Full-slide design context: 1920x1080 (16:9)." in prompt\n    assert "External title region: x=128, y=52, w=1664, h=120" in prompt\n    assert "Body visual region in the finished slide: x=128, y=216, w=1664, h=832" in prompt\n    assert "Body image export remains independent at 2048x1024 (2:1)" in prompt\n    assert "do not render title or subtitle into the body image" in prompt\n\n\ndef test_debug_receipt_persists_full_slide_mapping():\n    receipt = render_debug_receipt(_ir(), page_id="P03", compiler="artifact-spec-v3", prompt_ir_version="v5")\n    context = receipt["full_slide_design_context"]\n    assert context["canvas"] == [1920, 1080, "16:9"]\n    assert context["body_export_canvas"] == [2048, 1024, "2:1"]\n    assert context["title_render_mode"] == "external_text_layer"\n\n\ndef test_stage02_handoff_declares_full_slide_context_without_replacing_body_canvas():\n    source = (ROOT / "cyberppt" / "stage02_handoff.py").read_text(encoding="utf-8")\n    assert '"body_image_canvas": dict(BODY_CANVAS)' in source\n    assert '"full_slide_design_context": default_full_slide_design_context().to_dict()' in source\n    assert '"title_render_mode": "external_text_layer"' in source\n''',
    encoding="utf-8", newline="\n",
)

run(
    "python", "-m", "pytest", "-q",
    "tests/test_full_slide_context.py",
    "tests/test_full_slide_prompt_context.py",
    "tests/test_visual_thesis.py",
    "tests/test_text_capacity_v2.py",
    "tests/test_visual_medium_prompt_v2.py",
)

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", handoff, page, ir, artifact, renderer, contract, "tests/test_full_slide_prompt_context.py")
if run("git", "diff", "--cached", "--quiet", check=False).returncode != 0:
    run("git", "commit", "-m", "stage2-v3: add full-slide design context to production chain")
    run("git", "push", "origin", "HEAD:feature/stage2-artifact-contract-v3")
