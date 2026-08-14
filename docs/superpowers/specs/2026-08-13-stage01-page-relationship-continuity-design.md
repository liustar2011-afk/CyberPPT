# Stage 01 页面关系连续性审计设计

## 目标

在既有 `Outline → script-audit` 主链中增加页面间关系与单页关系可读性审计，减少三类内容质量问题：

1. 相邻页面重复承担同一论证职责；
2. 前页提前写入后页专属机制、任务或结论；
3. 页面上屏模块只是并列罗列，未表达材料确定的因果、输入输出、主次、过程或闭环关系。

本设计只增强现有 Stage 01 写作与 `script-audit`。不新增审批文件、状态 JSON、哈希绑定、人工停点、平行目录或第二套工作流。

## 边界与复用

- 权威输入继续是 `outline.json`、`source-truth.json` 与 `script-final.md`。
- 页面既有字段继续提供判断依据：`page_mission`、`audience_question`、`must_not_include`、`content_relations`、`argument_role`、`core_message`、`上屏文字` 与 `视觉结构`。
- 问题继续写入现有 `script-audit` JSON/Markdown 输出，并使用已有 `failed_pages` 与 `retry_scope` 引导局部重写。
- 既有 `script-audit`、Outline 审计和 Stage 02 handoff 的职责不迁移：本功能不评价视觉版式，不生成新的视觉决策，也不替代 Stage 02 的锁定文字或业务关系交接校验。

## 审计模型

### 1. 页面关系摘要

为每个内容页在内存中构造关系摘要，不新增落盘产物：

- `entry_conditions`：由 `content_relations` 中本页消费的前置对象、动作、条件或问题组成；
- `page_transformation`：本页 `page_mission`、`core_message` 与主 `content_relation` 所描述的对象变化、判断或关系；
- `exit_handoffs`：本页形成并由后续页面继续消费的对象、结论、任务或边界；
- `excluded_scope`：既有 `must_not_include`；
- `visible_relation`：上屏模块和 `视觉结构` 是否表达与主关系同向的谓词、链条或层级。

抽取必须基于现有结构化关系和脚本字段；不得仅用标题关键词推断业务关系。

### 2. 跨页规则

- **重复职责**：相邻内容页的任务、核心消息和主关系实质相同，且未声明不同的论证职责时，报错并定位两页。
- **越界预支**：当前页的可见内容或完整文字稿实质落入下一页 `must_not_include` / 专属页面使命时，报错并定位应迁移的页面。
- **断裂承接**：本页的核心判断依赖前页未形成的对象、条件或结论，并且 Source Truth/Outline 未将其直接赋予本页时，给出警告；避免把合法的独立事实页误判为断裂。

### 3. 单页规则

- **关系未显性表达**：已声明主业务关系为因果、过程、输入输出、层级、协同或闭环，而上屏顶层模块与 `视觉结构` 都未出现可读的关系谓词或顺序/层级证据时，报错。
- **伪关系并列**：上屏模块只有抽象名词或同义分类，不能承载主关系中的主体—动作—对象时，报错。
- **证据与关系脱钩**：上屏模块表达的关系不在该页 `content_relations` 或来源支持范围内时，复用既有来源/合同审计，并在本规则中给出关系方向的改写建议。

## 严重级别与兼容性

- 直接违反 `must_not_include`、重复职责、以及声明关系在可见层完全缺失：`error`，进入 `failed_pages` / `retry_scope`。
- 仅可能存在承接断裂：`warning`，不阻断 Stage 01；报告需明确缺少何种前置输入。
- 模板页、章节页及没有 `content_relations` 的遗留兼容稿跳过关系可读性规则，不因缺少新字段失败。

## 改动位置

1. `cyberppt/script_quality_contract.py`：新增纯函数，构造页面关系摘要并生成 `ScriptQualityIssue`。
2. `audit_script_quality()`：在既有页面字段、来源和页面合同检查后调用单页与跨页关系审计。
3. `tests/test_script_quality_contract.py`：增加最小夹具和定向断言。
4. 必要时仅补充 `references/script-quality.md` / Stage 01 写作输入的简短规则，说明“先写关系骨架、再写模块”，不改变字段合同。

## 测试与验收

新增至少四类定向测试：

1. 相邻两页重复页面使命/主关系，返回可定位的阻断问题；
2. 当前页写入下一页明确排除的机制或任务，返回可定位的阻断问题；
3. 已声明过程或因果关系但上屏只有并列名词，返回关系未显性表达问题；
4. 现有合格严格 Outline/脚本夹具保持通过，模板页和遗留无关系页不产生新增阻断。

完成条件：定向测试通过；相关完整测试文件通过；不修改 Stage 01 的交互停点与产物目录；重新运行的 `script-audit` 只在现有报告中呈现问题。
