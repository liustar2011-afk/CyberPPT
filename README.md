# CyberPPT

[简体中文](README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Português](README.pt.md) | [Español](README.es.md) | [العربية](README.ar.md)

CyberPPT 是一个 Codex Skill，用于把文档、研究材料和业务数据转化为高密度、可编辑、适用于央企、政府内部汇报的 PowerPoint 演示文稿。

默认适用场景：央企、政府及其直属单位的工作方案、阶段进展、形势研判、专题请示、项目立项和内部管理汇报。页面结构由材料类型、汇报任务和受众自适应生成，不采用固定章节顺序。外部咨询、商业提案、董事会或投资者材料需由用户明确指定。

不适用场景：字少的低信息密度风格，包括演讲、个人风格表达、叙事、分享、观点类 PPT。

CyberPPT 的核心不是“套模板”，而是把源材料先转成可审计证据链，再通过材料任务识别、汇报主线、页面密度规划、视觉蓝图和严格门禁，生成面向内部汇报的图片型 PPTX。默认生产模式为 `full_image_ppt`：正文区以已批准 full 图承载，标题、副标题、Logo、页码、页脚和公共模板元素由 PPT 管线生成。

## **使用方法（必看！）**

**安装：复制项目地址让Codex安装Skill。**

正式做PPT分为三个阶段：

**1.资料分析。**

-上传你的资料文档，明确告诉Codex：“使用XX文件夹下的CyberPPT这个skill，根据上传的文档/资料做一份PPT。”以及其他补充的要求。这个阶段会分析你的资料，出证据底稿。

-备注：这里它会自动分析、确认做多少页，如果你要指定，也可以指定。

**2.选择风格和制作蓝图。**

-这里会有8种内置的风格供你选择，选完以后，进入生成蓝图流程，会一次性把所有页面的蓝图做出来，这里还不可以编辑。

**3.生成图片型 PPT 并完成交付 QA。**

-这一阶段只走 `full_image_ppt`：先确认 full 图、speaker notes 和 template text lock，再通过 `produce prepare -> produce assemble -> produce verify` 组装套模板后的图片型 PPTX 并完成渲染 QA。正文区默认不承诺对象级可编辑。

**最后说明**

-必须经过三个阶段不可跳过。交付前必须通过渲染比对、strict QA 和依赖 freshness 检查；如果套模板后发现正文区问题，应回到对应 full 图或脚本锁定阶段返工，不要只在最终 PPT 中手工修补。

## 核心能力

- 从 DOCX、PDF、TXT、XLSX、研究报告、业务材料和原始数据中提取证据、事实、数字、判断和 caveat。
- 建立证据表，先识别材料类型、汇报任务和受众，再做内容脑暴、汇报主线比较和逐页页面计划；SCR 等框架仅在明确需要时作为分析工具使用。
- 默认提供 8 种固定 CyberPPT 视觉风格，每种风格都有独立 16:9 样张。
- 生成逐页正文内容区 ImageGen 蓝图，用于锁定正文区构图、层级、密度、色板和图表语言；标题、副标题和公共模板元素由模板/可编辑文字层生成。
- 使用 `produce prepare -> produce assemble -> produce verify` 状态机消费已批准脚本、template text lock、speaker notes 和 full 图。
- 默认 `full_image_ppt` 不承诺正文区对象级可编辑。
- 执行装配产物检查、渲染比对、full-image strict manifest 校验和 delivery promotion；任一关键门禁失败，不得写入 `deliverable_ready`。

## 强制流程

1. 分析：建立证据表，记录冲突、缺口和 caveat；识别材料类型与汇报任务，脑暴 2-3 条汇报主线，收敛为适配材料的逐页计划、图表计划、信息密度和组件清单。
2. 蓝图：展示 8 种固定视觉风格；用户选择后锁定风格编号、色板、正文区网格、图表语言和页面密度，并生成逐页正文内容区 ImageGen 蓝图。
3. 生产：用 `produce prepare` 准备脚本、template text lock、page image manifest 和 speaker notes，并停在人工审批；审批后用 `produce assemble` 只消费已批准资产组装图片型 PPTX。
4. 交付：用 `produce verify` 渲染 PPTX、比对正文区 full 图、运行 full-image strict manifest 校验，并只在全部通过后复制到 `delivery/` 和写入 `deliverable_ready`。

## ImageGen 提示词与交付文字 QA

第二阶段的 `imagegen_script.md` 是人工可检查、可修改的生图提示词源文件。页面内容锁定是唯一的页面可见文字来源；`【页面类型】`、`【内容锁定】`、`【构图指令】`、`【结构密度】` 等控制区只面向模型，不得把编译策略、过程说明、审阅意见、占位内容、执行元数据或调试标记写入页面。人工修改 MD 后，必须先通过 `imagegen_script.validation.json` 校验，再生成 full 图。

主流程逐页 FULL 图由 Codex 内置 `IMAGE_GEN` 执行：原样消费 `page_image_pairs.json` 的 `full.prompt`，并将结果写入同一条记录的 `full.path`。这只替换生图执行器；现有尺寸处理、运行记录、image-text QA、审批和 PPT 组装不变。

生成 full 图后必须运行 image-text QA，再执行 `produce verify`：

```bash
python3 -m cyberppt image-text-qa <project> --pages <range>
python3 -m cyberppt produce verify <project> --pages <range>
```

OCR 结果只作为待核对证据，不能替代确定性判定。`failed` 或 `review_required` 都会阻断交付，不得写入 `deliverable_ready`；检查不通过时回到 `imagegen_script.md` 或页面内容锁定返工。

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
| Asset Gate | `full_image_ppt` 是否只消费已批准 full 图 | 正文 full 图必须来自审批记录 |
| Template Text Gate | 标题、副标题、Logo、页码、页脚和公共模板元素是否来自 `template_text_lock` 并由 PPT 管线生成 | 模板文字层不匹配即失败 |
| Speaker Notes Gate | `speaker_notes_manifest.json` 是否已人工批准且未变化 | 未批准或 hash 变化即失败 |
| Render QA Gate | `produce verify` 是否渲染并比对 PPTX 正文区与 approved full 图 | 文件生成成功不等于完成 |
| Strict QA Gate | full-image delivery manifest 是否通过 `validate_pptx.py --strict` | 出现 errors 必须返工 |
| Dependency Freshness Gate | assembly、approved images、notes、template lock、visual report、strict report 和 delivery PPTX hash 是否仍然当前 | 任一依赖变化，`deliverable_ready` 失效 |

关键原则：默认 `full_image_ppt` 不要求正文区主要文字可编辑，但必须如实声明 `body_content_editable=false`，并守住模板文字层、speaker notes、渲染比对、strict QA 和依赖 freshness。

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
