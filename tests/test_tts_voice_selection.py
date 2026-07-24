"""Tests for per-language voice selection in TTS generation."""

from __future__ import annotations

from pathlib import Path

import pytest
from screencast_narrator_client.generated.storyboard_types import (
    Model as StoryboardModel,
)
from screencast_narrator_client.generated.storyboard_types import (
    Narration as StoryboardNarration,
)
from screencast_narrator_client.generated.storyboard_types import (
    Options,
)

from screencast_narrator.merge import (
    _build_voice_assignments,
    _generate_tts_audio,
    _resolve_voice,
    _segment_name,
)
from screencast_narrator.tts import TTSBackend


class _RecordingTTSBackend(TTSBackend):
    def __init__(self) -> None:
        super().__init__(language="en")
        self.calls: list[tuple[str, Path, str | None]] = []

    def resolve_voice(self, voice: str) -> str:
        return voice

    def generate(self, text: str, output_path: Path, voice: str | None = None) -> None:
        self.calls.append((text, output_path, voice))
        output_path.write_bytes(b"RIFF" + b"\x00" * 40)

    def _generate_raw(self, text: str, output_path: Path, voice: str) -> None:
        pass


def _make_storyboard(
    narrations: list[StoryboardNarration],
    language: str = "en",
    voices: dict[str, str] | None = None,
) -> StoryboardModel:
    return StoryboardModel(
        language=language,
        narrations=narrations,
        options=Options(voices=voices) if voices else None,
    )


def test_build_voice_assignments_single_female() -> None:
    tts = _RecordingTTSBackend()
    storyboard = _make_storyboard(
        [StoryboardNarration(narration_id=0, text="Hello", voice="nathaly")],
        voices={"nathaly": "female"},
    )
    assignments = _build_voice_assignments(storyboard, tts)
    assert assignments == {"nathaly": "female-1"}


def test_build_voice_assignments_multiple_same_gender() -> None:
    tts = _RecordingTTSBackend()
    storyboard = _make_storyboard(
        [
            StoryboardNarration(narration_id=0, text="Hello", voice="nathaly"),
            StoryboardNarration(narration_id=1, text="World", voice="sarah"),
        ],
        voices={"nathaly": "female", "sarah": "female"},
    )
    assignments = _build_voice_assignments(storyboard, tts)
    assert assignments == {"nathaly": "female-1", "sarah": "female-2"}


def test_build_voice_assignments_mixed_genders() -> None:
    tts = _RecordingTTSBackend()
    storyboard = _make_storyboard(
        [
            StoryboardNarration(narration_id=0, text="Hello", voice="nathaly"),
            StoryboardNarration(narration_id=1, text="World", voice="james"),
        ],
        voices={"nathaly": "female", "james": "male"},
    )
    assignments = _build_voice_assignments(storyboard, tts)
    assert assignments == {"nathaly": "female-1", "james": "male-1"}


def test_resolve_voice_with_assignments() -> None:
    assignments = {"nathaly": "female-1", "james": "male-1"}
    narration = StoryboardNarration(narration_id=0, text="Hello", voice="nathaly")
    assert _resolve_voice(narration, assignments) == "female-1"


def test_resolve_voice_defaults_to_first_alias() -> None:
    assignments = {"nathaly": "female-1"}
    narration = StoryboardNarration(narration_id=0, text="Hello")
    assert _resolve_voice(narration, assignments) == "female-1"


def test_resolve_voice_returns_none_without_assignments() -> None:
    narration = StoryboardNarration(narration_id=0, text="Hello")
    assert _resolve_voice(narration, {}) is None


def test_generate_tts_passes_resolved_voice(tmp_path: Path) -> None:
    tts = _RecordingTTSBackend()
    storyboard = _make_storyboard(
        [
            StoryboardNarration(narration_id=0, text="Hello", voice="nathaly"),
            StoryboardNarration(narration_id=1, text="World", voice="james"),
        ],
        voices={"nathaly": "female", "james": "male"},
    )
    _generate_tts_audio(storyboard, tmp_path, tts)

    assert len(tts.calls) == 2
    assert tts.calls[0][2] == "female-1"
    assert tts.calls[1][2] == "male-1"


def test_generate_tts_without_voices_passes_none(tmp_path: Path) -> None:
    tts = _RecordingTTSBackend()
    storyboard = _make_storyboard(
        [StoryboardNarration(narration_id=0, text="Hello")],
    )
    _generate_tts_audio(storyboard, tmp_path, tts)

    assert len(tts.calls) == 1
    assert tts.calls[0][2] is None


def test_generate_tts_skips_empty_text(tmp_path: Path) -> None:
    tts = _RecordingTTSBackend()
    storyboard = _make_storyboard([
        StoryboardNarration(narration_id=0, text=""),
        StoryboardNarration(narration_id=1, text="Has text"),
        StoryboardNarration(narration_id=2, text=""),
    ])
    _generate_tts_audio(storyboard, tmp_path, tts)

    assert len(tts.calls) == 1
    assert tts.calls[0][0] == "Has text"


class _RejectingTTSBackend(TTSBackend):
    def __init__(self, allowed_voices: set[str]) -> None:
        super().__init__(language="en")
        self._allowed = allowed_voices

    def resolve_voice(self, voice: str) -> str:
        if voice not in self._allowed:
            raise ValueError(f"Voice '{voice}' not supported")
        return voice

    def generate(self, text: str, output_path: Path, voice: str | None = None) -> None:
        output_path.write_bytes(b"RIFF" + b"\x00" * 40)

    def _generate_raw(self, text: str, output_path: Path, voice: str) -> None:
        pass


def test_validate_voices_fails_fast_on_invalid_voice(tmp_path: Path) -> None:
    tts = _RejectingTTSBackend(allowed_voices={"female-1"})
    storyboard = _make_storyboard(
        [
            StoryboardNarration(narration_id=0, text="Hello", voice="nathaly"),
            StoryboardNarration(narration_id=1, text="World", voice="james"),
        ],
        voices={"nathaly": "female", "james": "male"},
    )
    with pytest.raises(ValueError, match="male-1"):
        _generate_tts_audio(storyboard, tmp_path, tts)
    assert not list(tmp_path.glob("segment_*")), "No audio should be generated before validation fails"


def test_invalid_gender_rejected_by_schema() -> None:
    with pytest.raises(Exception, match=r"female.*male"):
        _make_storyboard(
            [StoryboardNarration(narration_id=0, text="Hello", voice="nathaly")],
            voices={"nathaly": "robot"},
        )


def test_generate_tts_does_not_regenerate_existing(tmp_path: Path) -> None:
    tts = _RecordingTTSBackend()
    storyboard = _make_storyboard(
        [StoryboardNarration(narration_id=0, text="Already exists")],
    )
    (tmp_path / _segment_name(0)).write_bytes(b"existing")
    _generate_tts_audio(storyboard, tmp_path, tts)

    assert len(tts.calls) == 0
