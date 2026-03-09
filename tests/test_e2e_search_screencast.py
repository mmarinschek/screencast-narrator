"""
End-to-end test: Wikipedia search screencast with narration.

Records a Playwright session that navigates to Wikipedia, searches for
"restaurant", reads the first few section headings, and produces a
narrated screencast via the full screencast-narrator pipeline.

The recording phase randomly picks between Python, TypeScript, and Java
implementations to verify the JSON-based API works across languages.

Requires Python <=3.13 (kokoro/spacy not yet compatible with 3.14).

Requirements:
    uv venv --python 3.13 .venv
    pip install -e ".[e2e]" && playwright install chromium

    For TypeScript recording:
        npm install playwright qrcode
        npx playwright install chromium

    For Java recording:
        mvn compile (in examples/ with pom.xml)

Run:
    pytest tests/test_e2e_search_screencast.py -v
"""

from __future__ import annotations

import random
import shutil
import subprocess
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright

from screencast_narrator.merge import process
from screencast_narrator_client import Storyboard, SyncFrameStyle
from wikipedia_search_recording import record_wikipedia_search

_PROJECT_ROOT = Path(__file__).parent.parent
_EXAMPLES_DIR = _PROJECT_ROOT / "examples"


def _can_run_typescript() -> bool:
    if shutil.which("npx") is None or not (_EXAMPLES_DIR / "record_wikipedia_search.ts").exists():
        return False
    result = subprocess.run(["npx", "--no-install", "tsx", "--version"], capture_output=True, timeout=10)
    return result.returncode == 0


def _can_run_java() -> bool:
    if shutil.which("java") is None or shutil.which("mvn") is None:
        return False
    return (_EXAMPLES_DIR / "RecordWikipediaSearch.java").exists()


def _record_with_python(output_dir: Path) -> None:
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
        sb = Storyboard(output_dir, page, sync_frame_style=SyncFrameStyle(debug_overlay=True))

        record_wikipedia_search(sb, page)
        sb.done()

        context.close()
        browser.close()


def _record_with_typescript(output_dir: Path) -> None:
    result = subprocess.run(
        ["npx", "tsx", str(_EXAMPLES_DIR / "record_wikipedia_search.ts"), str(output_dir)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(_PROJECT_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"TypeScript recording failed:\n{result.stdout}\n{result.stderr}")


def _record_with_java(output_dir: Path) -> None:
    result = subprocess.run(
        [
            "mvn",
            "-f",
            str(_EXAMPLES_DIR / "pom.xml"),
            "compile",
            "exec:java",
            "-Dexec.mainClass=RecordWikipediaSearch",
            f"-Dexec.args={output_dir}",
        ],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(_EXAMPLES_DIR),
    )
    if result.returncode != 0:
        raise RuntimeError(f"Java recording failed:\n{result.stdout}\n{result.stderr}")


def _choose_recording_language() -> str:
    available = ["python"]
    if _can_run_typescript():
        available.append("typescript")
    if _can_run_java():
        available.append("java")
    return random.choice(available)


@pytest.mark.e2e
def test_search_screencast(tmp_path: Path) -> None:
    """Full pipeline: record screencast (random language) -> TTS -> merge -> MP4."""
    language = _choose_recording_language()
    print(f"\nRecording language: {language}")
    print(f"Screencast output directory: {tmp_path}")

    output_dir = tmp_path / "search-screencast"

    if language == "python":
        _record_with_python(output_dir)
    elif language == "typescript":
        _record_with_typescript(output_dir)
    elif language == "java":
        _record_with_java(output_dir)

    # Verify recording produced the expected files
    storyboard_json = output_dir / "storyboard.json"
    assert storyboard_json.exists(), f"storyboard.json was not created by {language} recorder"

    videos_dir = output_dir / "videos"
    webm_files = list(videos_dir.glob("*.webm"))
    assert len(webm_files) > 0, f"No .webm video found after {language} recording"

    # Run the merge pipeline
    process(output_dir)

    # Verify output
    output_mp4 = output_dir / "search-screencast.mp4"
    assert output_mp4.exists(), f"Output MP4 not found at {output_mp4}"
    assert output_mp4.stat().st_size > 10_000, "Output MP4 is suspiciously small"

    assert (output_dir / "timeline.html").exists(), "Timeline HTML was not generated"
    timeline_json = output_dir / "timeline.json"
    assert timeline_json.exists(), "timeline.json was not generated"

    import json
    timeline = json.loads(timeline_json.read_text(encoding="utf-8"))
    assert len(timeline["narrations"]) > 0, "No narrations in timeline — sync frame detection or storyboard reconstruction failed"

    srt_file = output_mp4.with_suffix(".srt")
    assert srt_file.exists(), "SRT subtitle file was not generated"
    srt_content = srt_file.read_text(encoding="utf-8")
    assert len(srt_content.strip()) > 0, "SRT file is empty — no narration subtitles generated"
