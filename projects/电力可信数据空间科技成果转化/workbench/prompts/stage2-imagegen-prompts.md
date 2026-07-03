# Stage 2 ImageGen Prompts

本文件为逐页蓝图生图脚本的明文保存版本。后续若重生蓝图，应先修改本文件，再执行 ImageGen。

## 全局视觉锁定

- 风格编号：04
- 风格名称：象牙白 + 深蓝强调
- 背景：`#F7F6F0`
- 强调色：`#12355B`
- 标题：`#101820`
- 正文：`#303030`
- 次级文字：`#6F7275`
- 线条：`#C9CDD1`
- 目标语言：中文
- 语气：中电联内部立项汇报，正式、稳健、内部材料口径，不使用外部咨询顾问口吻。

## Slide 01 Prompt

```text
Use case: productivity-visual
Asset type: 16:9 PowerPoint blueprint, slide 01 cover
Primary request: Generate a polished 16:9 bitmap blueprint for an internal China Electricity Council leadership briefing cover. Target language Chinese. Exact visible title: “电力行业科技成果转化可信数据空间场景建设方案汇报”. Subtitle: “内部立项汇报”. Include small footer placeholders for 汇报单位：中国电力企业联合会科技服务中心, 汇报人：中电联内部人员, 日期：2026年. Visual style locked: CyberPPT option 04 象牙白 + 深蓝强调; warm ivory background #F7F6F0, deep blue accent #12355B, black title #101820, restrained gray lines #C9CDD1. Formal internal reporting tone, not advertising, not external consulting. Composition: low-density formal cover, left-aligned title block, subtle abstract trusted-data-space network motif in deep blue linework on the right, clean official document feel, 16:9, high resolution. Avoid logos, avoid fake seals, avoid English, avoid excessive slogans, avoid dark dashboard style.
```

## Slide 02 Prompt

```text
Use case: productivity-visual
Asset type: 16:9 PowerPoint blueprint, slide 02
Primary request: Generate a high-density Chinese internal briefing slide blueprint titled “项目建设背景”. Subtitle: “国家战略、行业转型与中电联职能叠加形成建设窗口期”. Visual style locked: CyberPPT option 04 象牙白 + 深蓝强调; background #F7F6F0, deep blue #12355B, black #101820, restrained gray #C9CDD1. Formal CEC internal report, not external consulting. Layout: top header with page title; main content as a horizontal policy-and-industry timeline with three bands: 国家战略, 新型电力系统, 中电联职能; right-side compact evidence panel with 3 policy references; bottom SO WHAT band: “项目具备内部立项的政策与职能基础”. Use Chinese labels, dense but readable, table/line/timeline style, small source footer. Avoid marketing slogans, avoid dark dashboard, avoid English, avoid fake logos.
```

## Slide 03 Prompt

```text
Use case: productivity-visual
Asset type: 16:9 PowerPoint blueprint, slide 03
Primary request: Generate a high-density Chinese internal briefing slide blueprint titled “项目建设必要性”. Subtitle: “成果转化痛点集中表现为跨主体可信协同能力不足”. Visual style locked: CyberPPT option 04, ivory background #F7F6F0, deep blue accent #12355B, gray dividers #C9CDD1, formal internal report. Layout: left vertical funnel showing “科研成果” to “产业化转化” with a highlighted key figure “不到10%” and caveat tag “需背书”; center 2x3 matrix of six pain points: 数据孤岛, 产权保护难, 价值评估不可信, 履约追溯弱, 科技金融难介入, 监管服务缺载体; right narrow panel showing root cause “缺少可信数据流通与全链可溯机制”; bottom SO WHAT band: “必要性不在于再建信息平台，而在于补齐跨主体信任基础设施”. Chinese labels, dense but readable, official tone. Avoid English, avoid marketing visuals, avoid dark dashboard.
```

## Slide 04 Prompt

```text
Use case: productivity-visual
Asset type: 16:9 PowerPoint blueprint, slide 04
Primary request: Generate a high-density Chinese internal briefing slide blueprint titled “项目建设可行性”. Subtitle: “政策授权、技术路径、行业资源和市场需求具备同步支撑”. Visual style locked: CyberPPT option 04, ivory #F7F6F0, deep blue #12355B, black #101820, formal internal report. Layout: 2x2 feasibility matrix with four panels: 政策可行性, 技术可行性, 资源可行性, 市场可行性. Each panel has 3 evidence bullets and a small icon, with a narrow right-side caveat column “需进一步确认事项” including 数据口径, 资金安排, 试点名单. Bottom conclusion band: “项目具备启动内部立项论证的基础条件”. Dense but orderly, official document style, no marketing, no English, no fake logos.
```

## Slide 05 Prompt

```text
Use case: productivity-visual
Asset type: 16:9 PowerPoint blueprint, slide 05
Primary request: Generate a high-density Chinese internal briefing slide blueprint titled “总体思路与建设目标”. Subtitle: “以 1+2+6+N 架构推进短中长期分阶段建设”. Visual style locked: CyberPPT option 04, ivory #F7F6F0, deep blue #12355B, formal internal report. Layout: left main diagram showing “1 个底座 + 2 套体系 + 6 大核心场景 + N 个生态节点” as a structured stack or hub architecture; right column with three goal bands: 短期目标（1年内）, 中期目标（2-3年）, 长期目标（3-5年）. Include KPI chips: 50家主体, 1000项成果, 3-5个标杆项目, 1000家主体, 10000项成果, 交易超10亿元, 5000家主体, 交易超50亿元. Bottom note: “建设目标按试点先行、逐步推广、生态深化推进”. Chinese text, dense but readable, official, no English, no fake logos.
```

## Slide 06 Prompt

```text
Use case: productivity-visual
Asset type: 16:9 PowerPoint blueprint, slide 06
Primary request: Generate a Chinese internal briefing slide blueprint titled “总体架构设计”. Subtitle: “以可信数据空间底座承载标准、安全、场景和生态节点”. Visual style locked: CyberPPT option 04, ivory #F7F6F0, deep blue #12355B, gray #C9CDD1. Layout: large central layered architecture diagram. Bottom layer: “1 个底座：电力行业科技成果转化可信数据空间”. Middle support layers: “标准规范体系” and “安全保障体系” as two horizontal rails. Top layer: six application blocks, and outer ring or side labels for “N 个生态节点”. Include flow arrows from ecosystem nodes to scenarios to trusted data space base. Bottom SO WHAT band: “总体架构需同时支撑公共服务、可信流通和生态协同”. Dense but formal, Chinese labels, no English, no fake logos, no dark dashboard.
```

## Slide 07 Prompt

```text
Use case: productivity-visual
Asset type: 16:9 PowerPoint blueprint, slide 07
Primary request: Generate a Chinese internal briefing slide blueprint titled “分层技术架构”. Subtitle: “五层技术架构支撑成果转化数据可信流通与全链监管”. Visual style locked: CyberPPT option 04, ivory background #F7F6F0, deep blue #12355B, restrained gray lines. Layout: full-width five-layer architecture stack from top to bottom: 用户层, 场景应用层, 核心能力层, 可信数据空间底座层, 基础设施层. In the trusted data space base layer show 8 modules: 权属管理, 隐私计算, 区块链存证, 数据治理, 智能合约, 交易结算, 节点管理, 监管审计. Right side slim column: “合规与安全要求” with 等保三级, 国密应用, 数据分类分级, 全程可溯. Bottom SO WHAT band: “技术架构重点是把可信流通能力嵌入成果转化业务流程”. Chinese labels, dense, official, no English, no fake logos, not a dark dashboard.
```

## Slide 08 Prompt

```text
Use case: productivity-visual
Asset type: 16:9 PowerPoint blueprint, slide 08
Primary request: Generate a Chinese internal briefing slide blueprint titled “核心应用场景”. Subtitle: “六大场景覆盖成果转化从确权、评估、匹配到履约、保护和金融的闭环”. Visual style locked: CyberPPT option 04, ivory #F7F6F0, deep blue #12355B, official internal report. Layout: central closed-loop process ring with six nodes: 成果可信存证与鉴定, 成果价值可信评估, 成果供需智能匹配, 成果转化全流程可信履约, 知识产权全周期可信保护, 科技金融赋能服务. For each node include 2 short function tags. Left side small column maps each scene to pain point; bottom band shows “确权—评估—匹配—履约—保护—金融” chain. Dense, structured, Chinese labels, consistent page header/footer, no English, no marketing, no fake logos.
```

## Slide 09 Prompt

```text
Use case: productivity-visual
Asset type: 16:9 PowerPoint blueprint, slide 09
Primary request: Generate a Chinese internal briefing slide blueprint titled “运营方案”. Subtitle: “中电联统筹与市场化运营主体协同，形成公益基础服务和增值服务双轨”. Visual style locked: CyberPPT option 04, ivory #F7F6F0, deep blue #12355B, formal internal report. Layout: left organization governance diagram: 中电联科技服务中心 as core, 专项运营管理委员会, 市场化运营公司, 生态合作伙伴. Center two-track operating model: 公益属性服务（免费） and 市场化增值服务（收费）. Right revenue sources list as stacked bars: 技术服务, 交易佣金, 会员服务, 金融服务分成, 培训咨询, 活动品牌. Bottom SO WHAT band: “运营设计需兼顾行业公共属性与可持续收入闭环”. Chinese labels, dense but readable, no English, no fake logos.
```

## Slide 10 Prompt

```text
Use case: productivity-visual
Asset type: 16:9 PowerPoint blueprint, slide 10
Primary request: Generate a Chinese internal briefing slide blueprint titled “实施路径与阶段安排”. Subtitle: “项目按 5 年四阶段推进，前 12 个月聚焦立项、底座与试点场景”. Visual style locked: CyberPPT option 04, ivory #F7F6F0, deep blue #12355B, formal internal report. Layout: horizontal 5-year roadmap with four stages: 第1阶段 筹备与基础建设（1-6个月）, 第2阶段 核心底座与试点场景上线（7-12个月）, 第3阶段 全场景拓展与行业推广（13-36个月）, 第4阶段 生态深化与全国推广（37-60个月). Under each stage show 4 task bullets and milestone chips. Highlight first 12 months with darker blue band. Right side KPI ladder: 50家主体/1000项成果/3-5项目, 1000家主体/10000项成果/10亿元, 5000家主体/50亿元. Bottom SO WHAT: “近期工作重点是立项审批、组织搭建、技术选型与试点落地”. Chinese, dense, no English, no fake logos.
```

## Slide 11 Prompt

```text
Use case: productivity-visual
Asset type: 16:9 PowerPoint blueprint, slide 11
Primary request: Generate a Chinese internal briefing slide blueprint titled “投入产出与效益分析”. Subtitle: “1 亿元分阶段投入对应第 3 年盈亏平衡和第 5 年累计回本目标”. Visual style locked: CyberPPT option 04, ivory #F7F6F0, deep blue #12355B, formal internal report. Layout: left stacked investment bar: total 1亿元 split 500万, 3000万, 4000万, 2500万; center revenue forecast line/bar chart: 第1年500万, 第2年2000万, 第3年4500万, 第4年8000万, 第5年15000万 with marker “第3年盈亏平衡”; right benefits panel: 5年累计收入约3亿元, 累计净利润约7000万元, 第5年回本, 行业节约成本, 新增产业产值. Bottom caveat strip: “财务测算需补充客单价、付费率、佣金比例和会员转化率假设”. Chinese labels, dense data slide, no English, no fake logos, no dark dashboard.
```

## Slide 12 Prompt

```text
Use case: productivity-visual
Asset type: 16:9 PowerPoint blueprint, slide 12
Primary request: Generate a Chinese internal briefing slide blueprint titled “风险评估与保障措施”. Subtitle: “立项推进需同步建立六类风险管控和六项保障机制”. Visual style locked: CyberPPT option 04, ivory #F7F6F0, deep blue #12355B, black #101820, gray #C9CDD1, formal internal report. Layout: left 3x2 risk heat matrix with six risk categories: 政策风险, 技术风险, 运营风险, 市场风险, 安全合规风险, 生态风险. Each cell includes risk level and 2 compact mitigation tags. Right side vertical保障机制 list: 组织保障, 政策保障, 技术保障, 资金保障, 人才保障, 合规保障. Bottom next-step band: “下一步：明确牵头机制、一期边界、资金安排、试点单位和技术服务商遴选”. Chinese only, dense but readable, official internal reporting tone, no English, no fake logos, no dark dashboard.
```
