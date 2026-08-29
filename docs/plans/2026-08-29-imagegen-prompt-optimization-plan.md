# ImageGen 送图脚本优化开发方案

## 1. 技术判断

**Verdict：SUPPORT WITH CONDITIONS**

目标成立：提高关系正确率、视觉设计完成度、文字准确率，并减少最终 prompt 的重复和冲突。

对话提出的 typed relation graph、唯一文字源、视觉论点、主载体、文字绑定、连接图和动态约束都有合理性。仓库已经实现其中大部分能力，当前缺陷集中在现有数据经过 Stage 02 和 Prompt Assembly 时发生的信息丢失与错误投影。因此开发采用增量修复，继续沿用现有权威产物和 `final-script-pages` 正式入口。

## 2. 对话中应吸收的内容

| 建议 | 判断 | 落地方式 |
|---|---|---|
| 用 typed relation graph 取代自然语言箭头推断 | 吸收 | 复用现有 `business_relationships`、semantic verifier 和 `semantic_topology`；最终 prompt 的主关系优先消费已验证结构化关系。 |
| 每段上屏文字只有一个 ID 和一个文本源 | 吸收 | 复用现有 `locked_text_items`、`content_integrity` 和 T-ID；修复 renderer，使正文在最终 prompt 中只出现一次。 |
| Stage 02 输出 visual thesis、carrier、topology、text binding、connectors | 吸收 | 这些字段已存在；修复 prompt 投影和审计，使受来源支持的决策真正进入最终 prompt。 |
| 结果节点必须成为主视觉 | 吸收 | 根据已选 focus/result 分配 primary，取消“第一组天然 primary”的实现。 |
| Hard constraints 按拓扑动态生成 | 吸收 | 移除 `equal_peer_cards` 的全局适用，把 peer、convergence、feedback、sequence 等约束放入对应拓扑映射。 |
| 冒号标签允许局部字重、颜色和换行层级 | 吸收 | 保持字符和唯一出现次数锁定，扩展允许的 typography treatment。 |
| 内容密度影响视觉策略 | 吸收现有能力 | 复用 `visual_budget`、`text_capacity_budget` 和 `is_text_dense()`；无需新增 Stage 1 权威字段。 |
| 所有页面由 Stage 2 固定构图 | 条件吸收 | hard authority 页面进入 `directed_composition`；其余页面保留 `semantic_brief`，只锁定语义边界、视觉论点和焦点。 |
| 删除完整语义上下文和大部分约束 | 暂缓 | 先完成结构化语义投影和 A/B 生图，再依据文字正确率、关系正确率和视觉评分决定压缩幅度。 |
| 新建 Semantic Contract 和 Visual Blueprint 文件体系 | 不采纳 | 现有 handoff、visual design input、decisions、deck visual spec 和 artifact spec 已覆盖这些职责；新增平行权威会增加漂移风险。 |

## 3. 已验证的根因

### 3.1 最终主关系使用了错误的优先级

`build_final_prompt_ir()` 当前优先采用 `semantic_context.argument_chain`，随后才使用 `visual_thesis`。这会让 p05、p07、p18 等页面的自然语言顺序链覆盖已验证拓扑。见 [artifact_prompt.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/artifact_prompt.py:488)。

### 3.2 semantic brief 丢弃了 Stage 02 的主要视觉决策

Stage 02 已产生 visual thesis、spatial grammar、主载体、text binding 和 connectors；`semantic_brief` 投影会改写为空间自由选择和核心判断焦点。见 [artifact_prompt.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/artifact_prompt.py:452)。

这解释了对话所说的“Stage 2 输出过少”：数据层已经生成，最终 prompt 表面没有消费。

### 3.3 语义组主次按出现顺序分配

`_semantic_groups()` 把第一组设为 primary，其余全部设为 secondary。见 [artifact_prompt.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/artifact_prompt.py:258)。视觉编译器已经把选定焦点写成 `kind: result`，这项信息没有进入 emphasis。

### 3.4 全局禁止项与并列页面冲突

`equal_peer_cards` 和 `invented_center_hub` 当前作为 universal forbidden structures 注入所有拓扑。见 [compiler.py](/Volumes/DOC/CyberPPT/cyberppt/visual_stage/compiler.py:24)。p07、p11、p18 的语义允许并列组织，p11 明确要求七类并列，因此全局禁止等权节点会产生直接冲突。

### 3.5 正文在 prompt 中重复出现

绑定正文先在 Semantic groups 中渲染，随后在 Exact visible text contract 中再次完整渲染。见 [final_prompt_renderer.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/final_prompt_renderer.py:26) 与 [final_prompt_renderer.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/final_prompt_renderer.py:110)。现有 T-ID 和 root binding 已经能够支持单源渲染。

## 4. 开发阶段

### P0：关系和约束正确性

目标：任何 prompt 都不能出现顺序、并列、汇聚、反馈之间的自相矛盾。

修改范围：

1. [artifact_prompt.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/artifact_prompt.py)
   - 主关系优先从 `spec.relationships` 和已审计拓扑生成。
   - `argument_chain` 只作为无结构化关系时的兼容回退。
   - semantic group 的 primary 从 `result`/focus 产生；仅在缺少焦点的兼容数据上回退到第一组。

2. [compiler.py](/Volumes/DOC/CyberPPT/cyberppt/visual_stage/compiler.py)
   - 把 `equal_peer_cards` 移出 universal 集合。
   - `parallel_set` 允许等权语义节点，同时禁止虚假顺序边。
   - `missing_feedback_edge` 只由 `lifecycle_loop` 生成。
   - 编译前校验 selected topology、spatial grammar、graph edges 和来源 semantic topology 的兼容性。

3. [visual_structure_contract.py](/Volumes/DOC/CyberPPT/cyberppt/visual_structure_contract.py)
   - 新增阻断项：`TOPOLOGY_RELATION_CONFLICT`、`FOCUS_ROLE_CONFLICT`、`CONSTRAINT_TOPOLOGY_CONFLICT`。
   - false feedback、parallel-as-sequence、convergence-as-chain 必须失败关闭。

P0 回归案例：

- p05：U1/U2/U3 汇聚到研究目标。
- p07：五维诊断保持并列，无连续因果边。
- p11：七类为同级分类，允许等权结构。
- p18：四项保障共同支撑路径，无串行依赖。
- p19：成果 → 工作 → 目标，不出现 feedback 约束。

### P1：Prompt IR v3 单源渲染

目标：保留全部审计能力，正文只出现一次，Stage 2 的有效视觉决策进入 prompt。

修改范围：

1. [final_prompt_ir.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/final_prompt_ir.py)
   - 版本升级为 `v3`。
   - 继续复用 `TextBindingIR`、`SemanticGroupIR`、`CompositionIR`。
   - 增加面向模型的 topology/focus 表达；内部 T-ID 和 root ID 继续只进入 debug receipt。

2. [final_prompt_renderer.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/final_prompt_renderer.py)
   - 合并 Semantic groups 和 Exact visible text contract，按组渲染角色、层级和 exact text。
   - 每条正文只出现一次，顺序与 `typography.visible_text` 完全一致。
   - locked text 提前到视觉结构之前。
   - semantic brief 传递 visual thesis、已验证 topology、主焦点和可画业务对象；具体坐标、组件和装饰仍由 ImageGen 决定。
   - directed composition 继续传递完整 carrier、空间组织、文字附着和 connectors。

3. [final_prompt_contract.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/final_prompt_contract.py)
   - 校验正文全局恰好出现一次。
   - 校验组绑定覆盖、顺序、唯一主焦点和关系约束。
   - 保持 backend ID、来源 ID、内部枚举和 style routing token 不泄漏。

推荐的最终六段表面结构：

1. Deliverable
2. Page visual intent
3. Bound visible content
4. Structure and hierarchy
5. Style
6. Hard constraints

这只是 renderer 的输出格式变化，不新增内容权威或平行编译器。

### P2：文字层级和密度策略

目标：降低高密度页的错字、小字和文本墙风险。

修改范围：

- 将 `label: sentence` 规则调整为：字符不变、区域内只出现一次；冒号前标签允许更强字重、颜色和独立换行。
- 把现有 `text_capacity_budget.risk_level` 投影为页面级排版策略：字号下限、允许列数、组间留白、辅助视觉预算。
- `extreme` 页面先阻断并要求 AUTHOR 压缩；只有用户明确接受时才采用多页拆分或实验性文字分层策略。
- p11 的“结构底图 + 原生文字”作为 Stage 02 Quick 分支实验；保持正式链路的 full 图文字审计和 authored SVG 文字真值，不在 P0 中改变生产门禁。

### P3：ImageGen A/B 验证后切换默认

测试三组 prompt：现行 v2、完成 P0 的 v2、P1 compact v3。每个代表页至少生成 3 个样本。

验收指标：

| 指标 | 门槛 |
|---|---|
| 锁定文字完整率 | 100% |
| 新增业务文字 | 0 |
| 关系拓扑正确率 | 100% |
| 主焦点正确率 | 100% |
| OCR 中文门禁通过率 | compact v3 不低于现行基线 |
| 视觉化程度人工评分 | compact v3 显著高于现行基线 |
| prompt 长度 | 中位数下降至少 25%，且不牺牲上述指标 |

只有 compact v3 同时通过事实、文字、关系和视觉门槛后，才替换生产默认。失败时保留 P0 正确性修复，继续使用现有 renderer。

## 5. 测试计划

新增或更新：

- `tests/test_stage02_semantic_verifier.py`：汇聚、并列、反馈、顺序的 typed relation 回归。
- `tests/test_visual_structure_stage.py`：topology/grammar/edge/constraint 兼容矩阵。
- `tests/test_visual_structure_contract.py`：三类新增阻断码。
- `tests/test_artifact_prompt.py`：verified relationship 优先级和 primary focus 投影。
- `tests/test_final_prompt_ir.py`：semantic brief 保留视觉论点与拓扑边界。
- `tests/test_final_prompt_renderer.py`：正文全局只出现一次、分组顺序稳定。
- `tests/test_final_prompt_contract.py`：重复正文、错误焦点、拓扑冲突均阻断。
- `tests/test_content_structure_real_project_regression.py`：p05、p07、p11、p18、p19 五个最小化真实回归夹具。

端到端验证继续通过 `.venv/bin/python3 -m cyberppt final-script-pages ... --production-build`，检查 prompts、manifest、OCR 审计、full 图、authored SVG、OfficeCLI PNG 和最终 PPTX。

## 6. 实施边界

- 不新增 Stage 1 权威产物。
- 不新增 Stage 2 平行 blueprint 文件。
- 不手写最终 prompt 或 `page_image_pairs.json`。
- 不改变 `final-script-pages` 唯一生产入口。
- 不在 P0 改动 ImageGen 模型、Style lock 或 Quick 组装分支。
- 不依据固定字数机械拆页；密度只作为风险信号和排版决策输入。

## 7. 建议提交顺序

1. `fix(stage02): reject topology and constraint contradictions`
2. `fix(prompt-ir): project verified focus and relationships`
3. `refactor(prompt): render bound visible text once`
4. `feat(prompt): project density-aware typography treatment`
5. `test(stage02): add real-page prompt regression cases`

每个提交保持独立可回滚；P0 可以单独上线，P1/P2 需通过 P3 的生图验收后进入生产默认。

## 8. 当前验证基线

- 12 份附件 prompt 的字符数为 4520～6823，中位附近约 5K；对话给出的平均值约 5112 与实测总量一致。
- 已确认 p05、p07、p11、p18、p19 存在上述关系或约束问题。
- 使用仓库 `.venv/bin/python3` 运行相关测试集，结果为 `99 passed`。
- 尚未执行 ImageGen A/B，prompt 缩短对视觉质量的净收益仍待验证。
