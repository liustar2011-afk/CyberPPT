# Outline Authoring Spec

`authoring-spec.json` is the only structured input that can promote the official generator's candidate to `author_edited`. It is an authoring input, not a second semantic source.

Generate the blank source-bound template with:

```bash
python scripts/prepare-authoring.py <semantic-dir> --outline-dir <outline-dir> -o <authoring-spec.json> --force
```

The preparer records source heading IDs, direct fact IDs, argument-node IDs, concept IDs and relation IDs as lookup context. Editorial fields remain blank; the preparer does not create a communication goal, audience, scenario, action or core judgment.

空白模板不能直接作为正式 Outline 编译输入。必须由作者补齐 deck 级交流约束、页面使命、核心判断、证据取舍和删除测试；生成器会在写出产物前拒绝不完整的作者化输入。

Minimal shape:

```json
{
  "deck": {
    "audience": "明确的交流对象",
    "purpose": "本次交流目的",
    "working_title": "源材料标题",
    "core_question": "交流对象需要回答的问题？",
    "deck_thesis": "源材料支持的全篇主张"
  },
  "pages": {
    "sec-0002": {
      "audience_question": "本页独立回答的问题？",
      "page_mission": "本页在全篇中的责任。",
      "key_judgment": "来源支持的单句核心判断。",
      "non_substitutable_value": "删除或合并本页会丢失什么。",
      "judgment_basis": "source_explicit",
      "argument_role": "background",
      "must_not_include": ["相邻页内容"],
      "reserved_for_later": [],
      "split_risk": "low",
      "transition_from_previous": "承接什么。",
      "transition_to_next": "交给什么。",
      "excluded_from_onscreen": [],
      "authoring_decisions": {
        "deletion_test": "删除测试结论。",
        "evidence_selection": "证据取舍结论。",
        "attachment_disposition": "not_applicable"
      }
    }
  },
  "planning": {
    "page_budget": {"target": 24, "min": 20, "max": 28},
    "merge_groups": [],
    "default_attachment_disposition": "trace_only"
  }
}
```

`pages` must cover every generated content heading; in the prepared template this means every selected content heading, while attachment headings remain lookup entries and are omitted when their disposition is `trace_only`. A `merge_groups` entry has `primary_source_heading_id`, `source_heading_ids` and a rationale. The generator owns `page_id`, order, source titles, source heading IDs, direct evidence IDs, page type, semantic-node status/weight/role and source-derived judgment derivation. The spec may not override those source-bound fields. Attachment pages must declare `attachment_disposition` as `main_deck`, `appendix`, or `trace_only`; `main_deck` additionally requires `attachment_promotion_rationale`.
