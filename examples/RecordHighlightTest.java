/**
 * Record a highlight test screencast using Java + Playwright.
 *
 * Usage:
 *     mvn -f examples/pom.xml compile exec:java \
 *         -Dexec.mainClass=RecordHighlightTest \
 *         -Dexec.args="<output-dir> <html-path> <color> <animation-speed-ms>"
 */

import com.microsoft.playwright.*;
import com.microsoft.playwright.options.WaitForSelectorState;
import com.microsoft.playwright.options.WaitUntilState;
import screencastnarrator.Storyboard;
import screencastnarrator.generated.HighlightStyle;

import java.nio.file.Files;
import java.nio.file.Path;

public class RecordHighlightTest {

    public static void main(String[] args) throws Exception {
        if (args.length < 4) {
            System.err.println("Usage: java RecordHighlightTest <output-dir> <html-path> <color> <animation-speed-ms>");
            System.exit(1);
        }

        Path outputDir = Path.of(args[0]);
        String htmlPath = args[1];
        String color = args[2];
        int animationSpeedMs = Integer.parseInt(args[3]);

        Path videosDir = outputDir.resolve("videos");
        Files.createDirectories(videosDir);

        HighlightStyle style = new HighlightStyle(color, animationSpeedMs, null, null, null);

        try (Playwright pw = Playwright.create()) {
            Browser browser = pw.chromium().launch(
                new BrowserType.LaunchOptions().setHeadless(true));
            BrowserContext context = browser.newContext(new Browser.NewContextOptions()
                .setViewportSize(1280, 720)
                .setRecordVideoDir(videosDir)
                .setRecordVideoSize(1280, 720));
            Page page = context.newPage();

            Storyboard storyboard = new Storyboard(outputDir, page, "en", true, 24, style);

            page.navigate("file://" + htmlPath,
                new Page.NavigateOptions().setWaitUntil(WaitUntilState.LOAD));
            page.waitForSelector("#target",
                new Page.WaitForSelectorOptions().setState(WaitForSelectorState.VISIBLE));

            storyboard.beginNarration();
            Locator button = page.locator("#target");
            storyboard.highlight(button);
            storyboard.endNarration();

            context.close();
            browser.close();
        }
    }
}
