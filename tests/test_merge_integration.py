"""Integration tests for the merge pipeline: storyboard parsing and narration building."""

import json

import pytest

from screencast_narrator.freeze_frames import HighlightEntry, NarrationSegment
from screencast_narrator.merge import (
    _build_highlights,
    _build_narrations_from_sync,
    _build_storyboard_from_sync,
    _extract_narration_texts,
    _segment_name,
)
from screencast_narrator.sync_detect import SyncDetectionResult, SyncFrameSpan
from screencast_narrator.shared_config import load_shared_config
from screencast_narrator_client.generated.storyboard_types import (
    Model as StoryboardModel,
    Narration as StoryboardNarration,
    ScreenAction,
    ScreenActionTiming,
    ScreenActionType,
)

_SM = load_shared_config().sync_markers


def _make_storyboard(narration_texts: list[str]) -> StoryboardModel:
    return StoryboardModel(
        language="en",
        narrations=[
            StoryboardNarration(narration_id=i, text=text)
            for i, text in enumerate(narration_texts)
        ],
    )


def test_extract_narration_texts():
    root = _make_storyboard(["first narration", "second narration"])
    result = _extract_narration_texts(root)
    assert result == ["first narration", "second narration"]


def test_extract_narration_texts_empty():
    root = _make_storyboard([])
    result = _extract_narration_texts(root)
    assert result == []


def test_extract_narration_texts_with_screen_actions():
    root = StoryboardModel(
        language="en",
        narrations=[
            StoryboardNarration(
                narration_id=0,
                text="Navigate to page",
                screen_actions=[
                    ScreenAction(type=ScreenActionType.navigate, screen_action_id=0, description="Click button"),
                ],
            )
        ],
    )
    result = _extract_narration_texts(root)
    assert result == ["Navigate to page"]


def test_segment_name():
    assert _segment_name(0) == "segment_000.wav"
    assert _segment_name(42) == "segment_042.wav"
    assert _segment_name(999) == "segment_999.wav"


def test_build_narrations_from_sync():
    sync_positions = {
        _SM.narration_start(0): 1.0,
        _SM.narration_end(0): 3.5,
        _SM.narration_start(1): 4.0,
        _SM.narration_end(1): 6.0,
    }
    result = _build_narrations_from_sync(
        ["first narration", "second narration"],
        [2500, 3000],
        sync_positions,
    )

    assert len(result) == 2
    assert result[0] == NarrationSegment(1000, 3500, "first narration", 2500)
    assert result[1] == NarrationSegment(4000, 6000, "second narration", 3000)


def test_build_narrations_from_sync_missing_start():
    sync_positions = {_SM.narration_end(0): 3.5}
    with pytest.raises(RuntimeError, match="Missing START sync frame for narration 0"):
        _build_narrations_from_sync(["text"], [2500], sync_positions)


def test_build_narrations_from_sync_missing_end():
    sync_positions = {_SM.narration_start(0): 1.0}
    with pytest.raises(RuntimeError, match="Missing END sync frame for narration 0"):
        _build_narrations_from_sync(["text"], [2500], sync_positions)


def test_build_highlights_from_casted_actions():
    storyboard = StoryboardModel(
        language="en",
        narrations=[
            StoryboardNarration(
                narration_id=0,
                text="Test",
                screen_actions=[
                    ScreenAction(type=ScreenActionType.navigate, screen_action_id=0, description="Navigate"),
                    ScreenAction(type=ScreenActionType.navigate, screen_action_id=1, description="Idle", timing=ScreenActionTiming.elastic),
                    ScreenAction(type=ScreenActionType.navigate, screen_action_id=2, description="Click"),
                ],
            )
        ],
    )
    sync_positions = {
        _SM.narration_start(0): 0.0,
        _SM.narration_end(0): 10.0,
        _SM.action_start(0): 0.5,
        _SM.action_end(0): 3.0,
        _SM.action_start(1): 3.0,
        _SM.action_end(1): 7.0,
        _SM.action_start(2): 7.0,
        _SM.action_end(2): 9.5,
    }
    highlights = _build_highlights(storyboard, sync_positions)

    assert len(highlights) == 2
    assert highlights[0] == HighlightEntry(500, 2500)
    assert highlights[1] == HighlightEntry(7000, 2500)


def test_build_highlights_skips_actions_without_sync_frames():
    storyboard = StoryboardModel(
        language="en",
        narrations=[
            StoryboardNarration(
                narration_id=0,
                text="Test",
                screen_actions=[
                    ScreenAction(type=ScreenActionType.navigate, screen_action_id=0, description="No sync frames"),
                ],
            )
        ],
    )
    sync_positions = {_SM.narration_start(0): 0.0, _SM.narration_end(0): 5.0}
    highlights = _build_highlights(storyboard, sync_positions)
    assert highlights == []


def test_build_highlights_timed_actions_block_freeze():
    storyboard = StoryboardModel(
        language="en",
        narrations=[
            StoryboardNarration(
                narration_id=0,
                text="Test",
                screen_actions=[
                    ScreenAction(
                        type=ScreenActionType.navigate,
                        screen_action_id=0,
                        description="Animation",
                        timing=ScreenActionTiming.timed,
                        duration_ms=5000,
                    ),
                ],
            )
        ],
    )
    sync_positions = {
        _SM.narration_start(0): 0.0,
        _SM.narration_end(0): 10.0,
        _SM.action_start(0): 1.0,
        _SM.action_end(0): 6.0,
    }
    highlights = _build_highlights(storyboard, sync_positions)
    assert len(highlights) == 1
    assert highlights[0] == HighlightEntry(1000, 5000)


def test_round_trip_storyboard_json(tmp_path):
    root = _make_storyboard(["hello world", "second part"])
    storyboard_file = tmp_path / "storyboard.json"
    storyboard_file.write_text(root.model_dump_json(by_alias=True, exclude_none=True), encoding="utf-8")

    loaded_data = json.loads(storyboard_file.read_text(encoding="utf-8"))
    loaded = StoryboardModel.model_validate(loaded_data)
    texts = _extract_narration_texts(loaded)
    assert texts == ["hello world", "second part"]


def test_build_storyboard_from_sync_basic():
    sync_detection = SyncDetectionResult(
        qr_spans=[
            SyncFrameSpan(_SM.narration, 0, _SM.start, 10, 14),
            SyncFrameSpan(_SM.narration, 0, _SM.end, 50, 54),
            SyncFrameSpan(_SM.narration, 1, _SM.start, 80, 84),
            SyncFrameSpan(_SM.narration, 1, _SM.end, 120, 124),
        ],
        green_frame_indices=set(range(10, 15)) | set(range(50, 55)) | set(range(80, 85)) | set(range(120, 125)),
        total_frames=200,
        narration_texts={0: "First narration", 1: "Second narration"},
        init_data={"t": _SM.init, "language": "de"},
    )
    storyboard = _build_storyboard_from_sync(sync_detection)

    assert storyboard.language == "de"
    assert len(storyboard.narrations) == 2
    assert storyboard.narrations[0].text == "First narration"
    assert storyboard.narrations[1].text == "Second narration"

    texts = _extract_narration_texts(storyboard)
    assert texts == ["First narration", "Second narration"]


def test_build_storyboard_from_sync_with_screen_actions():
    sync_detection = SyncDetectionResult(
        qr_spans=[
            SyncFrameSpan(_SM.narration, 0, _SM.start, 10, 14),
            SyncFrameSpan(_SM.action, 0, _SM.start, 20, 24),
            SyncFrameSpan(_SM.action, 0, _SM.end, 40, 44),
            SyncFrameSpan(_SM.action, 1, _SM.start, 50, 54),
            SyncFrameSpan(_SM.action, 1, _SM.end, 70, 74),
            SyncFrameSpan(_SM.narration, 0, _SM.end, 80, 84),
        ],
        green_frame_indices=set(),
        total_frames=200,
        narration_texts={0: "With actions"},
        init_data={},
    )
    storyboard = _build_storyboard_from_sync(sync_detection)

    assert len(storyboard.narrations) == 1
    actions = storyboard.narrations[0].screen_actions
    assert len(actions) == 2
    assert actions[0].screen_action_id == 0
    assert actions[1].screen_action_id == 1


def test_build_storyboard_from_sync_with_highlights():
    sync_detection = SyncDetectionResult(
        qr_spans=[
            SyncFrameSpan(_SM.narration, 0, _SM.start, 10, 14),
            SyncFrameSpan(_SM.highlight, 0, _SM.start, 30, 34),
            SyncFrameSpan(_SM.highlight, 0, _SM.end, 45, 49),
            SyncFrameSpan(_SM.narration, 0, _SM.end, 80, 84),
        ],
        green_frame_indices=set(),
        total_frames=200,
        narration_texts={0: "With highlight"},
        screen_actions={0: ScreenAction(type=ScreenActionType.highlight, screen_action_id=0)},
        init_data={},
    )
    storyboard = _build_storyboard_from_sync(sync_detection)

    actions = storyboard.narrations[0].screen_actions
    assert len(actions) == 1
    assert actions[0].type == ScreenActionType.highlight
    assert actions[0].screen_action_id == 0


def test_build_storyboard_from_sync_with_action_metadata():
    sync_detection = SyncDetectionResult(
        qr_spans=[
            SyncFrameSpan(_SM.narration, 0, _SM.start, 10, 14),
            SyncFrameSpan(_SM.action, 0, _SM.start, 20, 24),
            SyncFrameSpan(_SM.action, 0, _SM.end, 40, 44),
            SyncFrameSpan(_SM.action, 1, _SM.start, 50, 54),
            SyncFrameSpan(_SM.action, 1, _SM.end, 70, 74),
            SyncFrameSpan(_SM.narration, 0, _SM.end, 80, 84),
        ],
        green_frame_indices=set(),
        total_frames=200,
        narration_texts={0: "With actions"},
        init_data={},
        screen_actions={
            0: ScreenAction(type=ScreenActionType.navigate, screen_action_id=0, description="Click button"),
            1: ScreenAction(type=ScreenActionType.navigate, screen_action_id=1, description="Idle wait", timing=ScreenActionTiming.elastic),
        },
    )
    storyboard = _build_storyboard_from_sync(sync_detection)

    actions = storyboard.narrations[0].screen_actions
    assert actions[0].description == "Click button"
    assert actions[0].timing is None
    assert actions[1].description == "Idle wait"
    assert actions[1].timing == ScreenActionTiming.elastic


def test_build_storyboard_from_sync_with_translations():
    sync_detection = SyncDetectionResult(
        qr_spans=[
            SyncFrameSpan(_SM.narration, 0, _SM.start, 10, 14),
            SyncFrameSpan(_SM.narration, 0, _SM.end, 50, 54),
        ],
        green_frame_indices=set(),
        total_frames=100,
        narration_texts={0: "Hello world"},
        narration_translations={0: {"de": "Hallo Welt", "fr": "Bonjour le monde"}},
        init_data={"t": _SM.init, "language": "en"},
    )
    storyboard = _build_storyboard_from_sync(sync_detection)

    assert storyboard.narrations[0].translations["de"] == "Hallo Welt"
    assert storyboard.narrations[0].translations["fr"] == "Bonjour le monde"


def test_build_storyboard_from_sync_no_init_data():
    sync_detection = SyncDetectionResult(
        qr_spans=[
            SyncFrameSpan(_SM.narration, 0, _SM.start, 10, 14),
            SyncFrameSpan(_SM.narration, 0, _SM.end, 50, 54),
        ],
        green_frame_indices=set(),
        total_frames=100,
        narration_texts={0: "Solo"},
        init_data={},
    )
    storyboard = _build_storyboard_from_sync(sync_detection)

    assert storyboard.language == "en"
    assert storyboard.narrations[0].text == "Solo"
