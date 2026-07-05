# 多页按图复刻协议

本文定义 `slide-image-rebuild` 多页项目的最小稳定协议。目标不是一次性实现所有批量入口，而是保证多页复刻在命名、页序、QA 报告和断点续跑上有一致约束。

## 1. 页序来源

`slide_image_rebuild_manifest.json` 的 `pages[]` 是唯一页序来源。导出 PPTX、preview、QA 聚合和 notes 均按该数组顺序处理。

推荐页 ID 使用 `P01`、`P02`、`P03`。其他 ID 不阻断，但 manifest 校验会给出 `non_protocol_page_id` warning。

## 2. 推荐目录

```text
project/
  slide_image_rebuild_manifest.json
  images/
    reference_pages/
      P01.png
      P02.png
  pages/
    P01/
      layout_reference.json
      content_mapping.json
      text_region_map.json
      svg_output/P01.svg
    P02/
      layout_reference.json
      content_mapping.json
      text_region_map.json
      svg_output/P02.svg
  notes/
    total.md
  exports/
    preview_qa/
      P01.preview.png
      P02.preview.png
    qa/
      strict_run_summary.json
```

单页项目可以继续使用项目根目录 artifacts。多页项目推荐使用 `pages/Pxx/`，避免 `layout_reference.json`、`text_region_map.json` 等同名文件互相覆盖。

## 3. Manifest 约定

每页至少声明：

```json
{
  "page_id": "P01",
  "reference_image": "images/reference_pages/P01.png",
  "page_dir": "pages/P01"
}
```

如页面 artifacts 不在默认位置，可显式指定：

```json
{
  "page_id": "P01",
  "reference_image": "images/reference_pages/P01.png",
  "page_dir": "pages/P01",
  "layout_reference": "layout_reference.json",
  "content_mapping": "content_mapping.json",
  "text_region_map": "text_region_map.json"
}
```

相对路径以 `page_dir` 为基准；`reference_image` 以项目根目录为基准。

## 4. SVG 与 Preview 命名

推荐 SVG 文件名与 page id 完全一致：

```text
pages/P01/svg_output/P01.svg
pages/P02/svg_output/P02.svg
```

strict runner 仍可识别 `P01*.svg`，但偏离推荐命名会在 `svg` 及以后阶段产生 `non_protocol_svg_name` warning。

preview 命名沿用：

```text
exports/preview_qa/P01.preview.png
exports/preview_qa/P02.preview.png
```

contact sheet 命名沿用：

```text
exports/qa/contact_sheets/P01.contact_sheet.png
exports/qa/contact_sheets/P02.contact_sheet.png
```

## 5. Notes 约定

多页项目的 `notes/total.md` 必须按 page id 分段：

```markdown
# P01

第一页解说词。

# P02

第二页解说词。
```

导出阶段 manifest 校验会检查每个 page id 是否有对应一级 heading；缺失时返回 `missing_page_notes_heading` hard error。

## 6. 断点续跑

失败报告必须保留具体 page id。修复时优先使用 `exports/qa/strict_run_summary.json` 中的 `next_action.resume_command`，不要手工跳过 manifest 阶段。

## 7. 不做事项

当前 P1 不把目录/PDF/PPTX 批量输入入口做成默认能力；批量入口后续必须复用本协议生成 manifest 和 artifacts。

当前 P1 不把所有多页项目强制迁移到 `pages/Pxx/`；旧单页根目录结构继续兼容，多页根目录共用 artifacts 仅 warning。
