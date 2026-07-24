"""Tests for SRT subtitle generation."""

from __future__ import annotations

from pathlib import Path

from screencast_narrator_client.generated.storyboard_types import Narration as StoryboardNarration

from screencast_narrator.merge import _fmt_srt_time, _text_for_display, _text_for_tts, _write_srt
from screencast_narrator.narration_segment import NarrationSegment


def _sb_narrations(texts: list[str]) -> list[StoryboardNarration]:
    return [StoryboardNarration(narration_id=i, text=t) for i, t in enumerate(texts)]


def test_fmt_srt_time_zero():
    assert _fmt_srt_time(0) == "00:00:00,000"


def test_fmt_srt_time_simple():
    assert _fmt_srt_time(1500) == "00:00:01,500"


def test_fmt_srt_time_minutes_and_hours():
    assert _fmt_srt_time(3661234) == "01:01:01,234"


def test_fmt_srt_time_negative_clamps_to_zero():
    assert _fmt_srt_time(-500) == "00:00:00,000"


def test_write_srt_creates_valid_file(tmp_path: Path):
    narrations = [
        NarrationSegment(0, 2000, "Hello world", 1500),
        NarrationSegment(2000, 5000, "Second narration", 2800),
    ]
    sb_narrations = _sb_narrations(["Hello world", "Second narration"])
    timestamps = [0, 2000]
    srt_file = tmp_path / "test.srt"

    _write_srt(narrations, timestamps, srt_file, sb_narrations, "en")

    content = srt_file.read_text()
    lines = content.strip().split("\n")

    assert lines[0] == "1"
    assert lines[1] == "00:00:00,000 --> 00:00:01,500"
    assert lines[2] == "Hello world"
    assert lines[3] == ""
    assert lines[4] == "2"
    assert lines[5] == "00:00:02,000 --> 00:00:04,800"
    assert lines[6] == "Second narration"


def test_write_srt_with_adjusted_timestamps(tmp_path: Path):
    narrations = [
        NarrationSegment(0, 3000, "First", 2000),
        NarrationSegment(3000, 6000, "Second", 2500),
    ]
    sb_narrations = _sb_narrations(["First", "Second"])
    timestamps = [500, 4000]
    srt_file = tmp_path / "shifted.srt"

    _write_srt(narrations, timestamps, srt_file, sb_narrations, "en")

    content = srt_file.read_text()
    assert "00:00:00,500 --> 00:00:02,500" in content
    assert "00:00:04,000 --> 00:00:06,500" in content


def test_write_srt_single_narration(tmp_path: Path):
    narrations = [NarrationSegment(0, 5000, "Only one", 3000)]
    sb_narrations = _sb_narrations(["Only one"])
    timestamps = [1000]
    srt_file = tmp_path / "single.srt"

    _write_srt(narrations, timestamps, srt_file, sb_narrations, "en")

    content = srt_file.read_text()
    lines = content.strip().split("\n")
    assert lines[0] == "1"
    assert lines[1] == "00:00:01,000 --> 00:00:04,000"
    assert lines[2] == "Only one"


def test_write_srt_with_translation_language(tmp_path: Path):
    narrations = [
        NarrationSegment(0, 2000, "Hello world", 1500),
        NarrationSegment(2000, 5000, "Second narration", 2800),
    ]
    storyboard_narrations = [
        StoryboardNarration(narration_id=0, text="Hello world", translations={"de": "Hallo Welt", "fr": "Bonjour le monde"}),
        StoryboardNarration(narration_id=1, text="Second narration", translations={"de": "Zweite Erzählung"}),
    ]
    timestamps = [0, 2000]

    de_srt = tmp_path / "de.srt"
    _write_srt(narrations, timestamps, de_srt, storyboard_narrations, "de")

    content = de_srt.read_text()
    assert "Hallo Welt" in content
    assert "Zweite Erzählung" in content
    assert "Hello world" not in content


def test_write_srt_translation_falls_back_to_base_text(tmp_path: Path):
    narrations = [
        NarrationSegment(0, 2000, "Hello", 1500),
        NarrationSegment(2000, 5000, "World", 2800),
    ]
    storyboard_narrations = [
        StoryboardNarration(narration_id=0, text="Hello", translations={"fr": "Bonjour"}),
        StoryboardNarration(narration_id=1, text="World", translations={}),
    ]
    timestamps = [0, 2000]

    fr_srt = tmp_path / "fr.srt"
    _write_srt(narrations, timestamps, fr_srt, storyboard_narrations, "fr")

    content = fr_srt.read_text()
    assert "Bonjour" in content
    assert "World" in content


def test_write_srt_primary_uses_translated_text(tmp_path: Path):
    narrations = [
        NarrationSegment(0, 2000, "Hello", 1500),
    ]
    storyboard_narrations = [
        StoryboardNarration(narration_id=0, text="Hello", translations={"de": "Hallo"}),
    ]
    timestamps = [0]

    srt_file = tmp_path / "primary.srt"
    _write_srt(narrations, timestamps, srt_file, storyboard_narrations, "de")

    content = srt_file.read_text()
    assert "Hallo" in content
    assert "Hello" not in content


def test_write_srt_english_fallback_when_no_translation(tmp_path: Path):
    narrations = [
        NarrationSegment(0, 2000, "Hello", 1500),
        NarrationSegment(2000, 5000, "World", 2800),
    ]
    storyboard_narrations = [
        StoryboardNarration(narration_id=0, text="Hello", translations={"de": "Hallo"}),
        StoryboardNarration(narration_id=1, text="World"),
    ]
    timestamps = [0, 2000]

    en_srt = tmp_path / "en.srt"
    _write_srt(narrations, timestamps, en_srt, storyboard_narrations, "en")

    content = en_srt.read_text()
    assert "Hello" in content
    assert "World" in content
    assert "Hallo" not in content


def test_write_srt_de_primary_with_en_secondary(tmp_path: Path):
    narrations = [
        NarrationSegment(0, 2000, "Hello", 1500),
    ]
    storyboard_narrations = [
        StoryboardNarration(narration_id=0, text="Hello", translations={"de": "Hallo"}),
    ]
    timestamps = [0]

    de_srt = tmp_path / "primary.srt"
    _write_srt(narrations, timestamps, de_srt, storyboard_narrations, "de")
    assert "Hallo" in de_srt.read_text()
    assert "Hello" not in de_srt.read_text()

    en_srt = tmp_path / "secondary_en.srt"
    _write_srt(narrations, timestamps, en_srt, storyboard_narrations, "en")
    assert "Hello" in en_srt.read_text()
    assert "Hallo" not in en_srt.read_text()


def test_text_for_tts_replaces_with_pronunciation():
    text = 'Die <pronounced as="Trongsche">Tranche</pronounced> wurde erkannt.'
    assert _text_for_tts(text) == "Die Trongsche wurde erkannt."


def test_text_for_display_strips_pronunciation_tag():
    text = 'Die <pronounced as="Trongsche">Tranche</pronounced> wurde erkannt.'
    assert _text_for_display(text) == "Die Tranche wurde erkannt."


def test_text_for_tts_multiple_tags():
    text = '<pronounced as="Trongsche">Tranche</pronounced> und <pronounced as="Fong">Fonds</pronounced>'
    assert _text_for_tts(text) == "Trongsche und Fong"


def test_text_for_display_multiple_tags():
    text = '<pronounced as="Trongsche">Tranche</pronounced> und <pronounced as="Fong">Fonds</pronounced>'
    assert _text_for_display(text) == "Tranche und Fonds"


def test_text_without_pronunciation_tags_unchanged():
    text = "Normal text without any tags."
    assert _text_for_tts(text) == text
    assert _text_for_display(text) == text


def test_write_srt_strips_pronunciation_for_display(tmp_path: Path):
    narrations = [NarrationSegment(0, 2000, "test", 1500)]
    sb_narrations = [
        StoryboardNarration(
            narration_id=0,
            text='Die <pronounced as="Trongsche">Tranche</pronounced> wurde erkannt.',
        ),
    ]
    srt_file = tmp_path / "test.srt"
    _write_srt(narrations, [0], srt_file, sb_narrations, "en")

    content = srt_file.read_text()
    assert "Tranche" in content
    assert "Trongsche" not in content
    assert "<pronounced" not in content


def test_storyboard_serializes_language_and_translations(tmp_path: Path):
    from screencast_narrator.storyboard import Storyboard

    sb = Storyboard(tmp_path, language="en")
    sb.begin_narration("Hello world", translations={"de": "Hallo Welt"})
    sb.end_narration()

    import json
    data = json.loads((tmp_path / "storyboard.json").read_text())

    assert data["language"] == "en"
    assert data["narrations"][0]["text"] == "Hello world"
    assert data["narrations"][0]["translations"]["de"] == "Hallo Welt"


def test_storyboard_default_language_is_english(tmp_path: Path):
    from screencast_narrator.storyboard import Storyboard

    sb = Storyboard(tmp_path)
    sb.begin_narration("Test")
    sb.end_narration()

    import json
    data = json.loads((tmp_path / "storyboard.json").read_text())
    assert data["language"] == "en"


def test_storyboard_options_serialized(tmp_path: Path):
    from screencast_narrator.storyboard import Storyboard

    sb = Storyboard(tmp_path, debug_overlay=True, font_size=48)
    sb.begin_narration("Test")
    sb.end_narration()

    import json
    data = json.loads((tmp_path / "storyboard.json").read_text())
    assert data["options"]["debugOverlay"] is True
    assert data["options"]["fontSize"] == 48


def test_storyboard_no_options_when_defaults(tmp_path: Path):
    from screencast_narrator.storyboard import Storyboard

    sb = Storyboard(tmp_path)
    sb.begin_narration("Test")
    sb.end_narration()

    import json
    data = json.loads((tmp_path / "storyboard.json").read_text())
    assert "options" not in data


def test_storyboard_narration_without_translations(tmp_path: Path):
    from screencast_narrator.storyboard import Storyboard

    sb = Storyboard(tmp_path, language="de")
    sb.begin_narration("Hallo Welt")
    sb.end_narration()

    import json
    data = json.loads((tmp_path / "storyboard.json").read_text())
    assert data["language"] == "de"
    assert "translations" not in data["narrations"][0]
