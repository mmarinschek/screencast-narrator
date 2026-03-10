"""Debug overlay: generates drawtext filters and QR timestamp video for pipeline visualization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import qrcode
from PIL import Image

from screencast_narrator.ffmpeg import exec_ffmpeg, secs
from screencast_narrator.narration_segment import NarrationSegment
from screencast_narrator_client.generated.storyboard_types import (
    Model as StoryboardModel,
)


def _find_font() -> str | None:
    candidates = [
        Path("/System/Library/Fonts/Menlo.ttc"),
        Path("/System/Library/Fonts/Supplemental/Courier New.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf"),
        Path("C:/Windows/Fonts/consola.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


_FONT_FILE = _find_font()
_BOX = "box=1:boxcolor=black@0.7:boxborderw=6"


@dataclass(frozen=True)
class OverlayResult:
    filter_str: str
    qr_video: Path


def generate_qr_timestamp_video(duration_s: float, temp_dir: Path, qr_size: int = 100, fps: int = 25) -> Path:
    qr_dir = temp_dir / "qr_timestamps"
    qr_dir.mkdir(exist_ok=True)
    frame_duration_ms = 1000 / fps
    num_frames = int(duration_s * fps) + fps
    for i in range(num_frames):
        ms = int(i * frame_duration_ms)
        qr = qrcode.QRCode(box_size=4, border=1)
        qr.add_data(str(ms))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        img = img.resize((qr_size, qr_size), Image.NEAREST)
        img.save(qr_dir / f"qr_{i:06d}.png")

    qr_video = temp_dir / "qr_timestamps.mp4"
    exec_ffmpeg(
        "-y", "-framerate", str(fps),
        "-i", str(qr_dir / "qr_%06d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-t", secs(duration_s),
        str(qr_video),
    )
    return qr_video


def generate_overlay_filter(
    narrations: list[NarrationSegment],
    final_timestamps: list[int],
    storyboard: StoryboardModel,
    temp_dir: Path,
    font_size: int = 24,
) -> OverlayResult:
    overlay_dir = temp_dir / "overlay_texts"
    overlay_dir.mkdir(exist_ok=True)
    parts: list[str] = []
    idx = 0
    lh = int(font_size * 1.4)

    def _dt_expr(expr: str, x: str, y: int, color: str, enable_range: str = "") -> str:
        font_opt = f":fontfile={_FONT_FILE}" if _FONT_FILE else ""
        enable = f":enable='between(t,{enable_range})'" if enable_range else ""
        return f"drawtext=text='{expr}':x={x}:y={y}:fontsize={font_size}{font_opt}:fontcolor={color}:{_BOX}{enable}"

    def _dt_file(text: str, x: str, y: int, color: str, enable_range: str = "") -> str:
        nonlocal idx
        txt_file = overlay_dir / f"t{idx}.txt"
        txt_file.write_text(text, encoding="utf-8")
        idx += 1
        font_opt = f":fontfile={_FONT_FILE}" if _FONT_FILE else ""
        enable = f":enable='between(t,{enable_range})'" if enable_range else ""
        return f"drawtext=textfile={txt_file}:x={x}:y={y}:fontsize={font_size}{font_opt}:fontcolor={color}:{_BOX}{enable}"

    top = 50
    parts.append(_dt_expr("%{pts\\:hms}", "10", top, "lime"))
    parts.append(_dt_expr("%{pts\\:ms}", "(w-text_w-10)", top, "lime"))

    def _narration_label(i: int) -> str:
        n = narrations[i]
        s = final_timestamps[i]
        e = s + n.audio_duration_ms
        return f"{_fmt_ms(s)}-{_fmt_ms(e)} N{i}: {n.text[:55]}"

    for i, n in enumerate(narrations):
        start_s = final_timestamps[i] / 1000.0
        end_s = (final_timestamps[i] + n.audio_duration_ms) / 1000.0
        rng = f"{start_s:.3f},{end_s:.3f}"
        if i > 0:
            parts.append(_dt_file(f"PREV {_narration_label(i - 1)}", "10", top + 1 * lh, "gray", rng))
        parts.append(_dt_file(f"NOW  {_narration_label(i)}", "10", top + 2 * lh, "white", rng))
        if i < len(narrations) - 1:
            parts.append(_dt_file(f"NEXT {_narration_label(i + 1)}", "10", top + 3 * lh, "gray", rng))

    max_end_ms = max(
        (final_timestamps[i] + narrations[i].audio_duration_ms for i in range(len(narrations))),
        default=0,
    )
    duration_s = max_end_ms / 1000.0 + 2.0
    qr_video = generate_qr_timestamp_video(duration_s, temp_dir)

    return OverlayResult(filter_str=",".join(parts), qr_video=qr_video)


def _fmt_ms(ms: int) -> str:
    total_s = ms / 1000.0
    minutes = int(total_s) // 60
    seconds = total_s - minutes * 60
    return f"{minutes:02d}:{seconds:06.3f}"
