"""Record a highlight test screencast using Python + Playwright.

Usage:
    python examples/record_highlight_test.py <output-dir> <html-path> <color> <animation-speed-ms>
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from screencast_narrator.storyboard import HighlightStyle, Storyboard


def record(output_dir: Path, html_path: Path, color: str, animation_speed_ms: int) -> None:
    videos_dir = output_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    style = HighlightStyle(color=color, animation_speed_ms=animation_speed_ms)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(videos_dir),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()

        storyboard = Storyboard(output_dir, page, debug_overlay=True, highlight_style=style)

        page.goto(f"file://{html_path}", wait_until="load")
        page.wait_for_selector("#target", state="visible")

        storyboard.begin_narration()
        button = page.locator("#target")
        storyboard.highlight(button)
        storyboard.end_narration()

        context.close()
        browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python examples/record_highlight_test.py <output-dir> <html-path> <color> <animation-speed-ms>", file=sys.stderr)
        sys.exit(1)
    record(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]))
