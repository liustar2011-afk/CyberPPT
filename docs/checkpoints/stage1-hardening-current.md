# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到批次 `5A`。

- PR #34 第二轮 Python 3.12 CI：`3 failed, 2216 passed, 8 skipped, 49 subtests passed`；Stage1 hardening 自身新增回归已清零。
- Author Preflight 已升级为 `cyberppt.author_preflight.v2`，builder 升级为 `stage1-author-preflight-v2`。
- 每个内容页现在从 fresh Page Source Packet 汇总稳定、去重的 `unit_ids`；结构页 `unit_ids` 固定为空。
- exact source unit 缺 `unit_id`、缺正文或结构异常时，Preflight 无法形成有效 lineage，并继续按 exact-source unavailable 阻断。
- `contracts/author-preflight.schema.json` 已升级为 v2：有 `source_refs` 的页面要求至少一个 `unit_id`，无 `source_refs` 的结构页禁止携带 unit lineage。
- persisted Manifest 与当前 Gate 状态复核时新增 `unit_ids` 比较；unit lineage 被篡改或漂移即判 stale。
- focused tests 已补充：
  - 内容页输出 `unit_ids`；
  - 结构页 lineage 为空；
  - 重复 exact unit 稳定去重；
  - missing / stale / blocked 页面不伪造 unit lineage；
  - Manifest 中 `unit_ids` 被篡改时 Gate 阻断。

## 下一步

批次 `5B`：Final Script `source_provenance` 数据契约。

计划：

1. 为内容页新增并强制要求 `source_provenance`；
2. 字段至少包含 `packet_sha256`、`source_refs`、`unit_ids`；
3. Final Script schema 明确结构页不允许伪造 provenance；
4. 新增 provenance 语义校验：Final Script 必须与当前 Author Preflight 对应页面完全一致；
5. 先完成契约与 focused tests，再分步骤迁移 examples / fixtures，不增加历史兼容路径。