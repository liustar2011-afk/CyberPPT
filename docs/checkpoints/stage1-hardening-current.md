# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到批次 `5B`。

- Stage1 hardening 在上一轮 CI 中新增回归已清零；当前仅保留 3 个已确认的 `main` 基线失败。
- Author Preflight v2 已提供逐页 `packet_sha256 + source_refs + unit_ids` 三元 lineage。
- `contracts/final-script.schema.json` 新增独立的页面级 `source_provenance`，与既有 onscreen module provenance 分层管理。
- 每个 `content` 页面现在强制要求：
  - `packet_sha256`：64 位 SHA-256；
  - `source_refs`：非空、唯一；
  - `unit_ids`：非空、唯一。
- 非 `content` 的结构页明确禁止携带 `source_provenance`，避免伪造来源链。
- 新增 `script_engine/final_source_provenance.py`，提供纯语义校验：
  - Final Script packet hash 必须与 Author Preflight 一致；
  - provenance source refs 必须同时与 slide `source_refs`、Preflight `source_refs` 一致；
  - provenance unit ids 必须与 Preflight `unit_ids` 一致；
  - Preflight 页面缺失或 gate 非 passed 时直接阻断；
  - 结构页携带 lineage 直接报错。
- 新增 `tests/script_engine/test_final_source_provenance.py`，覆盖 schema 强制、结构页禁止、正常匹配和四类 drift。

## 下一步

批次 `5C`：迁移正式 Final Script 产物并接入运行门禁。

计划：

1. 迁移仓库 `examples/final-script*.json`，使正式示例具备 `source_provenance`；
2. 根据最新 CI 结果迁移测试 fixtures 中的内容页来源链，不增加兼容逻辑；
3. `audit-final` 在 Author Preflight Gate 通过后执行 `validate_final_source_provenance()`；
4. `render-stage02` 在写出 Markdown 前强制执行同一 provenance 校验；
5. Gate report 暴露当前经过复核的 Manifest 页面 lineage，避免下游自行拼接证据；
6. 完成迁移后重新运行 PR Actions，要求本分支新增失败再次归零。