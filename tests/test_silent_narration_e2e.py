"""E2E test: silent narrations with title screen actions.

Records a screencast with a silent title slide narration followed by a regular
narration, then runs the full pipeline and verifies the output.

Requirements:
    pip install -e ".[e2e]" && playwright install chromium
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright

from screencast_narrator.merge import process
from screencast_narrator.storyboard import ScreenActionType, Storyboard


@pytest.mark.e2e
def test_silent_title_followed_by_narration(tmp_path: Path) -> None:
    """Silent title narration + regular narration → full pipeline produces valid MP4."""
    output_dir = tmp_path / "silent-narration-test"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()

        storyboard = Storyboard(output_dir, page)

        storyboard.begin_narration()
        storyboard.begin_screen_action(type=ScreenActionType.title, description="Welcome to the demo")
        page.goto("https://example.com", wait_until="load")
        page.wait_for_selector("h1", state="visible")
        storyboard.end_screen_action()
        storyboard.end_narration()

        storyboard.begin_narration(
            "This is a narrated screencast. We are looking at the example.com page."
        )
        storyboard.begin_screen_action(description="Read the page content")
        page.wait_for_selector("p", state="visible")
        storyboard.end_screen_action()
        storyboard.end_narration()
        storyboard.done()

        context.close()
        browser.close()

    storyboard_json = output_dir / "storyboard.json"
    assert storyboard_json.exists()

    data = json.loads(storyboard_json.read_text(encoding="utf-8"))
    assert len(data["narrations"]) == 2
    assert "text" not in data["narrations"][0]
    assert data["narrations"][0]["screenActions"][0]["type"] == "title"
    assert data["narrations"][1]["text"] == "This is a narrated screencast. We are looking at the example.com page."

    videos_dir = output_dir / "videos"
    mp4_files = list(videos_dir.glob("narration-*.mp4"))
    assert len(mp4_files) > 0, "No per-narration MP4 videos found"

    process(output_dir)

    output_mp4 = output_dir / "silent-narration-test.mp4"
    assert output_mp4.exists()
    assert output_mp4.stat().st_size > 1_000

    timeline_json = output_dir / "timeline.json"
    assert timeline_json.exists()
    timeline = json.loads(timeline_json.read_text(encoding="utf-8"))
    assert len(timeline["narrations"]) == 2

    silent_narration = timeline["narrations"][0]
    assert silent_narration["audioDurationMs"] == 0
    assert silent_narration["text"] == ""

    voiced_narration = timeline["narrations"][1]
    assert voiced_narration["audioDurationMs"] > 0
    assert voiced_narration["text"] == "This is a narrated screencast. We are looking at the example.com page."

    srt_file = output_mp4.with_suffix(".srt")
    assert srt_file.exists()
    srt_content = srt_file.read_text(encoding="utf-8")
    assert "narrated screencast" in srt_content
    srt_lines = srt_content.strip().split("\n")
    assert srt_lines[0] == "1"
