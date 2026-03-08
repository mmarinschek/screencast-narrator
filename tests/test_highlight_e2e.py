"""E2E test: verify highlights are visually rendered in the screencast.

Uses a simple white HTML page with a centered button. Records a screencast
with a highlight on the button using randomized color and animation speed,
processes through the full pipeline, then verifies the highlight animation
fades in and out in both source and output.

The recording phase randomly picks between Python, TypeScript, and Java
implementations to verify the highlight API works across languages.

Requirements:
    pip install -e ".[e2e]" && playwright install chromium

    For TypeScript recording:
        npm install playwright qrcode
        npx playwright install chromium

    For Java recording:
        mvn compile (in examples/ with pom.xml)
"""

from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from screencast_narrator.merge import process

_PROJECT_ROOT = Path(__file__).parent.parent
_EXAMPLES_DIR = _PROJECT_ROOT / "examples"

_TEST_PAGE = """<!DOCTYPE html>
<html>
<body style="margin:0; background:white; display:flex; justify-content:center; align-items:center; height:100vh;">
  <button id="target" style="padding:20px 40px; font-size:24px; cursor:pointer;">Click Me</button>
</body>
</html>"""

_BASE_ANIMATION_SPEED_MS = 600


def _random_color() -> str:
    hue = random.choice(["red", "orange", "blue", "purple"])
    if hue == "red":
        return f"#{random.randint(200, 255):02x}{random.randint(0, 60):02x}{random.randint(0, 60):02x}"
    if hue == "orange":
        return f"#{random.randint(220, 255):02x}{random.randint(100, 180):02x}{random.randint(0, 40):02x}"
    if hue == "blue":
        return f"#{random.randint(0, 60):02x}{random.randint(0, 100):02x}{random.randint(200, 255):02x}"
    return f"#{random.randint(150, 255):02x}{random.randint(0, 60):02x}{random.randint(150, 255):02x}"


def _random_animation_speed_ms() -> int:
    factor = random.uniform(0.2, 5.0)
    return int(_BASE_ANIMATION_SPEED_MS * factor)


def _can_run_typescript() -> bool:
    return shutil.which("npx") is not None and (_EXAMPLES_DIR / "record_highlight_test.ts").exists()


def _can_run_java() -> bool:
    if shutil.which("java") is None or shutil.which("mvn") is None:
        return False
    return (_EXAMPLES_DIR / "RecordHighlightTest.java").exists()


def _choose_recording_language() -> str:
    available = ["python"]
    if _can_run_typescript():
        available.append("typescript")
    if _can_run_java():
        available.append("java")
    return random.choice(available)


def _record_with_python(output_dir: Path, html_path: Path, color: str, animation_speed_ms: int) -> None:
    result = subprocess.run(
        [sys.executable, str(_EXAMPLES_DIR / "record_highlight_test.py"),
         str(output_dir), str(html_path), color, str(animation_speed_ms)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Python recording failed:\n{result.stdout}\n{result.stderr}")


def _record_with_typescript(output_dir: Path, html_path: Path, color: str, animation_speed_ms: int) -> None:
    result = subprocess.run(
        ["npx", "tsx", str(_EXAMPLES_DIR / "record_highlight_test.ts"),
         str(output_dir), str(html_path), color, str(animation_speed_ms)],
        capture_output=True, text=True, timeout=120, cwd=str(_PROJECT_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"TypeScript recording failed:\n{result.stdout}\n{result.stderr}")


def _record_with_java(output_dir: Path, html_path: Path, color: str, animation_speed_ms: int) -> None:
    result = subprocess.run(
        [
            "mvn", "-f", str(_EXAMPLES_DIR / "pom.xml"),
            "compile", "exec:java",
            "-Dexec.mainClass=RecordHighlightTest",
            f"-Dexec.args={output_dir} {html_path} {color} {animation_speed_ms}",
        ],
        capture_output=True, text=True, timeout=180, cwd=str(_EXAMPLES_DIR),
    )
    if result.returncode != 0:
        raise RuntimeError(f"Java recording failed:\n{result.stdout}\n{result.stderr}")


def _extract_all_frames(video: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(output_dir / "frame_%04d.png")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), pattern],
        capture_output=True, text=True, check=True,
    )
    return sorted(output_dir.glob("frame_*.png"))


def _count_highlight_pixels(img: Image.Image, step: int = 4, min_saturation: int = 60) -> int:
    """Count pixels that are colored but not pure-green sync frames."""
    rgb = img.convert("RGB")
    count = 0
    for x in range(0, rgb.width, step):
        for y in range(0, rgb.height, step):
            r, g, b = rgb.getpixel((x, y))  # type: ignore[misc]
            if max(r, g, b) - min(r, g, b) < min_saturation:
                continue
            if r < 80 and g > 180 and b < 80:
                continue
            count += 1
    return count


def _collect_highlight_curve(frames: list[Path], sample_every: int = 3) -> list[int]:
    curve: list[int] = []
    for i in range(0, len(frames), sample_every):
        img = Image.open(frames[i])
        curve.append(_count_highlight_pixels(img))
    return curve


def _assert_highlight_animation(curve: list[int], label: str) -> None:
    nonzero = [c for c in curve if c > 0]
    assert len(nonzero) >= 2, (
        f"[{label}] Expected at least 2 sampled frames with highlight pixels, "
        f"found {len(nonzero)}. Curve: {curve}"
    )

    peak_val = max(curve)
    peak_idx = curve.index(peak_val)

    before_peak = curve[:peak_idx]
    after_peak = curve[peak_idx + 1:]
    has_lower_before = any(c < peak_val for c in before_peak) or not before_peak
    has_lower_after = any(c < peak_val for c in after_peak) or not after_peak
    assert has_lower_before and has_lower_after, (
        f"[{label}] Highlight should animate (grow then shrink). "
        f"Peak={peak_val} at idx={peak_idx}. Curve: {curve}"
    )


@pytest.mark.e2e
def test_highlight_visible_in_screencast(tmp_path: Path) -> None:
    """Record a highlight with randomized style (random language), verify animation in source and output."""
    language = _choose_recording_language()
    color = _random_color()
    animation_speed = _random_animation_speed_ms()
    print(f"\nRecording language: {language}")
    print(f"Highlight: color={color}, animation_speed={animation_speed}ms")

    output_dir = tmp_path / "highlight-test"
    test_html = tmp_path / "test.html"
    test_html.write_text(_TEST_PAGE, encoding="utf-8")

    if language == "python":
        _record_with_python(output_dir, test_html, color, animation_speed)
    elif language == "typescript":
        _record_with_typescript(output_dir, test_html, color, animation_speed)
    elif language == "java":
        _record_with_java(output_dir, test_html, color, animation_speed)

    storyboard_json = output_dir / "storyboard.json"
    assert storyboard_json.exists(), f"storyboard.json was not created by {language} recorder"

    data = json.loads(storyboard_json.read_text(encoding="utf-8"))
    narration = data["narrations"][0]
    has_highlight = (
        any(a.get("type") == "highlight" for a in narration.get("screenActions", []))
        or len(narration.get("highlights", [])) > 0
    )
    assert has_highlight, f"No highlight found in storyboard narration: {narration}"

    videos_dir = output_dir / "videos"
    webm_files = list(videos_dir.glob("*.webm"))
    assert len(webm_files) == 1

    source_frames = _extract_all_frames(webm_files[0], tmp_path / "source_frames")
    source_curve = _collect_highlight_curve(source_frames)
    _assert_highlight_animation(source_curve, f"source[{language}] (color={color}, speed={animation_speed}ms)")

    process(output_dir)

    output_mp4 = output_dir / "highlight-test.mp4"
    assert output_mp4.exists()

    timeline = json.loads((output_dir / "timeline.json").read_text(encoding="utf-8"))
    assert len(timeline["narrations"]) == 1
    assert any(
        a["type"] == "highlight"
        for a in timeline["narrations"][0].get("screenActions", [])
    )

    output_frames = _extract_all_frames(output_mp4, tmp_path / "output_frames")
    assert len(output_frames) >= 5
    output_curve = _collect_highlight_curve(output_frames)
    _assert_highlight_animation(output_curve, f"output[{language}] (color={color}, speed={animation_speed}ms)")
