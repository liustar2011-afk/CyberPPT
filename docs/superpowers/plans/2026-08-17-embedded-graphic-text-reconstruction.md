# Stage 02 Quick 配图文字重构规则固化计划

## 目标

将“图片或配图中的可读文字必须先分类，清底后只能保留或用原生 SVG 文字重建，空白容器不得交付”固化为 Stage 02 Quick 唯一路径的机器可检查契约，并保留现有高保真 SVG → 原生可编辑 PPTX 的生产边界。

## 设计结论

采用 `graphic_text_policy.v1` 作为每页 `pairs[*]` 的作者声明与门禁输入：

- `native_text`：清底后必须在作者 SVG 中逐字出现，并由 PPTX 文本 QA 保持可编辑。
- `preserved_in_image`：该文字随经过核验的局部图片层保留，不要求再生成原生文字，但必须声明图片层证据。
- `items` 为空也必须显式声明页面已完成配图文字检查。
- `empty_container_check` 必须为 `passed`；未处理的容器或 `manual_required` 直接阻断导出。

机器门禁验证结构、文字完整性、图片层证据和空白容器状态；视觉位置、字号、字重和清底质量仍由 SVG 质量检查与视觉复核负责。

## 任务

1. 新增 Stage 02 Quick 配图文字策略校验模块。
   - 解析每页策略。
   - 提取作者 SVG 的原生文字与图片层引用。
   - 校验策略状态、文字逐字覆盖、`preserved_in_image` 的图片层证据及空白容器门禁。
   - 输出可序列化的 QA 报告，便于生产回执和交付审计。

2. 接入唯一生产适配器。
   - 在 `run_stage02_reconstruction` 复制与检查作者 SVG 后、导出 PPTX 前执行策略门禁。
   - 缺失策略或策略未完成时 fail closed。
   - 将 `graphic_text_policy_qa.json` 写入 analysis，并纳入 production readiness 的必需报告。
   - 不改变归一尺寸、SVG 导出、Office CLI/Obscura 渲染或现有文本 QA 的职责。

3. 更新流程与 Quick Skill 文档。
   - 在主流程 Stage 02 中加入“配图文字分类与清底回写”步骤。
   - 在 Quick Skill 和 quick-generate 参考中明确三类处理规则、空白容器禁交付和策略字段。
   - 说明 `text_policy: embedded` 只描述生图资源的稳定字样；可编辑重构页面仍必须执行本契约。

4. 增加定向测试。
   - 原生文字逐字覆盖通过。
   - 原生文字缺失阻断。
   - 保留图片文字的局部图片层证据通过，缺证据阻断。
   - 未完成策略与空白容器阻断。
   - Stage 02 适配器把策略 QA 纳入结果与 readiness。

5. 验证与交付。
   - 运行配图文字策略、Stage 02 适配器、Skill 合同和 PPTX 文本 QA 相关测试。
   - 刷新 Graft 索引。
   - 本轮只提交源码、测试和流程文档，不覆盖或提交上一轮临时 PPTX 产物。

## 风险与边界

- OCR 只能辅助发现候选文字，不能替代作者对嵌入图中文字的完整分类；策略缺失时阻断，避免再次出现“清空后留下空白容器”。
- `preserved_in_image` 的视觉保真仍需要人工/视觉复核；机器门禁只验证其声明的图片层证据和无未处理状态。
- 旧的 `scripts/image_to_editable_svg` OCR/重构模块不恢复为生产路线；所有可编辑 PPTX 仍从 Stage 02 Quick 适配器导出。
