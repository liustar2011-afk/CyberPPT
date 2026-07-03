const pptxgen = require("pptxgenjs");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "CyberPPT";
pptx.subject = "电力行业科技成果转化可信数据空间场景建设方案汇报";
pptx.title = "Slide 01";
pptx.company = "中国电力企业联合会科技服务中心";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  lang: "zh-CN"
};

const C = {
  bg: "F7F6F0",
  title: "101820",
  body: "303030",
  secondary: "6F7275",
  line: "C9CDD1",
  accent: "12355B",
  accent2: "3C5F82",
  pale: "E9EDF0",
  white: "FFFFFF"
};

const slide = pptx.addSlide();
slide.background = { color: C.bg };

function rect(x, y, w, h, fill, line = fill, transparency = 0) {
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w, h,
    fill: { color: fill, transparency },
    line: { color: line, transparency: line ? 0 : 100, width: 0.7 }
  });
}

function line(x, y, w, h, color = C.accent, width = 1) {
  if (w === 0) w = 0.001;
  if (h === 0) h = 0.001;
  if (w < 0 && h < 0) {
    x += w;
    y += h;
    w = Math.abs(w);
    h = Math.abs(h);
  }
  slide.addShape(pptx.ShapeType.line, {
    x, y, w, h,
    line: { color, width }
  });
}

// Subtle document surface.
rect(0, 0, 13.333, 7.5, C.bg, C.bg);
rect(0, 7.14, 13.333, 0.07, C.accent, C.accent);
line(0.34, 0.72, 0.16, 0, C.accent, 2.2);
line(0.34, 3.02, 3.45, 0, C.accent, 1.3);

// Main title block.
slide.addText("电力行业科技成果转化\n可信数据空间场景建设方案汇报", {
  x: 0.34,
  y: 1.26,
  w: 5.55,
  h: 1.12,
  fontFace: "Microsoft YaHei",
  fontSize: 25,
  bold: true,
  color: C.title,
  breakLine: false,
  margin: 0,
  fit: "shrink"
});

slide.addText("内部立项汇报", {
  x: 0.34,
  y: 2.68,
  w: 1.8,
  h: 0.32,
  fontFace: "Microsoft YaHei",
  fontSize: 13,
  bold: true,
  color: C.accent,
  margin: 0
});

const info = [
  ["汇报单位", "中国电力企业联合会科技服务中心"],
  ["汇报人", "中电联内部人员"],
  ["日期", "2026年"]
];
info.forEach((row, idx) => {
  const y = 3.48 + idx * 0.36;
  slide.addShape(pptx.ShapeType.ellipse, {
    x: 0.36,
    y: y + 0.04,
    w: 0.13,
    h: 0.13,
    fill: { color: C.accent },
    line: { color: C.accent, transparency: 100 }
  });
  slide.addText(`${row[0]}：${row[1]}`, {
    x: 0.58,
    y,
    w: 3.9,
    h: 0.22,
    fontFace: "Microsoft YaHei",
    fontSize: 7.8,
    color: C.body,
    margin: 0
  });
});

// Right-side trusted data space motif, all native shapes.
const cx = 8.38;
const cy = 3.08;
const nodeColor = "6F8AAA";
for (let i = 0; i < 42; i++) {
  const x = 6.58 + (i % 7) * 0.27;
  const y = 0.78 + Math.floor(i / 7) * 0.20;
  slide.addShape(pptx.ShapeType.ellipse, {
    x, y, w: 0.018, h: 0.018,
    fill: { color: C.line, transparency: 30 },
    line: { color: C.line, transparency: 100 }
  });
}

// Central layered cube approximation.
slide.addShape(pptx.ShapeType.hexagon, {
  x: cx - 0.62,
  y: cy - 0.56,
  w: 1.24,
  h: 1.12,
  fill: { color: "E7EEF3", transparency: 10 },
  line: { color: C.accent, width: 1.1 }
});
slide.addShape(pptx.ShapeType.hexagon, {
  x: cx - 0.43,
  y: cy - 0.37,
  w: 0.86,
  h: 0.76,
  fill: { color: "D7E2EA", transparency: 8 },
  line: { color: C.accent2, width: 0.8 }
});
slide.addShape(pptx.ShapeType.hexagon, {
  x: cx - 0.24,
  y: cy - 0.20,
  w: 0.48,
  h: 0.42,
  fill: { color: C.accent, transparency: 8 },
  line: { color: C.accent, width: 0.5 }
});

// Node ring and connectors.
const nodes = [
  { label: "存证", x: 6.70, y: 1.68 },
  { label: "确权", x: 8.18, y: 1.23 },
  { label: "评估", x: 9.72, y: 1.72 },
  { label: "匹配", x: 10.24, y: 3.12 },
  { label: "履约", x: 9.57, y: 4.50 },
  { label: "金融", x: 8.18, y: 4.94 },
  { label: "监管", x: 6.72, y: 4.52 },
  { label: "保护", x: 6.12, y: 3.12 }
];

nodes.forEach((n) => {
  const dx = n.x + 0.22 - cx;
  const dy = n.y + 0.22 - cy;
  if (Math.abs(dx) < 0.08 || Math.abs(dy) < 0.08 || (dx > 0 && dy > 0) || (dx < 0 && dy < 0)) {
    line(cx, cy, dx, dy, C.line, 0.8);
  }
  slide.addShape(pptx.ShapeType.ellipse, {
    x: n.x,
    y: n.y,
    w: 0.44,
    h: 0.44,
    fill: { color: C.white, transparency: 8 },
    line: { color: C.accent, width: 0.9 }
  });
  slide.addText(n.label, {
    x: n.x - 0.09,
    y: n.y + 0.50,
    w: 0.62,
    h: 0.18,
    fontFace: "Microsoft YaHei",
    fontSize: 6.5,
    color: C.secondary,
    align: "center",
    margin: 0
  });
});

slide.addText("数据可信流通 · 全链可溯监管 · 生态协同共赢", {
  x: 6.25,
  y: 5.70,
  w: 4.35,
  h: 0.24,
  fontFace: "Microsoft YaHei",
  fontSize: 8,
  color: C.accent,
  align: "center",
  margin: 0
});

// Fine right/top decorative rules.
line(10.82, 0.94, 0.64, 0, C.line, 0.7);
line(11.12, 1.08, 0.46, 0, C.line, 0.7);
line(10.98, 5.92, 0.84, 0, C.line, 0.7);

pptx.writeFile({
  fileName: "projects/电力可信数据空间科技成果转化/outputs/pages/slide-01.pptx"
});
