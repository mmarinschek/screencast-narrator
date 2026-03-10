"""Element highlighting: draws an animated elliptical circle around a Playwright locator."""

from __future__ import annotations

from screencast_narrator_client.shared_config import SharedConfig


def draw_highlight(page, locator, config: SharedConfig) -> None:
    hl = config.highlight
    locator.evaluate(config.resolved_scroll_js)
    page.evaluate(config.resolved_scroll_wait_js)
    locator.evaluate(config.resolved_draw_js)
    page.wait_for_timeout(hl.animation_speed_ms + hl.draw_wait_ms)


def remove_highlight(page, config: SharedConfig) -> None:
    page.evaluate(config.resolved_remove_js)
    page.wait_for_timeout(config.highlight.remove_wait_ms)


def highlight(page, locator, config: SharedConfig) -> None:
    draw_highlight(page, locator, config)
    remove_highlight(page, config)
