# ppt-script V3.7.0

## V3.7.0 经验增强版

V3.7.0 在 V3.6 的双重独立阅读、综合裁决和证据图谱之后增加已批准案例检索。案例只提供方法、失败模式和修改理由，不参与事实抽取，也不能生成 Source ID。只有 `status=approved` 的案例进入索引。

## V3.5.1 深度材料解读修复版

V3.5.1 保留 V3.5 的任务路由、状态机、结构化合同和模块化工作台，同时修复过度压缩 Prompt 导致的复杂材料解读能力下降。深度解读内核在 Stage 1 全流程常驻；正式项目默认生成 `deep` 活动上下文，嵌入源材料正文、当前分析、Source Truth Map、决策稿、提纲和结构化合同。活动上下文只是一份工作集，不能替代对 `source/` 中全部材料的直接阅读。

## V3.3 正式汇报场景

新建项目默认使用 `government-soe-formal`，并在 `project.json` 写入 `report_subtype`、`decision_intent`、`audience_level`、`project_phase`。四项均为必填项目契约。正式组装前运行：

```bash
python3 scripts/project_manager.py style-check <项目名或路径>
python3 scripts/project_manager.py notes-check <项目名或路径>
```

四维场景配置见 `config/reporting-modes.yaml`；页面字段、密度、语义图与落图策略仍以 `config/rules.yaml` 为唯一权威来源。

将正式材料准确解读为内部汇报型PPT脚本，并衔接AI生图Prompt的统一技能。V3保留原有“材料分析—决策稿—提纲—逐页脚本—自检—三类组装输出—Stage 2视觉转译”生产链，新增Source Truth Map、章节合同、100分评价、四道质量闸门、智能优化回归和版本比较。

## 六种运行模式

| 模式 | 用途 |
|---|---|
| `source-interpret` | 只解读源材料并建立Source Truth Map |
| `script-from-source` | 从源材料形成故事线、章节规划、页面规划和完整脚本 |
| `evaluate-script` | 对已有脚本进行100分评价和四道闸门判定 |
| `optimize-script` | 在保持来源准确性和覆盖的前提下重构脚本 |
| `compare-scripts` | 比较两个脚本版本的内容覆盖、结构和表达变化 |
| `full-pipeline` | 完成解读、规划、编写、评估、优化和追溯回归 |

## 主流程

```text
源材料
→ 深度材料分析
→ Source Truth Map
→ 材料理解闸门
→ 内容取舍
→ 整套故事线
→ 章节合同
→ 页面合同
→ 逐页脚本
→ 100分评价
→ 智能优化
→ 追溯回归
→ Stage 2视觉制作
```

章节规划是页面规划的必经层。不得由源材料直接跳到逐页脚本。

政府、央企正式汇报必须执行总编工作流：

```text
全文语义理解 → Source Truth → 独立认知 → 语义规划合同
→ 总编独立判断 → 多结构竞争 → 总编结构裁决
→ 章节页面规划 → 总编提纲审稿 → 反方审稿 → 页面脚本
```

总编闸门失败时，其结论覆盖 `plan-check` 的通过状态并阻断页面生成；只有完成定向返工并重新通过相应 `editorial-check` 后才能进入页面脚本。

## 四道质量闸门

1. 源材料理解闸门
2. 故事线、章节与页面规划闸门
3. 逐页脚本编写闸门
4. 优化后追溯回归闸门

任一闸门失败时，即使综合分数较高，也不得判定为具备执行条件。

## 100分评价

| 维度 | 分值 |
|---|---:|
| 源材料理解、准确性与内容覆盖 | 30 |
| 故事线、章节结构与决策逻辑 | 15 |
| 页面规划、必要性与单页聚焦 | 15 |
| 页面内部论证与证据完整性 | 10 |
| 汇报对象、场景与决策需求匹配 | 8 |
| 上屏表达、信息密度与可读性 | 10 |
| 图形化表达与视觉施工可执行性 | 7 |
| 术语、口径、格式与合规一致性 | 5 |

## 项目结构

```text
projects/<项目名>/
├── source/
├── analysis/
│   ├── 00-analysis.md
│   ├── 00-source-inventory.md
│   ├── 01-source-truth-map.md
│   └── 02-understanding-gate.md
├── decision/01-decision.md
├── outline/
│   ├── 02-outline.md
│   └── 02-plan-audit.md
├── contracts/
│   ├── source-truth.json
│   ├── deck-decision.json
│   ├── chapter-contracts.json
│   └── page-contracts.json
├── pages/
├── review/
│   ├── 04-review.md
│   ├── 05-evaluation.md
│   └── 05-machine-audit.md
├── comparison/
├── approvals/
└── output/
```

## Codex 原生使用

仓库级Codex入口为 `.agents/skills/ppt-script/SKILL.md`，Claude入口为 `.claude/skills/ppt-script/SKILL.md`。使用Codex打开本仓库后，可直接要求对TXT、MD、DOCX、PPTX或PDF正式材料执行解读、章节规划、脚本编写、评估和优化。

## 快速开始

```bash
python3 scripts/project_manager.py init 项目名称
```

将MD、TXT、DOCX、PPTX或PDF源材料放入 `projects/项目名称/source/`。

```bash
python3 scripts/project_manager.py route 项目名称
python3 scripts/project_manager.py state 项目名称
python3 scripts/project_manager.py context-pack 项目名称 deep
python3 scripts/project_manager.py source-inventory 项目名称
python3 scripts/project_manager.py understanding-check 项目名称
python3 scripts/project_manager.py cognitive-init 项目名称
python3 scripts/project_manager.py cognitive-pack 项目名称 faithful
python3 scripts/project_manager.py cognitive-pack 项目名称 decision
python3 scripts/project_manager.py cognitive-pack 项目名称 reconcile
python3 scripts/project_manager.py cognitive-check 项目名称
python3 scripts/project_manager.py evidence-check 项目名称
python3 scripts/project_manager.py trace-claim 项目名称 C001
python3 scripts/project_manager.py case-index
python3 scripts/project_manager.py case-search "运营机制 领导审议" 5
python3 scripts/project_manager.py experience-pack 项目名称
python3 scripts/project_manager.py case-capture 项目名称
python3 scripts/project_manager.py contract-check 项目名称
python3 scripts/project_manager.py editorial-init 项目名称
python3 scripts/project_manager.py editorial-pack 项目名称 independent
python3 scripts/project_manager.py editorial-check 项目名称 semantic-planning
python3 scripts/project_manager.py editorial-pack 项目名称 storyline
python3 scripts/project_manager.py editorial-check 项目名称 storyline
python3 scripts/project_manager.py plan-check 项目名称
python3 scripts/project_manager.py editorial-check 项目名称 outline
python3 scripts/project_manager.py editorial-pack 项目名称 red-team
python3 scripts/project_manager.py editorial-check 项目名称 red-team
python3 scripts/project_manager.py audit 项目名称
python3 scripts/project_manager.py quality-check 项目名称
python3 scripts/project_manager.py notes-check 项目名称
python3 scripts/project_manager.py compare 项目名称 原稿.md 修订稿.md
python3 scripts/project_manager.py run 项目名称
```

`route` 确定任务路径，`state` 根据实际成果推导阶段，`context-pack` 在 deep 模式下生成包含源材料和项目事实的活动工作集；`understanding-check` 检查材料分析和 P0 来源底稿是否达到进入故事线阶段的最低要求；`contract-check` 检查机器可读合同。`run` 会按项目当前状态自动执行材料清点、规划检查、上屏正式性、标题质量、全稿一致性、脚本审计、来源核查、讲解词检查和组装；硬规则未通过时会报告具体页码并暂停。遇到需要模型生成 Source Truth Map、提纲或页面的阶段会提示下一步，不会绕过人工确认。

生图输出仅包含“内容页”。`script-imagegen.md` 将页面结论、内容关系、视觉要求以及讲解词中的核心讲解、重点强调和边界说明，转译为自然语言视觉提示词；只有每页【画面文字白名单】中的文字允许上屏，开场承接、转场语和预计讲解时长不会进入生图脚本。

原有命令全部保留：

```bash
python3 scripts/project_manager.py status 项目名称
python3 scripts/project_manager.py new-page 项目名称 05 数据平台架构
python3 scripts/project_manager.py rhythm-check 项目名称
python3 scripts/project_manager.py custom-types 项目名称
python3 scripts/project_manager.py check-coverage 项目名称 [pXX]
python3 scripts/project_manager.py evidence-usage 项目名称
python3 scripts/project_manager.py gap-summary 项目名称
python3 scripts/project_manager.py approve 项目名称 <步骤或页面>
python3 scripts/project_manager.py assemble 项目名称
```

## 组装输出

`assemble`继续生成：

- `output/script-final.md`：完整审稿、溯源和返修版
- `output/script-imagegen.md`：可逐页直接提交给 IMAGE-2 的自然语言生图提示词
- `output/outline-index.json`：机器索引
- `output/script-speaker-notes.md`：完整讲解词
- `output/speaker-notes.json`：结构化备注数据

`script-imagegen.md` 按“第X页”逐页复制给 IMAGE-2 使用。

## Source Truth Map

新项目统一使用 `S001`、`S002`等来源ID，并区分：

- F：事实
- P：政策要求
- J：判断
- I：推断
- R：建议
- B：边界或条件
- U：待核事项

每条同时记录P0/P1/P2重要性、状态、主体、数字和时间、条件和边界、原文出处及冲突说明。旧项目的F01编号仍可读取，但新项目不再创建两套编号。

## 交互配置

`project.json`支持：

```json
{
  "interaction_mode": "gated",
  "batch_pages": 3,
  "source_truth_mode": "full",
  "context_mode": "deep",
  "understanding_gate_required": true,
  "cognitive_gate_required": true,
  "experience_mode": "enabled"
}
```

`gated`适用于正式重大材料；`batch`适用于提纲已经确认的批量页面生成。默认每3页暂停一次。正式材料使用 `deep`；`compact` 仅适用于已经完成事实核验后的轻量修改，不得替代源材料阅读。

## 安装

```bash
./install.sh --target codex
./install.sh --target claude
./install.sh --target both
```

默认安装：

- `~/.codex/skills/ppt-script` 与 `~/.codex/skills/chapter-structure-review`
- 或 Claude 对应路径 `~/.claude/skills/...`

仓库内权威路径为 `.agents/skills/ppt-script/` 与 `.agents/skills/chapter-structure-review/`（Codex 在本仓库工作即可直接发现）。目标已存在时使用 `--force`。

## 依赖与测试

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```

## 维护与发布诊断

```bash
python3 scripts/project_manager.py version
python3 scripts/project_manager.py doctor
python3 scripts/repository_consistency.py
python3 scripts/release_check.py --quick
python3 scripts/release_check.py
```

`doctor` 检查 Python、依赖、配置、Skill 入口和仓库一致性；`release_check.py` 在正式发布前执行编译、测试和临时安装复测。


## V3.6 认知增强工作流

正式材料在完成深度材料分析和 Source Truth Map 后，必须分别完成忠实阅读与决策阅读。两个上下文均只包含源材料、当前项目事实和各自规则，不包含另一份阅读成果或历史案例。两份阅读完成后生成综合裁决上下文，并把最终命题写入 `contracts/evidence-graph.json`。只有 `cognitive-check` 通过后，项目才进入故事线阶段。

```text
源材料与 Source Truth
→ 忠实阅读
→ 决策阅读
→ 综合裁决
→ 证据图谱
→ 认知增强闸门
→ 已批准经验案例检索（仅供方法参考）
→ 故事线与页面规划
```

## V3.7 经验增强工作流

认知闸门通过后运行 `case-index` 和 `experience-pack`。检索综合任务类型、汇报对象、报告子类型、问题类型、标签和文本相似度，并对不适用条件进行惩罚。生成的 `analysis/00-experience-context.md` 明确标记为“仅供方法参考”。

项目修改得到确认后，在 `experience/feedback-capture.json` 中记录原输出、最终版本、修改原因、适用条件、不适用条件、正向模式和反模式，将状态改为 `approved`，再运行 `case-capture`。未批准案例不会进入索引。
