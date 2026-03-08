"""Tests for Storyboard: narration bracket and screen action recording."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from screencast_narrator.storyboard import HighlightStyle, ScreenActionTiming, ScreenActionType, Storyboard
from screencast_narrator_client.storyboard import _merge_highlight_styles


def test_begin_end_narration_creates_entry(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    nid = sb.begin_narration("Hello world")
    sb.end_narration()

    assert nid == 0
    assert len(sb.narrations) == 1
    assert sb.narrations[0].narration_id == 0
    assert sb.narrations[0].text == "Hello world"
    assert sb.narrations[0].screen_actions is None


def test_narration_ids_auto_increment(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    n0 = sb.begin_narration("First")
    sb.end_narration()
    n1 = sb.begin_narration("Second")
    sb.end_narration()
    n2 = sb.begin_narration("Third")
    sb.end_narration()

    assert (n0, n1, n2) == (0, 1, 2)


def test_screen_action_within_narration(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Do something")
    said = sb.begin_screen_action(description="Click the button")
    sb.end_screen_action()
    sb.end_narration()

    assert said == 0
    actions = sb.narrations[0].screen_actions
    assert len(actions) == 1
    assert actions[0].description == "Click the button"
    assert actions[0].type == ScreenActionType.navigate


def test_screen_action_without_description(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Do something")
    said = sb.begin_screen_action()
    sb.end_screen_action()
    sb.end_narration()

    assert said == 0
    actions = sb.narrations[0].screen_actions
    assert len(actions) == 1
    assert actions[0].description is None


def test_screen_action_ids_auto_increment_across_narrations(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("First")
    s0 = sb.begin_screen_action(description="Action A")
    sb.end_screen_action()
    s1 = sb.begin_screen_action(description="Action B")
    sb.end_screen_action()
    sb.end_narration()
    sb.begin_narration("Second")
    s2 = sb.begin_screen_action(description="Action C")
    sb.end_screen_action()
    sb.end_narration()

    assert (s0, s1, s2) == (0, 1, 2)


def test_multiple_screen_actions_in_narration(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Multiple actions")
    sb.begin_screen_action(description="Click")
    sb.end_screen_action()
    sb.begin_screen_action(type=ScreenActionType.input)
    sb.end_screen_action()
    sb.begin_screen_action()
    sb.end_screen_action()
    sb.end_narration()

    actions = sb.narrations[0].screen_actions
    assert len(actions) == 3
    assert [a.description for a in actions] == ["Click", None, None]
    assert actions[1].type == ScreenActionType.input


def test_screen_action_types(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("All types")
    sb.begin_screen_action(type=ScreenActionType.navigate)
    sb.end_screen_action()
    sb.begin_screen_action(type=ScreenActionType.input)
    sb.end_screen_action()
    sb.begin_screen_action(type=ScreenActionType.scroll)
    sb.end_screen_action()
    sb.begin_screen_action(type=ScreenActionType.wait)
    sb.end_screen_action()
    sb.begin_screen_action(type=ScreenActionType.animate, timing=ScreenActionTiming.timed, duration_ms=5000)
    sb.end_screen_action()
    sb.end_narration()

    actions = sb.narrations[0].screen_actions
    assert [a.type for a in actions] == [
        ScreenActionType.navigate,
        ScreenActionType.input,
        ScreenActionType.scroll,
        ScreenActionType.wait,
        ScreenActionType.animate,
    ]


def test_error_nested_narration_brackets(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("First")
    with pytest.raises(RuntimeError, match="another is still open"):
        sb.begin_narration("Nested")


def test_error_screen_action_outside_bracket(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    with pytest.raises(RuntimeError, match="outside of a narration bracket"):
        sb.begin_screen_action(description="Orphan action")


def test_error_end_narration_without_begin(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    with pytest.raises(RuntimeError, match="no narration bracket is open"):
        sb.end_narration()


def test_error_nested_screen_actions(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Test")
    sb.begin_screen_action(description="First action")
    with pytest.raises(RuntimeError, match="another is still open"):
        sb.begin_screen_action(description="Nested action")


def test_error_end_screen_action_without_begin(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Test")
    with pytest.raises(RuntimeError, match="no screen action is open"):
        sb.end_screen_action()


def test_error_end_narration_with_open_screen_action(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Test")
    sb.begin_screen_action(description="Still open")
    with pytest.raises(RuntimeError, match="screen action is still open"):
        sb.end_narration()


def test_json_serialization(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Navigate to page")
    sb.begin_screen_action(description="Open browser")
    sb.end_screen_action()
    sb.begin_screen_action()
    sb.end_screen_action()
    sb.end_narration()

    data = json.loads((tmp_path / "storyboard.json").read_text(encoding="utf-8"))
    assert "narrations" in data
    assert len(data["narrations"]) == 1

    n = data["narrations"][0]
    assert n["narrationId"] == 0
    assert n["text"] == "Navigate to page"
    assert len(n["screenActions"]) == 2
    assert n["screenActions"][0] == {"type": "navigate", "screenActionId": 0, "description": "Open browser"}
    assert n["screenActions"][1] == {"type": "navigate", "screenActionId": 1}


def test_json_no_screen_actions_omits_key(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Just narration")
    sb.end_narration()

    data = json.loads((tmp_path / "storyboard.json").read_text(encoding="utf-8"))
    assert "screenActions" not in data["narrations"][0]


def test_json_incremental_flush(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("First")
    sb.end_narration()

    data1 = json.loads((tmp_path / "storyboard.json").read_text(encoding="utf-8"))
    assert len(data1["narrations"]) == 1

    sb.begin_narration("Second")
    sb.end_narration()

    data2 = json.loads((tmp_path / "storyboard.json").read_text(encoding="utf-8"))
    assert len(data2["narrations"]) == 2


def test_output_dir_created_if_missing(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "c"
    sb = Storyboard(nested)
    sb.begin_narration("test")
    sb.end_narration()
    assert (nested / "storyboard.json").exists()


def test_screen_action_default_timing_is_casted(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Do something")
    sb.begin_screen_action(description="Click")
    sb.end_screen_action()
    sb.end_narration()

    action = sb.narrations[0].screen_actions[0]
    assert action.timing is None


def test_screen_action_elastic_timing(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Do something")
    sb.begin_screen_action(description="Idle moment", timing=ScreenActionTiming.elastic)
    sb.end_screen_action()
    sb.end_narration()

    action = sb.narrations[0].screen_actions[0]
    assert action.timing == ScreenActionTiming.elastic
    assert action.duration_ms is None


def test_screen_action_timed(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Do something")
    sb.begin_screen_action(description="Show animation", timing=ScreenActionTiming.timed, duration_ms=3000)
    sb.end_screen_action()
    sb.end_narration()

    action = sb.narrations[0].screen_actions[0]
    assert action.timing == ScreenActionTiming.timed
    assert action.duration_ms == 3000


def test_timed_without_duration_raises(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Do something")
    with pytest.raises(ValueError, match="duration_ms is required"):
        sb.begin_screen_action(description="Bad", timing=ScreenActionTiming.timed)


def test_screen_action_timing_json_serialization(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Mixed actions")
    sb.begin_screen_action(description="Navigate", timing=ScreenActionTiming.casted)
    sb.end_screen_action()
    sb.begin_screen_action(description="Pause", timing=ScreenActionTiming.elastic)
    sb.end_screen_action()
    sb.begin_screen_action(description="Animation", timing=ScreenActionTiming.timed, duration_ms=5000)
    sb.end_screen_action()
    sb.end_narration()

    data = json.loads((tmp_path / "storyboard.json").read_text(encoding="utf-8"))
    actions = data["narrations"][0]["screenActions"]

    assert actions[0] == {"type": "navigate", "screenActionId": 0, "description": "Navigate"}
    assert actions[1] == {"type": "navigate", "screenActionId": 1, "description": "Pause", "timing": "elastic"}
    assert actions[2] == {"type": "navigate", "screenActionId": 2, "description": "Animation", "timing": "timed", "durationMs": 5000}


def test_screen_action_type_json_serialization(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("Typed actions")
    sb.begin_screen_action(type=ScreenActionType.navigate)
    sb.end_screen_action()
    sb.begin_screen_action(type=ScreenActionType.input)
    sb.end_screen_action()
    sb.begin_screen_action(type=ScreenActionType.scroll)
    sb.end_screen_action()
    sb.end_narration()

    data = json.loads((tmp_path / "storyboard.json").read_text(encoding="utf-8"))
    actions = data["narrations"][0]["screenActions"]

    assert actions[0]["type"] == "navigate"
    assert actions[1]["type"] == "input"
    assert actions[2]["type"] == "scroll"


def test_silent_narration(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    nid = sb.begin_narration()
    sb.begin_screen_action(type=ScreenActionType.title, description="Welcome")
    sb.end_screen_action()
    sb.end_narration()

    assert nid == 0
    assert sb.narrations[0].text is None
    actions = sb.narrations[0].screen_actions
    assert len(actions) == 1
    assert actions[0].type == ScreenActionType.title


def test_silent_narration_json_omits_text(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration()
    sb.begin_screen_action(type=ScreenActionType.title)
    sb.end_screen_action()
    sb.end_narration()

    import json
    data = json.loads((tmp_path / "storyboard.json").read_text(encoding="utf-8"))
    assert "text" not in data["narrations"][0]
    assert data["narrations"][0]["screenActions"][0]["type"] == "title"


def test_silent_narration_followed_by_regular(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration()
    sb.end_narration()
    sb.begin_narration("Hello")
    sb.end_narration()

    assert sb.narrations[0].text is None
    assert sb.narrations[1].text == "Hello"


def test_highlight_without_page_raises(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    with pytest.raises(RuntimeError, match="no page was provided"):
        sb.highlight("some_locator")


def test_narrations_property_returns_copy(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.begin_narration("First")
    sb.end_narration()

    narrations = sb.narrations
    sb.begin_narration("Second")
    sb.end_narration()

    assert len(narrations) == 1
    assert len(sb.narrations) == 2


def test_highlight_style_defaults() -> None:
    style = HighlightStyle()
    assert style.color is None
    assert style.animation_speed_ms is None
    assert style.draw_duration_ms is None
    assert style.opacity is None
    assert style.padding is None


def test_highlight_style_custom_values() -> None:
    style = HighlightStyle(color="#ff0000", animation_speed_ms=300, draw_duration_ms=1500)
    assert style.color == "#ff0000"
    assert style.animation_speed_ms == 300
    assert style.draw_duration_ms == 1500


def test_highlight_style_merge() -> None:
    base = HighlightStyle(color="#ff0000", animation_speed_ms=300)
    override = HighlightStyle(color="#0000ff")
    merged = _merge_highlight_styles(base, override)
    assert merged.color == "#0000ff"
    assert merged.animation_speed_ms == 300


def test_highlight_style_merge_none_does_not_override() -> None:
    base = HighlightStyle(color="#ff0000", opacity=0.8)
    override = HighlightStyle(animation_speed_ms=200)
    merged = _merge_highlight_styles(base, override)
    assert merged.color == "#ff0000"
    assert merged.opacity == 0.8
    assert merged.animation_speed_ms == 200


def test_storyboard_with_highlight_style(tmp_path: Path) -> None:
    style = HighlightStyle(color="#ff0000")
    sb = Storyboard(tmp_path, highlight_style=style)
    assert sb.highlight_style.color == "#ff0000"


def test_storyboard_with_highlight_style_override(tmp_path: Path) -> None:
    base_style = HighlightStyle(color="#ff0000", animation_speed_ms=600)
    sb = Storyboard(tmp_path, highlight_style=base_style)

    result = sb.with_highlight_style(HighlightStyle(color="#0000ff"))

    assert result is sb
    assert sb.highlight_style.color == "#0000ff"
    assert sb.highlight_style.animation_speed_ms == 600


def test_storyboard_with_highlight_style_chaining(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path)
    sb.with_highlight_style(HighlightStyle(color="#ff0000")).with_highlight_style(HighlightStyle(opacity=0.5))

    assert sb.highlight_style.color == "#ff0000"
    assert sb.highlight_style.opacity == 0.5


def test_storyboard_with_highlight_style_preserves_unset(tmp_path: Path) -> None:
    sb = Storyboard(tmp_path, highlight_style=HighlightStyle(color="#ff0000", padding=20))
    sb.with_highlight_style(HighlightStyle(color="#00ff00"))

    assert sb.highlight_style.color == "#00ff00"
    assert sb.highlight_style.padding == 20
