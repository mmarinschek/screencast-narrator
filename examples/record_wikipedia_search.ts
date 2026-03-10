/**
 * Record a Wikipedia search screencast using TypeScript + Playwright.
 *
 * Setup:
 *     npm install playwright qrcode @types/qrcode
 *     npx playwright install chromium
 *
 * Usage:
 *     npx tsx examples/record_wikipedia_search.ts <output-dir>
 *
 * Produces storyboard.json and a video recording in <output-dir>/videos/.
 * Run `screencast-narrator <output-dir>` afterwards to produce the final MP4.
 */

import { chromium } from "playwright";
import { Storyboard } from "../api/typescript-client/src/index";

async function record(outputDir: string): Promise<void> {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
  });
  const page = await context.newPage();

  const storyboard = new Storyboard(outputDir, page, { debugOverlay: true });

  // --- Step 1: Navigate to Wikipedia ---
  await storyboard.narrate(
    async (sb) => {
      await sb.screenAction(
        async () => {
          await page.goto("https://en.wikipedia.org", { waitUntil: "load" });
          await page.waitForSelector("input[name='search']", {
            state: "visible",
          });
        },
        { description: "Navigate to Wikipedia" }
      );
    },
    "In this screencast, we will search Wikipedia for information " +
      "about restaurants. Let's start by navigating to the homepage."
  );

  // --- Step 2: Search for "restaurant" ---
  const searchBox = page.locator("input[name='search']").first();

  await storyboard.narrate(
    async (sb) => {
      await sb.screenAction(
        async () => {
          await searchBox.click();
          await searchBox.type("restaurant", { delay: 50 });
          await searchBox.press("Enter");
          await page.waitForSelector("#firstHeading", { state: "visible" });
          await page.waitForSelector("#mw-content-text h2", {
            state: "visible",
          });
        },
        { description: "Type 'restaurant' and search" }
      );
    },
    "We type 'restaurant' into the search box and press Enter to navigate to the article."
  );

  // --- Step 3: Read section headings ---
  const headingElements = await page
    .locator("#mw-content-text h2 .mw-headline, #mw-content-text h2")
    .all();
  const headings: { text: string; el: (typeof headingElements)[0] }[] = [];
  const skipHeadings = new Set([
    "See also",
    "References",
    "External links",
    "Notes",
    "Further reading",
  ]);

  for (const el of headingElements.slice(0, 8)) {
    try {
      let text = await el.innerText({ timeout: 2000 });
      text = text.replace("[edit]", "").trim();
      if (text && !skipHeadings.has(text)) {
        headings.push({ text, el });
      }
    } catch {
      continue;
    }
  }

  if (headings.length === 0) {
    await storyboard.narrate(
      async () => {},
      "No section headings were found on the page."
    );
  }

  for (let i = 0; i < Math.min(headings.length, 3); i++) {
    const { text: headingText, el: headingEl } = headings[i];
    await storyboard.narrate(
      async (sb) => {
        await sb.screenAction(
          async () => {
            await sb.highlight(headingEl);
          },
          { description: `Read section heading: ${headingText}` }
        );
      },
      `Section ${i + 1} of the article is titled: ${headingText}.`
    );
  }

  await storyboard.done();
  await context.close();
  await browser.close();
}

const outputDir = process.argv[2];
if (!outputDir) {
  console.error(
    "Usage: npx tsx examples/record_wikipedia_search.ts <output-dir>"
  );
  process.exit(1);
}

record(outputDir).catch((err) => {
  console.error(err);
  process.exit(1);
});
