"""Visual demo: record highlights on elements of different sizes.

Run with: DYLD_LIBRARY_PATH=/opt/homebrew/lib pytest tests/test_underline_visual_demo.py -v -s --basetemp=/tmp/underline-demo

Then open the videos in /tmp/underline-demo/ to compare.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_DEMO_PAGE = """<!DOCTYPE html>
<html>
<body style="margin:0; background:white; padding:20px; font-family:sans-serif;">
  <div id="small-btn" style="display:inline-block; padding:12px 24px; background:#e0e7ff; border-radius:6px; margin:10px;">
    Small Button
  </div>

  <div id="medium-card" style="width:400px; padding:20px; background:#f0f0f0; border-radius:8px; margin:20px 0;">
    <h3 style="margin:0 0 10px 0;">Medium Card</h3>
    <p style="margin:0;">Some content in a medium-sized card.</p>
  </div>

  <div id="large-card" style="width:90vw; height:50vh; padding:30px; background:#f8f8f8; border-radius:8px; margin:20px 0;">
    <h2 style="margin:0 0 20px 0; font-size:28px;">Large Card Title</h2>
    <p>This card takes up a lot of the viewport.</p>
    <p>The highlight should underline the heading, not circle everything.</p>
  </div>

  <div id="large-no-heading" style="width:90vw; height:40vh; padding:30px; background:#f0f8ff; border-radius:8px; margin:20px 0;">
    <p style="font-size:18px; margin:0;">Large area with no heading — underline should go under the full element width.</p>
  </div>
</body>
</html>"""


def _record_highlight_on(output_dir: Path, html_path: Path, selector: str) -> Path:
    from playwright.sync_api import sync_playwright
    from screencast_narrator_client import Storyboard

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(500)

        sb = Storyboard(output_dir, page=page)
        sb.begin_narration(f"Highlighting {selector}")
        sb.highlight(page.locator(selector))
        sb.end_narration()
        sb.done()
        browser.close()

    return output_dir / "videos" / "narration-000.mp4"


@pytest.mark.e2e
def test_highlight_visual_demo(tmp_path: Path) -> None:
    """Record highlights on 4 different element sizes for visual comparison."""
    html_path = tmp_path / "demo.html"
    html_path.write_text(_DEMO_PAGE, encoding="utf-8")

    targets = [
        ("small-btn", "#small-btn"),
        ("medium-card", "#medium-card"),
        ("large-card", "#large-card"),
        ("large-no-heading", "#large-no-heading"),
    ]

    for name, selector in targets:
        out = tmp_path / name
        video = _record_highlight_on(out, html_path, selector)
        assert video.exists(), f"Video not found for {name}"
        print(f"\n  {name}: {video}")

    print(f"\nOpen videos with: open {tmp_path}/*/videos/narration-000.mp4")
