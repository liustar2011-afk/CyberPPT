# PPT页面脚本视觉重构 Skill

> **CyberPPT 说明：** 本目录仅作构图规则来源对照，**不是**生产入口。  
> 上屏/视觉结构纪律已吸收至仓库 `references/script-quality.md` 与 `cyberppt.script_quality_contract`。  
> 正式脚本流程请使用根目录 `SKILL.md`（cyber-ppt）与 `python -m cyberppt script-audit`。

该Skill用于把已有的逐页PPT脚本重新进行视觉设计，并输出一份适合Codex后续逐页生图的新脚本。

它位于内容脚本和图片生成之间：

```text
原始PPT脚本
→ 内容理解与页面使命判断
→ 业务关系转为空间关系
→ 视觉构图重构
→ 新的Markdown生图脚本
→ Codex逐页生图
```

## 能做什么

- 完整读取整套脚本，而不是孤立处理单页。
- 保留标题、终稿文字、数据、单位、专有名词和业务关系。
- 重做页面构图、主链、视觉中心、空间占比和配图方式。
- 为每页输出页面使命、核心结论、视觉主张、草图、框位置、箭头关系和禁止事项。
- 输出适合人工预审和Codex生图的Markdown脚本。
- 自动检查页码、固定章节、空章节、`overlay`字段、星号列表和关系页缺失箭头等问题。

## 不做什么

- 不生成图片。
- 不调用图像模型。
- 不生成HTML、SVG或PPTX。
- 不机械套用模板库。
- 不默认拆页、并页或改变页序。

## 目录结构

```text
ppt-script-visual-redesign/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── assets/
│   ├── default-profile-cec.yaml
│   ├── redesigned-script-template.md
│   ├── example-input.md
│   └── example-output.md
├── references/
│   ├── semantic-analysis.md
│   ├── visual-design-principles.md
│   ├── composition-grammar.md
│   ├── government-enterprise-style.md
│   ├── script-contract.md
│   ├── codex-handoff.md
│   ├── visual-qa.md
│   └── source-notes.md
├── scripts/
│   ├── install.sh
│   ├── install.ps1
│   └── validate_script.py
└── tests/
    └── test_validate_script.py
```

## 安装到Codex

Codex当前支持从用户级`$HOME/.agents/skills`和项目级`.agents/skills`读取Skill。

### macOS或Linux：用户级安装

```bash
cd ppt-script-visual-redesign
bash scripts/install.sh user
```

### macOS或Linux：当前项目安装

```bash
bash scripts/install.sh repo
```

### 兼容旧版Codex目录

```bash
bash scripts/install.sh legacy-codex
```

### Windows PowerShell：用户级安装

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Scope User
```

### Windows PowerShell：当前项目安装

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Scope Repo
```

安装后可在Codex中使用：

```text
$ppt-script-visual-redesign
```

Codex通常会自动发现Skill；未显示时重启Codex。

## 推荐调用方式

```text
$ppt-script-visual-redesign
读取“某项目PPT脚本.md”，保持所有终稿文字、数字和业务关系，
对整套页面进行视觉重构，输出“某项目PPT脚本_视觉重构.md”，
保持原页数和页序，最后运行校验脚本。
```

只处理一页时：

```text
$ppt-script-visual-redesign
只重构第7页。先结合前后页判断本页使命，再重新设计构图并输出完整页面脚本。
```

提供视觉参考时：

```text
$ppt-script-visual-redesign
以参考页面A作为视觉语言参考，保留其空间节奏和层级，不复制其具体内容和装饰，
重构脚本中的第4至第8页。
```

## 校验输出脚本

```bash
python3 scripts/validate_script.py path/to/your_视觉重构.md
```

输出JSON结果：

```bash
python3 scripts/validate_script.py path/to/your_视觉重构.md --json
```

运行测试：

```bash
python3 -m unittest discover -s tests -v
```

## 默认输出格式

每页固定包含：

- 页面角色
- 页面使命
- 核心结论
- 内容保真要求
- 视觉主张
- 页面草图
- 页面构图
- 元素与空间关系
- 箭头与连接关系
- 终稿文字
- 视觉设计要求
- 禁止事项
- Codex生图执行摘要

详见`references/script-contract.md`和`assets/redesigned-script-template.md`。

## 设计来源

该Skill为独立实现，设计思想参考了Figma Slides的内容驱动构图原则、Frontend Slides的反通用AI审美规则，以及Powerpoint Fancy Design的逐页Markdown输入和几何结构保护思路。具体出处见`references/source-notes.md`。
