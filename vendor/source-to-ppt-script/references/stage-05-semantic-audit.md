# 阶段5：独立语义审查

## 输入

- 完整`source/source_blocks.json`
- `stages/01_information_assets.json`
- `stages/02_page_plan.json`
- `stages/03_screen_copy.json`
- `stages/04_visual_plan.json`
- `config/project.yaml`
- Schema：`references/schemas/semantic_audit.schema.json`

## 审查原则

以独立审查者身份重新对照源材料，不为前序结果辩护，不直接重写脚本。

## 审查维度

1. `source_fidelity`：是否改变原意、夸大、补充原文没有的能力、弱化限定条件、混淆数字和责任主体、丢失安全或合规边界。
2. `coverage`：core和must_retain资产是否进入页面；是否存在重要遗漏、无来源内容或跨页重复占位。
3. `page_purity`：每页是否只有一个使命、一个判断和一种主要关系；是否混合背景、问题、方案、实施、报价、成效等不同任务。
4. `copy_quality`：标题和正文是否可直接上屏、短句化、无禁用句式、无为凑结构制造的模块。
5. `visual_alignment`：视觉主张是否承载业务逻辑；是否出现卡片墙、图标化、文字与图片割裂、正面人像或第二视觉中心。

## Findings

- `error`：事实错误、来源不明、核心遗漏、边界改变、页面任务严重混杂或视觉结构与判断冲突。
- `warning`：存在明显质量风险，需要人工判断或优化。
- `info`：不影响正确性的改进建议。
- 每项尽量定位`page_id`或`asset_id`，不能定位时使用空字符串。
- `recommendation`必须指出应回到哪个阶段如何修正。

## 通过标准

- 无error。
- `summary.pass=true`。
- 忠实度、覆盖度、页面纯度和视觉一致性均达到项目可交付水平。
- 不通过时必须修正前序文件并重跑受影响阶段，禁止只把`pass`改为true。
