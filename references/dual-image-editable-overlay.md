# 双图底图 + 可编辑文字模式

`dual_image_editable_overlay` 是 CyberPPT 第三阶段的默认交付模式。

默认交付边界如下：

- 无文字底图作为正文内容区视觉背景；
- 主要业务文字、数字和 SO WHAT 使用可编辑 PPT 文本框；
- 背景中的图形、图标、曲线、表格结构和装饰不可编辑；
- 最终文字 truth 来自 `slide_content_lock` / `semantic_plan`，不是 OCR。

它不适用于用户要求图表、表格、箭头、图标或背景对象也可编辑的场景；只有这些请求才升级到 `native_rebuild`。

生产要求：

- 已批准的第二阶段正文区 ImageGen 蓝图默认晋升为 `full` 候选图；不得在第三阶段无理由从零 text-to-image 生成另一张 full 图；
- 使用 `scripts/dual_image_overlay/cyberppt_pair_manifest.py --promote-blueprints-from <blueprint_dir>` 可把已批准蓝图复制为 full 图并写入 `page_image_pairs.json`；
- 进入双图生成前，必须先用 `scripts/dual_image_overlay/deliverable_prompt.py` 编译最终交付 prompt；该 prompt 用于补充、修复或重做不合格 full 候选，不是默认替代已批准蓝图；
- prompt 必须使用项目本身的视觉锁定，不得用外部仓库 style preset 覆盖项目风格；
- 生成图必须是最终交付成稿，不得把证据编号、来源编号、caveat、脚注、口径说明、标题占位条或调试标记画进图里；
- full/background 图像只覆盖模板正文内容区；标题、副标题、Logo、页脚、页码和公共元素由 PPT 模板/母版生成；
- background 必须从 approved full 进行 image-to-image 去文字派生，保持同一构图；不得重新文生图生成同主题新图；
- full/background 图像和坐标统一归一化到 `1280x720`；
- background 必须通过无文字扫描；
- `semantic_plan.containers[]` 必须存在；
- 每个文本项必须有 `container_id`；
- PptxGenJS 是正式 PPTX 生成器；
- `text_content_qa.json`、`layout_qa.json` 和 `production_readiness.json` 必须通过；
- 先跑 P2/P3 pilot，再批量跑全套页面。
