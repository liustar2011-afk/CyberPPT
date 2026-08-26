# OfficeCLI 集成

CyberPPT 通过 OfficeCLI 对导出的 PPTX 进行独立渲染 QA。OfficeCLI 先生成单页 HTML，随后由仓库 Playwright 截图器加载 `assets/fonts/extracted/` 中的微软雅黑 Light、Regular 和 Bold 字体文件截图。该路径不依赖构建机已安装微软雅黑，避免中文缺字显示为方框。OfficeCLI 只负责渲染和诊断；CyberPPT 原有的 SVG 到原生 DrawingML 生产链路继续作为唯一 PPTX 组装路径。

`final-script-pages --production-build` 会在每个已请求组装分支的 PPTX 导出后自动运行该 QA，并把报告写入当前构建目录的 `qa-delivery/<assembly-mode>/officecli_render_qa.json`。OfficeCLI 缺失、渲染失败、页数不一致或几何检查失败都会阻断生产命令成功退出；此正式门禁不回退到 LibreOffice。

首次在仓库内安装已固定版本及 SHA-256 的官方二进制：

```bash
.venv/bin/python3 -m cyberppt officecli install
```

查看解析路径和实际版本：

```bash
.venv/bin/python3 -m cyberppt officecli status
```

二进制存放在 `.tools/officecli/v1.0.144/`，不会提交到 Git。解析优先级为 `CYBERPPT_OFFICECLI`、仓库内固定二进制、`PATH` 中的 `officecli`。渲染 QA 默认使用该解析结果；不可用时仍沿用 LibreOffice 回退路径。

该集成固定使用 [OfficeCLI v1.0.144](https://github.com/iOfficeAI/OfficeCLI/releases/tag/v1.0.144)，上游以 Apache-2.0 许可发布。
