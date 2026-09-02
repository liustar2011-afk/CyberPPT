"""Persist reviewable ImageGen handoff prompts and delivery diagnostics."""

from __future__ import annotations

from pathlib import Path

from cyberppt.commands.script_gate import stage_script
from cyberppt.page_artifact_spec import load_project_page_artifact_specs
from cyberppt.script_quality_contract import parse_script_markdown
from scripts.imagegen_pipeline.build_transaction import atomic_write_text, build_lock
from scripts.imagegen_pipeline.prompt_compiler import (
    ARTIFACT_PROMPT_COMPILER,
    DEFAULT_PROMPT_COMPILER,
    PROMPT_COMPILERS,
    validate_prompt_compiler,
)
from scripts.imagegen_pipeline.prompt_diagnostics import (
    PagePromptDiagnostics,
    analyze_prompt,
    write_batch_diagnostics,
    write_compiler_comparison,
)
from scripts.imagegen_pipeline.script_parser import (
    load_page_missions,
    load_page_visual_contexts,
    load_page_visual_intent_overrides,
)
from scripts.imagegen_pipeline.handoff.contracts import VISUAL_INTENT_TEMPLATES
from scripts.imagegen_pipeline.handoff.presentation import PresentationDecision
from scripts.imagegen_pipeline.handoff.prompt import compile_page_prompt
from scripts.imagegen_pipeline.handoff.text import diagnostic_onscreen_text


_page_missions = load_page_missions
_page_visual_contexts = load_page_visual_contexts


def _page_visual_intent_overrides(project: Path) -> dict[str, dict[str, str]]:
    """Compatibility wrapper backed by the shared Stage 01 parser."""

    allowed = {
        "visual_intent_type",
        "semantic_intent_type",
        "visual_proof",
        "visual_carrier",
        *VISUAL_INTENT_TEMPLATES["judgment_evidence"].keys(),
    }
    return load_page_visual_intent_overrides(project, allowed_fields=allowed)


def write_chapter_handoff(
    *,
    project: Path,
    script: Path,
    style_lock: Path,
    pages: list[int],
    batch_name: str,
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
    compare_with: str | None = None,
    visual_structure_mode: str = "off",
    text_render_mode: str | None = None,
) -> dict[str, Path]:
    # stage_script() resolves the project root internally, so page outputs in
    # `outputs` below come back as fully-resolved paths. Resolve project here
    # too so every path this function returns (batch/diagnostics/comparison/
    # gate included) is anchored the same way -- otherwise a symlinked path
    # component (e.g. macOS /var -> /private/var) makes some returned paths
    # resolved and others not, breaking any relative_to()/equality comparison
    # against them.
    project = project.expanduser().resolve()
    prompt_compiler = validate_prompt_compiler(prompt_compiler)
    if compare_with is not None and compare_with not in PROMPT_COMPILERS:
        raise ValueError(f"unsupported comparison compiler: {compare_with}")
    if visual_structure_mode not in {"off", "review"}:
        raise ValueError("visual_structure_mode must be 'off' or 'review'")
    document = parse_script_markdown(script.read_text(encoding="utf-8"))
    by_num = {int(page.page_id[1:]): page for page in document.pages}
    missions = _page_missions(project)
    use_legacy_visual_context = (
        prompt_compiler != DEFAULT_PROMPT_COMPILER
        or visual_structure_mode == "review"
    )
    visual_contexts = _page_visual_contexts(project) if use_legacy_visual_context else {}
    visual_intent_overrides = (
        _page_visual_intent_overrides(project) if use_legacy_visual_context else {}
    )
    if ARTIFACT_PROMPT_COMPILER in {prompt_compiler, compare_with}:
        from cyberppt.commands.visual_structure_stage import assert_visual_structure_ready

        assert_visual_structure_ready(project, script)
    artifact_specs = (
        load_project_page_artifact_specs(project, style_lock=style_lock)
        if ARTIFACT_PROMPT_COMPILER in {prompt_compiler, compare_with}
        else {}
    )
    out_dir = project / "workbench" / "prompts" / "imagegen"
    out_dir.mkdir(parents=True, exist_ok=True)

    if prompt_compiler == ARTIFACT_PROMPT_COMPILER:
        compilation_rules = [
            "- 每页提示词由通过审计的 Stage 02 handoff、deck visual spec 与 style lock 投影生成。",
            "- 九段顺序固定：成品规格、页面使命、视觉论点、证据关系、视觉载体、空间组织、视觉语言、文字资产、硬约束。",
            "- 上屏文字逐字来自 content lock；不注入证据编号、文字 ID、源材料、作者构图备注或额外 enrichment。",
            "- 审批稿、canonical prompt 与 manifest 必须复用同一编译结果。",
        ]
    elif prompt_compiler == "content-first-v1":
        compilation_rules = [
            "- 每页独立完整，可直接送入 ImageGen，不依赖批次级公共提示。",
            "- 送入：页面任务、核心判断、主导关系标签、锁定关键文字、完整上屏与页面语义关系、画布尺寸，以及所选风格的气质与配色。",
            "- 不送入：源材料全文、完整事实边界或重复设计理论。",
            "- 不送入：证据编号、讲解提示、文字取舍、图片数量或后期制作规则。",
            (
                "- 默认不送入视觉载体、视觉中心、空间组织、本页避免、视觉证明等构图指导；本批次已显式开启审阅模式，以下页面仅注入通过结构合同生成的构图模块。"
                if visual_structure_mode == "review"
                else "- 不送入：视觉载体、视觉中心、空间组织、本页避免、视觉证明等任何构图/画法指导。"
            ),
            "- 页面任务、核心判断与主导关系只用于理解业务关系；锁定关键文字逐字准确，完整上屏内容均需进入 full 图。",
        ]
        if visual_structure_mode == "review":
            compilation_rules.extend(
                [
                    "- 已显式启用视觉结构审阅模式：在内容锁定之后加入主导关系、空间组织、阅读路径、载体和退化禁项。",
                    "- 该模式只生成待审阅提示词，不代表视觉结构已获人工批准，也不得自动进入 ImageGen。",
                ]
            )
    else:
        compilation_rules = [
            "- 送入：页面使命、核心判断、上屏文字，以及页面级视觉意图。",
            "- 不送入：边界/Boundary/禁止项、完整文字稿、取舍说明、证据映射、证据编号、视觉结构、讲解提示。",
            "- 页面使命、核心判断与页面级视觉意图只作为理解和构图上下文；不要把字段名或说明文字渲染到画面，正文文字以“上屏文字”为准。",
        ]

    review_parts: list[str] = [
        f"# ImageGen 送图脚本审阅稿 · {batch_name}",
        "",
        "> 状态：等待用户修改或批准。未经批准不得进入 ImageGen。",
        f"> 源脚本：`{script.as_posix()}`",
        f"> 风格锁定：`{style_lock.as_posix()}`",
        f"> Prompt compiler: `{prompt_compiler}`",
        f"> Visual structure mode: `{visual_structure_mode}`",
        f"> Text render mode: `{text_render_mode or 'style default'}`",
        "",
        "## 编入规则",
        "",
        *compilation_rules,
        "- 封面/目录/章节过渡/封底：不生成正文区 ImageGen，由模板层承载。",
        "",
    ]
    outputs: dict[str, Path] = {}
    content_prompts: list[str] = []
    diagnostics: list[PagePromptDiagnostics] = []
    prior_decisions: list[PresentationDecision] = []
    prior_semantic_carriers: list[str] = []
    comparison_diagnostics: list[
        tuple[PagePromptDiagnostics, PagePromptDiagnostics]
    ] = []

    for page_number in pages:
        page = by_num[page_number]
        if page.page_type != "content":
            review_parts.extend(
                [
                    f"## 第{page_number}页：{page.title or page.page_type}",
                    "",
                    f"- 页面类型：`{page.page_type}`",
                    "- 结论：本页不生成正文区 ImageGen；标题/章节字由模板文字层输出。",
                    "",
                ]
            )
            continue

        compiled = compile_page_prompt(
            page,
            style_lock,
            page_mission=missions.get(page.page_id, ""),
            visual_context=visual_contexts.get(page.page_id),
            visual_intent_override=visual_intent_overrides.get(page.page_id),
            prompt_compiler=prompt_compiler,
            prior_decisions=tuple(prior_decisions),
            visual_structure_mode=visual_structure_mode,
            prior_semantic_carriers=tuple(prior_semantic_carriers),
            text_render_mode=text_render_mode,
            artifact_spec=artifact_specs.get(page_number),
        )
        if compiled.presentation is not None:
            prior_decisions.append(compiled.presentation)
        if compiled.semantic_structure is not None:
            prior_semantic_carriers.append(
                str(compiled.semantic_structure["visual_carrier"]["selected"])
            )
        prompt = compiled.prompt
        content_prompts.append(prompt)
        selected_diagnostics = PagePromptDiagnostics(
            page_id=page.page_id,
            title=page.title or page.page_id,
            metrics=analyze_prompt(
                prompt,
                onscreen_text=diagnostic_onscreen_text(
                    page,
                    prompt_compiler,
                ),
            ),
            build_metadata=compiled.build_metadata(),
        )
        diagnostics.append(selected_diagnostics)
        if compare_with and compare_with != prompt_compiler:
            comparison = compile_page_prompt(
                page,
                style_lock,
                page_mission=missions.get(page.page_id, ""),
                visual_context=visual_contexts.get(page.page_id),
                visual_intent_override=visual_intent_overrides.get(page.page_id),
                prompt_compiler=compare_with,
                prior_decisions=tuple(prior_decisions[:-1]),
                visual_structure_mode="off",
                text_render_mode=text_render_mode,
                artifact_spec=artifact_specs.get(page_number),
            )
            comparison_page = PagePromptDiagnostics(
                page_id=page.page_id,
                title=page.title or page.page_id,
                metrics=analyze_prompt(
                    comparison.prompt,
                    onscreen_text=diagnostic_onscreen_text(
                        page,
                        compare_with,
                    ),
                ),
                build_metadata=comparison.build_metadata(),
            )
            if prompt_compiler == "legacy":
                comparison_diagnostics.append(
                    (selected_diagnostics, comparison_page)
                )
            else:
                comparison_diagnostics.append(
                    (comparison_page, selected_diagnostics)
                )
        draft_source = out_dir / f"_tmp_slide-{page_number:02d}-imagegen.md"
        with build_lock(out_dir, f"{batch_name}-p{page_number:02d}"):
            atomic_write_text(draft_source, prompt)
        staged = stage_script(
            project,
            slide=page_number,
            kind="imagegen",
            phase="draft",
            source=draft_source,
            note=f"{batch_name} imagegen handoff draft for review",
        )
        draft_source.unlink(missing_ok=True)
        outputs[page.page_id] = staged
        review_parts.extend(
            [
                f"## 第{page_number}页：{page.title or page.page_id}",
                "",
                *(
                    [
                        (
                            "- 结构分类对照：现行生产关系 "
                            f"`{compiled.relation}` → 新审阅关系 "
                            f"`{compiled.semantic_structure['intent']['primary_intent']}`；"
                            + (
                                "需人工确认后方可切换。"
                                if compiled.relation
                                != compiled.semantic_structure["intent"]["legacy_intent"]
                                else "兼容映射一致。"
                            )
                        ),
                        "",
                    ]
                    if compiled.semantic_structure is not None
                    else []
                ),
                prompt,
                "",
            ]
        )

    batch_path = out_dir / f"{batch_name}-imagegen-review.md"
    with build_lock(out_dir, f"{batch_name}-batch"):
        atomic_write_text(batch_path, "\n".join(review_parts).rstrip() + "\n")
    outputs["batch"] = batch_path
    diagnostics_path = out_dir / f"{batch_name}-imagegen-diagnostics.json"
    write_batch_diagnostics(
        diagnostics_path,
        diagnostics,
        batch_name=batch_name,
    )
    outputs["diagnostics"] = diagnostics_path
    if comparison_diagnostics:
        comparison_path = out_dir / f"{batch_name}-imagegen-compiler-comparison.json"
        write_compiler_comparison(
            comparison_path,
            comparison_diagnostics,
            batch_name=batch_name,
        )
        outputs["comparison"] = comparison_path

    gate = project / "workbench" / "stages" / "02-imagegen" / f"{batch_name}-imagegen-script-gate.md"
    gate.parent.mkdir(parents=True, exist_ok=True)
    with build_lock(gate.parent, f"{batch_name}-gate"):
        atomic_write_text(
            gate,
            "\n".join(
                [
                    f"# ImageGen 送图脚本门禁 · {batch_name}",
                    "",
                    f"- batch_review: `{batch_path.as_posix()}`",
                    "- status: waiting_for_user_modify_or_approve",
                    "- rule: 用户批准前不得调用 ImageGen / final-script-pages --production-build",
                    "",
                    "## 请回复",
                    "",
                    "1. **批准送图脚本**（可指定页段）→ 将对应页 stage 为 final 并登记 approve-script 后再生图",
                    "2. **修改第N页** → 给出改法，返工该页 prompt 后再审",
                    "",
                ]
            ),
        )
    outputs["gate"] = gate
    return outputs


__all__ = (
    "_page_missions",
    "_page_visual_contexts",
    "_page_visual_intent_overrides",
    "write_chapter_handoff",
)
