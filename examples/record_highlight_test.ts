/**
 * Record a highlight test screencast using TypeScript + Playwright.
 *
 * Usage:
 *     npx tsx examples/record_highlight_test.ts <output-dir> <html-path> <color> <animation-speed-ms>
 */

import { chromium } from "playwright";
import { Storyboard, HighlightStyle } from "../api/typescript-client/src/index";

async function record(outputDir: string, htmlPath: string, color: string, animationSpeedMs: number): Promise<void> {
  const videosDir = `${outputDir}/videos`;

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: {
      dir: videosDir,
      size: { width: 1280, height: 720 },
    },
  });
  const page = await context.newPage();

  const style: HighlightStyle = { color, animationSpeedMs };
  const storyboard = new Storyboard(outputDir, page, {
    debugOverlay: true,
    highlightStyle: style,
  });
  await storyboard.init();

  await page.goto(`file://${htmlPath}`, { waitUntil: "load" });
  await page.waitForSelector("#target", { state: "visible" });

  await storyboard.beginNarration();
  const button = page.locator("#target");
  await storyboard.highlight(button);
  await storyboard.endNarration();

  await context.close();
  await browser.close();
}

const [outputDir, htmlPath, color, speedStr] = process.argv.slice(2);
if (!outputDir || !htmlPath || !color || !speedStr) {
  console.error("Usage: npx tsx examples/record_highlight_test.ts <output-dir> <html-path> <color> <animation-speed-ms>");
  process.exit(1);
}

record(outputDir, htmlPath, color, parseInt(speedStr, 10)).catch((err) => {
  console.error(err);
  process.exit(1);
});
