"""Tests that JSON schemas, enums, and config.json are all in sync."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from screencast_narrator.shared_config import MarkerPosition, SyncType, load_shared_config
from screencast_narrator.sync_frames import SyncFrameInjector

_CONFIG = load_shared_config()
_SM = _CONFIG.sync_markers
_SYNC = SyncFrameInjector(_CONFIG)
_SHARED_DIR = Path(__file__).parent.parent / "api" / "common"


def _load_schema(name: str) -> dict:
    return json.loads((_SHARED_DIR / name).read_text(encoding="utf-8"))


def test_sync_type_enum_matches_config():
    assert SyncType.init == _SM.init
    assert SyncType.nar == _SM.narration
    assert SyncType.act == _SM.action
    assert SyncType.hlt == _SM.highlight


def test_marker_position_enum_matches_config():
    assert MarkerPosition.start == _SM.start
    assert MarkerPosition.end == _SM.end


def test_sync_type_enum_matches_qr_schema():
    schema = _load_schema("qr-payload-schema.json")
    schema_types = set(schema["definitions"]["syncType"]["enum"])
    enum_values = {e.value for e in SyncType}
    assert schema_types == enum_values


def test_marker_position_enum_matches_qr_schema():
    schema = _load_schema("qr-payload-schema.json")
    schema_markers = set(schema["definitions"]["markerPosition"]["enum"])
    enum_values = {e.value for e in MarkerPosition}
    assert schema_markers == enum_values


def test_qr_payload_init_validates():
    schema = _load_schema("qr-payload-schema.json")
    payload = json.loads(_SYNC.format_init_data("en", debug_overlay=True, font_size=32))
    jsonschema.validate(payload, schema)


def test_qr_payload_narration_start_validates():
    schema = _load_schema("qr-payload-schema.json")
    payload = json.loads(_SYNC.format_sync_data(0, _SM.start, "Hello", {"de": "Hallo"}))
    jsonschema.validate(payload, schema)


def test_qr_payload_narration_end_validates():
    schema = _load_schema("qr-payload-schema.json")
    payload = json.loads(_SYNC.format_sync_data(0, _SM.end))
    jsonschema.validate(payload, schema)


def test_qr_payload_action_start_validates():
    schema = _load_schema("qr-payload-schema.json")
    payload = json.loads(_SYNC.format_action_sync_data(0, _SM.start, description="Click", timing="timed", duration_ms=3000))
    jsonschema.validate(payload, schema)


def test_qr_payload_action_end_validates():
    schema = _load_schema("qr-payload-schema.json")
    payload = json.loads(_SYNC.format_action_sync_data(0, _SM.end))
    jsonschema.validate(payload, schema)


def test_qr_payload_highlight_validates():
    schema = _load_schema("qr-payload-schema.json")
    for marker in (_SM.start, _SM.end):
        payload = json.loads(_SYNC.format_highlight_sync_data(0, marker))
        jsonschema.validate(payload, schema)


def test_qr_payload_rejects_unknown_type():
    schema = _load_schema("qr-payload-schema.json")
    bad = {"t": "UNKNOWN", "id": 0, "m": "start"}
    with __import__("pytest").raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_qr_payload_rejects_unknown_marker():
    schema = _load_schema("qr-payload-schema.json")
    bad = {"t": "nar", "id": 0, "m": "START"}
    with __import__("pytest").raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_storyboard_schema_validates(tmp_path: Path):
    from screencast_narrator.storyboard import ScreenActionTiming, Storyboard

    sb = Storyboard(tmp_path)
    sb.begin_narration("Hello world", translations={"de": "Hallo Welt"})
    sb.begin_screen_action(description="Click button")
    sb.end_screen_action()
    sb.begin_screen_action(description="Animate", timing=ScreenActionTiming.timed, duration_ms=5000)
    sb.end_screen_action()
    sb.end_narration()

    data = json.loads((tmp_path / "storyboard.json").read_text(encoding="utf-8"))
    schema = _load_schema("storyboard-schema.json")
    jsonschema.validate(data, schema)


def test_storyboard_schema_rejects_extra_fields():
    schema = _load_schema("storyboard-schema.json")
    bad = {"language": "en", "narrations": [], "unknownField": True}
    with __import__("pytest").raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)
