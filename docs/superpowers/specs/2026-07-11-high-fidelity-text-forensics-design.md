# 高保真文字取证：PaddleOCR 本地集成设计

## 目标与边界

为 CyberPPT 的 legacy/advanced editable rebuild 增加完全本地的文字取证阶段。输入仅为 GPT 生成的清晰页面 PNG；不处理扫描件、拍照件、旋转或透视畸变。输出必须按视觉行给出文字、精确几何证据、受控纠错记录和样式取证数据，供后续字体拟合、PPTX 文字框生成与回渲染 QA 使用。

该阶段不属于 `full_image_ppt` 主线；仅在用户明确要求正文可编辑或进入 legacy overlay/template rebuild 时启用。

## 方案

采用本地 PP-OCR 作为文字与位置事实源，而非当前远端 Codex Vision。PaddleOCR-VL 不作为第一版依赖：其主要输出是文档版面块与 Markdown，不适合 PPT 的逐行精确定位。第一版使用 PP-OCR 的逐行识别结果（文本、置信度、四点框/矩形框）；后续可单独扩展表格与复杂图表解析。

PaddleOCR 不以外部服务形式依赖。将可复现的 Python 3.12 虚拟环境、版本锁定、模型清单和模型校验值放在仓库受控目录；主流程通过受限 subprocess 调用该环境，不能直接依赖主项目 Python 3.14 的包集合。

## 流程

```text
GPT 页面图
  -> 原尺寸 PP-OCR
  -> 质量不足时等比例 2x/分区复核
  -> 逐行合并与阅读顺序
  -> 受控自动纠错
  -> 颜色/字形/行高取证
  -> text_forensics.json + 可视化证据
  -> style-fit -> editable rebuild -> render compare
```

禁止默认使用旋转、去畸变或 unwarping：它们会改变原图坐标。放大复核必须严格映射回原图像素坐标。

## 后端契约

新增后端名 `paddleocr-local`。保留 `vision-json` 仅供显式诊断或人工指定；`none` 保留用于隔离下游流程。移除或弃用当前名为 `paddleocr-vl` 但实际调用远端 Vision 的占位行为。

`locate_text()` 的兼容输出继续为：

```json
{
  "image_size": {"width": 1672, "height": 941},
  "items": [
    {
      "text": "经营管理能力",
      "bbox": [112, 237, 418, 276],
      "confidence": 0.98,
      "source": "paddleocr-local"
    }
  ]
}
```

另新增不可丢失的 `text_forensics.json`，保存每一行的 `polygon`、原始 OCR、最终文本、逐字/候选证据、尺度来源、颜色采样、字形裁剪路径、模型与配置哈希。

## 受控自动纠错

OCR 识别的图上原文必须先保存为 `observed_text`。只有同时满足以下条件时才写入 `final_text`：

1. 多尺度或分区复核结果一致；
2. 候选字形与检测框中的图像证据吻合；
3. 中文上下文和领域词库显著支持替换；
4. 目标不属于保护词表（机构名、项目名、数字、日期、编号、英文缩写）。

每个替换保存原字、目标字、触发证据、规则/词库版本、置信度和可逆变更。未达门槛时绝不猜测：保留原文，标记 `review_required`，不得作为高质量可编辑文字层输入。

## 样式取证边界

OCR 阶段只采集样式证据，不宣称识别出确定字体。其输出包含文字掩码、主色/边缘颜色、行高、基线、宽高、字符裁剪。后续 `style-fit` 从项目允许字体库中渲染候选字体与粗细，拟合字号、字重、颜色、字间距和行距，再由回渲染差异选择最佳结果。

## 质量门

质量门配置化且按项目保存，不写死在代码中。必须包含：

- 逐行检测召回、阅读顺序与重复框检查；
- OCR 内容正确率与低置信行比例；
- 自动纠错准确率、替换审计完整性和保护词命中情况；
- 原图坐标的框 IoU / 中心偏差；
- 文字颜色差、字体回渲染后的局部像素差；
- 失败时的原始结果、复核结果、叠框图和恢复命令。

建立由真实 GPT 页面图和人工标注组成的黄金基准集；在该集上达标后，`paddleocr-local` 才能成为 legacy editable rebuild 的默认后端。

## 实现范围

1. 仓库内 PaddleOCR runtime、模型 manifest 与安装/离线校验脚本。
2. `paddleocr-local` subprocess adapter 与现有布局契约适配。
3. 多尺度复核、逐行合并、文本取证 schema 与叠框证据图。
4. 受控自动纠错、领域/保护词配置和可逆审计。
5. 配置化质量门、黄金样本测试与 legacy rebuild 接线。
6. 文档、CLI 帮助、迁移说明和回归测试。

不修改 `full_image_ppt` 主流程；不把 OCR 作为模板标题或正文事实来源。

## 验收

在黄金样本与至少一个 legacy editable rebuild 端到端项目上验证：全程无远端 OCR 调用、工件可复现、所有替换可回退、文字逐行框可视化可检查、质量门能拒绝低可信结果，且后续回渲染 QA 消费取证数据。

## 黄金 fixture 与验证合同

黄金 fixture 位于 `tests/fixtures/ocr_golden/`，只允许保存获批准的 GPT 页面图、
人工确认的逐行框/文本和纠错审计记录，不得保存密钥、Authorization header 或
远程服务地址。每条 line 必须同时保留 `observed_text` 与 `final_text`，并携带可
逆转的 correction audit。尚未有批准页面图时，仓库可保留显式标记为 `synthetic`
的 JSON 契约记录；该记录只验证 schema，不代表真实 OCR 质量达标。

离线契约命令：

```bash
python3 -m pytest tests/test_ocr_golden_contract.py -q
```

完整回归仍须覆盖 runtime manifest、本地适配器、逐行取证、受控纠错、质量门和
legacy 接线测试。至少执行一次 legacy rebuild 并渲染其输出供人工检查；失败时保留
原始取证、复核结果、叠框图和恢复命令。默认 `full_image_ppt` 主线继续不调用 OCR。
