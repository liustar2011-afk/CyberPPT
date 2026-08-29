# ImageGen 提示词优化开发交付

日期：2026-08-29

## 技术判断

结论：`SUPPORT WITH CONDITIONS`

本轮保留现有 `PageArtifactSpec → FinalPromptIR → renderer → contract` 正式链路，在编译边界补充语义约束，并通过回归测试锁定行为。完整的提示词章节重写、运行时重构和新增抽象暂缓；当前证据支持以较小改动先解决主焦点偏移、文字重复、标签僵化和拓扑冲突。

## 已落地能力

1. 结果型语义组优先成为视觉主焦点；缺少结果组时继续使用首个语义组。
2. 已审计的 `visual_thesis` 优先于兼容字段 `argument_chain`，避免旧链路覆盖正式视觉命题。
3. 绑定到语义组的可见文字只在最终提示词中声明一次；未绑定的兼容输入继续由文字章节统一声明。
4. `label: sentence` 保持字符完整与单一语义区域，同时允许冒号前标签加强字重或换行，禁止在其他位置重复标签。
5. 平行拓扑允许等权节点，并明确禁止强加顺序边；其他拓扑继续禁止等权卡片结构。
6. Stage 01 已验证关系拓扑与候选视觉拓扑建立兼容性校验，序列关系无法误选反馈环等不相容结构。
7. 最终提示词 IR 版本升级为 `v3`，使调试回执能够识别新的渲染契约。

## 修改范围

- `scripts/imagegen_pipeline/artifact_prompt.py`：主焦点、视觉命题优先级和职责边界。
- `scripts/imagegen_pipeline/final_prompt_ir.py`：IR 契约版本。
- `scripts/imagegen_pipeline/final_prompt_renderer.py`：语义组文字单次渲染与标签排版说明。
- `scripts/imagegen_pipeline/final_prompt_contract.py`：单次文字绑定校验。
- `cyberppt/visual_stage/compiler.py`：关系拓扑兼容性和结构禁用规则。
- `tests/test_artifact_prompt.py`、`tests/test_final_prompt_ir.py`、`tests/test_final_prompt_renderer.py`：既有契约更新与回归覆盖。
- `tests/test_prompt_optimization_regressions.py`：平行结构、标签自由度和拓扑冲突专项回归。

## 验证结果

- 提示词及视觉编译相关测试：`104 passed`。
- 排除 3 个工作区既有 Stage 02 handoff 契约冲突后，全仓测试：`1601 passed, 8 skipped, 3 deselected, 53 subtests passed`。
- `git diff --check`：通过。
- `graft build`：完成，索引覆盖 466 个文件。

全仓原始运行中的 3 个失败均对应本轮开始前已存在的 `cyberppt/stage02_handoff.py` 未提交修改：该修改移除了 deck plan 边界消费和外部脚本摘要失效检查。本轮遵循工作区保护规则，没有覆盖或回退这些改动。

## 尚未执行

未调用外部 ImageGen 服务进行付费 A/B 生图。代码层契约和完整本地测试已经通过；真实视觉收益仍需在固定样本、固定模型与固定风格锁下比较文字重复率、拓扑正确率和结果主焦点命中率。
