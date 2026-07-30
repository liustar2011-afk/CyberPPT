# 阶段 1：PPT Master runtime bridge

阶段 1 将双图排版链从“业务代码直接加载 vendor 文件”收敛为一个可探测、可诊断、可回退的 runtime bridge。

## 运行时选择

入口：`scripts/dual_image_overlay/ppt_master_runtime_bridge.py`

选择顺序：

1. `CYBERPPT_PPT_MASTER_ROOT` 指定的 PPT Master 根目录；
2. CyberPPT 同级的 `ppt-master` 根目录；
3. CyberPPT 内置 `vendor/ppt_master_slide_image_rebuild` 快照。

只有存在明确的 `dual_image_rebuild_pptx.py` 时才加载 host 核心；当前 PPT Master
主仓库尚未提供该同名布局核心，因此阶段 1 的实际选择是 `cyberppt_vendor`。
这不是静默降级：`runtime_descriptor()` 会返回来源、模块路径、host/vendor 根目录、
resource bindings 路径和共享资源是否解析成功，并写入 semantic layout plan 的
`ppt_master_runtime` 字段。

## 共享资源

`resolve_shared_resource()` 读取 vendor 的 `resource_bindings.json`：优先解析
PPT Master 的 icons/templates/references/SVG checker，找不到时回退到 CyberPPT
本地资源，再回退到 vendor 目录。业务层不再硬编码 PPT Master 的绝对路径。

## 兼容性与安全边界

- `_load_vendored_ppt_master_core()` 保留为兼容函数，但内部只调用 bridge。
- vendor 快照仍是可用回退，阶段 1 不改变双图输出几何和文本策略。
- host 核心只允许来自显式根目录下的固定候选路径，不扫描任意 Python 文件。
- 模块加载失败会返回 `None`，沿用原有“保守地保留业务布局”的行为。

## 验证

- bridge 单元测试覆盖 vendor fallback、host 根目录探测和共享 SVG checker 解析。
- Python 编译检查通过。
- 既有测试中 Windows 路径断言改为跨平台分隔符比较。
- 工作树中的历史生产资产变更未纳入本阶段提交。

