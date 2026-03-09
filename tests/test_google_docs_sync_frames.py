"""Test that sync frame overlays render correctly on Google Docs pages.

Google Docs uses a complex DOM (iframes, canvas rendering, high z-index layers).
This test verifies that our green QR overlay is visible and decodable when
injected on top of a Google Docs page.

Run:
    DYLD_LIBRARY_PATH=/opt/homebrew/lib pytest tests/test_google_docs_sync_frames.py -v -s
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode

from screencast_narrator.sync_detect import is_green_frame
from screencast_narrator_client.shared_config import load_shared_config
from screencast_narrator_client.sync_frames import SyncFrameInjector


GOOGLE_DOCS_URL = "https://docs.google.com/document/d/1UCs6CCJP_wle34UlpKZCWGugxh-Jx9D2hxmI6aq1coE/edit?tab=t.0"


def _screenshot_as_pil(page) -> Image.Image:
    return Image.open(BytesIO(page.screenshot()))


def _assert_green_frames_in_video(tmp_path: Path, context_msg: str) -> None:
    import subprocess
    from screencast_narrator.ffmpeg import probe_dimensions

    video_files = list((tmp_path / "video").glob("*.webm"))
    assert len(video_files) > 0, "No video recorded"
    video_path = video_files[0]
    print(f"\nVideo recorded to: {video_path}")

    width, height = probe_dimensions(video_path)
    frame_size = width * height * 3

    pipe = subprocess.Popen(
        ["ffmpeg", "-i", str(video_path), "-r", "25",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )

    green_frame_count = 0
    total_frames = 0
    while True:
        raw = pipe.stdout.read(frame_size)
        if len(raw) < frame_size:
            break
        total_frames += 1
        img = Image.frombytes("RGB", (width, height), raw)
        if is_green_frame(img):
            green_frame_count += 1

    pipe.stdout.close()
    pipe.wait()

    print(f"Video: {total_frames} frames, {green_frame_count} green frames")
    assert green_frame_count > 0, (
        f"Screenshot shows green overlay, but video ({total_frames} frames) contains "
        f"ZERO green frames. The overlay was not captured by the video recorder "
        f"{context_msg}."
    )


@pytest.mark.e2e
def test_sync_frame_visible_over_google_docs(tmp_path: Path) -> None:
    """Inject overlay on Google Docs, screenshot BEFORE removal, verify green + QR."""
    from playwright.sync_api import sync_playwright

    config = load_shared_config()
    sync = SyncFrameInjector(config)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        page.goto(GOOGLE_DOCS_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        before = _screenshot_as_pil(page)
        assert not is_green_frame(before), "Page is green before injection — test is invalid"

        data_url = sync.generate_qr_data_url('{"t":"init"}')
        inject_js = config.sync_frame.resolved_inject_js.replace("{{dataUrl}}", data_url).replace("{{label}}", "test")
        remove_js = config.sync_frame.remove_js

        page.evaluate(inject_js)

        during = _screenshot_as_pil(page)
        during.save(tmp_path / "during_overlay.png")
        print(f"Screenshot saved to: {tmp_path / 'during_overlay.png'}")

        page.evaluate(remove_js)

        context.close()
        browser.close()

    assert is_green_frame(during), (
        "Sync frame overlay is NOT visible over Google Docs. "
        "The green overlay was injected but is not showing in the screenshot."
    )

    qr_results = pyzbar_decode(during)
    assert len(qr_results) > 0, (
        "Green overlay is visible but QR code could not be decoded on Google Docs."
    )


@pytest.mark.e2e
def test_overlay_survives_google_docs_dom_cleanup(tmp_path: Path) -> None:
    """Verify Google Docs doesn't remove our overlay element after injection."""
    from playwright.sync_api import sync_playwright

    config = load_shared_config()
    sync = SyncFrameInjector(config)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        page.goto(GOOGLE_DOCS_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        data_url = sync.generate_qr_data_url('{"t":"init"}')
        inject_js = config.sync_frame.resolved_inject_js.replace("{{dataUrl}}", data_url).replace("{{label}}", "test")

        page.evaluate(inject_js)

        checks: list[tuple[int, bool]] = []
        for ms in [100, 500, 1000, 2000, 3000, 4000]:
            page.wait_for_timeout(100 if not checks else ms - checks[-1][0])
            exists = page.evaluate("() => document.getElementById('_e2e_sync') !== null")
            checks.append((ms, exists))
            print(f"  {ms}ms: overlay exists = {exists}")

        context.close()
        browser.close()

    for ms, exists in checks:
        assert exists, f"Google Docs removed the overlay after {ms}ms!"


@pytest.mark.e2e
def test_sync_frame_visible_over_google_docs_search_bar(tmp_path: Path) -> None:
    """Inject overlay while Google Docs Find & Replace dialog is open."""
    from playwright.sync_api import sync_playwright

    config = load_shared_config()
    sync = SyncFrameInjector(config)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        page.goto(GOOGLE_DOCS_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        page.keyboard.press("Meta+Shift+h")
        page.wait_for_timeout(1000)

        search_open = _screenshot_as_pil(page)
        search_open.save(tmp_path / "search_open.png")
        print(f"\nSearch dialog screenshot: {tmp_path / 'search_open.png'}")

        data_url = sync.generate_qr_data_url('{"t":"init"}')
        inject_js = config.sync_frame.resolved_inject_js.replace("{{dataUrl}}", data_url).replace("{{label}}", "test")
        remove_js = config.sync_frame.remove_js

        page.evaluate(inject_js)

        overlay_info = page.evaluate("""() => {
            const el = document.getElementById('_e2e_sync');
            if (!el) return {exists: false};
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return {
                exists: true,
                rect: {top: rect.top, left: rect.left, width: rect.width, height: rect.height},
                zIndex: style.zIndex,
                display: style.display,
                visibility: style.visibility,
                opacity: style.opacity,
                parent: el.parentElement?.tagName,
            };
        }""")
        print(f"Overlay info with search bar open: {overlay_info}")

        during = _screenshot_as_pil(page)
        during.save(tmp_path / "during_overlay_with_search.png")
        print(f"Screenshot saved to: {tmp_path / 'during_overlay_with_search.png'}")

        page.evaluate(remove_js)

        context.close()
        browser.close()

    assert is_green_frame(during), (
        "Sync frame overlay is NOT visible when Google Docs search bar is open. "
        "The Find & Replace dialog is covering the overlay."
    )

    qr_results = pyzbar_decode(during)
    assert len(qr_results) > 0, (
        "Green overlay is visible but QR code could not be decoded with search bar open."
    )


@pytest.mark.e2e
def test_sync_frame_visible_after_find_and_replace_closed(tmp_path: Path) -> None:
    """Reproduce the exact failing scenario: Find & Replace opened, used, closed with
    Escape, then sync frame injected. This is what happens at narrations 16 and 19
    in the annual-reports e2e test."""
    from playwright.sync_api import sync_playwright

    config = load_shared_config()
    sync = SyncFrameInjector(config)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(tmp_path / "video"),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()

        page.goto(GOOGLE_DOCS_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        page.locator(".kix-appview-editor").click()
        page.wait_for_timeout(300)

        page.keyboard.press("Meta+Shift+h")
        page.wait_for_timeout(500)
        page.keyboard.type("test")
        page.wait_for_timeout(300)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1500)
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        after_escape = _screenshot_as_pil(page)
        after_escape.save(tmp_path / "after_escape.png")
        print(f"\nAfter Escape screenshot: {tmp_path / 'after_escape.png'}")
        assert not is_green_frame(after_escape), "Page is green after Escape — test is invalid"

        data_url = sync.generate_qr_data_url('{"t":"init"}')
        inject_js = config.sync_frame.resolved_inject_js.replace("{{dataUrl}}", data_url).replace("{{label}}", "test")
        remove_js = config.sync_frame.remove_js

        page.evaluate(inject_js)

        overlay_info = page.evaluate("""() => {
            const el = document.getElementById('_e2e_sync');
            if (!el) return {exists: false};
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return {
                exists: true,
                rect: {top: rect.top, left: rect.left, width: rect.width, height: rect.height},
                zIndex: style.zIndex,
                display: style.display,
                visibility: style.visibility,
                opacity: style.opacity,
                parent: el.parentElement?.tagName,
            };
        }""")
        print(f"Overlay info after Find & Replace closed: {overlay_info}")

        during = _screenshot_as_pil(page)
        during.save(tmp_path / "during_overlay_after_escape.png")
        print(f"Screenshot saved to: {tmp_path / 'during_overlay_after_escape.png'}")

        page.wait_for_timeout(2000)

        page.evaluate(remove_js)

        page.wait_for_timeout(500)
        context.close()
        browser.close()

    assert is_green_frame(during), (
        "Sync frame overlay is NOT visible after closing Google Docs Find & Replace. "
        "The Escape key that closed the dialog may have interfered with overlay rendering."
    )

    qr_results = pyzbar_decode(during)
    assert len(qr_results) > 0, (
        "Green overlay visible but QR code not decodable after Find & Replace closed."
    )

    _assert_green_frames_in_video(tmp_path, "after closing Find & Replace with Escape")


@pytest.mark.e2e
def test_sync_frame_visible_after_scrolling_google_docs(tmp_path: Path) -> None:
    """Reproduce narration 15: scroll 10 pages on Google Docs with sync frame
    injections between each scroll step, then inject a final sync frame.
    This is the exact pattern from scroll_page + add_action in annual-reports."""
    from playwright.sync_api import sync_playwright

    config = load_shared_config()
    sync = SyncFrameInjector(config)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(tmp_path / "video"),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()

        page.goto(GOOGLE_DOCS_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        data_url = sync.generate_qr_data_url('{"t":"init"}')
        inject_js = config.sync_frame.resolved_inject_js.replace("{{dataUrl}}", data_url).replace("{{label}}", "")
        remove_js = config.sync_frame.remove_js
        display_ms = config.sync_frame.display_duration_ms
        gap_ms = config.sync_frame.post_removal_gap_ms

        for i in range(10):
            page.keyboard.press("PageDown")
            page.evaluate(inject_js)
            page.wait_for_timeout(display_ms)
            page.evaluate(remove_js)
            page.wait_for_timeout(gap_ms)
            page.evaluate(inject_js)
            page.wait_for_timeout(display_ms)
            page.evaluate(remove_js)
            page.wait_for_timeout(gap_ms)
            page.wait_for_timeout(1500)
            print(f"  Scroll step {i + 1}/10 done")

        print("\nInjecting final sync frame after 10 scrolls...")
        page.evaluate(inject_js)

        during = _screenshot_as_pil(page)
        during.save(tmp_path / "during_overlay_after_scroll.png")
        print(f"Screenshot saved to: {tmp_path / 'during_overlay_after_scroll.png'}")

        page.wait_for_timeout(2000)
        page.evaluate(remove_js)

        page.wait_for_timeout(500)
        context.close()
        browser.close()

    assert is_green_frame(during), (
        "Sync frame overlay is NOT visible after scrolling 10 pages on Google Docs."
    )

    qr_results = pyzbar_decode(during)
    assert len(qr_results) > 0, (
        "Green overlay visible but QR code not decodable after scrolling."
    )

    _assert_green_frames_in_video(tmp_path, "after scrolling 10 pages on Google Docs")
