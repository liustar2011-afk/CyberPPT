# 三图模板正文区等比落位设计

## 目标

三图可编辑正文套用模板时，保持 FULL、BACKGROUND 和 TEXT 的共同坐标系，不再把接近 16:9 的三图画布强制拉伸到原有约 2.095:1 的模板正文区。

## 适用范围

本设计只作用于 `editable_text_three_image` 的正文页模板装配。封面、目录、章节过渡页、结束页、普通非三图图片流程、图片生成、三图归一、OCR 和供应商批处理均保持不变。

## 正文最大边界

在 1280×720 的模板坐标系内，三图正文最大边界固定为：

```text
x=100, y=96, width=1080, height=608
```

该区域是允许落位的最大边界，不要求图片强制填满。

## 坐标契约

1. FULL 继续作为每页三图的唯一规范坐标系。
2. BACKGROUND 图像尺寸及 TEXT 的像素坐标继续归一到 FULL。
3. 模板装配阶段读取该页 FULL 规范画布的宽高比，在正文最大边界内计算单一 `contain` 变换。
4. 变换只包含统一比例缩放和平移：

   ```text
   scale = min(max_width / full_width, max_height / full_height)
   placed_width = full_width * scale
   placed_height = full_height * scale
   placed_x = max_x + (max_width - placed_width) / 2
   placed_y = max_y + (max_height - placed_height) / 2
   ```

5. BACKGROUND 和所有 TEXT 文本框必须共享同一个 `placed_x`、`placed_y` 和 `scale`。
6. 不允许为背景和文本分别计算横向、纵向或独立缩放比例。

## 图像处理边界

- 禁止 `preserveAspectRatio="none"`。
- 不裁剪、不补边、不重采样或改写输入图片文件。
- 图片在模板区域内按原始比例完整显示。
- 未被图片占用的模板空间属于幻灯片布局空间，不属于图片文件留白。
- 不通过扩大图片覆盖范围侵入标题、Logo、分隔线或页脚保护区域。

## 典型结果

当 FULL 为 `1680×944` 时，在 `1080×608` 最大边界内计算得到约：

```text
x=100, y≈96.57, width=1080, height≈606.86
```

BACKGROUND 使用该矩形；TEXT 的每个坐标和字号使用同一比例映射，因此不会产生三图之间的相对漂移，也不会发生横向拉伸。

## 实现边界

模板导出模块应增加一个纯计算的等比落位函数，返回页面共享的放置变换。`render_editable_body_svg` 只消费该变换：背景 `<image>` 使用等比显示，文本框调用同一个坐标映射。不得把 contain 逻辑分别复制到背景和文本路径。

## 错误处理

- FULL 规范画布或正文最大边界的宽高非正数时立即失败。
- editable page 声明的 canvas 必须是 FULL 规范坐标系；缺失或非法时立即失败。
- 不在运行时静默回退到旧的非等比拉伸行为。

## 验收标准

1. `1680×944`、`1672×941` 等接近 16:9 的规范画布均完整落入 `1080×608` 最大边界。
2. 输出宽高比与输入 FULL 相同，允许的差异仅来自浮点序列化精度。
3. BACKGROUND 与 TEXT 使用相同的平移和统一缩放比例。
4. SVG 中三图可编辑正文背景不再出现 `preserveAspectRatio="none"`。
5. 输入图片文件哈希在模板装配前后保持不变。
6. 普通非三图图片、模板页和三图归一测试行为不变。
