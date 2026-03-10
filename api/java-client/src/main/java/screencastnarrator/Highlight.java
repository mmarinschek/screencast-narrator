package screencastnarrator;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;

public class Highlight {

    private Highlight() {}

    public static void drawHighlight(Page page, Locator locator, SharedConfig config) {
        locator.evaluate(config.highlight().getScrollJs());
        page.evaluate(config.highlight().getScrollWaitJs());
        locator.evaluate(config.resolvedDrawJs());
        page.waitForTimeout(config.highlight().getAnimationSpeedMs() + config.highlight().getDrawWaitMs());
    }

    public static void removeHighlight(Page page, SharedConfig config) {
        page.evaluate(config.highlight().getRemoveJs());
        page.waitForTimeout(config.highlight().getRemoveWaitMs());
    }

    public static void highlight(Page page, Locator locator, SharedConfig config) {
        drawHighlight(page, locator, config);
        removeHighlight(page, config);
    }
}
