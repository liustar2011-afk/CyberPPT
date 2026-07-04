const pptxgen = require("pptxgenjs");
const path = require("path");

const OUT = path.resolve(__dirname, "p2-p3-text-overlay-sample.pptx");
const BG_DIR = path.resolve(__dirname, "backgrounds");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "Codex";
pptx.subject = "CyberPPT no-text background plus editable text overlay prototype";
pptx.title = "Power Overseas Capability - Text Overlay Prototype";
pptx.company = "CyberPPT";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Arial",
  bodyFontFace: "Arial",
  lang: "zh-CN"
};
pptx.defineLayout({ name: "CUSTOM_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "CUSTOM_WIDE";

const C = {
  green: "1F5B4D",
  dark: "111111",
  body: "333333",
  muted: "666666",
  white: "FFFFFF"
};

function addBg(slide, filename) {
  slide.addImage({
    path: path.join(BG_DIR, filename),
    x: 0,
    y: 0,
    w: 13.333,
    h: 7.5
  });
}

function addTitle(slide, text) {
  slide.addText(text, {
    x: 0.56,
    y: 0.26,
    w: 12.2,
    h: 0.58,
    margin: 0,
    fontFace: "Arial",
    fontSize: 21,
    bold: true,
    color: C.white,
    breakLine: false,
    fit: "shrink"
  });
}

function addTag(slide, text, x, y, w = 0.62) {
  slide.addText(text, {
    x,
    y,
    w,
    h: 0.16,
    margin: 0.01,
    fontFace: "Arial",
    fontSize: 5.8,
    color: C.green,
    bold: true,
    align: "center",
    fit: "shrink"
  });
}

function addBody(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x,
    y,
    w,
    h,
    margin: opts.margin ?? 0.03,
    fontFace: "Arial",
    fontSize: opts.fontSize ?? 10.5,
    bold: opts.bold ?? false,
    color: opts.color ?? C.body,
    valign: opts.valign ?? "mid",
    breakLine: false,
    fit: "shrink",
    paraSpaceAfterPt: 0,
    breakLineAfter: false
  });
}

function addSoWhat(slide, text) {
  slide.addText(text, {
    x: 0.7,
    y: 6.85,
    w: 11.95,
    h: 0.38,
    margin: 0.02,
    fontFace: "Arial",
    fontSize: 13.5,
    bold: true,
    color: C.white,
    align: "center",
    valign: "mid",
    fit: "shrink"
  });
}

function addP2() {
  const slide = pptx.addSlide();
  addBg(slide, "page-02-bg-no-text.png");
  addTitle(slide, "建议由中电联牵头，用“六位一体”体系和四阶段试点，把电力产业链企业出海能力证明从“自证”转向“可信证据”");

  addTag(slide, "(E106)", 0.84, 1.37);
  addBody(
    slide,
    "电力产业链企业出海能力证明体系建设已具备推进必要性，应坚持场景牵引、证据支撑、分角色建模、分层产品化、数据化运营和边界清晰原则",
    1.15,
    1.34,
    10.95,
    0.58,
    { fontSize: 11.2, bold: true, color: C.dark }
  );
  addBody(slide, "注：现有材料以方法论与框架设计为主，暂无独立财务测算数据支撑", 1.15, 1.94, 7.9, 0.18, {
    fontSize: 6.8,
    color: C.muted
  });

  const items = [
    "补齐企业能力可信表达短板",
    "坚持分角色、分场景、分维度、重证据",
    "监测是评价有效性的关键支撑",
    "服务产品必须进入真实业务流程",
    "数据基础设施应服务于场景化能力证明",
    "组织实施采用五方协同模式",
    "风险边界必须前置控制"
  ];
  const positions = [
    [1.18, 2.74],
    [5.32, 2.74],
    [9.46, 2.74],
    [1.18, 3.82],
    [5.32, 3.82],
    [9.46, 3.82],
    [5.32, 4.9]
  ];
  addTag(slide, "(E107)", 10.8, 5.42, 0.66);
  items.forEach((item, idx) => {
    const [x, y] = positions[idx];
    addBody(slide, `${idx + 1}. ${item}`, x, y, 2.55, 0.38, {
      fontSize: 10.2,
      bold: true,
      color: C.dark
    });
  });
  addSoWhat(slide, "建议按“规则先行—试点验证—常态运营—规模推广”路径启动首阶段工作");
}

function addP3() {
  const slide = pptx.addSlide();
  addBg(slide, "page-03-bg-no-text.png");
  addTitle(slide, "全球能源转型叠加海外规则趋严，审查方式正从“资质审查”转向“持续证据审查”");

  addTag(slide, "(E001)", 1.08, 1.42);
  addBody(slide, "2025年全球能源投资总额", 1.52, 1.32, 2.7, 0.25, { fontSize: 8.6, color: C.muted });
  addBody(slide, "3.3万亿美元", 1.5, 1.62, 2.7, 0.42, { fontSize: 18, bold: true, color: C.green });

  addTag(slide, "(E002)", 5.6, 1.42);
  addBody(slide, "清洁能源相关投资约", 6.0, 1.32, 2.7, 0.25, { fontSize: 8.6, color: C.muted });
  addBody(slide, "2.2万亿美元", 6.0, 1.62, 2.7, 0.42, { fontSize: 18, bold: true, color: C.green });
  addBody(slide, "约占全球能源投资三分之二", 8.15, 1.71, 2.3, 0.26, { fontSize: 8, color: C.muted });

  addTag(slide, "(E008-E013)", 10.55, 2.7, 0.88);
  const steps = [
    ["审查对象扩展", "从单一项目扩展到企业整体"],
    ["审查材料扩展为证据链", "从资质证书扩展为可核验证据"],
    ["审查方式扩展为持续监测", "从一次性审查扩展为动态跟踪"]
  ];
  const xs = [1.18, 4.84, 8.5];
  steps.forEach(([head, sub], i) => {
    addBody(slide, head, xs[i], 3.28, 2.36, 0.28, { fontSize: 12.2, bold: true, color: C.dark, margin: 0.02 });
    addBody(slide, sub, xs[i], 3.68, 2.36, 0.42, { fontSize: 8.5, color: C.body, margin: 0.02 });
  });
  addBody(slide, "注：审查方式转变为方向性判断，原文未给出量化转变幅度", 1.22, 5.45, 6.0, 0.2, {
    fontSize: 6.8,
    color: C.muted
  });
  addSoWhat(slide, "这一趋势是建设行业化能力证明体系的根本动因");
}

addP2();
addP3();

pptx.writeFile({ fileName: OUT });
