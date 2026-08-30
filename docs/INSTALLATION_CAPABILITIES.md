# CyberPPT 安装与能力边界

CyberPPT 当前正式运行形态是仓库应用：克隆仓库后，在仓库根目录创建虚拟环境并以 editable 模式安装。Stage 02 正式运行时仍消费仓库内 `scripts/`、`references/`、`assets/` 等资源，因此本文件不把当前版本描述为“脱离仓库即可独立运行的 wheel 应用”。

## 基础依赖

`pyproject.toml` 的基础依赖覆盖正式 Python 代码直接导入的通用运行库。Pillow 现在作为直接依赖声明，不再依赖其他包间接带入。

## Source 解析能力

安装：

```bash
python -m pip install -e '.[source]'
```

增加：

- `openpyxl`：XLSX 原生 worksheet / row / formula 提取。
- `markitdown`：PDF、HTML、RTF 等格式的可选文本转换回退。

未安装这些可选依赖时，source extractor 必须明确给出 capability warning，不得静默声称完成原生解析。

## 开发环境

```bash
python -m pip install -e '.[dev]'
```

`dev` 合并 source 解析能力和测试依赖。CI 使用该入口，并执行生产 runtime import smoke test。

## 后续 wheel 化条件

只有完成以下工作后，才把 CyberPPT 标记为可脱离仓库资源独立 wheel 安装：

1. `scripts.imagegen_pipeline`、`scripts.image_to_pptx_runtime`、`scripts.presentation_qa` 等正式 runtime 进入明确 package 边界。
2. `references/visual-system.md`、样张、模板和运行时资源改为 package resource 或安装后可定位的数据资源。
3. 新增 `python -m build` + wheel 安装后的端到端 smoke test。

在此之前，editable repository install 是正式支持路径。
