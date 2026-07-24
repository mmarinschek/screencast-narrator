"""Tests for the Gemini TTS backend and CLI TTS backend selection."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from screencast_narrator.merge import main
from screencast_narrator.tts import SAMPLE_RATE, EdgeTTS, GeminiTTS, KokoroTTS


def test_resolve_voice_maps_logical_names() -> None:
    tts = GeminiTTS(api_key="test-key")
    assert tts.resolve_voice("female-1") == "Leda"
    assert tts.resolve_voice("male-1") == "Charon"


def test_resolve_voice_rejects_unknown_voice() -> None:
    tts = GeminiTTS(api_key="test-key")
    with pytest.raises(ValueError, match="Unknown voice"):
        tts.resolve_voice("robot-1")


def test_write_wave_produces_mono_16bit_wav(tmp_path: Path) -> None:
    pcm = b"\x01\x02" * 240
    out = tmp_path / "out.wav"
    GeminiTTS(api_key="test-key")._write_wave(out, pcm)
    with wave.open(str(out), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == SAMPLE_RATE
        assert wf.readframes(wf.getnframes()) == pcm


def test_retry_on_rate_limit_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr("screencast_narrator.tts.time.sleep", sleeps.append)
    attempts = 0

    def request() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return "ok"

    assert GeminiTTS._retry_on_rate_limit(request) == "ok"
    assert attempts == 3
    assert sleeps == [5.0, 7.5]


def test_retry_on_rate_limit_reraises_other_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "screencast_narrator.tts.time.sleep",
        lambda _: pytest.fail("must not sleep on non-rate-limit errors"),
    )

    def request() -> str:
        raise RuntimeError("invalid api key")

    with pytest.raises(RuntimeError, match="invalid api key"):
        GeminiTTS._retry_on_rate_limit(request)


def test_retry_on_rate_limit_gives_up_after_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr("screencast_narrator.tts.time.sleep", sleeps.append)
    attempts = 0

    def request() -> str:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("429 rate limited")

    with pytest.raises(RuntimeError, match="429"):
        GeminiTTS._retry_on_rate_limit(request)
    assert attempts == 11
    assert len(sleeps) == 10


def _run_cli(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> dict:
    captured: dict = {}

    def fake_process(target_dir, tts_backend_factory=None, offline=False, debug_overlay=None, font_size=None):
        captured.update(
            target_dir=target_dir,
            tts_backend_factory=tts_backend_factory,
            offline=offline,
            debug_overlay=debug_overlay,
            font_size=font_size,
        )

    monkeypatch.setattr("screencast_narrator.merge.process", fake_process)
    monkeypatch.setattr("sys.argv", ["screencast-narrator", *argv, "recording-dir"])
    main()
    return captured


def test_cli_defaults_to_no_backend_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _run_cli(monkeypatch, [])
    assert captured["tts_backend_factory"] is None
    assert captured["offline"] is False
    assert captured["debug_overlay"] is None
    assert captured["font_size"] is None
    assert captured["target_dir"] == Path("recording-dir")


def test_cli_selects_edge_backend_with_language(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _run_cli(monkeypatch, ["--tts-backend", "edge"])
    backend = captured["tts_backend_factory"]("fr")
    assert isinstance(backend, EdgeTTS)
    assert backend._language == "fr"


def test_cli_selects_kokoro_backend_with_language(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _run_cli(monkeypatch, ["--tts-backend", "kokoro"])
    backend = captured["tts_backend_factory"]("en")
    assert isinstance(backend, KokoroTTS)
    assert backend._language == "en"


def test_cli_selects_gemini_backend_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "key-from-env")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    captured = _run_cli(monkeypatch, ["--tts-backend", "gemini"])
    backend = captured["tts_backend_factory"]("de")
    assert isinstance(backend, GeminiTTS)
    assert backend._api_key == "key-from-env"
    assert backend._language == "de"


def test_cli_gemini_falls_back_to_google_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    captured = _run_cli(monkeypatch, ["--tts-backend", "gemini"])
    backend = captured["tts_backend_factory"]("en")
    assert isinstance(backend, GeminiTTS)
    assert backend._api_key == "google-key"


def test_cli_gemini_without_api_key_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="GEMINI_API_KEY"):
        _run_cli(monkeypatch, ["--tts-backend", "gemini"])


def test_cli_rejects_unknown_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit):
        _run_cli(monkeypatch, ["--tts-backend", "espeak"])
