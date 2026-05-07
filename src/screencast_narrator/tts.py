"""TTS interface with Kokoro and Edge TTS implementations."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from shutil import copy2

log = logging.getLogger(__name__)

SAMPLE_RATE = 24000

MAX_VOICES_PER_GENDER = 4


class TTSBackend(ABC):
    def __init__(self, language: str = "en", cache_dir: Path | None = None) -> None:
        self._language = language
        self._cache_dir = cache_dir or Path.home() / ".cache" / "screencast-narrator-tts"

    @abstractmethod
    def resolve_voice(self, voice: str) -> str:
        """Resolve a logical voice name (e.g. 'female-1') to a backend-specific voice ID.

        Raises ValueError if the voice is not available for the current language.
        """

    @abstractmethod
    def _generate_raw(self, text: str, output_path: Path, voice: str) -> None: ...

    def generate(self, text: str, output_path: Path, voice: str | None = None) -> None:
        concrete_voice = self.resolve_voice(voice or "female-1")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_key = self._cache_key(text, concrete_voice)
        cached = self._cache_dir / (cache_key + ".wav")

        if cached.exists():
            log.debug("TTS cache hit: %s", cached.name)
            copy2(cached, output_path)
            return

        log.info("Generating TTS: voice=%s (%s), text=%.60s...", voice, concrete_voice, text)
        self._generate_raw(text, output_path, concrete_voice)
        copy2(output_path, cached)

    def _cache_key(self, text: str, concrete_voice: str) -> str:
        data = f"{self.__class__.__name__}:{concrete_voice}:{text}".encode()
        digest = hashlib.sha256(data).hexdigest()[:16]
        return f"{concrete_voice}_{digest}"


class KokoroTTS(TTSBackend):
    VOICE_MAP: dict[str, dict[str, str]] = {
        "female-1": {"en": "bf_alice"},
        "female-2": {"en": "bf_emma"},
        "female-3": {"en": "bf_isabella"},
        "female-4": {"en": "bf_lily"},
        "male-1": {"en": "bm_daniel"},
        "male-2": {"en": "bm_george"},
        "male-3": {"en": "bm_fable"},
        "male-4": {"en": "bm_lewis"},
    }

    def resolve_voice(self, voice: str) -> str:
        mapping = self.VOICE_MAP.get(voice)
        if mapping is None:
            raise ValueError(
                f"Unknown voice '{voice}'. Use female-1..{MAX_VOICES_PER_GENDER} or male-1..{MAX_VOICES_PER_GENDER}"
            )
        concrete = mapping.get(self._language)
        if concrete is None:
            raise ValueError(
                f"Voice '{voice}' not available for language '{self._language}'. "
                f"Kokoro only supports: {sorted({lang for m in self.VOICE_MAP.values() for lang in m})}"
            )
        return concrete

    def _generate_raw(self, text: str, output_path: Path, voice: str) -> None:
        import kokoro
        import numpy as np
        import soundfile as sf

        pipeline = kokoro.KPipeline(lang_code="b")
        all_audio = []
        for _gs, _ps, audio in pipeline(text, voice=voice, speed=1.0):
            all_audio.append(audio)
        combined = np.concatenate(all_audio)
        sf.write(str(output_path), combined, SAMPLE_RATE)


class EdgeTTS(TTSBackend):
    VOICE_MAP: dict[str, dict[str, str]] = {
        "female-1": {
            "en": "en-US-AriaNeural",
            "de": "de-AT-IngridNeural",
            "fr": "fr-FR-DeniseNeural",
            "es": "es-ES-ElviraNeural",
            "it": "it-IT-IsabellaNeural",
        },
        "female-2": {
            "en": "en-US-EmmaNeural",
            "de": "de-DE-KatjaNeural",
            "fr": "fr-FR-EloiseNeural",
            "es": "es-ES-XimenaNeural",
            "it": "it-IT-ElsaNeural",
        },
        "female-3": {
            "en": "en-US-JennyNeural",
            "de": "de-DE-AmalaNeural",
            "fr": "fr-FR-VivienneMultilingualNeural",
        },
        "female-4": {
            "en": "en-US-MichelleNeural",
            "de": "de-DE-SeraphinaMultilingualNeural",
        },
        "male-1": {
            "en": "en-US-AndrewNeural",
            "de": "de-AT-JonasNeural",
            "fr": "fr-FR-HenriNeural",
            "es": "es-ES-AlvaroNeural",
            "it": "it-IT-DiegoNeural",
        },
        "male-2": {
            "en": "en-US-BrianNeural",
            "de": "de-DE-ConradNeural",
            "fr": "fr-FR-RemyMultilingualNeural",
            "es": "es-ES-AlvaroNeural",
            "it": "it-IT-GiuseppeMultilingualNeural",
        },
        "male-3": {
            "en": "en-US-ChristopherNeural",
            "de": "de-DE-KillianNeural",
        },
        "male-4": {
            "en": "en-US-EricNeural",
            "de": "de-DE-FlorianMultilingualNeural",
        },
    }

    def resolve_voice(self, voice: str) -> str:
        mapping = self.VOICE_MAP.get(voice)
        if mapping is None:
            raise ValueError(
                f"Unknown voice '{voice}'. Use female-1..{MAX_VOICES_PER_GENDER} or male-1..{MAX_VOICES_PER_GENDER}"
            )
        concrete = mapping.get(self._language)
        if concrete is None:
            raise ValueError(
                f"Voice '{voice}' not available for language '{self._language}'. "
                f"Available languages: {sorted(mapping.keys())}"
            )
        return concrete

    def _generate_raw(self, text: str, output_path: Path, voice: str) -> None:
        import edge_tts

        mp3_path = output_path.with_suffix(".mp3")
        communicate = edge_tts.Communicate(text, voice)
        asyncio.run(communicate.save(str(mp3_path)))
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3_path),
             "-ar", str(SAMPLE_RATE), "-ac", "1", str(output_path)],
            check=True,
        )
        mp3_path.unlink()

class GeminiTTS(TTSBackend):

    def __init__(self, api_key: str ) -> None:
        self._api_key = api_key
        super().__init__()

    VOICE_MAP: dict[str, str] = {
        "female-1": "Leda",
        "female-2": "Zephyr",
        "female-3": "Callirrhoe",
        "female-4": "Gacrux",
        "male-1": "Charon",
        "male-2": "Algieba",
        "male-3": "Orus",
        "male-4": "Schedar",
    }

    def resolve_voice(self, voice: str) -> str:
        mapping = self.VOICE_MAP.get(voice)
        if mapping is None:
            raise ValueError(
                f"Unknown voice '{voice}'. Use female-1..{MAX_VOICES_PER_GENDER} or male-1..{MAX_VOICES_PER_GENDER}"
            )
        return mapping

    # Set up the wave file to save the output:
    def wave_file(self, filename, pcm, channels=1, rate=SAMPLE_RATE, sample_width=2):
        import wave
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)

    def _generate_raw(self, text: str, output_path: Path, voice: str) -> None:
        from google import genai
        from google.genai import types
        import sys
        import time
        client = genai.Client(api_key=self._api_key)
        config = types.GenerateContentConfig(
           response_modalities=["AUDIO"],
           speech_config=types.SpeechConfig(
              voice_config=types.VoiceConfig(
                 prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice,
                 )
              )
           ),
        )
        delay = 5.0
        max_retries = 10
        for attempt in range(max_retries + 1):
            try:
                response = client.models.generate_content(
                   model="gemini-3.1-flash-tts-preview",
                   contents=text,
                   config=config
                )
                break
            except Exception as e:
                status = getattr(e, "code", None) or getattr(e, "status_code", None)
                is_429 = status == 429 or "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
                if not is_429 or attempt == max_retries:
                    raise
                print(f"Gemini TTS rate-limited (attempt {attempt + 1}/{max_retries}); retrying in {delay:.1f}s", file=sys.stderr)
                time.sleep(delay)
                delay *= 1.5
        data = response.candidates[0].content.parts[0].inline_data.data

        self.wave_file(str(output_path), data)

