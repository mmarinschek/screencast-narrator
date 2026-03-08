# screencast-narrator API

screencast-narrator takes two inputs and produces a narrated screencast video:

1. A **timeline file** (`storyboard.json`) — declares what to narrate
2. A **screen recording** (`.webm`) — the raw video with embedded sync frames

The merge pipeline reads both, generates TTS audio, detects sync frames in the video to establish timing, and produces the final MP4 with narration audio synced to the on-screen actions.

## Timeline JSON Schema

The timeline is a JSON file that describes narration brackets and their associated screen actions. It contains **no timestamps** — all timing is derived from sync frames embedded in the video.

```json
{
  "narrations": [
    {
      "narrationId": 0,
      "text": "We open the example website and look at the main page.",
      "screenActions": [
        { "screenActionId": 0, "description": "Navigate to example.com" },
        { "screenActionId": 1, "description": "Wait for page load" }
      ]
    },
    {
      "narrationId": 1,
      "text": "Now we click the 'More information' link.",
      "screenActions": [
        { "screenActionId": 2 }
      ]
    }
  ]
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `narrations` | array | yes | Ordered list of narration brackets |
| `narrations[].narrationId` | integer | yes | Unique ID, must match sync frame QR payloads in the video |
| `narrations[].text` | string | yes | Narration text, will be converted to speech audio |
| `narrations[].screenActions` | array | no | Screen actions that occur during this narration |
| `narrations[].screenActions[].screenActionId` | integer | yes | Unique ID for the screen action |
| `narrations[].screenActions[].description` | string | no | Human-readable description of the action |

Screen actions are metadata — they don't affect the merge pipeline. They exist for documentation, debugging, and timeline visualization.

## Sync Frame Protocol

Sync frames are full-screen green overlays with a QR code, injected into the browser during recording. They tell the merge pipeline exactly when each narration bracket starts and ends in the video.

### What a sync frame looks like

- Full-screen overlay: `background: #00FF00`, fixed position, covers entire viewport
- Centered QR code: 400x400 pixels, black on white
- Displayed for **160ms**, then removed
- `z-index: 999999` to appear on top of all content

### QR code payload

The QR code encodes a pipe-delimited string:

```
SYNC|{narrationId}|{marker}
```

- `narrationId` — integer matching `narrations[].narrationId` in the timeline
- `marker` — either `START` or `END`

Each narration bracket must have exactly one `START` and one `END` sync frame in the video.

### Injection sequence

For each narration bracket:

```
1. Inject sync frame with marker START  (shows green QR overlay for ~160ms)
2. Perform screen actions               (navigate, click, type, scroll, etc.)
3. Inject sync frame with marker END    (shows green QR overlay for ~160ms)
```

The merge pipeline strips these green frames from the final video — they are never visible to the viewer.

### JavaScript for sync frame injection

This is the JavaScript that must be executed in the browser to show a sync frame. It works in any browser automation framework that can evaluate JavaScript.

**Inject overlay:**

```javascript
(function() {
    const overlay = document.createElement('div');
    overlay.id = '_e2e_sync';
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;'
        + 'background:#00FF00;display:flex;align-items:center;justify-content:center;'
        + 'z-index:999999;';
    const img = document.createElement('img');
    img.src = '<QR_CODE_DATA_URL>';
    img.style.cssText = 'width:400px;height:400px;image-rendering:pixelated;';
    overlay.appendChild(img);
    document.body.appendChild(overlay);
})()
```

**Remove overlay (after ~160ms):**

```javascript
document.getElementById('_e2e_sync')?.remove()
```

The `<QR_CODE_DATA_URL>` is a base64-encoded PNG data URL of the QR code. Any QR code library can generate this — the QR content must be `SYNC|{narrationId}|{marker}`.

## Directory Structure

The merge pipeline expects this directory layout:

```
my-screencast/
  storyboard.json          # narration declarations
  videos/
    recording.webm       # raw screen recording with sync frames
```

And produces:

```
my-screencast/
  storyboard.json
  videos/
    recording.webm
  narration-audio/       # generated TTS audio segments
    segment_000.wav
    segment_001.wav
  narration-tmp/         # intermediate files (can be deleted)
  my-screencast.mp4      # final narrated video
  timeline.json          # computed timeline with timestamps, audio durations, freeze frames
  gap-cuts.json          # dead air gaps that were cut
  timeline.html          # interactive timeline visualization
```

## Running the Merge Pipeline

### CLI

```bash
screencast-narrator my-screencast/
```

### Python

```python
from pathlib import Path
from screencast_narrator.merge import process

process(Path("my-screencast"))
```

### Custom TTS

```python
from screencast_narrator.tts import TTSBackend
from screencast_narrator.merge import process
from pathlib import Path

class MyTTS(TTSBackend):
    def generate(self, text: str, output_path: Path) -> None:
        # write a WAV file to output_path
        ...

process(Path("my-screencast"), tts_backend=MyTTS())
```

## Client Libraries

Helper classes are provided for Python, TypeScript, and Java. They manage narration IDs, screen action IDs, and `storyboard.json` serialization, and provide sync frame injection functions.

### Python (built-in)

```python
from screencast_narrator.storyboard import Storyboard
from screencast_narrator.sync_frames import inject_sync_frame

timeline = Storyboard(output_dir)
nid = timeline.begin_narration("We open the website.")
inject_sync_frame(page, nid, "START")
timeline.add_screen_action("Navigate to example.com")
# ... perform actions ...
inject_sync_frame(page, nid, "END")
timeline.end_narration()
```

### TypeScript

Source: [`api/typescript-client/src/index.ts`](../api/typescript-client/src/index.ts)

```typescript
import { Storyboard, injectSyncFrame } from "screencast-narrator";

const timeline = new Storyboard(outputDir);
const nid = timeline.beginNarration("We open the website.");
await injectSyncFrame(page, nid, "START");
timeline.addScreenAction("Navigate to example.com");
// ... perform actions ...
await injectSyncFrame(page, nid, "END");
timeline.endNarration();
```

### Java

Source: [`api/java-client/src/main/java/screencastnarrator/`](../api/java-client/src/main/java/screencastnarrator/)

```java
import screencastnarrator.Storyboard;
import screencastnarrator.SyncFrames;

Storyboard timeline = new Storyboard(outputDir);
int nid = timeline.beginNarration("We open the website.");
SyncFrames.injectSyncFrame(page, nid, "START");
timeline.addScreenAction("Navigate to example.com");
// ... perform actions ...
SyncFrames.injectSyncFrame(page, nid, "END");
timeline.endNarration();
```

All three follow the same pattern for each narration bracket:

```
1. Begin narration (declare text, get narration ID)
2. Inject START sync frame (green QR overlay for ~160ms)
3. Perform screen actions (navigate, click, type, scroll)
4. Inject END sync frame (green QR overlay for ~160ms)
5. End narration (flush to storyboard.json)
```

## Sample Code

Full working examples that record a Wikipedia search screencast are in the [`examples/`](../examples/) directory:

| Language | File | Client Library |
|----------|------|---------------|
| Python | [`record_wikipedia_search.py`](../examples/record_wikipedia_search.py) | `screencast_narrator.storyboard` + `screencast_narrator.sync_frames` |
| TypeScript | [`record_wikipedia_search.ts`](../examples/record_wikipedia_search.ts) | [`api/typescript-client/`](../api/typescript-client/) |
| Java | [`RecordWikipediaSearch.java`](../examples/RecordWikipediaSearch.java) | [`api/java-client/`](../api/java-client/) |

Each example navigates to Wikipedia, searches for "restaurant", reads section headings, and produces a `storyboard.json` + recorded video. The E2E test randomly picks between available languages to verify the API works across all of them.

### Running an example

```bash
# Python
python examples/record_wikipedia_search.py my-screencast/

# TypeScript
npx tsx examples/record_wikipedia_search.ts my-screencast/

# Java
mvn -f examples/pom.xml compile exec:java -Dexec.args="my-screencast/"

# Then produce the final narrated video
screencast-narrator my-screencast/
```

## How the Pipeline Processes Your Input

1. **Read** `storyboard.json` to get narration texts
2. **Generate TTS** audio for each narration (WAV files cached by text hash)
3. **Extract frames** from the video at 25 FPS
4. **Detect green frames** (R < 80, G > 180, B < 80 at sample points)
5. **Decode QR codes** from green frames to find `SYNC|id|START` and `SYNC|id|END` markers
6. **Strip sync frames** from the video (they are removed from the final output)
7. **Map narration brackets** to video positions using sync frame locations
8. **Calculate freeze frames** where narration audio exceeds the bracket duration
9. **Build extended video** with freeze frames inserted
10. **Detect and cut dead air** gaps longer than 2 seconds between narrations
11. **Overlay audio** segments at their computed positions
12. **Write final MP4** with H.264 video and AAC audio
