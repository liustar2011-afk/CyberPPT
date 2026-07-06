import fs from "node:fs";
import path from "node:path";
import pptxgen from "pptxgenjs";

function readJob(jobPath) {
  return JSON.parse(fs.readFileSync(jobPath, "utf8"));
}

function requireFile(filePath, label) {
  if (!filePath || !fs.existsSync(filePath)) {
    throw new Error(`${label} not found: ${filePath}`);
  }
}

function pxBoxToInches(box, canvas, slide) {
  if (!Array.isArray(box) || box.length !== 4) {
    throw new Error(`bbox must be [x1, y1, x2, y2]: ${JSON.stringify(box)}`);
  }
  const [x1, y1, x2, y2] = box.map(Number);
  return {
    x: (x1 / canvas.width) * slide.width_in,
    y: (y1 / canvas.height) * slide.height_in,
    w: ((x2 - x1) / canvas.width) * slide.width_in,
    h: ((y2 - y1) / canvas.height) * slide.height_in
  };
}

function normalizeColor(value, fallback = "#111111") {
  return String(value || fallback).replace(/^#/, "").toUpperCase();
}

function normalizeValign(value) {
  if (value === "middle") {
    return "mid";
  }
  return value || "top";
}

function normalizeShapeType(pptx, value) {
  if (value === "ellipse") {
    return pptx.ShapeType.ellipse;
  }
  if (value === "rect") {
    return pptx.ShapeType.rect;
  }
  return pptx.ShapeType.rect;
}

async function main() {
  const jobPath = process.argv[2];
  if (!jobPath || jobPath === "--help" || jobPath === "-h") {
    console.error("Usage: node render_overlay.mjs <job.json>");
    if (jobPath === "--help" || jobPath === "-h") {
      return;
    }
    throw new Error("Usage: node render_overlay.mjs <job.json>");
  }

  const job = readJob(jobPath);
  const canvas = job.canvas || { width: 1672, height: 941 };
  const slideSize = job.slide || { width_in: 13.333, height_in: 7.5 };
  requireFile(job.background, "background");

  const pptx = new pptxgen();
  pptx.author = "CyberPPT";
  pptx.subject = "dual_image_editable_overlay";
  pptx.title = "CyberPPT dual image editable overlay";
  pptx.company = "CyberPPT";
  pptx.lang = "zh-CN";
  pptx.defineLayout({
    name: "LAYOUT_CUSTOM",
    width: Number(slideSize.width_in),
    height: Number(slideSize.height_in)
  });
  pptx.layout = "LAYOUT_CUSTOM";

  const slide = pptx.addSlide();
  slide.background = { color: "FFFFFF" };
  slide.addImage({
    path: job.background,
    x: 0,
    y: 0,
    w: Number(slideSize.width_in),
    h: Number(slideSize.height_in)
  });

  for (const shape of job.shapes || []) {
    const rect = pxBoxToInches(shape.bbox, canvas, slideSize);
    slide.addShape(normalizeShapeType(pptx, shape.type), {
      x: rect.x,
      y: rect.y,
      w: rect.w,
      h: rect.h,
      fill: { color: normalizeColor(shape.fill, "#0B3B75"), transparency: Number(shape.transparency || 0) },
      line: { color: normalizeColor(shape.line || shape.fill || "#0B3B75"), transparency: Number(shape.lineTransparency || 100) }
    });
  }

  for (const box of job.boxes || []) {
    const rect = pxBoxToInches(box.bbox, canvas, slideSize);
    slide.addText(String(box.text || ""), {
      x: rect.x,
      y: rect.y,
      w: rect.w,
      h: rect.h,
      margin: 0,
      fontFace: box.font_family || "Arial",
      fontSize: Number(box.font_size || 12),
      color: normalizeColor(box.fill),
      bold: box.bold === true,
      italic: box.italic === true,
      align: box.align || "left",
      valign: normalizeValign(box.v_align),
      fit: "shrink",
      wrap: box.wrap === false ? false : true,
      breakLine: false
    });
  }

  const outPath = path.resolve(job.output_pptx);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  await pptx.writeFile({ fileName: outPath });
}

main().catch((error) => {
  console.error(JSON.stringify({ valid: false, error: error.message }, null, 2));
  process.exit(1);
});
