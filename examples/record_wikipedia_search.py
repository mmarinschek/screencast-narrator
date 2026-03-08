"""Record a Wikipedia search screencast using Python + Playwright.

Usage:
    python examples/record_wikipedia_search.py <output-dir>

Produces storyboard.json and a video recording in <output-dir>/videos/.
Run `screencast-narrator <output-dir>` afterwards to produce the final MP4.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from screencast_narrator.storyboard import Storyboard


def record(output_dir: Path) -> None:
    videos_dir = output_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(videos_dir),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()

        storyboard = Storyboard(output_dir, page, debug_overlay=True)

        # --- Step 1: Navigate to Wikipedia ---
        storyboard.begin_narration(
            "In this screencast, we will search Wikipedia for information "
            "about restaurants. Let's start by navigating to the homepage."
        )
        storyboard.begin_screen_action(description="Navigate to Wikipedia")
        page.goto("https://en.wikipedia.org", wait_until="load")
        page.wait_for_selector("input[name='search']", state="visible")
        storyboard.end_screen_action()
        storyboard.end_narration()

        # --- Step 2: Search for "restaurant" ---
        search_box = page.locator("input[name='search']").first

        storyboard.begin_narration(
            "We type 'restaurant' into the search box and press Enter to navigate to the article."
        )
        storyboard.begin_screen_action(description="Type 'restaurant' and search")
        search_box.click()
        search_box.type("restaurant", delay=50)
        search_box.press("Enter")
        page.wait_for_selector("#firstHeading", state="visible")
        page.wait_for_selector("#mw-content-text h2", state="visible")
        storyboard.end_screen_action()
        storyboard.end_narration()

        # --- Step 3: Read section headings ---
        heading_elements = page.locator("#mw-content-text h2 .mw-headline, #mw-content-text h2").all()
        headings = []
        for el in heading_elements[:8]:
            try:
                text = el.inner_text(timeout=2000)
                text = text.replace("[edit]", "").strip()
                if text and text not in ("See also", "References", "External links", "Notes", "Further reading"):
                    headings.append((text, el))
            except Exception:
                continue

        if not headings:
            headings = [("No section headings found on the page", None)]

        for i, (heading_text, heading_el) in enumerate(headings[:3]):
            storyboard.begin_narration(f"Section {i + 1} of the article is titled: {heading_text}.")

            storyboard.begin_screen_action(description=f"Read section heading: {heading_text}")
            if heading_el is not None:
                storyboard.highlight(heading_el)
            storyboard.end_screen_action()

            storyboard.end_narration()

        context.close()
        browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/record_wikipedia_search.py <output-dir>", file=sys.stderr)
        sys.exit(1)
    record(Path(sys.argv[1]))
