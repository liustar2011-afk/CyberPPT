# 整页生图提示模块组装

## CyberPPT正式合同

CyberPPT把GPT Image输出视为可交付的视觉资产，不把它描述成普通插画请求。正式提示词只能由仓库`artifact-spec-v2`编译器从三项已审计来源投影：

1. `workbench/stages/02-handoff/stage02-handoff.json`：页面使命、核心判断、锁定文字和成品画布。
2. `visual/deck-visual-spec.json`：选中的视觉论点、业务关系、载体/场景策略、空间组织和文字归属。
3. 项目style lock：唯一视觉语言合同。

Skill不得自行拼接正式提示词，也不得把候选理由、作者版式备注、`trace_refs`、证据ID或文字ID送给ImageGen。

## 九段式artifact spec

正式编译结果严格按以下顺序，标题必须唯一且不得改序：

```text
[1. Deliverable / 成品规格]
[2. Communication goal / 页面使命｜不上屏]
[3. Visual thesis / 核心视觉论点｜不上屏]
[4. Evidence & relationships / 证据与关系｜不上屏]
[5. Visual carrier / 视觉载体｜不上屏]
[6. Composition / 空间组织｜不上屏]
[7. Art direction / 视觉语言｜不上屏]
[8. Typography & exact text / 文字资产合同]
[9. Hard constraints / 硬约束]
```

各段权威边界：

- `Deliverable`声明成品类型、2048×1024（2:1）正文画布、页面角色及标题/页码/Logo/页脚等外部PPT层。
- `Communication goal`只解释页面要完成的沟通任务，不作为可见文案。
- `Visual thesis`必须直接来自选中候选自己的`visual_thesis`，不是`core_judgment`的复制品。
- `Evidence & relationships`只使用已审计证据摘要和纯业务关系句；不得出现`E1`、`P07-T01`等后台ID。
- `Visual carrier`必须保留`execution_design`选中的`business_object`、`semantic_role`、`use_scene`与`scene_type`，不得由编译器重新猜测。
- `Composition`使用已选空间组织、阅读路径、焦点、关系编码、文字融合与连接语义，不导入未选候选。
- `Art direction`只读取style lock，不得写入或改写`semantic_graph`的`topology`、`focus_node`、`nodes`、`edges`，也不得改写`structural_decision`的`reading_sequence`、`text_bindings`；同一份`deck-visual-spec.json`换用不同style lock时，这些字段必须逐字保持一致，只有`Art direction`本身和携带的style lock哈希可以不同。Style09终端执行锁必须唯一且位于提示词绝对结尾。
- `Typography & exact text`是唯一可见文字合同，逐字来自`content_lock`、`final_text`和`generation_handoff.required_text`的一致交集。
- `Hard constraints`声明画布、模板禁绘、事实禁编、后台字段禁绘和逐页退化禁项。

审批稿、canonical prompt、manifest prompt和实际发送prompt必须复用这一编译结果。用户可以在审批阶段修改完整九段式prompt，但进入manifest前仍必须通过九段结构、可见文字、后台ID和Style09终端锁校验；审批后不得追加enrichment或另一套风格/构图模块。

## 旧结构预览

以下命令仍可为独立Skill调用或旧项目生成`generation-prompts.md`结构预览：

```bash
python3 scripts/build_generation_prompt.py deck.json --output deck_prompts.md
python3 scripts/build_generation_prompt.py deck.json --page 7 --output page_07_prompt.md
```

该输出仅用于人工结构审阅和兼容诊断，不是CyberPPT生产提示词来源，不得追加到`artifact-spec-v2`结果中。
