"""Sync pipeline tests: building narrations from sync positions and computing audio delays."""

from screencast_narrator.freeze_frames import FreezeFrameCalculator, NarrationSegment
from screencast_narrator.merge import _build_narrations_from_sync
from screencast_narrator.shared_config import load_shared_config

_SM = load_shared_config().sync_markers


def assert_no_audio_overlap(audio_delays: list[int], narrations: list[NarrationSegment]) -> None:
    for i in range(len(audio_delays) - 1):
        audio_end = audio_delays[i] + narrations[i].audio_duration_ms
        assert audio_end <= audio_delays[i + 1], (
            f"narration {i} audio (ends {audio_end}ms) must not overlap "
            f"narration {i + 1} (starts {audio_delays[i + 1]}ms)"
        )


def test_build_narrations_and_compute_delays():
    sync_positions = {
        _SM.narration_start(0): 1.0,
        _SM.narration_end(0): 3.0,
        _SM.narration_start(1): 3.5,
        _SM.narration_end(1): 5.5,
    }
    narrations = _build_narrations_from_sync(
        ["first narration", "second narration"],
        [3000, 3000],
        sync_positions,
    )
    result = FreezeFrameCalculator(narrations, []).calculate()
    assert_no_audio_overlap(result.adjusted_timestamps, narrations)


def test_many_narrations_should_not_overlap():
    sync_positions: dict[str, float] = {}
    texts: list[str] = []
    audio_durations: list[int] = []
    pos = 0.0

    for i in range(5):
        sync_positions[_SM.narration_start(i)] = pos
        pos += 3.0
        sync_positions[_SM.narration_end(i)] = pos
        pos += 0.5
        texts.append(f"narration {i}")
        audio_durations.append(4000)

    narrations = _build_narrations_from_sync(texts, audio_durations, sync_positions)
    result = FreezeFrameCalculator(narrations, []).calculate()
    assert_no_audio_overlap(result.adjusted_timestamps, narrations)


def test_single_narration_freeze_duration():
    sync_positions = {
        _SM.narration_start(0): 0.0,
        _SM.narration_end(0): 2.0,
    }
    narrations = _build_narrations_from_sync(["only narration"], [5000], sync_positions)
    result = FreezeFrameCalculator(narrations, []).calculate()

    bracket_duration = narrations[0].end_ms - narrations[0].start_ms
    assert bracket_duration == 2000
    assert len(result.freeze_frames) == 1
    assert result.freeze_frames[0].duration_ms == 3000
