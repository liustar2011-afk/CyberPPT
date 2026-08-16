import { chromium } from "playwright";
import { fileURLToPath } from "node:url";

export const DEFAULT_PLAYWRIGHT_BROWSER = "chromium";
export const DEFAULT_PLAYWRIGHT_HEADLESS = true;

/**
 * Launch the repository-standard Playwright browser.
 *
 * Chromium and headless mode are the defaults; callers may override launch
 * options explicitly when a headed or specialized run is required.
 */
export function launchDefaultBrowser(options = {}) {
  return chromium.launch({
    ...options,
    headless: options.headless ?? DEFAULT_PLAYWRIGHT_HEADLESS,
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const browser = await launchDefaultBrowser();
  try {
    const page = await browser.newPage();
    await page.goto("data:text/html,<title>CyberPPT Playwright OK</title>");
    console.log(await page.title());
  } finally {
    await browser.close();
  }
}
