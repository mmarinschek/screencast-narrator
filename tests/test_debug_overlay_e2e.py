"""E2E test: verify debug overlay QR timestamps match actual video playback time.

Records a screencast, processes it with debug overlay enabled, then extracts
frames at known timestamps and decodes the QR code overlay to verify the
displayed time matches the actual video position.

Requirements:
    pip install -e ".[e2e]" && playwright install chromium
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image
from pyzbar.pyzbar import decode as decode_qr

from screencast_narrator.merge import process


def _extract_frame(video: Path, time_s: float, output: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(time_s), "-i", str(video), "-frames:v", "1", str(output)],
        capture_output=True,
        check=True,
    )


def _decode_qr_timestamp(frame_path: Path) -> int | None:
    img = Image.open(frame_path)
    w, h = img.size
    qr_crop = img.crop((w - 120, h - 120, w, h))
    qr_big = qr_crop.resize((qr_crop.width * 4, qr_crop.height * 4), Image.NEAREST)
    results = decode_qr(qr_big)
    if not results:
        return None
    return int(results[0].data.decode("utf-8"))


@pytest.mark.e2e
def test_overlay_qr_timestamps_match_video_time(tmp_path: Path) -> None:
    """Extract frames at known times and verify QR-decoded timestamps match."""
    output_dir = tmp_path / "overlay-test"
    result = subprocess.run(
        [sys.executable, "examples/record_wikipedia_search.py", str(output_dir)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Recording failed:\n{result.stdout}\n{result.stderr}")

    process(output_dir, debug_overlay=True, font_size=48)

    mp4 = output_dir / (output_dir.name + ".mp4")
    assert mp4.exists()

    import json
    timeline_json = output_dir / "timeline.json"
    assert timeline_json.exists(), "timeline.json was not generated"
    timeline = json.loads(timeline_json.read_text(encoding="utf-8"))
    assert len(timeline["narrations"]) > 0, "No narrations in timeline — sync frame detection or storyboard reconstruction failed"

    frames_dir = tmp_path / "extracted_frames"
    frames_dir.mkdir()

    sample_times = [2.0, 5.0, 8.0, 12.0, 16.0]

    for t in sample_times:
        frame_path = frames_dir / f"frame_{t:.1f}.png"
        _extract_frame(mp4, t, frame_path)
        decoded_second = _decode_qr_timestamp(frame_path)

        assert decoded_second is not None, f"QR code not decoded from frame at t={t}s"
        assert abs(decoded_second - t) < 1.5, (
            f"Timestamp mismatch at t={t}s: QR shows {decoded_second}s, "
            f"diff={abs(decoded_second - t):.1f}s > 1.5s tolerance"
        )
