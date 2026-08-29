# “分析送图脚本问题”对话评估

## 结论

**技术判断：SUPPORT WITH CONDITIONS**

这段对话准确识别了两个高优先级问题：页面的“顺序链”与“共同汇聚”语义发生冲突；最终结果节点被错误标为次级。它对视觉机制不足、文字密度高、风格合同偏弱的观察也有合理性。

对话同时把“最终 prompt 的可读简洁度”和“生产合同的完整性”混在了一起。完整语义上下文、精确文字白名单、主体与事实约束承担来源边界、OCR 文字审核和可编辑 SVG 重建职责，不能仅凭 prompt 较长就整体删除。当前也没有生成图、OCR 结果、视觉评分或 A/B 对照实验，无法证明“重复导致模型强化文字”“否定约束使创造性下降”等因果判断。

## 已验证的有效判断

### 1. A→B→C→D 与共同汇聚存在真实冲突

附件把主关系写成顺序链，同时要求所有贡献线到达统一结果。前者表达阶段承接，后者表达多项因素共同支撑一个结论，两套拓扑不能同时作为页面权威。

仓库的视觉编译器已经明确区分这两类关系：存在 `convergence` 时，所有非焦点证据直接连向焦点节点；普通 flow 才按阅读序列逐项相连。见 [compiler.py](/Volumes/DOC/CyberPPT/cyberppt/visual_stage/compiler.py:276)。因此本页应在上游语义关系中明确选定 `converge`，并让 `argument_chain`、`semantic_graph`、forbidden structures 和最终 prompt 保持一致。

### 2. “研究目标”被降为 secondary 是实现缺陷

当前 `_semantic_groups()` 依据语义组的出现顺序分配强调级别：第一组为 `primary`，其余均为 `secondary`，没有读取已选定的 focus/result 绑定。见 [artifact_prompt.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/artifact_prompt.py:258)。

视觉编译器其实已经把选定焦点写为 `result`，并记录 `primary_refs`、`binding: result` 和 `visual_hierarchy.primary`。见 [compiler.py](/Volumes/DOC/CyberPPT/cyberppt/visual_stage/compiler.py:319) 与 [compiler.py](/Volumes/DOC/CyberPPT/cyberppt/visual_stage/compiler.py:438)。最终 prompt 投影丢失了这项层级信息。

建议修复根因：语义组强调级别应从焦点绑定或 `primary_refs` 投影；出现多个 primary、无 primary、焦点与 result 不一致时阻断。不要只为当前电力页面调换 A/D 顺序。

### 3. 正向视觉论点不足，判断方向合理

生产默认使用 `semantic_brief`。该模式只保留语义边界，并把载体、空间组织和场景选择交给 ImageGen。见 [artifact_prompt.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/artifact_prompt.py:452)。这项设计用于防止上游形成第二套布局引擎，目标合理。

附件中的 `argument_chain` 已经发生拓扑冲突，`visual_thesis` 又被核心判断覆盖，导致 ImageGen 获得了自由度，却没有获得稳定、无冲突的视觉论点。对话提出“锁视觉论点和对象关系，保留载体自由”符合本项目边界。

实施时应采用已有双模式：

- 来源只支持语义方向时，继续使用 `semantic_brief`，补强简洁的视觉论点、可画业务对象和唯一主关系。
- 来源明确支持硬拓扑、方向和条件时，使用 `directed_composition`。当前模式选择门禁要求 hard authority、受支持拓扑和显式业务关系同时成立，见 [page_artifact_spec.py](/Volumes/DOC/CyberPPT/cyberppt/page_artifact_spec.py:237)。

不建议把所有页面统一改成带固定横向构图的 directed prompt。

### 4. 上屏文本有排版风险，但“文字锁过死”的描述需要修正

附件的两条长句会提高图片内文字生成和排版风险，这一观察成立。上游 AUTHOR 应优先压缩上屏内容，保留完整论证在完整稿和讲述中。

当前生产合同已经允许 `line_break`、`grouping` 和 `position_change`，见 [compiler.py](/Volumes/DOC/CyberPPT/cyberppt/visual_stage/compiler.py:413)。因此“完全不能分行、不能形成层级”并非当前实现事实。`label: sentence` 约束的主要作用是阻止模型额外复制标签并生成第二套标题体系。

可以优化约束措辞，显式说明冒号前后允许通过字号、字重、颜色和换行形成层级，同时保持字符、顺序和唯一出现次数。精确文字白名单应继续保留。

## 部分成立或证据不足的判断

| 对话判断 | 评估 | 依据与边界 |
|---|---|---|
| 同一逻辑重复五遍 | 部分成立 | 人类阅读层面确有重复；各段分别承担使命、语义来源、关系、内容分组、文字真值等不同合同职责。当前只验证了字符预算和字段一致性，没有验证语义冗余对图像质量的影响。 |
| 删除 Semantic Groups | 不支持直接删除 | 分组用于绑定权威内容根、限制跨根合并，并为后续文字区域与结果绑定提供基础。可以压缩渲染文本，同时保留 IR 和审计合同。 |
| 删除完整 source-grounded context | 不支持直接删除 | 代码明确从 `full_prose` 建立语义上下文，并测试其进入 prompt 且不进入可见文字。见 [page_artifact_spec.py](/Volumes/DOC/CyberPPT/cyberppt/page_artifact_spec.py:761)。可考虑摘要化，但摘要必须保持主体、条件、边界和论证强度。 |
| Hard constraints 压缩一半 | 证据不足 | 这些规则来自内容锁、标题排除、页面 avoid 和拓扑禁用项，见 [page_artifact_spec.py](/Volumes/DOC/CyberPPT/cyberppt/page_artifact_spec.py:739)。应先按“生成必要 / 审计必要 / 可后置”分类并做 A/B 测试。 |
| 否定规则让模型进入合规优先模式 | 合理假设 | 对话没有提供相同输入、相同模型、相同 seed 或多样本评分，当前无法确认为因果。 |
| Style Contract 只有颜色 | 对附件成立 | 附件的风格语言确实偏薄。仓库支持独立 style lock，改进应发生在风格锁或视觉结构上，避免在单页 prompt 临时建立平行风格权威。 |
| 标题颜色属于无效信息 | 低风险冗余 | 正文图排除标题，该颜色在本页直接价值有限；若风格合同作为整套主题统一输入，保留也不会改变标题排除门禁。 |

## 对原对话十二项判断的总体评级

- **强支持**：关系拓扑冲突、结果节点视觉权重错误。
- **有条件支持**：补充正向视觉论点、减少可见重复、压缩长上屏文字、增强风格视觉语言、把抽象语义锚点转成可画对象。
- **不支持直接实施**：删除 Semantic Groups、删除完整语义上下文、大幅删除事实与文字约束、把所有页面改为固定构图。
- **尚待实验**：重复文本与否定约束是否直接导致“文字框 + 箭头”退化。

## 建议的修复顺序

1. 修复上游关系权威：本页选择 `convergence`，统一 argument chain、focus、edges 和 forbidden structures。
2. 修复语义组强调投影：从 focus/result 绑定决定 primary，增加冲突审计和回归测试。
3. 在 `semantic_brief` 中加入短而明确的视觉论点与可画业务对象，继续保持载体和具体空间实现自由。
4. 调整文字合同表述：明确允许换行、局部字重和层级设计；继续锁定字符、顺序、事实与唯一出现次数。
5. 对长上屏句在 Stage 01 AUTHOR 环节做内容压缩，避免把 Stage 02 当作改写器。
6. 设计 A/B 实验后再决定 prompt 减重：至少比较当前 prompt、去重版、去约束版，每版多样本，记录文字正确率、关系正确率、视觉化程度、可读性和 OCR 通过率。

## 反例检查

对话倾向于通过增加正向视觉结构提升稳定性。仓库已有明确反例：当来源没有 hard authority、显式方向和受支持拓扑时，固定构图可能把弱关系升级为强因果。当前 `semantic_brief` 默认避免锁定阅读路径，最终 prompt 校验也禁止该模式声明固定 Reading path，见 [final_prompt_contract.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/final_prompt_contract.py:141)。因此视觉机制只能在来源支持强度范围内增强。

## 验证记录

- 使用仓库 `.venv/bin/python3` 运行 3 个定向测试，结果为 `3 passed`。
- 测试覆盖：语义组当前按顺序分配 primary、完整 prose 进入非可见语义上下文、semantic brief 不锁 execution design。
- 未执行真实 ImageGen A/B 生成；关于视觉质量和创造性下降的因果结论仍属未知。
