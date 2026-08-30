# CyberPPT 安装与能力边界

CyberPPT 的正式开发/生产入口仍优先采用仓库根目录的 editable install。自 2026-08-31 起，正式 Python runtime 与关键只读资源也进入 wheel 包边界，并由 CI 做离开仓库目录后的 import/resource smoke test。

## 基础依赖

`pyproject.toml` 的基础依赖覆盖正式 Python 代码直接导入的通用运行库。Pillow 作为直接依赖声明，不再依赖其他包间接带入。

## Source 解析能力

```bash
python -m pip install -e '.[source]'
```

增加：

- `openpyxl`：XLSX 原生 worksheet / row / formula 提取。
- `markitdown`：PDF、HTML、RTF 等格式的可选文本转换回退。

## Wheel 包边界

当前 wheel 明确打包：

- `cyberppt`、`script_engine`；
- 正式 `scripts` runtime，包括 ImageGen 与 image-to-PPTX runtime；
- `contracts/*.json`；
- `references/*.md`；
- `assets/palette-samples/*.png`；
- ImageGen style preset JSON。

CI 在完成 pytest 后构建 wheel，用 wheel 覆盖 editable install，并切换到 `/tmp` 再 import 正式 Stage 02 runtime，同时检查 style library 与 `visual-system.md` 能够从安装位置定位。

## 当前边界

Wheel smoke 证明“正式 Python 模块和上述关键资源可安装、可导入”，不等价于完整端到端 PPT 生产已在纯 wheel 环境验证。OfficeCLI、ImageGen provider、外部二进制、vendor enhancer 和平台相关能力仍需要各自的运行环境检查。

完整 wheel 交付的下一步是增加一个不调用外网和 Office 的最小 Stage 01→Stage 02 fixture build，再分别增加 macOS/Windows 的 Office/render 集成测试。
