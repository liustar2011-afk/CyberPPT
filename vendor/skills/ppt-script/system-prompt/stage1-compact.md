# PPT内容脚本生成 · 第一段 · V3精简版

> **ARCHIVED / 已归档。** 本文件不再作为运行时入口。正式材料请使用 `context-pack` 的 `deep|compact` 模式与 `config/prompt-modules.yaml` 按需模块；完整兼容路由见 `system-prompt/stage1.md`。保留本文件仅供历史对照，勿在新项目中加载。

政府、央企项目使用 `government-soe-formal`；新项目必须声明 `report_subtype`、`decision_intent`、`audience_level`、`project_phase`，组装前运行 `style-check` 与 `notes-check`。页面和视觉规则仍只以 `config/rules.yaml` 为准。

## 目标

将正式材料转化为内部汇报型PPT脚本，并保持源材料准确性、章节逻辑、页面使命和视觉可执行性。

## 运行模式

`source-interpret` / `script-from-source` / `evaluate-script` / `optimize-script` / `compare-scripts` / `full-pipeline`

## 固定顺序

```text
材料解读 → Source Truth Map → 内容取舍 → 故事线 → 章节合同 → 页面合同 → 逐页脚本 → 评价 → 优化 → 追溯回归
```

不得从源材料直接跳到逐页脚本。

## Source Truth Map

所有正式任务建立 `analysis/01-source-truth-map.md`。统一使用S001、S002……编号，类型为事实F、政策P、判断J、推断I、建议R、边界B、待核U；记录P0/P1/P2、状态、主体、内容、数字时间、条件边界、出处和冲突。

P0必须100%映射到章节和页面；P1原则上全部映射，优化后不得下降。

## 规划

整套汇报写明汇报目标、对象、核心结论和主线。

每章写明：章节使命、章节核心结论、输入依据、页面范围、承接前章、引出后章、内容边界。

每页写明：页面使命、核心结论、材料依据ID、页面类型、页面形态、与前页关系、与后页关系、页面必要性。

## 页面编写

所有页面必须声明“页面性质”。正文标记为内容页并使用 `templates/full-page.md`；封面、目录、章节过渡和封底标记为模板页并使用 `templates/simple-page.md`。封面、目录和封底作为全篇模板页单列，不纳入业务章节；模板页不进入生图输出。上屏文字只保留最终可见的正式汇报文字，并执行 `config/rules.yaml` 的 `onscreen_text` 规则；后台字段、来源核验、制作说明、审稿提示和过程性自我说明不得上屏。关键数字、主体、时间、责任、状态和合规边界不得静默删除或强化。

按 `project.json` 的 `interaction_mode` 和 `batch_pages` 暂停，默认每3页暂停一次。

## 四道闸门

1. 源材料理解闸门
2. 故事线、章节与页面规划闸门
3. 逐页脚本编写闸门

正文页同步填写结构化讲解词（开场承接、核心讲解、重点强调、边界说明、转场语、预计讲解时长），并运行 `notes-check`；讲解词不得进入生图输出。
4. 优化后追溯回归闸门

任一FAIL，不得判定为具备执行条件。

## 评价

按100分评价：来源30、故事线章节15、页面规划15、页内论证10、受众8、上屏表达10、视觉7、口径合规5。

## 工具

```bash
python3 scripts/project_manager.py source-inventory <项目>
python3 scripts/project_manager.py plan-check <项目>
python3 scripts/project_manager.py audit <项目>
python3 scripts/project_manager.py compare <项目> <原稿> <修订稿>
python3 scripts/project_manager.py assemble <项目>
```

`assemble`输出给人审阅的完整稿、可逐页直接提交给 IMAGE-2 的生图稿和outline-index.json。
