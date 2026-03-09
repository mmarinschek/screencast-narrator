import json

import pytest

from screencast_narrator_client.shared_config import load_shared_config
from screencast_narrator_client.sync_frames import SyncFrameInjector, split_into_continuation_frames


@pytest.fixture()
def config():
    return load_shared_config()


@pytest.fixture()
def sync(config):
    return SyncFrameInjector(config)


class TestSyncFramePayloads:
    def test_sync_frame_with_voice_includes_vc_field(self, sync, config):
        payload = sync.format_sync_data(0, config.sync_markers.start, "Hello", voice="douglas")
        parsed = json.loads(payload)

        assert parsed["tx"] == "Hello"
        assert parsed["vc"] == "douglas"

    def test_sync_frame_without_voice_omits_vc_field(self, sync, config):
        payload = sync.format_sync_data(0, config.sync_markers.start, "Hello")
        parsed = json.loads(payload)

        assert parsed["tx"] == "Hello"
        assert "vc" not in parsed

    def test_init_frame_with_voices_includes_voices_field(self, sync):
        voices = {"douglas": {"en": "am_adam"}, "natalie": {"en": "bf_alice"}}
        payload = sync.format_init_data("en", voices=voices)
        parsed = json.loads(payload)

        assert parsed["voices"]["douglas"]["en"] == "am_adam"
        assert parsed["voices"]["natalie"]["en"] == "bf_alice"

    def test_init_frame_without_voices_omits_voices_field(self, sync):
        payload = sync.format_init_data("en")
        parsed = json.loads(payload)

        assert "voices" not in parsed

    def test_sync_frame_with_translations_and_voice_includes_all(self, sync, config):
        payload = sync.format_sync_data(
            0, config.sync_markers.start, "Hello",
            translations={"de": "Hallo"}, voice="harmony",
        )
        parsed = json.loads(payload)

        assert parsed["tx"] == "Hello"
        assert parsed["tr"]["de"] == "Hallo"
        assert parsed["vc"] == "harmony"

    def test_split_small_payload_returns_single_frame(self, sync, config):
        payload = sync.format_sync_data(0, config.sync_markers.start, "short", voice="douglas")
        frames = split_into_continuation_frames(payload)

        assert len(frames) == 1
        assert frames[0] == payload
