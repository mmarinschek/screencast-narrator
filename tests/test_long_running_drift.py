"""Long-running drift test: replay Wikipedia search ~100x, check for cumulative drift.

Skipped by default. Run with:
    DYLD_LIBRARY_PATH=/opt/homebrew/lib pytest tests/test_long_running_drift.py -v -s --run-long

To skip the recording phase and reuse an existing recording:
    DYLD_LIBRARY_PATH=/opt/homebrew/lib pytest tests/test_long_running_drift.py -v -s --run-long \
        --reuse-recording=/private/tmp/long_drift_100/test_no_timestamp_drift_after_0/long-drift
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image
from pyzbar.pyzbar import decode as decode_qr

from screencast_narrator.merge import process
from screencast_narrator_client import Storyboard
from wikipedia_search_recording import record_wikipedia_search

REPLAY_COUNT = 100


def _record(output_dir: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()
        sb = Storyboard(output_dir, page, debug_overlay=True)

        for i in range(REPLAY_COUNT):
            record_wikipedia_search(sb, page, iteration=i)
            print(f"  Round {i + 1}/{REPLAY_COUNT} done")

        sb.done()
        context.close()
        browser.close()


def _decode_qr_ms(frame_path: Path) -> int | None:
    img = Image.open(frame_path)
    w, h = img.size
    crop = img.crop((w - 120, h - 120, w, h))
    big = crop.resize((crop.width * 4, crop.height * 4), Image.NEAREST)
    results = decode_qr(big)
    return int(results[0].data.decode("utf-8")) if results else None


@pytest.mark.e2e
@pytest.mark.long
def test_no_timestamp_drift_after_long_session(request: pytest.FixtureRequest, tmp_path: Path) -> None:
    reuse = request.config.getoption("--reuse-recording")

    if reuse:
        output_dir = Path(reuse)
        assert output_dir.exists(), f"Recording dir not found: {output_dir}"
        assert (output_dir / "storyboard.json").exists(), f"No storyboard.json in {output_dir}"
        print(f"\nReusing existing recording from {output_dir}")
        # Clean previous postprocessed output
        for f in output_dir.glob("*.mp4"):
            f.unlink()
        for d in output_dir.glob("narration-tmp"):
            shutil.rmtree(d)
    else:
        output_dir = tmp_path / "long-drift"
        print(f"\nRecording {REPLAY_COUNT} iterations...")
        _record(output_dir)

    print("Postprocessing...")
    process(output_dir, debug_overlay=True, font_size=48)

    mp4 = next(output_dir.glob("*.mp4"))
    assert mp4.exists()

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(mp4)],
        capture_output=True, text=True, check=True,
    )
    duration_s = float(json.loads(probe.stdout)["format"]["duration"])
    print(f"Video: {duration_s:.1f}s ({duration_s / 60:.1f} min)")

    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(exist_ok=True)

    sample_times: list[float] = []
    t = 5.0
    while t < duration_s - 1:
        sample_times.extend([t, t + 0.37])
        t += 30.0

    tolerance_ms = 80
    max_diff = 0

    for t in sample_times:
        fp = frames_dir / f"f_{t:.3f}.png"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(t), "-i", str(mp4), "-frames:v", "1", str(fp)],
            capture_output=True, check=True,
        )
        ms = _decode_qr_ms(fp)
        if ms is None:
            continue
        diff = ms - int(t * 1000)
        max_diff = max(max_diff, abs(diff))
        print(f"  t={t:8.3f}s  qr={ms:8d}ms  diff={diff:+4d}ms")
        assert abs(diff) < tolerance_ms, f"Drift at {t:.3f}s: {diff:+d}ms exceeds {tolerance_ms}ms"

    print(f"\nMax drift: {max_diff}ms")
