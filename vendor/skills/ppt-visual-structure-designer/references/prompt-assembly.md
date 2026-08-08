# 整页生图提示模块组装

## 组装顺序

严格按以下顺序输出：

1. 内容和文字锁定。
2. 强制构图指引。
3. 实景锚点与图文融合。
4. 页面几何和阅读路径。
5. 上屏正文。
6. 全局视觉风格。
7. 禁止事项。

构图字段名和说明文字不得被画进页面。

## 强制构图指引模板

```text
[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.
[Prompt context] Page-specific visual intent (composition guidance only; do not render field names or instruction text)
- Selected visual intent type: <visual_intent_type>
- Visual thesis: <visual_thesis>
- Decision relationship: <decision_relationship>
- Dominant visual carrier: <dominant_visual_carrier>
- Recommended composition: <spatial_organization>
- Reading path: <reading_path>
- Industry scene anchor: <industry_scene_anchor>
- Text integration: <text_integration_method>
- Relationship encoding: <relationship_encoding>
- Avoid on this page: <avoid_on_this_page>
```

## 标题区

默认写明：

```text
Reserve the top title area for an external PowerPoint text layer. Do not draw the page title, subtitle, page number, logo, or template header inside the generated image.
```

正文是否在图中生成由`body_render_mode`决定。用户要求完整全图生图时，正文必须逐字提供，不使用省略。

## 场景和文字

提示中必须说明：

- 实景场景承担什么业务含义。
- 哪些文字贴近哪些对象或节点。
- 哪些连接是主链，哪些只用邻接或边界表达。
- 场景不能与文字分成两个独立区域。
- 不出现正面人物和可识别地点。

## 禁止事项

负面约束使用具体失败形态：

- no equal card wall
- no one-icon-per-bullet layout
- no disconnected left-text/right-image split
- no front-facing portrait
- no decorative dashboard UI
- no generic center circle with surrounding icons
- no dirty shadows or glowing arrows
- no tiny text below 12pt equivalent

不要使用“不要丑、不要普通”等不可执行描述。

## 生成器交接

JSON规格生成提示模块：

```bash
python3 scripts/build_generation_prompt.py deck.json --output deck_prompts.md
```

只生成某页：

```bash
python3 scripts/build_generation_prompt.py deck.json --page 7 --output page_07_prompt.md
```
