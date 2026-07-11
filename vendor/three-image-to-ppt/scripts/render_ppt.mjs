#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import pptxgen from "pptxgenjs";

const SLIDE_WIDTH_IN = 13.333333;
const SLIDE_HEIGHT_IN = 7.5;
const DEFAULT_FONT = "Microsoft YaHei";
const DEFAULT_FONT_SIZE_PT = 12;
const PX_TO_PT = 72 / 96;

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!flag?.startsWith("--") || value === undefined) {
      throw new Error("Usage: render_ppt.mjs --json page.json --background background.png --out page.pptx");
    }
    result[flag.slice(2)] = value;
  }
  for (const required of ["json", "background", "out"]) {
    if (!result[required]) throw new Error(`Missing required argument: --${required}`);
  }
  return result;
}

function linePosition(line, page) {
  const box = line.target?.bbox_px ?? line.bbox;
  return {
    x: (box.x / page.width_px) * SLIDE_WIDTH_IN,
    y: (box.y / page.height_px) * SLIDE_HEIGHT_IN,
    w: (box.width / page.width_px) * SLIDE_WIDTH_IN,
    h: (box.height / page.height_px) * SLIDE_HEIGHT_IN,
  };
}

function normalizeColor(value) {
  if (value === undefined || value === null || value === "") return undefined;
  return String(value).replace(/^#/, "").replace(/^0x/i, "").toUpperCase();
}

function fontSizeInPoints(value, unit = "px") {
  if (value === undefined || value === null || value === "") return undefined;
  if (typeof value === "number") return unit === "pt" ? value : value * PX_TO_PT;
  const text = String(value).trim();
  const number = Number.parseFloat(text);
  if (!Number.isFinite(number)) return undefined;
  if (text.toLowerCase().endsWith("pt")) return number;
  if (unit === "pt") return number;
  return number * PX_TO_PT;
}

function runStyle(style = {}) {
  const normalized = {
    fontFace: style.typeface ?? style.fontFamily ?? style.font_family ?? DEFAULT_FONT,
  };
  const fontSizePt = style.fontSizePt !== undefined
    ? fontSizeInPoints(style.fontSizePt, "pt")
    : fontSizeInPoints(style.font_size_px ?? style.font_size ?? style.fontSize);
  if (fontSizePt !== undefined) normalized.fontSize = fontSizePt;

  for (const key of ["bold", "italic", "underline"]) {
    if (style[key] !== undefined) normalized[key] = style[key];
  }
  if (style.weight !== undefined) {
    normalized.bold = style.weight === "bold" || Number(style.weight) >= 600;
  }
  const color = normalizeColor(style.color);
  if (color) normalized.color = color;
  return normalized;
}

function textRuns(line) {
  if (!line.runs?.length) return line.text;
  return line.runs.map((run) => ({
    text: run.text,
    options: { ...runStyle(run.style), breakLine: false },
  }));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const pageSpec = JSON.parse(await fs.readFile(args.json, "utf8"));
  const pptx = new pptxgen();
  pptx.layout = "LAYOUT_WIDE";
  pptx.author = "CyberPPT";
  pptx.subject = "Three-image editable text reconstruction";
  pptx.title = pageSpec.page?.page_id ?? "Reconstructed slide";

  const slide = pptx.addSlide();
  slide.addImage({
    path: args.background,
    x: 0,
    y: 0,
    w: SLIDE_WIDTH_IN,
    h: SLIDE_HEIGHT_IN,
    objectName: "Reconstructed slide background",
    altText: "Reconstructed slide background",
  });

  for (const line of pageSpec.text_lines) {
    if (/\r|\n/.test(line.text) || line.runs?.some((run) => /\r|\n/.test(run.text))) {
      throw new Error(`Visual line ${line.line_id} must not contain a newline`);
    }
    const align = { left: "left", center: "center", right: "right" }[line.layout?.align ?? "left"];
    const valign = { top: "top", middle: "mid", bottom: "bottom" }[line.layout?.valign ?? "top"];
    slide.addText(textRuns(line), {
      ...linePosition(line, pageSpec.page),
      objectName: `text-${pageSpec.page.page_id}-${line.line_id}`,
      fontFace: DEFAULT_FONT,
      fontSize: DEFAULT_FONT_SIZE_PT,
      margin: fontSizeInPoints(line.layout?.margin_px ?? 0),
      fit: "none",
      wrap: line.layout?.wrap ?? false,
      align,
      valign,
      rotate: line.layout?.rotation_deg ?? 0,
    });
  }

  await fs.mkdir(path.dirname(path.resolve(args.out)), { recursive: true });
  await pptx.writeFile({ fileName: path.resolve(args.out) });
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
