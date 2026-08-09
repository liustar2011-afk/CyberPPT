# 整页生图提示模块组装

## 组装顺序

严格按以下顺序输出：

1. 内容和文字锁定。
2. 结构指引。
3. 连接关系。
4. 文字放置和标题区约束。
5. 上屏正文。
6. 外部风格来源引用。

结构字段名和说明文字不得被画进页面。结构模块不得复制风格正文。

## 结构指引模板

```text
[Structural guidance]
- Selected visual intent type: <visual_intent_type>
- Visual thesis: <visual_thesis>
- Decision relationship: <decision_relationship>
- Semantic focus: <kind> / <ref>
- Spatial grammar: <spatial_grammar>
- Semantic tags: <semantic_tags>
- Primary structure refs: <primary_refs>
- Secondary structure refs: <secondary_refs>
- Reading sequence: <reading_sequence>
- Text binding: <evidence_id> -> <target_ref> / <binding>
- Representation freedom: carrier=<carrier>; medium=<medium>; reason=<reason>
```

该模块只描述语义结构，不指定载体、媒介或风格。具体载体和媒介仅在来源明确约束时通过`representation_freedom`标记为`constrained`或`*_required`。

## 标题区

默认写明：

```text
Reserve the top title area for an external PowerPoint text layer. Do not draw the page title, subtitle, page number, logo, or template header inside the generated image.
```

正文是否在图中生成由`body_render_mode`决定。用户要求完整全图生图时，正文必须逐字提供，不使用省略。

## 媒介和文字

提示中必须说明：

- 所选媒介承担什么业务含义；媒介自由时不得提前指定。
- 哪些文字归属于哪些对象、动作、关系或结果。
- 哪些连接是主链，哪些只用邻接或边界表达。
- 媒介与文字不能形成两个互不关联的结构。

## 结构约束与风格来源

结构约束只描述结构退化，例如：

- keep one primary structure
- bind every P0 evidence unit
- do not duplicate one judgment as another primary region
- do not map bullet count directly to visual-object count

字体、字号、颜色、线条、边框、形状、人物表现、阴影和材质不得写入结构模块。只输出：

```text
[Style source]
<style_source_ref>
```

最终提示词编译器负责读取该来源并装配风格；视觉结构消费者不得把`[Style source]`当作构图正文导入。

## 生成器交接

JSON规格生成提示模块：

```bash
python3 scripts/build_generation_prompt.py deck.json --output deck_prompts.md
```

只生成某页：

```bash
python3 scripts/build_generation_prompt.py deck.json --page 7 --output page_07_prompt.md
```
