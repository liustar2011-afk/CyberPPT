# PPT脚本编译器

将 DOCX、PDF、Markdown、TXT 或 PPTX 源材料分阶段编译为可审查、可追溯的PPT脚本。

本工具不采用“源材料一次性直出最终脚本”的方式，而是固定执行：

```text
源材料确定性解析
→ 信息资产
→ 页面规划卡
→ 上屏文字
→ 视觉意图与构图
→ 独立质量审查
→ Markdown / JSON / YAML / ZIP 导出
```

## 核心能力

- 每个来源段落、表格行或PDF文本块自动生成唯一 `source_id`。
- 信息资产、页面规划和上屏文案全部保留来源追溯关系。
- 每个阶段使用 JSON Schema 约束 Codex 输出，降低结构漂移。
- 支持人工修改任一阶段；修改后自动将后续阶段标记为需要重跑。
- 支持阶段锁定、局部重跑和一键生成。
- 长材料自动分块解析，再进行资产归并。
- 本地执行来源编号、覆盖率、页面纯度、跨页引用、字数和禁用句式检查。
- 独立语义审查检查原文忠实度、核心覆盖度、页面纯度和视觉一致性。
- Codex以只读沙箱运行，不启用网页搜索，不允许源材料中的指令改变任务。

## Windows安装

1. 解压本项目。
2. 双击 `setup_windows.bat`。
3. 如提示未登录，在命令提示符中运行：

```powershell
codex login
```

选择 **Sign in with ChatGPT**。

4. 双击 `start_windows.bat`。
5. 浏览器打开 `http://127.0.0.1:8501`。

Codex CLI官方说明：

- https://developers.openai.com/codex/cli
- https://developers.openai.com/codex/cli/reference

## 使用步骤

1. 左侧创建项目。
2. 在“源材料”页上传并解析文件。
3. 根据项目需要修改“配置”中的YAML规则。
4. 逐阶段生成并人工审查，或点击“一键运行至最终脚本”。
5. 对重要项目，建议依次锁定“信息资产”“页面规划”“上屏文字”后再生成视觉构图。
6. 在“导出”页下载：
   - `ppt_script.md`：完整PPT脚本；
   - `ppt_script_bundle.json`：机器可读全量数据；
   - `ppt_script_bundle.yaml`：便于人工维护的中间表示；
   - ZIP：项目完整归档。

## 支持的源文件

| 格式 | 说明 |
|---|---|
| DOCX | 解析段落、标题样式和表格行 |
| PDF | 解析可复制文本；扫描版PDF需要先OCR |
| Markdown | 保留标题层级和段落 |
| TXT | 按段落解析，并启用简单标题识别 |
| PPTX | 提取现有页面标题和文本，用于重构脚本 |

暂不直接支持旧版 `.doc`，请先另存为 `.docx`。

## Codex调用方式

工具使用非交互命令 `codex exec`，并启用：

- `--output-schema`：约束最终JSON结构；
- `--output-last-message`：将最终结果写入阶段文件；
- `--sandbox read-only`：模型只能读取项目文件；
- `--ephemeral`：不保存每次阶段运行的会话记录；
- `--skip-git-repo-check`：允许在普通项目目录中运行。

工具会先执行 `codex login status` 检查登录状态。模型和额度使用当前Codex登录账户的配置；“模型覆盖”留空时使用Codex默认模型。

## 项目目录

```text
workspaces/<项目>/
├─ project.json
├─ profile.yaml
├─ source/
│  ├─ original/
│  ├─ source_blocks.json
│  └─ source_readable.md
├─ stages/
│  ├─ 01_information_assets.json
│  ├─ 02_page_plan.json
│  ├─ 03_screen_copy.json
│  ├─ 04_visual_plan.json
│  └─ 05_audit.json
├─ logs/
└─ exports/
```

## 命令行用法

检查Codex：

```powershell
python cli.py check
```

一键运行：

```powershell
python cli.py run "D:\材料\汇报.docx" --name "汇报项目"
```

离线流程测试：

```powershell
python cli.py run samples\demo.md --name "演示项目" --mock
```

## 测试

```powershell
python -m pytest
```

## 数据边界

源材料首先在本地解析和编号。语义阶段会由本机Codex CLI读取对应项目文件，内容将按用户的Codex账户和工作区数据政策处理。涉及敏感材料时，应先确认所在组织的Codex使用政策和数据控制设置。
