import { chromium } from "playwright";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const DEFAULT_PLAYWRIGHT_BROWSER = "chromium";
export const DEFAULT_PLAYWRIGHT_HEADLESS = true;
export const DEFAULT_PLAYWRIGHT_FONT_FAMILY = "Microsoft YaHei";
export const PLAYWRIGHT_HEADLESS_ONLY_MESSAGE =
  "CyberPPT Playwright is headless-only; headed browser launches are forbidden.";
export const DEFAULT_PLAYWRIGHT_FONT_DIRECTORY = fileURLToPath(
  new URL("../assets/fonts/extracted/", import.meta.url),
);

const FONT_ROUTE_BASE = "http://cyberppt.local/__cyberppt_fonts/";
const FONT_STYLE_ID = "__cyberppt_repository_fonts__";
const FONT_DEFINITIONS = [
  { file: "MicrosoftYaHei-Light.ttf", weight: 300 },
  { file: "MicrosoftYaHei-Regular.ttf", weight: 400 },
  { file: "MicrosoftYaHei-Bold.ttf", weight: 700 },
];
const FONT_FILES = new Map(
  FONT_DEFINITIONS.map(({ file }) => [
    file,
    resolve(DEFAULT_PLAYWRIGHT_FONT_DIRECTORY, file),
  ]),
);
const FONT_CSS = FONT_DEFINITIONS.map(
  ({ file, weight }) => `@font-face {
  font-family: "${DEFAULT_PLAYWRIGHT_FONT_FAMILY}";
  src: url("${FONT_ROUTE_BASE}${file}") format("truetype");
  font-style: normal;
  font-weight: ${weight};
  font-display: block;
}`,
).join("\n");
const FONT_INIT_SCRIPT = `
(() => {
  const installFonts = () => {
    const root = document.head || document.documentElement;
    if (!root || document.getElementById(${JSON.stringify(FONT_STYLE_ID)})) return;
    const style = document.createElement("style");
    style.id = ${JSON.stringify(FONT_STYLE_ID)};
    style.textContent = ${JSON.stringify(FONT_CSS)};
    root.appendChild(style);
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", installFonts, { once: true });
  } else {
    installFonts();
  }
})();
`;

/**
 * Launch the repository-standard Playwright browser.
 *
 * Chromium is the repository browser and headless mode is mandatory.
 */
export function launchDefaultBrowser(options = {}) {
  if (options.headless === false) {
    throw new Error(PLAYWRIGHT_HEADLESS_ONLY_MESSAGE);
  }
  const browserCandidates = [
    chromium.executablePath(),
    // Playwright's downloaded browser is absent in some clean local
    // workspaces. macOS Chrome remains compatible with the pinned Playwright
    // protocol and lets the repository-font route keep SVG/HTML screenshots
    // deterministic instead of falling back to a renderer with missing CJK
    // glyphs.
    ...(process.platform === "darwin"
      ? ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
      : []),
  ];
  const executablePath = browserCandidates.find((candidate) => existsSync(candidate));
  return chromium.launch({
    ...options,
    headless: DEFAULT_PLAYWRIGHT_HEADLESS,
    // Playwright may have the full Chromium bundle while the optional
    // headless-shell download is absent. Use the installed bundle explicitly
    // so repository-font rendering remains available in fresh workspaces.
    ...(executablePath ? { executablePath } : {}),
  });
}

/**
 * Create a browser context that serves the repository fonts to every page.
 */
export async function createDefaultContext(browser, options = {}) {
  const context = await browser.newContext(options);
  await context.route(`${FONT_ROUTE_BASE}**`, async (route) => {
    const requestUrl = new URL(route.request().url());
    const fileName = decodeURIComponent(
      requestUrl.pathname.slice(new URL(FONT_ROUTE_BASE).pathname.length),
    );
    const fontPath = FONT_FILES.get(fileName);
    if (!fontPath) {
      await route.abort("failed");
      return;
    }
    await route.fulfill({
      status: 200,
      body: readFileSync(fontPath),
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=31536000, immutable",
        "Content-Type": "font/ttf",
      },
    });
  });
  await context.addInitScript({ content: FONT_INIT_SCRIPT });
  return context;
}

/**
 * Explicitly load the repository font faces before screenshot or PDF work.
 */
export async function waitForDefaultFonts(page) {
  await page.evaluate(async (fontFamily) => {
    await Promise.all([
      document.fonts.load(`300 16px "${fontFamily}"`),
      document.fonts.load(`400 16px "${fontFamily}"`),
      document.fonts.load(`700 16px "${fontFamily}"`),
    ]);
  }, DEFAULT_PLAYWRIGHT_FONT_FAMILY);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const browser = await launchDefaultBrowser();
  const context = await createDefaultContext(browser);
  try {
    const page = await context.newPage();
    await page.goto(
      "data:text/html,<title>CyberPPT Playwright OK</title><body style=\"font-family:'Microsoft YaHei'\">微软雅黑</body>",
    );
    await waitForDefaultFonts(page);
    console.log(
      JSON.stringify({
        title: await page.title(),
        fontFamily: DEFAULT_PLAYWRIGHT_FONT_FAMILY,
        fontLoaded: await page.evaluate((fontFamily) => {
          return document.fonts.check(`400 16px "${fontFamily}"`);
        }, DEFAULT_PLAYWRIGHT_FONT_FAMILY),
      }),
    );
  } finally {
    await context.close();
    await browser.close();
  }
}
