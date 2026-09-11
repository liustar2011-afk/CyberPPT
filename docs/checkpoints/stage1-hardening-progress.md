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

---

## 批次 3：Author Preflight Manifest

状态：已完成

### 已完成工作

1. 新增 `script_engine/author_preflight.py`。
2. 新增 `contracts/author-preflight.schema.json`。
3. Preflight 基于当前 Deck Plan、Foundation、Source Index 与逐页 Packet 构建项目级门禁结果。
4. 页面状态统一为：
   - `passed`
   - `blocked`
   - `missing`
   - `stale`
   - `not_applicable`
5. 当前规则以 `source_refs` 是否为空区分内容页与结构页：无来源页为 `not_applicable`；有来源页必须具备 fresh + passed 的 v2 Packet。
6. Preflight 同时校验：
   - Packet schema / fingerprints；
   - page_id；
   - authoring_mode；
   - page_source_refs；
   - Packet 自身 gate status；
   - exact source evidence 是否真实存在且结构有效。
7. 每个已加载 Packet 计算 `packet_sha256`，为后续 Final Script provenance 与 Stage02 复核提供稳定标识。
8. 新增 Packet 目录加载逻辑，错误 JSON、缺 page_id、重复 page_id 均形成阻断性 loader issue。
9. 新增 `tests/script_engine/test_author_preflight.py`，覆盖：
   - 内容页 passed + 结构页 N/A；
   - Packet 缺失；
   - 上游变更导致 stale；
   - Packet 已被 Exact Source Gate 阻断；
   - malformed exact source unit 被阻断。
10. 修复 exact source 检查边界：非对象 source unit 或空 text 均不能通过 Preflight。

### 当前验证状态

核心模块、Schema 和 focused tests 已写入分支。远端 CI 尚未执行。

---

## 批次 4A：Author Preflight CLI

状态：已完成

### 已完成工作

1. 新增 `author_preflight_report()`，负责加载 Deck Plan、Foundation、Source Index 和逐页 Packet，并生成/持久化 Manifest。
2. 新增 CLI 命令：`author-preflight`。
3. 默认来源：
   - Source Index：`<foundation-dir>/.cache/source-index.json`
   - Packet 目录：`<foundation-dir>/.cache/page-source`
   - Manifest：`<foundation-dir>/.cache/author-preflight.json`
4. 支持 `--source-index`、`--packet-dir`、`--output` 显式覆盖。
5. `overall_status == passed` 时返回 0；任何 missing / stale / blocked / loader issue 返回非零退出码。
6. 缺失或错误 Source Index 返回 `cyberppt.author_preflight_error.v1`，不生成伪造的有效 Manifest。
7. 新增 `tests/script_engine/test_author_preflight_cli.py`，覆盖：
   - Page Source → Author Preflight 正常链路；
   - 默认 Manifest 路径写入；
   - Packet 缺失时返回非零且持久化 blocked Manifest。

### 当前验证状态

CLI 入口、默认路径与 focused tests 已写入分支。尚未执行远端 CI。

### 下一步工作

批次 4B：把 Preflight 变成不可绕过的下游门禁。

计划：

1. 增加统一 `validate_author_preflight_gate()`，重新读取当前 Packet 并与已持久化 Manifest 对比，防止 Manifest 或 Packet 在生成后失效。
2. `audit-final` 强制要求当前 Preflight 存在、fresh、overall passed。
3. `render-stage02` 强制要求当前 Preflight 存在、fresh、overall passed。
4. 两个入口共用同一 Gate validator，不复制规则。
5. 增加 audit / delivery focused tests，覆盖 missing / stale / blocked / passed 四种状态。
