# CyberPPT 视觉系统说明

> 本文件是说明性文档，不参与运行时 Prompt 解析。
>
> Stage 02 的唯一可执行视觉权威是 `scripts/imagegen_pipeline/style_presets/cyberppt_default_styles.json`；项目运行时使用 `workbench/locks/visual_style_lock.json` 中冻结的 registry snapshot。修改本文件不会改变既有 Style Lock，也不会改变实际送图 Prompt。

## 1. 当前正式生产风格

CyberPPT 当前正式 Stage 02 生产链统一使用 canonical Style 09：

- `style_id`: `9`
- `slug`: `ivory_deep_blue_scene`
- 名称：`纯白 + 深蓝领导汇报`
- 页面背景：`#FFFFFF`
- 标题：`#101820`
- 正文：`#303030`
- 次级文字：`#6F7275`
- 分隔线：`#C9CDD1`
- 强调色：`#12355B`
- 参考样张：`assets/palette-samples/palette-09.png`

视觉目标：政企领导汇报、演讲辅助、阅读型 PPT；强调完整业务语义、清晰层级、连续构图、真实业务对象与场景、克制的编辑式视觉表达。

Style 09 的完整硬约束、构图语法、文字规则、人物/图标/箭头规则、内容忠实度规则和最终执行锁只维护在 style registry 的 `prompt_contract` 中。本文件只解释规则来源和使用方式，避免形成第二套可执行合同。

## 2. 单一视觉权威

运行链遵循以下顺序：

```text
style registry JSON
        ↓
创建 visual_style_lock.json
        ↓
冻结 resolved contract + SHA256
        ↓
Stage 02 Prompt compiler
        ↓
逐页 ImageGen Prompt
```

规则：

1. `cyberppt_default_styles.json` 是可执行视觉合同的唯一解析源。
2. 新建项目创建 Style Lock 时读取一次 registry，并将合同快照冻结到项目。
3. 已冻结的 Style Lock 后续按原字节消费；registry 更新只影响新锁。
4. 历史 pre-snapshot Style 09 锁首次读取时迁移一次到当前 registry snapshot，迁移后永久冻结。
5. `references/visual-system.md` 只用于帮助人理解视觉系统，不得覆盖 Prompt、背景色、构图规则或 build identity。
6. Style Lock 的 `resolved_contract.sha256` 与实际冻结合同一致，用于 provenance、恢复和失效判断。

## 3. Style 10 兼容规则

历史 Style 10 已退出独立视觉体系，仅保留旧项目兼容入口。

以下旧调用统一解析到 canonical Style 09：

- `style_id=10`
- `light_tech_business_dense`
- `ivory_deep_blue_semantic_scene`

兼容锁会记录原始 requested style，同时写入：

- `canonical_style_id=9`
- `legacy_alias=true`

最终使用的 Prompt、Prompt SHA、palette 和参考图全部来自 Style 09，不再维护第二套 Style 10 合同。

## 4. 历史 Style 1–8 的定位

Style 1–8 仍保留在 registry 和 `assets/palette-samples/` 中，作为历史探索、对照样张和兼容数据。

当前正式 Stage 02 主链不依赖“先展示 8 套样张再选择”的旧流程。默认生产由 Style 09 snapshot 驱动。未来如果重新开放多风格生产，应以新的明确 feature、独立测试和版本化 registry contract 实施，避免通过说明文档恢复旧流程。

## 5. Style 09 的稳定视觉原则

下列内容用于帮助人工检查；真正硬门禁以 registry `prompt_contract` 为准。

### 页面底色与气质

- 页面级背景保持纯白 `#FFFFFF`。
- 深蓝只承担关键层级、必要强调和结构锚点。
- 允许局部浅蓝灰用于轻量分区、证据区和低干扰结构组织。
- 避免将整页整体偏向象牙白、米黄、暖纸色。
- 整体保持平面、哑光、克制、高级编辑式汇报质感。

### 页面结构

- 每页围绕一个核心业务判断组织。
- 优先使用一个可识别的业务对象、业务场景、内容资产或结果作为主视觉锚点。
- 通过空间、尺度、裁切、重叠、对齐、包含和色调层级表达关系。
- 页面内容按语义权重分配面积，避免按条目数量机械均分。
- 构图保持连续、非对称、主次明确，避免平行卡片堆叠。

### 上屏文字

- 事实、数字、日期、单位、主体、责任、状态和条件保持来源语义强度。
- 标记为 locked/verbatim 的文字保持完整、原样、清晰可读。
- 普通上屏文字允许为阅读型 PPT 调整断句、层级和视觉组织，但不得改变事实含义。
- 文字空间优先于装饰、图标和泛化场景；空间不足时先简化视觉，再考虑压缩表达。

### 图像、人物、图标和连接关系

- 默认不出现人物；避免正脸、围桌会议、多人讨论和摆拍式素材。
- 组织名称、Logo、印章和组织标识不进入正文生图画面。
- 图标从零开始，仅在缺少图标会显著损害即时语义理解时使用极少量小型平面图标。
- 禁止 icon wall、逐条图标、逐模块图标和装饰性图标阵列。
- 默认不使用箭头或箭头头部；优先通过空间关系表达流程、汇聚、包含、对比和因果。
- 真实场景必须与本页锁定内容直接相关；没有具体业务指向时，优先使用平面结构关系场，而非泛化控制室或科技大屏。

## 6. Stage 02 生图边界

正文完整图用于后续“完整图 → 可编辑 PPT”重建，因此必须保持重建友好：

- 正文画布：`2048 × 1024`。
- 页面标题、副标题、Logo、页码、页脚和模板框架由 PowerPoint 层处理，不进入正文图。
- 不在图中绘制 source refs、evidence ids、text ids、字段名或编排指令。
- 完整图通过审计后成为 editable reconstruction 的 visual authority。
- Clean Base 与 Authored SVG 只能恢复可编辑层和清除对应文字区域，不得重新设计已冻结的视觉构图。

## 7. 修改视觉风格的正确方式

需要调整正式生产风格时：

1. 修改 `scripts/imagegen_pipeline/style_presets/cyberppt_default_styles.json` 中 Style 09 的 registry contract；
2. 更新与该合同相关的 invariant tests；
3. 为新项目重新创建 Style Lock；
4. 通过 Prompt SHA / input fingerprint 触发正确的视觉资产失效；
5. 保持历史已冻结项目可复现。

仅修改本说明文件不会改变任何生产行为。

## 8. 权威优先级

视觉规则冲突时按以下顺序处理：

```text
项目 visual_style_lock.json 中冻结的 contract
        ↓
style registry 当前合同（用于新锁）
        ↓
Stage 02 页面语义 / Artifact Spec
        ↓
本说明文件与参考样张
```

参考样张只影响审美理解和视觉校准，不得覆盖页面事实、上屏文字、业务关系、构图语法和硬约束。
