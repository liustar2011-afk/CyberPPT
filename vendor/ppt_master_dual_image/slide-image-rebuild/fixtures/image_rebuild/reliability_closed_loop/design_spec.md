---
kind: project_design_spec
workflow: slide-image-rebuild
---

# Design Spec

## Template Overview

Rebuild `6 电力领域数据基础设施为可靠性成果深化应用提供受控承接底座` as a native editable PPT slide from the supplied reference image. Use the reference for layout and visual fidelity; final visible text must come from `content_mapping.json`.

## Canvas

| Field | Value |
| --- | --- |
| Format | 16:9 |
| Width | 1280 |
| Height | 720 |
| Safe margin | 48 |

## Color Scheme

| Token | Value |
| --- | --- |
| Background | #FFFFFF |
| Primary | #0A3580 |
| Accent | #2E7FD6 |
| Border | #2F6EC4 |
| Text | #111827 |

## Typography

| Token | Value |
| --- | --- |
| Font family | Microsoft YaHei |
| Tone | corporate_blue |
| Density | reference |

## Page Structure

| Zone | Role | Component | Position | Ratio box |
| --- | --- | --- | --- | --- |
| zone_title | page_title | title_block | title | 0.0297,0.0222,0.9406,0.0778 |
| zone_guidance | design_guidance | guidance_banner | guidance | 0.0297,0.1194,0.9406,0.1056 |
| zone_stage_01 | process_step | chevron_column | stage 1 chevron + body | 0.0297,0.2333,0.1805,0.4972 |
| zone_stage_02 | process_step | chevron_column | stage 2 chevron + body | 0.2195,0.2333,0.1805,0.4972 |
| zone_stage_03 | process_step | chevron_column | stage 3 chevron + body | 0.4094,0.2333,0.1805,0.4972 |
| zone_stage_04 | process_step | chevron_column | stage 4 chevron + body | 0.6,0.2333,0.1805,0.4972 |
| zone_stage_05 | process_step | chevron_column | stage 5 chevron + body | 0.7898,0.2333,0.1805,0.4972 |
| zone_footer | operating_principles | footer_summary_band | footer summary | 0.0297,0.7417,0.9406,0.0944 |

## Content Outline

| Field | Value |
| --- | --- |
| Title | 6 电力领域数据基础设施为可靠性成果深化应用提供受控承接底座 |
| Intro | 电力领域数据基础设施在可靠性场景中的价值，体现在把可靠性资源、规则、授权、计算、结果和反馈统一组织起来，形成边界清晰、过程留痕、结果可用的运行机制。 |
| Takeaway | 数据基础设施解决的不是“拿数据”，而是把可靠性成果在安全边界内组织成可运行、可复用、可交付的场景机制。 |

| Zone | Title | Body | Result |
| --- | --- | --- | --- |
| zone_stage_01 | 资源目录化 | 建立可靠性数据目录、指标目录、规则目录、成果目录和产品目录，明确资源来源、责任主体、质量状态、授权状态和适用场景。 |  |
| zone_stage_02 | 规则工程化 | 把指标口径、评价规程、采集规范、质量校核逻辑转化为字段、规则、模板和计算流程。 |  |
| zone_stage_03 | 受控计算 | 支持汇总统计、规则计算、质量校核、本地计算、可信执行和结果生成，敏感明细保持在原有管理边界内。 |  |
| zone_stage_04 | 结果出证 | 输出分析报告、专题评价、诊断结论、风险标签和核验结果，通过版本留痕和出证审计保障可复核。 |  |
| zone_stage_05 | 服务运营 | 将服务反馈、整改结果、案例复盘回流到指标基准库、规则模型库、案例知识库和产品库。 |  |

## Icon Style

- Use editable semantic vector icons for functional icons.
- Keep page numbers, decorative badges, and chrome labels outside `icon_reconstruction.icons[]` unless they carry semantic icon meaning.
- Add `data-icon-id` only for icons declared in `layout_reference.json`.

## Editability

| Policy | Value |
| --- | --- |
| Native editable | title, body_text, cards, arrows, tables, simple_charts |
| Image allowed | logo, screenshot, complex_icon, decorative_pattern |
| Never flatten full slide | True |
| Reference text trust | untrusted_for_final_text |
