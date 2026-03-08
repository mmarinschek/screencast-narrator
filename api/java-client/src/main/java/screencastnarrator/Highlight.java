package screencastnarrator;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;

public class Highlight {

    private Highlight() {}

    public static void drawHighlight(Page page, Locator locator, SharedConfig.HighlightConfig config) {
        locator.evaluate(config.scrollJs());
        page.evaluate(config.scrollWaitJs());
        locator.evaluate(config.resolvedDrawJs());
        page.waitForTimeout(config.animationSpeedMs() + config.drawWaitMs());
    }

    public static void removeHighlight(Page page, SharedConfig.HighlightConfig config) {
        page.evaluate(config.removeJs());
        page.waitForTimeout(config.removeWaitMs());
    }

    public static void highlight(Page page, Locator locator, SharedConfig.HighlightConfig config) {
        drawHighlight(page, locator, config);
        removeHighlight(page, config);
    }
}
