/**
 * Record a Wikipedia search screencast using Java + Playwright.
 *
 * Setup:
 *     mvn -f examples/pom.xml compile
 *     mvn -f examples/pom.xml exec:java -Dexec.args="<output-dir>"
 *
 * Produces storyboard.json and a video recording in <output-dir>/videos/.
 * Run `screencast-narrator <output-dir>` afterwards to produce the final MP4.
 */

import com.microsoft.playwright.*;
import com.microsoft.playwright.options.WaitForSelectorState;
import com.microsoft.playwright.options.WaitUntilState;
import screencastnarrator.Storyboard;

import java.nio.file.Path;
import java.util.*;

public class RecordWikipediaSearch {

    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("Usage: java RecordWikipediaSearch <output-dir>");
            System.exit(1);
        }

        Path outputDir = Path.of(args[0]);

        try (Playwright pw = Playwright.create()) {
            Browser browser = pw.chromium().launch(
                new BrowserType.LaunchOptions().setHeadless(true));
            BrowserContext context = browser.newContext(new Browser.NewContextOptions()
                .setViewportSize(1280, 720));
            Page page = context.newPage();

            Storyboard storyboard = new Storyboard(outputDir, page, "en", null, true);

            // --- Step 1: Navigate to Wikipedia ---
            storyboard.narrate(
                "In this screencast, we will search Wikipedia for information "
                    + "about restaurants. Let's start by navigating to the homepage.",
                sb -> sb.screenAction("Navigate to Wikipedia", s -> {
                    page.navigate("https://en.wikipedia.org",
                        new Page.NavigateOptions().setWaitUntil(WaitUntilState.LOAD));
                    page.waitForSelector("input[name='search']",
                        new Page.WaitForSelectorOptions().setState(WaitForSelectorState.VISIBLE));
                }));

            // --- Step 2: Search for "restaurant" ---
            Locator searchBox = page.locator("input[name='search']").first();

            storyboard.narrate(
                "We type 'restaurant' into the search box and press Enter "
                    + "to navigate to the article.",
                sb -> sb.screenAction("Type 'restaurant' and search", s -> {
                    searchBox.click();
                    searchBox.type("restaurant", new Locator.TypeOptions().setDelay(50));
                    searchBox.press("Enter");
                    page.waitForSelector("#firstHeading",
                        new Page.WaitForSelectorOptions().setState(WaitForSelectorState.VISIBLE));
                    page.waitForSelector("#mw-content-text h2",
                        new Page.WaitForSelectorOptions().setState(WaitForSelectorState.VISIBLE));
                }));

            // --- Step 3: Read section headings ---
            List<Locator> headingElements = page.locator(
                "#mw-content-text h2 .mw-headline, #mw-content-text h2").all();
            List<String> headingTexts = new ArrayList<>();
            List<Locator> headingLocators = new ArrayList<>();
            Set<String> skipHeadings = Set.of(
                "See also", "References", "External links", "Notes", "Further reading");

            for (int i = 0; i < Math.min(headingElements.size(), 8); i++) {
                try {
                    String text = headingElements.get(i).innerText(
                        new Locator.InnerTextOptions().setTimeout(2000));
                    text = text.replace("[edit]", "").trim();
                    if (!text.isEmpty() && !skipHeadings.contains(text)) {
                        headingTexts.add(text);
                        headingLocators.add(headingElements.get(i));
                    }
                } catch (Exception e) {
                    // skip unreadable headings
                }
            }

            for (int i = 0; i < Math.min(headingTexts.size(), 3); i++) {
                String headingText = headingTexts.get(i);
                Locator headingEl = headingLocators.get(i);

                storyboard.narrate(
                    "Section " + (i + 1) + " of the article is titled: " + headingText + ".",
                    sb -> sb.screenAction("Read section heading: " + headingText, s -> {
                        sb.highlight(headingEl);
                    }));
            }

            storyboard.done();
            context.close();
            browser.close();
        }
    }
}
