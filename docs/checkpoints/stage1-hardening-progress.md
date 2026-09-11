# Stage1 Hardening 实施记录

分支：`stage1-hardening`

目标：按照《CyberPPT Stage1 开发改造方案》逐步把 faithful authoring 从流程约定改造成程序级不可绕过的证据链和状态门禁。

## 批次 1：Exact Source 硬门禁

状态：已完成

### 已完成工作

1. 修改 `script_engine/page_source_packet.py`。
2. faithful 页面引用未知来源时，Packet 状态改为 `blocked`。
3. Foundation 条目没有 source-unit 绑定时，改为阻断：`PAGE_SOURCE_UNIT_BINDING_MISSING`。
4. source-unit 全部无法在 `source-index.v2` 中解析时，改为阻断：`PAGE_SOURCE_EXACT_TEXT_UNRESOLVED`。
5. source-unit 仅部分解析时，改为阻断：`PAGE_SOURCE_EXACT_TEXT_PARTIAL`。
6. Foundation statement 保留为上下文信息，但不再作为 exact source 缺失时的事实兜底。
7. 更新 `tests/script_engine/test_page_source_packet.py`，覆盖 unknown / missing binding / unresolved / partial resolution 四类阻断场景。
8. `page_source_report()` 已按现有逻辑对所有非 `passed` Packet 返回非零退出码，因此本批次无需增加兼容分支。

### 当前验证状态

已完成代码级契约和单元测试用例更新。尚未执行远端全量 CI；后续创建/更新 PR 后以 GitHub Actions 结果为准。

### 下一步工作

批次 2：Page Source Packet 版本与 freshness。

计划：

1. 将 Packet 升级为新的 schema 版本。
2. 写入 `generated_at`、`builder_version`。
3. 对 Deck Plan、Foundation、Source Index 计算稳定 SHA-256 指纹。
4. 增加 freshness 校验函数，能够明确返回 `fresh / stale / invalid`。
5. 为输入变更导致 Packet 失效建立单元测试。
