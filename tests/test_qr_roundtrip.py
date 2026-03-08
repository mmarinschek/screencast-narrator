"""QR code roundtrip tests: generate with qrcode, decode with pyzbar."""

import base64
import io
import json

from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode

import pytest

from screencast_narrator.shared_config import load_shared_config
from screencast_narrator.sync_frames import (
    MAX_QR_DATA_LENGTH,
    SyncFrameInjector,
    split_into_continuation_frames,
    reassemble_continuation_frames,
)
from screencast_narrator_client.generated.storyboard_types import (
    ScreenAction,
    ScreenActionTiming,
    ScreenActionType,
)

_CONFIG = load_shared_config()
_SM = _CONFIG.sync_markers
_SYNC = SyncFrameInjector(_CONFIG)


def test_qr_code_roundtrip():
    data = _SYNC.format_sync_data(7, _SM.start)
    parsed = json.loads(data)
    assert parsed["t"] == _SM.narration
    assert parsed["id"] == 7
    assert parsed["m"] == _SM.start

    data_url = _SYNC.generate_qr_data_url(data)
    assert data_url.startswith("data:image/png;base64,")

    b64 = data_url[len("data:image/png;base64,"):]
    image_bytes = base64.b64decode(b64)
    img = Image.open(io.BytesIO(image_bytes))
    assert img.width == 400
    assert img.height == 400

    results = pyzbar_decode(img)
    assert len(results) >= 1
    decoded = results[0].data.decode("utf-8")
    assert json.loads(decoded) == parsed


def test_different_narration_ids_produce_different_qr_codes():
    url1 = _SYNC.generate_qr_data_url(_SYNC.format_sync_data(0, _SM.start))
    url2 = _SYNC.generate_qr_data_url(_SYNC.format_sync_data(1, _SM.start))
    assert url1 != url2


def test_format_sync_data_is_valid_json():
    parsed = json.loads(_SYNC.format_sync_data(0, _SM.start))
    assert parsed["t"] == _SM.narration
    assert parsed["id"] == 0
    assert parsed["m"] == _SM.start

    parsed = json.loads(_SYNC.format_sync_data(12, _SM.end))
    assert parsed["id"] == 12
    assert parsed["m"] == _SM.end


def test_format_sync_data_with_text():
    data = _SYNC.format_sync_data(0, _SM.start, "Hello world")
    parsed = json.loads(data)
    assert parsed["tx"] == "Hello world"
    assert parsed["t"] == _SM.narration


def test_format_action_sync_data_is_valid_json():
    parsed = json.loads(_SYNC.format_action_sync_data(0, _SM.start))
    assert parsed["t"] == _SM.action
    assert parsed["id"] == 0
    assert parsed["m"] == _SM.start

    parsed = json.loads(_SYNC.format_action_sync_data(5, _SM.end))
    assert parsed["id"] == 5
    assert parsed["m"] == _SM.end


def test_action_sync_qr_roundtrip():
    data = _SYNC.format_action_sync_data(3, _SM.start)
    expected = json.loads(data)
    data_url = _SYNC.generate_qr_data_url(data)
    b64 = data_url[len("data:image/png;base64,"):]
    image_bytes = base64.b64decode(b64)
    img = Image.open(io.BytesIO(image_bytes))
    results = pyzbar_decode(img)
    assert len(results) >= 1
    decoded = results[0].data.decode("utf-8")
    assert json.loads(decoded) == expected


def test_generate_qr_data_url_rejects_oversized_payload():
    long_text = "x" * (MAX_QR_DATA_LENGTH + 1)
    with pytest.raises(ValueError, match="QR payload too large"):
        _SYNC.generate_qr_data_url(long_text)


def test_format_sync_data_with_translations():
    data = _SYNC.format_sync_data(0, _SM.start, "Hello", {"de": "Hallo", "fr": "Bonjour"})
    parsed = json.loads(data)
    assert parsed["tx"] == "Hello"
    assert parsed["tr"] == {"de": "Hallo", "fr": "Bonjour"}


def test_format_action_sync_data_with_description():
    data = _SYNC.format_action_sync_data(0, _SM.start, description="Click button")
    parsed = json.loads(data)
    assert parsed["desc"] == "Click button"
    assert "tm" not in parsed


def test_format_action_sync_data_with_timing():
    data = _SYNC.format_action_sync_data(0, _SM.start, timing="elastic")
    parsed = json.loads(data)
    assert parsed["tm"] == "elastic"


def test_format_action_sync_data_with_timed_duration():
    data = _SYNC.format_action_sync_data(0, _SM.start, description="Animate", timing="timed", duration_ms=5000)
    parsed = json.loads(data)
    assert parsed["desc"] == "Animate"
    assert parsed["tm"] == "timed"
    assert parsed["dur"] == 5000


def test_continuation_split_roundtrip():
    large_payload = json.dumps({"t": "nar", "id": 0, "m": "start", "tx": "x" * 2500})
    frames = split_into_continuation_frames(large_payload)
    assert len(frames) >= 2
    for frame in frames:
        assert len(frame) <= MAX_QR_DATA_LENGTH

    reassembled = reassemble_continuation_frames(frames)
    assert reassembled == large_payload


def test_continuation_not_needed_for_small_payload():
    small_payload = json.dumps({"t": "nar", "id": 0, "m": "start", "tx": "short"})
    frames = split_into_continuation_frames(small_payload)
    assert len(frames) == 1
    assert frames[0] == small_payload


def test_continuation_qr_roundtrip():
    large_payload = json.dumps({"t": "nar", "id": 0, "m": "start", "tx": "y" * 2500})
    frames = split_into_continuation_frames(large_payload)

    for frame in frames:
        data_url = _SYNC.generate_qr_data_url(frame)
        b64 = data_url[len("data:image/png;base64,"):]
        img = Image.open(io.BytesIO(base64.b64decode(b64)))
        results = pyzbar_decode(img)
        assert len(results) >= 1
        decoded = results[0].data.decode("utf-8")
        assert decoded == frame


def test_client_payload_roundtrip_through_detection():
    """Full roundtrip: storyboard produces payloads -> sync_detect parses them -> merge reconstructs storyboard."""
    from screencast_narrator.sync_detect import SyncFrameSpan, SyncDetectionResult, _parse_qr_payload
    from screencast_narrator.merge import _build_storyboard_from_sync

    payloads = [
        _SYNC.format_init_data("de", debug_overlay=True, font_size=32),
        _SYNC.format_sync_data(0, _SM.start, "First narration", {"en": "First narration EN"}),
        _SYNC.format_action_sync_data(0, _SM.start, description="Click button"),
        _SYNC.format_action_sync_data(0, _SM.end),
        _SYNC.format_highlight_sync_data(1, _SM.start),
        _SYNC.format_highlight_sync_data(1, _SM.end),
        _SYNC.format_sync_data(0, _SM.end),
        _SYNC.format_sync_data(1, _SM.start, "Second narration"),
        _SYNC.format_action_sync_data(2, _SM.start, description="Animate", timing="timed", duration_ms=5000),
        _SYNC.format_action_sync_data(2, _SM.end),
        _SYNC.format_sync_data(1, _SM.end),
    ]

    narration_texts: dict[int, str] = {}
    narration_translations: dict[int, dict[str, str]] = {}
    screen_actions: dict[int, ScreenAction] = {}
    init_data: dict = {}
    spans: list[SyncFrameSpan] = []
    frame_idx = 0

    for payload_str in payloads:
        parsed = _parse_qr_payload(payload_str)
        sync_type = parsed["t"]
        assert sync_type in _SM.all_types, f"Unknown sync type: {sync_type}"

        if sync_type == _SM.init:
            init_data = parsed
            frame_idx += 4
            continue

        entity_id = parsed["id"]
        marker_type = parsed["m"]
        assert marker_type in (_SM.start, _SM.end), f"Unknown marker: {marker_type}"

        if sync_type == _SM.narration and marker_type == _SM.start:
            assert "tx" in parsed, f"Narration START payload missing 'tx' field"
            narration_texts[entity_id] = parsed["tx"]
            if "tr" in parsed:
                narration_translations[entity_id] = parsed["tr"]

        if sync_type == _SM.action and marker_type == _SM.start:
            st_raw = parsed.get("st")
            tm_raw = parsed.get("tm")
            screen_actions[entity_id] = ScreenAction(
                type=ScreenActionType(st_raw) if st_raw else ScreenActionType.navigate,
                screen_action_id=entity_id,
                description=parsed.get("desc"),
                timing=ScreenActionTiming(tm_raw) if tm_raw else None,
                duration_ms=parsed.get("dur"),
            )

        if sync_type == _SM.highlight and marker_type == _SM.start:
            screen_actions[entity_id] = ScreenAction(
                type=ScreenActionType.highlight,
                screen_action_id=entity_id,
            )

        spans.append(SyncFrameSpan(sync_type, entity_id, marker_type, frame_idx, frame_idx + 3))
        frame_idx += 6

    sync_result = SyncDetectionResult(
        qr_spans=spans,
        green_frame_indices=set(range(0, frame_idx)),
        total_frames=frame_idx + 100,
        narration_texts=narration_texts,
        narration_translations=narration_translations,
        screen_actions=screen_actions,
        init_data=init_data,
    )

    assert init_data["language"] == "de"
    assert init_data["debugOverlay"] is True
    assert init_data["fontSize"] == 32

    assert len(narration_texts) == 2
    assert narration_texts[0] == "First narration"
    assert narration_texts[1] == "Second narration"
    assert narration_translations[0] == {"en": "First narration EN"}

    assert screen_actions[0].description == "Click button"
    assert screen_actions[1].type == ScreenActionType.highlight
    assert screen_actions[2].description == "Animate"
    assert screen_actions[2].timing == ScreenActionTiming.timed
    assert screen_actions[2].duration_ms == 5000

    storyboard = _build_storyboard_from_sync(sync_result)
    assert storyboard.language == "de"
    assert len(storyboard.narrations) == 2

    n0 = storyboard.narrations[0]
    assert n0.narration_id == 0
    assert n0.text == "First narration"
    assert n0.translations == {"en": "First narration EN"}
    actions0 = n0.screen_actions
    assert len(actions0) == 2
    assert actions0[0].screen_action_id == 0
    assert actions0[0].description == "Click button"
    assert actions0[1].type == ScreenActionType.highlight
    assert actions0[1].screen_action_id == 1

    n1 = storyboard.narrations[1]
    assert n1.narration_id == 1
    assert n1.text == "Second narration"
    assert n1.translations is None
    actions1 = n1.screen_actions
    assert len(actions1) == 1
    assert actions1[0].description == "Animate"
    assert actions1[0].timing == ScreenActionTiming.timed
    assert actions1[0].duration_ms == 5000
    assert actions1[0].screen_action_id == 2
