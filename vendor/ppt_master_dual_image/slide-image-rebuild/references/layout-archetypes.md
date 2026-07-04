# Layout Archetypes for Slide Image Rebuild

This file defines a small, reusable archetype library for Chinese business,
government, and SOE-style slide screenshots. Archetypes are advisory: they
help the Executor name and organize objects, but they do not force a page into
a template when confidence is low.

| Archetype | Use | Recognition signals | Required objects |
|---|---|---|---|
| `three_stage_goal_timeline` | 三阶段目标 / 路线图 | 3 dominant stage/card zones, horizontal sequence, stage labels such as short/mid/long term | title, 3 stage cards, 2 connectors |
| `policy_pathway` | 政策路径 / 建设路径 | 4+ process nodes, arrows/chevrons, optional bottom principle band | title, process nodes, chain connectors |
| `capability_matrix` | 能力矩阵 / 责任矩阵 | grid/table-like zones, row/column headings, repeated cells | title, row headers, column headers, matrix cells |
| `left_right_comparison` | 前后对比 / 方案对比 | two balanced columns or before/after panels | title, left panel, right panel, contrast labels |
| `four_quadrant_framework` | 四象限分析 | 2x2 structure, central axes or four equal quadrants | title, 4 quadrants, axis/labels when present |
| `kpi_dashboard` | 指标看板 | metric cards, numeric highlights, repeated KPI tiles | title, KPI cards, metric labels, values |
| `organization_architecture` | 组织架构 / 技术架构 | hierarchy/tree/layered platform blocks, parent-child links | title, hierarchy nodes, relationship connectors |
| `table_with_callouts` | 表格重点标注 | table-like region plus badges/arrows/highlight callouts | table, callouts, highlighted cells |

## Classification Policy

- Classification is lightweight and deterministic.
- `custom` is valid when signals are weak.
- `confidence < 0.65` must be treated as an editing hint only.
- The `required_objects` list is for SVG planning and review, not a hard gate.
- Do not use archetype classification to change user-provided text or page order.

## SVG Planning Contract

When available, `detected_layout_family.archetype` should be copied into
`svg_build_plan.json` and `svg_build_plan.md` so the Executor can keep stable
object names, reading order, connector semantics, and alignment expectations.
