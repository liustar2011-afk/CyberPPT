# PPTX Generation Scripts Index

本文件索引当前已经形成的 PPTX 生成脚本。后续每页应先写脚本，停下来给用户审阅，再运行生成。

## Existing Scripts

| Slide | Script | Status |
|---|---|---|
| 01 | `workbench/reconstruction/build_slide_01.js` | 已生成，用户已确认不再修 |
| 02 | `workbench/reconstruction/build_slide_02.js` | 已生成过一次；后续应先审脚本再继续执行 |

## Execution Command Pattern

```bash
NODE_PATH=/tmp/cyberppt-node/node_modules node projects/电力可信数据空间科技成果转化/workbench/reconstruction/build_slide_XX.js
```

## Review Gate

在运行脚本前，用户应能看到：

- 本页标题、副标题和真实内容来源；
- 本页版式结构；
- 图表或矩阵计划；
- 主要文本、数字、来源是否来自内容锁；
- 是否使用图片；
- 如果使用图片，图片资产准入理由；
- 生成脚本路径。

只有用户确认后，才运行脚本生成 PPTX 和渲染图。
