const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname);
const WORKBENCH = path.resolve(ROOT, "..");
const TEMPLATE_DIR = path.join(
  WORKBENCH,
  "dual-image-final-deliverable-density/ppt-master-run/templates"
);
const IMAGE_DIR = path.join(ROOT, "images");
const OUT = path.join(ROOT, "body-blueprint-template-preview.pptx");

const pptx = new pptxgen();
pptx.defineLayout({ name: "CEC_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "CEC_WIDE";
pptx.author = "CyberPPT";
pptx.company = "中国电力企业联合会";
pptx.subject = "Body blueprint in enterprise template preview";
pptx.title = "Power Overseas Capability Body Blueprint Template Preview";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  lang: "zh-CN"
};

const C = {
  bg: "FFFFFF",
  title: "123B66",
  subtitle: "123B66",
  red: "8B0000",
  footer: "003366",
  white: "FFFFFF"
};

const PX = {
  w: 1280,
  h: 720
};
const SLIDE = {
  w: 13.333,
  h: 7.5
};

function pxX(value) {
  return (value * SLIDE.w) / PX.w;
}

function pxY(value) {
  return (value * SLIDE.h) / PX.h;
}

function addEnterpriseChrome(slide, pageNo, title, subtitle) {
  slide.background = { color: C.bg };
  slide.addText(title, {
    x: pxX(32),
    y: pxY(18),
    w: pxX(980),
    h: pxY(34),
    fontFace: "Microsoft YaHei",
    fontSize: 18,
    bold: true,
    color: C.title,
    margin: 0,
    fit: "shrink",
    breakLine: false
  });
  slide.addText(subtitle, {
    x: pxX(32),
    y: pxY(56),
    w: pxX(980),
    h: pxY(18),
    fontFace: "Microsoft YaHei",
    fontSize: 7.5,
    bold: true,
    color: C.subtitle,
    margin: 0,
    fit: "shrink",
    breakLine: false
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: pxY(82),
    w: SLIDE.w,
    h: pxY(7),
    fill: { color: C.red },
    line: { color: C.red, transparency: 100 }
  });
  slide.addImage({
    path: path.join(TEMPLATE_DIR, "../images/logo.png"),
    x: pxX(1060),
    y: pxY(16),
    w: pxX(189),
    h: pxY(63)
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: pxY(696),
    w: SLIDE.w,
    h: pxY(24),
    fill: { color: C.footer },
    line: { color: C.footer, transparency: 100 }
  });
  slide.addText("中国电力企业联合会", {
    x: pxX(40),
    y: pxY(704),
    w: pxX(240),
    h: pxY(12),
    fontFace: "Microsoft YaHei",
    fontSize: 6.5,
    color: C.white,
    margin: 0
  });
  slide.addText(String(pageNo), {
    x: pxX(1200),
    y: pxY(704),
    w: pxX(42),
    h: pxY(12),
    fontFace: "Microsoft YaHei",
    fontSize: 6.5,
    color: C.white,
    margin: 0,
    align: "right"
  });
}

function addBodyBlueprint(slide, filename) {
  slide.addImage({
    path: path.join(IMAGE_DIR, filename),
    x: pxX(32),
    y: pxY(98),
    w: pxX(1216),
    h: pxY(589)
  });
}

function addSlide(pageNo, title, subtitle, image) {
  const slide = pptx.addSlide();
  addEnterpriseChrome(slide, pageNo, title, subtitle);
  addBodyBlueprint(slide, image);
}

addSlide(
  4,
  "电力产业链企业出海呈现多角色、多场景特征，八类核心能力成为通用需求",
  "多角色、多场景特征决定评价体系必须分角色、分场景设计",
  "page-04-body-blueprint-normalized.png"
);

addSlide(
  5,
  "企业现有能力表达方式分散、失真、静态，难以适配海外多变场景",
  "现状问题构成建设行业化能力证明服务体系的现实必要性",
  "page-05-body-blueprint-normalized.png"
);

pptx.writeFile({ fileName: OUT });
