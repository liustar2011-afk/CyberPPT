# Changelog

## 2.3.0 — 2026-08-07

### Fixed

- 修复模块间逻辑关系"判断在Gate 4、丢弃在Gate 5/送图"的断链：`decision_relationship`、`reading_path`、`relationship_encoding`等视觉字段现在必须继承Gate 4逻辑骨架的判断，Gate 5禁止独立重新判定关系（`SKILL.md`、`references/09-visual-design.md`、`references/07-logic-and-parallelism.md`）。
- 2.1.0起"送图端不再接收逻辑骨架"被误读为"关系可以只留在逻辑骨架里"；本版本明确该字段不进入送图契约只代表其原文不作为图像提示词，其记录的关系必须已经体现在上屏文字与页面视觉结构中（`references/16-single-page-imagegen-contract.md` 3.4/3.4a/3.6）。

### Added

- `references/06-on-screen-text.md`新增"顺序与关系信号"：一级模块超过3个且关系为因果/递进/流程/分层/闭环时，模块标题或上屏正文必须出现①②③④、一/二/三/四或`→`/随之等顺序信号，并给出真实反例（业务演进/协同需求/现实制约/基础需求四个并列标题、有语义角色但无顺序信号）。
- `validate_script.py`新增两项校验：`MISSING_ORDER_SIGNAL`（模块数超过阈值但标题无顺序信号）、`LOGIC_SKELETON_NOT_ONSCREEN`（逻辑骨架记录了顺序/因果链但上屏文字无对应信号）；`config/quality-rules.yaml`新增`min_order_signal_modules`阈值。
- `module_blocks()`模块边界识别从只认`###`扩展为同时识别`####`，修复真实项目里模块小节写成`####`嵌套层级时被错误合并成单一模块、导致模块计数和关系校验失真的问题。
- `references/13-quality-gates.md` Gate D、`ppt-visual-structure-designer/SKILL.md`"建立页级语义模型"同步更新措辞，统一为"核对并继承上游关系，不独立创设"。

### Root cause

实际项目`power-data-infrastructure-cooperation-v12-20260807`的`script-final.md`中，31页里有超过20页命中`LOGIC_SKELETON_NOT_ONSCREEN`，证实这不是个别页面疏漏，而是2.1.0以来一直存在的系统性问题。

## 2.2.0 — 2026-08-06

- 将页级视觉结构与全局视觉风格解耦。
- 送图脚本新增清洗后的页面视觉结构段。
- 默认从总仓库 `visual/ACTIVE-STYLE.md` 注入视觉风格，并记录版本与哈希。
- 保留旧版模板风格文件作为独立使用兼容后备。

## 2.1.0 — 2026-08-04

### Added

- 单页ImageGen送图契约规范；
- 模板页 `cover / contents / chapter / closing` 标准类型映射；
- 内容页锁定关键文字自动提取，按原序去重并默认限制7项；
- 2048×1024、2:1正文区送图尺寸配置；
- 标题、副标题、页码和Logo模板层禁绘合同；
- `validate_imagegen_contract.py` 单页送图契约校验器；
- 实际33页ImageGen送图审阅稿黄金样例；
- 单页和页段选择编译参数。

### Changed

- 明确 `10-script-final.md` 为正式完整主产物，送图脚本仅为派生产物；
- `build_generation_prompt.py` 改为输出内容优先的单页送图格式；
- 送图端不再接收证据映射、演讲者备注、逻辑骨架和视觉结构字段；
- 完整脚本校验器改为适配“主判断＋完整文字稿＋文字取舍说明＋证据映射＋页级合同注释”的真实格式；
- 更新完整脚本模板和示例工程。

## 2.0.0 — 2026-08-04

- 增加页面主题唯一归属与边界矩阵；
- 增加上屏文字逻辑、分类维度和跨页重复校验；
- 增加视觉意图、构图语法和完整视觉合同；
- 增加完整项目校验和机读JSON产物。

## 1.1.0 — 2026-08-03

- 增加模块标题和细项小标题格式；
- 增加正文密度和基础视觉可执行性校验。
