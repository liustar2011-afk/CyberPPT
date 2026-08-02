# 与ppt-script工作台的衔接

## 适用范围

用于将`ppt-script` V3.5.1及后续版本的已验证逐页脚本，传递到本Skill完成视觉结构设计。该衔接层不重新开展材料研究、故事线规划和页面分配，只继承上游真值、页面合同和终稿文字。

## 上游就绪条件

正式项目进入视觉阶段前应满足：

- 上游状态为`SCRIPT_VALIDATED`，不得仅因页面文件存在就视为就绪。
- 提纲页码、`page-contracts.json`页面集合和逐页脚本页面集合完全一致。
- 页面文件不含模板占位符、空字段和未完成页。
- Source Truth的Markdown与JSON已同步，P0事项具有主体、状态、边界和来源。
- 页面使命、核心结论、来源ID和页面必要性已经通过上游闸门。

任一条件不满足时，列出不一致项，不用视觉设计掩盖上游内容缺口。

## 推荐输入

按优先级读取：

1. `contracts/source-truth.json`：事实、状态、主体、数字和边界的最高权威。
2. `contracts/page-contracts.json`：页面使命、核心结论、来源ID、页面类型、前后页关系和必要性。
3. `output/script-imagegen.md`或已批准的逐页脚本：上屏终稿文字和既有业务关系。
4. `contracts/deck-decision.json`和`contracts/chapter-contracts.json`：整套叙事和章节职责。
5. `analysis/00-active-context.md`：发生歧义时回查，不替代原始材料。

演讲备注、后台字段、来源说明和过程性审查文字不得进入可见页面文字。

## 权威顺序

发生冲突时按以下顺序处理：

1. Source Truth中的事实、状态和边界。
2. 已批准页面合同中的页面使命与核心结论。
3. 已批准逐页脚本中的终稿文字。
4. 原脚本中的草图、视觉形式和构图建议。
5. 本Skill默认规则。

原脚本中的`visual_form`、草图和模块位置只是设计提示，不构成锁定结构；终稿文字、数据和业务关系默认严格锁定。

## 字段映射

| 上游字段 | 本Skill字段 | 处理规则 |
|---|---|---|
| `page_id` | `page_id` | 原样继承 |
| `page_mission` | `page_mission` | 原样继承，不改成排版任务 |
| `key_message`或`core_conclusion` | `core_judgment` | 原样继承或仅做不改义规范化 |
| `source_ids` | `content_lock.locked_items.source_ref` | 保持双向追溯 |
| `page_type` | `page_role` | 映射为最接近的页面角色 |
| `visual_form` | 候选构图提示 | 不直接锁定，必须重新经过视觉意图路由 |
| `previous_page_relationship` | 整套节奏和承接 | 用于避免重复构图和断链 |
| `next_page_relationship` | 整套节奏和承接 | 用于控制本页收束位置 |
| 逐页终稿文字 | `final_text`和`content_lock` | 默认`strict` |

## 项目输出位置

在上游项目内建议写入：

```text
visual/
├── deck-visual-spec.json
├── script-visual-structure.md
├── generation-prompts.md
└── validation-report.json
```

只有以下条件全部满足，项目才可从`SCRIPT_VALIDATED`进入`VISUAL_READY`：

- 上游页面集合与视觉规格页面集合一致。
- 每页具有一个视觉意图、一个主视觉载体和一个视觉中心。
- 所有锁定文字和来源ID均可追溯。
- Markdown和JSON视觉合同均通过校验。
- 整套重复构图、色彩角色和命名一致性已经检查。

## 推荐调用

```text
$ppt-visual-structure-designer
读取当前ppt-script项目的source-truth、deck/chapter/page contracts和已批准script-imagegen.md。
保持页面集合、页序、终稿文字、数字、状态、主体和边界不变，
将原有visual_form仅作为参考，重新完成整套视觉意图路由和页面构图，
把结果写入visual/目录，并运行Markdown与JSON校验。
```

## 不允许的降级

- 不因进入视觉阶段停止回查Source Truth。
- 不用“视觉优化”名义删除P0内容或改变事项状态。
- 不把页面合同中的主职能扩展为多个页面任务。
- 不将讲解词、来源ID、审核结论和后台元数据画到页面上。
- 不因上游构图建议存在就跳过三候选比较和视觉意图路由。
