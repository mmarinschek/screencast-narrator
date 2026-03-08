# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

screencast-narrator is a Python library that turns screen recordings into narrated screencasts. It takes a storyboard (narration text + screen actions) and a raw video with embedded sync frames, generates TTS audio, detects sync frames for timing, calculates freeze frames, and merges everything into a final video using FFmpeg.

## Commands

```bash
# Install for development (with TTS support)
pip install -e ".[dev,tts]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_freeze_frames.py -v

# Run a single test
pytest tests/test_freeze_frames.py::test_name -v

# CLI entry point
screencast-narrator /path/to/recording-output/
```

**System dependencies:** ffmpeg (must be on PATH), libzbar (Ubuntu: `libzbar0`, macOS: `brew install zbar`). On macOS, pyzbar needs: `DYLD_LIBRARY_PATH=/opt/homebrew/lib pytest`.

## Architecture

The pipeline in `src/screencast_narrator/` has 7 stages, orchestrated by `merge.py:process()`:

1. **storyboard.py** — Declares narration brackets (text + screen actions) during browser automation. Serializes to `storyboard.json` with camelCase keys. No timestamps — timing is derived from sync frames in the video.

2. **sync_frames.py** — Injects green QR-code overlay frames into the browser at narration boundaries. QR payload: `SYNC|{narration_id}|{START|END}`, displayed for 160ms.

3. **tts.py** — Pluggable `TTSBackend` protocol. Default: KokoroTTS (voice "bf_alice", 24kHz WAV). Caches files under `~/.cache/screencast-narrator-tts/` keyed by SHA256 of "voice:text".

4. **sync_detect.py** — Extracts frames at 25 FPS, detects green frames (R<80, G>180, B<80), decodes QR codes via pyzbar. Returns QR spans, green frame indices, total count. Converts frame positions to milliseconds in the stripped video.

5. **freeze_frames.py** — When narration audio exceeds the action duration, calculates where to insert freeze frames. Also detects dead air gaps (>2s with no narration).

6. **merge.py** — Sync-frame pipeline only: reads storyboard, generates TTS, detects sync frames, strips them, builds extended video with freeze frames, cuts dead air, overlays audio via FFmpeg filter graphs. Writes `timeline.json` with computed timing.

7. **timeline_html.py** — Generates interactive HTML timeline visualization from `timeline.json` showing bracket positions, freeze frames, gap cuts, and audio durations.

**ffmpeg.py** — Thin wrappers around `ffmpeg`/`ffprobe` subprocesses.

## Key Conventions

- Python >=3.11, tested on 3.11/3.12/3.13
- Storyboard JSON uses camelCase keys (narrationId, screenActionId)
- Package uses setuptools via pyproject.toml (no setup.py/requirements.txt)
- Optional dependencies split into `[tts]` and `[dev]` extras
- Client libraries in `clients/` for TypeScript and Java (Python is built-in)
