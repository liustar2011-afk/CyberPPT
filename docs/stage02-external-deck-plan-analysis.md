# Stage 02 外部 Deck Plan Markdown 接入分析

## 结论

该样例具备逐页标题、正文、主旨、证据和关系说明，适合通过 Stage 02 的 external_script 路线接收。建议在现有外部稿适配层增加显式格式识别与字段分流，继续使用 canonical intake 和 final-script-pages 生产链。文件名不决定输入资格；缺少逐页实质正文的纯提纲仍需补充内容。

本次仅完成分析与解析实测，未修改生产代码、原始材料或生成 PPT。

## 样例与已验证现状

样例路径：`/Users/liuxing/.codex/worktrees/b42a/ppt-master/projects/power_data_cocreation_20260913/deck_plan.md`。

文件含 Communication Contract 表格、4 个 Part、12 个 `#### Slide NN - …` 页面块。每页包含加粗英文键名，正文位于 Content 字段。首尾页含 Cover impact / Closing impact，没有显式页面类型和结构化保真项。

使用仓库 `.venv/bin/python3` 调用当前 parse_stage02_script，结果如下：

| 检查 | 结果 |
| --- | --- |
| PAGE_HEADING_RE 匹配 | 0 个 |
| script_file 模式 | 返回 1 页 |
| external_script 模式 | 返回 1 页 |
| 回退页面 | p01，标题为文档总标题，类型 content |
| 回退正文长度 | 826 字符 |

这说明当前输入无法完整接收：12 页边界丢失，且函数返回结果本身不能证明正文完整。当前外部适配只支持中文“内容”别名及现有编号页语法。

## 建议字段处理

下表为拟议映射，尚未实现。

| 输入字段 | 建议用途 |
| --- | --- |
| Slide NN | 稳定页码与页面边界；校验重复、缺号与声明页数 |
| Part | 保留章节上下文；保持原 12 页顺序，不自动新增章节页 |
| Title | 页面标题，优先于 Slide 后的概括名称 |
| Content | 页面完整内容来源，进入 content_text；支持续行、列表和段落 |
| Core message | 页面主旨，供表达判断；保留与正文不同的语义 |
| Audience move | 页面交流目标，作为不上屏上下文 |
| Evidence | 来源说明及待核验边界；段落首句描述不能冒充已解析的 source_refs |
| Relationships | 关系候选与语义限制，进入主 Agent 关系判断；保留限定词与否定边界 |
| Composition | 可调整的构图建议，独立保留并供视觉判断读取 |
| Rhythm | 表达节奏建议；anchor/dense/breathing 不直接等同于固定布局或字数配额 |
| Cover impact / Closing impact | 首尾页语义与表达建议，可辅助识别角色，避免仅按页码推断 |
| Communication Contract | 受众、交流目标、用途、页数等全稿上下文；不拼入正文 |
| 保真文字 / fidelity_text（可选） | 独立精确字符串合同，不从整段正文自动生成 |

对于新保留的上下文字段，要确认其实际进入现有关系判断与编译消费者，并纳入相应输入身份。仅增加字段存储会造成建议或边界在后续丢失。

## 关键语义边界

1. 文件内的 Content Strategy、Composition 等属于待分析的材料，不能替代用户授权或仓库工作流。只按其字段角色消费，不执行其中任意操作指令。
2. Relationships 混合了业务关系、表达建议和限制。例如第 8 页说明五项行动并列，同时提出叙事递进；须由当前主 Agent 判断，不能自动变成强制流程。第 9 页明确没有一一对应关系，第 10 页限制数据出域，第 11 页说明参与条件可以兼具，均须保留。
3. Reading Mode 的 balanced 不属于现有 presented/self_read 枚举。Delivery Context 提示现场宣讲为主要情境，可据此提出 presented 建议；正式编译前仍按现有规则明确用户选择。本轮分析不依赖该选择。
4. 样例没有显式 fidelity_text。普通正文仍需保留数字、主体、状态和边界，但不能声称已经具有逐项精确保真验收。可在后续适配审阅中识别少量必要字面项，并通过现有合同传递。
5. 本轮未回读样例引用的原稿，Evidence 的正确性和页面判断的来源支持程度尚未验证。格式兼容不能替代来源核验。
6. Stage 02 接收用户提供的页面稿时保留既有分页。无需将本文件转为 Stage 01 的 deck-plan.json，也无需重新启动 Stage 01 规划流程。

## 修改落点

- `cyberppt/stage02_script_adapter.py`：新增此类结构化外部 Markdown 的识别、页块解析、英文加粗字段分流与完整性校验；保留现有中文外部稿和内部脚本行为。
- `cyberppt/stage02_input.py`：使新增外部上下文与必要限制进入 canonical intake，沿用现有快照、哈希及 source_mode；不建立平行事实源。
- 当前 build_stage02_input 对正文调用外部适配器，对语义标注仍读取原始文本。兼容实现必须统一页面编号与适配结果，避免正文已识别、关系仍丢失。
- Stage 02 Skill 与工作流文档：补充支持的外部格式、字段权威、用途解析和失败行为。
- 测试：增加真实格式的回归样例，并验证正式入口只编译路径；生图与组装继续走原入口。

建议优先实现一个明确的 Deck Plan 格式分支。遇到已识别的 Slide 文档出现缺失 Content、重复字段、页数不符或无法解释的字段时，应给出可定位诊断，避免静默回退成单页。未知字段可保留为不上屏上下文并报告，不能直接拼入正文。

## 验收标准

1. 样例准确产生 p01 至 p12，标题逐页来自 Title，正文逐页来自 Content，无章节串页。
2. Communication Contract、Evidence、Composition 等未混入可见正文来源；关系限制与来源说明在后续判断中可获得。
3. 多行正文、嵌套列表、加粗键名、冒号差异、章节边界和末页边界均正确处理。
4. 缺正文、重复页码、声明页数不匹配等出现可定位诊断；未知用途不静默映射。
5. 旧中文外部稿、自由正文稿及内部 Final Script 1.0/1.1/1.2 回归通过。
6. 正式入口只编译验证实际 intake、逐页提示词及 source_mode；正文或相关上下文变化使旧绑定失效。
7. 生图、可编辑组装及最终 QA 需在实施后另外执行，本次未验证。
