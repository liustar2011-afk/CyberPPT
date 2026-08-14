# 阶段 6：代表页、真实渲染与逐页验收

阶段 6 新增 `scripts/dual_image_overlay/page_acceptance.py`：

- 按视觉节点、关系、图片、曲线和页面角色复杂度，确定性选择代表页；
- 代表页只用于高风险抽查，不能替代全 deck 逐页验收；
- 每页登记 full/background、scene graph、Page SVG IR、SVG、PPTX、渲染图、side-by-side、QA 和 geometry evidence；
- 可调用现有 `qa_render_page` 做真实 PPTX geometry 检查和 LibreOffice/Poppler 渲染；
- 缺少必需证据、QA 失败或需要用户确认但未确认时，页面保持未接受。

该阶段建立的是验收合同和编排器，不伪造渲染结果；渲染工具不可用时明确记录
`render_status=unavailable`。

