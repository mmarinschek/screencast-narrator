# screencast-narrator

Turn raw screen recordings + narration text into polished narrated screencasts.

**screencast-narrator** is a Python library and CLI that takes a browser screen recording together with a narration timeline and produces a final video with:

- Text-to-speech narration synced to on-screen actions
- QR-code-based frame-accurate synchronization
- Automatic freeze-frame insertion when narration overflows action duration
- Dead-air gap detection and cutting
- Interactive HTML timeline visualization

## Installation

```bash
pip install screencast-narrator
```

For TTS support (Kokoro):
```bash
pip install screencast-narrator[tts]
```

System dependencies:
```bash
# macOS
brew install ffmpeg zbar

# Ubuntu/Debian
apt-get install ffmpeg libzbar0

# Windows
winget install GyanDev.FFmpeg
# The pyzbar Python package ships its own libzbar DLL but needs the Visual C++ 2013 runtime:
winget install Microsoft.VCRedist.2013.x64
```

## Quick Start

### As a library with Playwright

```python
from pathlib import Path
from playwright.sync_api import sync_playwright
from screencast_narrator.storyboard import Storyboard
from screencast_narrator.sync_frames import inject_sync_frame
from screencast_narrator.merge import process

output_dir = Path("my-screencast")
storyboard = Storyboard(output_dir)

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(
        record_video_dir=str(output_dir / "videos"),
        record_video_size={"width": 1280, "height": 720},
    )
    page = context.new_page()

    # Narration bracket with sync frames
    nid = storyboard.begin_narration("We open the example website.")
    inject_sync_frame(page, nid, "START")
    storyboard.add_screen_action("Navigate to example.com")
    page.goto("https://example.com")
    inject_sync_frame(page, nid, "END")
    storyboard.end_narration()

    context.close()
    browser.close()

# Produce the final narrated video
process(output_dir)
```

### As a CLI

```bash
screencast-narrator /path/to/recording-output/
```

The directory must contain:
- A `storyboard.json` file (produced by `Storyboard` or hand-written)
- A video file (`.webm`) in a `videos/` subdirectory with sync frames embedded

## API

The screencast-narrator API is JSON-based and language-agnostic. Any browser automation framework that can record video and execute JavaScript can produce the inputs.

See **[docs/api.md](docs/api.md)** for:
- Timeline JSON schema
- Sync frame protocol specification
- Sample code in **Python**, **Java**, and **TypeScript**
- Pipeline processing details

## Architecture

The pipeline has these stages:

1. **Storyboard** (`storyboard.py`) — Declares narration text and screen actions. No timestamps — timing comes from sync frames.

2. **Sync frame injection** (`sync_frames.py`) — Inject green QR-code overlay frames into the browser at narration bracket boundaries for frame-accurate sync.

3. **TTS generation** (`tts.py`) — Convert narration text to speech audio files. Pluggable backend; ships with Kokoro TTS.

4. **Sync detection** (`sync_detect.py`) — Extract frames from the recorded video, detect green sync frames, decode QR codes to map video frames to narration events.

5. **Freeze frame calculation** (`freeze_frames.py`) — When narration audio is longer than the on-screen action, calculate where to insert freeze frames so audio and video stay in sync.

6. **Video merge** (`merge.py`) — Orchestrate FFmpeg to build the final video: strip sync frames, insert freeze frames, overlay audio, cut dead air gaps.

7. **Timeline visualization** (`timeline_html.py`) — Generate an interactive HTML timeline showing bracket positions, freeze frames, gap cuts, and audio durations.

## Custom TTS Backend

Implement the `TTSBackend` protocol:

```python
from screencast_narrator.tts import TTSBackend
from pathlib import Path

class MyTTS(TTSBackend):
    def generate(self, text: str, output_path: Path) -> None:
        # Generate audio file at output_path
        ...

# Use it
from screencast_narrator.merge import process
process(target_dir, tts_backend=MyTTS())
```

## Development

```bash
git clone https://github.com/mmarinschek/screencast-narrator.git
cd screencast-narrator
pip install -e ".[dev,tts]"

# Run tests
pytest tests/ -v

# On macOS, if pyzbar can't find libzbar:
DYLD_LIBRARY_PATH=/opt/homebrew/lib pytest tests/ -v
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
