"""Element highlighting: draws an animated elliptical circle around a Playwright locator."""

from __future__ import annotations

from screencast_narrator_client.shared_config import HighlightConfig


def draw_highlight(page, locator, config: HighlightConfig) -> None:
    locator.evaluate(config.scroll_js)
    page.evaluate(config.scroll_wait_js)
    locator.evaluate(config.resolved_draw_js)
    page.wait_for_timeout(config.animation_speed_ms + config.draw_wait_ms)


def remove_highlight(page, config: HighlightConfig) -> None:
    page.evaluate(config.remove_js)
    page.wait_for_timeout(config.remove_wait_ms)


def highlight(page, locator, config: HighlightConfig) -> None:
    draw_highlight(page, locator, config)
    remove_highlight(page, config)
