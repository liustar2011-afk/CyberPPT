# CyberPPT

[简体中文](README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Português](README.pt.md) | [Español](README.es.md) | [العربية](README.ar.md)

CyberPPT 是一个 Codex Skill，用于把文档、研究材料和业务数据转化为高密度、可编辑、适用于央企、政府内部汇报的 PowerPoint 演示文稿。

默认适用场景：央企、政府及其直属单位的工作方案、阶段进展、形势研判、专题请示、项目立项和内部管理汇报。页面结构由材料类型、汇报任务和受众自适应生成，不采用固定章节顺序。外部咨询、商业提案、董事会或投资者材料需由用户明确指定。

CyberPPT 的核心不是“套模板”，而是把源材料先转成可审计证据链，再通过材料任务识别、汇报主线、页面密度规划、视觉蓝图和严格门禁，生成面向内部汇报的图片型 PPTX。默认生产模式为 `full_image_ppt`：正文区以已批准 full 图承载，标题、副标题、Logo、页码、页脚和公共模板元素由 PPT 管线生成。

## 核心能力

- 从 DOCX、PDF、TXT、XLSX、研究报告、业务材料和原始数据中提取证据、事实、数字、判断和 caveat。
- 建立证据表，先识别材料类型、汇报任务和受众，再做内容脑暴、汇报主线比较和逐页页面计划；SCR 等框架仅在明确需要时作为分析工具使用。
- 默认提供 8 种固定 CyberPPT 视觉风格，每种风格都有独立 16:9 样张。
- 生成逐页正文内容区 ImageGen 蓝图，用于锁定正文区构图、层级、密度、色板和图表语言；标题、副标题和公共模板元素由模板/可编辑文字层生成。
- 使用 `produce prepare -> produce assemble -> produce verify` 状态机消费已批准脚本、template text lock、speaker notes 和 full 图。
- 默认 `full_image_ppt` 不承诺正文区对象级可编辑；需要可编辑正文层时，必须显式启用 Legacy/Advanced editable rebuild 路径并记录交付模式。
- 执行装配产物检查、渲染比对、full-image strict manifest 校验和 delivery promotion；任一关键门禁失败，不得写入 `deliverable_ready`。

## 强制流程

1. 分析：建立证据表，记录冲突、缺口和 caveat；识别材料类型与汇报任务，脑暴 2-3 条汇报主线，收敛为适配材料的逐页计划、图表计划、信息密度和组件清单。
2. 蓝图：展示 8 种固定视觉风格；用户选择后锁定风格编号、色板、正文区网格、图表语言和页面密度，并生成逐页正文内容区 ImageGen 蓝图。
3. 生产：用 `produce prepare` 准备脚本、template text lock、page image manifest 和 speaker notes，并停在人工审批；审批后用 `produce assemble` 只消费已批准资产组装图片型 PPTX。
4. 交付：用 `produce verify` 渲染 PPTX、比对正文区 full 图、运行 full-image strict manifest 校验，并只在全部通过后复制到 `delivery/` 和写入 `deliverable_ready`。

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

使用 Git 将 CyberPPT 安装到 Codex skills 目录，并保持目录名为 `cyber-ppt`。文件夹根目录必须包含 `SKILL.md`。

```powershell
git clone https://github.com/crazyykhllc-bit/CyberPPT.git "$env:USERPROFILE\.codex\skills\cyber-ppt"
```

## 更新

```powershell
cd "$env:USERPROFILE\.codex\skills\cyber-ppt"
git pull
```

## PPTX 校验

```bash
python scripts/validate_pptx.py path/to/deck.pptx --manifest path/to/slide_manifest.json --visual-qa path/to/visual_qa_gate.json --strict --json-out path/to/report.json
```

## 本地工程入口

仓库同时提供 Python CLI、npm scripts 和 Makefile。`SKILL.md` 仍是工作流契约；CLI 只负责项目初始化、脚本确认门和仓库脚本的稳定入口。

目录归整规则见 [docs/repository-layout.md](docs/repository-layout.md)。正式项目优先放在 `projects/<project-name>/`，临时运行可放在 `image2pptx_runs/`；根目录 `images/` 只作为历史 scratch 位置，不再作为新流程默认输出目标。

### 分析表达确认门

在进入视觉设计前，项目必须按以下顺序完成五道分析表达确认门：

1. source analysis（源材料与证据分析）
2. reporting direction（汇报方向）
3. report structure（汇报结构）
4. page design（页面设计）
5. business script（页面业务稿）

业务稿确认后，第二阶段依次生成独立成果物：视觉风格候选与批准锁、蓝图输入（绘制稿）与批准记录、逐页 full 图及图片复核记录、speaker notes 审批、图片型 PPT 装配和渲染 QA。`stage-*` 只会保存待确认工件；`approve-* --option-id <id>` 才能进入下一环。用 `analysis-expression-status <project> --json` 检查第一阶段状态；Stage 2 的每个成果物都保留其上游哈希，便于定位问题。

业务稿的每个内容页均使用正式内部汇报语言，并在非上屏区域保存证据 ID、来源位置、完整性校核和信息密度单元。蓝图输入从已确认业务稿转换，只保留上屏内容、阅读关系和表达方式；不得出现证据链、来源位置、坐标、颜色、字体或最终构图等制作信息。目录、章节过渡等导航页不承载论证或证据。

新建项目自动启用该合同。已有项目只有在显式执行 `adopt-analysis-expression-contract <project>` 后才创建合同 metadata；该命令不会覆盖已有业务或页面工件，也不会替项目生成内容。

```bash
python3 -m cyberppt doctor
python3 -m cyberppt init projects/example
python3 -m cyberppt analysis-expression-status projects/example --json
python3 -m cyberppt adopt-analysis-expression-contract projects/existing-project
python3 -m cyberppt stage-script projects/example --slide 1 --kind imagegen --phase draft --source prompt.md
python3 -m cyberppt approve-script projects/example --slide 1 --kind imagegen
python3 -m cyberppt script-status projects/example --slide 1 --kind imagegen
python3 -m cyberppt produce prepare projects/example --pages 7-8
python3 -m cyberppt produce assemble projects/example --pages 7-8
python3 -m cyberppt produce verify projects/example --pages 7-8
```

Legacy/Advanced: editable rebuild remains available only when explicitly requested for object-level正文还原. It is not the default mainline, and its OCR/overlay/template-rebuild artifacts must be labeled separately from `full_image_ppt` delivery.

常用开发检查：

```bash
make doctor
make test
make test-validate-pptx
```

## 许可

MIT。详见 [LICENSE](LICENSE)。

## Acknowledgments

[SVG Repo](https://www.svgrepo.com/) · [Tabler Icons](https://github.com/tabler/tabler-icons) · [Simple Icons](https://github.com/simple-icons/simple-icons) · [Phosphor Icons](https://github.com/phosphor-icons/core) · [Robin Williams](https://en.wikipedia.org/wiki/Robin_Williams_(designer)) (CRAP principles)
