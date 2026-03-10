"""Tests for debug overlay drawtext filter generation."""

from screencast_narrator.debug_overlay import generate_overlay_filter
from screencast_narrator.narration_segment import NarrationSegment
from screencast_narrator_client.generated.storyboard_types import (
    Model as StoryboardModel,
    Narration as StoryboardNarration,
)


def _read_all_overlay_texts(tmp_path):
    overlay_dir = tmp_path / "overlay_texts"
    if not overlay_dir.exists():
        return []
    return [f.read_text(encoding="utf-8") for f in sorted(overlay_dir.glob("t*.txt"))]


def _empty_storyboard() -> StoryboardModel:
    return StoryboardModel(language="en", narrations=[])


def test_generates_filter_with_narrations(tmp_path):
    narrations = [
        NarrationSegment(1000, 3000, "First narration", 2500),
        NarrationSegment(4000, 6000, "Second narration", 3000),
    ]
    final_timestamps = [1000, 4000]
    storyboard = StoryboardModel(language="en", narrations=[
        StoryboardNarration(narration_id=0, text="First"),
        StoryboardNarration(narration_id=1, text="Second"),
    ])

    result = generate_overlay_filter(narrations, final_timestamps, storyboard, tmp_path)

    assert "drawtext=" in result.filter_str
    assert result.qr_video.exists()
    texts = _read_all_overlay_texts(tmp_path)
    combined = " ".join(texts)
    assert "N0" in combined
    assert "N1" in combined
    assert "First narration" in combined
    assert "Second narration" in combined


def test_includes_timestamp_display(tmp_path):
    narrations = [NarrationSegment(0, 2000, "Test", 1500)]
    result = generate_overlay_filter(narrations, [0], _empty_storyboard(), tmp_path)

    assert "pts" in result.filter_str
