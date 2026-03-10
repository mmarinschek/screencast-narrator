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

from screencast_narrator_client import Storyboard


def record(output_dir: Path) -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()

        storyboard = Storyboard(output_dir, page, debug_overlay=True)

        # --- Step 1: Navigate to Wikipedia ---
        def navigate(sb: Storyboard) -> None:
            def do_navigate(_sb: Storyboard) -> None:
                page.goto("https://en.wikipedia.org", wait_until="load")
                page.wait_for_selector("input[name='search']", state="visible")

            sb.screen_action(do_navigate, description="Navigate to Wikipedia")

        storyboard.narrate(
            navigate,
            text="In this screencast, we will search Wikipedia for information "
            "about restaurants. Let's start by navigating to the homepage.",
        )

        # --- Step 2: Search for "restaurant" ---
        search_box = page.locator("input[name='search']").first

        def search(sb: Storyboard) -> None:
            def do_search(_sb: Storyboard) -> None:
                search_box.click()
                search_box.type("restaurant", delay=50)
                search_box.press("Enter")
                page.wait_for_selector("#firstHeading", state="visible")
                page.wait_for_selector("#mw-content-text h2", state="visible")

            sb.screen_action(do_search, description="Type 'restaurant' and search")

        storyboard.narrate(
            search,
            text="We type 'restaurant' into the search box and press Enter to navigate to the article.",
        )

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
            def read_heading(sb: Storyboard, el=heading_el, desc=heading_text) -> None:
                def do_highlight(_sb: Storyboard) -> None:
                    if el is not None:
                        sb.highlight(el)

                sb.screen_action(do_highlight, description=f"Read section heading: {desc}")

            storyboard.narrate(
                read_heading,
                text=f"Section {i + 1} of the article is titled: {heading_text}.",
            )

        storyboard.done()
        context.close()
        browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/record_wikipedia_search.py <output-dir>", file=sys.stderr)
        sys.exit(1)
    record(Path(sys.argv[1]))
