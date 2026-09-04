# Vendored Quick runtime

本目录内的 Quick 转换运行时直接同步自 `ppt-master`，交付和运行均不依赖外部仓库。

- 上游同步版本：`c40028bdef80bc12470231cee27d5aee91ba3b1c`
- 上游相对位置：`skills/ppt-master/scripts/`
- 维护原则：按功能边界同步上游模块，保留来源归属；CyberPPT 适配层独立维护，不承诺整棵运行时与上游逐字节一致。
- 本次同步范围：段落/tspan 归一化、CJK 文字测量、SVG 文字边界检查及 `text_measure.py`；转换 trace 在两仓库使用同一文字几何字段合同。
- 打包例外：`attribution_guard.py`、`console_encoding.py` 保留本仓库包内资源定位方式，避免回指外部 Skill 目录。
- CyberPPT 自有入口：`__init__.py`、`quick.py`、`stage02_adapter.py` 以及文字策略、清底策略、模板组装和可编辑页验证模块。

高保真 Quick 的页面 SVG 由当前 Codex 主 Agent 根据归一化 full 图、无字底图、锁定文字真值和局部资产直接编写。OCR 只提供观察证据，生产编排不使用 OCR 框自动合成 authored SVG。

## 独立集成边界

- 参考图编辑、原图局部裁切、逐行 SVG 编写及逐页看图复核的操作规则已接入仓库 Stage 02 Skill；执行时无需读取上游 Skill 或访问上游项目。
- `authored_layers.py` 提供本地资产登记和重新校验；`register-quick-page` 只写入当前生产 manifest。它不生成 SVG、不推算文字框、不自动伪造视觉检查结论。
- `final-script-pages --production-build` 消费登记产物，使用本目录的转换器生成原生 DrawingML 文字、渲染预览并逐页恢复。正式入口不调用 `clean_base_generator.prepare_clean_bases`。
- 历史 v3 清底校验保留用于旧项目兼容。外部 Quick 后端与外部项目导入参数已撤销。
- 运行依赖由本仓库环境提供：Python 包、OfficeCLI 及其渲染工具。参考图编辑由当前主 Agent 的图像编辑工具执行，不依赖外部仓库服务。
