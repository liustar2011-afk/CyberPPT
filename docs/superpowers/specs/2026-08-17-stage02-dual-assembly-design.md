# Stage 02 双路径 PPT 组装设计

## 目标

在当前 Stage 02 生图、文字审计、尺寸归一和 Quick 可编辑重建链路上，恢复模板正文区组装能力，同时保留两种可选交付路径：

1. 图片式 PPT：将审计通过的 2:1 正文图片缩放到 16:9 模板的正文区。
2. 可编辑 PPT：将审计通过的 2:1 Quick authoring SVG 等比例缩放到同一正文区，保留原生文字、形状和图片层。

两条路径共享 Stage 02 handoff、manifest、正文图尺寸契约、graphic_text_policy、模板页顺序和最终 QA，不恢复 OCR 坐标回填或旧的图片反推页面结构。

## 已验证事实

- 当前 Quick 产物的 SVG 和 PPTX 画布均为 2:1。
- 当前品牌正文区为 `x=33, y=89, width=1214, height=607`，比例为 2:1。
- 当前模板画布为 1280×720。
- 旧项目的 `template_image_ppt_export.py` 已跑通正文图片、标题层、模板元素和 PPTX 导出。
- 当前 `stage02_adapter.py` 只导出 flat Quick PPTX，尚未消费 `assets/presentation-templates/cec-lightweight/`。

## 组装契约

### 图片式路径

输入：manifest 中审计通过的 `full.path`，尺寸归一为 `generation_contract.generation_size`。

组装：创建 1280×720 页面 SVG，将图片放入正文区，标题放在正文区上方，加入品牌 Logo、红线、页脚和动态页码，再调用现有 SVG/PPTX 原生导出器。

输出：`exports/template_image.pptx`。

### 可编辑路径

输入：图片式路径同一份 `full.path`，以及每页通过 Quick 质量门的 `authoring_svg`。

组装：要求 authoring SVG 的根画布为 2:1，将其所有正文对象置于正文区的等比例变换组内；模板标题和公共元素位于外层 1280×720 页面。

输出：`exports/editable_svg.pptx`。

### 页面角色

- `content`：按所选 assembly mode 使用正文图片或正文 SVG。
- `cover`、`agenda`、`section`、`ending`：使用品牌模板 SVG，不进入图片生成；两种 PPT 路径共用这些模板页。
- 最终顺序严格服从 manifest 的 `requested_pages`。

## CLI 与结果

新增 `--assembly-mode`，取值为 `image`、`editable`、`both`，默认 `editable`。`both` 在一次已完成的 Stage 02 生图和 Quick 检查后同时输出两份 PPTX。

运行结果保留既有 `exported_pptx` 字段，并新增 `exported_pptx_by_mode`、`assembly_mode` 和每种模式的 QA 结果。现有 editable 输出路径保持兼容。

## QA

- 检查输入图片实际像素尺寸与 2:1 generation contract 一致。
- 检查 authoring SVG 根 viewBox 为 2:1，并拒绝已经包含模板 Logo、页脚、红线或页面外框的正文 SVG。
- 检查正文对象落在模板正文区，标题不与正文内容重复。
- 检查模板页、内容页与 requested_pages 数量和顺序一致。
- 对两种输出分别运行 SVG 质量检查、文字 QA、PPTX 结构校验，并使用 OfficeCLI 作为默认渲染检查工具；Obscura 作为浏览器渲染检查环境。

## 不在本次范围

- 恢复 `scripts/dual_image_overlay/` 旧目录。
- 恢复 OCR/坐标回填、模板图片反推页面结构或三图兼容路线。
- 修改 Stage 01、Source Truth、Outline 或视觉风格选择流程。
