# Stage 02 Build Identity

Stage 02 使用两个相互独立的身份概念。

## `input_fingerprint`

`input_fingerprint` 是确定性的输入身份。相同的有效输入必须得到相同 fingerprint；时间、输出目录和本次执行时间不得影响它。

当前纳入：

- Final Script 快照 SHA-256；
- Stage 02 intake SHA-256；
- visual spec SHA-256；
- visual style lock SHA-256；
- frozen resolved Style contract SHA-256；
- 请求页面集合；
- production / assembly mode；
- ImageGen model / quality；
- prompt enrich；
- style reference、image text audit、prompt edit 等影响产物的开关；
- prompt override 目录摘要；
- autonomous contract 摘要。

用途：缓存判定、输入变化诊断、跨 run 对比、产物失效分析。

## `run_id`

`run_id` 是一次具体执行的身份。默认由时间戳和 `input_fingerprint` 短摘要组成，因此相同输入重复执行会产生不同 run。

当前历史 CLI/API 字段仍叫 `build_id`。在兼容期：

`run_id == build_id`

`Stage02BuildContext.run_id` 是语义明确的只读别名。`--build-id` 继续用于指定/恢复既有 run，避免破坏历史命令。

用途：输出目录、恢复同一次运行、artifact ledger、逐页 checkpoint、运行审计。

## 禁止混用

- 不得用 `run_id/build_id` 判断两次运行的输入是否相同。
- 不得把时间戳写入 `input_fingerprint`。
- 不得因为两个 run 的 fingerprint 相同就自动覆盖历史产物。
- 恢复同一 run 必须继续使用原 `build_id`；创建新 run 则生成新的时间戳身份。

后续如移除历史兼容字段，只删除 `build_id` 命名层，不改变上述双身份模型。
