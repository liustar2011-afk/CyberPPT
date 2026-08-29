# CyberPPT

[简体中文](README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Português](README.pt.md) | [Español](README.es.md) | [العربية](README.ar.md)

CyberPPT 是一个 Codex Skill，用于把文档、研究材料、方案材料和业务数据转化为结构合宜、高密度、可审计的 PowerPoint 演示文稿。

适用场景：咨询风格 PPT，高信息密度，包括行业研究、消费品分析、品牌战略、电商分析、用户研究、高管汇报、董事会材料、客户提案和项目复盘。 不适用场景：字少的低信息密度风格，包括演讲、个人风格表达、叙事、分享、观点类 PPT。

CyberPPT 的核心不是“套模板”，而是把源材料先转成可审计证据链，再按材料类型选择方案型或咨询型架构，通过页面密度规划、视觉蓝图和严格门禁生成 PPTX。方案、研究、建设、实施和立项材料默认使用 `solution`；`consulting` 与 SCR 仅在明确选用时启用。

## 核心能力

- 从 DOCX、PDF、TXT、XLSX、研究报告、业务材料和原始数据中提取证据、事实、数字、判断和 caveat。
- 建立 MBB 标准证据表，再做内容脑暴、故事线比较、SCR 收敛和逐页页面计划。
- 默认提供 8 种固定 CyberPPT 视觉风格，每种风格都有独立 16:9 样张。
- 生成逐页正文内容区 ImageGen 蓝图，用于锁定正文区构图、层级、密度、色板和图表语言；标题、副标题和公共模板元素由模板/可编辑文字层生成。
- 使用“复杂视觉保真 + 主要文字可编辑”的混合还原策略生成 PPTX。
- 第三阶段只使用已审计 full 图 → 可编辑 SVG → 原生 PPTX 的重建链。每页先盘点可还原区域和注册图层；未验证的数据图、标识或文字必须标记 `manual_required` 并阻断交付，禁止以整页截图蒙版回退。
- 执行结构 QA、视觉 QA、可编辑性 QA、容器溢出 QA、空间锚点 QA 和曲线追踪 QA。

## 当前正式主流程

完整流程、人工停点、产物权威关系和 Stage 01 / Stage 02 边界统一见 [CyberPPT 主流程总览](docs/CYBERPPT_WORKFLOW.md)。

当前唯一正式路线为：

源材料 → Source Foundation → 业务语义理解 → 交流目标 → Outline 与页面计划 → Handoff → 逐页脚本 → 最终全稿 → Stage 02 视觉生产 → PPTX QA 与交付

Stage 01 的正式 Skill 顺序为：

`cyberppt-source-foundation` → `business-semantic-understanding` → `ppt-outline-planning` → `cyberppt-handoff` → `cyberppt-write-single-page`

旧版 MBB 证据表、故事线脑暴和固定视觉风格说明属于历史或具体生产细则，不替代上述当前主流程。

## 8 种视觉风格

| 选项 | 名称 | 样张 |
|---|---|---|
| 01 | 经典深红咨询风 | ![Palette 01](assets/palette-samples/palette-01.png) |
| 02 | 冷灰 + 勃艮第红 | ![Palette 02](assets/palette-samples/palette-02.png) |
| 03 | 暖象牙白 + 暗酒红 | ![Palette 03](assets/palette-samples/palette-03.png) |
| 04 | 象牙白 + 深蓝强调 | ![Palette 04](assets/palette-samples/palette-04.png) |
| 05 | 浅灰白 + 墨绿 | ![Palette 05](assets/palette-samples/palette-05.png) |
| 06 | 纸张米色 + 铜棕 | ![Palette 06](assets/palette-samples/palette-06.png) |
| 07 | 纯净浅灰 + 黑金 | ![Palette 07](assets/palette-samples/palette-07.png) |
| 08 | 冷白灰 + 深紫 | ![Palette 08](assets/palette-samples/palette-08.png) |

## 门禁机制

CyberPPT 内置多层门禁，防止“文件生成了，但证据、密度、可编辑性或视觉还原不合格”。

| 门禁 | 检查什么 | 失败后怎么处理 |
|---|---|---|
| Reference Gate | 每个阶段开始前是否读取对应 reference 文件 | 未读取不得进入阶段 |
| Evidence Gate | 所有事实、数字、判断、建议是否可追溯到源材料 | 缺证据必须标记缺口或返工 |
| Storyline Gate | 是否完成 2-3 条故事线脑暴、比较和 SCR 收敛 | 不能只交单版大纲 |
| Communication Strategy Gate | 是否在提纲前确认沟通对象、沟通目的、决策任务和汇报方向 | 用户未选择方向，或提纲未绑定已选策略时不得继续 |
| Density Gate | 每页是否有信息密度、组件清单、图表计划和 SO WHAT | 低密度页面必须补充或重排 |
| Style Gate | 是否展示 8 张独立 16:9 风格样张，并锁定选定风格 | 不能只给文字风格说明 |
| Blueprint Gate | 是否为全部页面生成逐页正文内容区 ImageGen 蓝图 | 蓝图未确认不得进入 PPTX |
| Asset Admission Gate | 每页图片资产是否有来源、必要性和可编辑性影响说明 | 无必要性的图片必须改为原生重建 |
| Editable Layer Gate | 主标题、正文、关键数字、图表标签、页脚、SO WHAT 是否可编辑 | 主要信息图片化即失败 |
| Visual Semantics Gate | 图表语义、曲线、面板系统、底色、层级和视觉重心是否忠实蓝图 | 不能用“可编辑”解释视觉降级 |
| Curve Trace Gate | 流线、弧线、异形边界、Ribbon、桑基图等是否精确追踪 | 粗略矩形、少点折线或默认曲线失败 |
| Spatial Registration Gate | 图标、节点、标签、箭头、曲线是否按锚点对齐 | 没重叠不代表位置合格 |
| Container Overflow Gate | 文字是否越过卡片、单元格、结论条、SO WHAT 或图表区 | 容器内溢出即失败 |
| Typography Gate | 字号是否符合固定 C0/T1-T14 层级 | 不得用无限缩字解决密度 |
| Render QA Gate | 是否逐页渲染并与蓝图对照 | 文件生成成功不等于完成 |
| Strict QA Gate | `validate_pptx.py --strict` 是否通过 manifest 和 visual QA 检查 | 出现 errors 必须返工 |

关键原则：`结构可编辑` 和 `视觉还原` 是同等硬门槛；`strict QA` 通过不等于视觉合格；ImageGen 蓝图是参考，不是最终 PPT 背景。

## 安装

克隆仓库后，从仓库根目录启动 Codex。仓库级 Skills 位于 `.agents/skills/`，无需复制或安装根目录 Skill。

```powershell
git clone https://github.com/crazyykhllc-bit/CyberPPT.git CyberPPT
```

## 更新

```powershell
cd CyberPPT
git pull
```

## PPTX 校验

```bash
.venv/bin/python3 scripts/validate_pptx.py path/to/deck.pptx --manifest path/to/slide_manifest.json --visual-qa path/to/visual_qa_gate.json --strict --json-out path/to/report.json
```

## 本地工程入口

仓库同时提供 Python CLI、npm scripts 和 Makefile。`docs/CYBERPPT_WORKFLOW.md` 是主流程总览和检索入口；`.agents/skills/` 保存各阶段唯一权威细则，CLI 负责确定性准备、校验和生产编排。

Stage 01 的权威内容产物为 `script/foundation.json`、`script/deck-plan.json` 和 `script/dist/final-script.md`。用户交互在对话中完成，不新增确认文件、状态 JSON 或平行运行目录。

目录归整规则见 [docs/repository-layout.md](docs/repository-layout.md)。正式项目优先放在 `projects/<project-name>/`，临时运行可放在 `image2pptx_runs/`；根目录 `images/` 只作为历史 scratch 位置，不再作为新流程默认输出目标。

```bash
.venv/bin/python3 -m cyberppt doctor
.venv/bin/python3 -m cyberppt init projects/example
.venv/bin/python3 -m cyberppt prepare-source-context projects/example
.venv/bin/python3 -m cyberppt prepare-script-foundation projects/example --profile script
.venv/bin/python3 -m script_engine.cli validate plan projects/example/script/deck-plan.json
.venv/bin/python3 -m script_engine.cli audit-plan projects/example/script/deck-plan.json projects/example/script/foundation.json
.venv/bin/python3 -m script_engine.cli audit-final projects/example/script/dist/final-script.json projects/example/script/deck-plan.json projects/example/script/foundation.json
.venv/bin/python3 -m script_engine.cli lint projects/example/script/dist/final-script.json
.venv/bin/python3 -m script_engine.cli check-sync projects/example/script/dist/final-script.json projects/example/script/dist/final-script.md
.venv/bin/python3 -m cyberppt final-script-pages projects/example --script projects/example/script/dist/final-script.md --production-build --assembly-mode editable
```

若脚本来自仓库外部、另一个项目或人工编辑，可在 Stage 02 直接接收：

```bash
.venv/bin/python3 -m cyberppt final-script-pages projects/example --script /path/to/external-script.md --pages 1-8 --style-id 4 --external-script --production-build
```

正式项目的最终全稿经当前主 Agent 完成 AUTHOR，并通过 `audit-final`、`lint` 及必要的 `check-sync` 后，才进入 Stage 02。`final-script-pages --production-build` 是后续唯一正式编排入口。

`final-script-pages` 默认按 `build_id` 创建新的构建目录，不覆盖既有版本；`workbench/artifact-ledger.json` 以追加方式记录每次产物，并用 `supersedes` 连接同一路径的历史版本。Stage 02 默认走 `image-to-editable-svg` 的可编辑分支：审计 full 图后准备无文字底图，将文字回写为原生 SVG，再组装 PPTX。PPTX 导出必须使用本次运行的明确输出路径，导出工程同时写入 `analysis/export_artifact.json`，续跑不会按文件修改时间猜测旧 PPTX。提示词发送默认 `--prompt-enrich off`，即消费已批准 Prompt 原文；只有明确指定 `deterministic` 或 `send` 才会进行发送时增强。

默认 `script` profile 与合同/监管等 `strict/legacy` profile 的选择、AUTHOR 写作要求和 Stage 02 门禁，以 [主流程总览](docs/CYBERPPT_WORKFLOW.md) 及其路由到的仓库级 Skill 为准；README 不复制阶段细则。

常用开发检查：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
make env-check
make doctor
make test
make test-unittest
make test-validate-pptx
```

仓库内的 Make 目标会优先使用 `.venv/bin/python`，不依赖系统全局的
`python3` 或 `pytest`。测试依赖通过 `pyproject.toml` 的 `test` extra
安装；`make test` 是 pytest 全量入口，`make test-unittest` 保留用于
兼容性回归。

## 许可

MIT。详见 [LICENSE](LICENSE)。

## Acknowledgments

[SVG Repo](https://www.svgrepo.com/) · [Tabler Icons](https://github.com/tabler/tabler-icons) · [Simple Icons](https://github.com/simple-icons/simple-icons) · [Phosphor Icons](https://github.com/phosphor-icons/core) · [Robin Williams](https://en.wikipedia.org/wiki/Robin_Williams_(designer)) (CRAP principles)
