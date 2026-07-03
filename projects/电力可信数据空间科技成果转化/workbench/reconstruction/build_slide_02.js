const pptxgen = require("pptxgenjs");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "CyberPPT";
pptx.title = "Slide 02";
pptx.company = "中国电力企业联合会科技服务中心";
pptx.lang = "zh-CN";
pptx.theme = { headFontFace: "Microsoft YaHei", bodyFontFace: "Microsoft YaHei", lang: "zh-CN" };

const C = {
  bg: "F7F6F0",
  title: "101820",
  body: "303030",
  secondary: "6F7275",
  line: "C9CDD1",
  accent: "12355B",
  lightBlue: "E7EEF3",
  midBlue: "D7E2EA",
  white: "FFFFFF"
};

const slide = pptx.addSlide();
slide.background = { color: C.bg };

function addText(text, x, y, w, h, opt = {}) {
  slide.addText(text, {
    x, y, w, h,
    fontFace: "Microsoft YaHei",
    fontSize: opt.fontSize || 9,
    bold: opt.bold || false,
    color: opt.color || C.body,
    align: opt.align || "left",
    valign: opt.valign || "top",
    margin: opt.margin ?? 0.03,
    fit: "shrink",
    breakLine: false
  });
}

function rect(x, y, w, h, fill, line = fill, width = 0.6, transparency = 0) {
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w, h,
    fill: { color: fill, transparency },
    line: { color: line, width, transparency: line ? 0 : 100 }
  });
}

function line(x, y, w, h, color = C.line, width = 0.6) {
  if (w === 0) w = 0.001;
  if (h === 0) h = 0.001;
  slide.addShape(pptx.ShapeType.line, { x, y, w, h, line: { color, width } });
}

// Header
rect(0, 0, 0.78, 0.78, C.accent, C.accent);
addText("02", 0.12, 0.16, 0.54, 0.38, { fontSize: 18, bold: true, color: C.white, align: "center" });
addText("项目建设背景", 0.98, 0.13, 2.9, 0.42, { fontSize: 25, bold: true, color: C.title });
line(3.95, 0.17, 0.001, 0.44, C.line, 0.8);
addText("国家战略、行业转型与中电联职能叠加形成建设窗口期", 4.16, 0.20, 6.35, 0.34, { fontSize: 15, bold: true, color: C.accent });
line(0, 0.78, 13.33, 0.001, C.accent, 1.8);

// Main matrix
const matrixX = 0.35;
const matrixY = 1.08;
const labelW = 1.30;
const colW = 1.94;
const colGap = 0.04;
const rowH = 1.36;
const rowGap = 0.05;
const periods = ["国家战略", "新型电力系统", "中电联职能"];
const cols = ["战略要求", "政策窗口", "建设基础", "立项指向"];
const data = [
  [
    ["科技自立自强", "数据要素市场化", "成果转化法定职责"],
    ["《数据二十条》释放数据价值", "可信流通成为关键基础设施", "公共服务需要数字化载体"],
    ["可信数据空间标准逐步完善", "技术路线已有行业试点", "内部立项具备政策基础"],
    ["以场景建设承接战略要求", "先建可信底座与核心场景", "形成可复制示范"]
  ],
  [
    ["新型电力系统进入攻坚期", "科技创新与成果转化要求提高", "行业协同需求增强"],
    ["2024—2027行动方案提出体系建设", "能源领域首台套政策持续推进", "数字化基础条件成熟"],
    ["发输变配用数据体系完善", "隐私计算、区块链、TEE可用", "电网企业已有相关试点"],
    ["围绕新型电力系统重点领域试点", "支撑技术转化和产业化落地", "补齐跨主体可信协同能力"]
  ],
  [
    ["国务院复函与章程授权", "承担成果评审、鉴定、推广职能", "具备行业统筹基础"],
    ["创新奖、首台套、专家库等资源", "会员覆盖产业链各主体", "可沉淀行业成果数据资产"],
    ["行业协调与标准制定能力突出", "科技服务中心可统筹运营", "适合承担公共基础设施角色"],
    ["推动职能平台化、数据化、常态化", "形成行业服务入口", "支撑内部立项和试点组织"]
  ]
];

// Column headings and timeline rail
addText("时间轴", matrixX, 0.98, labelW, 0.28, { fontSize: 9, bold: true, color: C.white, align: "center" });
rect(matrixX, 0.98, labelW, 0.28, C.accent, C.accent);
cols.forEach((c, i) => {
  const x = matrixX + labelW + i * (colW + colGap);
  addText(c, x, 1.02, colW, 0.20, { fontSize: 9.2, bold: true, color: C.accent, align: "center" });
  line(x + colW / 2, 1.25, 0.001, 0.10, C.accent, 0.8);
});
line(matrixX + labelW, 1.25, 7.75, 0.001, C.accent, 1);

periods.forEach((p, r) => {
  const y = matrixY + r * (rowH + rowGap);
  rect(matrixX, y, labelW, rowH, C.accent, C.accent);
  addText(p, matrixX + 0.12, y + 0.50, labelW - 0.24, 0.30, { fontSize: 13, bold: true, color: C.white, align: "center" });
  for (let c = 0; c < 4; c++) {
    const x = matrixX + labelW + c * (colW + colGap);
    rect(x, y, colW, rowH, r === 1 ? "F2F5F7" : C.bg, "D6DCE0", 0.4);
    addText(data[r][c][0], x + 0.12, y + 0.14, colW - 0.24, 0.22, { fontSize: 9.2, bold: true, color: C.accent });
    addText(`· ${data[r][c][1]}\n· ${data[r][c][2]}`, x + 0.12, y + 0.43, colW - 0.22, 0.62, { fontSize: 7.4, color: C.body });
  }
});

// Right policy panel
const px = 10.35;
rect(px, 1.02, 2.48, 0.34, C.accent, C.accent);
addText("政策依据（源文件列明）", px, 1.10, 2.48, 0.18, { fontSize: 10.5, bold: true, color: C.white, align: "center" });
const policies = [
  ["01", "《中华人民共和国促进科技成果转化法》", "支持科技成果转化体系建设与专业化服务能力形成。"],
  ["02", "《数据二十条》", "明确数据要素市场化配置方向，为可信流通提供政策基础。"],
  ["03", "《加快构建新型电力系统行动方案（2024—2027年）》", "要求发挥行业组织作用，建立健全电力科技成果转化体系。"]
];
policies.forEach((p, i) => {
  const y = 1.48 + i * 1.15;
  rect(px, y, 2.48, 1.02, "F9FAF7", "BFC8D0", 0.5);
  rect(px + 0.12, y + 0.12, 0.34, 0.30, C.accent, C.accent);
  addText(p[0], px + 0.14, y + 0.18, 0.30, 0.12, { fontSize: 8, bold: true, color: C.white, align: "center" });
  addText(p[1], px + 0.55, y + 0.13, 1.78, 0.30, { fontSize: 7.8, bold: true, color: C.title });
  addText(p[2], px + 0.18, y + 0.50, 2.12, 0.34, { fontSize: 6.8, color: C.secondary });
});
addText("注：以上为源文件明确列示依据；具体条文和外部数据可在立项材料中进一步补充。", px, 5.02, 2.44, 0.42, { fontSize: 6.3, color: C.secondary });

// SO WHAT band
const sy = 6.12;
rect(0.35, sy, 1.32, 0.78, C.accent, C.accent);
addText("SO WHAT", 0.47, sy + 0.27, 0.86, 0.18, { fontSize: 11, bold: true, color: C.white, align: "center" });
const implications = [
  ["政策条件", "数据要素与科技成果转化政策方向明确"],
  ["行业条件", "新型电力系统建设对成果转化提出更高要求"],
  ["职能条件", "中电联具备承接行业公共服务的职责基础"]
];
implications.forEach((it, i) => {
  const x = 1.83 + i * 2.22;
  rect(x, sy, 2.05, 0.78, "F9FAF7", C.line, 0.5);
  addText(it[0], x + 0.12, sy + 0.14, 0.55, 0.18, { fontSize: 8, bold: true, color: C.accent });
  addText(it[1], x + 0.12, sy + 0.39, 1.72, 0.18, { fontSize: 7.2, color: C.body });
});
rect(8.62, sy, 4.00, 0.78, C.accent, C.accent);
addText("项目具备内部立项的政策与职能基础", 8.92, sy + 0.20, 3.40, 0.30, { fontSize: 14, bold: true, color: C.white, align: "center" });

// Footer
addText("资料来源：源文件《基于电力行业可信数据空间的科技成果转化场景建设运营方案》；内部资料，注意保密", 0.36, 7.18, 8.50, 0.16, { fontSize: 6.2, color: C.secondary });
addText("02", 12.48, 7.18, 0.28, 0.16, { fontSize: 6.2, color: C.secondary, align: "right" });

pptx.writeFile({ fileName: "projects/电力可信数据空间科技成果转化/outputs/pages/slide-02.pptx" });
