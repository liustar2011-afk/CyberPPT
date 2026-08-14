import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const project = path.resolve('projects/power-industry-data-services-operation-20260802');
const sourcePath = path.join(project, 'source', 'PPT逐页文字稿-原稿.md');
const outPath = path.join(project, 'workbench', 'scripts', 'drafts', '全稿-v1.md');
const truthPath = path.join(project, 'workbench', 'stages', '01-analysis', 'source-truth.json');
const visualSpecPath = path.join(project, 'visual', 'deck-visual-spec.json');
const raw = fs.readFileSync(sourcePath, 'utf8');
const blocks = [...raw.matchAll(/^### Page (\d{2})｜([^\r\n]+)\r?\n([\s\S]*?)(?=^### Page \d{2}｜|$(?![\s\S]))/gm)];
if (blocks.length !== 28) throw new Error(`expected 28 pages, got ${blocks.length}`);

const visualSpecByPage = new Map();
if (fs.existsSync(visualSpecPath)) {
  const deckVisualSpec = JSON.parse(fs.readFileSync(visualSpecPath, 'utf8'));
  for (const page of deckVisualSpec.pages || []) visualSpecByPage.set(Number(page.page_number), page);
}

function visualSummary(page) {
  if (!page?.visual_decision) return '';
  const v = page.visual_decision;
  const trim = value => String(value || '').replace(/[。；，、]+$/,'');
  const relation = trim(page.semantic_graph?.decision_relationship || v.relationship_encoding || '');
  const reading = Array.isArray(v.reading_path) ? v.reading_path.join('→') : String(v.reading_path || '');
  const avoid = Array.isArray(page.avoid) ? page.avoid.slice(-2).map(trim).join('；') : '';
  return `主视觉载体：${trim(v.dominant_visual_carrier)}；空间组织：${trim(v.spatial_organization)}；阅读路径：${reading}；关系编码：${relation}${avoid ? `；本页避免：${avoid}` : ''}`;
}

function field(body, label) {
  const re = new RegExp(`^- \\*\\*${label}：\\*\\*\\s*([\\s\\S]*?)(?=^- \\*\\*[^\\n]+：\\*\\*|$(?![\\s\\S]))`, 'gm');
  const values = [...body.matchAll(re)].map(m=>m[1].trim()).filter(Boolean);
  return values.sort((a,b)=>b.length-a.length)[0] || '';
}
function clean(s) { return s.replace(/^\s{2}/gm, '').trim(); }
function compactSentence(value, max=92) {
  const clean=value.replace(/\s+/g,' ').replace(/^[一二三四五六七八九十]+[、，]\s*/,'').trim();
  if (clean.length<=max) return clean;
  const clauses=clean.split(/[；。，]/).filter(Boolean);
  const kept=[]; let count=0;
  for (const clause of clauses) { if (count+clause.length>max) break; kept.push(clause); count+=clause.length; }
  return (kept.join('；') || clean.slice(0,max)).replace(/[，、；：]$/,'');
}
function grams(value) {
  const s=value.replace(/[^\u4e00-\u9fffA-Za-z0-9]/g,'');
  const out=new Set(); for(let i=0;i<s.length-1;i++) out.add(s.slice(i,i+2)); return out;
}
function onscreenModules(text, fallback, fullText='') {
  let items = text.split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map(x=>x.replace(/^[-*]\s*/,''));
  if (!items.length) return {lines:[`  **核心信息**`,'',`  - ${fallback}`],titles:['核心信息']};
  let itemChars=items.reduce((sum,item)=>sum+item.length,0);
  while (itemChars>365) {
    const index=items.reduce((best,item,i)=>item.length>items[best].length?i:best,0);
    const excess=itemChars-365;
    const target=Math.max(42,items[index].length-excess);
    const shortened=compactSentence(items[index],target);
    if (shortened.length>=items[index].length) break;
    itemChars-=items[index].length-shortened.length;
    items[index]=shortened;
  }
  const sentences=fullText.split(/(?<=[。；！？])/).map(x=>x.trim()).filter(x=>x.length>=24);
  const used=new Set();
  let extraBudget=Math.max(0, 380-items.reduce((sum,item)=>sum+item.length,0));
  const lines=[]; const titles=[];
  items.forEach((item,index)=>{
    const parts=item.split(/[：:]/,2);
    const title=(parts.length>1?parts[0]:`要点${index+1}`).replace(/[。；，]$/,'').slice(0,22);
    const detail=(parts.length>1?item.slice(parts[0].length+1):item).trim();
    const key=grams(`${title}${detail}`);
    const ranked=sentences.map((sentence,si)=>({sentence,si,score:[...key].filter(g=>sentence.includes(g)).length})).filter(x=>!used.has(x.si)).sort((a,b)=>b.score-a.score);
    const best=ranked[0];
    titles.push(title); lines.push(`  **${String(index+1).padStart(2,'0')}｜${title}**`,'',`  - ${detail}`);
    if (best && best.score>=2 && extraBudget>=28) {
      const extra=compactSentence(best.sentence);
      if (!detail.includes(extra) && !extra.includes(detail) && extra.length<=extraBudget) { lines.push(`  - ${extra}`); used.add(best.si); extraBudget-=extra.length; }
    }
    lines.push('');
  });
  return {lines,titles};
}
function pageType(n, name) {
  if (n === 1) return '封面';
  if (n === 2) return '目录页';
  if (/章节页/.test(name)) return '章节过渡页';
  if (/封底页/.test(name)) return '封底页';
  return '内容页';
}
function chapterFor(n) {
  if (n <= 2) return 'template';
  if (n <= 8) return 'c1';
  if (n <= 16) return 'c2';
  if (n <= 23) return 'c3';
  if (n <= 27) return 'c4';
  return 'template';
}
function roleFor(title) {
  if (/建议|工作安排|试点/.test(title)) return 'implementation';
  if (/边界|安全|验收/.test(title)) return 'assurance';
  if (/架构|体系|机制|流程|能力/.test(title)) return 'solution';
  return 'positioning';
}

const pageOverrides = {
  4: {
    onscreen: `- 行业节点定位：上接国家全域节点，横向协同区域及其他行业节点，下联电力企业、行业机构和业务系统
- 行业节点职责：中电联负责行业目录、规则协调、产品运营、跨主体交付和生态组织
- 企业控制边界：企业保留原始数据、核心模型和专业能力的生产管理权，通过接口、结果服务或受控计算参与行业服务`,
    visual: '三级节点关系——国家节点、电力行业节点、企业及业务系统自上而下连接；企业控制边界作为底部约束条。',
  },
  6: {
    title: '四类核心能力把主体、资源、服务、安全和结算纳入统一运营',
    onscreen: `- 可信接入：统一身份、目录标识、接口规范和连接器，解决主体与能力如何进入行业节点
- 产品运营：完成资源登记、产品加工、供需匹配、订购授权和版本管理
- 安全交付：以数字合约、使用控制、隐私计算、数据沙箱和存证审计约束服务过程
- 智能与结算：提供知识库、模型服务和智能应用，并以统一计量、计费和分账形成运营闭环`,
    visual: '能力域—交付环节矩阵：横向设置“连接—治理—交付—计量—审计”五个交付环节，纵向设置可信接入、产品运营、安全交付、智能与结算四类能力域；以高亮交叉点表示各能力的主要支撑位置，避免再叠加第二条独立流程。',
  },
  8: {
    onscreen: `- 五层架构：可信连接与接入、统一门户与服务网关、流通利用与核心运营、数据与人工智能底座、安全运维保障
- 企业接入链：主体入驻→资源登记→合约授权→服务调用→可信交付→计量结算→运营评价
- 接入边界：连接器执行身份认证、接口适配、策略控制和日志采集；企业数据与模型仍按约定留在企业控制域`,
    visual: '五层纵向架构：安全运维保障作为贯穿全图的侧边控制带，其余四层自下而上承载接入、门户、运营与数据智能能力；企业接入链仅在可信连接与接入层内横向展开，连接器嵌入该链，不跨越全部层级。',
  },
  10: {
    onscreen: `- 三项支撑：平台负责连接、授权、交付、计量和审计；机制明确权责、收益与运营规则；模型提供理解、推理、生成和编排
- 运营主线：数据资源→数据产品→数据服务→场景服务→客户使用→成效反馈→产品迭代
- 两类服务出口：数据服务形成可重复的基础供给；场景服务组合数据、模型、专家和实施能力，面向业务结果持续运营
- 客户购买方式：既可直接订购数据服务，也可采购多项能力组合形成的场景服务`,
    visual: '一条运营主链＋三项底部支撑＋两类服务出口；成效反馈只回流到产品迭代节点。',
  },
  11: {
    onscreen: `- 数据资源：原始数据、知识资料、指标数据和模型相关数据，是运营加工的基础对象
- 数据产品：将资源封装为数据集、接口、指标服务、报告和知识库，形成可登记、可授权的供给单元
- 数据服务：围绕查询、分析、预测、模型调用、报告和持续监测形成可重复交付
- 场景服务：组合数据、模型、算法、专家和实施能力解决具体业务问题；服务类型和计量报价按交付形态配置`,
    visual: '四层产品塔——资源→产品→数据服务→场景服务；服务类型和计量报价作为右侧配套规则，不计入主层级。',
  },
  12: {
    onscreen: `- 八步生命周期：资源登记→治理加工→质量合规审核→目录上架→订购授权→受控交付→计量评价→更新续约
- 产品卡合同：明确服务内容、来源、对象、交付方式、服务等级、计量单位、价格方式、授权期限和责任边界`,
    visual: '八步受控交付流程——在审核、授权、交付和计量评价节点设置规则控制；产品卡作为贯穿全流程的合同载体。',
  },
  13: {
    onscreen: `- 需求池：记录业务问题、客户对象、使用频率和成效目标，作为场景选择起点
- 能力池：登记可调用的数据、模型、算法、专家、实施和运维能力
- 场景池：固化业务流程、数据边界、模型任务、交付成果和评价指标
- 运营闭环：三池组合形成场景服务包，使用效果回流需求池和场景池，验证结果驱动能力池更新`,
    visual: '三池汇聚回环——需求池、能力池、场景池汇聚为场景服务包；反馈箭头明确回到需求池和场景池。',
  },
  14: {
    onscreen: `- 目录与供需：统一登记主体、资源、产品、场景和版本，支撑需求发布、产品匹配与工单审核
- 合约与控制：固化用途、期限、额度、输出和责任，管理授权变更、暂停、撤销及异常处置
- 统一记录：按统一规则采集服务调用、用量、状态和质量记录，为后续账单与分账提供依据
- 质量与安全：开展服务评价、版本整改、审计存证、投诉处理和退出管理`,
    visual: '四类治理域——目录供需、合约控制、统一记录、质量安全环绕统一运营中心；账单和分账细节留给P16。',
  },
  15: {
    onscreen: `- 客户价格结构：数据服务按基础接入、订阅/使用、许可和保障计价；场景服务按建设实施、年度运营、资源使用和可选效果奖励计价
- 报价与套餐：依据低中高用量、服务等级和预算上限测算；支持基础费＋按量费＋封顶，以及预付、组合采购和批量折扣
- 后台成本边界：记录调用、数据量、算力、服务时长和成果交付；Token仅用于内部核算，客户侧展示服务事项、成果和年度预算`,
    visual: '三段式价格阶梯：顶部用两条并列价格公式区分数据服务与场景服务，中部用“用量×服务等级×预算约束”形成报价套餐选择区，底部以虚线边界区分客户报价与后台成本核算；计价对象对照表嵌入中段右侧，不单独形成第四层。',
  },
  16: {
    onscreen: `- 计量结算主链：有效服务事件→统一计量→月度试算→双方对账→正式账单→分账确认→财务支付；失败交付执行重试、补交或额度返还
- 收益分配原则：扣除税费、退款、云算力和约定第三方成本后，按数据、模型、平台、应用服务和合同责任分配
- 持续经营验证：以资产运营、服务运营、智能效果、安全合规和平台运维指标，持续观察贡献毛利、付费转化、续费、增购和运维覆盖`,
    visual: '一条计量结算主链＋两条辅助带——收益分配原则和持续经营指标置于主链下方，不作为等权流程节点。',
  },
  18: {
    onscreen: `- 企业控制域：原始数据、模型权重、核心算法和知识产权继续由企业管理，对外提供接口、结果服务或受控计算任务
- 可信连接层：连接器承担主体认证、资源登记、合约执行、访问控制、日志采集和运行监测
- 行业节点层：中电联负责行业规则、标准评价和重大协同，数智公司承担统一产品运营、客户服务与计量结算
- 客户服务端：数据服务和场景服务通过统一门户、服务网关和生态实施能力交付给行业客户`,
    visual: '四层协同架构——企业控制域→可信连接层→行业节点层→客户服务端；组织推进机制留给P20。',
  },
  19: {
    onscreen: `- 远程API与结果服务：适用于公开或低敏数据、标准指标、知识检索、模型推理和报告成果
- 专属实例：适用于高并发、强隔离、响应时间和服务连续性要求较高的客户
- 私有化部署：适用于集团级业务、敏感数据和需要长期独立运行的场景
- 数据留域受控计算：适用于设备运行、经营管理和联合建模，原始数据留在企业控制域`,
    visual: '四种接入方式渐进轴——从开放调用到数据留域排列；统一身份、目录、合约、计量和审计作为贯穿底座。',
  },
  20: {
    onscreen: `- 五方职责：中电联统筹治理，数智公司统一运营，大型企业供给能力，生态伙伴联合交付，客户持续使用反馈
- 重点企业机制：以“一企一组、一企一目录、一企一协议、一企一试点”锁定协同组织、能力范围、权利商务和真实验证
- 供给合作规则：战略型单位、核心产品方、技术服务商和渠道伙伴按能力成熟度与交付责任分层合作
- 公平运营规则：实行统一准入测评、关联披露与回避、透明价格、投诉处理和可解释推荐`,
    visual: '五方协同关系图：数智公司作为统一运营枢纽，中电联位于治理侧，大型企业与生态伙伴位于供给侧，客户位于需求侧；各方仅用“治理、供给、交付、反馈”四类连线连接。下方保留“一企一策”和“公平运营”两条规则带，不再展开第二套流程。',
  },
  21: {
    onscreen: `- 基础服务层：数据与知识服务提供政策标准检索、专业接口、数据集和质量核验；模型与算法服务提供模型调用、评测、诊断、预测和经营分析
- 场景服务层：面向生产设备、新能源综合能源、经营决策和人才培养，组合基础服务形成持续运营方案
- 客户价值出口：根据企业实际能力、客户真实需求和采购条件，分阶段形成可订购的数据产品和可复制的场景服务包`,
    visual: '两层服务体系汇聚客户价值——基础服务层支撑场景服务层，两层共同输出数据产品和场景服务包。',
  },
  22: {
    onscreen: `- 电力行业中小企业：重点需求包括预测、设备诊断、运维、市场规则和运营优化，适合订阅、年度服务、API和专题报告
- 产业链专业企业：围绕设备实证、质量评价、故障知识和模型嵌入，采用评测、诊断、API、SDK和联合方案
- 教育科研与公共服务：采用知识库、数据集许可、模型评测、专题报告、指标服务和受控查询
- 跨行业客户：围绕电碳、能效、设备风险和综合能源，采购核验评价或专题场景服务
- 分层运营路径：中小客户降低首次接入成本，大型客户配置专属连接器、实例和SLA；统一经历线索→试用→验证→采购→实施→续费增购`,
    visual: '四行客户服务矩阵：按客户类型、核心需求、优先服务形态三列逐行对应，禁止把需求和服务拆成漂浮标签；矩阵下方仅保留一条六步客户旅程，分层运营策略以旅程起点和实施节点的注释呈现。',
  },
  23: {
    onscreen: `- 最低闭环：首期至少选择1项数据服务＋1项场景服务，以真实供给、真实客户和真实业务验证运营闭环
- 扩展组合：当多方供给和客户条件具备时，可扩展为“3＋1”候选组合，不作为首期强制数量要求
- 试点验收事件：验证产品上架、客户订购、数字合约、受控调用、统一计量、账单对账、结算分账和成效评价是否贯通
- 合作边界：原始数据、核心模型、知识产权、授权责任和退出安排由合作协议与任务书明确`,
    visual: '最低闭环与扩展组合双层结构——左侧说明1+1最低闭环，右侧说明3+1条件扩展；底部列验收事件和合作边界。',
  },
  25: {
    onscreen: `- 调研输入：形成资源清单、能力清单和需求清单，覆盖数据、知识、模型、平台、专家、客户问题与采购路径
- 综合筛选：按需求真实性、资源可用性、权利清晰度、技术可行性、服务可计量性和复制价值排序
- 调研输出：形成首批数据服务目录、场景服务目录及需要进一步确认的安全、接口和商务条件`,
    visual: '输入—筛选—输出漏斗——三类清单进入六项标准筛选器，输出首批合作目录和待确认条件。',
  },
  26: {
    onscreen: `- 任务书合同：明确产品、客户、交付方式、安全边界、计量单位、价格方式、责任分工、服务等级和验收指标
- 技术实施线：完成连接器或接口适配、目录登记、服务网关、数字合约、受控调用、计量和账单能力
- 商务实施线：完成采购路径、合同附件、报价结算、权利责任、服务等级和异常退出安排
- 运营实施线：完成客户订购、真实调用、用量记录、账单生成、分账核验和成效反馈
- 验收依据：以真实供给、真实客户、真实调用、真实账单和可核验成效判断是否具备持续运营条件`,
    visual: '三线并行实施泳道：任务书作为共同起点，技术、商务、运营三条泳道分别展示实施动作，并在“真实供给、真实客户、真实调用、真实账单、可核验成效”五项验收门汇合；不重复P23的试点组合选择。',
  },
  27: {
    onscreen: `- 0—2个月｜供需锁定：完成能力盘点、需求访谈、产品筛选和合作条件确认，形成产品卡、场景服务卡与合作框架
- 3—5个月｜闭环建设：完成目录、连接器、网关、数字合约、计量和账单流程，验证最小运营闭环
- 6—10个月｜付费试点：完成客户订购、受控调用、对账分账和效果评价，建立周运营、月结算和季度复评
- 11—18个月｜复制推广：沉淀标准产品、场景服务包、接口与实施清单，逐步扩大服务对象
- 贯穿式经济性闸门：持续检验贡献毛利、付费转化、续费增购、分账及时性和运维覆盖，达标后进入下一阶段`,
    visual: '四阶段时间轴＋底部经济性闸门——每阶段固定显示关键任务和阶段交付，终点形成可复制合作模式。',
  },
};

const pages = [];
const records = [];
const conclusions = [];
const truthPages = [];
const script = ['# 依托电力领域数据基础设施开展行业数据服务与场景服务运营合作方案', '', '> 28页全稿｜仓库格式整理稿 v1', '> 来源：逐页文字稿原稿；两份 Word 材料用于补充核验', '', '---', ''];

for (const m of blocks) {
  const n = Number(m[1]);
  const pageId = `p${String(n).padStart(2, '0')}`;
  const name = m[2].trim();
  const body = m[3];
  const override = pageOverrides[n] || {};
  const title = override.title || field(body, '标题') || name.replace(/^第.章章节页$/, name);
  const subtitle = field(body, '副标题');
  const judgment = field(body, '主判断');
  const full = clean(field(body, '完整文字稿'));
  const onscreen = override.onscreen || clean(field(body, '上屏信息'));
  const visual = visualSummary(visualSpecByPage.get(n)) || override.visual || clean(field(body, '视觉结构'));
  const boundary = clean(field(body, '证据与边界'));
  const notes = clean(field(body, '讲解词'));
  const type = pageType(n, name);
  const content = type === '内容页';
  const sid = `S${String(n).padStart(3, '0')}`;
  const cid = `C${String(n).padStart(3, '0')}`;

  script.push(`## 第${n}页：${title}`, '', `- 页面类型：${type}`, `- 页面标题：${title}`);
  if (subtitle) script.push(`- 副标题：${subtitle}`);
  if (content) {
    const visible = onscreenModules(onscreen, judgment, full);
    const cleanJudgment = judgment.replace(/[。；，、！？!?：:]$/,'');
    script.push(
      `- 主判断：${judgment}`,
      '- 完整文字稿：', '',
      ...full.split(/\r?\n/).map(x => x ? `  ${x}` : ''),
      '', `  ${notes.replace(/\s+/g,' ')}`, '',
      '- 文字稿取舍说明：',
      `  - 必留上屏：${visible.titles.join('、')}。`,
      `  - 仅讲解：完整文字稿中的关系解释、合作价值和实施含义。`,
      `  - 仅追溯：${sid}。`,
      `- 证据映射：本页完整文字稿、关键判断与边界→${sid}`,
      '- 上屏结论模式：semantic_only',
      `- 上屏结论：${cleanJudgment}`,
    );
  }
  if (content) script.push(`- 证据：${sid}。`);
  const visibleOut = onscreenModules(onscreen, judgment, full);
  if (type === '章节过渡页') script.push(`- 上屏文字：${onscreen.replace(/^[-*]\s*/gm,'').trim()}`);
  else script.push('- 上屏文字：', '', ...visibleOut.lines, '');
  if (content && visual) script.push(`- 视觉结构：${visual.replace(/[。；]+$/,'')}。`);
  if (boundary && type !== '章节过渡页') script.push(`- 边界：${boundary}`);
  const cleanNotes = notes.replace(/这(?:一)?页/g,'').replace(/本页/g,'').replace(/下面进入第[^。]+。?/g,'').replace(/下一页/g,'后续内容');
  script.push('【演讲者备注】', '', cleanNotes, '', '---', '');

  const refs = content ? [sid] : [];
  if (content) {
    pages.push({page_id:pageId, sequence:n, page_type:'content', chapter_id:chapterFor(n), title, main_message:judgment, core_message:judgment, onscreen_conclusion:judgment.replace(/[。；，、！？!?：:]$/,''), source_refs:refs, business_question:`${title}需要说明哪些关键内容与边界`, visual_center:visual, modules:[], source_weight:1, page_job:`说明${title}的关键内容与合作含义`, page_mission:`完整呈现${title}的关键内容、关系与边界`, page_necessity:`本页独立回答“${title}”这一合作决策问题，不能由相邻页替代。`, proof_points:[{claim:judgment,source_refs:refs,consumption:'primary'}], new_value_vs_previous:judgment, reserved_for_later:'相邻页面仅展开各自标题所对应的内容，不重复本页判断。', argument_role:roleFor(title), allowed_claim_roles:['fact','judgment','recommendation'], forbidden_claim_roles:[], prerequisite_pages:[], main_claim_status:'confirmed', content_units:[{id:`${pageId}-u1`,statement:judgment,role:'primary',source_refs:refs}], content_relations:[{relation:'contains',subject:title,objects:[judgment],source_refs:refs}]});
  } else {
    pages.push({page_id:pageId,sequence:n,page_type:type==='封面'?'cover':type==='目录页'?'agenda':type==='章节过渡页'?'chapter':'back_cover',chapter_id:chapterFor(n),title});
  }
  if (content) {
    const quote = full.replace(/\s+/g,' ').slice(0, 500);
    records.push({id:sid,type:/建议|安排|试点/.test(title)?'R':'J',priority:'P0',statement:judgment,source_locator:{source_id:'MD01',file:'PPT逐页文字稿-原稿.md',section:`Page ${m[1]}｜${name}`,paragraph:n},status:/建议|安排|试点/.test(title)?'拟建议':'原文陈述',claim_role:/建议|安排|试点/.test(title)?'recommendation':'judgment',semantic_units:[{text:judgment,claim_role:/建议|安排|试点/.test(title)?'recommendation':'judgment'}],allowed_page_roles:['assurance','change','decision','foundation','gap','implementation','necessity','positioning','scope','solution'],forbidden_page_roles:[],depends_on:[],conditions:boundary?[boundary]:[],supports:[cid],page_refs:[pageId],quote,fingerprint:`sha256:${crypto.createHash('sha256').update(quote).digest('hex')}`});
    conclusions.push({id:cid,statement:judgment,source_refs:[sid]});
    truthPages.push({id:pageId,source_refs:[sid]});
  }
}

const chapterTargets = [
  ['CT01','第一章 中电联电力领域数据基础设施介绍',4,8],
  ['CT02','第二章 电力行业数据服务与场景服务运营体系规划',10,16],
  ['CT03','第三章 与电力骨干企业的合作方案设想',18,23],
  ['CT04','第四章 下一步工作建议',25,27],
].map(([id,label,a,b])=>({id,kind:'section',label,priority:'P0',required:true,record_refs:records.filter(r=>{const n=Number(r.page_refs[0].slice(1));return n>=a&&n<=b}).map(r=>r.id)}));
const truth = {schema:'cyberppt.source_truth.v1',argument_contract_mode:'strict',source_receipt_policy:'required',document_semantics_mode:'required',document_semantics:{document_role:'面向电力骨干企业的运营合作方案讨论稿',subject_of_report:'依托电力领域数据基础设施开展行业数据服务与场景服务运营合作',primary_thesis:'通过行业节点、企业能力和联合运营机制形成可交付、可计量、可持续迭代的行业服务',decision_boundary:'合作产品、商务条件、试点范围和验收指标仍需双方调研确认',source_refs:records.map(r=>r.id)},project:{title:'依托电力领域数据基础设施开展行业数据服务与场景服务运营合作方案',material_type:'合作方案',audience:'电力骨干企业决策与业务合作相关方',architecture_mode:'solution'},sources:[{id:'MD01',file:'source/PPT逐页文字稿-原稿.md',role:'primary',non_empty_paragraphs:raw.split(/\r?\n/).filter(x=>x.trim()).length,headings:30,tables:0},{id:'DOC01',file:'source/运营合作方案（讨论稿）.docx',role:'supporting',non_empty_paragraphs:257,headings:77,tables:0},{id:'DOC02',file:'source/运营体系研究报告V0801.docx',role:'supporting',non_empty_paragraphs:412,headings:120,tables:47}],coverage_targets:chapterTargets,records,conclusions,pages:truthPages,retry:{attempt:1,max_attempts:3,strategy:'page_script_sweep'}};
const outline = {schema:'cyberppt.outline.v2',argument_contract_mode:'strict',core_message_derivation_mode:'required',document_semantics:truth.document_semantics,material_type:'合作方案',audience:'电力骨干企业决策与业务合作相关方',architecture_mode:'solution',architecture_reason:'正式合作方案采用方案型架构，并保留原稿四章顺序',user_requested_architecture:false,narrative_thesis:truth.document_semantics.primary_thesis,source_section_weights:{c1:5/21,c2:7/21,c3:6/21,c4:3/21},pages:pages.map(p=>p.page_type==='content'?{...p,core_message_derivation:{source_refs:p.source_refs,supporting_statements:[p.core_message],derivation:'保留逐页原稿主判断及其限定条件，不强化事实状态。',introduced_relations:[],introduced_modalities:[]}}:p),retry:{attempt:2,max_attempts:3,strategy:'source_native'}};

fs.mkdirSync(path.dirname(outPath),{recursive:true});
fs.writeFileSync(outPath, script.join('\n'), 'utf8');
fs.writeFileSync(truthPath, JSON.stringify(truth,null,2)+'\n','utf8');
fs.writeFileSync(path.join(project,'workbench','stages','01-analysis','outline.json'),JSON.stringify(outline,null,2)+'\n','utf8');
console.log(JSON.stringify({pages:blocks.length,content_pages:records.length,outPath,truthPath},null,2));
