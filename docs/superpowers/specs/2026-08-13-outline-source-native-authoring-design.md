# Outline Source-Native Authoring Design

## Goal

Make a formal Stage 01 Outline simultaneously preserve the source document's first-level chapter structure, expose the author-facing page judgment, and prove that every audience-facing judgment is supported by its declared evidence.

## Problem

The Stage 00 semantic contract preserves source-native chapters and the current Outline audit validates `core_message` derivation.  However, an author-facing judgment can live in an uncontracted field and therefore escape derivation checks.  A formal Outline can also replace source chapter titles with editorial labels without retaining a first-class mapping back to its source section.  Finally, an omitted attachment/detail records only omission rationale, not its intended downstream use.

## Design

### 1. Source-native chapter contract

Every non-template chapter page in a strict semantic Outline must declare:

```json
{
  "chapter_id": "C1",
  "title": "第一章　总体概述",
  "source_section_node_id": "N001",
  "source_section_title": "第一章　总体概述",
  "editorial_chapter_label": "合作必要性与共识边界"
}
```

`title` and `source_section_title` must equal the referenced Stage 00 top-level `section_node.source_heading`; `editorial_chapter_label` is optional and may not substitute for the source title.  The sequence of mapped core section nodes must equal the source model's core top-level section order.  Detail sections, including appendices, remain subject to the existing disposition contract rather than this chapter-page requirement.

### 2. Editorial judgment contract

Content pages may declare `editorial_judgment` only with a corresponding `editorial_judgment_derivation`:

```json
{
  "editorial_judgment": "合作事项应在真实条件下验证后再转入运营。",
  "editorial_judgment_derivation": {
    "source_refs": ["ST0121", "ST0133"],
    "supporting_statements": ["..."],
    "derivation": "...",
    "introduced_relations": [],
    "introduced_modalities": []
  }
}
```

The derivation uses the same source-subset, semantic-strength, relation-strength and modality rules as `core_message_derivation`.  It is optional for compatibility; if an Outline supplies `editorial_judgment`, its derivation becomes mandatory.  No legacy arbitrary author-judgment field is read by the audit.

### 3. Argument-chain and evidence-role contracts

When `editorial_authoring_status=author_edited`, `argument_chain` becomes a list of one or more steps:

```json
[{"statement": "真实试点验证价值与边界", "relation": "supports", "source_refs": ["ST0121", "ST0133"]}]
```

`evidence_roles` becomes a list of role records:

```json
[{"role": "claim", "source_refs": ["ST0121", "ST0133"]}]
```

All refs must be non-empty members of `page.source_refs`.  At least one `claim` record must cover the editorial-judgment derivation sources.  Existing dictionary-shaped evidence roles remain accepted only for non-strict/legacy Outlines.

### 4. Retained-detail disposition

`intentional_omission` dispositions receive optional downstream metadata:

```json
{
  "retained_for": ["page_script", "implementation_plan"],
  "related_page_ids": ["p27", "p28"],
  "source_heading_path": ["附件三　合作事项成熟度评估要点"]
}
```

For a strict author-edited Outline, intentionally omitted source nodes must contain one non-empty `retained_for` value; `related_page_ids` must name existing pages when supplied.  This does not force attachments on screen or create workflow artifacts.

## Boundaries

- Do not change Stage 00 extraction, semantic node generation or Source Truth compilation.
- Do not infer editorial judgments, chapter labels or retained destinations in the compiler.
- Do not require detail/appendix sections to become chapter pages.
- Keep v1 and non-author-edited Outline compatibility.

## Verification

Add unit tests for all new rejection and pass cases in `test_outline_contract.py` and `test_source_argument_model.py`; rerun the Stage 01 contract suite and use the current V16 project as a read-only regression fixture after its Outline is updated in a later implementation task.
