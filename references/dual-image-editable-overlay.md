# 已审计 Full 图到可编辑 SVG 的 Stage 02 重建

CyberPPT Stage 02 的唯一正式交付链是：已审计的 `full` 图 → 页面盘点与注册图层 → 可编辑 SVG → 原生 PPTX。

生产要求：

- `page_image_pairs.json` 的 `production_mode` 必须为 `image-to-editable-svg`，且每页只有经文字审计通过的 `full` 图；
- 脚本文字是唯一文字 truth；OCR 只提供位置证据，不能替代或修正脚本文字；
- 每个重建层必须保留 canonical full 图的画布、边界框、z-order 和 registration evidence；
- 图表、数值、Logo、wordmark 或其他身份资产未被验证时，必须写入 `manual_required` 并阻断 PPTX 导出；
- 禁止把 canonical full 图或其截图作为隐藏或可见的整页背景，再叠加可编辑文字伪装重建；
- 只有通过 inventory、SVG quality、PPTX 文字回读和 render comparison 的页面才能进入 `delivery_readiness.json`。

正常入口是 `python -m cyberppt final-script-pages ... --production-build`。诊断性重建可使用 `python -m scripts.image_to_editable_svg`，但它不替代正式 Stage 02 编排。
