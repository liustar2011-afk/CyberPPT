# 阶段 2：Scene Graph → Page SVG IR

阶段 2 新增 `scripts/dual_image_overlay/scene_graph/page_svg_ir.py`，把已通过
scene graph gate 的页面编译为 `cyberppt.page_svg_ir.v1`。该 IR 是结构化交接格式，
不负责绘图；后续 PPT Master SVG/DrawingML runtime 可据此生成 SVG、原生文本和形状。

## 三层合同

- `background`：可选的无字底图，标记 `text_bearing=false`、`editable=false`，只承担复杂视觉资产。
- `visuals`：scene graph visual nodes 与 relations；保留语义角色、bbox、来源、几何和组件 ID。
- `editable_information`：所有 scene graph text nodes 编译为 `kind=text`，保留 script/content-lock
  truth source、binding、布局策略和可编辑样式。

根节点写入 `data-pptx-bounds`，画布沿用 scene graph 的 1672×941 normalized canvas，避免后续
SVG→DrawingML 坐标漂移。

## 闸门

编译前运行 `build_scene_graph_gate()`；严格模式拒绝未绑定文字、越界节点和未解析坐标。
编译后运行 `validate_page_svg_ir()`，检查元素 ID 唯一性、画布边界和可编辑文字真值合同。
两套结果分别写入 `scene_graph_gate` 与 `page_svg_ir_gate`，供阶段 5 QA 合并。

阶段 2 没有替换现有 PPTX 导出器，也没有把整页蓝图变成交付背景；它只建立 scene graph 到
Page SVG/DrawingML 之间的稳定 IR 边界。

