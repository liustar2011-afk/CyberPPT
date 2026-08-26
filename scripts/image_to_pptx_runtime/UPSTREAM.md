# Vendored Quick runtime

本目录内的 Quick 转换运行时直接同步自 `ppt-master`，交付和运行均不依赖外部仓库。

- 上游同步版本：`53c9c2a5e9f1a49096324fba4f95833649c6a0f4`
- 上游相对位置：`skills/ppt-master/scripts/`
- 同步原则：同名运行时文件保持逐字节一致；CyberPPT 只在外围适配正式生产编排、manifest 和项目路径。
- 打包例外：`attribution_guard.py`、`console_encoding.py` 保留本仓库包内资源定位方式，避免回指外部 Skill 目录。
- CyberPPT 自有入口：`__init__.py`、`quick.py`、`stage02_adapter.py` 以及文字策略、清底策略、模板组装和可编辑页验证模块。

高保真 Quick 的页面 SVG 由当前 Codex 主 Agent 根据归一化 full 图、无字底图、锁定文字真值和局部资产直接编写。OCR 只提供观察证据，生产编排不使用 OCR 框自动合成 authored SVG。
