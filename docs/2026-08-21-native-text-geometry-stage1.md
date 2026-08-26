# Stage 02 原生文字几何优化：阶段 1 交付报告

日期：2026-08-21

## 当前结论

第 1 阶段已完成：Stage 02 默认 editable 链路新增原生文字几何 QA-only。它读取
`graphic_text_policy.items[*].bbox` 与 authored SVG，输出文字节点的坐标、字号、
行数、行距、匹配方式和偏差；运行期间不改写 SVG。

第 2 阶段已启动并完成一次 fresh build 尝试。新批次完成图片生成和文字审计，流程
在 clean-base 前停止，原因是当前正式 manifest 的 `graphic_text_policy` 仍为
`required`，没有完成 native text 区域声明与 bbox。当前证据不足以启用自动坐标或字号
校准，需先完成该页的 Stage 02 文字区域登记和 authored SVG，再进入校准决策。

## 已落地代码

- `scripts/image_to_pptx_runtime/native_text_geometry.py`
  - 匹配优先级：显式 `data-cyberppt-text-id`、唯一规范化文本、无歧义稳定顺序。
  - 记录 `source_bbox`、`svg_x`、`svg_y`、`font_size`、`line_count`、`line_step`、
    `dx`、`dy`、`font_ratio` 和人工复核原因。
  - 重复文本、缺少 bbox、缺少坐标和锁定 SVG 都保留为明确 QA 状态。
- `scripts/image_to_pptx_runtime/stage02_adapter.py`
  - 在 native text style 之前调用几何 QA。
  - 写入 `native_text_geometry_qa.json`，并纳入 Stage 02 `artifacts`、`reports` 与
    production readiness。
- `.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md`
  - 固化 QA-only 规则：OCR bbox 用作坐标锚点，字号仍以 authored SVG 为准。

## 验证结果

使用仓库虚拟环境运行：

```text
24 passed in 1.09s
```

覆盖新几何模块、锁定 SVG 跳过、显式 ID、唯一文本、重复文本、多行文字、缺少 bbox、
回执写入，以及既有 native style 和 Stage 02 runtime 测试。

## Fresh build 证据

批次目录：`D:\CyberPPT\p09geometry02`

- 新图片生成完成，尺寸为 4096×2048，逻辑画布为 2048×1024。
- 图片文字审计完成，状态为 valid。
- clean-base 状态为 `manual_required`，报告指出需要完整的
  `graphic_text_policy`。
- 尚未产生 authored SVG、native geometry QA 或 editable PPTX，因此本阶段不对页面的
  真实坐标偏差和字号偏差作结论。

## 下一阶段准入条件

完成当前页的 `graphic_text_policy`，为每个 `native_text` 项提供准确 bbox，并准备与
该批次绑定的 authored SVG。随后使用同一正式 `final-script-pages --production-build`
链路重新执行 QA。只有当多个文字节点的偏差呈现稳定规律时，才考虑页面级 median
偏移；字号保持 authored 值，除非具备独立的字形高度证据。歧义匹配和异常区域继续
保留人工复核。
