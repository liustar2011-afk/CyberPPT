#!/usr/bin/env node
/** Render one OfficeCLI HTML slide with CyberPPT's repository-pinned fonts. */

import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

import {
  createDefaultContext,
  launchDefaultBrowser,
  waitForDefaultFonts,
} from "../playwright_default.mjs";

const [inputHtml, outputPng] = process.argv.slice(2);
if (!inputHtml || !outputPng) {
  console.error("usage: officecli_html_screenshot.mjs <input.html> <output.png>");
  process.exit(2);
}

const browser = await launchDefaultBrowser();
const context = await createDefaultContext(browser, { viewport: { width: 1600, height: 900 } });
try {
  const page = await context.newPage();
  await page.goto(pathToFileURL(resolve(inputHtml)).href, { waitUntil: "networkidle" });
  await waitForDefaultFonts(page);
  const slide = page.locator(".slide").first();
  if (await slide.count() !== 1) {
    throw new Error("OfficeCLI HTML does not contain one .slide element");
  }
  await slide.screenshot({ path: resolve(outputPng) });
} finally {
  await context.close();
  await browser.close();
}
