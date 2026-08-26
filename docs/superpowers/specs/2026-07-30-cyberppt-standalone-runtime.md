# 阶段 7：CyberPPT standalone runtime

阶段 7 将生产运行时边界收敛到 CyberPPT 自身：

- `ppt_master_runtime_bridge.py` 不再探测、加载或解析 `D:\ppt-master`；
- 双图核心固定使用 `vendor/ppt_master_slide_image_rebuild` 本地快照；
- SVG checker、资源绑定和 QA 融合全部走 CyberPPT 本地路径；
- `standalone_runtime.py` 提供独立性闸门，检查 host_root、核心模块和 checker 资源；
- QA fusion 把 standalone runtime 作为必需组件，外部依赖会阻断报告。

PPT Master 后续只能通过显式的离线同步/升级流程向 CyberPPT 提供能力，不能成为
CyberPPT 的生产运行时依赖。阶段 7 不删除 vendor 快照，也不影响已有双图产物。

