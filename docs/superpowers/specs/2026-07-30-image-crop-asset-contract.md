# 阶段 4：图片裁切与同源资源合同

阶段 4 新增 `scene_graph/image_assets.py`，将 Page SVG IR 中的图片统一登记为
`cyberppt.image_asset_contract.v1`。同一 canonical source 只生成一个 `asset_id`，
不同页面使用或 crop variant 通过 `uses` 和 `crop_variants` 记录，避免 PPTX 包重复嵌入同源图片。

合同明确：无字底图只能作为 `complex_visual_background` 且 `text_bearing=false`；
带文字图片不能静默升级为背景。每个图片元素携带 `asset_id`，IR 顶层写入资产清单和
`image_asset_contract_gate`，供后续 SVG/DrawingML postflight 复用。

