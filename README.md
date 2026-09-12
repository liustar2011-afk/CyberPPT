# CyberPPT

[简体中文](README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Português](README.pt.md) | [Español](README.es.md) | [العربية](README.ar.md)

CyberPPT 是一个把逐页脚本转换成 PowerPoint 的小工具。它优先解决三件事：

- 把脚本生成成完整 PPT 页面图片；
- 已成功页面可以直接续跑，不重复生成；
- 需要时把同一套页面继续转换为可编辑 PPTX。

内部仍保留文字检查、构建记录和可编辑页验证，但普通使用不需要理解这些流程概念。

## 最简单的用法

准备一个带页码的 Markdown 脚本，然后执行：

```bash
cyberppt build ./script.md
```

默认行为：

- 自动识别脚本中的全部页面；
- 自动创建 `<脚本名>.cyberppt` 工作目录；
- 自动生成页面图片；
- 默认输出图片版 PPTX；
- 再次执行同一个命令时，自动复用已经通过的页面，只继续未完成部分。

如果脚本已经位于初始化过的 CyberPPT 项目中，会直接复用该项目，不再创建额外工作目录。

### 输出可编辑 PPT

```bash
cyberppt build ./script.md --mode editable
```

### 同时输出图片版和可编辑版

```bash
cyberppt build ./script.md --mode both
```

可编辑模式沿用同一张已经验收的完整页面图。若当前页需要本地 SVG 拆层或视觉复核，命令会返回 `needs_action`；完成提示的当前页操作后，再执行同一个 `cyberppt build` 命令即可继续，不需要重新生成已经完成的页面。

### 只生成部分页面

```bash
cyberppt build ./script.md --pages 3-6
```

也可以使用离散页码：

```bash
cyberppt build ./script.md --pages 1,3,5
```

### 指定工作目录

```bash
cyberppt build ./script.md --project ./my-ppt-workspace
```

### 强制重画

默认会复用已经通过的页面。如果明确需要全部重新生成：

```bash
cyberppt build ./script.md --force
```

## 脚本格式

最简单的脚本只需要页标题和正文：

```markdown
## P01 项目背景

国家数据基础设施建设持续推进，行业侧需要形成稳定的数据资源组织、可信流通和应用服务能力。

## P02 建设思路

围绕数据资源、基础能力、业务场景和持续运营形成一体化建设路径。
```

也可以使用 CyberPPT 的结构化页面脚本。新脚本支持 `完整文字稿 + 保真文字`：普通正文允许在生成阶段提炼和改写，少量必须准确出现的数字、正式名称或固定字符串可以单独声明。

例如：

```markdown
## P03 建设目标

- 页面类型：内容页
- 页面标题：建设目标

### 完整文字稿

到2028年形成稳定的数据服务能力，并持续服务真实业务场景。

### 保真文字

- [required] 2028年
```

`保真文字` 是一个小型文字保护功能，不是另一套上屏稿。普通文案不需要逐字锁定。

## 从原始材料开始

如果你只有 DOCX、PDF、TXT、XLSX、研究报告或业务材料，可以继续使用仓库现有的脚本工作流先生成 `final-script.md`，再交给 `cyberppt build`。

默认的轻量脚本路线：

```bash
cyberppt init projects/example
cyberppt prepare-source-context projects/example
cyberppt prepare-script-foundation projects/example --profile script
```

随后由 Agent 完成分页、脚本撰写和必要审核。详细方法见 [CyberPPT 主流程总览](docs/CYBERPPT_WORKFLOW.md)。这些属于脚本生产能力，不是 `build` 的使用前置条件。

## 高级入口

`cyberppt build` 是普通使用入口。仓库仍保留原来的高级命令，供调试、迁移和精细控制使用，例如：

```bash
cyberppt final-script-pages ...
cyberppt stage-script ...
cyberppt script-status ...
cyberppt stage02-handoff-check ...
```

这些命令继续复用现有 Stage 02 实现，但不再要求普通用户把内部阶段、审计回执和构建身份当作日常操作对象。

## 当前视觉路线

页面制作仍遵循一个简单原则：

> 先生成完整页面视觉稿，再在需要时基于这张图进行可编辑重建。

这样可以优先保证构图、层级、配色和整体视觉质量，同时保留后续可编辑输出能力。仓库当前正式可编辑路线仍是 full image → SVG → PPTX；底层 QA 和复用机制继续存在，但由工具自动管理。

## 安装

```bash
git clone https://github.com/liustar2011-afk/CyberPPT.git CyberPPT
cd CyberPPT
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

之后可以直接使用：

```bash
cyberppt build ./script.md
```

也可以不安装命令，直接从仓库运行：

```bash
.venv/bin/python -m cyberppt build ./script.md
```

## 常用开发检查

```bash
make env-check
make doctor
make test
make test-unittest
make test-validate-pptx
```

高级流程、内部合同和开发者约束统一放在 `docs/`、`AGENTS.md` 和 `.agents/skills/` 中维护，不再作为 README 的主使用路径。

## 许可

MIT。详见 [LICENSE](LICENSE)。

## Acknowledgments

[SVG Repo](https://www.svgrepo.com/) · [Tabler Icons](https://github.com/tabler/tabler-icons) · [Simple Icons](https://github.com/simple-icons/simple-icons) · [Phosphor Icons](https://github.com/phosphor-icons/core)
