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
8. `page_source_report()` 对所有非 `passed` Packet 返回非零退出码。

### 当前验证状态

已完成代码级契约和单元测试用例更新。远端 CI 待分支 PR 建立后统一验证。

---

## 批次 2：Page Source Packet v2 与 Freshness

状态：已完成

### 已完成工作

1. 新增 `script_engine/source_freshness.py`。
2. 建立稳定 JSON 序列化规则，并使用 SHA-256 生成输入指纹。
3. Page Source Packet 升级为 `cyberppt.page_source_packet.v2`。
4. Packet 新增 `builder_version=stage1-page-source-v2` 和 `generated_at`。
5. 持久化 Packet 新增三个强制输入指纹：
   - `deck_plan_sha256`
   - `foundation_sha256`
   - `source_index_sha256`
6. 新增 `packet_freshness()`，明确返回：
   - `fresh`
   - `stale`
   - `invalid`
7. 新增 `contracts/page-source-packet.schema.json`，将 v2 Packet 的输入指纹和核心字段固化为数据契约。
8. 前置加载错误改用 `cyberppt.page_source_error.v1`，不再伪装成缺少 fingerprints 的 v2 Packet。
9. 新增 `tests/script_engine/test_source_freshness.py`，覆盖：
   - JSON key 顺序不影响指纹；
   - page-source 命令持久化完整指纹；
   - 上游输入变化后 Packet 变为 stale；
   - 旧版本或缺少指纹的 Packet 判定为 invalid。

### 当前验证状态

代码、Schema 和单元测试均已写入分支。尚未执行远端 CI；后续 PR 建立后统一读取 Actions 结果并继续修正。

### 下一步工作

批次 3：Author Preflight Manifest。

计划：

1. 新增 `script_engine/author_preflight.py`。
2. 新增 `contracts/author-preflight.schema.json`。
3. 基于 Deck Plan 逐页检查 Page Source Packet：`passed / blocked / missing / stale / not_applicable`。
4. 结构页显式标记 `not_applicable`，内容页必须具备 fresh + passed 的 exact source Packet。
5. 输出项目级 `overall_status` 和汇总计数。
6. 建立 Preflight 单元测试，为后续 AUTHOR / audit-final / render-stage02 强制接入提供唯一门禁依据。
