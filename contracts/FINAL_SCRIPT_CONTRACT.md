# CyberPPT Final Script Contract — Stage 02 Consumer Profile v1

CyberPPT-Stage02 treats the approved final script as the sole content authority for visual production.

## Required page semantics

A content page must expose, directly or through the accepted parser aliases:

- page id and page type;
- page title;
- page mission;
- core message;
- on-screen text;
- optional subtitle;
- optional full copy;
- optional visual structure;
- optional speaker notes;
- optional source references.

Canonical CyberPPT-Script Markdown headings include:

- `## Pxx 页面标题`
- `- 页面类型：...`
- `- 页面标题：...`
- `- 页面使命：...`
- `- 核心结论：...`
- `- 主论证链：...`
- `### 完整文字稿`
- `### 上屏文字`
- `### 视觉结构`
- `### 演讲者备注`
- `### 内容来源`

## Relationship semantics

The producer owns business meaning. Stage 02 may project explicit visual-structure statements into internal business-semantic families such as:

- `evidence_supports`
- `problem_response`
- `peer_classification`
- `layer_supports`
- `optional_progression`
- `semantic_mapping`
- `comparison`
- `causes`
- `sequence_before`
- `feeds_back_to`
- `bounded_by`
- `covers`
- `transforms_to`

These relation names are not visual topologies. Stage 02 combines relation semantics, cardinality, module structure and authored visual structure to form a layout-neutral reading contract before the visual-structure designer selects topology/composition.

## Authority rules

- Stage 02 does not rewrite the approved final script.
- Legacy hidden `content_relations` remain higher-priority when explicitly present.
- Derived Stage 02 relationships record provenance as internal adapter output.
- Ambiguous pages stay reviewable; Stage 02 must not invent a business relation merely to satisfy a visual gate.

## Versioning

The Stage 02 consumer profile is versioned separately from CyberPPT-Script implementation versions. A producer upgrade does not require a Stage 02 upgrade when the final-script contract remains compatible.
