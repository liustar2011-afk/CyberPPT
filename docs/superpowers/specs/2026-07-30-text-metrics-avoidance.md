# 阶段 3：文本度量、容器避让与异常处理

阶段 3 在 Page SVG IR 前增加统一的文本度量和安全区处理：
`scene_graph/text_metrics.py` 先按 PPT Master DrawingML 度量（可导入时），否则使用
CJK 保守估算；文本先换行，再按统一字号缩放，不能 fit 时返回明确的
`blocked_overflow`，不得静默溢出或无限缩小。

文本节点还会读取 binding metadata 中的 `reserved_zones`，在所属 safe bbox 内尝试
下移、右移或上移；无合法位置时返回 `blocked_reserved_zone` 并阻断严格 IR 编译。
Page SVG IR 现在记录 `metrics` 与 `avoidance` 诊断，方便阶段 5 的 QA 合并。

